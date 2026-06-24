# Architecture Research: git-ssh-fallback

Date: 2026-06-24
Research phase for: `project_plans/git-ssh-fallback/requirements.md`

---

## 1. Git Credential Helper Protocol: Can It Signal SSH Fallback?

**Verdict: Dead end. The credential helper protocol cannot switch protocols.**

The git credential helper protocol is a line-oriented stdin/stdout protocol with exactly three operations: `get`, `store`, `erase`. On `get`, the helper receives a key/value block (protocol=, host=, path=) and writes back username= and password=. Git reads these and proceeds with the HTTPS request.

Exit codes only signal capability support — a non-zero exit means "no capabilities understood," not "switch to SSH." If a helper exits with no output on `get`, git proceeds to prompt the user interactively (or fails in headless contexts). There is no field, flag, or exit code that tells git "retry this operation over SSH."

The `continue` flag (introduced for multi-round auth like NTLM/Kerberos) is the closest to a signaling mechanism, but it still operates entirely within the HTTP auth flow. There is no escape hatch to the SSH transport layer from inside a credential helper.

**Implication:** Any solution must operate *outside* the credential helper layer — either by wrapping git itself or by pre-rewriting URLs before git is invoked.

References:
- [git-credential man page](https://git-scm.com/docs/git-credential)
- [gitcredentials documentation](https://git-scm.com/docs/gitcredentials)
- [How Does Git Authentication Work? — Ken Muse](https://www.kenmuse.com/blog/how-does-git-authentication-work/)

---

## 2. Git Wrapper Approach: PATH Prepend or Shell Function

**Both work. Shell function is safer for interactive shells; script-in-PATH is better for headless/subagents.**

### Shell function (interactive shells)

```bash
git() {
    # pre-logic: check auth, maybe set env vars
    command git "$@"
    local rc=$?
    # post-logic: examine $rc and stderr, retry via SSH if needed
    return $rc
}
```

`command git` bypasses the function and invokes the binary directly — no recursion risk. Defined in `~/.zshrc` or `~/.bashrc`, it covers interactive shells. **Does not cover** headless subprocesses, systemd user units, IDE-launched git operations, or Claude Code subagents unless those contexts source the shell profile.

### Script-in-PATH (~/.local/bin/git or ~/bin/git)

Place a `git` executable earlier in `PATH` than `/usr/bin/git`. Inside the script, avoid infinite recursion by either:
- Hard-coding the real git binary path (`exec /usr/bin/git "$@"` or `exec $(type -ap git | grep -v "$0" | head -1) "$@"`)
- Stripping the wrapper directory from PATH before exec: `PATH=$(echo "$PATH" | tr ':' '\n' | grep -v "$HOME/.local/bin" | tr '\n' ':') exec git "$@"`

**Pitfalls:**
1. **Recursive invocation:** Must explicitly skip the wrapper when calling git internally. Hard-coded absolute path is the safest.
2. **git alias `!` commands:** Git aliases prefixed with `!` run as shell commands from the repo root with a modified environment — they will re-enter the wrapper, which may cause double-execution of pre-logic.
3. **IDE and subagent integration:** IDEs (VSCode, IntelliJ) and Claude Code subagents spawn git directly via PATH, not via a shell function. A script-in-PATH covers these; a shell function does not.
4. **GIT_PREFIX / cwd shifts:** Alias-triggered shell commands run from the repo root, not the original cwd; wrapper logic that depends on cwd needs adjustment.

**Recommendation:** Use both. Shell function for interactive shells (sourced from `~/.zshrc`); script-in-PATH at `~/.local/bin/git` for headless contexts. The script path covers Claude Code subagents, systemd, and CI-like environments. The dotfiles `install.sh` can symlink or install the script.

References:
- [git wrapper gist — global pre/post hooks](https://gist.github.com/mmueller/7286919)
- [git-retry fault-tolerant wrapper](https://github.com/blond/git-retry)

---

## 3. url.insteadOf Conditionality: Per-Invocation Options

### Option A: `git -c url.<base>.insteadOf=...` (per-invocation flag)

```bash
git -c 'url.git@github.com:.insteadOf=https://github.com/' fetch
```

Works for a single command. Clean, no side effects. Useful inside a wrapper script that has already decided to rewrite.

### Option B: `GIT_CONFIG_COUNT` / `GIT_CONFIG_KEY_n` / `GIT_CONFIG_VALUE_n` (env vars)

Introduced in git 2.31+. Lets you inject arbitrary config key-value pairs via environment variables for a single subprocess:

```bash
export GIT_CONFIG_COUNT=1
export GIT_CONFIG_KEY_0="url.git@github.com:.insteadOf"
export GIT_CONFIG_VALUE_0="https://github.com/"
git fetch   # uses SSH URL transparently
```

These environment variables override config files but are overridden by `-c` flags. **This is the cleanest mechanism for a wrapper** — set the env vars before exec'ing the real git, no temporary files, no config mutation, works for any subcommand including `clone`. The env vars survive into git's child processes (e.g., LFS) automatically.

**Caveat:** There are rare compatibility issues reported with `GIT_CONFIG_VALUE_0` and third-party tools (e.g., `pre-commit`) that also set these variables. Should be rare in practice.

### Option C: Persistent `url.insteadOf` in ~/.gitconfig

```gitconfig
[url "git@github.com:"]
    insteadOf = https://github.com/
```

This is a **permanent global rewrite** — all HTTPS operations to github.com become SSH, regardless of whether gh is authenticated. Breaks `gh auth git-credential` for HTTPS, breaks `cargo`, `go get`, and other tools that rely on HTTPS-URL resolution. Not suitable for Tyler's use case where HTTPS should continue working when gh is authenticated.

### Option D: `includeIf` conditional includes

`includeIf "gitdir:..."` activates a config file based on repository location. `includeIf "onbranch:..."` activates on branch name. Neither condition can be based on runtime state (auth status). There is no `includeIf "env:..."`. This approach cannot implement dynamic, per-auth-state URL rewriting.

**Recommendation:** Use `GIT_CONFIG_COUNT` / `GIT_CONFIG_KEY_n` / `GIT_CONFIG_VALUE_n` in the wrapper script when SSH fallback is needed. Construct the env vars to cover all detected HTTPS hosts generically (one pair per unique hostname). Then `exec` the real git with these vars set.

References:
- [git Environment Variables — GIT_CONFIG_COUNT](https://git-scm.com/book/en/v2/Git-Internals-Environment-Variables)
- [git-config documentation](https://git-scm.com/docs/git-config)
- [Using url.insteadOf in git-clone — Graphite](https://graphite.com/guides/git-config-insteadof)

---

## 4. Proactive vs. Reactive Fallback

### Proactive: check `gh auth status` before running git, rewrite URL if not authed

**Mechanism:** Before exec'ing real git, parse the remote URL from the arguments (or from `git remote get-url origin` for subcommands like `fetch`/`push`/`pull`). If the URL is HTTPS, run `gh auth status --hostname <host>`. If exit code is non-zero, inject SSH URL via env vars and proceed.

**Pros:**
- Zero latency on the happy path (gh authenticated): no retry, no stderr capture, no error parsing
- The git command runs exactly once
- Clean behavior in non-interactive contexts (no hanging on prompts)

**Cons:**
- `gh auth status` exit code has a known bug history (issue #8845: always returned 0 in some versions)
- `gh auth status` invokes gh which may hit the network or Keychain, adding latency (target SLO: < 500ms)
- Does not cover non-GitHub hosts unless `gh` supports them (gh only handles GitHub/GHE hosts)
- Requires parsing the remote URL from git arguments — complex for `clone` (URL is in args) vs. `fetch`/`push` (URL is in config)
- Caching auth state helps: write a small cache file (`~/.cache/git-ssh-fallback/<host>.auth`) with a TTL of ~5 minutes

**Latency:** `gh auth status` on macOS with a valid Keychain token typically completes in 50–200ms. If cached, near-zero. If gh is not installed or not on PATH, the check fails gracefully (skip fallback, proceed normally).

### Reactive: let git fail, parse stderr, retry with SSH URL

**Mechanism:** Run git normally. Capture stderr. If exit code is 128 and stderr contains auth-failure strings (`fatal: could not read Username`, `Authentication failed`, `remote: HTTP Basic: Access denied`, `remote: Support for password authentication was removed`), rewrite URL to SSH and re-run.

**Pros:**
- Guaranteed no behavior change on success path (HTTPS with valid auth just works)
- Does not require `gh` at all — works for any HTTPS host with SSH keys
- Exit code 128 is definitive for fatal git errors

**Cons:**
- Requires capturing stderr, which means buffering the full output before printing it — this breaks streaming progress output for large clone/fetch operations (user sees nothing during the failed attempt, then everything restarts)
- Adds one full git invocation latency on the fallback path (could be seconds for a large repo)
- Stderr parsing is fragile — error message strings vary by git version and remote host. GitHub, GitLab, Bitbucket, and Gitea all produce different error text.
- Hanging git prompts (e.g., `Username for 'https://...'`) must be suppressed with `GIT_TERMINAL_PROMPT=0` or `GIT_ASKPASS=/bin/false`, otherwise the reactive path never triggers (git blocks waiting for input instead of failing)
- **Critical:** Must set `GIT_TERMINAL_PROMPT=0` for the initial attempt to prevent interactive prompts in headless contexts from blocking indefinitely.

**Recommendation: Proactive with cached state for known hosts (primarily GitHub), with reactive as a safety net.**

Rationale:
1. The proactive path covers the primary use case (GitHub, gh CLI) cleanly and within SLO.
2. For non-GitHub HTTPS hosts where `gh auth status` cannot help, a lightweight "attempt with `GIT_TERMINAL_PROMPT=0`, parse exit code 128 + stderr" reactive path catches failures.
3. Combining both gives defense in depth without significant complexity.
4. Always set `GIT_TERMINAL_PROMPT=0` unconditionally to prevent hanging in headless contexts; restore or omit for interactive shells where prompts are desired (but if the wrapper is doing its job, prompts should not appear).

References:
- [`gh auth status` exit code bug #8845](https://github.com/cli/cli/issues/8845)
- [Claude Code multi-agent gh auth toast issue #67055](https://github.com/anthropics/claude-code/issues/67055)
- [gh-auth-status-shim for exit code reliability](https://github.com/cnighswonger/claude-code-cache-fix/blob/main/tools/gh-auth-status-shim/README.md)

---

## 5. Integration with Existing .gitconfig

Tyler's current `.gitconfig` (at `/Users/tyler.stapler/dotfiles/.gitconfig`):

```gitconfig
[credential "https://github.com"]
    helper =
    helper = !/opt/homebrew/bin/gh auth git-credential
[credential "https://gist.github.com"]
    helper =
    helper = !/opt/homebrew/bin/gh auth git-credential
[credential]
    helper = !gh auth git-credential
```

The `helper =` (empty line) before each `gh` helper is a standard pattern to reset the inherited credential helper chain before adding the `gh`-specific one. This prevents credential stuffing from multiple helpers.

**Key constraint:** The wrapper must not modify `.gitconfig`. Adding a global `url.insteadOf` to `.gitconfig` would permanently bypass `gh auth git-credential` and break all HTTPS tooling (Cargo, Go modules, npm git dependencies). The URL rewrite must be per-invocation only.

**Integration strategy:**

1. The wrapper script detects that a git HTTPS operation would fail auth.
2. It injects `GIT_CONFIG_KEY_n` / `GIT_CONFIG_VALUE_n` for the specific host only.
3. With SSH URL rewriting active, git never reaches the credential helper for that host — the credential helper chain is preserved for hosts not being rewritten.
4. The `[hub] protocol = ssh` stanza in `.gitconfig` already indicates Tyler prefers SSH for hub/GitHub operations — the fallback aligns with this intent.
5. The `[includeIf "gitdir:~/WorkProjects/"]` stanza loads `.gitconfig.fbg` for work repos — the wrapper must not interfere with work-host credentials. The per-host `GIT_CONFIG_KEY_n` approach is safe here: only inject SSH rewrite for hosts where `gh auth status` fails, not globally.

**Host detection:** Extract the hostname from the HTTPS URL being operated on. For `fetch`/`push`/`pull`, get it from `git remote get-url <remote>`. For `clone`, parse it from the command-line argument. Run `gh auth status --hostname <host>` only for GitHub-family hosts. For non-GitHub HTTPS hosts, fall through to reactive detection.

---

## 6. SSH Agent Socket Detection

Tyler's existing detection logic (from `/Users/tyler.stapler/dotfiles/.shell/exports.sh`, lines 155–169):

```bash
# SSH agent priority: 1Password → GPG → ~/.ssh/agent/* fallback.
if [ -z "$SSH_AUTH_SOCK" ] || [ ! -S "$SSH_AUTH_SOCK" ]; then
  _gpg_sock="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/gnupg/S.gpg-agent.ssh"
  _op_sock="$HOME/.1password/agent.sock"
  _fb_sock=$(ls -t "$HOME/.ssh/agent"/s.*.agent.* 2>/dev/null | head -1)
  if [ -S "$_op_sock" ]; then
    export SSH_AUTH_SOCK="$_op_sock"
  elif [ -S "$_gpg_sock" ]; then
    export SSH_AUTH_SOCK="$_gpg_sock"
  elif [ -n "$_fb_sock" ] && [ -S "$_fb_sock" ]; then
    export SSH_AUTH_SOCK="$_fb_sock"
  fi
  unset _gpg_sock _op_sock _fb_sock
fi
```

This logic runs at shell startup for interactive shells. In headless contexts (Claude Code subagents, systemd user units), it may not run at all.

**Agent socket locations by priority:**

| Priority | Agent | macOS socket path | Linux socket path |
|---|---|---|---|
| 1 | 1Password | `~/.1password/agent.sock` (symlink) | `~/.1password/agent.sock` |
| 1 | 1Password (native macOS) | `~/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock` | — |
| 2 | GPG agent | `$GNUPGHOME/S.gpg-agent.ssh` | `$XDG_RUNTIME_DIR/gnupg/S.gpg-agent.ssh` |
| 3 | macOS system agent | `/private/tmp/com.apple.launchd.*/Listeners` (glob) | — |
| 4 | Fanatics bastion agent | `~/.ssh/agent/s.*.agent.*` (glob, newest) | same |
| 5 | Standard SSH agent | `$SSH_AUTH_SOCK` if already set | `$XDG_RUNTIME_DIR/ssh-agent.socket` |

**Detection algorithm for the wrapper script:**

```bash
_detect_ssh_agent() {
    # 1. If SSH_AUTH_SOCK is already set and the socket exists, use it
    if [ -n "$SSH_AUTH_SOCK" ] && [ -S "$SSH_AUTH_SOCK" ]; then
        return 0
    fi
    # 2. 1Password symlink (macOS and Linux)
    local _op="$HOME/.1password/agent.sock"
    [ -S "$_op" ] && export SSH_AUTH_SOCK="$_op" && return 0
    # 3. 1Password native macOS path
    local _op_mac="$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"
    [ -S "$_op_mac" ] && export SSH_AUTH_SOCK="$_op_mac" && return 0
    # 4. GPG agent SSH socket
    local _gpg="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/gnupg/S.gpg-agent.ssh"
    [ -S "$_gpg" ] && export SSH_AUTH_SOCK="$_gpg" && return 0
    # 5. systemd standard ssh-agent socket
    local _systemd="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/ssh-agent.socket"
    [ -S "$_systemd" ] && export SSH_AUTH_SOCK="$_systemd" && return 0
    # 6. Fanatics bastion glob
    local _fb; _fb=$(ls -t "$HOME/.ssh/agent"/s.*.agent.* 2>/dev/null | head -1)
    [ -n "$_fb" ] && [ -S "$_fb" ] && export SSH_AUTH_SOCK="$_fb" && return 0
    return 1  # No agent found
}
```

**Headless context gap:** In headless environments where `~/.zshrc` is not sourced, `SSH_AUTH_SOCK` may be unset even though 1Password is running. The wrapper script must re-run the detection logic (above) before attempting SSH operations. If no agent is found, the wrapper should skip the SSH fallback and let git fail with the original HTTPS error (better than hanging on SSH key passphrase prompts).

**Validate the agent is usable:** After detecting a socket, optionally verify with `ssh-add -l` (0 or 1 exit code means agent is live; exit code 2 means socket exists but agent is not responding). Keep this validation cheap — skip if latency budget is tight.

**systemd environment.d:** Tyler's exports note "environment.d/ssh-agent.conf handles the systemd user instance." This suggests there is or should be a `~/.config/environment.d/ssh-agent.conf` that exports `SSH_AUTH_SOCK` with a fixed socket path for systemd user units. This is the correct pattern; the wrapper should not need to handle this case separately if it is configured correctly.

References:
- [1Password SSH Agent socket paths](https://developer.1password.com/docs/ssh/agent/config/)
- [Systemd user session SSH_AUTH_SOCK — Fedora Discussion](https://discussion.fedoraproject.org/t/setting-ssh-auth-sock-in-systemd-user-unit-file/72693)
- [Baeldung: SSH-Agent as Systemd Unit](https://www.baeldung.com/linux/ssh-agent-systemd-unit-configure)

---

## Recommended Architecture

Based on the research above, the recommended approach is:

**A transparent git wrapper script at `~/.local/bin/git`** (placed before `/usr/bin/git` in PATH via dotfiles), with the following logic:

1. **Parse the git subcommand** to determine if it is a network operation (`clone`, `fetch`, `push`, `pull`, `remote update`, `ls-remote`). Non-network subcommands pass through immediately with zero overhead.

2. **Extract the target hostname** from arguments (for `clone`) or from `git -C <repo> remote get-url <remote>` (for `fetch`/`push`/`pull`).

3. **If hostname is HTTPS:**
   a. Check auth cache: `~/.cache/git-ssh-fallback/<encoded-host>` with 5-minute TTL.
   b. If cache miss: run `gh auth status --hostname <host>` (for github.com / GHE hosts) or skip (for non-GitHub hosts).
   c. If auth check fails or cache indicates "unauthenticated": detect SSH agent (reuse existing exports logic), then inject `GIT_CONFIG_COUNT` / `GIT_CONFIG_KEY_0` / `GIT_CONFIG_VALUE_0` for `url.<ssh-equivalent>.insteadOf=https://<host>/`.
   d. If auth is good: pass through.

4. **Exec the real git** (hard-coded path: `/usr/bin/git` on macOS, `$(PATH_without_wrapper) which git` discovered at install time). Pass all original args and the (possibly augmented) environment.

5. **Reactive safety net:** For any network operation where the HTTPS URL was not rewritten (either because gh is authenticated or because the host is unknown), if git exits with code 128 and stderr contains known auth failure strings AND `GIT_TERMINAL_PROMPT=0` was set, re-run with SSH URL injection.

6. **Logging:** If `GIT_SSH_FALLBACK_DEBUG=1` is set, emit debug lines to stderr prefixed with `[git-ssh-fallback]`.

**Dotfiles integration:** The wrapper script is installed at `~/.local/bin/git` by `install.sh`. `~/.local/bin` is already first in PATH (or should be added there). The script is self-contained with no runtime dependencies beyond `sh`, `git`, and optionally `gh`.

**No .gitconfig changes needed.** The existing credential helper chain is preserved. The wrapper operates entirely in the environment layer, not the config layer.

---

## Open Questions for Planning Phase

1. Should the wrapper handle `git` aliases that are network operations? (e.g., `git sync` alias that calls `fetch + rebase`)
2. For reactive detection, which exact stderr strings are authoritative across GitHub, GitLab, Bitbucket, and self-hosted Gitea?
3. How should the SSH URL be constructed for non-standard ports or paths? (`https://gitlab.com/org/repo` → `git@gitlab.com:org/repo` is standard; self-hosted may differ)
4. Does the 5-minute auth cache TTL need to be configurable? (Useful for CI where a token may expire mid-run)
5. Should the wrapper also handle `git credential approve/reject` passthrough without modification?
