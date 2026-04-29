---
description: Autonomously iterate on a PR — fix CI failures, address review comments, resolve merge conflicts — until it is ready to merge
prompt: |
  # PR Ship Loop — Make It Ready to Merge

  Drive PR `${1:-$(gh pr list --head $(git branch --show-current) --json number --jq '.[0].number')}` to a mergeable state by iterating through CI failures, review comments, and merge conflicts until every gate is green.

  ## Entry Check

  ```bash
  PR="${1:-$(gh pr list --head $(git branch --show-current) --json number --jq '.[0].number')}"
  gh pr view "$PR" --json number,title,state,mergeable,mergeStateStatus
  ```

  If the PR is already merged or closed, report that and stop.

  ---

  ## The Loop

  Repeat the following cycle until **all three gates pass**:

  ### Gate 1 — CI Checks

  ```bash
  gh pr checks "$PR" --watch=false
  ```

  - If any check is **pending/in_progress**: wait 60s (use `ScheduleWakeup` with `delaySeconds: 90` and re-run this skill with the same PR arg) and stop this iteration.
  - If any check is **failing**: download logs and fix.
    ```bash
    # Get the run ID for the failing check
    gh run list --branch $(git branch --show-current) --json databaseId,name,status,conclusion --jq '.[] | select(.conclusion == "failure") | .databaseId'
    # Download failed logs
    gh run view <RUN_ID> --log-failed
    ```
    Common fixes by failure type:
    - **TypeScript errors**: read the file, fix the type, commit
    - **Jest/test failures**: read the test output, fix or update the test, commit
    - **ESLint / lint**: `cd web-app && npm run lint -- --fix` or fix manually, commit
    - **Build errors**: read error, fix source, commit
    - **Go test failures**: `go test ./...` locally, diagnose, fix, commit
    - **Go lint**: `make lint`, fix, commit
    - **Kotlin/KMP compile errors**: fix imports/types, then validate with `./gradlew compileTestKotlinJvm` before pushing
    - **Kotlin/KMP test failures**: fix the test, then validate with `./gradlew jvmTest` before pushing

    **Local validation before push** — always run the cheapest local check that covers the fix:
    | Stack | Compile check | Full test |
    |-------|--------------|-----------|
    | Kotlin/KMP | `./gradlew compileTestKotlinJvm --no-daemon` | `./gradlew jvmTest --no-daemon` |
    | Go | `go build ./...` | `go test ./...` |
    | TypeScript | `npx tsc --noEmit` | `npm test` |
    | JS/lint | `npm run lint -- --fix` | `npm test` |

    Only push if the local check passes. This prevents burning multiple CI rounds on incremental fixes.
    After validating locally: `git push origin HEAD` and restart the loop.

  ### Gate 2 — Review Comments

  ```bash
  REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
  gh api repos/$REPO/pulls/$PR/comments --paginate \
    | jq '.[] | {id, user: .user.login, path, line, body: .body[:300], resolved: .in_reply_to_id}'
  gh pr view "$PR" --json reviews --jq '.reviews[] | {state, author: .author.login, body: .body[:200]}'
  ```

  For each unresolved comment:
  - **Default: Fix it.** If a suggestion is reasonable and can be done correctly within this PR's scope, implement it — even if it adds a little extra work. Doing it right beats a follow-up PR.
  - **Fix** if it identifies: a bug, logic error, null-safety issue, data integrity problem, security concern, clarity improvement, naming inconsistency, missing test case, or valid performance issue.
  - **Also fix** style preferences and "minor" suggestions if the fix is small and clearly correct — don't decline just because it's cosmetic.
  - **Defer** (not decline) if the suggestion is valid but requires a larger refactor that would be risky to do here — reply "Good catch. This needs a broader fix — deferring to a follow-up to keep this PR focused."
  - **Decline** only if: the suggestion is factually wrong, contradicts an explicit design decision with a documented reason, or the reviewer misunderstood the intent. Always include specific reasoning, never just "won't fix".
  - **CHANGES_REQUESTED reviews**: treat every item as blocking; address each one
  After addressing comments: commit fixes and `git push origin HEAD`.
  After addressing comments: commit fixes and `git push origin HEAD`.

  ### Gate 3 — Merge Conflicts

  ```bash
  gh pr view "$PR" --json mergeable,mergeStateStatus
  ```

  If `mergeable == "CONFLICTING"`:
  ```bash
  git fetch origin main
  git merge origin/main
  # Resolve conflicts: read conflicting files, keep the right changes
  git add <resolved-files>
  git commit -m "chore: resolve merge conflicts with main"
  git push origin HEAD
  ```

  ---

  ## Exit Condition

  After a full pass where:
  - All CI checks are **success** ✅
  - No unresolved review comments remain (or all declines replied to) ✅
  - `mergeable == "MERGEABLE"` ✅
  - No `CHANGES_REQUESTED` review state ✅

  Report:

  ```markdown
  ## PR #<N> is Ready to Merge

  - CI: all checks green
  - Reviews: <APPROVED / REVIEW_REQUIRED with no blockers>
  - Merge conflicts: none
  - Fixes applied: <summary of what was changed>

  Merge with: gh pr merge <N> --squash --delete-branch
  ```

  Do NOT merge automatically — leave the final merge to the user.

  ---

  ## Pacing with ScheduleWakeup

  When CI checks are still running, use `ScheduleWakeup` to resume:
  - Checks pending < 2 min → `delaySeconds: 90`
  - Checks pending 2–10 min → `delaySeconds: 270`
  - Checks pending > 10 min → `delaySeconds: 600`

  Always pass `prompt: "/github:pr-ship <PR_NUMBER>"` so the loop re-enters correctly.

  ---

  ## Never

  - Force-push over others' commits without asking
  - Merge the PR automatically
  - Skip `--no-verify` or bypass hooks
  - Close review threads manually (push fixes; GitHub auto-resolves)
---

# PR Ship Loop — Make It Ready to Merge

Autonomously drives PR `$1` (or the current branch's open PR) to a mergeable state by iterating through CI failures, review comments, and merge conflicts until every gate is green. Leaves the final merge to you.

**Usage**: `/github:pr-ship` (current branch) or `/github:pr-ship 22`
