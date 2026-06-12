---
name: fix-ci-failures
description: Diagnose and fix CI failures on main or release branches. Checks GitHub Actions run status, reads failure logs, applies fixes, and verifies a re-run passes. Use when CI is red on main, a release is broken, or you want to confirm all checks are green before shipping.
---

# fix-ci-failures

Systematically diagnose, fix, and verify all CI failures on a branch.

## Workflow

### Step 1 — Assess current state

```bash
gh run list --branch main --limit 5 --json status,conclusion,name,headSha \
  | python3 -c "
import json,sys
runs = json.load(sys.stdin)
sha = runs[0]['headSha'][:8]
print('HEAD:', sha)
for r in runs:
    if r['headSha'][:8] == sha:
        icon = '✅' if r['conclusion'] == 'success' else ('❌' if r['conclusion'] == 'failure' else '⏳')
        print(f'{icon} {r[\"conclusion\"] or r[\"status\"]:12} {r[\"name\"]}')"
```

If any jobs are still `in_progress`, wait before diagnosing. Get the run IDs of failures:

```bash
gh run list --branch main --limit 5 --json databaseId,name,conclusion,headSha \
  | python3 -c "
import json,sys
runs = json.load(sys.stdin)
sha = runs[0]['headSha'][:8]
for r in runs:
    if r['headSha'][:8] == sha and r['conclusion'] == 'failure':
        print(r['databaseId'], r['name'])"
```

### Step 2 — Read failure logs for each failed job

```bash
gh run view --log-failed <RUN_ID> 2>&1 | grep -E "Error:|error:|FAIL|fatal|##\[error\]" \
  | grep -v "Warning\|warning\|boundaries" | head -30
```

**Critical**: always read logs to the end — the REAL failure is usually the last `##[error]` line, not the first warning in the log. Debug messages that look like errors (e.g. `❯ error message:` in release-please logs) are often not the actual failure.

```bash
gh run view --log-failed <RUN_ID> 2>&1 | tail -40
```

### Step 3 — Classify each failure

| Symptom | Category | Fix |
|---|---|---|
| `GitHub Actions is not permitted to create or approve pull requests` | Repo settings | Enable in Settings → Actions → General, or add RELEASE_TOKEN PAT |
| `Permission to *.git denied to github-actions[bot]` | Workflow permissions | Add `permissions: contents: write` to the job |
| `git push` rejected (fetch first) | Race condition | Add retry loop: `for i in 1 2 3; do git pull --rebase --autostash && git push && break \|\| sleep 5; done` |
| `ESLint: Error:` in specific file | Code lint | Fix the violation in the flagged file |
| `gofmt` unformatted files | Go formatting | `gofmt -w <files>` |
| `go vet` / `lint-custom` compile error | Working tree contamination from other sessions | `git checkout -- <file>` to restore, then re-run |
| `useMemo/useState called conditionally` | React hooks rule | Move hook call above the early return |
| `Component definition is missing display name` | React displayName | Add `.displayName = "Name"` or use `Object.assign(component, { displayName: "Name" })` |
| `unexpected token` in commit body | Commit parser quirk | Usually a debug message, not the real failure — read to end of log |
| Benchmark baseline push rejected | Same race condition | Retry loop (see above) |
| `node_modules` / dependency install fails | Infrastructure | Check for lockfile conflicts; re-run often fixes it |

### Step 4 — Apply fixes

Fix each failure using the appropriate pattern. Follow these rules:

1. **Check if the failure pre-existed our commits** before fixing:
   ```bash
   git log --oneline <baseline-sha>..HEAD -- <file>
   ```
   If the file isn't in our commit range, the failure is from another session's work — still fix it.

2. **Never restore working-tree contamination as a fix** — always identify root cause.

3. **For gofmt**: run on the exact files listed, not `gofmt -w .` (avoid touching unrelated files).

4. **For React hooks**: move the hook call above ALL early returns. Hooks on empty arrays/maps are cheap no-ops.

5. **For missing displayName inside useMemo object literals**: use `// eslint-disable-next-line react/display-name` — the lint rule cannot see displayName assignments at object-literal depth, and this is the correct suppression.

6. **For permissions**: `permissions: contents: write` goes on the **job** level, not workflow level, unless all jobs need it.

### Step 5 — Commit, push, and watch

```bash
git add <changed files>
git commit -m "fix(ci): <description of what was broken and how fixed>"
git fetch origin main && git rebase origin/main && git push origin main
```

**Primary: use `gh run watch` (GitHub's native blocking wait)**

Get the new run ID immediately after push, then watch it with `run_in_background: true`
so Claude is notified when it completes — no polling required:

```bash
# Wait ~5s for the run to register, then grab the latest run ID
sleep 5
RUN_ID=$(gh run list --branch main --limit 1 --json databaseId --jq '.[0].databaseId')
echo "Watching run $RUN_ID"
gh run watch "$RUN_ID" --exit-status
```

Run this with `run_in_background: true`. Claude will be notified when it finishes.
Exit code 0 = all green; non-zero = something failed.

> **Note**: `gh run watch` requires `checks:read` permission. If you authenticated
> with a fine-grained PAT that lacks this scope, it will fail — fall back to the
> polling loop below.

**Fallback: polling loop (use only if `gh run watch` is unavailable)**

```bash
until gh run list --branch main --limit 3 --json status,conclusion,name,headSha \
  | python3 -c "
import json,sys
runs = json.load(sys.stdin)
sha = runs[0]['headSha'][:8]
mine = [r for r in runs if r['headSha'][:8] == sha]
done = [r for r in mine if r['status'] == 'completed']
print(f'{len(done)}/{len(mine)} on {sha}')
for r in done:
    icon = '✅' if r['conclusion'] == 'success' else '❌'
    print(f'  {icon} {r[\"conclusion\"]} {r[\"name\"]}')
if len(done) == len(mine): sys.exit(0)
sys.exit(1)"; do sleep 30; done
```

### Step 6 — Verify all checks pass

After the run completes, confirm every job is green:

```bash
gh run list --branch main --limit 3 --json status,conclusion,name,headSha \
  | python3 -c "
import json,sys
runs = json.load(sys.stdin)
sha = runs[0]['headSha'][:8]
failures = [r for r in runs if r['headSha'][:8] == sha and r['conclusion'] == 'failure']
if failures:
    print('STILL FAILING:')
    for r in failures: print(' ❌', r['name'])
    sys.exit(1)
else:
    print('✅ All checks green on', sha)"
```

If still failing, return to Step 2.

## Known permanent failures (acceptable on this repo)

These are infra races that self-resolve — do NOT spend time fixing them if they're the only remaining failures:

- **Benchmarks "Update baseline" push rejected** — race when multiple commits land rapidly. The retry loop fixes most cases; occasional failures are acceptable and self-resolve on the next push.
- **Release Please creating a release PR** — requires `RELEASE_TOKEN` PAT or "Allow GitHub Actions to create PRs" repo setting. Fix once per repo, not per run.
- **Publish Demo GIFs 403** — requires `permissions: contents: write` on the job. Fix the workflow file once.

## Escaping working-tree contamination

Other sessions may leave modified files in the working tree that break compilation when CI's linter runs. Before diagnosing:

```bash
git status --short | grep -v "^??"  # look for unexpected modified files
```

If you see files you didn't touch that are broken, restore them:
```bash
git checkout -- <file>
```

Then re-run CI locally (`make lint-custom`, `make lint-css-tokens`) to confirm your commits are clean before pushing.

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `github-actions-debugging` | Diagnose failures inside specific workflow steps or composite actions |
| `lean-agent-loop` | Parallelize multiple failing job categories and iterate fix cycles until all checks pass |
