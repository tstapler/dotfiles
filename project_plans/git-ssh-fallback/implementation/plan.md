# Implementation Plan: git-ssh-fallback

Feature: POSIX shell git wrapper that transparently falls back from HTTPS to SSH when gh is not authenticated for a host
Date: 2026-06-24
Status: Ready for implementation
ADRs: ADR-002-git-wrapper-over-credential-helper.md, ADR-003-gh-auth-token-over-auth-status.md

---

## Domain Glossary

`RealGit` | The actual git binary on disk (e.g., `/usr/bin/git`), resolved at wrapper startup by scanning PATH and skipping the wrapper's own directory. | newtype (path string)
`WrapperScript` | The POSIX shell script at `stapler-scripts/git-ssh-fallback` deployed as `~/.local/bin/git` by cfgcaddy. | identity
`NetworkSubcommand` | A git subcommand that contacts a remote (clone, fetch, pull, push, remote update, ls-remote, submodule). | sum type / whitelist
`RemoteHost` | The hostname extracted from an HTTPS remote URL (e.g., `github.com`, `gitlab.com`). | newtype (string, no port)
`AuthCache` | A file at `~/.cache/git-ssh-fallback/<host-hash>.auth` whose mtime signals the last successful auth check; TTL 5 minutes. | value object
`SshUrl` | A valid SSH remote URL in either SCP form (`git@HOST:ORG/REPO.git`) or `ssh://` form for non-standard ports. | newtype (string)
`HttpsUrl` | An HTTPS remote URL of the form `https://[creds@]HOST[:PORT]/PATH[.git]`. | newtype (string)
`RecursionGuard` | The environment variable `GIT_SSH_FALLBACK_ACTIVE=1`; when set, the wrapper immediately exec's `RealGit` without any logic. | boolean env var
`GhAuthResult` | Outcome of `gh auth token --hostname HOST`: `authenticated` (exit 0) or `unauthenticated` (exit non-zero). | sum type
`SshAgent` | A live SSH authentication agent reachable via `SSH_AUTH_SOCK`; may be 1Password, GPG agent, or a standard ssh-agent. | value object
`FallbackWarning` | The stderr message emitted when HTTPS falls back to SSH: `warning: falling back to SSH (gh not authenticated for HOST)`. | identity
`DebugTrace` | Structured stderr lines with `[git-ssh-fallback]` prefix, emitted when `GIT_SSH_FALLBACK_DEBUG=1` or `GIT_TRACE` is set. | log category
`ConfigInjection` | The set of `GIT_CONFIG_COUNT` + `GIT_CONFIG_KEY_n` + `GIT_CONFIG_VALUE_n` env vars that inject a per-invocation `url.insteadOf` rewrite without mutating `.gitconfig`. | value object

---

## Pattern Decisions

### Architecture Alternative Exploration (Step 0.5)

Three distinct high-level approaches were evaluated before committing:

**Approach A — Static `url.insteadOf` in .gitconfig**
Strength: Zero runtime cost, no wrapper, works everywhere.
Weakness: Unconditional — permanently bypasses `gh auth git-credential` and breaks all token-based HTTPS tooling (Cargo, Go modules, gh itself).
Decision: Rejected.

**Approach B — Post-hoc retry (let git fail, parse stderr, retry via SSH)**
Strength: No false positives — only activates after a confirmed failure; works for any HTTPS host without knowing about gh.
Weakness: Requires capturing and buffering stderr which breaks streaming progress output; double git invocation on failure path; stderr error strings differ across git versions and hosts.
Decision: Rejected.

**Approach C — Pre-flight `gh auth token` check + ConfigInjection (chosen)**
Strength: Single git invocation on both paths; gh check is fast (52ms unauthenticated); no global config mutation; transparent to all callers.
Weakness: Adds one `gh` subprocess for HTTPS network operations (mitigated by AuthCache).
Decision: Selected.

| Component | PoEAA Pattern | GoF Pattern | Type-Driven Design |
|-----------|---------------|-------------|-------------------|
| WrapperScript overall | Transaction Script (linear, no domain objects) | — | RecursionGuard as boolean env var not int |
| URL rewriting logic | — | Strategy (SCP vs ssh:// format based on port presence) | HttpsUrl / SshUrl as newtypes prevent accidental raw-string usage |
| Auth check + caching | — | Null Object (if gh absent, treat as unauthenticated gracefully) | GhAuthResult as sum type: Authenticated \| Unauthenticated \| GhNotFound |
| SSH agent detection | — | Chain of Responsibility (1Password → GPG → ~/.ssh/agent fallback chain) | SshAgent as value object requiring both path + socket liveness check |
| ConfigInjection | — | Builder (construct GIT_CONFIG_KEY_n env vars) | Reject approach if GIT_CONFIG_COUNT would overflow existing env (defensive) |

**Alternative Rejected: Reactive path for all hosts** — would require capturing stderr for every HTTPS git invocation, breaking streaming output for large clone/fetch operations. Proactive check with AuthCache is the right tradeoff.

**Alternative Rejected: Shell function in .zshrc** — does not cover IDE subprocess invocations, Claude Code subagents, or systemd user sessions; PATH-prepend script covers all invocation paths.

---

## Migration Plan

No schema or data changes. The wrapper is additive:
- `stapler-scripts/git-ssh-fallback` is a new file; existing scripts are unchanged.
- `.cfgcaddy.yml` gets one new link rule to deploy the wrapper as `~/.local/bin/git`.
- `.gitconfig` gets no permanent changes (the credential helper chain is untouched).

Existing machines: unaffected until they run `cfgcaddy link` after pulling dotfiles.
Rollback: remove `~/.local/bin/git` symlink; delete AuthCache directory.

---

## Observability Plan

Logs: All wrapper output goes to stderr. In default mode: `warning:` lines only when fallback triggers. In debug mode (`GIT_SSH_FALLBACK_DEBUG=1` or `GIT_TRACE` set): `[git-ssh-fallback]` prefixed lines showing auth check result, URL transform, and exec command.

Metrics: None (personal tool, no telemetry).

Alerts: None.

Debug escalation path: `GIT_SSH_FALLBACK_DEBUG=1 git push` → phase-by-phase trace on stderr.

---

## Risk Control

Feature flag: Not required — the wrapper is a PATH-prepend; removing `~/.local/bin/git` returns to vanilla git with zero config changes.

Rollback procedure:
1. `rm ~/.local/bin/git` — immediately restores vanilla git behavior.
2. Optionally `rm -rf ~/.cache/git-ssh-fallback/` — clears cached auth state.

Staged rollout: Personal dotfiles; single user. No rollout staging needed.

Critical risk mitigations built into implementation:
- `RecursionGuard`: `GIT_SSH_FALLBACK_ACTIVE=1` detected at top of script → immediate exec of `RealGit`.
- AuthCache with 5-minute TTL prevents gh Keychain contention on rapid sequential operations.
- `GIT_SSH_COMMAND="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new"` prevents headless hangs.
- SSH agent detection mirrors `exports.sh` probe sequence; fail-fast with diagnostic if no agent found.
- Strip embedded credentials from `HttpsUrl` before constructing `SshUrl`.

---

## Unresolved Questions

- Should `GIT_SSH_FALLBACK_QUIET=1` suppress even the `warning:` fallback line? (Defer; not required for initial implementation.)
- Should `GH_MANAGED_HOSTS` be read from a gitconfig section instead of an env var? (Defer; env var is sufficient for personal dotfiles scope.)

## Known Limitations (P1 Pre-mortem Items — documented, not blocking)

**P1-1: `timeout 1 gh auth token` exit 124 treated as unauthenticated.**
If the macOS Keychain is locked or contended, `gh` will time out and the wrapper will fall back to SSH even when the user has a valid token. This is an intentional design choice: when we cannot confirm auth within 1 second, SSH is the safer fallback. Users who experience this unexpectedly can re-run `gh auth status` to diagnose, or set `GIT_SSH_FALLBACK_DEBUG=1` to see the exit code. The AuthCache will absorb subsequent calls once a non-timeout result is written.

**P1-3: Non-gh-managed host SSH path assumes SSH keys are provisioned.**
Epic 2.4 proactively rewrites to SSH for any non-gh-managed host when a live SSH agent is present. If the user has an SSH agent but no key for the target host (e.g., a corporate Gitea with PAT-only auth), the SSH attempt will fail with `Permission denied (publickey)` instead of the original HTTPS auth prompt. This is consistent with the requirements constraint "SSH keys for target hosts must already be configured." Users on HTTPS-only corporate hosts should add those hostnames to the `GH_MANAGED_HOSTS` env var to opt them out of the proactive SSH path.

**P1-4: `git clone --recurse-submodules` multiplies SSH agent liveness probe.**
Each submodule invocation runs `_timeout 1 ssh-add -l`. For repos with many submodules this adds up to 1 × N seconds of overhead on cache miss. Mitigation: run `git-ssh-fallback --self-test` or any single git operation first to warm the AuthCache before recursive clone. Documented as a known limitation in Story 3.3.1.

**P1-5: macOS ships without a `timeout` binary by default.**
The `_timeout()` POSIX wrapper function (Task 1.1.1d) handles this transparently, but the POSIX fallback uses a background-process kill that is slightly less precise than GNU `timeout`. Users who want exact behavior can install coreutils: `brew install coreutils`. The POSIX fallback is correct for all use cases in this tool (1s probes).

**P1-6: Authenticated-path SLO is < 500ms; fallback-path SLO is < 1.5s.**
The performance SLO is split by path: on the authenticated path (HTTPS proceeds), the gh auth check adds ~52ms per host per 5-minute window (cache hit = 0ms). On the fallback path, the SSH agent probe adds up to 1s (liveness `_timeout 1 ssh-add -l`) for a worst-case total of ~1.05s — this is acceptable since the operation would have failed anyway without SSH fallback. See requirements.md for the full SLO definition.

---

## Dependency Visualization

```
cfgcaddy link
    └── stapler-scripts/git-ssh-fallback → ~/.local/bin/git
            │
            ├── PATH lookup: RealGit (/usr/bin/git or Homebrew git)
            │
            ├── NetworkSubcommand check (whitelist)
            │       └── non-network → exec RealGit immediately
            │
            ├── RemoteHost extraction
            │       ├── clone: parse URL from $@ args
            │       └── fetch/push/pull: RealGit remote get-url <remote>
            │
            ├── GhAuthResult check
            │       ├── AuthCache hit (mtime < 5min) → Authenticated
            │       └── cache miss → gh auth token --hostname HOST
            │               ├── exit 0 → write AuthCache, proceed HTTPS
            │               └── exit !=0 → SshAgent probe → ConfigInjection
            │
            ├── SshAgent detection (1Password → GPG → ~/.ssh/agent)
            │       └── no agent → error + hint, exit 1 (do not hang)
            │
            ├── ConfigInjection (GIT_CONFIG_COUNT/KEY/VALUE env vars)
            │       └── url."git@HOST:".insteadOf = "https://HOST/"
            │
            └── exec RealGit $@ (with augmented env if fallback)
```

---

## Phase 1: Core Wrapper Script

### Epic 1.1: Recursive-safe RealGit resolution and no-op passthrough

Goal: The wrapper exists as a deployable script that finds and execs the real git binary correctly, with a recursion guard, without breaking any existing git behavior.

#### Story 1.1.1: WrapperScript skeleton with RecursionGuard and RealGit resolution

As a developer, I want the git wrapper to safely exec the real git binary (with no added logic) so that it can be deployed immediately without breaking anything.

Acceptance Criteria:
- The script uses `#!/usr/bin/env sh` and is POSIX-compliant (no bash-isms).
- Given `GIT_SSH_FALLBACK_ACTIVE=1` is set in the environment, When `git status` is run, Then the wrapper immediately execs `RealGit` without printing any debug output.
- Given the wrapper is at `~/.local/bin/git` and the real git is at `/usr/bin/git`, When `git --version` is run, Then the output is the real git's version string (no recursion, no infinite loop).
- Given `GIT_SSH_FALLBACK_DEBUG=1` is set, When any git command runs, Then each wrapper decision step emits a `[git-ssh-fallback]` prefixed line to stderr.
- Files: `stapler-scripts/git-ssh-fallback`

##### Task 1.1.1a: Create the WrapperScript file with shebang, RecursionGuard, and RealGit probe (~3 min)
- Create `stapler-scripts/git-ssh-fallback` with `#!/usr/bin/env sh` and `set -euf`.
- At top: check `GIT_SSH_FALLBACK_ACTIVE`; if set, `exec "$REAL_GIT" "$@"`.
- Implement `_find_real_git()`: iterate `$PATH` directories, skip the directory containing `$0`, return the first `git` executable found. Fall back to `/usr/bin/git`.
- Set `REAL_GIT` via `_find_real_git`.
- Files: `stapler-scripts/git-ssh-fallback`

##### Task 1.1.1b: Implement `_log()` debug emission function (~2 min)
- `_log()`: emits `[git-ssh-fallback] $*` to stderr only when `GIT_SSH_FALLBACK_DEBUG` is non-empty or `GIT_TRACE` is non-empty.
- Add `_warn()`: always emits `warning: $*` to stderr (for FallbackWarning in default mode).
- Files: `stapler-scripts/git-ssh-fallback`

##### Task 1.1.1c: Make script executable and validate no-op passthrough manually (~2 min)
- `chmod +x stapler-scripts/git-ssh-fallback`
- Manually test: `GIT_SSH_FALLBACK_ACTIVE=1 stapler-scripts/git-ssh-fallback --version` exits cleanly.
- Manually test: `stapler-scripts/git-ssh-fallback status` works in any repo without recursion.
- Files: `stapler-scripts/git-ssh-fallback`

##### Task 1.1.1d: Add `_timeout()` POSIX wrapper and `|| true` guards for `set -euf` optional-failure paths (~3 min)
- **`_timeout()` function**: `timeout` is absent on macOS by default (requires `brew install coreutils`). Implement a `_timeout()` wrapper: use `command -v timeout >/dev/null 2>&1 && timeout "$@"` when available; otherwise fall back to a POSIX background-process kill: `( sleep "$1" & SLEEP_PID=$!; shift; "$@" & CMD_PID=$!; wait "$CMD_PID"; STATUS=$?; kill "$SLEEP_PID" 2>/dev/null; exit "$STATUS" )`. All `timeout 1 …` calls in the script MUST use `_timeout 1 …` instead of the bare `timeout` binary.
- **`|| true` guards (C1)**: Under `set -euf`, any optional-failure path that can return non-zero outside of an `if`/`&&`/`||` context will abort the script silently. Required guards:
  - Task 2.1.1a's `find "$cache_file" -mmin -5 2>/dev/null | grep -q .` — used as `if` condition, which is safe; document this explicitly so the pattern is not accidentally changed to an assignment.
  - Task 1.3.1b's `"$REAL_GIT" remote get-url "$remote" 2>/dev/null` — must be assigned as `url=$( "$REAL_GIT" remote get-url "$remote" 2>/dev/null ) || url=""` so an unknown remote does not abort the script.
  - Task 2.2.1a's `_timeout 1 ssh-add -l` — exit codes 0 and 1 are both "agent alive"; only exit 2 is stale socket. Use `_timeout 1 ssh-add -l >/dev/null 2>&1; ssh_add_status=$?` (capture without triggering `set -e`) rather than guarding with `|| true` (which obscures the exit-2 stale-socket case).
- Files: `stapler-scripts/git-ssh-fallback`

---

### Epic 1.2: NetworkSubcommand detection

Goal: The wrapper passes local git operations through immediately (zero overhead) and only activates auth-check logic for operations that contact a remote.

#### Story 1.2.1: Classify git subcommand as network or local

As a developer running `git status` or `git log`, I want zero added latency from the wrapper so that daily local git operations are not slowed down.

Acceptance Criteria:
- Given a git invocation of `git status`, When the wrapper runs, Then it execs `RealGit` without invoking `gh` or any auth logic.
- Given a git invocation of `git fetch origin`, When the wrapper runs, Then it proceeds to the auth-check phase.
- Given `git clone https://github.com/owner/repo`, When the wrapper runs, Then it proceeds to the auth-check phase.
- Given `git -C /some/path fetch`, When the wrapper runs (git flags before subcommand), Then it correctly identifies `fetch` as a NetworkSubcommand.
- Files: `stapler-scripts/git-ssh-fallback`

##### Task 1.2.1a: Implement NetworkSubcommand whitelist and subcommand extraction (~3 min)
- Define `NETWORK_SUBCOMMANDS="clone fetch pull push remote ls-remote submodule"`.
- Implement `_extract_subcommand()`: skip leading flags (`-C`, `--git-dir`, etc.) to find the first non-flag argument (the subcommand).
- Implement `_is_network_op()`: check if extracted subcommand is in the whitelist.
- If not a network op: `export GIT_SSH_FALLBACK_ACTIVE=1; exec "$REAL_GIT" "$@"`.
- Files: `stapler-scripts/git-ssh-fallback`

---

### Epic 1.3: RemoteHost extraction

Goal: Reliably determine which hostname the git operation is targeting, for both `clone` (URL in args) and `fetch`/`push`/`pull` (URL in remote config).

#### Story 1.3.1: Extract RemoteHost from git arguments or remote config

As the wrapper logic, I need to know which host to check auth for so that only the relevant host's auth state drives the fallback decision.

Acceptance Criteria:
- Given `git clone https://github.com/owner/repo.git`, When `_extract_host()` is called, Then it returns `github.com`.
- Given `git push origin main` in a repo with remote `origin = https://gitlab.com/org/proj`, When `_extract_host()` is called, Then it returns `gitlab.com`.
- Given `git fetch` (no remote specified) in a repo with remote `origin = https://github.com/owner/repo`, When `_extract_host()` is called, Then it returns `github.com`.
- Given `git fetch` in a repo with remote `origin = git@github.com:owner/repo`, When `_extract_host()` is called, Then it returns the empty string (already SSH; no fallback needed), and the wrapper passes through.
- Files: `stapler-scripts/git-ssh-fallback`

##### Task 1.3.1a: Implement `_extract_host()` for clone subcommand (~3 min)
- For `clone`: scan `$@` for the first argument that starts with `https://`; extract host via `${url#https://}` then `${host%%/*}`.
- Strip any embedded credentials (`user:pass@host` → `host`) via `${host##*@}`.
- If URL starts with `git@` or `ssh://`: return empty string (already SSH).
- Files: `stapler-scripts/git-ssh-fallback`

##### Task 1.3.1b: Implement `_extract_host()` for fetch/push/pull subcommands (~3 min)
- For non-clone network ops: determine remote name (first positional arg after subcommand, or `origin` as default).
- Call `"$REAL_GIT" remote get-url "$remote" 2>/dev/null` to get the URL.
- Apply same host extraction and SSH-already check as Task 1.3.1a.
- If remote get-url fails (not in a git repo, no such remote): return empty string.
- Files: `stapler-scripts/git-ssh-fallback`

---

## Phase 2: Auth Detection and SSH Fallback Logic

### Epic 2.1: GhAuthResult check with AuthCache

Goal: Determine whether gh is authenticated for the detected host, using a per-host file cache to avoid spawning gh on every git operation.

#### Story 2.1.1: Auth check with 5-minute file cache

As the wrapper, I need to know if gh has a valid token for the host so that I can decide whether to inject SSH rewriting, without calling gh more than once per 5 minutes per host.

Acceptance Criteria:
- Given a valid `AuthCache` file at `~/.cache/git-ssh-fallback/github.com.auth` with mtime less than 5 minutes ago, When `_check_auth()` is called for `github.com`, Then it returns `authenticated` without spawning a `gh` subprocess.
- Given no AuthCache file or mtime older than 5 minutes, When `_check_auth()` is called for `github.com` and `gh auth token --hostname github.com` exits 0, Then the AuthCache file is written/updated and `authenticated` is returned.
- Given `gh` is not in `$PATH`, When `_check_auth()` is called, Then it returns `unauthenticated` gracefully (no error exit from the wrapper itself).
- Given `gh auth token --hostname gitlab.com` exits non-zero, When `_check_auth()` is called for `gitlab.com`, Then it returns `unauthenticated` (no AuthCache write on failure).
- Files: `stapler-scripts/git-ssh-fallback`

##### Task 2.1.1a: Implement `_check_auth()` with AuthCache read (~4 min)
- Cache dir: `~/.cache/git-ssh-fallback/`. Create if absent with `mkdir -p`.
- Cache file name: `${host}.auth` (alphanumeric hostname is safe as filename; no hash needed for typical hostnames).
- TTL check using `find`: `find "$cache_file" -mmin -5 2>/dev/null | grep -q .` → cached authenticated.
- Files: `stapler-scripts/git-ssh-fallback`

##### Task 2.1.1b: Implement `_check_auth()` gh invocation with timeout and cache write (~3 min)
- If cache miss: `timeout 1 gh auth token --hostname "$host" >/dev/null 2>&1`
- Exit 0 → `touch "$cache_file"`, return `authenticated`.
- Exit 124 (timeout — macOS Keychain locked/contended, cli/cli#13317) → `_log "gh auth check timed out for $host, assuming authenticated"`, return `authenticated` (do NOT trigger fallback; HTTPS is the safer assumption when auth state is unknown).
- Exit non-zero (not 0, not 124) → return `unauthenticated` (do not write cache).
- If `command -v gh >/dev/null 2>&1` is false → return `unauthenticated` (gh absent).
- Files: `stapler-scripts/git-ssh-fallback`

---

### Epic 2.2: SshAgent probe before SSH fallback

Goal: Verify an SSH agent is available before attempting SSH, to fail fast with a clear diagnostic rather than hanging on passphrase prompts or key-not-found errors.

#### Story 2.2.1: Detect SshAgent with priority chain from exports.sh

As the wrapper, I need to confirm a live SSH agent exists before initiating SSH fallback so that headless contexts fail fast with a clear error instead of hanging.

Acceptance Criteria:
- Given `SSH_AUTH_SOCK` points to a live socket, When `_detect_ssh_agent()` is called, Then it returns success (0) without probing other paths.
- Given `SSH_AUTH_SOCK` is unset but `~/.1password/agent.sock` is a live socket, When `_detect_ssh_agent()` is called, Then it sets `SSH_AUTH_SOCK` to the 1Password path and returns success.
- Given no agent socket is found on any probe path, When `_detect_ssh_agent()` is called, Then it returns failure (1), and the wrapper emits `error: SSH fallback skipped: no SSH agent found (SSH_AUTH_SOCK not set)` plus a hint line, then execs `RealGit` with the original HTTPS URL (letting git fail with its own auth error rather than hanging).
- Files: `stapler-scripts/git-ssh-fallback`

##### Task 2.2.1a: Implement `_detect_ssh_agent()` mirroring exports.sh probe order with liveness check (~5 min)
- Priority 1: `$SSH_AUTH_SOCK` already set and `[ -S "$SSH_AUTH_SOCK" ]`.
- Priority 2: `$HOME/.1password/agent.sock`.
- Priority 3: `$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock` (macOS native path).
- Priority 4: `${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/gnupg/S.gpg-agent.ssh`.
- Priority 5: `${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/ssh-agent.socket`.
- Priority 6: `$(ls -t "$HOME/.ssh/agent"/s.*.agent.* 2>/dev/null | head -1)`.
- **After finding a socket path that passes `[ -S ... ]`: validate agent liveness with `timeout 1 ssh-add -l >/dev/null 2>&1`; exit codes 0 (keys loaded) and 1 (no keys) both mean alive; exit code 2 means stale socket — skip this candidate and continue probing. Using 1s timeout (not 3s) to bound overhead for `git clone --recurse-submodules` which invokes the wrapper once per submodule.**
- On success: export `SSH_AUTH_SOCK`. On failure: return 1.
- Files: `stapler-scripts/git-ssh-fallback`

---

### Epic 2.3: ConfigInjection and SSH URL rewriting

Goal: Inject per-invocation `url.insteadOf` via environment variables so that the real git uses SSH for the target host without any mutation to `.gitconfig`.

#### Story 2.3.1: Construct and apply ConfigInjection for unauthenticated host

As the wrapper, when gh is not authenticated for a host, I need to inject SSH URL rewriting for that single git invocation so that git transparently uses SSH without changing persistent config.

Acceptance Criteria:
- Given `RemoteHost = github.com` and `GhAuthResult = unauthenticated`, When the fallback activates, Then `GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=url.git@github.com:.insteadOf`, `GIT_CONFIG_VALUE_0=https://github.com/` are set before exec'ing `RealGit`.
- Given `RemoteHost = gitlab.com` and `GhAuthResult = unauthenticated`, When the fallback activates, Then the ConfigInjection uses `git@gitlab.com:` and `https://gitlab.com/`.
- Given the `HttpsUrl` contains embedded credentials (`https://user:token@github.com/org/repo`), When constructing the ConfigInjection value, Then the `insteadOf` prefix is `https://github.com/` (credentials stripped from the match prefix).
- Given the fallback activates for `github.com`, When the operation runs, Then stderr contains `warning: falling back to SSH (gh not authenticated for github.com)`.
- Given `GIT_SSH_FALLBACK_DEBUG=1`, When fallback activates, Then stderr contains `[git-ssh-fallback] rewriting https://github.com/ → git@github.com:` before exec.
- Files: `stapler-scripts/git-ssh-fallback`

##### Task 2.3.1a: Implement ConfigInjection env var construction (~3 min)
- `_inject_ssh_config()` receives `$host`.
- Sets: `GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0="url.git@${host}:.insteadOf"`, `GIT_CONFIG_VALUE_0="https://${host}/"`.
- Export all three.
- Files: `stapler-scripts/git-ssh-fallback`

##### Task 2.3.1b: Implement GIT_SSH_COMMAND for BatchMode headless safety (~2 min)
- Before exec in fallback path: `export GIT_SSH_COMMAND="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"`.
- This prevents interactive SSH prompts in headless contexts and enforces a connection timeout.
- Files: `stapler-scripts/git-ssh-fallback`

##### Task 2.3.1c: Emit FallbackWarning and DebugTrace, then exec RealGit (~2 min)
- Call `_warn "falling back to SSH (gh not authenticated for $host)"`.
- Call `_log "rewriting https://$host/ → git@$host:"`.
- Call `_log "exec: $REAL_GIT $*"`.
- Set `GIT_SSH_FALLBACK_ACTIVE=1` then `exec "$REAL_GIT" "$@"`.
- Files: `stapler-scripts/git-ssh-fallback`

---

### Epic 2.4: Reactive safety net for non-gh hosts

Goal: For HTTPS hosts where `gh auth token` is not applicable (non-GitHub forges, self-hosted Gitea, etc.), catch auth failure after the fact and retry via SSH — ensuring the "works for any HTTPS git host" success metric is met.

#### Story 2.4.1: Post-hoc SSH retry for non-gh-managed hosts

As a developer pushing to a self-hosted Gitea instance over HTTPS, I want git-ssh-fallback to retry via SSH when HTTPS auth fails even though gh has no token concept for that host, so that SSH fallback is genuinely host-agnostic.

Acceptance Criteria:
- Given `RemoteHost = git.internal.example.com` (not gh-managed) and a live SSH agent exists, When the wrapper runs, Then it proactively emits `warning: falling back to SSH (gh not authenticated for git.internal.example.com)` and execs `RealGit` with SSH ConfigInjection — no HTTPS attempt, no stderr buffering.
- Given `RemoteHost = git.internal.example.com` and no live SSH agent, When the wrapper runs, Then it execs `RealGit` with the original HTTPS args (no warning, no modification — let git fail naturally if HTTPS also fails).
- Given `RemoteHost = github.com` (managed by gh), When the wrapper runs, Then the proactive `gh auth token` path applies and the non-gh path is NOT taken.
- Given `GIT_SSH_FALLBACK_DEBUG=1` and a non-gh host with live agent, When the wrapper runs, Then stderr emits `[git-ssh-fallback] non-gh host, SSH agent available, using SSH directly`.
- Files: `stapler-scripts/git-ssh-fallback`

##### Task 2.4.1a: Implement `_is_gh_managed_host()` to gate proactive vs reactive path (~3 min)
- Maintain a `GH_MANAGED_HOSTS` list: `"github.com gist.github.com"` plus any `GIT_SSH_FALLBACK_GH_HOSTS` env var (space-separated, user-extensible).
- `_is_gh_managed_host "$host"`: returns 0 if host is in the list, 1 otherwise.
- **Exact-match enforcement (N3)**: Implementation MUST use a POSIX-safe `for`-loop with `[ "$host" = "$candidate" ]` — never `grep`, `case`-with-glob, or `eval`. Prevents glob metacharacters in `GIT_SSH_FALLBACK_GH_HOSTS` (e.g., `*.com`) from producing false positives or enabling injection.
- **GHES documentation**: Add a comment block above `GH_MANAGED_HOSTS` in the script explaining that GitHub Enterprise Server (GHES) instances use custom hostnames (e.g., `git.company.com`) and must be manually enrolled via `GIT_SSH_FALLBACK_GH_HOSTS=git.company.com` to receive the `gh auth token` proactive check; without enrollment they take the non-gh proactive-SSH path.
- Files: `stapler-scripts/git-ssh-fallback`

##### Task 2.4.1b: Proactive SSH path for non-gh-managed hosts with known_hosts gate (~4 min)
- For non-gh-managed hosts: skip `gh auth token` check entirely (gh cannot assess these hosts).
- Instead: (1) probe `_detect_ssh_agent()` — if no live agent, fall through to vanilla HTTPS. (2) Check if the host is in `~/.ssh/known_hosts` via `ssh-keygen -F "$host" >/dev/null 2>&1` — exit 0 means known, exit 1 means unknown.
- If agent alive AND host is in known_hosts: proactively emit FallbackWarning, inject ConfigInjection, exec `RealGit "$@"` with SSH rewriting — no HTTPS attempt, no stderr capture.
- If no live agent OR host not in known_hosts: fall through to `exec "$REAL_GIT" "$@"` without any rewriting (let git try HTTPS normally).
- Rationale: `known_hosts` presence is the minimal positive signal that SSH has been used for this host before; it prevents breaking HTTPS-PAT-based forges where the user has credentials but no SSH key.
- Files: `stapler-scripts/git-ssh-fallback`

---

## Phase 3: Deployment and Integration

### Epic 3.1: cfgcaddy deployment

Goal: The WrapperScript is distributed via dotfiles and deployed to `~/.local/bin/git` on every machine that runs `cfgcaddy link`.

#### Story 3.1.1: cfgcaddy link rule deploys wrapper as ~/.local/bin/git

As Tyler bootstrapping a new machine, I want `cfgcaddy link` to deploy the git wrapper to `~/.local/bin/git` automatically so that SSH fallback works immediately after dotfiles setup.

Acceptance Criteria:
- Given `.cfgcaddy.yml` has the new link rule for `stapler-scripts/git-ssh-fallback` → `.local/bin/git`, When `cfgcaddy link` runs on a fresh machine, Then `~/.local/bin/git` is a symlink pointing to `dotfiles/stapler-scripts/git-ssh-fallback`.
- Given `~/.local/bin` is the first entry in `$PATH` (confirmed from `.shell/exports.sh`), When `which git` runs in any shell, Then `~/.local/bin/git` is returned before `/usr/bin/git`.
- Given `git --version` runs via the deployed symlink, Then the real git's version string is returned (wrapper passthrough verified).
- Files: `/Users/tyler.stapler/dotfiles/.cfgcaddy.yml`

##### Task 3.1.1a: Add cfgcaddy link rule for the git wrapper (~3 min)
- **First**: run `cfgcaddy link --dry-run 2>&1 | grep -i "stapler\|git"` to confirm no existing ignore rule (e.g., a `*stapler*` glob pattern) would suppress the symlink. If suppressed, add an explicit include override before proceeding.
- Add to `.cfgcaddy.yml` under `links:`:
  ```yaml
  - src: stapler-scripts/git-ssh-fallback
    dest: .local/bin/git
    os: "Linux Darwin"
  ```
- This deploys a symlink at `~/.local/bin/git` → `~/dotfiles/stapler-scripts/git-ssh-fallback`.
- Files: `/Users/tyler.stapler/dotfiles/.cfgcaddy.yml`

---

### Epic 3.2: Smoke tests

Goal: Manually verifiable test cases that confirm the wrapper works end-to-end for the three critical scenarios: HTTPS pass-through when authenticated, SSH fallback when not authenticated, and no-op for local commands.

#### Story 3.2.1: Validate all three execution paths

As Tyler, I want to confirm the wrapper behaves correctly on my machine before committing so that I don't break git operations across all my repos.

Acceptance Criteria:
- Given the wrapper is deployed at `~/.local/bin/git` and `gh` is authenticated for `github.com`, When `git fetch` is run in any GitHub repo, Then git uses HTTPS (no `warning:` line on stderr, no ConfigInjection env vars set externally).
- Given a test where `GH_NO_AUTH=1` triggers the "not authenticated" path (or by temporarily removing the auth cache), When `git fetch` is run against an HTTPS GitHub remote, Then stderr contains `warning: falling back to SSH (gh not authenticated for github.com)` and the fetch succeeds via SSH.
- Given `git status` is run in any repo, When the wrapper handles it, Then no `gh` subprocess is spawned and no overhead is measurable.
- Given `GIT_SSH_FALLBACK_DEBUG=1 git fetch`, When the wrapper runs in fallback mode, Then stderr shows all `[git-ssh-fallback]` trace lines including: host checked, auth verdict, URL rewrite, exec command.
- Files: `stapler-scripts/git-ssh-fallback` (verify behavior, no code changes expected)

##### Task 3.2.1a: Write a self-test function in the script (~4 min)
- Add a `--self-test` flag that the wrapper intercepts before any git logic.
- `git-ssh-fallback --self-test`: runs three internal assertions:
  1. `_find_real_git` returns a path that is not `$0`.
  2. `_extract_subcommand "fetch" "origin"` returns `fetch`.
  3. `_is_network_op "status"` returns 1 (false).
- Print `[git-ssh-fallback] self-test: PASS` on success or `FAIL` with which assertion failed.
- Files: `stapler-scripts/git-ssh-fallback`

---

### Epic 3.3: Documentation and observability

Goal: The wrapper is discoverable and debuggable by Tyler when something goes wrong, both on first install and in headless contexts.

#### Story 3.3.1: First-run detection and debug hint

As Tyler on a new machine, I want the wrapper to announce itself on first activation so that I know it is installed and working.

Acceptance Criteria:
- Given `GIT_SSH_FALLBACK_DEBUG=1 git status`, When the wrapper runs, Then the first `[git-ssh-fallback]` line identifies the script path and RealGit path.
- Given the SSH fallback fails (no SSH agent found), When the wrapper logs the error, Then stderr includes `hint: Run with GIT_SSH_FALLBACK_DEBUG=1 for detailed diagnostic output`.
- Given the SSH fallback fails (no SSH agent), When the wrapper exits, Then it execs `RealGit` with the original args (letting git's own error surface) rather than exiting with a wrapper-specific error code.
- Files: `stapler-scripts/git-ssh-fallback`

##### Task 3.3.1a: Add identity header to DebugTrace and error hint footer (~2 min)
- At top of debug path: `_log "wrapper: $0 | real git: $REAL_GIT"`.
- In `_detect_ssh_agent` failure path: `_warn "SSH fallback skipped: no SSH agent found"` then `printf 'hint: %s\n' "Run with GIT_SSH_FALLBACK_DEBUG=1 for detailed diagnostic output" >&2`.
- Files: `stapler-scripts/git-ssh-fallback`

---

## Complete File Inventory

| File | Action | Phase |
|------|--------|-------|
| `stapler-scripts/git-ssh-fallback` | Create (new WrapperScript) | 1–3 |
| `/Users/tyler.stapler/dotfiles/.cfgcaddy.yml` | Edit (add link rule) | 3 |
| `docs/adr/ADR-002-git-wrapper-over-credential-helper.md` | Create | — |
| `docs/adr/ADR-003-gh-auth-token-over-auth-status.md` | Create | — |

Files explicitly NOT changed:
- `/Users/tyler.stapler/dotfiles/.gitconfig` — credential helper chain preserved as-is.
- `/Users/tyler.stapler/dotfiles/.shell/exports.sh` — PATH already has `~/.local/bin` first.
- Any Ansible playbook — cfgcaddy handles deployment; no playbook change needed.
