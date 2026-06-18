# Architecture Research: claude-proxy-rs

**Date**: 2026-06-17
**Status**: Complete

---

## 1. Provider Fallback Pattern

### Recommendation: Roll a custom cooldown state machine

No existing circuit-breaker crate models the exact requirement (trip on first 429 → fixed-duration provider-level cooldown → retry primary). The two viable crates have impedance mismatches:

| Crate | Version | Verdict |
|---|---|---|
| `failsafe` | 1.3.0 | Trips on failure-rate threshold, not a single 429. Fighting the abstraction. |
| `tokio-retry` | 0.3.2 | Per-request transient retry only; no provider-level state. Add as supplemental. |
| `backoff` | 0.4.0 | Good for `Retry-After` header parsing from 429 responses. Supplemental use. |

**Recommended state struct** (in `src/fallback.rs`):

```rust
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio::time::Instant;

#[derive(Clone)]
pub enum ProviderState {
    Normal,
    Cooldown { until: Instant },
}

pub struct FallbackState {
    inner: Arc<RwLock<ProviderState>>,
    cooldown_secs: u64,
}

impl FallbackState {
    pub async fn should_use_fallback(&self) -> bool {
        let state = self.inner.read().await;
        match *state {
            ProviderState::Normal => false,
            ProviderState::Cooldown { until } => Instant::now() < until,
        }
    }

    pub async fn enter_cooldown(&self) {
        let mut state = self.inner.write().await;
        *state = ProviderState::Cooldown {
            until: Instant::now() + Duration::from_secs(self.cooldown_secs),
        };
    }

    pub async fn try_exit_cooldown(&self) -> bool {
        let mut state = self.inner.write().await;
        match *state {
            ProviderState::Cooldown { until } if Instant::now() >= until => {
                *state = ProviderState::Normal;
                true
            }
            _ => false,
        }
    }
}
```

**Cargo.toml additions**:
```toml
tokio-retry = "0.3"   # per-request transient retries (5xx, timeouts)
backoff = { version = "0.4", features = ["tokio"] }  # optional: Retry-After parsing
```

**Key insight**: `tokio::sync::RwLock<ProviderState>` is correct here (many concurrent reads, rare writes). `AtomicBool` is insufficient because the cooldown-expiry check and state transition must be atomic together.

---

## 2. In-Memory LRU Cache (Rewind Store)

### Recommendation: `moka` v0.12 with `future` feature

Requirements: 500 entries, 10-minute TTL, `Arc<String>` keys, `Arc<Vec<u8>>` values, thread-safe from async handlers.

| Crate | TTL | Thread-safe | Async-native | Verdict |
|---|---|---|---|---|
| `lru` 0.12 | None | `Mutex` only | No | Disqualified |
| `quick_cache` 0.6 | None (manual) | Yes | Partial | Too much plumbing |
| `ttl_cache` / `lru-time-cache` | Basic | `Mutex` only | No | Outdated |
| **`moka` 0.12** | **Built-in** | **Internally concurrent** | **Yes (tokio)** | **Recommended** |

**Cargo.toml**:
```toml
moka = { version = "0.12", features = ["future"] }
```

**Setup** (in `src/compression/rewind.rs`):
```rust
use moka::future::Cache;
use std::sync::Arc;
use std::time::Duration;

// Build once in AppState, clone cheaply into handlers
let rewind_cache: Cache<String, Arc<Vec<u8>>> = Cache::builder()
    .max_capacity(500)
    .time_to_live(Duration::from_secs(10 * 60))
    .build();

// Insert (async)
cache.insert(hash.to_string(), Arc::new(original_bytes)).await;

// Get (sync, only clones the Arc pointer — not the bytes)
if let Some(data) = cache.get(&hash) { ... }
```

**Key insight**: `moka::future::Cache` is `Clone` — sharing across request handlers requires no `Arc<Mutex<>>` wrapper, just `cache.clone()`. Wrapping values in `Arc<Vec<u8>>` avoids copying large byte payloads on cache hits.

---

## 3. SSE Streaming Passthrough

### Recommendation: Direct pipe via `eventsource-stream`

Architecture: `reqwest` bytes stream → `eventsource-stream` parser → `axum::response::sse::Event` map → downstream `Sse<S>`. No channel needed for a single-upstream proxy.

**Cargo.toml**:
```toml
reqwest = { version = "0.12", features = ["stream"] }
eventsource-stream = "0.2.3"
axum = { version = "0.7", features = ["http2"] }
futures-util = "0.3"
tokio-stream = { version = "0.1", features = ["sync"] }
```

**Handler skeleton** (in `src/providers/`):
```rust
use axum::response::sse::{Event as AxumEvent, KeepAlive, Sse};
use eventsource_stream::Eventsource;
use futures_util::StreamExt;

async fn proxy_sse(upstream_response: reqwest::Response)
    -> Sse<impl Stream<Item = Result<AxumEvent, axum::BoxError>>>
{
    let stream = upstream_response
        .bytes_stream()
        .eventsource()
        .map(|result| match result {
            Ok(event) => {
                let mut axum_event = AxumEvent::default().data(event.data);
                if !event.event.is_empty() {
                    axum_event = axum_event.event(event.event);
                }
                Ok(axum_event)
            }
            Err(e) => Err(axum::BoxError::from(e.to_string())),
        });

    Sse::new(stream).keep_alive(KeepAlive::default())
}
```

**When to use channels instead**: Fan-out to multiple clients, or when the upstream connection lifecycle must be decoupled from the HTTP handler (not needed here — 1:1 proxy).

**Key insight**: `eventsource-stream`'s `.eventsource()` extension trait handles the `data: ...\n\n` framing, multi-line data, event type, and id fields per spec. The direct pipe provides natural back-pressure: upstream reads are gated on downstream polling.

---

## 4. Graceful Shutdown with In-Flight SSE Notification

### Recommendation: `CancellationToken` + `TaskTracker` from `tokio-util`

**Cargo.toml**:
```toml
tokio-util = { version = "0.7", features = ["sync", "task-tracker"] }
```

**Shutdown sequence**:
1. `SIGTERM` or `SIGINT` fires the shutdown signal future
2. Set `AtomicBool shutting_down = true` → middleware returns 503 to new requests
3. `shutdown_token.cancel()` → broadcasts into every active SSE stream's `select!`
4. Each SSE stream sends a final `Event::default().event("server-shutdown").retry(5s)` and breaks
5. `tracker.close(); tracker.wait()` → blocks until all connections drain
6. Hard timeout (30s) via `tokio::time::timeout` before axum drops remaining connections

**Critical details**:
- `axum::serve(...).with_graceful_shutdown(signal)` stops the TCP listener but does NOT inject cancellation into streaming handlers — that's your job via `CancellationToken`
- Use `tracker.token()` (not `tracker.spawn()`) to track inline SSE handler futures: returns a `TaskTrackerToken` guard that counts as one tracked task, drops when handler returns
- `tracker.wait()` only resolves after `tracker.close()` is called first
- Signal handling: combine SIGTERM + SIGINT with `tokio::select!` on `signal(SignalKind::terminate())` and `tokio::signal::ctrl_c()`
- The SSE `.retry(Duration)` field becomes `retry: 5000\n` in SSE wire format — tells `EventSource` clients when to reconnect

**Per-handler pattern**:
```rust
async fn sse_handler(State(state): State<AppState>) -> impl IntoResponse {
    let _guard = state.tracker.token();  // counts connection; drops on return
    let token = state.shutdown_token.clone();

    let stream = upstream_stream.map(move |event| {
        // event processing
    }).take_until(token.cancelled());
    // On cancellation, append final shutdown event before stream ends
    Sse::new(stream)
}
```

---

## 5. Metrics Collection

### Recommendation: `AtomicU64` static struct + `VecDeque` rolling histogram

No metrics crate is needed. Zero additional dependencies (beyond `serde_json` which is already present).

**Counters** (in `src/metrics/mod.rs`):
```rust
use std::sync::atomic::{AtomicU64, Ordering};

pub struct Counters {
    pub req_anthropic:  AtomicU64,
    pub req_bedrock:    AtomicU64,
    pub err_timeout:    AtomicU64,
    pub err_auth:       AtomicU64,
    pub err_rate_limit: AtomicU64,
    // compression metrics
    pub tokens_before:  AtomicU64,
    pub tokens_after:   AtomicU64,
    pub requests_compressed: AtomicU64,
}

pub static COUNTERS: Counters = Counters { /* AtomicU64::new(0) for each */ };

// Emit: COUNTERS.req_anthropic.fetch_add(1, Ordering::Relaxed);
// Read: COUNTERS.req_anthropic.load(Ordering::Relaxed)
```

**Rolling 15-minute latency histogram** (for `/dashboard` charts):
```rust
use std::collections::VecDeque;
use std::sync::{Mutex, OnceLock};
use std::time::{Duration, Instant};

const WINDOW: Duration = Duration::from_secs(900);

pub struct RollingLatency {
    samples: Mutex<VecDeque<(Instant, f64)>>,
}

impl RollingLatency {
    pub fn record(&self, secs: f64) {
        let now = Instant::now();
        let mut q = self.samples.lock().unwrap();
        q.push_back((now, secs));
        let cutoff = now - WINDOW;
        while q.front().map_or(false, |(t, _)| *t < cutoff) {
            q.pop_front();
        }
    }
    pub fn percentile(&self, p: f64) -> Option<f64> { /* sort + index */ }
    pub fn chart_data(&self) -> Vec<(u64, f64)> { /* 30s buckets */ }
}

pub static LATENCY: OnceLock<RollingLatency> = OnceLock::new();
// Init in main(): LATENCY.get_or_init(|| RollingLatency { samples: Mutex::new(VecDeque::new()) });
```

**Memory**: at 1000 req/s × 15 min = ~900K entries × 16 bytes = ~14 MB worst case. Pre-aggregate to 1 sample/second if needed.

**Crate comparison**:
| Option | Deps | Counters | Histograms | JSON | Verdict |
|---|---|---|---|---|---|
| `metrics` + `DebuggingRecorder` | 2 crates | Yes | Raw Vec, no window | Manual | Testing tool, skip |
| **AtomicU64 static** | **0** | **Yes** | **No (add VecDeque)** | **Trivial** | **Recommended** |
| `prometheus-client` 0.25 | 1 crate | Yes | Buckets only | Not native | Add later if Prometheus scraping needed |
| `metered` | unmaintained | Yes | HdrHistogram | serde | RUSTSEC advisory, skip |

**Future-proofing**: `prometheus-client = "0.25"` can coexist alongside the atomic approach if Prometheus scraping is added later — no replacement needed.

---

## 6. Rotating Log Files

### Recommendation: `rolling-file` + `tracing-appender::non_blocking` + multi-layer subscriber

`tracing-appender` alone cannot meet the 10MB size-based rotation requirement — it only supports time-based rotation (MINUTELY, HOURLY, DAILY, WEEKLY, NEVER). It does support `max_log_files(n)` in v0.2.5, but only for time-triggered rotation.

**Cargo.toml**:
```toml
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }
tracing-appender = "0.2"   # for non_blocking wrapper only
rolling-file = "0.2"       # size-based rotation
```

**Setup** (in `src/main.rs` or `src/logging.rs`):
```rust
use rolling_file::{BasicRollingFileAppender, RollingConditionBasic};
use tracing_appender::non_blocking;
use tracing_subscriber::{filter, fmt, prelude::*, Layer};

fn init_logging() {
    // App log: 10MB × 10 files
    let app_file = BasicRollingFileAppender::new(
        "/tmp/claude-proxy.app.log",
        RollingConditionBasic::new().max_size(10 * 1024 * 1024),
        10,
    ).unwrap();
    let (app_writer, _app_guard) = non_blocking(app_file);

    // HTTP log: 10MB × 5 files
    let http_file = BasicRollingFileAppender::new(
        "/tmp/claude-proxy.http.log",
        RollingConditionBasic::new().max_size(10 * 1024 * 1024),
        5,
    ).unwrap();
    let (http_writer, _http_guard) = non_blocking(http_file);

    tracing_subscriber::registry()
        .with(fmt::layer().with_filter(filter::LevelFilter::INFO))
        .with(fmt::layer().with_writer(app_writer)
            .with_filter(filter::filter_fn(|m| m.target() != "http_access")))
        .with(fmt::layer().with_writer(http_writer)
            .with_filter(filter::filter_fn(|m| m.target() == "http_access")))
        .init();

    // IMPORTANT: keep _app_guard and _http_guard alive for program duration
    // Store them in main() local scope or a static OnceLock
}
```

**Route events to specific files** using the `target:` field:
```rust
tracing::info!(target: "http_access", method = %req.method(), status = 200, "request");
```

**Key insight**: Multiple `fmt::Layer` instances with different `with_filter()` predicates write simultaneously to different files — natively supported by `tracing_subscriber::registry()`. Guards returned by `non_blocking()` must be kept alive for the program's lifetime; dropping them flushes and closes the writer channel.

**File naming**: `rolling-file` uses Debian convention: `basename`, `basename.1`, ..., `basename.N`.

---

## Crate Dependency Summary

```toml
[dependencies]
# Web framework
axum = { version = "0.7", features = ["http2"] }
tokio = { version = "1", features = ["rt-multi-thread", "macros", "signal"] }
tower = "0.4"
tower-http = { version = "0.5", features = ["trace"] }

# HTTP client
reqwest = { version = "0.12", features = ["stream", "json"] }

# SSE streaming
eventsource-stream = "0.2.3"
futures-util = "0.3"
tokio-stream = { version = "0.1", features = ["sync"] }

# Fallback / retry
tokio-retry = "0.3"

# Cache
moka = { version = "0.12", features = ["future"] }

# Graceful shutdown
tokio-util = { version = "0.7", features = ["sync", "task-tracker"] }

# Serialization
serde = { version = "1", features = ["derive"] }
serde_json = "1"

# Logging
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }
tracing-appender = "0.2"
rolling-file = "0.2"
```

---

## Key Architectural Decisions

1. **Fallback state**: `RwLock<ProviderState>` custom state machine — no circuit-breaker crate models "trip on single 429, hold for wall-clock N minutes" without impedance mismatch. Roll it in ~40 lines.

2. **Rewind cache**: `moka` v0.12 — the only async-native Rust LRU crate with built-in TTL. Wrap values in `Arc<Vec<u8>>` to avoid byte-copying on cache hits.

3. **SSE passthrough**: Direct pipe via `eventsource-stream` — no channel buffering needed for 1:1 proxy. Natural back-pressure, handles all SSE framing per spec.

4. **Graceful shutdown**: `CancellationToken` (per-connection broadcast) + `TaskTracker` (drain counter) — axum's `with_graceful_shutdown` only stops the accept loop; you must inject cancellation into each SSE stream manually.

5. **Metrics**: Zero-dep approach — `AtomicU64` static struct for counters, `VecDeque<(Instant, f64)>` for rolling histogram. Sufficient for JSON export and 15-min chart history without a metrics crate.

6. **Log rotation**: `rolling-file` (size-based) wrapped in `tracing_appender::non_blocking`, with per-layer `filter_fn` predicates routing events to separate files. `tracing-appender`'s built-in rotation is time-only — it cannot do 10MB triggers.
