# Headless settings for pr-ship

**The deny rules below are advisory, and some are known to be bypassable.** Per the
[permissions docs](https://code.claude.com/docs/en/permissions), a Bash deny rule "matches the command text Claude writes"
and "isn't a security boundary around the program"; git also accepts unique long-option
prefixes, so no list of option spellings can be complete (see "What the rules cannot stop").
The controls that actually hold are in the launcher, not in the rules:

1. A **disposable checkout** (fresh clone or worktree, deleted after the run).
2. **Hooks and git config neutralized structurally** by the launcher (next section).
3. A **repo-scoped, least-privilege token**: one repository, pull-request and contents
   write only, **no workflow-file write** (no `workflow` scope / "Workflows" permission),
   no admin, no org scope.
4. **No write access to workflow files** for the run: protect `.github/` with
   CODEOWNERS/branch protection.

## Launcher requirements

Run before `claude -p`, in the disposable checkout:

```sh
git config core.hooksPath /dev/null          # no hook runs at commit/push, planted or not
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null   # no user/system git config (aliases, helpers, hooksPath)
export GIT_TERMINAL_PROMPT=0                 # never block on a credential prompt
export GH_HOST=<host>                        # only if not github.com; set here, not inside a command
```

Checked in a throwaway repo with a failing `pre-commit` hook (git 2.50.1):

- Without the setting, `git commit -m x` runs the hook and fails; `git commit -m x -n`,
  `git commit --no-verif -m y`, `git commit --no-v` (ambiguous, rejected), `git commit -nm z` and
  `git commit -anm q` all skip it. Option-spelling denies cannot cover that family.
- With `core.hooksPath=/dev/null`, `git commit -qm w` succeeds and no hook runs, so a planted
  `.git/hooks/*` or `.husky` hook cannot fire regardless of flags. The repo's own hook checks
  are therefore **not** run headless; Gates 1a/1b/2 are the equivalent.
- `git -c core.hooksPath=.git/hooks commit` re-enables hooks, so keep `Bash(git -c *)` denied
  and do not allow `git` with leading global options (the allow list below never matches them).
- In a git worktree, `git config core.hooksPath ...` writes the **shared** config of the main
  repository; prefer a fresh clone over a worktree for headless runs.
- `GIT_CONFIG_GLOBAL=/dev/null` also removes your global credential helper: supply push
  credentials through the token (for example a repo-local `credential.helper` set by the
  launcher), not through global config.

`git fetch --upload-pack` is still an open hole after all of the above: `git fetch
--upl='sh -c "..." #' origin` ran an arbitrary command in the same throwaway repo even with
`core.hooksPath=/dev/null` (`--upl` and `--upload-pac` are both accepted abbreviations).
The structural control is to allow network git commands only in an exact form, which Claude
Code allow rules can express: `Bash(git fetch origin)` and `Bash(git push origin HEAD)` with
**no wildcard tail**, so any added option fails to match. Allow no `ls-remote`, `clone`,
`pull` or `remote`. Claude Code allow rules cannot express "only against the configured
remote" for a wildcard form, which is why no `git fetch:*` is in the template. The exact-match
behavior of a rule without `*` is per the docs and was not run-tested against a live
Claude Code session.

## Template

Save as a per-run `settings.json` and pass it with `claude -p --settings ./pr-ship-settings.json ...`.
Deny rules win over allow rules.

```json
{
  "permissions": {
    "allow": [
      "Read", "Grep", "Glob", "Agent",
      "Edit(./**)", "Edit(//tmp/pr-ship-*)",
      "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git reflog show:*)",
      "Bash(git fetch origin)",
      "Bash(git add:*)", "Bash(git commit:*)", "Bash(git rev-parse HEAD)",
      "Bash(git push origin HEAD)",
      "Bash(gh pr view:*)", "Bash(gh pr diff:*)", "Bash(gh pr checks:*)", "Bash(gh pr list:*)",
      "Bash(gh run list:*)", "Bash(gh run view:*)", "Bash(gh repo view:*)",
      "Bash(python3 ~/.claude/scripts/pr-threads.py:*)",
      "Bash(date -u +%Y-%m-%dT%H:%M:%SZ)",
      "Bash(grep:*)", "Bash(tr:*)", "Bash(cut:*)", "Bash(echo:*)", "Bash(sleep:*)"
    ],
    "deny": [
      "Edit(.git)", "Edit(.git/**)",
      "Edit(.github/**)", "Edit(.claude/**)",
      "Edit(.husky/**)", "Edit(.githooks/**)",
      "Edit(.pre-commit-config.yaml)",
      "Bash(git push *--for*)", "Bash(git push * -f*)", "Bash(git push *+*)",
      "Bash(git commit *--am*)", "Bash(git rebase:*)", "Bash(git reset --hard:*)",
      "Bash(git clean:*)", "Bash(git checkout *)", "Bash(git switch *)",
      "Bash(git *--upl*)", "Bash(git *--rece*)", "Bash(git *--exe*)", "Bash(git *--ou*)",
      "Bash(git *--no-ver*)", "Bash(git commit *-n*)",
      "Bash(git -c *)", "Bash(git *core.hooksPath*)", "Bash(git config:*)",
      "Bash(gh api:*)",
      "Bash(gh pr merge:*)", "Bash(gh pr close:*)", "Bash(gh pr review:*)",
      "Bash(gh pr ready:*)", "Bash(gh pr edit:*)", "Bash(gh pr create:*)"
    ]
  }
}
```

## Rule syntax (from the permissions docs)

- **`Write(...)` rules are inert.** Claude Code consults only `Edit(path)` and `Read(path)` for
  file permissions; a `Write(path)` rule is "accepted but never consulted" (it warns at startup).
  `Edit(...)` covers Write, so the template has no `Write` entries.
- **State file in `/tmp`.** `Edit(./**)` is cwd-relative and does not cover `/tmp`; an
  absolute path needs the `//` form (`Edit(//tmp/scratch.txt)` in the docs). The template
  therefore adds the narrow `Edit(//tmp/pr-ship-*)`, which covers the state file
  (`/tmp/pr-ship-<owner>-<repo>-<branch-slug>-<PR>.md`) and a commit-message file
  (`/tmp/pr-ship-msg-<PR>.md`) for `git commit -F`. Write both with the Edit/Write tool, not
  shell redirects. An interactive run is unaffected: it uses the normal edit prompts.
- **`pr-threads.py` rule is literal text.** `Bash(python3 ~/.claude/scripts/pr-threads.py:*)`
  matches the characters `~/.claude/...`, not the expanded home directory. The agent must
  invoke it with the literal `~` form; an absolute path or `$HOME` matches nothing. To use an
  absolute path instead, put that exact path in the rule and in the launcher prompt.
- **`printf`, `date`, `export` are not in the docs' read-only set.** The skill's snippets use
  `echo` instead of `printf`, and the template allows only the exact `date -u
  +%Y-%m-%dT%H:%M:%SZ` form for timestamps.
- **Path patterns** use gitignore syntax. `Edit(./**)` is relative to the current directory,
  so it allows edits anywhere under the checkout. A bare name like `Edit(.git)` matches at any
  depth. In a **deny** rule a single-segment directory pattern such as `.github/**` also matches
  nested copies; in an **allow** rule it would match only at the top level.
- **`:*`** is only recognized at the very end of a Bash pattern and is equivalent to a trailing
  ` *` (so `git status:*` matches `git status` and `git status -s`). A `*` elsewhere stands for
  any text. The earlier `Bash(git checkout -- :*)` put `:*` after a space-separated token and is
  not that form; it is replaced by `Bash(git checkout *)`.
- **Redirections are checked.** `> file`, `>> file` and `2> file` are checked against your
  `Edit` allow and deny rules, protected paths and the working directories. So `echo > f` can
  write anything `Edit(./**)` allows, and nothing the `Edit` denies protect.
- **Allow rules are prefix matches on the command text**, so `git -C . push` or
  `git -c k=v commit` match no allow rule above. Unmatched commands are not auto-approved
  (with no human to approve under `claude -p`, expected to fail; not run-tested here).

## Tradeoff: deny patterns also block benign commands

The patterns are substrings of the whole command text, so a commit message or path that
contains one is blocked too: `git commit -m "document --amend handling"`, `-m "fix-nothing"`
(matches `*-n*`), or a message mentioning `core.hooksPath`. Put the
message in a file and use `git commit -F <file>`, or reword. The patterns are partial
mitigations of the commonest spellings, not controls (`git commit -anm` slips past `*-n*`).

## Notes

- **`gh api` is denied outright, so reads need a non-`api` route.** `gh api` switches to POST
  as soon as any field is present, and the field flag has many spellings: `-f`/`--raw-field`,
  `-F`/`--field`, `--input`, `-X`/`--method`, plus no-space (`-fbody=x`) and `=`
  (`--method=POST`) forms (flags confirmed with `gh api --help`). An allow rule like
  `gh api repos/*/*/issues/*/comments:*` therefore also matches `... --raw-field body=x`.
  Everything the skill reads has a non-`api` route: PR/issue comments and reviews via
  `gh pr view --json comments,reviews`, threads via `pr-threads.py`. If you must allow one
  endpoint, add an exact rule **without** a `:*` tail and deny every field/verb spelling above.
- **`gh api graphql` is likewise unavailable**: a mutation rides in `-f query=` exactly
  like a read. `pr-threads.py` makes its own API calls, outside these permissions, and its
  `reply`/`resolve` subcommands write (see below).
- `gh pr merge` is denied on purpose: the skill never merges. A merge step you add
  yourself must use `--match-head-commit <verified-sha>`.
- `git push origin HEAD` is allowed so Gate 4 can push; force variants are denied (partially).
  `git rev-parse HEAD` is allowed so a push's SHA can be recorded in Push History.
- `git fetch origin` is exact so no option can follow it.

## What the rules cannot stop

These stay reachable with the allow list above. Deny patterns narrow them; the launcher
settings, token and checkout isolation contain them.

- **Option-prefix bypasses of the deny patterns.** git accepts any unique prefix of a long
  option, and short options bundle. Verified: `git commit -m x -n`, `git commit --no-verif`,
  `git commit -nm z`, `git commit -anm q` skip hooks; `git fetch --upl='<cmd>' origin` runs
  `<cmd>`. The partial denies above (`*--upl*`, `*--no-ver*`, `*-n*`, ...) catch the common
  spellings only. Control: `core.hooksPath=/dev/null` (hooks) and exact-form network
  allows (fetch/push), not the deny list.
- **`git diff`/`git log` write/exec options.** `--output=FILE` (any unique prefix) overwrites
  a file; `--ext-diff` and textconv run drivers from repo config. Partially denied; contained
  by the disposable checkout.
- **`pr-threads.py reply/resolve`** acts on any repo, PR and thread the token can reach.
  Scope the token to one repository.
- **Edit plus `git push`**: a pushed `.github/workflows/*` change runs in CI with that
  repository's secrets. Contained only by a token without workflow-file write and by
  CODEOWNERS/branch protection on `.github/`.
- **`Edit(./**)` is broad.** It covers `.claude/settings.json` and hooks (denied above with
  `Edit(.claude/**)`, but a PR can also *arrive* with them already in the checkout), and every
  script that a build or test command runs (`Makefile`, `package.json`, test files, CI
  helpers). Edit plus an opted-in build/test command is arbitrary code execution.
- **In a git worktree `.git` is a file**, not a directory, so `Edit(.git/**)` does not match
  it; `Edit(.git)` does, but the real `.git` directory (shared config, hooks) lives outside
  the working directory. Use a fresh clone to avoid the ambiguity.
- **Hold state in `/tmp`.** The hold records the live remote `headRefOid`, and local-only
  commits never clear it. The Push History used by the hold-clear check is an untrusted
  local file; the skill also consults the checkout's reflog (`update by push` entries on
  `refs/remotes/origin/<branch>`), which exists only in the same checkout. If neither can
  be consulted, a hold is not auto-cleared.
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
| PR number defaulted from the current branch (`git branch --show-current`) | `git branch` is not allowed | Pass the PR number as the argument |
| Closing Keyword Check's `sort`-based issue extraction | `sort` is not allowed (and `gh pr edit` is denied anyway) | Unavailable headless (see the closing-keyword row above) |
| Raw `gh api` reads | Denied (see Notes) | Use `gh pr view --json` or `pr-threads.py` |
| Ending the turn to wait for a polling agent | Under `claude -p` the process exits when the turn ends | Keep the polling agent in the foreground inside the invocation, or re-invoke from an external scheduler (see SKILL.md, Background Polling) |

Utilities the skill's own steps use (`tr`, `cut`, `grep`, `echo`, `sleep`) are in the allow
list because they are pure filters/timers. Output redirection is **not** free: it is checked
against the `Edit` rules (see Rule syntax), so `echo x > file` can write wherever `Edit(./**)`
allows and nowhere the `Edit` denies cover.
