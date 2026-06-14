---
name: github-actions-authoring
description: Use when writing, reviewing, or designing GitHub Actions workflows. Covers
  the full decision framework (composite actions vs reusable workflows), security
  tooling (actionlint, zizmor, pinact), anti-patterns from real incident reviews, and
  the long-term direction toward a CUE-based config generator.
---

# GitHub Actions Authoring Guide

Reference for writing maintainable, secure GitHub Actions workflows. Complements
`/github-composite-actions` (composite action mechanics) and `/github-actions-debugging`
(CI failure diagnosis).

---

## Decision Framework: What Kind of Abstraction?

Always start here before writing a new workflow or extracting shared logic.

| Goal | Use |
|------|-----|
| Reuse a group of steps inside one job | **Composite action** (`.github/actions/<name>/action.yml`) |
| Reuse an entire job with its own runner/permissions | **Reusable workflow** (`workflow_call`) |
| Fan out across OS/version combinations | **Matrix strategy** in one workflow |
| Trigger a deploy only when specific files change | **Path filters** + job `if:` conditions |
| Share workflows across every repo in an org | **`.github` org repository** |

**Rule of thumb:** if it needs `runs-on:`, `environment:`, `permissions:`, or `secrets:` at the job level — it's a reusable workflow. If it's just steps — it's a composite action.

See `/github-composite-actions` for composite action mechanics and limitations.

---

## Security Baseline — Run These on Every Workflow PR

### actionlint

Statically checks workflow YAML for correctness. Runs `shellcheck` on embedded `run:` scripts. Catches type errors in `${{ }}` expressions that are invisible to YAML validators.

```bash
# Install (one-time, pin to a specific version)
curl -sSfL \
  "https://github.com/rhysd/actionlint/releases/download/v1.7.12/actionlint_1.7.12_linux_amd64.tar.gz" \
  | tar -xz -C ~/.local/bin actionlint

# Run against all workflows in the repo
actionlint -color

# Run against a single file
actionlint -color .github/workflows/ci.yml
```

**What it catches that nothing else does:**
- `${{ github.event.pull_request.lablels }}` — typo in expression field name (caught as type error)
- `|| true` that accidentally inverts an assertion (via shellcheck)
- `needs.foo` referencing a job that doesn't exist
- `run:` steps missing `shell:` inside composite actions
- Undefined outputs referenced from other jobs

**In CI** (from `ci.yml`):
```yaml
- name: Install actionlint
  run: |
    ACTIONLINT_VERSION="1.7.12"
    curl -sSfL \
      "https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/actionlint_${ACTIONLINT_VERSION}_linux_amd64.tar.gz" \
      | tar -xz -C /usr/local/bin actionlint
- name: Run actionlint
  run: actionlint -color
```

### zizmor

Security-focused auditor. Catches issues that are syntactically valid but dangerous.

```bash
# Run (no install — uvx handles it via PyPI)
uvx 'zizmor==1.25.2' .

# With GitHub token (enables action metadata lookups for permission auditing)
GH_TOKEN=$(gh auth token) uvx 'zizmor==1.25.2' .

# Update to latest
uvx 'zizmor' .  # omit version pin to get latest
```

**What it catches that actionlint doesn't:**
- Floating action tags (`@v4`) — mutable, supply-chain attack surface
- Template injection: `${{ github.event.issue.body }}` used directly in a `run:` step
- Excessive permissions: job requests `contents: write` but only reads
- `pull_request_target` misuse (can expose secrets to fork PRs)
- `secrets: inherit` passing more secrets than the callee needs

**Suppress a known false positive** (use sparingly; document why):
```yaml
# zizmor: ignore[unpinned-uses]
- uses: actions/checkout@v4
```

Or via `.zizmor.yml`:
```yaml
rules:
  unpinned-uses:
    ignore:
      - actions/checkout
      - actions/setup-java
```

### pinact — Pin Floating Tags to SHAs

```bash
# Install
go install github.com/suzuki-shunsuke/pinact/cmd/pinact@latest

# Pin all actions in .github/ to commit SHAs (adds version comment)
pinact run
# Result: uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2

# Validate that all actions are pinned (for CI enforcement)
pinact run --check

# Update pinned SHAs to latest version
pinact run --update
```

**Use Dependabot to keep SHAs updated automatically** (`.github/dependabot.yml`):
```yaml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    groups:
      github-actions:
        patterns: ["*"]
```

---

## Security Anti-Patterns (from Real Workflow Audits)

### `secrets: inherit` — Least Privilege Violation

```yaml
# WRONG — passes ALL repo secrets (Android keystore, Gradle key, etc.) to fdroid job
uses: ./.github/workflows/fdroid.yml
secrets: inherit

# CORRECT — enumerate only what the callee actually needs
uses: ./.github/workflows/fdroid.yml
secrets:
  FDROID_KEYSTORE_BASE64: ${{ secrets.FDROID_KEYSTORE_BASE64 }}
  FDROID_KEY_PASS: ${{ secrets.FDROID_KEY_PASS }}
  FDROID_STORE_PASS: ${{ secrets.FDROID_STORE_PASS }}
```

Requires the callee to declare `on.workflow_call.secrets:` explicitly.

### Credentials Written to Workspace Files

```bash
# WRONG — keystore in workspace directory, adjacent to artifact upload paths
echo "$KEYSTORE_B64" | base64 -d > repo/keystore.p12

# CORRECT — write outside the working tree entirely
echo "$KEYSTORE_B64" | base64 -d > /tmp/keystore.p12
```

**Why:** Artifact upload globs (`fdroid/repo`) are close to credential files (`fdroid/keystore.p12`). One typo in a glob exposes the key publicly for 90 days.

### Credentials in Heredoc Shell Expansion

```bash
# WRONG — shell expands ${PASSWORD} before writing; special chars corrupt YAML
cat >> config.yml <<EOF
password: ${FDROID_STORE_PASS}
EOF

# CORRECT — printf handles special chars without YAML corruption risk
printf 'password: %s\n' "$FDROID_STORE_PASS" >> config.yml

# BEST — use a tool that understands the target format
yq -i ".password = strenv(FDROID_STORE_PASS)" config.yml
```

### `workflow_call` Without Caller Guard

Without caller restrictions, any workflow in the repo (including one introduced in a PR) can call a signing workflow and access secrets:

```yaml
# Restrict workflow_call to the specific authorized callers
jobs:
  publish:
    if: |
      github.event_name == 'workflow_dispatch' ||
      github.event_name == 'release' ||
      (github.event_name == 'workflow_call' &&
       startsWith(github.workflow_ref, 'my-org/my-repo/.github/workflows/release.yml@'))
```

---

## Correctness Anti-Patterns

### Silent Failure — `|| true` on Critical Operations

```bash
# WRONG — if every download fails, the next step runs on an empty directory
while read -r tag; do
  gh release download "$tag" --pattern "*.apk" --dir repo/ || true
done

# CORRECT — track success separately; fail loudly if nothing downloaded
DOWNLOADED=0
while read -r tag; do
  gh release download "$tag" --pattern "*.apk" --dir repo/ 2>/dev/null && DOWNLOADED=$((DOWNLOADED+1))
done
if [ "$DOWNLOADED" -eq 0 ]; then
  echo "No APKs downloaded — refusing to publish empty repo"
  exit 1
fi
```

### Doubled Error Suppression

```yaml
# WRONG — continue-on-error already handles step failure; || true additionally
# swallows auth/network errors that should be visible
- continue-on-error: true
  run: gh run download "$RUN_ID" --name artifact || true

# CORRECT — let continue-on-error do the single-level suppression
- continue-on-error: true
  run: gh run download "$RUN_ID" --name artifact
```

### Inverted File-Size Assertion

```bash
# WRONG — || true catches the exit 1, so the assertion never actually fails
find . -type f -size +90M | grep . && exit 1 || true

# CORRECT — check find output in a variable
LARGE=$(find . -type f -size +90M)
if [ -n "$LARGE" ]; then
  echo "Files exceed 90 MB limit:"
  echo "$LARGE"
  exit 1
fi
```

### Missing `timeout-minutes`

GitHub's default job timeout is 6 hours. A hung step (stalled download, hung process) blocks the concurrency group for the entire duration:

```yaml
jobs:
  publish:
    timeout-minutes: 30  # always set; scale to expected job duration × 2
```

### Artifact Path Contract Drift

When uploading an artifact, `actions/upload-artifact` preserves the full workspace-relative path. The consumer must account for this:

```yaml
# Upload: path is fdroid/repo → artifact contains fdroid/repo/...
- uses: actions/upload-artifact@v4
  with:
    name: fdroid-content
    path: fdroid/repo

# Download to dir: fdroid-content/ → files land at fdroid-content/fdroid/repo/
# NOT at fdroid-content/repo/
- run: gh run download "$RUN_ID" --name fdroid-content --dir fdroid-content/
- run: ls fdroid-content/fdroid/repo/  # correct path

# Document this contract where the upload and download are in separate files
```

---

## Architecture Patterns

### Single Deployer — Eliminate Dual-Writer Races

Two workflows that both deploy to the same target (GitHub Pages, a registry) create an ordering hazard. Even with `concurrency: cancel-in-progress: false`, a later workflow can overwrite a fresher deploy from the earlier one using a stale artifact snapshot.

```
WRONG:
  fdroid.yml  → uploads pages artifact → deploy-pages
  pages.yml   → uploads pages artifact → deploy-pages
  (whichever runs last wins — may overwrite newer F-Droid index with stale one)

CORRECT:
  pages.yml   → uploads site-content artifact only (no deploy)
  fdroid.yml  → downloads site-content, merges fdroid/repo, uploads pages artifact → deploy-pages
  (one deployer, one source of truth for what's on the site)
```

### Artifact Fallback — Search Multiple Runs

When a build step is conditionally skipped (e.g., only rebuild Wasm when app code changes), the fallback artifact download must search past the most recent run:

```bash
# WRONG — the most recent successful run may have skipped build-demo
LAST_RUN=$(gh run list --workflow pages.yml --status success --limit 1 \
  --json databaseId --jq '.[0].databaseId // empty')

# CORRECT — iterate until an artifact is found
for RUN_ID in $(gh run list --workflow pages.yml --status success --limit 20 \
  --json databaseId --jq '.[].databaseId'); do
  if gh run download "$RUN_ID" --name demo-dist --dir site/public/demo/ 2>/dev/null; then
    break
  fi
done
```

### Separate Concerns in Monolithic Jobs

A job that does fdroid indexing + demo artifact retrieval + npm build + content merge + Pages deployment has five failure domains. A failure in npm build blocks the fdroid index from publishing even though it succeeded. Split into separate jobs:

```yaml
jobs:
  generate-fdroid-index:
    timeout-minutes: 30
    steps:
      # fdroidserver only — uploads fdroid-index artifact
  
  build-site:
    needs: generate-fdroid-index
    timeout-minutes: 20
    steps:
      # npm build only — downloads fdroid-index, uploads site artifact
  
  deploy:
    needs: build-site
    steps:
      # deploy-pages only
```

---

## Dependency Pinning Strategy

| Tool | Command | Notes |
|------|---------|-------|
| `pinact` | `pinact run` | One-time: pins all `@v4` tags to SHAs |
| Dependabot | `.github/dependabot.yml` | Ongoing: weekly PR for updated SHAs |
| `fdroidserver` | `pip install fdroidserver==2.3.1` | Pin pip tools in signing jobs |
| apt packages | Version-pin in `apt-get install` | Only when package security matters |
| External binaries | Download with SHA256 verification | Any binary that touches secrets |

---

## Future Direction: Config Generator

### The Problem at Scale

With 5–10 workflow files, native composite actions + reusable workflows cover most duplication. At 20+ files across multiple repos, or when targeting multiple CI systems (GitHub Actions, GitLab CI, Buildkite), a config generator becomes worth the investment.

### Why CUE Lang

[CUE](https://cuelang.org) is a typed configuration language designed for exactly this class of problem:

- **Schema + data in one language** — define the shape of a valid workflow *and* the data that fills it, without a separate schema file
- **Constraints as code** — express invariants like "all jobs must have `timeout-minutes`" or "signing jobs must pin dependencies to SHAs" as CUE constraints that are checked at generation time
- **Imports and composition** — define a `setupGradle` mixin that expands to the correct steps, import it wherever needed
- **Multi-output** — a single CUE source can emit GitHub Actions YAML *and* GitLab CI YAML with different backends

### What a Generator Would Look Like

```cue
// .cue/workflows/patterns.cue

// Shared step mixin
#SetupGradle: {
    name: "Setup Gradle"
    uses: "gradle/actions/setup-gradle@\(gradleActionSHA)"  // SHA enforced by constraint
    with: {
        "gradle-home-cache-cleanup": true
        "cache-encryption-key": "${{ secrets.GRADLE_ENCRYPTION_KEY }}"
    }
}

// Constraint: every job must have timeout-minutes
#Job: {
    "timeout-minutes": int & >=5 & <=120
    // ... other required fields
}
```

Source: `.cue/workflows/ci.cue` → Generated: `.github/workflows/ci.yml`

### Scoping a Generator Project

**Phase 1 — Local validation only** (lowest cost, high value):
- CUE schema that validates existing `.github/workflows/*.yml` files
- Run in CI as a lint step alongside actionlint
- No code generation yet — just catches structural violations

**Phase 2 — Mixin library**:
- Define mixins for `setupGradle`, `setupNode`, `deployPages`
- Generate workflow YAML from CUE sources
- Commit both CUE source and generated YAML (diff-visible changes)

**Phase 3 — Multi-CI output**:
- Define an abstract pipeline model in CUE
- Backends: GitHub Actions, GitLab CI, Buildkite
- Enables moving between CI providers without rewriting logic

### Trade-offs vs Alternatives

| Approach | Learning Curve | Tooling Maturity | Best For |
|----------|---------------|-----------------|----------|
| CUE | Medium | Medium (v0.x, evolving) | Typed validation + generation |
| Dhall | High | Medium | Type-safe generation (functional style) |
| Jsonnet | Medium | Low (no GA Actions library) | Kubernetes-adjacent teams |
| Native only | None | Mature | <20 workflow files |

**Recommendation:** Start with Phase 1 (CUE validation schema) as a low-risk way to evaluate the toolchain before committing to generation. The CUE CLI can be installed via `brew install cue-lang/tap/cue`.

---

## Checklist for Every Workflow PR

Run this mentally or as a pre-commit script:

```bash
# Correctness
actionlint -color

# Security
uvx 'zizmor==1.25.2' .

# Verify all new actions are pinned
pinact run --check

# Confirm secrets: inherit is not used (prefer explicit enumeration)
grep -r 'secrets: inherit' .github/workflows/
```

Manual checks:
- [ ] Every job has `timeout-minutes`
- [ ] No credentials written to workspace files (use `/tmp`)
- [ ] No `|| true` on operations where failure should be visible
- [ ] Artifact upload paths documented if consumed by another workflow
- [ ] `continue-on-error` not doubled with `|| true`
- [ ] `workflow_call` callers restricted if the workflow accesses signing secrets

---

## Related Skills

- `/github-composite-actions` — Composite action mechanics, limitations, and gotchas
- `/github-actions-debugging` — Diagnosing CI failures
- `/github-pr` — PR review and gh CLI patterns
