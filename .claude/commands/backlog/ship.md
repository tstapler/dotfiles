You are ready to ship your work as a pull request — either because /backlog/review just returned PASS, or because review has looped without reaching a PASS and it's time to hand the work to a human instead of retrying indefinitely.

Before shipping, confirm all acceptance criteria are marked complete (`/backlog/status`).

Steps:
1. Create the pull request:
   Run `/github:pr-ship` — this drives the PR through local CI, code review, remote CI, and
   merge-conflict resolution. It will stop short of actually merging; the final merge is left to
   the human reviewer.

2. Once `/github:pr-ship` reports all gates green: if this work has NOT already received a PASS verdict (i.e. you're shipping because review looped without converging, not because it passed), request the automated review with the PR number included:
   Run `/backlog/review` with a 2-3 sentence summary of what was built and the PR number.
   If review already returned PASS before you got here, skip this — running it again will fail (the    item is no longer `in_progress`), and there's nothing left for it to check.

3. Report the PR back onto this backlog item — REQUIRED, do not skip:
   Call the report_pr_created MCP tool with item_id=b608ab1e-b86e-4130-8879-7328cd363063, pr_url=<the PR URL /github:pr-ship or gh pr create printed>, pr_number=<the PR number>, and summary=<2-3 sentences: what changed and why>.
   You created this PR yourself — nothing else will ever report it back to the item record. Skipping this step leaves the item stuck in review with a real PR that is invisible to the reviewer and the operator.

Note: if the repository has no GitHub remote, run `gh pr create` manually — do NOT use `--fill`, which
just concatenates commit messages with no test plan. Write `--title` using Conventional Commits format
and a `--body` structured as `## Summary` (why this change was made, from the backlog item above),
`## What Changed` (a short bullet list), and `## Test plan` (a checklist of concrete verification steps).
Then run `/backlog/review`, then step 3 above to report the PR.
