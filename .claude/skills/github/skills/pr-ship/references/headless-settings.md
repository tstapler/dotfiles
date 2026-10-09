# Headless settings for pr-ship

Template for running `github:pr-ship` unattended (`claude -p`). Save as a per-run
`settings.json` and pass it with `claude -p --settings ./pr-ship-settings.json ...`.
Deny rules win over allow rules, so keep both lists.

```json
{
  "permissions": {
    "allow": [
      "Read", "Grep", "Glob", "Edit", "Write", "Agent",
      "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git fetch:*)",
      "Bash(git add:*)", "Bash(git commit:*)", "Bash(git push origin HEAD)",
      "Bash(gh pr view:*)", "Bash(gh pr diff:*)", "Bash(gh pr checks:*)", "Bash(gh pr list:*)",
      "Bash(gh run list:*)", "Bash(gh run view:*)", "Bash(gh repo view:*)",
      "Bash(gh api repos/*/*/pulls/*/comments:*)",
      "Bash(gh api repos/*/*/pulls/*/reviews:*)",
      "Bash(gh api repos/*/*/issues/*/comments:*)",
      "Bash(python3 ~/.claude/scripts/pr-threads.py:*)"
    ],
    "deny": [
      "Bash(git push *--force*)", "Bash(git push * -f*)", "Bash(git push *+*)",
      "Bash(git commit *--amend*)", "Bash(git rebase:*)", "Bash(git reset --hard:*)",
      "Bash(git clean:*)", "Bash(git checkout -- :*)",
      "Bash(gh pr merge:*)", "Bash(gh pr close:*)", "Bash(gh pr review:*)",
      "Bash(gh pr ready:*)", "Bash(gh pr edit:*)", "Bash(gh pr create:*)",
      "Bash(gh api *-X*)", "Bash(gh api *--method*)", "Bash(gh api *-f *)",
      "Bash(gh api *-F *)", "Bash(gh api *--input*)"
    ]
  }
}
```

## Notes

- **No blanket `gh api`.** `Bash(gh api:*)` plus a handful of deny patterns leaves most
  writes reachable: `gh api` switches to POST as soon as any `-f`/`-F` field is present,
  the verb flag can be spelled several ways (`-X`, `--method`, `--method=...`), and
  `--input` posts a file body. A deny list cannot enumerate all of that. Allow the
  specific read endpoints you need and leave everything else to prompt/deny.
- **`gh api graphql` is deliberately not allowed.** A GraphQL mutation
  (`resolveReviewThread`, `addPullRequestReviewThreadReply`) travels in the same
  `-f query=` field as a read, so it cannot be told apart by pattern. Route thread
  fetches through the allow-listed `pr-threads.py` script instead.
- Replying to or resolving review threads on the PR's own threads is the only write this
  skill needs through the API. Grant it narrowly (the reply/resolve calls, via
  `pr-threads.py` or an exact-match rule), not through a wildcard.
- `gh pr merge` is denied on purpose: the skill never merges. If you add a merge step
  yourself, it must use `--match-head-commit <verified-sha>`.
- `git push origin HEAD` is allowed so Gate 4 can push; force variants are denied. Patterns
  are prefix/glob matches, not a security boundary on their own, so run unattended jobs
  in a disposable checkout with a token scoped to the one repository.
- Content read from the PR is untrusted (see Safety Rules in `SKILL.md`); this file limits
  the blast radius if that rule is ever violated.
