# ADR-004: LRU Cache — moka v0.12 with Native TTL

**Status**: Accepted
**Date**: 2026-06-17

## Context

FR-5.5 requires an in-memory LRU cache (Rewind Store) with 500 entries, 10-minute TTL, and thread-safe access from async request handlers. The cache stores original uncompressed request content keyed by hash, allowing retrieval when a client sends a `rewind_retrieve` tool call. The cache must not require manual TTL management or external locking wrappers.

## Decision

Use **moka v0.12** with the `future` feature.

```toml
moka = { version = "0.12", features = ["future"] }
```

Configure with:
- `max_capacity(500)` for the 500-entry LRU eviction limit
- `time_to_live(Duration::from_secs(600))` for the 10-minute TTL
- Values wrapped in `Arc<Vec<u8>>` to avoid byte-copying on cache hits

## Alternatives Considered

| Option | Rejected because |
|--------|-----------------|
| `lru` 0.12 | No built-in TTL; thread safety requires `Mutex` wrapper; not async-native — every cache access blocks the async task |
| `quick_cache` 0.6 | No built-in TTL (requires manual eviction logic); async support is partial; too much plumbing to reach equivalent functionality |
| `ttl_cache` / `lru-time-cache` | Outdated; thread safety is `Mutex` only; not async-native |

## Consequences

- `moka::future::Cache` is `Clone` — sharing across request handlers requires no `Arc<Mutex<>>` wrapper; clone the cache handle cheaply when building `AppState`
- `cache.insert(key, value).await` is async; `cache.get(&key)` is synchronous (only clones the `Arc` pointer, not the bytes)
- Wrapping values in `Arc<Vec<u8>>` means cache hits return a pointer clone (~8 bytes) regardless of payload size
- The same `moka` cache type covers both the Rewind Store (FR-5.5) and the SharedContext memory store (FR-10) — consistent API across both features
- moka's internal concurrency is segment-based; no single global lock; safe for 50+ concurrent handlers (NFR-1.4)
