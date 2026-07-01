---
description: Autonomously iterate on a PR — local CI, code review, remote CI, review comments, merge conflicts — until ready to merge
prompt: |
  # PR Ship Loop — Make It Ready to Merge

  Drive PR `${1:-$(gh pr list --head $(git branch --show-current) --json number --jq '.[0].number')}` to a mergeable state by iterating through five ordered gates until all are green.

  ## State File

  All progress is tracked in `/tmp/pr-ship-${REPO_SLUG}-${BRANCH_SLUG}-${PR}.md`. Read it at the start of every iteration to understand what's already done. Update it after every action. This is your working memory across ScheduleWakeup wakeups.

  **State file format** (initialize if missing):
  ```markdown
  # PR Ship State — PR #N
  Iteration: 0
  Branch: <branch>
  Base: <base-branch>

  ## Changed Files
  (populated once from `gh pr diff "$PR" --name-only`)
  - path/to/file.go

  ## Gate Status
  - [ ] Gate 1a: Local compile
  - [ ] Gate 1b: Local tests (changed packages only)
  - [ ] Gate 2:  Code review clean
  - [ ] Gate 3:  PR review comments addressed
  - [ ] Gate 4:  Remote CI green
  - [ ] Gate 5:  No merge conflicts

  ## Push History
  (append after each push: `- COMMIT_SHA pushed at ITERATION N`)

  ## Code Review Issues
  ### Open
  (populated after Gate 2 runs; format: `- [ ] FILE:LINE — DESCRIPTION [severity]`)

  ### Resolved
  (moved here when fixed; format: `- [x] FILE:LINE — DESCRIPTION [fixed in COMMIT]`)

  ## Decision Log
  (one line per iteration: what gate advanced, what was done, commits made)
  ```

  ## Entry Check

  ```bash
  PR="${1:-$(gh pr list --head $(git branch --show-current) --json number --jq '.[0].number')}"
  REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' | tr '/' '-')
  BRANCH=$(gh pr view "$PR" --json headRefName --jq '.headRefName' | tr '/' '-' | tr '_' '-' | cut -c1-40)
  STATE="/tmp/pr-ship-${REPO}-${BRANCH}-${PR}.md"
  gh pr view "$PR" --json number,title,state,mergeable,mergeStateStatus,headRefName,baseRefName
  ```

  If the PR is already merged or closed, report that and stop.

  Read the state file. If it doesn't exist, initialize it. Populate **Changed Files** once using:
  ```bash
  gh pr diff "$PR" --name-only
  ```
  Never re-derive the changed files list from scratch — use what's in the state file.

  ---

  ## Context Discipline — Orchestrator Only

  **This skill is an orchestrator, not a worker.** Delegate all file editing, compiling, and committing to fresh subagents. Never accumulate file contents or diffs in this context — only gate status and state file updates. This is the `lean-agent-loop` skill pattern: the state file is the coordinator's memory, each fresh subagent is a Ralph Wiggum agent, and the five gates are the loop condition.

  ```
  Orchestrator (this context)
    └─ reads state file, checks gate, collects failure details
       └─ spawns Agent(prompt="Fix these specific failures: ...") → waits for result
          └─ fresh agent does all file reading, editing, testing, committing, pushing
  ```

  After each agent returns: verify the fix locally (run the relevant check command), update the state file, append to Decision Log, then advance to the next gate.

  ---

  ## The Loop (max 10 iterations; stop if no gate advances)

  At the top of each iteration, increment `Iteration:` in the state file. Read Gate Status. Skip gates already marked `[x]`. Process gates in order — do not jump ahead.

  ### Gate 1a — Local Compile

  Only run if `[ ]`. Detect stack from repo contents, then compile:

  | Stack | Compile check |
  |-------|--------------|
  | Java/Maven | `./mvnw compile -q` |
  | Kotlin/KMP | `./gradlew compileTestKotlinJvm --no-daemon` |
  | Go | `go build ./...` |
  | TypeScript | `npx tsc --noEmit` |
  | JS | `npm run build` |

  If it fails: delegate to a fresh agent with the exact error and the repo path. After agent returns, re-run the same compile command to verify — do not mark `[x]` until you confirm it passes. Update state file.

  ### Gate 1b — Local Tests (changed packages only)

  Only run if `[ ]` and Gate 1a is `[x]`. Scope tests to only the packages/modules containing changed files:

  | Stack | Scoped test command |
  |-------|-------------------|
  | Go | `go test $(git diff --name-only origin/<base>...HEAD \| grep '\.go$' \| xargs -I{} dirname {} \| sort -u \| sed 's|^|./|' \| tr '\n' ' ')` |
  | Java/Maven | `./mvnw test -pl $(changed modules) -q` |
  | TypeScript | `npm test -- --testPathPattern="<changed files>"` |
  | Kotlin/KMP | `./gradlew jvmTest --no-daemon` |

  If a scoped command is too complex to derive, fall back to the full test suite. If it fails: delegate to a fresh agent with failing test output. After agent returns, re-run the failing tests to verify — not the full suite, just the specific failing ones. Mark `[x]` only after the re-run passes.

  ### Gate 2 — Code Review (changed files only)

  Only run if `[ ]` and Gates 1a+1b are `[x]`.

  Invoke the code review skill on the current diff (it naturally scopes to changed files):
  ```
  /code:review --fix
  ```

  Parse the findings. Write all **BLOCKER** and **CRITICAL** issues to `## Code Review Issues → Open` in the state file. Write **MAJOR** issues too. Suggestions/NITs are optional — log them but don't block.

  Delegate a fresh agent to fix all BLOCKER/CRITICAL/MAJOR issues. Include in the agent prompt:
  - The state file path
  - Each open issue with file, line, severity, description
  - Instruction to commit (but NOT push — Gate 3 handles the push decision)

  After the agent returns:
  1. Re-run `/code:review` to verify no new BLOCKER/CRITICAL issues
  2. Move fixed issues to `Resolved` in the state file with the commit SHA
  3. Repeat until no BLOCKER/CRITICAL/MAJOR issues remain
  4. Mark `[x]` in state file

  ### Gate 3 — PR Review Comments

  Only run if `[ ]` and Gates 1a+1b+2 are `[x]`. Address all reviewer feedback **before** pushing so CI runs on code reviewers have already seen and haven't flagged.

  #### Copilot Review Check (run first)

  Before processing any threads, check whether Copilot was requested as a reviewer:

  ```bash
  REPO_NWO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
  OWNER="${REPO_NWO%%/*}"; REPO_NAME="${REPO_NWO##*/}"

  # Is Copilot a requested reviewer?
  COPILOT_REQUESTED=$(gh pr view "$PR" --json reviewRequests \
    --jq '[.reviewRequests[] | (.login // .name // "")] | map(select(test("copilot";"i"))) | length > 0')
  ```

  If `COPILOT_REQUESTED == true`:

  ```bash
  # Has Copilot already posted a review?
  COPILOT_REVIEWED=$(gh pr view "$PR" --json reviews \
    --jq '[.reviews[] | select(.author.login | test("copilot";"i"))] | length > 0')

  # Has Copilot posted a rate-limit / skip comment?
  COPILOT_RATE_LIMITED=$(gh api "repos/$OWNER/$REPO_NAME/issues/$PR/comments" \
    --jq '[.[] | select(.user.login | test("copilot";"i")) | .body] | map(select(test("rate.limit|quota|unavailable|temporarily|skip|unable|error";"i"))) | length > 0')
  ```

  Decision:
  - **`COPILOT_REVIEWED == true`** → include Copilot's review comments in Gate 3 processing below (treat like any other reviewer).
  - **`COPILOT_REVIEWED == false` + `COPILOT_RATE_LIMITED == true`** → log "Copilot rate-limited — skipping Copilot review" in Decision Log and proceed to thread processing.
  - **`COPILOT_REVIEWED == false` + `COPILOT_RATE_LIMITED == false`** → Copilot review is still pending. Use `ScheduleWakeup` with `delaySeconds: 90` and stop. Do **not** advance Gate 3. Log "Waiting for Copilot review" in Decision Log.

  #### Thread Processing

  Use the `github-address-pr-comments` skill (`~/.claude/skills/github-address-pr-comments/SKILL.md`) to:
  1. Fetch all unresolved threads (single GraphQL call)
  2. For each thread: fix/decline/defer per decision rules below
  3. Reply + resolve each thread
  4. Commit any code changes locally (do NOT push yet — push happens in Gate 4)

  Decision rules (encode in every delegated agent prompt):
  - **Fix**: bugs, logic errors, security, clarity, naming, missing tests, valid perf issues
  - **Also fix**: cosmetic/style if small and clearly correct
  - **Defer**: valid-but-large refactors — reply "Deferring to follow-up — too broad for this PR"
  - **Decline**: only if factually wrong or contradicts a documented design decision
  - **CHANGES_REQUESTED**: treat every item as blocking

  Mark `[x]` when all threads are resolved or explicitly declined with a reply.

  ### Gate 4 — Remote CI

  Only run if `[ ]` and Gates 1a+1b+2+3 are `[x]`. Push all local commits now:
  ```bash
  git push origin HEAD
  # append to Push History in state file: "- <sha> pushed at iteration N"
  ```

  Then check:
  ```bash
  gh pr checks "$PR" --watch=false
  ```

  - **Pending/in_progress**: use `ScheduleWakeup` (see Pacing section) and stop. Do not mark gate.
  - **All success**: check for any new PR review comments added since the push (re-run Gate 3 check). If new unresolved threads exist, reset Gate 3 to `[ ]` and loop. Otherwise mark Gate 4 `[x]`.
  - **Failing**: collect the logs:
    ```bash
    gh run list --branch $(git branch --show-current) \
      --json databaseId,name,status,conclusion \
      --jq '.[] | select(.conclusion == "failure") | .databaseId'
    gh run view <RUN_ID> --log-failed
    ```
    Delegate to a fresh agent with the exact error lines. Agent commits locally. Then re-run Gate 3 (address any new comments), then push again and set a ScheduleWakeup.

  ### Gate 5 — Merge Conflicts

  Only run if `[ ]` and Gate 4 is `[x]`.

  ```bash
  gh pr view "$PR" --json mergeable,mergeStateStatus
  ```

  If `mergeable == "CONFLICTING"`: delegate to a fresh agent to fetch + merge base, resolve conflicts, commit, and push. Mark `[x]` when `mergeable == "MERGEABLE"`.

  ---

  ## Progress Check

  After each gate transitions `[ ]` → `[x]`, append to Decision Log:
  ```
  Iteration N — Gate X: <what was done, commits made, issues found/fixed count>
  ```

  If an entire iteration completes with **zero gates newly marked `[x]`** (no progress), stop and report:
  - Which gates are still open
  - What was attempted
  - What's blocking (with exact error or status)

  ---

  ## Exit Condition

  When all five gates are `[x]`, report:

  ```markdown
  ## PR #N is Ready to Merge

  - Gate 1a Local compile: green
  - Gate 1b Local tests: green
  - Gate 2  Code review: N issues fixed, N deferred, N declined
  - Gate 3  PR review comments: N threads resolved
  - Gate 4  Remote CI: all checks green
  - Gate 5  Merge conflicts: none

  Decision log:
  <paste from state file>

  Merge with: gh pr merge N --squash --delete-branch
  ```

  Do NOT merge automatically — leave the final merge to the user.

  ---

  ## Pacing with ScheduleWakeup

  When Remote CI checks are still running:
  - Pending < 2 min → `delaySeconds: 90`
  - Pending 2–10 min → `delaySeconds: 270`
  - Pending > 10 min → `delaySeconds: 600`

  Always pass `prompt: "/github:pr-ship <PR_NUMBER>"` so the loop re-enters and reads the state file (the repo/branch slug is re-derived from the live PR on each entry).

  ---

  ## Never

  - Push code before Gates 1a and 1b are `[x]`
  - Push code before Gate 2 (code review) is `[x]`
  - Push code before Gate 3 (PR comments) is `[x]` — reviewers' feedback must be addressed first
  - Force-push over others' commits without asking
  - Merge the PR automatically
  - Skip `--no-verify` or bypass hooks
  - Re-derive changed files — always use the state file's list
---

**Usage**: `/github:pr-ship` (current branch) or `/github:pr-ship 61`

Gates run in order: local compile → local tests (scoped) → code review → **PR comments** → remote CI → merge conflicts. Push only happens at Gate 4, after all local work and reviewer feedback is incorporated. After CI passes, re-check for new comments before marking done. State tracked in `/tmp/pr-ship-{repo}-{branch}-{PR}.md`.
