# Build vs. Buy: git-ssh-fallback

**Date:** 2026-06-24  
**Scope:** Automatic HTTPS→SSH fallback when `gh auth git-credential` is missing or expired

---

## Problem Restatement

Tyler's global `.gitconfig` uses `gh auth git-credential` as the credential helper for GitHub and all HTTPS hosts. When `gh` is unauthenticated (expired token, new machine, headless CI-like env), `git` operations over HTTPS fail. The goal is to detect that failure and transparently retry the same operation over SSH — no manual URL editing, no re-running the command.

**Constraint:** Tyler's `.gitconfig` already has:
```ini
[credential "https://github.com"]
    helper = 
    helper = !/opt/homebrew/bin/gh auth git-credential
[credential "https://gist.github.com"]
    helper = 
    helper = !/opt/homebrew/bin/gh auth git-credential
[credential]
    helper = !gh auth git-credential
```
Any solution must coexist with this without breaking the working case (when `gh` is authenticated).

---

## 1. Existing OSS Solutions

### 1a. Dedicated "HTTPS→SSH fallback" packages

**Verdict: Not recommended — nothing exists.**

No package named `git-credential-ssh-fallback` or similar exists on Homebrew, npm, cargo (crates.io), or pip. Searches across all four package registries returned zero hits for this exact use-case. The closest thing in name is `git-credential-manager` (Microsoft GCM), which is irrelevant (see §1b).

No popular dotfiles repos (mathiasbynens/dotfiles, holman/dotfiles, thoughtbot/dotfiles) implement this pattern. They either hardcode SSH via `url.insteadOf` (unconditional rewrite) or use HTTPS+token exclusively. None implement conditional fallback based on live auth status.

**Pros:** N/A  
**Cons:** Does not exist  

---

### 1b. Git Credential Manager (GCM) — `git-ecosystem/git-credential-manager`

The Microsoft-originated cross-platform credential manager. Available as `brew install --cask git-credential-manager`.

GCM explicitly says in its FAQ: *"GCM is only useful for HTTP(S)-based remotes. Git supports SSH out-of-the box so you shouldn't need to install anything else."* It has no SSH fallback capability whatsoever. It is a HTTPS credential storage layer, not a protocol router.

**Pros:** Well-maintained, cross-platform  
**Cons:** HTTPS-only, zero SSH awareness, would conflict with Tyler's existing `gh auth git-credential` setup  
**Verdict: Not recommended**

---

### 1c. git-credential-oauth

A cross-platform helper that performs OAuth browser flows for GitHub/GitLab/Bitbucket. Included in many Linux distros. Has `--device` flag for headless flows.

No SSH fallback. Like GCM, it operates entirely within the HTTPS credential plane.

**Pros:** Handles expired OAuth tokens gracefully via re-auth  
**Cons:** No SSH fallback, requires a browser or device flow, heavier than the problem requires  
**Verdict: Not recommended**

---

### 1d. pass / 1Password CLI git credential integration

- **pass** (`git-credential-pass`): A credential helper backed by the Unix `pass` password store. Pure credential storage, no protocol awareness.
- **1Password CLI** (`op run`): Can inject secrets into environment variables, including `GIT_ASKPASS` style, but does not implement SSH fallback.

**Pros:** Good credential hygiene  
**Cons:** Neither implements SSH fallback; both operate only within the HTTPS credential plane  
**Verdict: Not recommended**

---

### 1e. git-absorb, git-branchless, git-stack

These are Git workflow tools (restack, fix-up commits, branch management). They do not touch authentication or protocol selection. Not relevant.

**Verdict: Not recommended**

---

## 2. Partial Solutions to Compose

### 2a. `url.insteadOf` — Static unconditional HTTPS→SSH rewrite

The most common dotfiles pattern for "I want SSH everywhere":
```ini
[url "git@github.com:"]
    insteadOf = https://github.com/
```
This is unconditional: it rewrites HTTPS URLs to SSH for every operation, regardless of `gh` auth state. When Tyler is authenticated with `gh`, this bypasses the credential helper entirely (which is fine). When not authenticated, it also bypasses `gh` (which is the desired behavior).

**Critical limitation:** This is a static config entry. It cannot be conditioned on runtime auth state. It would permanently disable `gh auth git-credential` for GitHub, meaning token-based operations (e.g., `git fetch` from a machine with no SSH key) would also fail silently.

Additionally, Tyler already has `[hub] protocol = ssh` set in `.gitconfig`, showing partial SSH preference — but the HTTPS credential entries (`[credential "https://github.com"]`) exist precisely for the cases where SSH is not available.

**Pros:** Zero dependencies, works with vanilla git, dotfiles-distributable  
**Cons:** All-or-nothing — breaks `gh auth git-credential` entirely; cannot fall back, can only replace  
**Verdict: Viable only as an "always SSH" config, not a conditional fallback**

---

### 2b. `url.insteadOf` + `includeIf` composition

`includeIf` conditions currently support: `gitdir:`, `gitdir/i:`, `onbranch:`, `hasconfig:remote.*.url`, and `remote:<name>`. There is **no `ifenv:` or `ifcmd:` condition type**. Git has no built-in conditional to include a block "only if `gh auth status` returns 0."

This means there is no native `.gitconfig` mechanism to say "apply this `insteadOf` rewrite only when `gh` is not authenticated." The composition doesn't exist in git's config model.

**Verdict: Not viable as a conditional fallback**

---

### 2c. Custom credential helper wrapper script

Git's credential helper protocol supports a `quit=1` response to abort the entire credential chain. A custom shell script placed before `gh auth git-credential` in the helper chain can:
1. Check `gh auth status` (or `gh auth token`) as a gate
2. If `gh` is unauthenticated: output nothing and let git proceed (which causes auth failure) — OR redirect via a separate mechanism
3. If `gh` is authenticated: delegate to `gh auth git-credential`

**The gap:** A credential helper runs during `git credential fill` — it cannot redirect git to use SSH instead of HTTPS. The credential protocol has no "use SSH for this request" signal. A helper can only provide credentials or abort; it cannot tell git to change the transport protocol mid-operation.

The only way to transparently redirect to SSH is to change the remote URL before git makes its credential request. This means the URL rewrite must happen at a higher level (git config's `url.insteadOf`, a git wrapper, or a pre-hook).

**Verdict: Viable as a detection mechanism, but cannot complete the fallback without a higher-level URL rewrite mechanism**

---

### 2d. Shell wrapper for `git` (the "git-wrapper" pattern)

Create a shell function or script named `git` that:
1. Inspects whether the operation is network-bound (`clone`, `fetch`, `pull`, `push`, `remote update`)
2. Checks `gh auth status --active` to see if `gh` is authenticated
3. If unauthenticated: rewrites HTTPS URLs to SSH (`https://github.com/org/repo` → `git@github.com:org/repo`) via `GIT_CONFIG_PARAMETERS` or a temporary `--config` flag, then runs the real `git`
4. If authenticated: passes through unchanged

This is the only approach capable of both detecting the auth failure condition _and_ redirecting to SSH at the right layer (before git's credential protocol runs).

**Complexity of the URL transform:** The transform `https://HOST/ORG/REPO` → `git@HOST:ORG/REPO` is straightforward. A shell `sed` one-liner handles it reliably for the standard GitHub/GitLab pattern:
```bash
ssh_url=$(echo "$https_url" | sed 's|https://\([^/]*\)/\(.*\)|git@\1:\2|')
```
The `git-scm.com` native `url.insteadOf` mechanism achieves the same with zero parsing: `[url "git@github.com:"].insteadOf = https://github.com/`. There is no complex URL parsing library needed.

**Pros:** Full control, correct layer for intervention, composable with dotfiles  
**Cons:** Wrapping `git` is fragile — callers can bypass it with `/usr/bin/git`, PATH ordering matters, and it adds latency for all git operations (even local ones that don't need auth)  
**Verdict: Viable but requires careful implementation (see §4 below)**

---

### 2e. `GIT_CONFIG_PARAMETERS` env var injection

Git 2.31+ supports `GIT_CONFIG_PARAMETERS` to inject config key-value pairs for a single git process without modifying files. This would allow a wrapper to inject `url.insteadOf` dynamically:
```bash
GIT_CONFIG_PARAMETERS="'url.git@github.com:.insteadOf=https://github.com/'" git "$@"
```
This is cleaner than modifying `~/.gitconfig` at runtime. Available on both macOS (which ships git 2.39+ with Homebrew) and Linux.

**Verdict: The right mechanism for a git wrapper to inject SSH rewrites without touching config files**

---

## 3. SaaS / Managed Approaches

Not applicable. This is a local dotfiles configuration problem.

---

## 4. LLM-Generated Shell Script vs. Battle-Tested Library

### URL parsing complexity

The HTTPS→SSH transform for standard forge hosts (GitHub, GitLab, Bitbucket) is trivial:
- `https://github.com/org/repo` → `git@github.com:org/repo`
- `https://github.com/org/repo.git` → `git@github.com:org/repo.git`
- Pattern: strip `https://`, replace first `/` with `:`, prepend `git@`

One `sed` call handles all standard cases. No library needed.

For cross-host generalization (the stated requirement), the same pattern applies as long as the host supports SSH with `git@HOST:ORG/REPO` syntax, which GitHub, GitLab, and Bitbucket all do.

Edge cases to handle:
- Ports in URL: `https://HOST:PORT/ORG/REPO` (rare for public forges, common for self-hosted Gitea/Forgejo)
- Non-standard SSH usernames (some hosts use `hg@` or similar)
- Gist URLs: `https://gist.github.com/` (different SSH path format)

For the dotfiles use-case (macOS personal + Linux secondary, public forges), these edge cases are unlikely to matter.

### Verdict on build complexity

A purpose-built shell script is appropriate here. The logic is:
1. ~20 lines for `gh` auth detection (`gh auth status` exits non-zero when unauthenticated)
2. ~5 lines for URL transform (sed)
3. ~10 lines for git wrapper scaffolding

No external library is needed. The script is small enough that an LLM-generated first draft is fully auditable and maintainable.

---

## 5. Fork or Adapt

### Forkable candidates found

**None.** No existing shell script in popular dotfiles repos implements conditional HTTPS→SSH fallback based on live credential-helper status. The closest patterns found are:

1. **Static `url.insteadOf` blocks** (MoOx/setup, others) — unconditional SSH rewrite, no fallback logic
2. **`gh auth setup-git` pattern** (official gh CLI) — wires HTTPS+`gh` only, no SSH fallback
3. **Tyler's own `setup-github-ssh.sh`** in this dotfiles repo — sets up SSH host aliases for personal repos but doesn't implement runtime fallback

The static `url.insteadOf` pattern from MoOx/setup is conceptually related but architecturally different (always-SSH vs. fallback-to-SSH). It is not worth forking because the core mechanism (unconditional rewrite) is the wrong model.

---

## Summary & Recommendation

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Dedicated OSS package | Drop-in | Does not exist | Not recommended |
| Git Credential Manager | Well-maintained | HTTPS-only, no SSH | Not recommended |
| `url.insteadOf` (static) | Zero deps, simple | Breaks `gh` auth entirely — all-or-nothing | Viable only if always-SSH is acceptable |
| `url.insteadOf` + `includeIf` | Native git | No runtime condition support in git config | Not viable |
| Custom credential helper wrapper | Shell-native | Cannot redirect protocol, only detect | Partial solution only |
| `git` wrapper + `GIT_CONFIG_PARAMETERS` | Full control, correct layer, dotfiles-distributable | PATH fragility, latency on all git calls | **Recommended (build)** |

### Recommended approach: Build a thin `git` wrapper script

Place a script at `~/.local/bin/git` (or `~/bin/git`) that:
1. Checks if the operation is network-bound by inspecting `$1` (clone/fetch/pull/push/remote/submodule)
2. Runs `gh auth status >/dev/null 2>&1` to test auth (fast — reads cached token, no network call)
3. If unauthenticated: injects SSH rewrites via `GIT_CONFIG_PARAMETERS` for the configured hosts (initially `github.com`, generalized to others in `.gitconfig`) then execs real git
4. If authenticated: execs real git unchanged

The wrapper:
- Is distributable as a dotfiles symlink (`~/bin/git` → `dotfiles/bin/git`)
- Does not modify `~/.gitconfig`
- Coexists with `gh auth git-credential` (authentication plane is untouched when `gh` is working)
- Works for clone, fetch, push, pull (all network ops)
- Works cross-host (GitHub, GitLab, etc.) by parameterizing the SSH rewrite hosts in `.gitconfig` or a companion config file
- Works on macOS and Linux (POSIX shell + `gh` CLI)

**Estimated implementation: ~50 lines of POSIX shell.** No library dependencies. Fully auditable. Symlink-distributable. No homebrew formula, no cargo crate, no npm package.

---

## References

- [Git Credential Storage](https://git-scm.com/book/en/v2/Git-Tools-Credential-Storage)
- [gitcredentials documentation](https://git-scm.com/docs/gitcredentials)
- [Automatically Transforming Git URLs — Scott Lowe](https://blog.scottlowe.org/2023/12/11/automatically-transforming-git-urls/)
- [git-ecosystem/git-credential-manager FAQ](https://github.com/git-ecosystem/git-credential-manager/blob/main/docs/faq.md)
- [gh auth setup-git manual](https://cli.github.com/manual/gh_auth_setup-git)
- [Using gh as the credential helper per-OS — cli/cli discussion #9438](https://github.com/cli/cli/discussions/9438)
- [Configuring SSH for Personal and Work GitHub Accounts (Jan 2026)](https://awakecoding.com/posts/configuring-ssh-for-personal-and-work-github-accounts/)
