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
    After fixing: `git push origin HEAD` and restart the loop.

  ### Gate 2 — Review Comments

  ```bash
  REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
  gh api repos/$REPO/pulls/$PR/comments --paginate \
    | jq '.[] | {id, user: .user.login, path, line, body: .body[:300], resolved: .in_reply_to_id}'
  gh pr view "$PR" --json reviews --jq '.reviews[] | {state, author: .author.login, body: .body[:200]}'
  ```

  For each unresolved comment:
  - **Fix** if it identifies a real bug, null-safety issue, logic error, data integrity problem, or security issue → implement the fix
  - **Decline** if it is a style preference, premature optimization, or out-of-scope suggestion → reply with rationale:
    ```bash
    gh api repos/$REPO/pulls/$PR/comments \
      -X POST -f body="<rationale>" -f in_reply_to=<COMMENT_ID>
    ```
  - **CHANGES_REQUESTED reviews**: treat every item as blocking; address each one
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
