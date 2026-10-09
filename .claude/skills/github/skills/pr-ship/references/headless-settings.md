# Headless settings for pr-ship

**The deny rules below are advisory.** They are prefix/glob matches on command text, and
any allowed tool that can run or write arbitrary content defeats them (see "What the rules
cannot stop"). The real controls are outside this file:

1. A **disposable checkout** (fresh clone or worktree, deleted after the run).
2. A **repo-scoped, least-privilege token**: one repository, pull-request and contents
   write only, **no workflow-file write** (no `workflow` scope / "Workflows" permission),
   no admin, no org scope.
3. **No write access to workflow files or git hooks** for the run: protect `.github/` and
   hook directories with CODEOWNERS/branch protection, and keep the Edit/Write allow rules
   scoped to the worktree.

Template for running `github:pr-ship` unattended (`claude -p`). Save as a per-run
`settings.json` and pass it with `claude -p --settings ./pr-ship-settings.json ...`.
Deny rules win over allow rules. Set `GH_HOST` (if needed) in the launching environment,
not inside a command.

```json
{
  "permissions": {
    "allow": [
      "Read", "Grep", "Glob", "Agent",
      "Edit(./**)", "Write(./**)",
      "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git fetch:*)",
      "Bash(git add:*)", "Bash(git commit:*)", "Bash(git push origin HEAD)",
      "Bash(gh pr view:*)", "Bash(gh pr diff:*)", "Bash(gh pr checks:*)", "Bash(gh pr list:*)",
      "Bash(gh run list:*)", "Bash(gh run view:*)", "Bash(gh repo view:*)",
      "Bash(python3 ~/.claude/scripts/pr-threads.py:*)",
      "Bash(grep:*)", "Bash(tr:*)", "Bash(cut:*)", "Bash(echo:*)", "Bash(sleep:*)"
    ],
    "deny": [
      "Edit(.git/**)", "Write(.git/**)",
      "Edit(.github/**)", "Write(.github/**)",
      "Edit(.husky/**)", "Write(.husky/**)",
      "Edit(.githooks/**)", "Write(.githooks/**)",
      "Edit(.pre-commit-config.yaml)", "Write(.pre-commit-config.yaml)",
      "Bash(git push *--force*)", "Bash(git push * -f*)", "Bash(git push *+*)",
      "Bash(git commit *--amend*)", "Bash(git rebase:*)", "Bash(git reset --hard:*)",
      "Bash(git clean:*)", "Bash(git checkout -- :*)",
      "Bash(git *--upload-pack*)", "Bash(git *--receive-pack*)", "Bash(git *--exec*)",
      "Bash(git *--output*)", "Bash(git *--no-verify*)", "Bash(git commit * -n *)",
      "Bash(git -c *)", "Bash(git *core.hooksPath*)", "Bash(git config:*)",
      "Bash(gh api:*)",
      "Bash(gh pr merge:*)", "Bash(gh pr close:*)", "Bash(gh pr review:*)",
      "Bash(gh pr ready:*)", "Bash(gh pr edit:*)", "Bash(gh pr create:*)"
    ]
  }
}
```

The `Edit(...)`/`Write(...)` path syntax (relative to the working directory) and the
exact matching of `Bash(...)` glob patterns are **unverified** against your Claude Code
version; test each deny rule with a throwaway command before trusting it.

## Notes

- **`gh api` is denied outright, so reads are read-only by construction.** `gh api`
  switches to POST as soon as any field is present, and the field flag has many
  spellings: `-f`/`--raw-field`, `-F`/`--field`, `--input`, `-X`/`--method`, plus no-space
  (`-fbody=x`) and `=` (`--method=POST`) forms (flags confirmed with `gh api --help`). An
  allow rule like `gh api repos/*/*/issues/*/comments:*` therefore also matches
  `... --raw-field body=x`. Everything the skill reads has a non-`api` route:
  PR/issue comments and reviews via `gh pr view --json comments,reviews`, threads via
  `pr-threads.py`. If you must allow one endpoint, add an exact rule **without** a
  `:*` tail and deny every field/verb spelling above.
- **`gh api graphql` is likewise unavailable**: a mutation rides in `-f query=` exactly
  like a read. `pr-threads.py` makes its own API calls, outside these permissions.
- `gh pr merge` is denied on purpose: the skill never merges. A merge step you add
  yourself must use `--match-head-commit <verified-sha>`.
- `git push origin HEAD` is allowed so Gate 4 can push; force variants are denied.

## What the rules cannot stop

These carriers stay reachable with the allow list above. Deny patterns narrow them, token
and checkout isolation contain them; this is why the deny list is advisory, not the
"only write path" it might look like.

- **`pr-threads.py reply/resolve`** acts on any repo, PR and thread the token can reach.
  Scope the token to one repository.
- **Edit/Write plus `git commit`**: planted hooks (`.husky/`, `.git/hooks`, or a changed
  `core.hooksPath`) run at commit time. Mitigated by the path denies and `git config`
  deny above; contained by the disposable checkout.
- **Edit/Write plus `git push`**: a pushed `.github/workflows/*` change runs in CI with
  that repository's secrets. Contained only by a token without workflow-file write and by
  CODEOWNERS/branch protection on `.github/`.
- **`git fetch`/`git diff`/`git log` option carriers** (`--upload-pack=<cmd>`,
  `--output=FILE`): denied by pattern; a pattern miss would still execute or overwrite.
- **Build and test commands execute repo code** by definition. They are left out of the
  template. Opt in per stack (for example `Bash(go build:*)`, `Bash(go test:*)`) only when
  the checkout is disposable, and accept that PR-supplied code then runs with your
  environment.

## Steps unavailable headless

These pr-ship steps cannot run under the template. Do not widen the allow list to make
them work; take the degraded behavior, which for anything that writes is **Tier 3:
escalate and hold**.

| Step | Why it is unavailable | Degraded behavior |
|------|----------------------|-------------------|
| Closing Keyword Check, appending `Closes #N` (`gh pr edit`) | `gh pr edit` is denied | Report that the keyword is missing and which issue is referenced; do not edit the PR |
| Gate 5 conflict resolution (merge/checkout base, push) | Merge and branch switching are not allowed | Report `CONFLICTING`; Tier 3 hold |
| `gh pr merge` | Denied | Never merged; print the pinned merge command for the user |
| Gate 1b scoped test derivation (`sed`, `sort`, `xargs` pipelines) | `sed -i`, `sort -o` and `xargs` can write or run arbitrary commands | Run the stack's full test command if opted in; otherwise Tier 3 |
| Gate 1a/1b build and test | Not allowed by default (runs repo code) | Opt in per stack, or Tier 3 |
| `export GH_HOST=...` inside a command | Environment is set by the launcher | Set it before `claude -p` |
| Raw `gh api` reads | Denied (see Notes) | Use `gh pr view --json` or `pr-threads.py` |

Utilities the skill's own steps use (`tr`, `cut`, `grep`, `echo`, `sleep`) are in the allow
list because they are pure filters/timers (output redirection is not covered by these rules; do not rely on it being blocked).
