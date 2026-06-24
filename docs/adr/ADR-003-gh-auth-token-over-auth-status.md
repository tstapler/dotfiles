# ADR-003: Use `gh auth token` Over `gh auth status` for Auth Detection

**Date:** 2026-06-24
**Status:** Accepted
**Deciders:** Tyler Stapler

---

## Context

The git wrapper needs to determine whether `gh` has a valid token for a given hostname before deciding whether to fall back to SSH. Two `gh` CLI commands are candidates for this check:

- `gh auth status --hostname <host>`: Human-readable status output; exits 0 if authenticated.
- `gh auth token --hostname <host>`: Outputs raw token on stdout; exits 0 if authenticated, non-zero if not.

## Decision

Use `gh auth token --hostname "$host" >/dev/null 2>&1` as the auth detection primitive.

## Rationale

**`gh auth status` reliability issues:**

1. **Known exit-code bug (cli/cli#8845)**: In some `gh` versions, `gh auth status` returned exit code 0 even when the user was not authenticated. This bug was observed and reported in production use.

2. **Keychain timeout silent failure (cli/cli#13317)**: On macOS, `gh auth status` wraps Keychain reads in a 3-second timeout. When the Keychain is slow or locked (headless sessions, multi-agent contention), the command may report "not authenticated" while the user actually has a valid token — or report "authenticated" while actual API calls fail with 401. This is an open upstream bug as of 2026.

3. **Human-readable output**: `gh auth status` output format is designed for human consumption. Parsing it in a script is fragile across `gh` versions.

**`gh auth token` advantages:**

1. **Machine-readable**: Outputs the raw token (or nothing) — no parsing required. Exit code is the only signal needed.

2. **Faster**: Does not produce human-formatted output; slightly lower overhead than `auth status`.

3. **Correct semantics**: Exit code directly answers the binary question "do you have a valid token for this host?"

4. **Per-host targeting**: `--hostname` flag works identically on both commands; no behavioral difference here.

**Caching to mitigate Keychain contention:**

The wrapper uses a file-based AuthCache (`~/.cache/git-ssh-fallback/<host>.auth`) with a 5-minute TTL to avoid spawning `gh` on every network git operation. This reduces exposure to Keychain contention in multi-agent workloads (e.g., parallel Claude Code subagents running git operations).

## Consequences

**Positive:**
- No output parsing required; exit code is the sole decision signal.
- Faster than `gh auth status` on the unauthenticated path (~52ms measured).
- AuthCache reduces per-operation overhead to near-zero for repeated operations within the TTL window.

**Negative:**
- `gh auth token` may still trigger Keychain access on cache miss; the 3-second Keychain timeout risk still applies, though AuthCache bounds its frequency.
- A 5-minute stale cache could theoretically trigger unnecessary SSH fallback if a token was refreshed mid-cache-window (acceptable tradeoff for personal dotfiles use).

## Alternatives Rejected

| Alternative | Reason |
|-------------|--------|
| `gh auth status --hostname` | Known exit-code bug; Keychain timeout silent failure; human-readable output requires parsing |
| `GH_TOKEN` / `GITHUB_TOKEN` env var check | Only covers env-var-configured tokens; does not detect Keychain-stored tokens used by the existing `gh auth git-credential` setup |
| `~/.config/gh/hosts.yml` file parse | Would require parsing YAML in POSIX sh; file presence does not guarantee token validity |
| No caching (call gh every time) | Acceptable latency for single operation (52ms); unacceptable for `git clone --recurse-submodules` with many submodules (N × 52ms) |
