# Requirements: git-ssh-fallback

**Date**: 2026-06-24
**Type**: new service
**Complexity**: 3 — system design

## Problem Statement

When the `gh` CLI is not authenticated (expired token, new machine, headless/CI-like environment), `git fetch`/`push`/`clone` over HTTPS silently or noisily fails with an auth error. Tyler has `gh auth git-credential` set as the credential helper globally, so any HTTPS operation that reaches a host where `gh` has no token will fail. The user wants the same operation to succeed transparently via SSH fallback — no manual intervention, no remote URL editing.

## Baseline

Today: HTTPS git operations fail with an authentication error when `gh` is not configured for a host. The user must manually either run `gh auth login`, change the remote URL to SSH (`git remote set-url origin git@...`), or add a temporary `url.insteadOf` rewrite. This is friction-heavy and breaks non-interactively.

## Users / Consumers

- Tyler, on personal macOS machines (interactive shells)
- Tyler, on work machines in `~/WorkProjects/` (already has `.gitconfig.fbg` identity overlay)
- Tyler, in headless environments: systemd user sessions, Claude Code subagents, CI-like scripts

## Success Metrics

- HTTPS git operations that would have failed due to missing `gh` auth succeed via SSH fallback with zero manual intervention
- No change in behavior when `gh` is authenticated (HTTPS stays HTTPS)
- **Coverage bounds**: For gh-managed hosts (github.com, gist.github.com, user-defined via `GIT_SSH_FALLBACK_GH_HOSTS`): fallback is proactive via `gh auth token`. For other HTTPS hosts: fallback activates if the host is in `~/.ssh/known_hosts` and a live SSH agent is present; otherwise HTTPS is attempted unchanged.
- SSH fallback is observable (log line or debug flag) so failures are diagnosable
- **Security design decision (explicit)**: When `gh auth token --hostname HOST` times out (exit 124, macOS Keychain contention), the wrapper treats this as "assume authenticated" and does NOT trigger SSH fallback. Rationale: triggering fallback on ambiguous auth state is higher risk than letting HTTPS try and fail with git's own error. This decision is documented in ADR-003.

## Appetite

Medium (1–2 weeks)
*(Scope must fit the appetite. If it doesn't fit, cut scope — do not move the deadline.)*

## Constraints

- Must integrate with existing `.gitconfig` without breaking current `gh auth git-credential` setup
- Must work on macOS (primary) and Linux (secondary)
- SSH keys for target hosts must already be configured — the helper does not provision SSH keys
- Should be distributable via dotfiles (cfgcaddy-tracked) so it deploys on new machines via bootstrap

## Non-functional Requirements

- **Performance SLO**: On the authenticated path (cache miss + gh auth check), overhead must be < 500ms (~52ms measured). On the unauthenticated/fallback path, additional SSH agent probe latency is acceptable since the operation would have failed anyway; total fallback path overhead target is < 1.5s.
- **Scalability**: Per-invocation, not a daemon — no persistent process
- **Security classification**: internal (credential handling — must not log tokens or keys)
- **Data residency**: no special requirements

## Scope

### In Scope

- Detection of missing/expired `gh` auth for any HTTPS git host
- Transparent URL rewriting from `https://HOST/ORG/REPO` → `git@HOST:ORG/REPO` before executing the git operation
- Works for: clone, fetch, push, pull
- Cross-host generalization (not GitHub-specific)
- Opt-in via PATH-prepend (wrapper script at `~/.local/bin/git` deployed by cfgcaddy; `.gitconfig` credential helper chain is untouched)
- `DEBUG` or `GIT_TRACE`-compatible logging mode

### Out of Scope

- Provisioning or rotating SSH keys — user must have SSH keys for hosts pre-configured
- OAuth/PAT token management (that remains `gh`'s job)
- Windows support
- Fixing broken SSH connectivity — SSH must already work on the host for fallback to succeed

## Rabbit Holes

- **Credential helper protocol cannot switch protocols**: Git credential helpers only respond with `username`/`password` — they cannot redirect a live HTTPS operation to SSH. True transparent fallback therefore requires wrapping `git` itself (intercept the command, detect likely auth failure, rewrite remote URL, re-invoke with SSH), OR proactively rewriting HTTPS→SSH via `url.insteadOf` before the operation starts. Research phase must decide which is more robust.
- **Pre-flight `gh auth status` cost**: Calling `gh auth status` on every git operation adds latency. Caching the auth state (file mtime, env var) could mitigate this but adds complexity and stale-state risk.
- **`url.insteadOf` global side effects**: Adding a persistent `url.insteadOf` rule globally rewrites ALL HTTPS URLs — no per-operation conditionality. A session-scoped or env-var-gated approach would be cleaner but requires the git wrapper approach.
- **SSH host key fingerprint prompts**: On a truly new host, SSH will prompt to confirm the fingerprint. In non-interactive (headless) contexts this will hang. The helper needs `StrictHostKeyChecking=accept-new` or similar for non-interactive paths, which has its own security tradeoff.

## Alternatives Considered

- **Static `url.insteadOf` always**: `git config --global url."git@github.com:".insteadOf "https://github.com/"` — solves the problem but is unconditional; breaks workflows that need HTTPS (e.g., GitHub Actions tokens, `gh` itself internally).
- **Per-repo SSH remotes**: Always clone with SSH URLs — correct but requires discipline and doesn't help for repos already cloned or tooling that generates HTTPS URLs.
- **`git credential-osxkeychain` fallback**: macOS Keychain can store HTTPS credentials, but managing per-host tokens there is manual and orthogonal to the SSH fallback goal.

## Feasibility Risks

- **No native protocol-switch hook in git**: The credential helper protocol is a dead end for protocol switching. A git wrapper or session-level URL rewriting is the only path to true transparency. Must validate in research that a shell wrapper (`git` alias or `PATH`-prepended script) is reliable enough for all invocation paths (IDEs, Claude Code subagents, system scripts).
- **Headless SSH agent availability**: The `.config/environment.d/ssh-agent.conf` added in the recent SSH commit helps systemd sessions, but non-systemd headless contexts (cron, launchd, direct exec) may not have `SSH_AUTH_SOCK` set. The helper must handle this gracefully rather than hang.

## Observability Requirements

- **Default mode**: emit `warning: falling back to SSH (gh not authenticated for HOST)` to stderr whenever fallback triggers (always visible — users need to know when protocol switching occurs)
- **Debug mode** (`GIT_SSH_FALLBACK_DEBUG=1` or `GIT_TRACE` active): additionally emit `[git-ssh-fallback]` prefixed trace lines for each wrapper decision step
- Exit code from the fallback operation passed through unchanged

## Risk Control

- Delivered as an opt-in change to `.gitconfig` — existing machines unaffected until they pull dotfiles and run bootstrap
- The original `gh auth git-credential` chain is preserved as a comment/fallback, making rollback a one-line gitconfig edit
- No feature flag needed — scope is personal dotfiles, low blast radius

## Open Questions

- Is a shell wrapper script (`stapler-scripts/git-ssh-fallback`) the right implementation, or would a compiled Go binary be more portable and reliable across shells/IDEs?
- Can we detect `gh auth status` failure cheaply (exit code + timeout) without spawning a full gh CLI subprocess on every git operation?
- What is the right SSH URL format for non-GitHub hosts (e.g., GitLab, self-hosted Gitea)?
