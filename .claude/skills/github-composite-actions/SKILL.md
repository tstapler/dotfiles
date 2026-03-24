---
name: github-composite-actions
description: Use when writing, debugging, or designing GitHub Actions composite actions. Covers the `uses:` field rules, relative path resolution, composite-to-composite calling, secrets limitations, differences from reusable workflows, and best practices.
---

# GitHub Actions Composite Actions

Reference for writing and debugging composite actions (`action.yml` files with `runs.using: composite`).

## Critical Limitations (Know Before You Code)

### `uses:` Does NOT Support Expressions

The `uses:` field is evaluated at parse time — expressions like `${{ inputs.ref }}` or `${{ env.VERSION }}` will **not** be evaluated. All references must be literal strings.

```yaml
# WRONG — will not work
uses: my-org/actions/my-action@${{ inputs.version }}

# CORRECT — must be a literal ref
uses: my-org/actions/my-action@v2
uses: my-org/actions/my-action@abc1234
uses: my-org/actions/my-action@main
```

**Confirmed by:** [GitHub community discussion #44832](https://github.com/orgs/community/discussions/44832), GitHub staff, and official docs:
> "You cannot use contexts or expressions in this keyword."

**Workaround:** Pass the ref value as an `input` to the action, and have the action use it inside a `run:` step or pass it to a nested checkout.

### Secrets Context Is Blocked

Composite actions cannot access `${{ secrets.MY_SECRET }}` directly. The `secrets` context is unavailable.

```yaml
# WRONG — secrets context unavailable
- run: echo ${{ secrets.MY_TOKEN }}

# CORRECT — require caller to pass secrets as inputs
inputs:
  github-token:
    required: true
steps:
  - run: echo ${{ inputs.github-token }}
```

Secrets passed as inputs **are masked in logs** by the runner.

Sources: [actions/runner issue #1284](https://github.com/actions/runner/issues/1284), [docs issue #12705](https://github.com/github/docs/issues/12705)

### `GITHUB_ENV` Does Not Propagate to Caller

Environment variables set via `$GITHUB_ENV` inside a composite action stay within the composite — they do **not** flow back to the calling workflow's subsequent steps.

### No Top-Level `env:` Block

There is no job-level `env:` block in `action.yml`. Set env vars at the step level only:

```yaml
steps:
  - name: My step
    shell: bash
    env:
      MY_VAR: ${{ inputs.my-input }}
    run: echo "$MY_VAR"
```

---

## Relative Path Resolution

Relative paths in composite action `uses:` resolve to **`$GITHUB_WORKSPACE`**, not to the current action's directory.

```yaml
# In .github/actions/my-action/action.yml:
steps:
  - uses: ./other-action
  # Resolves to: $GITHUB_WORKSPACE/other-action  (NOT .github/actions/other-action)
```

This is a known pain point for monorepos. Tracked: [actions/runner issue #2101](https://github.com/actions/runner/issues/2101).

**Pattern to work around this:** Check out the actions repo explicitly, then reference by path:

```yaml
- uses: actions/checkout@v4
  with:
    repository: my-org/actions
    ref: v1
    path: actions-repo
    token: ${{ inputs.github-token }}

- uses: ./actions-repo/path/to/sibling-action
```

**Use `github.action_path` for scripts/files relative to the action itself:**

```yaml
- shell: bash
  run: ${{ github.action_path }}/scripts/my-script.sh
```

---

## Composite Calling Composite

Composite actions support nesting up to **10 levels deep**. If the limit is exceeded, the job fails during "Set up job."

Each level receives only what is explicitly passed via `with:` — no implicit context or env inheritance.

```yaml
# Outer composite: my-org/actions/build/action.yml
steps:
  - uses: my-org/actions/build/report-error@v1   # literal ref required
    with:
      github-token: ${{ inputs.github-token }}   # must explicitly re-pass
      build-tool: GRADLE
```

Reusable workflows, by contrast, **cannot** call other reusable workflows (one level only).

---

## Composite vs. Reusable Workflow — When to Use Which

| Need | Use |
|------|-----|
| Reusable steps within a single job | Composite action |
| Multiple jobs with different runners | Reusable workflow |
| `secrets: inherit` | Reusable workflow |
| Deployment environments | Reusable workflow |
| Matrix strategy | Reusable workflow |
| Caller can add steps before/after | Composite action |
| Steps need to run on same runner as caller | Composite action |

**Full limitation comparison (composite actions lack these vs. workflows):**

- Multiple jobs / `needs:` dependency graph
- `runs-on:` per-job runner selection
- `secrets:` context (must pass as inputs)
- Job-level `env:` block
- Job-level `if:` / `continue-on-error:` / `timeout-minutes:`
- `environment:` (deployment environments)
- `concurrency:` groups
- Matrix strategy

---

## Best Practices

### Always Use `github.action_path` for Internal Files

```yaml
- shell: bash
  run: ${{ github.action_path }}/scripts/setup.sh
```

### Pin External Actions to a SHA or Tag

```yaml
- uses: actions/checkout@v4          # tag — readable
- uses: actions/checkout@abc1234     # SHA — more secure
# Never: uses: actions/checkout@main  (in production)
```

### Explicit Input-to-Env Mapping

Composite actions do NOT auto-expose inputs as env vars. Map them explicitly:

```yaml
steps:
  - name: Run build
    shell: bash
    env:
      BUILD_TOOL: ${{ inputs.build-tool }}
      OUTPUT_FILE: ${{ inputs.output-file }}
    run: ./build.sh
```

### Descriptive Step Names

All steps are collapsed under the parent step in the GitHub UI. Add clear names so the collapsed view is readable.

### `continue-on-error: true` on Optional Steps

For observability or reporting steps that should never block the primary outcome:

```yaml
- name: Report errors
  if: always() && steps.build.outputs.build_failed == 'true'
  continue-on-error: true
  uses: my-org/actions/report-error@v1
  with:
    github-token: ${{ github.token }}
```

### Deferred Exit Code Pattern

When you need artifacts/reporting to run even after a build failure, capture the exit code instead of failing immediately:

```yaml
- name: Build
  id: build
  shell: bash {0}          # disables errexit for this step
  run: |
    ./gradlew build
    echo "exit_code=$?" >> $GITHUB_OUTPUT
    echo "build_failed=$([[ $? -ne 0 ]] && echo true || echo false)" >> $GITHUB_OUTPUT

- name: Upload logs
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: build-logs
    path: /tmp/build-output.txt

- name: Exit with real status
  shell: bash
  run: exit $(cat /tmp/build-exit-code.txt)
```

---

## Sources

- [GitHub Docs: Creating a composite action](https://docs.github.com/actions/creating-actions/creating-a-composite-action)
- [GitHub Docs: Metadata syntax reference](https://docs.github.com/en/actions/reference/workflows-and-actions/metadata-syntax)
- [GitHub Docs: Reuse workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows)
- [Community #44832: `uses` does not evaluate expressions](https://github.com/orgs/community/discussions/44832)
- [actions/runner #1284: Secrets in composite actions](https://github.com/actions/runner/issues/1284)
- [actions/runner #2101: Monorepo composite action path resolution](https://github.com/actions/runner/issues/2101)
- [actions/runner ADR 1144: Composite actions design (10-level nesting limit)](https://github.com/actions/runner/blob/main/docs/adrs/1144-composite-actions.md)
- [DEV: Composite Actions vs Reusable Workflows](https://dev.to/n3wt0n/composite-actions-vs-reusable-workflows-what-is-the-difference-github-actions-11kd)