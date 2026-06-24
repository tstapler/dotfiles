# Stack Research: git-ssh-fallback

**Date**: 2026-06-24
**Researcher**: SDD research agent

---

## 1. Implementation Language: Shell Script vs Go vs Rust

### Verdict: Shell script (`#!/usr/bin/env sh`) is the right choice

**Why shell wins here:**

- The tool does three things: check `gh auth status`, parse a URL, re-exec git. All three are one-liners in POSIX sh.
- cfgcaddy deploys `stapler-scripts/*` to `bin/scripts` via symlink (confirmed in `~/.cfgcaddy.yml`). A shell script drops in without any build step.
- The existing codebase (`set_git_ssh`, `git_shared.sh`, `ssh-switch`, `check_commit_email`) is entirely shell for git-adjacent helpers. Pattern consistency matters for maintainability.
- No compilation toolchain required on new machines before bootstrap runs.
- The Rust binary in the repo (`claude-proxy-rs`) and Python tools (`claude-proxy`, `display-switch`) are used only where shell is genuinely insufficient (async HTTP proxy, display automation). This is not that case.

**Go/Rust disqualifiers:**

- Both require a build step before the binary is usable. Bootstrap would need a `go build` / `cargo build` stage. This adds failure modes and ordering dependencies in `playbook.yml`.
- The latency budget is 500ms. `gh auth status` completes in ~50–265ms (measured: 52ms for unauthenticated host, 265ms for authenticated github.com). A shell script with no startup overhead stays well inside budget.
- `golangci-lint` is in `Brewfile` but there is no Go module at the dotfiles root, meaning Go is not a first-class tool here.

**Shell anti-patterns to avoid:**

- Do not use `bash`-isms (arrays, `[[`, process substitution) — the `aliases.sh` `git()` function already wraps hub and a POSIX sh wrapper must survive being sourced from varied contexts.
- Use `#!/usr/bin/env sh` not `#!/bin/bash` for maximum portability (macOS/Linux).

---

## 2. Git Credential Helper Protocol

**Protocol mechanics (confirmed via `git help gitcredentials`):**

The credential helper protocol is a simple line-oriented stdin/stdout exchange. Git invokes the helper with one of three subcommands:

- `get` — git sends key=value pairs (protocol, host, username), helper responds with username= and password= or exits non-zero to signal "no credentials"
- `store` — git sends successful credentials for the helper to cache
- `erase` — git sends credentials that failed; helper should invalidate them

**Critical constraint for this project:**

The helper receives a `host=` field but **cannot change the protocol**. A credential helper invoked for `https://github.com` cannot redirect git to use `git@github.com:...` instead. The helper can only return a username+password (or nothing). This is a hard architectural limit.

**Implication:** A git wrapper (intercept the command, rewrite URLs, re-exec with SSH) is the only path to transparent protocol switching. The credential helper approach is a dead end for this feature.

**Observed behavior of `gh auth git-credential`:**

```
$ echo "protocol=https\nhost=github.com" | git credential fill
protocol=https
host=github.com
username=TylerStaplerAtFanatics
password=gho_****
```

When gh has no token for a host it exits non-zero and outputs nothing. Git then falls through to the next helper in the chain, or prompts the user.

---

## 3. `git config url.insteadOf` — How It Works and Its Limits

**Mechanism:**

```gitconfig
[url "git@github.com:"]
    insteadOf = https://github.com/
```

When git resolves any remote URL, it checks all `url.<base>.insteadOf` entries and replaces the longest matching prefix. This happens before the credential helper is consulted, before any network connection is made. It applies to clone, fetch, push, pull — all operations.

**Limits (confirmed via `git config --help`):**

1. **Global and unconditional** — once in `.gitconfig`, it applies to every HTTPS URL matching that prefix, every time, with no way to condition it on auth state. This breaks `gh pr create` (which uses HTTPS internally), GitHub Actions tokens, and HTTPS-only corporate proxies.
2. **Longest-match wins** — if two patterns overlap, the longer one takes precedence. Useful for per-host specificity but still stateless.
3. **`pushInsteadOf` is a companion** — `url.<base>.pushInsteadOf` rewrites only for push operations. Useful but still unconditional.
4. **No env-var gating** — there is no native way to make `insteadOf` conditional on an environment variable. Conditionality requires the wrapper approach.

**`url.insteadOf` + session env var approach:**

A git wrapper could write a temporary `.gitconfig` or set `GIT_CONFIG_PARAMETERS` to inject `insteadOf` only for the current invocation. This is the cleanest hybrid: the persistent `.gitconfig` is unchanged, but when the wrapper detects missing auth it invokes the real git with an extra env-var-based config that rewrites the URL for that one call.

`GIT_CONFIG_PARAMETERS` is a git 2.31+ feature. macOS ships git 2.39+ (Apple Command Line Tools), so this is safe.

Example:
```sh
GIT_CONFIG_PARAMETERS="'url.git@github.com:.insteadOf=https://github.com/'" git "$@"
```

This avoids persistent side effects entirely.

---

## 4. Shell Wrapper: Transparent PATH-Prepend Approach

**The approach:**

Place a script named `git` in a directory that appears **before** `/usr/bin` in `$PATH`. From `.shell/exports.sh`, `~/.local/bin` is the first directory added to PATH. cfgcaddy deploys `stapler-scripts/*` to `bin/scripts` (symlinked at `~/bin/scripts`). The correct install target is `~/.local/bin/git`.

**Recursive call hazard:**

A script named `git` that calls `git` will recurse infinitely. The solution is to call the real git binary by absolute path:

```sh
REAL_GIT=$(command -v git | grep -v "$HOME/.local/bin") # skip self
# or store the path at install time
REAL_GIT=/usr/bin/git  # macOS CLT path, reliable
```

On macOS, `/usr/bin/git` is the stable system git. On Linux with Homebrew, `/home/linuxbrew/.linuxbrew/bin/git` or `/usr/bin/git`. The wrapper should probe at invocation:

```sh
_real_git() {
    # Find git that isn't this wrapper
    IFS=: read -ra _path <<< "$PATH"
    for _dir in "${_path[@]}"; do
        [ "$_dir" = "$(dirname "$0")" ] && continue
        [ -x "$_dir/git" ] && { echo "$_dir/git"; return; }
    done
}
```

**Shell function vs PATH-prepend:**

The existing `aliases.sh` already defines `function git() { hub "$@"; }` (when hub is installed). This is a shell-function wrapper at the shell level. It would **not** be invoked by IDE git operations, Claude Code subagents, or scripts that exec git directly — those go through PATH. The PATH-prepend approach covers all invocation paths. The shell function approach covers only interactive shells and tools that inherit the shell environment.

For the headless/subagent use case (explicitly required), PATH-prepend is mandatory.

**Conflict with hub function:**

The hub `git()` function in `aliases.sh` will shadow the PATH-prepend wrapper in interactive shells — but hub delegates to git internally, and by the time hub calls git the PATH-prepend wrapper is in PATH. This should not cause infinite recursion because hub is not git; it only becomes an issue if hub calls `git` as a shell function (it doesn't — hub is a compiled binary).

---

## 5. `gh auth status` — Behavior, Exit Codes, Speed

**Measured performance (this machine):**

| Scenario | Time |
|---|---|
| Authenticated host (github.com) | 265ms |
| Unauthenticated host (gitlab.com) | 52ms |
| Unauthenticated host (nonexistent.example.com) | 52ms |

Both cases are well within the 500ms SLO. The unauthenticated path (the one that triggers fallback) is the fastest.

**Exit codes:**

- `0` — authenticated and token is valid
- `1` — not logged in to this host

**Relevant flags:**

- `gh auth status --hostname <host>` — checks only that host, avoids querying all configured accounts. More targeted and slightly faster.
- `gh auth token --hostname <host>` — outputs just the raw token on stdout. Non-zero exit if no token. Faster than `auth status` and avoids parsing human-readable output.

**Caching consideration:**

`gh auth token` is the better detection primitive: it exits 0 with a token, or exits non-zero with no output. The wrapper can use:

```sh
if ! gh auth token --hostname "$host" >/dev/null 2>&1; then
    # fallback to SSH
fi
```

For caching, a file at `~/.cache/git-ssh-fallback/<host>.ok` with a 1-hour mtime could skip the gh invocation on subsequent calls, at the cost of not detecting token expiry immediately. Given the 52ms cost for the unauthenticated check, caching is an optimization not a requirement — defer until measured to be a problem.

---

## 6. SSH Agent Socket Detection for Headless Environments

**Existing infrastructure (confirmed in dotfiles):**

`~/.config/environment.d/ssh-agent.conf`:
```
SSH_AUTH_SOCK=${HOME}/.1password/agent.sock
```

This sets `SSH_AUTH_SOCK` for systemd user sessions (Claude Code subagent, background services). It points to 1Password's SSH agent socket.

`~/.shell/exports.sh` contains a runtime check:
```sh
if [ -z "$SSH_AUTH_SOCK" ] || [ ! -S "$SSH_AUTH_SOCK" ]; then
  _op_sock="$HOME/.1password/agent.sock"
  _gpg_sock="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/gnupg/S.gpg-agent.ssh"
  _fb_sock=$(ls -t "$HOME/.ssh/agent"/s.*.agent.* 2>/dev/null | head -1)
  # priority: 1Password > GPG > ~/.ssh/agent/*
fi
```

**What the git-ssh-fallback wrapper must do:**

The wrapper should not assume `SSH_AUTH_SOCK` is set. Before invoking git with SSH, it should:

1. Check if `SSH_AUTH_SOCK` is set and points to a live socket: `[ -S "$SSH_AUTH_SOCK" ]`
2. If not, probe the known socket paths in priority order (mirror `exports.sh` logic)
3. If no agent socket is found, emit a diagnostic and exit with an error (do not hang waiting for SSH to prompt for key passphrase)

For truly headless contexts (cron, launchd, CI-like), the wrapper should pass `-o BatchMode=yes` via `GIT_SSH_COMMAND` to prevent SSH from prompting:

```sh
export GIT_SSH_COMMAND="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
```

`StrictHostKeyChecking=accept-new` automatically accepts new host keys (no prompt) but still rejects changed host keys. This is the right tradeoff for headless use: new hosts work, MITM attacks are still blocked.

---

## 7. GIT_TRACE — What It Exposes and How a Wrapper Can Emit to It

**What GIT_TRACE exposes (confirmed via `GIT_TRACE=1 git status`):**

```
11:27:02.103289 exec-cmd.c:145  trace: resolved executable path from Darwin stack: /Library/Developer/CommandLineTools/usr/bin/git
11:27:02.104171 git.c:476       trace: built-in: git status
11:27:02.107691 run-command.c:673 trace: run_command: cd cfgcaddy; unset GIT_PREFIX; GIT_DIR=.git git status --porcelain=2
```

GIT_TRACE writes timestamped trace lines to stderr (when set to `1`, `true`, or `2`). Setting `GIT_TRACE=2` redirects to fd 2 (stderr). Setting it to a path like `GIT_TRACE=/tmp/git-trace.log` redirects to a file.

**How the wrapper should emit diagnostic output:**

The wrapper should check if `GIT_TRACE` is set **or** if `GIT_SSH_FALLBACK_DEBUG=1` is set, and if so write to stderr:

```sh
_log() {
    if [ -n "$GIT_SSH_FALLBACK_DEBUG" ] || [ -n "$GIT_TRACE" ]; then
        printf '[git-ssh-fallback] %s\n' "$*" >&2
    fi
}
```

This integrates with `GIT_TRACE=1 git fetch` output that developers already use for debugging, without adding noise to normal operation. The `[git-ssh-fallback]` prefix distinguishes wrapper output from git's own trace lines.

**GIT_TRACE_CURL** is a separate variable that traces HTTP headers (useful for debugging HTTPS auth failures but not directly relevant to the wrapper).

---

## 8. URL Rewriting: HTTPS → SSH Format

**Universal pattern (confirmed for GitHub, GitLab, Gitea, self-hosted):**

All major git hosts follow the same SSH URL convention:
- HTTPS: `https://HOST/ORG/REPO.git`
- SSH: `git@HOST:ORG/REPO.git`

The transform is mechanical:
```
strip "https://"
split at first "/"
→ HOST, PATH
→ "git@" + HOST + ":" + PATH
```

Verified for:
- `https://github.com/tstapler/myrepo` → `git@github.com:tstapler/myrepo.git`
- `https://gitlab.com/org/sub/repo.git` → `git@gitlab.com:org/sub/repo.git`
- `https://gitea.example.com/org/repo` → `git@gitea.example.com:org/repo.git`

POSIX sh implementation:
```sh
https_to_ssh() {
    _url="$1"
    _url="${_url#https://}"        # strip scheme
    _host="${_url%%/*}"            # everything before first /
    _path="${_url#*/}"             # everything after first /
    _path="${_path%.git}"          # strip trailing .git if present
    echo "git@${_host}:${_path}.git"
}
```

---

## 9. Deployment and Distribution

**cfgcaddy link spec (from `~/.cfgcaddy.yml`):**

```yaml
- src: stapler-scripts/*
  dest: bin/scripts
  os: "Linux Darwin"
```

This symlinks all files in `dotfiles/stapler-scripts/` to `~/bin/scripts/`. However, `~/bin/scripts` is not in the PATH shown — `~/.local/bin` is. The wrapper must be placed in `~/.local/bin/git`, either by:

1. Adding a cfgcaddy link rule: `src: stapler-scripts/git-ssh-fallback`, `dest: .local/bin/git`
2. Or adding an Ansible task in `bootstrap/roles/github/tasks/main.yml` (fits thematically with the existing SSH/git setup in that role)

The Ansible approach is more explicit and bootstrappable on new machines without requiring `cfgcaddy link` to run first.

---

## 10. Key Architecture Decision

**Recommended implementation path:**

A POSIX shell script at `stapler-scripts/git-ssh-fallback` (symlinked to `~/.local/bin/git`) that:

1. Extracts the remote host from git args (parse `clone URL` directly; for fetch/push/pull use `git -C <dir> remote get-url origin` via the real git)
2. Calls `gh auth token --hostname "$host" >/dev/null 2>&1`
3. If exit 0: exec the real git with original args unchanged (zero overhead beyond the gh check)
4. If exit non-zero: convert HTTPS URL → SSH URL, set `GIT_SSH_COMMAND` with `BatchMode=yes StrictHostKeyChecking=accept-new`, emit diagnostic, exec the real git with rewritten args
5. For operations that don't involve a remote (status, log, diff): exec real git immediately without any auth check

**Why not `GIT_CONFIG_PARAMETERS` with `url.insteadOf`:**

Rewriting the URL argument directly is simpler and doesn't require git 2.31+. Exec with rewritten args avoids the need to understand `GIT_CONFIG_PARAMETERS` quoting rules.

---

## Summary of Confirmed Facts

| Question | Answer |
|---|---|
| Best implementation language | POSIX shell script |
| Credential helper protocol-switch | Impossible — git wrapper is the only path |
| `url.insteadOf` conditionality | None natively; requires wrapper to inject per-invocation |
| `gh auth status` latency | 52ms (unauthenticated), 265ms (authenticated) |
| `gh auth token` exit codes | 0=valid token, 1=no token |
| GIT_TRACE emission | Write to stderr with `[git-ssh-fallback]` prefix when `GIT_TRACE` or `GIT_SSH_FALLBACK_DEBUG=1` |
| SSH agent for headless | `~/.1password/agent.sock` via `environment.d`; must check before SSH ops |
| SSH URL format (cross-host) | `git@HOST:ORG/REPO.git` for all major hosts |
| Deployment path | `~/.local/bin/git` (first in PATH); add cfgcaddy link or Ansible task |
| Recursive call prevention | Skip `$HOME/.local/bin` when probing PATH for real git; fall back to `/usr/bin/git` |
