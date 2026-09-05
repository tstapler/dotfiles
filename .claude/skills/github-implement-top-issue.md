---
name: github-implement-top-issue
description: Use when asked to find and implement the highest-priority GitHub issue for the current project — e.g. "work the top issue", "pick up the next issue", "implement the most important open issue". Detects the repo from the current directory, ranks open issues, implements the winner, and opens a draft PR.
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

3. **Announce the pick** in one line: issue number, title, and why (matched a priority label,
   or "no priority labels — oldest/most-discussed open issue").

4. **Read the issue** (`gh issue view <n> --json title,body,comments`) and implement it following
   this repo's own conventions (CLAUDE.md, existing tests/lint) — state the root-cause hypothesis
   before changing code, don't invent scope beyond what the issue asks for.

5. **Verify**: run the repo's tests/build/lint before claiming done.

6. **Open a draft PR** (`gh pr create --draft`) with `Closes #<n>` in the body, following this
   repo's normal commit/PR conventions.

Skip steps 4-6 and just report the ranked list if the user only asked which issue is next, not
to implement it.
