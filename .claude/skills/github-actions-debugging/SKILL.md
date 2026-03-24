---
name: github-actions-debugging
description: Debug GitHub Actions workflow failures by analyzing logs, identifying error patterns, and providing actionable fixes. Use when CI/CD workflows fail, jobs timeout, or actions produce unexpected errors.
---

# GitHub Actions Debugging

Systematically diagnose and fix GitHub Actions failures. Provide precise fixes, not generic troubleshooting.

## Get Logs Fast

Always start here. Use `gh` CLI to fetch failure context before reading workflow files.

```bash
# List recent failed runs
gh run list --limit 10 --status failure

# View failed run summary (shows failed jobs/steps — get job IDs from here)
gh run view <run-id>

# Get job ID from PR URL (most common starting point)
gh pr checks <pr-number> --json name,conclusion,detailsUrl

# List jobs for a run to get job IDs
gh run view <run-id> --json jobs --jq '.jobs[] | "\(.databaseId) \(.name) \(.conclusion)"'
```

### CRITICAL: Always write logs to a unique temp file before parsing

**NEVER** pipe `gh run view --log` directly to `awk`, `grep -n`, or tools with flags.
The `gh` CLI intercepts flags like `-F`, `-n`, and `-v` when they appear in pipe chains.
Always use `mktemp` to create unique temp files — prevents collisions between parallel sessions.

```bash
# CORRECT — unique temp file, then parse
LOG=$(mktemp /tmp/gh-ci-XXXXXX.log)
gh run view <run-id> --repo <owner>/<repo> --log --job <job-id> > "$LOG" 2>&1
gh run view <run-id> --repo <owner>/<repo> --log-failed --job <job-id> > "$LOG" 2>&1

# WRONG — gh intercepts the -F flag, awk never sees it
gh run view <run-id> --log | awk -F'\t' '{print $3}'  # FAILS
gh run view <run-id> --log | grep -n "error"           # FAILS
```

### Parse logs after writing to file

GitHub Actions log format: `<job-name>\tUNKNOWN STEP\t<timestamp>Z <message>`

```bash
# Find errors — always use file path, not pipe
grep -i "error\|FAILED\|fatal\|Exit code" "$LOG" | head -40

# Strip the job/timestamp prefix to read clean messages (Python — most reliable)
python3 - "$LOG" << 'EOF'
import re, sys
for line in open(sys.argv[1]):
    # Strip: "<job>\tUNKNOWN STEP\t2026-..Z "
    clean = re.sub(r'^[^\t]+\tUNKNOWN STEP\t\S+ ', '', line.rstrip())
    print(clean)
EOF

# Alternative: cut on tab delimiter (file-based, not piped from gh)
cut -f3- "$LOG" | sed 's/^[0-9T:Z.-]* //'

# Search for specific pattern after stripping prefix
python3 -c "
import re, sys
for line in open(sys.argv[1]):
    clean = re.sub(r'^[^\t]+\tUNKNOWN STEP\t\S+ ', '', line.rstrip())
    if re.search(r'error|FAILED|fatal', clean, re.I):
        print(clean)
" "$LOG" | head -40
```

### Download full logs for deep analysis

```bash
# Unique temp dir — prevents collisions between parallel sessions
LOGDIR=$(mktemp -d /tmp/gh-logs-XXXXXX)
gh run download <run-id> --repo <owner>/<repo> -D "$LOGDIR"

# After download, search freely
grep -rn "error\|FAILED\|fatal\|Exit code" "$LOGDIR/" | head -40

# Re-run failed jobs after fix
gh run rerun <run-id> --failed
```

## Debugging Checklist

Work through sequentially. Stop when root cause is identified.

1. **Identify failure scope** — Which job/step failed? What trigger (push, PR, schedule, fork PR)? Runner type? Matrix build?
2. **Read logs** — Fetch with `gh run view --log-failed`. Find first error, not last. Check timestamps for timeouts vs. instant failures.
3. **Read workflow file** — Open `.github/workflows/*.yml`. Verify step ordering, conditional expressions, env vars, secret references.
4. **Classify error** — Match against Quick Reference below. Check if flaky (re-run history) or deterministic.
5. **Fix and verify** — Apply fix, push, confirm CI passes. If flaky, add retry logic or fix race condition.

## Project-Specific Failures (engineering-score-cards)

Check these first — most common in this codebase.

| Check Name | Root Cause | Fix |
|---|---|---|
| **Contrast Validation / Audit Text Contrast** | `npm run audit:contrast` found Tailwind classes failing WCAG (e.g., `text-gray-400` on white) | Check `STYLEGUIDE.md` for approved colors. Replace forbidden classes. |
| **Push / Code Formatting Check** | `./gradlew spotlessCheck` found unformatted Java/Kotlin | Run `./gradlew spotlessApply` locally, commit the result. |
| **E2E Tests - Compliance Dashboard** | Playwright tests in Docker Compose timeout or container unhealthy | Run `make up` locally, check `docker compose ps` — all containers healthy? Check Docker resource limits, review Playwright trace artifacts. |
| **Frontend build failure** | TypeScript errors or missing types after API changes | Run `./gradlew generateOpenApiSpec` then `npm run generate:types:static` in `scorecards-ui/`. |

## General Error Quick Reference

| Error Pattern | Category | Fix |
|---|---|---|
| `Process completed with exit code 1` | Generic step failure | Read preceding log lines for actual error |
| `Resource not accessible by integration` | Permissions | Add `permissions:` block (e.g., `contents: read`, `pull-requests: write`) |
| `Unable to resolve action` | Action reference | Check version tag exists; pin to SHA for reliability |
| `No space left on device` | Disk | Add cleanup step or `rm -rf` before heavy build steps |
| `The job was canceled` | Timeout | Increase `timeout-minutes` or optimize slow steps |
| `Context access might be invalid` | Expression syntax | Check `${{ }}` expressions; quote strings, use `fromJSON()` for complex types |
| `HttpError: rate limit exceeded` | API throttling | Add `GITHUB_TOKEN`, use `actions/cache`, reduce API calls |
| `Dependencies lock file is not found` | Missing lockfile | Commit `package-lock.json` / `gradle.lockfile`; check `working-directory` |
| `ECONNREFUSED` / `Connection refused` | Service container | Verify `services:` health checks; use `localhost` not `127.0.0.1` |
| `denied: permission` (Docker) | Registry auth | Add `docker/login-action` step before push |
| `npm ERR! code ERESOLVE` | Peer dependency conflict | Add `--legacy-peer-deps` or resolve conflicting versions |
| `exit code 137` / `Killed` | OOM | Increase `--max-old-space-size` or use larger runner |

## Workflow Patterns to Check

```yaml
# Correct permissions block
permissions:
  contents: read
  checks: write

# Skip on fork PRs (they lack secrets)
if: github.event.pull_request.head.repo.full_name == github.repository

# Service health check (wait for DB)
services:
  postgres:
    image: postgres:15
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

## Key Principles

- **First error wins** — scroll up past cascading failures to find the root error
- **Compare with last green run** — `gh run list --status success --limit 1`, diff workflow/code changes
- **Fork PRs lack secrets** — failure only on fork PRs? Check `secrets.*` access
- **Self-hosted runner drift** — check runner tool versions match workflow expectations

---

*For extended error pattern catalog, see `error-patterns.md`. For large log files (>500 lines), use `scripts/parse_workflow_logs.py`.*
