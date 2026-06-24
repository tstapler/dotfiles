# git-ssh-fallback: Known Pitfalls and Risks

**Date:** 2026-06-24
**Phase:** Research
**Focus:** Implementation risks for a git wrapper / credential helper that transparently falls back from HTTPS to SSH

---

## 1. Recursive Invocation Risk

### The Problem
If a shell function named `git` (or a shim on `PATH`) calls the real `git` internally, it will call itself unless it explicitly uses the full binary path (e.g., `/usr/bin/git`). This produces infinite recursion and a process fork bomb.

### How Existing Wrappers Handle It
- **`hub`** (the original git wrapper) aliases `git` to `hub` in shell configs, but internally calls `git` via the full resolved path. The convention is to resolve the "real" binary path at wrapper initialization time using `$(which -a git | grep -v "$0" | head -1)` or equivalent.
- **`mise` shims** explicitly strip their own shim directory from `PATH` before delegating. They also document that credential commands must use `mise which` to find the resolved binary path rather than relying on the shim.
- **`gh` credential helper** registers `credential.https://github.com.helper` (host-specific), which takes precedence over the global `credential.helper`. A wrapper that overrides the global helper while `gh`'s host-specific helper remains can still trigger a layered call chain: wrapper → git → gh credential helper → git (recursion if git resolves to the wrapper).

### Mitigations
- Store the absolute path to the real `git` binary at wrapper load time: `GIT_REAL=$(command -v git)` evaluated *before* the wrapper function shadows `git`.
- Use `#!/usr/bin/env -S` or hardcode `/usr/bin/git` inside the wrapper body — never `git`.
- In the SSH fallback path, unset any environment variable that might cause re-entry (`GIT_SSH_FALLBACK_ACTIVE=1` guard).

### Risk Level: **Critical** — unguarded recursion causes process exhaustion.

---

## 2. IDE and Editor Integration

### The Problem
VSCode, JetBrains IDEs, and similar tools spawn `git` as a subprocess — but they do *not* necessarily respect `PATH` the same way an interactive terminal does. macOS does not source `~/.zprofile` for non-login shells spawned by GUI apps, so `PATH` modifications made in shell config files are often invisible to IDEs.

### VSCode
- VSCode has a `git.path` setting in `settings.json` that can point to an **absolute path**, bypassing `PATH` entirely.
- Extensions like **GitLens** have their own separate path resolution and may ignore the core `git.path` setting, calling `git` from `PATH` lookup.
- A wrapper prepended to `PATH` will be silently ignored if `git.path` is already hardcoded to `/usr/bin/git`.
- Workaround: Point `git.path` explicitly to the wrapper script.

### JetBrains (IntelliJ, GoLand, etc.)
- JetBrains IDEs resolve git via an absolute path configured in **Settings → Version Control → Git → Path to Git executable**.
- `PATH` prepend alone will not intercept JetBrains git calls.
- Background fetch operations (periodic `git fetch`) will bypass the wrapper unless the IDE's git path is updated.

### Claude Code Subagents
- Claude Code subagent processes inherit the shell environment from the parent process. If Claude Code is launched from a terminal where `PATH` includes the wrapper, subagents will use the wrapper. If launched from a launchd service or Spotlight, `PATH` may not include the wrapper directory.
- This is particularly relevant for the headless/CI-like environment use case described in the requirements.

### Risk Level: **High** — PATH-only wrappers provide incomplete coverage; IDE integration requires explicit configuration per tool.

---

## 3. URL Rewriting Edge Cases

### git submodules and `url.insteadOf`

A persistent, well-documented bug: **`url.*.insteadOf` rules in the super-repo config are not consulted by the `git clone` invoked during `git submodule update`**. The submodule clone runs in an isolated context and only sees global `~/.gitconfig` — it does not inherit the super-repo's local config where `insteadOf` rules may live.

A patch was proposed to the git mailing list to fix this via a new `rewrite-url` subcommand of `git config`, but it has not been merged into mainline git as of 2026.

**Implication:** A global `url.https://github.com/.insteadOf` in `~/.gitconfig` will affect submodule clones (good), but any repo-local or worktree-specific `insteadOf` rule will not propagate to submodule operations.

### git-lfs inside submodules
Even with a global `url.insteadOf`, git-lfs does not honor the rewrite when operating inside a submodule. The `lfs.transfer.enablehrefrewrite` setting does not reliably fix this. This is an open bug (git-lfs#5665).

### `submodule.recurse=true` Side Effects
Setting `submodule.recurse=true` globally causes unexpected failures in unrelated commands: `git grep --untracked` will fatal with `--untracked not supported with --recurse-submodules`. This affects any automation scripts that run git commands on repos with this config set.

### Sparse Checkouts
Sparse checkouts use a cone or pattern mode to limit the working tree. URL rewriting via `insteadOf` should be transparent to sparse checkouts since the rewrite happens before the transport layer. However, if the wrapper inspects URLs to decide whether to apply fallback logic, it must handle the case where only a partial set of paths is fetched — the remote URL is the same regardless of sparse cone configuration.

### `git clone --recurse-submodules`
This flag causes git to clone all submodules after the main clone. Each submodule clone is a separate git process, and each will trigger the wrapper independently. With an SSH fallback wrapper, this means:
- Each submodule HTTPS clone may independently trigger the `gh auth status` preflight check.
- If the check has a 500ms latency, a repo with 20 submodules adds 10 seconds of overhead at minimum.
- If SSH fallback is triggered, the SSH host key prompt can hang the entire recursive clone in non-interactive environments.

### Risk Level: **High** — submodule URL propagation is a known git limitation; git-lfs interaction is a confirmed bug.

---

## 4. SSH Agent Reliability

### `SSH_AUTH_SOCK` Not Set or Stale
Git uses `SSH_AUTH_SOCK` to find the SSH agent socket. In headless/non-GUI environments this variable is frequently absent or stale:
- **systemd user sessions**: `SSH_AUTH_SOCK` is only populated if `ssh-agent` is started as a systemd user service and the socket path is exported. This is not the default on macOS.
- **Claude Code subagents**: Subagents inherit `SSH_AUTH_SOCK` from the Claude Code parent process. If the parent was launched without a live SSH agent (e.g., via launchd rather than a terminal), `SSH_AUTH_SOCK` will be empty.
- **Stale sockets**: The SSH agent may have exited but the socket file still exists. `ssh-add -l` against a stale socket returns "Could not open a connection to your authentication agent" but does *not* error with a clear exit code — scripts may misinterpret this.

### 1Password SSH Agent
The 1Password SSH agent requires the **full desktop application to be running**. The `op` CLI alone does not expose the agent socket in headless environments. If Tyler uses 1Password as the SSH agent on macOS, the fallback will silently fail in any headless context where the desktop app is not active.

Additionally, the 1Password agent socket (`~/.1password/agent.sock`) can conflict with the macOS system SSH agent (`/private/tmp/com.apple.launchd.*/Listeners`). If `SSH_AUTH_SOCK` is set to the system agent but keys only exist in 1Password's agent, SSH connections will fail with "Permission denied (publickey)".

### Timeout Behavior
When `SSH_AUTH_SOCK` points to a non-responsive socket, SSH will hang indefinitely unless `ConnectTimeout` or `ServerAliveInterval` is configured in `~/.ssh/config`. An unresponsive SSH agent during a `git push` fallback will block the entire operation with no user-visible timeout.

### Mitigation
- Before SSH fallback, validate the agent: `ssh-add -l &>/dev/null` with a timeout (`timeout 3 ssh-add -l`).
- If agent is unavailable, fall back gracefully with an error message rather than hanging.
- Document that `~/.ssh/config` must include `IdentityFile` directives for target hosts so identity file-based auth works without an agent.

### Risk Level: **High** — headless environments are the primary failure scenario for this project, and SSH agent availability is not reliable in those contexts.

---

## 5. `gh auth status` Reliability

### Hard 3-Second Keychain Timeout
Since `gh` v2.31.0 (introduced in cli/cli#7580), all macOS Keychain reads are wrapped in a **hard 3-second timeout**. When the Keychain read fails or exceeds this timeout, `gh` treats the token as empty and sends unauthenticated requests (HTTP 401). This has two implications for the preflight check:

1. **False negatives**: `gh auth status` may report "not authenticated" when the user *is* authenticated but the Keychain is temporarily slow (e.g., during multi-agent workload contention).
2. **Silent failures**: The upstream bug `cli/cli#13317` (open as of 2026) means `gh api` silently falls back to unauthenticated rather than surfacing the Keychain error. `gh auth status` can return exit code 0 (appearing authenticated) while actual API calls fail with 401.

### Keychain Locked in Non-GUI Sessions
The macOS login Keychain is not unlocked in non-GUI (headless) sessions by default. Any process spawned by launchd (rather than a terminal login) will encounter a locked Keychain. This means:
- In systemd-like headless environments, `gh auth status` will always timeout/fail even if the user is authenticated in their GUI session.
- `security unlock-keychain` can manually unlock it but requires the user's macOS password.

### Latency Budget
The project spec targets < 500ms added latency. `gh auth status` itself has been observed to take 200–500ms on a warm system, and can spike to 3+ seconds under Keychain contention. The preflight check alone may blow the latency budget in adverse conditions.

### Alternative: Environment Variable Check
A more reliable and faster preflight: check `GH_TOKEN` or `GITHUB_TOKEN` environment variables first (zero latency), then check for `~/.config/gh/hosts.yml` existence and whether it contains a token (file stat, ~1ms), before falling back to `gh auth status` as a last resort.

### Risk Level: **Critical** — the preflight mechanism has confirmed reliability bugs, and its behavior differs between GUI and headless environments.

---

## 6. Security Risks: URL Rewriting and Credential Confusion

### The "Clone2Leak" / Confused Deputy Class
A URL rewriting wrapper sits between the user's intent and the transport layer. This creates a confused deputy risk: if the wrapper rewrites a URL from HTTPS to SSH, and the SSH target is different from what the user intended (e.g., due to a crafted or malformed remote URL), credentials or code can be exfiltrated.

Known CVEs in this space:
- **CVE-2025-23040** (GitHub Desktop, CVSS 6.6): Carriage return (`\r`) smuggling in remote URLs caused the credential helper to send credentials for `github.com` to an attacker-controlled host.
- **CVE-2024-53858** (GitHub CLI): Logic flaw in `tokenForHost` caused tokens to be sent to non-GitHub hosts classified as "enterprise."
- **CVE-2020-5260**: Newline injection in git credential helper protocol caused credential leaks to wrong hosts.

### Risk Specific to SSH Fallback
A `url.insteadOf` global rule that rewrites `https://github.com/` to `git@github.com:` affects **all operations on all repos**. If a user clones an internal repo at `https://github.com/attacker/repo`, the URL rewrite still applies — the intent was to fix auth, not validate the target.

A wrapper-script approach has more opportunity to apply targeting logic (only rewrite on auth failure) but a global `url.insteadOf` is a permanent, unconditional rewrite.

### Trust Model Recommendation
- Never apply URL rewrites based on pattern matching alone. Tie the rewrite to an explicit trigger (auth failure detected).
- Validate that the SSH equivalent host (derived from the HTTPS URL) is in the user's `~/.ssh/known_hosts` before redirecting. If it is not, refuse the fallback and surface an explicit error.
- Log all URL rewrites performed by the wrapper for auditability.
- Do not silently swallow authentication errors — surface them so the user can distinguish "SSH fallback succeeded" from "silently failed."

### Risk Level: **High** — URL rewriting wrappers have a documented history of credential exfiltration bugs; unconditional `url.insteadOf` is particularly dangerous.

---

## 7. Interaction with Git Hooks

### Environment Variable Leakage
When git runs client-side hooks (`pre-push`, `commit-msg`, `post-merge`, etc.), the hooks inherit the full git environment including `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, and any custom variables set by the wrapper. If a hook invokes `git` in a different repository (e.g., a submodule or a sibling repo), these environment variables will cause the hook's git calls to operate on the wrong repository.

The git documentation explicitly warns about this: hooks that invoke git in foreign repositories must unset these variables first using `unset $(git rev-parse --local-env-vars)`.

### Wrapper Interference with Hook Subprocess `git` Calls
If the wrapper sets a guard variable (e.g., `GIT_SSH_FALLBACK_ACTIVE=1`) to prevent recursion, hooks that invoke `git` directly will also be subject to that guard. Depending on the implementation, this could suppress the fallback for git operations triggered inside hooks — which may or may not be the desired behavior.

### Hook Script Bypassing
Hooks can be bypassed with `git commit --no-verify` or `git push --no-verify`. This is not a wrapper-specific risk but is worth noting: if the SSH fallback is implemented as a hook rather than a wrapper, it can be bypassed.

### `pre-push` and Auth Ordering
The `pre-push` hook runs *before* data is sent to the remote but *after* the remote connection is established. If the SSH fallback occurs at the transport layer (before the hook), the hook sees a successful push path. If the wrapper intercepts the entire `git push` command, the hook must be re-invoked by the wrapper, which duplicates hook logic and can trigger double-execution.

### Risk Level: **Medium** — hooks interact with the wrapper's environment variable state; careful scoping is required.

---

## 8. Concurrency: Parallel Git Operations

### Git's File-Based Locking
Git uses file-based locking (`.git/index.lock`, `.git/config.lock`, `.git/refs/<name>.lock`) to serialize modifications. When two git processes attempt to write the same ref simultaneously:
- The second process receives a fatal error: "Another git process seems to be running in this repository."
- Lock files from crashed processes are not automatically cleaned up.

### IDE Background Fetch vs. User Pull
IDEs (VSCode, JetBrains) periodically run `git fetch` in the background. If the user runs `git pull` at the same moment, both processes attempt to update refs under `.git/refs/remotes/`. The fetch may already hold a lock on a remote ref that the pull needs to update, causing the pull to fail.

With an SSH fallback wrapper, this scenario becomes more complex:
- Both the IDE background fetch and the user pull trigger the wrapper independently.
- If the preflight `gh auth status` check is being run by both, they may race on Keychain access (exacerbating the 3-second timeout issue above).
- If both fall back to SSH simultaneously, there is no coordination between the two SSH connections.

### Parallel `git clone --recurse-submodules`
As noted in section 3, each submodule clone is a separate process. With many submodules, multiple SSH connections will be established simultaneously. If SSH host key fingerprint prompts are required (new host, known_hosts not pre-populated), all parallel clone processes will hang waiting for input on stdin — in a non-interactive environment this is a silent deadlock.

### Mitigation
- Use `GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=10"` for SSH fallback operations. `BatchMode=yes` causes SSH to fail immediately rather than prompt for host key verification or passphrase.
- Document that `StrictHostKeyChecking=accept-new` (added in OpenSSH 7.6) provides a middle ground: accept unknown hosts automatically without prompting, but fail on mismatched known hosts.

### Risk Level: **Medium** — git's own locking handles the worst cases, but concurrent preflight checks and parallel submodule clones can cause cascading delays.

---

## Summary of Risk Ratings

| Risk Area | Severity | Primary Concern |
|---|---|---|
| Recursive invocation | Critical | Infinite self-call without full-path guard |
| `gh auth status` reliability | Critical | 3s Keychain timeout + silent unauthenticated fallback (open upstream bug) |
| SSH agent in headless env | High | `SSH_AUTH_SOCK` absent or stale; 1Password requires desktop app |
| URL rewriting security | High | Clone2Leak class CVEs; unconditional `insteadOf` affects all repos |
| IDE integration (PATH bypass) | High | IDEs use absolute path settings; `PATH` prepend insufficient |
| Submodule `url.insteadOf` | High | Known git limitation: repo-local rules not propagated to submodule clones |
| Git hooks env var leakage | Medium | `GIT_DIR` etc. inherited by hook subprocesses |
| Concurrent operations | Medium | IDE background fetch races with user pull; parallel submodule SSH hangs |

---

## References

- [mise: GitHub Tokens — recursive mise invocation prevention](https://mise.jdx.dev/dev-tools/github-tokens.html)
- [cli/cli#13317: gh api silently sends unauthenticated requests when keychain access fails](https://github.com/cli/cli/issues/13317)
- [claude-code#67055: gh auth status 5s timeout causes false "expired credentials" toasts](https://github.com/anthropics/claude-code/issues/67055)
- [git-lfs#5665: git lfs does not honor url.insteadOf inside submodules](https://github.com/git-lfs/git-lfs/issues/5665)
- [renovatebot/renovate#26153: submodule.recurse=true unintended side effects](https://github.com/renovatebot/renovate/discussions/26153)
- [GHSA-qm7j-c969-7j4q: malicious URLs may cause Git to send stored credentials to wrong server](https://github.com/git/git/security/advisories/GHSA-qm7j-c969-7j4q)
- [CVE-2024-53858: GitHub CLI leaks access tokens to arbitrary hosts](https://github.com/cli/cli/security/advisories)
- [The Hacker News: GitHub Desktop Vulnerability Risks Credential Leaks via Malicious Remote URLs (CVE-2025-23040)](https://thehackernews.com/2025/01/github-desktop-vulnerability-risks.html)
- [1Password: SSH agent requires desktop app in headless environments](https://www.1password.community/discussions/developers/how-do-i-use-the-ssh-agent-in-headless-linux/159260)
- [Git Concurrency in GitHub Desktop (async reader-writer lock pattern)](https://github.blog/2015-10-20-git-concurrency-in-github-desktop/)
- [VSCode git.path setting — absolute path bypasses PATH](https://bobbyhadz.com/blog/git-not-found-install-it-or-configure-it-in-vscode)
- [git patch series: Fix url.*.insteadOf for submodule URLs](https://git.vger.kernel.narkive.com/EpirFuhf/patch-0-5-fix-url-insteadof-for-submodule-urls)
- [git-scm.com: githooks — GIT_DIR leakage in foreign repo invocations](https://git-scm.com/docs/githooks)
- [Honnibal: Restricting Coding Agents' CLI GitHub Write Access (sudo-gated wrapper pattern)](https://honnibal.dev/blog/locking-down-gh)
