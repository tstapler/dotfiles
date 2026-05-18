---
description: Autonomously iterate on a PR — fix CI failures, address review comments, resolve merge conflicts — until it is ready to merge
disable-model-invocation: true
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

  ## Context discipline — delegate work, don't accumulate it

  **This skill is an orchestrator, not a worker.** Each fix cycle spawns a fresh subagent so this
  context stays small and fast. Never do the actual code editing inline — always delegate via the
  Agent tool. Collect the failure/comment details first, then hand them off.

  ```
  Orchestrator (this context)
    └─ reads gates, collects info, decides what to fix
       └─ spawns Agent(prompt="Fix these specific failures: ...") → waits for result
          └─ fresh agent does all the file reading, editing, compiling, committing
  ```

  After each Agent call returns, check gates again. Do not accumulate file contents or diffs in
  this context — the subagent handles that entirely.

  ---

  ## The Loop

  Repeat the following cycle until **all three gates pass**:

  ### Gate 1 — CI Checks

  ```bash
  gh pr checks "$PR" --watch=false
  ```

  - If any check is **pending/in_progress**: use `ScheduleWakeup` (`delaySeconds: 90–600`) and stop.
  - If any check is **failing**: collect the raw log, then **delegate to a fresh agent**:
    ```bash
    gh run list --branch $(git branch --show-current) --json databaseId,name,status,conclusion \
      --jq '.[] | select(.conclusion == "failure") | .databaseId'
    gh run view <RUN_ID> --log-failed   # copy the relevant error output
    ```
    Spawn an Agent with a self-contained prompt that includes:
    - The repo path and current branch
    - The exact error lines from the log
    - What local validation to run before pushing (see table below)
    - Instruction to commit and push when fixed

    **Local validation table** (include in every Gate-1 agent prompt):
    | Stack | Compile check | Full test |
    |-------|--------------|-----------|
    | Java/Maven | `./mvnw compile -q` | `./mvnw test -q` |
    | Kotlin/KMP | `./gradlew compileTestKotlinJvm --no-daemon` | `./gradlew jvmTest --no-daemon` |
    | Go | `go build ./...` | `go test ./...` |
    | TypeScript | `npx tsc --noEmit` | `npm test` |
    | JS/lint | `npm run lint -- --fix` | `npm test` |

    After the agent returns: restart the loop (check gates again).

  ### Gate 2 — Review Comments

  Use the `github-address-pr-comments` skill (`~/.claude/skills/github-address-pr-comments/SKILL.md`) to systematically address all unresolved threads:
  1. Fetch all unresolved threads via GraphQL (single call)
  2. For each thread: decide fix/decline/defer, implement the fix, reply with the outcome, resolve via GraphQL mutation
  3. **CHANGES_REQUESTED reviews**: treat every item as blocking; address each one

  Group the comments, then **delegate to a fresh agent** (or multiple in parallel for independent
  files). Each agent prompt must be self-contained: include the file path, line, comment text, and
  what to do. Decision rules to encode in the prompt:
  - **Fix** bugs, logic errors, security concerns, clarity issues, naming, missing tests, valid perf issues.
  - **Also fix** cosmetic/style suggestions if small and clearly correct.
  - **Defer** valid-but-large refactors: reply "Deferring to follow-up — too broad for this PR."
  - **Decline** only if factually wrong or contradicts a documented design decision.
  - **CHANGES_REQUESTED**: treat every item as blocking.

  After the agent(s) return: commit + push (the agents should do this), then restart the loop.

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

**Usage**: `/github:pr-ship` (current branch) or `/github:pr-ship 61`

Gate 2 delegates to the `github-address-pr-comments` skill for systematic thread resolution.
