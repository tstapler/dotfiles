# Feature Research: git-ssh-fallback

**Date**: 2026-06-24
**Phase**: Research (SDD Phase 2)
**Research scope**: Prior art, URL conversion edge cases, failure modes, unstated needs, existing credential helpers

---

## 1. Prior Art — Tools and Scripts That Do HTTPS→SSH Fallback

### 1.1 Static `url.insteadOf` (Most Common Approach)

The most widely documented approach is a one-time static rewrite in `.gitconfig`:

```ini
[url "git@github.com:"]
    insteadOf = https://github.com/
```

This is unconditional — every HTTPS request to github.com is rewritten to SSH before the operation. Resources that cover this:

- [Meziantou's blog — `url.insteadOf`](https://www.meziantou.net/using-git-insteadof-to-automatically-replace-https-urls-with-ssh.htm)
- [Jamie Tanna — HTTPS/SSH URL rewriting](https://www.jvt.me/posts/2019/03/20/git-rewrite-url-https-ssh/)
- [Peter Kolloch — SSH locally, HTTPS in CI](https://blog.eigenvalue.net/git-ssh-insteadof-https/)

**Verdict for this project**: The static approach is well-trodden but explicitly ruled out in requirements — it breaks `gh` itself and GitHub Actions HTTPS token workflows. It also gives no conditionality on auth state.

### 1.2 `pushInsteadOf` — Push-Only SSH

```ini
[url "ssh://git@github.com/"]
    pushInsteadOf = https://github.com/
```

Applies SSH only for `git push`, leaving fetch/clone over HTTPS. Narrower than the full-fallback goal but shows the git URL rewriting API can be targeted per-operation.

### 1.3 Environment-Gated `url.insteadOf` (CI vs. local)

Peter Kolloch's writeup describes using a gitconfig `includeIf` on an environment variable to switch between SSH (local dev) and HTTPS (CI). This is the closest prior art to the conditional approach:

```ini
[includeIf "env:CI=true"]
    path = ~/.gitconfig-ci   # HTTPS overrides
```

Tyler's `.gitconfig` already uses `includeIf "gitdir:~/WorkProjects/"` for identity switching, so this pattern is known. The gap: `includeIf` cannot branch on `gh auth status` — it is static at config parse time.

### 1.4 Earthly Build Tool — Protocol Fallback Chain

The [Earthly build tool](https://docs.earthly.dev/docs/guides/auth) implements SSH→HTTPS fallback automatically for private dependency clones during builds. It:
1. Tries SSH (port 22) first
2. Falls back to HTTPS if SSH is unreachable
3. Refuses to fall back to plain HTTP (security)

This is the closest tool-level analog to what this project needs, but in the opposite direction (SSH-first, not HTTPS-first). Key insight: protocol fallback on network/auth failure is a solved pattern in build tooling.

### 1.5 APM (Agent Package Manager) — Multi-Protocol Retry

Microsoft's APM retries across protocols on the same port: `ssh://host:7999` retries as `https://host:7999/...` if SSH is unreachable. Demonstrates that per-host port preservation is expected in non-standard-port scenarios.

### 1.6 `GIT_SSH_COMMAND` / `GIT_SSH` Wrapper Pattern

Git provides `GIT_SSH_COMMAND` and `GIT_SSH` env vars for injecting a custom SSH binary. This pattern is used for per-repo key injection but does not address the HTTPS→SSH protocol switch itself. It would only apply after the URL has already been rewritten to SSH.

### 1.7 `GIT_EXEC_PATH` Shadow Directory

By setting `GIT_EXEC_PATH` to a directory of wrapper scripts that shadow real git sub-programs (`git-remote-https`, etc.), you can intercept git operations before they execute. This is an advanced approach that would allow detecting a credential failure at the transport level and retrying with SSH. It is not documented as a mainstream pattern and carries maintenance risk (must track git's internal binary naming).

### 1.8 `GIT_ASKPASS` Hook

`GIT_ASKPASS` replaces the interactive password prompt. A script here could detect the auth failure scenario and signal a fallback, but it cannot change the protocol mid-operation — it can only provide credentials or fail. Not a viable path for protocol switching.

### 1.9 Git Credential Manager (GCM)

[GCM](https://github.com/git-ecosystem/git-credential-manager) is cross-platform and supports MFA, OAuth, and many hosts. However:
- GCM operates **exclusively over HTTPS** — no SSH fallback mechanism
- macOS `osxkeychain` similarly stores HTTPS credentials only
- Neither tool has a documented SSH fallback path

**Verdict**: Existing credential helpers (GCM, osxkeychain, `gh auth git-credential`) are dead ends for protocol switching. The [git credential protocol](https://git-scm.com/docs/gitcredentials) only returns `username`/`password` fields; it cannot redirect an operation to a different URL scheme. This confirms the requirements doc's assessment.

### 1.10 Shell Wrapper Approach (Most Viable Prior Art)

The synthesized recommended approach from multiple sources is:
1. Place a `git` wrapper script early in `$PATH`
2. Pass all args to real git, capturing stderr
3. If stderr matches `fatal: Authentication failed` or similar, rewrite remote URL to SSH and retry
4. This is fire-and-forget: no daemon, no persistent state

`gh auth status` exits with code 1 when auth is expired/missing, making it usable as a pre-flight check:

```sh
if command -v gh >/dev/null && gh auth status --hostname "$HOST" >/dev/null 2>&1; then
    # HTTPS is safe — gh has a token
else
    # Rewrite to SSH
fi
```

The pre-flight approach (check before the operation) is cleaner than retry-on-failure because it avoids a double git invocation in the failure path.

---

## 2. URL Conversion Edge Cases

Converting `https://HOST/PATH` → SSH URL is not trivially a sed one-liner. Known edge cases:

### 2.1 SCP-style vs `ssh://` URL Style

Two valid SSH URL formats exist:
- **SCP-style**: `git@github.com:org/repo.git`
- **ssh:// scheme**: `ssh://git@github.com/org/repo.git`

The SCP colon syntax (`git@host:path`) is legacy and cannot encode a port number. For any non-standard port, `ssh://` with explicit port is required.

**Decision needed**: Use `ssh://` style universally (portable across ports) or SCP style (more widely seen in docs).

### 2.2 `.git` Suffix

HTTPS URLs may or may not include `.git`. GitHub, GitLab, and Gitea all accept both. The SSH URL should preserve the suffix as-is rather than strip or add it.

### 2.3 GitLab Subgroups (Deep Nesting)

GitLab supports unlimited subgroup nesting: `https://gitlab.com/org/sub1/sub2/repo`. The `url.insteadOf` prefix-rewrite approach handles this automatically since it replaces only the prefix. A regex-based URL converter also handles it naturally as long as it captures the full path after the hostname.

However, SCP-style SSH for deep paths (`git@gitlab.com:org/sub1/sub2/repo`) may confuse tools that naively parse on the colon. Using `ssh://git@gitlab.com/org/sub1/sub2/repo` avoids this.

### 2.4 Non-Standard Ports

If HTTPS is on port 8443 (`https://mygitea.internal:8443/org/repo`), the SSH port is likely also non-standard but may be different (e.g., 2222). There is no way to know the SSH port from the HTTPS URL alone without per-host configuration. A `~/.config/git-ssh-fallback/hosts.yaml` (or similar) could map HTTPS port → SSH port per host.

The SSH-over-HTTPS-port pattern (GitHub: `ssh.github.com:443`, GitLab: `altssh.gitlab.com:443`) requires host-specific knowledge that cannot be inferred from URL structure alone.

### 2.5 Query Strings and Fragments

HTTPS git URLs may theoretically carry query strings (e.g., `?ref=main`). In practice, `git clone`/`fetch`/`push` do not use query strings, but URL parsers should be robust against them. Strip or ignore.

### 2.6 `https://` URLs with Embedded Credentials

URLs of the form `https://user:token@host/repo` should have credentials stripped before SSH rewriting. Passing credentials in the SSH URL is meaningless and could leak them.

### 2.7 Port Preservation on Standard Ports

`https://host:443/path` should be treated identically to `https://host/path`. Stripping the `:443` is correct for HTTPS before conversion.

### 2.8 Summary Conversion Table

| HTTPS URL | Converted SSH URL | Notes |
|---|---|---|
| `https://github.com/org/repo` | `git@github.com:org/repo` | Standard |
| `https://github.com/org/repo.git` | `git@github.com:org/repo.git` | Preserve `.git` |
| `https://gitlab.com/org/sub/repo` | `ssh://git@gitlab.com/org/sub/repo` | Subgroup — use ssh:// to avoid colon ambiguity |
| `https://host:8443/org/repo` | `ssh://git@host:PORT/org/repo` | Port unknown — needs host config |
| `https://user:token@host/repo` | `git@host:org/repo` | Strip embedded creds |
| `https://host/repo` (root-level) | `git@host:repo` | No org, unlikely but valid |

---

## 3. Failure Modes

### 3.1 Network Partition Mid-Operation

If the SSH connection drops mid-`git clone`, the partial clone leaves a `.git` directory. On retry, `git clone` will refuse to overwrite an existing directory. The wrapper must not interfere with git's normal mid-operation error handling — pass errors through unchanged and let the user deal with cleanup.

### 3.2 SSH Timeout in Headless Context

`ssh -T git@host` hangs if:
- No `SSH_AUTH_SOCK` (agent not running)
- SSH key requires passphrase and there's no agent or `SSH_ASKPASS`
- `StrictHostKeyChecking=yes` and the host key is unknown

Mitigations:
- Wrap SSH connectivity check with a short timeout: `ssh -o ConnectTimeout=5 -T git@host 2>/dev/null`
- Use `StrictHostKeyChecking=accept-new` in headless mode (or as a configurable option)
- Fail fast if `SSH_AUTH_SOCK` is unset and no identity file is specified

### 3.3 Wrong Key for the Host

If the SSH key registered for a host is wrong (expired, revoked, wrong key), SSH will fail with `Permission denied (publickey)`. The wrapper should detect this and not loop — pass the error through and do not re-attempt HTTPS (which already failed).

### 3.4 `gh auth status` Subprocess Cost

`gh auth status` spawns a subprocess and may do a network call to validate the token. Target: < 500ms per the SLO. If `gh` is not in `$PATH` (e.g., minimal headless environment), the check must be skipped gracefully. A per-host token cache file (e.g., `~/.cache/git-ssh-fallback/auth-status.json`) could skip the subprocess for ~30 seconds, at the cost of stale-state risk.

### 3.5 SSH Host Key Fingerprint Prompt

On a truly new host, SSH interactive mode prompts: `The authenticity of host '...' can't be established. Are you sure...?`. In headless contexts this hangs indefinitely. The fallback wrapper must either:
- Pre-accept with `StrictHostKeyChecking=accept-new` (security tradeoff: TOFU)
- Pre-check `ssh -o BatchMode=yes ...` and surface a clear error if the host key is missing
- Require that SSH known_hosts is pre-populated (bootstrap step)

### 3.6 Partial `gh auth` (Some Hosts, Not Others)

The user has `gh auth git-credential` configured for `github.com` (both in `[credential "https://github.com"]` and the global fallback). A non-GitHub host like `gitlab.com` or a self-hosted Gitea instance would also hit the global `gh auth git-credential` helper and fail silently if `gh` has no token for that host. The wrapper must detect per-host failures, not just a global "gh is authenticated" state. `gh auth status --hostname $HOST` supports this.

### 3.7 IDE / Tool Subprocess Invocations

IDEs (IntelliJ, VS Code), Claude Code subagents, and other tooling invoke `git` as a subprocess. A `PATH`-prepended wrapper script must be idempotent and must pass through all flags/arguments faithfully to avoid breaking tool-specific git behaviors.

### 3.8 Recursive Invocation

A wrapper script that calls `git` by name would invoke itself recursively if its directory appears in `$PATH` before the real git. It must invoke the real git binary by absolute path (e.g., `/usr/bin/git` or `$(which -a git | grep -v wrapper | head -1)`).

---

## 4. Unstated Needs

### 4.1 Per-Host Allow-List / Block-List

The current requirements say "any HTTPS git host," but in practice Tyler works with:
- `github.com` (personal + fanatics org)
- Possibly `gitlab.com`
- Self-hosted hosts (unknown)

A per-host configuration (allow SSH fallback for these hosts, not for others) would prevent accidental SSH-fallback to a host where SSH is not set up, avoiding a confusing `Permission denied (publickey)` error instead of the original HTTPS auth error.

### 4.2 Audit / Debug Log

The requirements mention a `GIT_SSH_FALLBACK_DEBUG=1` flag. Implicit need: when something goes wrong in a headless context (CI-like script), having a timestamped log file at `~/.local/share/git-ssh-fallback/fallback.log` (not stderr) would enable post-hoc diagnosis without re-running interactively.

### 4.3 Cache for `gh auth status` Result

To hit the < 500ms SLO, the auth-check result should be cached briefly per-host. A simple file at `~/.cache/git-ssh-fallback/$HOST.auth` containing the last-known result with a mtime-based TTL (e.g., 60s) avoids subprocess overhead on rapid sequential git operations (e.g., `git fetch && git pull`).

### 4.4 SSH Agent Availability Check

Before falling back to SSH, the wrapper should verify that SSH auth would actually work (agent running with a key, or identity file exists). A failed SSH fallback that leaves the user with an opaque `Permission denied` is worse UX than the original auth error.

### 4.5 Dotfiles Bootstrap Integration

The requirements say "distributable via dotfiles." Implicit need: the wrapper must be wired up automatically when `bootstrap/run.sh` or the Makefile installs dotfiles on a new machine. This likely means adding a `stapler-scripts/git-ssh-fallback` entry to cfgcaddy and a gitconfig stanza that gets appended by bootstrap.

### 4.6 Work Machine Identity Preservation

Tyler's `.gitconfig` uses `[includeIf "gitdir:~/WorkProjects/"]` to overlay a work identity. The SSH fallback must not break this: when falling back to SSH on a work host, the SSH key chosen should be the work key, not the personal one. This is handled by `~/.ssh/config` host blocks rather than the fallback script itself, but it's a testing requirement.

---

## 5. Existing Credential Helpers — SSH Fallback Inventory

| Tool | Platform | SSH Fallback? | Notes |
|---|---|---|---|
| `gh auth git-credential` | macOS/Linux | No | HTTPS only; no protocol switching |
| `git-credential-manager` (GCM) | Cross-platform | No | HTTPS only; uses system keyring |
| `osxkeychain` | macOS | No | HTTPS only; stores username/password |
| `libsecret` / GNOME Keyring | Linux | No | HTTPS only |
| `git-credential-cache` | Unix | No | In-memory HTTPS cred cache |
| Earthly build tool | Cross-platform | Partial (SSH-first) | SSH→HTTPS fallback for build deps only |
| APM (GitHub Packages) | Cross-platform | Partial (per-port) | Protocol retry on same port |

**Finding**: No general-purpose credential helper implements HTTPS→SSH fallback. This is a gap in the ecosystem and validates that this project must implement a novel solution.

---

## 6. Implementation Approaches — Comparative Analysis

### Option A: Pre-flight `gh auth status` + `url.insteadOf` Injection

1. Before any git operation, check `gh auth status --hostname $HOST`
2. If auth is missing: inject a session-scoped `url.insteadOf` rewrite via `GIT_CONFIG_GLOBAL` or `-c` flag
3. Re-invoke git with the override

**Pros**: Simple, no git binary replacement  
**Cons**: Must intercept every `git` invocation; requires wrapper script regardless  
**`url.insteadOf` via `-c`**: `git -c url."git@$HOST:".insteadOf="https://$HOST/" $@` — this is per-invocation and does not pollute global config

### Option B: Retry on Auth Failure (Post-hoc)

1. Run git normally, capture stderr
2. Detect `fatal: Authentication failed` pattern
3. Rewrite remote URL to SSH, retry

**Pros**: No pre-flight cost; HTTPS is attempted first (correct for auth'd environments)  
**Cons**: Double git invocation on every failure; stderr buffering may cause display issues; some operations (clone) create side effects before failing

### Option C: Compiled Go Binary

A small Go binary that wraps `os/exec.Command` and implements the auth-check + retry logic. More portable across shells and IDEs than a shell script; can be statically linked.

**Pros**: No shell dependency; handles arg passing and env cleanly; easy to test  
**Cons**: Requires compilation step in bootstrap; harder to read/modify casually

### Option D: Git Alias (Limited)

```ini
[alias]
    sfetch = "!git-ssh-fallback fetch"
```

Only works for explicit alias invocations. Claude Code subagents and IDEs calling `git fetch` directly would not use the alias.

**Verdict**: Option A (pre-flight + `-c url.insteadOf`) implemented as a shell wrapper on `$PATH` is the most viable path. It avoids global config mutation, is debuggable, and requires only a POSIX shell. Option C (Go binary) is the upgrade path if shell limitations (arg handling, portability) become problems.

---

## 7. Key References

- [Git credential helper documentation](https://git-scm.com/docs/gitcredentials)
- [Meziantou — `url.insteadOf`](https://www.meziantou.net/using-git-insteadof-to-automatically-replace-https-urls-with-ssh.htm)
- [Jamie Tanna — HTTPS/SSH URL rewriting](https://www.jvt.me/posts/2019/03/20/git-rewrite-url-https-ssh/)
- [Peter Kolloch — SSH locally, HTTPS in CI](https://blog.eigenvalue.net/git-ssh-insteadof-https/)
- [GitHub Docs — SSH over HTTPS port](https://docs.github.com/en/authentication/troubleshooting-ssh/using-ssh-over-the-https-port)
- [gh auth status manual](https://cli.github.com/manual/gh_auth_status)
- [gh auth setup-git manual](https://cli.github.com/manual/gh_auth_setup-git)
- [GCM — git-credential-manager](https://github.com/git-ecosystem/git-credential-manager)
- [Earthly auth guide](https://docs.earthly.dev/docs/guides/auth)
- [Git environment variables](https://git-scm.com/book/en/v2/Git-Internals-Environment-Variables)
