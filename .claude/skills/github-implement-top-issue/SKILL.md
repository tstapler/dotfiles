---
name: github-implement-top-issue
description: Use when asked to find and implement the highest-priority GitHub issue for the current project — e.g. "work the top issue", "pick up the next issue", "implement the most important open issue". Detects the repo from the current directory, ranks open issues, implements the winner, opens a draft PR, and drives it to mergeable via github:pr-ship.
---

# Implement the top GitHub issue

1. **Resolve the repo** from the current directory: `gh repo view --json nameWithOwner --jq .nameWithOwner`. If that fails (not a GitHub repo, no `gh` auth), stop and say so.

2. **Rank open issues** with this one-liner (adjust `--limit` if the repo has more than 100 open issues). It excludes already-assigned issues and `blocked`/`wontfix`/`duplicate`/`invalid`, then sorts by priority label → comment count → age (oldest first):

   ```bash
   gh issue list --state open --limit 100 \
     --json number,title,body,labels,assignees,comments,createdAt,url \
     --jq '
       map(select(
         (.assignees | length) == 0
         and (([.labels[].name] | any(test("blocked|wontfix|duplicate|invalid";"i"))) | not)
       ))
       | map(. + {
           prio: (
             if   ([.labels[].name] | any(test("P0|priority:\\s*critical";"i"))) then 0
             elif ([.labels[].name] | any(test("P1|priority:\\s*high";"i")))     then 1
             elif ([.labels[].name] | any(test("P2|priority:\\s*medium";"i")))   then 2
             elif ([.labels[].name] | any(test("P3|priority:\\s*low";"i")))      then 3
             else 4 end
           ),
           commentCount: (.comments | length)
         })
       | sort_by([.prio, -.commentCount, .createdAt])
     '
   ```

   This repo has no priority labels, so everything falls into bucket 4 and ties break on
   comments/age — that's expected, not a bug in the query.

   If the array is empty, tell the user there's nothing eligible (all issues are assigned or
   filtered out) and stop.

3. **Check the top-ranked candidate for a stale close** before announcing it — some repos have
   issues that were already fixed by a merged PR but never got closed (e.g. an issue filed by an
   automated agent, or `Closes #n` omitted from the fixing PR). For the top candidate:

   - `git log --oneline --all | grep -i "<keyword from the issue title>"` to look for a merged
     commit/PR touching the same area.
   - If a plausible match turns up, open that PR (`gh pr view <n> --json title,body,mergedAt,state`)
     and do one quick read of the current relevant source to confirm the fix is actually present
     in the code today (not just claimed in the PR body — code can regress after merge).
   - If confirmed already fixed: close the issue with a comment citing the PR and what you
     verified, then drop to the next-ranked candidate and repeat this check on it. Keep going
     until you land on a candidate that is genuinely still open, or you run out of candidates
     (in which case tell the user the queue is empty of real work and stop).
   - If nothing turns up in a quick search, or the match is ambiguous, treat the candidate as
     open and proceed — this check is a cheap grep-and-read, not a deep investigation. Don't
     spend more than a couple of minutes per candidate on it.

4. **Announce the pick** in one line: issue number, title, and why (matched a priority label,
   or "no priority labels — oldest/most-discussed open issue"). Mention any candidates skipped
   as already-fixed in step 3.

5. **Read the issue** (`gh issue view <n> --json title,body,comments`) and implement it following
   this repo's own conventions (CLAUDE.md, existing tests/lint) — state the root-cause hypothesis
   before changing code, don't invent scope beyond what the issue asks for.

6. **Verify**: run the repo's tests/build/lint before claiming done.

7. **Open a draft PR** (`gh pr create --draft`) with `Closes #<n>` in the body, following this
   repo's normal commit/PR conventions.

8. **Ship it**: invoke the `github:pr-ship` skill on the PR you just opened and let it iterate
   (local CI, code review, remote CI, review comments, merge conflicts) until the PR is
   mergeable. Opening the draft PR is not the finish line — do not report the task done, hand
   back to the user, or stop until `github:pr-ship` reports the PR is ready to merge (or reports
   a blocker only the user can resolve, e.g. a design question or missing credential). If
   `github:pr-ship` surfaces such a blocker, report it plainly and say what's needed — don't
   silently give up and call it done.

Skip steps 5-8 and just report the ranked list if the user only asked which issue is next, not
to implement it. Still run the step-3 stale-close check in this mode, and report any candidates
you closed as already-fixed alongside the list.
