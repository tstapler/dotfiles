# ADR-006: Fallback State Machine — Custom RwLock<ProviderState>

**Status**: Accepted
**Date**: 2026-06-17

## Context

FR-4.1 requires: on a 429 from Anthropic, switch to Bedrock and enter a configurable cooldown period (default 300s) before retrying Anthropic. FR-4.2 requires Bedrock to never be placed in cooldown. The semantics are: trip on the **first** 429, hold for a fixed wall-clock duration, then automatically return to normal.

This is a provider-level state machine, not a per-request retry policy. Existing circuit-breaker crates model failure-rate thresholds or per-request transient retries — neither matches the single-429-trip requirement.

## Decision

Roll a **custom `RwLock<ProviderState>` state machine** in ~40 lines in `src/fallback.rs`:

```rust
pub enum ProviderState {
    Normal,
    Cooldown { until: Instant },
}

pub struct FallbackState {
    inner: Arc<RwLock<ProviderState>>,
    cooldown_secs: u64,
}
```

## Alternatives Considered

| Option | Rejected because |
|--------|-----------------|
| `failsafe` 1.3.0 | Trips on a configurable failure-rate threshold (e.g., >50% failures in a window), not on a single 429 event; fighting the abstraction to model "trip immediately on first 429" |
| `circuit-breaker-rs` | Uses rate thresholds and half-open probe states; the same impedance mismatch as `failsafe`; no concept of a fixed-duration wall-clock cooldown |
| `tokio-retry` 0.3.2 | Per-request transient retry only; no shared provider-level state across concurrent requests; useful supplementally for 5xx/timeout retries, not for the fallback logic |
| `AtomicBool` | Insufficient: the cooldown-expiry check and the state transition from Cooldown→Normal must be atomic together; a bool cannot carry the `until: Instant` needed for expiry |

## Consequences

- `tokio::sync::RwLock` is correct (many concurrent reads checking `should_use_fallback`, rare writes on 429 events); use the tokio async variant, not `std::sync::RwLock`, to avoid blocking the runtime during lock contention
- `try_exit_cooldown()` acquires a write lock and atomically checks expiry + clears state in one operation — prevents the TOCTOU race of check-then-update with two separate lock acquisitions
- `tokio-retry` is added as a supplemental dependency for per-request transient retries (5xx, timeouts) on Bedrock (FR-4.3)
- The `backoff` crate's `Retry-After` header parsing is available as an optional supplement for respecting Anthropic's rate-limit headers
- The `FallbackState` struct is added to `AppState` and cloned into each request handler via axum's `State` extractor
