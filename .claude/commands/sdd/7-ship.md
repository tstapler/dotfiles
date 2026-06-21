---
description: "Phase 7 — Create the PR and drive it to merge-ready via github:pr-ship."
user-invocable: true
---

# sdd:7-ship

Create the PR and iterate it to a merge-ready state using the `github:pr-ship` loop.

## HARD GATE

Only run this after `/sdd:6-verify` has produced a ✅ PASS verdict. If you skipped verification, run it now.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Present ship options** using `AskUserQuestion`:
   ```
   header: "Ship method"
   question: "How would you like to proceed?"
   options:
     - label: "Open a PR and drive to merge-ready (recommended)"
       description: "Create a GitHub PR, then run github:pr-ship to handle compile, tests, code review, CI, and merge conflicts automatically"
     - label: "Open a PR only — no automation"
       description: "Create the PR with a description, but stop there"
     - label: "Keep branch for more work"
       description: "Leave the branch as-is — no PR yet"
     - label: "Discard changes"
       description: "Reset — abandon this branch"
   ```

3. **For option A or B**: draft the PR description:

   ```markdown
   ## Summary
   [2-3 sentences: what this PR does and why it matters]

   ## Context
   [Problem solved, motivation, issue/ticket link if in requirements.md]

   ## Changes
   - **<Component A>**: <specific changes>
   - **<Component B>**: <specific changes>
   - **Tests**: <unit/integration/UX acceptance tests added>

   ## Impact
   - **Scope**: <what parts of the system are affected>
   - **Breaking Changes**: <none, or list explicitly>
   - **Performance**: <improvements, regressions, or neutral>
   - **Dependencies**: <new or updated>

   ## Reviewer Notes
   - **Focus areas**: <risky areas, design decisions>
   - **Known limitations**: <intentional trade-offs>
   - **Follow-up tasks**: <deferred work>
   - **Rollback procedure**: <specific revert steps, or "standard revert PR — no special steps">
   - **Feature flag**: <flag name and how to disable, or "not gated">
   - **Feature flag cleanup**: <if gated — "[ ] File follow-up ticket to remove flag `<flag-name>` after N sprints of stable rollout", or "N/A — not gated">

   ## UX Preview
   *(Include only for user-facing features. Attach or inline the golden-path recording.)*
   - Golden path: `project_plans/<PROJECT_NAME>/design/golden-path.gif`

   ## Related
   - Closes <issue> (if linked in requirements.md)
   ```

4. **Create the PR** using `gh pr create` with a body file:
   ```bash
   cat > /tmp/pr-description.md <<'EOF'
   <PR description>
   EOF
   gh pr create --title "<type>(<scope>): <description>" --body-file /tmp/pr-description.md
   ```

   Capture the PR number from the output URL (`gh pr view --json number --jq '.number'`).

5. **For option A only — invoke `github:pr-ship <PR_NUMBER>`.**

   This drives the PR through five ordered gates until all are green:
   - Gate 1a: Local compile
   - Gate 1b: Local tests (changed packages only)
   - Gate 2: Code review with fixes
   - Gate 3: PR review comments addressed
   - Gate 4: Remote CI green (polls with ScheduleWakeup)
   - Gate 5: No merge conflicts

   The PR is NOT merged automatically — `github:pr-ship` stops when all gates are `[x]` and reports the merge command for the user to run.

6. **Clean up worktree** (if this feature was developed in a git worktree):
   ```bash
   git worktree remove <path> --force
   ```
   Ask for confirmation before removing. Do not remove if the PR is not yet merged.

7. **Run `/knowledge:extract-learnings`** to capture project-specific instincts before the session ends.

   Specifically prompt it to capture:
   - Whether the build-vs-buy decision matched the Phase 2 recommendation in practice
   - Any pitfalls discovered during implementation that weren't in `research/pitfalls.md`
   - Architecture decisions made during implementation that deviated from `plan.md` and why
   - Any UX acceptance criteria that turned out to be wrong or missing once the feature was real
