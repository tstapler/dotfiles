# ADR-002: Git Wrapper Script Over Credential Helper for HTTPS→SSH Fallback

**Date:** 2026-06-24
**Status:** Accepted
**Deciders:** Tyler Stapler

---

## Context

When `gh auth git-credential` is not configured for a host, HTTPS git operations fail. The goal is to transparently fall back to SSH for those operations.

Three architectural approaches were evaluated:

1. **Credential helper wrapper**: Intercept at the credential helper layer.
2. **Static `url.insteadOf`**: Permanently rewrite HTTPS URLs to SSH in `.gitconfig`.
3. **PATH-prepended git wrapper script**: Intercept at the git binary level, conditionally inject URL rewriting.

## Decision

Use a **PATH-prepended POSIX shell script** (`stapler-scripts/git-ssh-fallback` deployed as `~/.local/bin/git`) that intercepts git invocations, checks `gh` auth state for the target host, and injects `url.insteadOf` rewriting via `GIT_CONFIG_COUNT` / `GIT_CONFIG_KEY_n` / `GIT_CONFIG_VALUE_n` environment variables on a per-invocation basis when the host is not authenticated.

## Rationale

**Against credential helper wrapper**: The git credential helper protocol (stdin/stdout line-oriented with `get`/`store`/`erase`) can only return `username` and `password` fields. It has no mechanism to redirect git to use a different transport protocol. A credential helper cannot signal "retry this via SSH." This is a hard protocol limitation confirmed by the git credential documentation. (Research ref: architecture.md §1)

**Against static `url.insteadOf`**: An unconditional `.gitconfig` entry rewrites every HTTPS URL for the host, permanently bypassing `gh auth git-credential`. This breaks operations that legitimately need HTTPS (e.g., on a machine with SSH keys not yet configured, or for tooling that only understands HTTPS like Cargo or Go modules). Tyler's `.gitconfig` already has `gh auth git-credential` configured for github.com and gist.github.com precisely because HTTPS is needed in some contexts. (Research ref: build-vs-buy.md §2a)

**For git wrapper**: The wrapper operates at the git binary level — above the credential protocol but before the network connection. It can conditionally inject `url.insteadOf` for a single invocation without persisting any config change. It covers all invocation paths (interactive shells, IDE subprocesses, Claude Code subagents, systemd user sessions) because it intercepts via PATH rather than shell functions. (Research ref: architecture.md §2)

## Consequences

**Positive:**
- `.gitconfig` is never mutated by the wrapper; the existing credential helper chain is fully preserved.
- All invocation contexts are covered (PATH-prepend beats shell-function-only coverage).
- SSH fallback is conditional on detected auth state, not permanent.

**Negative:**
- One `gh` subprocess added per network git operation (mitigated by 5-minute AuthCache).
- IDEs with hardcoded git paths (`git.path` setting in VSCode, JetBrains) bypass the wrapper unless configured explicitly.
- Must guard against recursive invocation via `GIT_SSH_FALLBACK_ACTIVE=1` environment variable.

## Alternatives Rejected

| Alternative | Reason |
|-------------|--------|
| Credential helper wrapper | Protocol dead end — cannot switch transport |
| Static `url.insteadOf` | Unconditional rewrite breaks legitimate HTTPS usage |
| Git alias | Only applies to explicit alias invocations; IDEs and subagents bypass aliases |
| Compiled Go binary | Requires build step in bootstrap; shell script is sufficient for the logic involved |
| Reactive retry (parse stderr) | Requires stderr buffering which breaks streaming progress output for large operations |
