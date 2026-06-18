# Stack Research: claude-proxy-rs

**Date**: 2026-06-17
**Research scope**: HTTP server, async client, async runtime, AWS SDK, middleware, JSON

---

## 1. HTTP Server: Axum vs Actix-web vs Hyper

**Recommendation: axum 0.8.9**

### Version / adoption (June 2026)

| Crate | Version | GitHub stars | Monthly downloads |
|---|---|---|---|
| axum | 0.8.9 | ~26,300 | ~32M |
| actix-web | 4.13.0 | ~24,700 | ~2.9M |
| hyper | 1.10.1 | ~16,100 | ~59M (transitive) |

axum now downloads 11x more per month than actix-web and is used by 9,110 crates vs actix-web's 1,966. Ecosystem momentum has fully shifted.

### SSE support

**axum**: Built-in, first-class via `axum::response::sse`. No extra crates needed.

```rust
use axum::response::sse::{Event, KeepAlive, Sse};

async fn proxy_sse(client: State<reqwest::Client>) -> Sse<impl Stream<Item = Result<Event, Infallible>>> {
    let upstream = client
        .post("https://api.anthropic.com/v1/messages")
        .send().await.unwrap()
        .bytes_stream()
        .eventsource()   // eventsource-stream crate — parses SSE frames
        .map(|r| r.map(|e| Event::default().event(e.event).data(e.data)));
    Sse::new(upstream).keep_alive(KeepAlive::default())
}
```

reqwest's `.bytes_stream()` feeds directly into axum's `Sse<S>` with no adapter code.

**actix-web**: No built-in SSE type. Requires manually constructing a streaming `HttpResponse`; third-party `actix-web-lab` adds helpers. Keep-alive comments must be injected manually. Incompatible with Tower middleware — a hard architectural constraint for this project.

**hyper**: Raw only. Full SSE byte formatting written by hand as `Stream<Item = Result<Frame<Bytes>, Error>>`. Appropriate for building frameworks, not applications.

### Performance

TechEmpower: actix-web is top 5–10 globally; axum ~10–20% slower in pure synthetic throughput. For a proxy, upstream API latency (100–5000ms per Anthropic/Bedrock call) completely dominates — framework overhead is sub-1% and irrelevant.

axum's own docs: "a relatively thin layer on top of hyper that adds very little overhead."

### Tower middleware compatibility

axum's `Router` is a `tower::Service` — `tower-http` middleware attaches via `.layer()` with zero glue. This is essential for the proxy's timeout, tracing, and auth middleware. actix-web uses its own `Transform` trait and cannot use Tower middleware.

### Known SSE / backpressure issues

axum 0.8.x correctly sets `Transfer-Encoding: chunked`, flushes per-event, and propagates Tower backpressure — slow downstream clients pause the upstream stream naturally. A flush bug from 0.6.x was fixed in 0.7.x.

Deployment note: Nginx/load balancer buffering requires `X-Accel-Buffering: no` on SSE responses — neither framework sets this automatically.

---

## 2. HTTP Client: reqwest vs hyper

**Recommendation: reqwest 0.13.4 + eventsource-stream 0.2.x**

### reqwest vs hyper comparison

| | reqwest 0.13.4 | hyper 1.10.1 |
|---|---|---|
| GitHub stars | 11,700 | 16,100 |
| Abstraction | High-level client | Low-level per-connection |
| TLS | Built-in (rustls or native-tls) | Manual |
| Connection pooling | Built-in | Manual (hyper-util) |
| Timeouts | 3 granularities built-in | Manual (`tokio::time::timeout`) |
| Built-in retry (0.13) | Yes | No |
| SSE streaming | `.bytes_stream()` | Manual body polling |

reqwest 0.13 is built on hyper 1.x internally — no raw throughput is left on the table by choosing reqwest.

### Streaming: `bytes_stream()`

reqwest supports non-buffered streaming. `.bytes()` and `.text()` buffer the full response; `.bytes_stream()` does not:

```rust
// Cargo.toml: reqwest = { version = "0.13", features = ["stream"] }
let resp = client.post(url).send().await?;
let stream = resp.bytes_stream(); // Stream<Item = Result<Bytes, reqwest::Error>>
```

### Timeout configuration for SSE (critical)

```rust
let client = reqwest::Client::builder()
    .connect_timeout(Duration::from_secs(5))   // TCP + TLS handshake only
    .read_timeout(Duration::from_secs(30))     // resets on each chunk — safe for SSE
    // DO NOT set .timeout() — it's a hard wall-clock deadline from connect through full
    // body drain; it will kill long-lived SSE streams after N seconds regardless of activity
    .build()?;
```

### Retry (reqwest 0.13 built-in)

No tower-retry needed for initial connection failures:

```rust
use reqwest::retry;
let policy = retry::for_host("api.anthropic.com")
    .on_status(StatusCode::TOO_MANY_REQUESTS);
let client = reqwest::Client::builder().retry(policy).build()?;
```

Do not configure retry for mid-stream SSE connections — only on initial connection attempts.

### Forwarding reqwest → axum SSE

Use `eventsource-stream` to parse SSE protocol frames correctly (handles multi-line data, event types, IDs):

```rust
use eventsource_stream::Eventsource;
use axum::response::sse::{Event, Sse};

let event_stream = resp
    .bytes_stream()
    .eventsource()
    .map(|r| r.map(|e| Event::default().event(e.event).data(e.data).id(e.id.unwrap_or_default())));

Sse::new(event_stream)
```

### SSE-related crates evaluated

- **`eventsource-stream` 0.2.x** — correct choice for a proxy. Parses a `Stream<Bytes>` into typed SSE frames. Use this.
- **`reqwest-eventsource` 0.6.0** — wraps reqwest + eventsource-stream into a typed `EventSource` consumer with reconnect. Good for *consuming* SSE from a backend; wrong for a *forwarding* proxy — it deserializes into structs you'd re-serialize.
- **`eventsource-client` 0.17.5** (LaunchDarkly) — "early stage, API subject to change." Low adoption. Not recommended.

---

## 3. Async Runtime: Tokio

**Recommendation: tokio 1.52.3, `tokio::runtime::Builder` explicitly**

### `#[tokio::main]` vs `Builder`

The macro expands to exactly `Builder::new_multi_thread().enable_all()`. For production, use `Builder` explicitly to set `worker_threads`, `thread_name`, and a panic hook:

```rust
fn main() -> anyhow::Result<()> {
    tokio::runtime::Builder::new_multi_thread()
        .worker_threads(std::thread::available_parallelism()?.get())
        .thread_name("proxy-worker")
        .enable_all()
        .build()?
        .block_on(run())
}
```

### `worker_threads` for I/O-heavy proxy

Default (match CPU count) is correct. Tokio worker threads drive the async event loop; each handles thousands of tasks. 50+ SSE streams = 50 lightweight tokio tasks (~64 bytes each). Do NOT over-provision to 32 threads on an 8-core machine — it doesn't help for I/O-bound work.

The blocking thread pool (separate, default max 512) handles synchronous work. FR-4.8 requires 20+ threads for AWS credential operations — these must use `spawn_blocking`, not run in async context.

### Key gotchas

- **`spawn_blocking` vs `block_in_place`**: Always prefer `spawn_blocking` for proxy work. `block_in_place` inside a `join!` freezes sibling futures (not just starves) and panics in `current_thread` runtimes.
- **reqwest blocking client**: Never use `reqwest::blocking` inside async code. It stalls the runtime. Use only the async reqwest API.
- **`enable_all()`**: Required. Omitting it causes panics on first I/O or timer use.
- **AWS credential refresh** (FR-4.7): STS/SSO credential operations must go through `spawn_blocking`.

---

## 4. AWS SDK: `aws-sdk-bedrockruntime` vs `reqwest + aws-sigv4`

**Recommendation: `aws-sdk-bedrockruntime` 1.135.0 + `aws-config` 1.8.18**

### Does the SDK support streaming?

Yes. `InvokeModelWithResponseStream` returns an `EventReceiver<ResponseStream, ResponseStreamError>` backed by `aws-smithy-eventstream`. Clean async `.recv().await` iteration:

```rust
let mut stream = client
    .invoke_model_with_response_stream()
    .model_id(&model_id)
    .body(blob)
    .send().await?
    .body;

while let Some(event) = stream.recv().await? {
    match event {
        ResponseStream::Chunk(chunk) => { /* forward SSE bytes */ }
        _ => {}
    }
}
```

### Dependency weight and TLS gotcha

The SDK pulls ~7 smithy crates plus a critical TLS mismatch: the default backend is now `aws-lc-rs` (requires C compiler + CMake at build time). If the proxy uses `rustls` with `ring` (as reqwest does by default), explicitly opt in:

```toml
# In Cargo.toml — prevents "no process-level CryptoProvider" panic at startup
aws-smithy-http-client = { version = "*", features = ["rustls-ring"] }
```

This was tracked as GitHub issue #1264 (Mar 2025).

### Why not `reqwest + aws-sigv4`?

`aws-sigv4` still pulls 4–5 smithy support crates (not significantly lighter). Credential refresh for SSO/STS/IRSA would require pulling `aws-config` back anyway, negating the weight savings. FR-4.7 requires proactive AWS credential refresh — reimplementing STS/SSO credential refresh chains is non-trivial. The SDK's automatic refresh is worth the compile cost for a side project.

Compile overhead is a one-time cold build; incremental rebuilds are fast.

---

## 5. Tower Middleware

**Recommendation: Use tower + tower-http 0.7.0 throughout**

axum's `Router` is a `tower::Service` — compose with `ServiceBuilder`:

```rust
use tower_http::trace::TraceLayer;
use tower_http::compression::CompressionLayer;
use tower_http::timeout::TimeoutLayer;

let app = Router::new()
    .route("/v1/messages", post(messages_handler))
    .layer(
        ServiceBuilder::new()
            .layer(TraceLayer::new_for_http())         // outermost — captures full timing
            .layer(TimeoutLayer::with_status_code(StatusCode::REQUEST_TIMEOUT, Duration::from_secs(5)))
            .layer(CompressionLayer::new())            // innermost
    );
```

### SSE safety matrix (verified from tower-http source)

| Middleware | SSE Safe? | Detail |
|---|---|---|
| `TraceLayer` | Safe | Hooks on headers, not body frames |
| `TimeoutLayer` | Safe | Times out handler *startup*, not body streaming — SSE returns headers almost immediately |
| `CompressionLayer` | **Safe** | `DefaultPredicate` explicitly skips `text/event-stream` via `NotForContentType::SSE` at source line 127 |
| `ResponseBodyDeadlineLayer` | **Dangerous** | Wraps the response body stream; kills long-lived SSE connections — never apply globally |
| `ResponseBodyTimeoutLayer` | Conditional | Idle timeout that resets per frame — OK for active streams, kills truly idle ones |

### Middleware ordering

`TraceLayer` should be outermost (first in `ServiceBuilder`), `CompressionLayer` innermost. This way trace spans capture full timing including the compression pass.

---

## 6. JSON Manipulation: serde_json

**Recommendation: serde_json 1.0.x; migrate to sonic-rs only if profiling shows JSON as a bottleneck**

### Performance comparison

| Crate | Parse time (twitter.json ~630KB) | vs serde_json |
|---|---|---|
| `serde_json` | 3.76–3.85 ms | baseline |
| `simd-json` | 1.19–1.79 ms | ~2x faster |
| `sonic-rs` | 550–563 µs | ~7x faster |

For a proxy handling LLM responses (typically 2–20 KB per request body), serde_json parse time is sub-millisecond. Bedrock/Anthropic network latency (100–5000ms) dominates completely.

### Field removal API (FR-1.6 — body cleaning)

```rust
// Strip top-level disallowed fields
if let Value::Object(ref mut map) = body {
    for key in &["defer_loading", "input_examples", "custom", "cache_control",
                 "output_config", "context_management"] {
        map.remove(*key);
    }
}

// Filter tool_reference from tool_results content array
if let Some(Value::Array(messages)) = body.get_mut("messages") {
    for msg in messages.iter_mut() {
        if let Some(Value::Array(content)) = msg.get_mut("content") {
            content.retain(|block| {
                block.get("type").and_then(Value::as_str) != Some("tool_reference")
            });
        }
    }
}
```

### Why not simd-json?

simd-json mutates the input buffer in-place during string unescaping — requires `Vec<u8>`, not `&[u8]`. Awkward in proxy code where the original request body may need to be logged or retried.

### sonic-rs as upgrade path

sonic-rs ~7x faster, near-drop-in replacement, has `LazyValue` for zero-copy field inspection without full parse. Good upgrade path if profiling ever flags JSON as a bottleneck.

---

## Recommended Cargo.toml

```toml
[dependencies]
# HTTP server
axum = { version = "0.8", features = ["sse"] }
tower = "0.5"
tower-http = { version = "0.7", features = ["trace", "compression-full", "timeout"] }

# HTTP client
reqwest = { version = "0.13", features = ["stream", "json", "rustls-tls"] }
eventsource-stream = "0.2"

# Async runtime
tokio = { version = "1.52", features = ["full"] }

# AWS
aws-sdk-bedrockruntime = "1.135"
aws-config = { version = "1.8", features = ["behavior-version-latest"] }
aws-smithy-http-client = { version = "*", features = ["rustls-ring"] }  # prevent TLS conflict

# JSON
serde = { version = "1", features = ["derive"] }
serde_json = "1"

# Utilities
anyhow = "1"
tokio-stream = "0.1"
futures-util = "0.3"
```

---

## Summary: Key Decisions

1. **axum 0.8.9 is the clear HTTP server choice.** Built-in SSE (`axum::response::sse::Sse<S>`), native Tower compatibility, and reqwest's `.bytes_stream()` feeds directly into it — the proxy SSE forwarding path requires zero glue code. actix-web has no built-in SSE and is incompatible with Tower; raw hyper is unjustifiable complexity for an application.

2. **reqwest 0.13 is the correct upstream client; set `connect_timeout` + `read_timeout`, never `.timeout()` for SSE.** The `.timeout()` builder method is a hard wall-clock deadline that will kill long-lived SSE streams. `read_timeout` resets on each received chunk, which is the correct behavior for streaming. Use `eventsource-stream` (not `reqwest-eventsource`) to parse upstream SSE frames for forwarding.

3. **Use `aws-sdk-bedrockruntime` with explicit `rustls-ring` feature to avoid a silent TLS conflict.** The SDK's automatic STS/SSO credential refresh is worth the compile weight — reimplementing it manually would require pulling `aws-config` back anyway. The `aws-lc-rs` vs `ring` TLS conflict is a known production footgun (GH #1264) and must be addressed in Cargo.toml on day one.
