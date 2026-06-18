# ADR-008: System Prompt Pipeline — 2-Block Array with cache_control on Block 0

**Status**: Accepted
**Date**: 2026-06-17

## Context

FR-7 (CacheAligner) and FR-9 (Verbosity Steering) both modify the system prompt before forwarding. Anthropic's prompt cache key is a cryptographic hash of the exact byte sequence up to the cache breakpoint — any byte change at or before the breakpoint invalidates the cache.

FR-7 needs to place `cache_control: {"type": "ephemeral"}` on the stable system prompt to maximize cache hit rate. FR-9 needs to append a verbosity-steering suffix (e.g., "Be terse. Skip preamble.") to reduce output token count. If these two transformations run as separate passes or both modify the same block, they corrupt each other's output and bust the cache on every request.

The system field in the Anthropic Messages API can be either a plain string or an array of content blocks.

## Decision

Transform the system prompt into a **2-block array** in a **single unified pipeline**:

1. Block 0: original system prompt text + `cache_control: {"type": "ephemeral"}` — byte-stable, will be cached
2. Block 1: verbosity suffix (if FR-9 active) — no `cache_control`, not cached, does not affect block 0's hash

Pipeline order (in `src/compression/` or a dedicated `src/system_prompt.rs`):
1. Parse incoming system (string → wrap in block; array → use as-is)
2. Normalize/stabilize: detect and flag volatile content (ISO timestamps, UUIDs in system text); do NOT add `cache_control` if volatile content detected
3. Add `cache_control` to the last stable block (block 0 in the normal case)
4. If FR-9 active and turn is a continuation turn: append verbosity suffix as new uncached block

## Alternatives Considered

| Option | Rejected because |
|--------|-----------------|
| Separate passes (FR-7 then FR-9 independently) | Both modify the `system` field; FR-9 appending to a string that FR-7 already processed would either create a 3-block array incorrectly or move `cache_control` to the wrong block, corrupting cache keys |
| String append (appending verbosity suffix to the original string) | Changes the hash of the entire system string — busts the cache on every single request; eliminates all CacheAligner benefit |
| Injecting verbosity prefix (at start of system prompt) | Also changes the cached prefix hash; worse than suffix injection |
| Placing `cache_control` on block 1 (the suffix block) | The verbosity suffix is dynamic and varies by verbosity level; caching it would still bust on any level change; the stable content is block 0 |

## Consequences

- When Claude Code sends `system` as a plain string: convert to 1-element array, add `cache_control`, then optionally append suffix block
- When Claude Code sends `system` as an array with existing `cache_control` on the last block: keep existing placement; insert suffix as new block after the last `cache_control` block
- Minimum token threshold check before adding `cache_control`: only cache when prefix is estimated ≥ 1,024 tokens (`len(text_bytes) / 4` as approximation) — Sonnet's minimum cacheable size; below this threshold Anthropic silently does not cache (no error)
- Volatile content detection: if system text contains ISO 8601 timestamps, UUIDs, or session IDs, log a warning and skip `cache_control` — caching volatile content creates a cache entry that is guaranteed to miss on every subsequent request
- `cache_read_input_tokens` and `cache_creation_input_tokens` in response `usage` (or `message_start` SSE event) are tracked for `cache_hits_estimated` / `cache_misses_estimated` metrics (FR-7.2)
