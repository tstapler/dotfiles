# Pitfalls & Migration Concerns: claude-proxy-rs

Research date: 2026-06-17  
Scope: Rewriting Python/FastAPI proxy to Rust/axum+tokio  
Key features: OAuth auth, AWS Bedrock with SSO credential refresh, SSE streaming, in-memory LRU compression cache

---

## 1. AWS SSO Credential Refresh

### The Core Gap

`aws-config`'s `SsoCredentialsProvider` reads cached SSO tokens from `~/.aws/sso/cache/<hash>.json` and holds an in-memory expiring cache. When credentials approach expiry, it refreshes them automatically **from the cache file only** — it does not open a browser or call `aws sso login`. If the cached SSO token itself is expired, it returns `CredentialsNotLoaded` or an auth error.

This means FR-4.7 (proactive refresh when expiring within 5 minutes) **cannot be delegated to the SDK** — you must implement it yourself.

### Recommended Approach: CredentialWatcher

```
~/.aws/sso/cache/<hash>.json  →  read expiresAt field
                                       ↓ if < 5 minutes remaining
tokio::process::Command::new("aws").args(["sso", "login", "--profile", profile])
                                       ↓ await subprocess completion
proceed with Bedrock request
```

Implementation notes:
- Use `tokio::fs::read_to_string` (async) to read the cache file, never `std::fs`
- Parse `expiresAt` from the JSON as an RFC3339 timestamp
- The `aws-sdk-bedrockruntime` crate is **fully async** — no `spawn_blocking` needed for SDK calls
- `aws-sdk-ssooidc` can implement the device-code flow manually, but `aws sso login` shell-out is the pragmatic path

### LaunchAgent / No-TTY Hazard

`aws sso login` opens a browser and blocks waiting for user interaction. Under a macOS LaunchAgent (no TTY, no user session context), this creates a hung request and possibly a zombie subprocess.

**Mitigation**: Do not hang — detect the no-TTY condition and return a 503 with a clear message:

```
Bedrock credentials expire in < 5m. Run: aws sso login --profile <profile>
Return: HTTP 503 {"error": "bedrock_credentials_expired", "action": "run 'aws sso login'"}
```

Cache the credential validity check result for 30 seconds (FR-4.7) to avoid hammering the filesystem on every request.

### Mid-Request Token Expiry

The AWS SDK for Rust does not automatically retry `ExpiredTokenException` — it is not in the standard transient retry set. If a token expires mid-streaming Bedrock request, you will get a stream termination error that surfaces as an incomplete SSE stream to the client. The 30-second cache + 5-minute pre-check buffer (FR-4.7) is the primary mitigation.

---

## 2. Blocking Operations in Tokio

### `spawn_blocking` Mechanics

- Default blocking thread pool limit: effectively 512 threads; tasks queue when saturated (no automatic error)
- **Critical**: `spawn_blocking` tasks **cannot be aborted** once running — `JoinHandle::abort()` has no effect
- Runtime shutdown waits indefinitely for all started `spawn_blocking` tasks unless `Runtime::shutdown_timeout` is set
- Rule: use `spawn_blocking` for short, bounded blocking work only; for persistent background loops (e.g., SSO token watcher), use `std::thread::spawn` + channels

### AWS SDK: No `spawn_blocking` Needed

All `aws-sdk-bedrockruntime` and `aws-config` calls are **fully async** on tokio. FR-4.8's requirement for a "dedicated thread pool, min 20 threads" was written against boto3's blocking interface — in Rust this is moot; the async runtime handles concurrency natively.

### Log Rotation: Non-Blocking Wrapper Required

`tracing_appender::RollingFileAppender` **blocks on writes** when used directly. Always wrap:

```rust
let (non_blocking, _guard) = tracing_appender::non_blocking(file_appender);
```

The `WorkerGuard` (`_guard`) **must be held for the process lifetime** — typically stored in `main`. Dropping it early causes log loss on shutdown.

**Size-based rotation gap**: `RollingFileAppender` supports `NEVER`/`MINUTELY`/`HOURLY`/`DAILY` rotation only — not byte-size rotation (FR-6.5 requires 10MB × N files). Use the `rolling_file` crate or a custom implementation for byte-size rotation.

### Other Blocking Hazards

| Operation | Safe approach |
|---|---|
| AWS SDK calls | `.await` directly (fully async) |
| SSO cache file read | `tokio::fs::read_to_string` |
| Log writes | `tracing_appender::non_blocking` |
| DNS resolution | reqwest with rustls uses async DNS internally |
| LRU cache (in-memory) | No disk I/O — no concern |
| `aws sso login` subprocess | `tokio::process::Command` (async-native) |

---

## 3. SSE Streaming Edge Cases

### Client Disconnect Detection Is Lazy

axum's `Sse<S>` drives the stream via hyper's async body mechanism. Client disconnect is detected **only when the next write to the TCP socket fails** (broken pipe / connection reset) — not proactively. There is no built-in "on disconnect" callback.

To cancel upstream work on client disconnect, use `tokio::select!` with a `CancellationToken`:

```rust
tokio::select! {
    chunk = upstream_stream.next() => { /* forward */ }
    _ = cancellation_token.cancelled() => { /* stop upstream read */ }
}
```

Wire the cancellation to axum's connection close signal by watching the body drop or using tower's `on_failure`.

### Half-Open Connections

Without keep-alive, a Bedrock stream that takes 30+ seconds before the first token will appear half-open to intermediate proxies (macOS localhost loop typically fine, but relevant if the proxy is ever exposed over a network).

```rust
Sse::new(stream).keep_alive(
    KeepAlive::new().interval(Duration::from_secs(15))
)
```

This sends `": ping\n\n"` comments on the interval. Anthropic's own SSE stream sends `ping` events; Bedrock may not — the keep-alive guard is important for Bedrock streams.

### Chunked Encoding vs SSE

HTTP/1.1 applies chunked transfer encoding at the transport layer; SSE uses `\n\n` event delimiters at the application layer. These are orthogonal — no double-encoding problem. SSE clients parse `text/event-stream` by line scanning, unaware of chunk boundaries.

### Backpressure

axum polls the stream only when hyper has sent the previous chunk and the TCP window has space. If the upstream (Anthropic/Bedrock) produces faster than the client consumes, events accumulate in memory unboundedly.

**Mitigation**: Bridge the upstream reqwest byte stream through a **bounded** `tokio::sync::mpsc` channel before feeding to axum's `Sse`:

```rust
let (tx, rx) = tokio::sync::mpsc::channel::<Result<Event, _>>(32); // bounded
```

This provides backpressure: upstream reading pauses when the channel is full.

### reqwest Connection Pool Exhaustion

reqwest's default connection pool reuses connections. Long-lived SSE connections hold a pool slot permanently, starving other requests under 50+ concurrent streams (NFR-1.4).

**Mitigation**: Use a dedicated `reqwest::Client` for streaming requests with connection pooling disabled:

```rust
let streaming_client = reqwest::Client::builder()
    .pool_max_idle_per_host(0)
    .build()?;
```

Keep a separate pooled client for short requests (health checks, non-streaming Anthropic calls).

### Upstream SSE Connection Drop

If the upstream SSE connection drops, the reqwest `bytes_stream()` returns `Err` or terminates. axum's `Sse<S>` propagates this as stream termination — the connection closes on the client side. The proxy should emit a final SSE error event before terminating:

```
event: error
data: {"type":"upstream_disconnected","message":"upstream connection lost"}
```

---

## 4. JSON Body Manipulation Pitfalls

### `serde_json::Value` vs Typed Structs

For a proxy that must strip unknown fields without losing them, `serde_json::Value` is the correct choice. Typed structs drop any field not in the struct definition. A hybrid approach — typed structs + `#[serde(flatten)] extra: HashMap<String, Value>` — preserves unknowns at the top level, but has critical limitations:

- `#[serde(flatten)]` is **incompatible with `#[serde(deny_unknown_fields)]`**
- Combining `flatten` with untagged enums is a known bug (serde issue #1600)

**Recommendation**: Use `Value` for deeply nested unknowns; typed structs + flatten only at the top-most request struct level.

### Axum Default Body Size Limit

axum's `Json`, `Bytes`, and `String` extractors hard-limit bodies to **2MB by default**. Tool results containing base64-encoded images can easily exceed this.

```rust
// Apply per-route, not globally
.route_layer(DefaultBodyLimit::max(50 * 1024 * 1024))
```

Apply the large limit only to `/v1/messages`, `/chat/completions`, `/v1/chat/completions`.

### Must Buffer Before Modifying

You cannot stream-mutate JSON. The proxy must:

1. Receive full body into `Bytes`
2. Parse with `serde_json::from_slice` (zero-copy parse from bytes — prefer over `from_str`)
3. Mutate: `as_object_mut().remove("key")`, splice arrays
4. Re-serialize with `serde_json::to_vec`
5. Forward new bytes

At 10MB per request with 50 concurrent streams (NFR-1.4), peak memory from body buffering is ~1.5GB. Use `serde_json::from_slice` to avoid the extra UTF-8 allocation from `from_str`.

### Content-Length Must Be Rewritten

axum/hyper do **not** rewrite `Content-Length` automatically after body modification. Forwarding the original `Content-Length` will cause the upstream to reject the request with a mismatch.

**Mitigation**: When building the outgoing reqwest request, explicitly drop `Content-Length` and `Transfer-Encoding` headers from the client request, then set the body bytes — reqwest/hyper will compute the correct `Content-Length`:

```rust
let mut headers = incoming_headers.clone();
headers.remove(CONTENT_LENGTH);
headers.remove(TRANSFER_ENCODING);
client.post(url).headers(headers).body(modified_body).send().await
```

---

## 5. Binary Size and Compilation Time

### Realistic Targets (macOS arm64)

| Metric | Unoptimized | Optimized release |
|---|---|---|
| Stripped binary | ~60–90MB | **~15–25MB** |
| Cold release build | — | **8–15 min** (M2 MacBook) |
| Incremental build (proxy logic edit) | — | ~30–60s |

NFR-1.2 requires < 30MB — achievable with optimization profile below.

### Optimization Profile

```toml
[profile.release]
opt-level = "z"
lto = "fat"
codegen-units = 1
strip = "symbols"
panic = "abort"
```

### Dependency Size Drivers

- `aws-sdk-bedrockruntime` is modular (single service crate) but pulls `aws-smithy-*`, `aws-config`, and `aws-credential-types` — adds ~5–8MB stripped
- `aws-lc-rs` (default TLS crypto in AWS SDK) adds **~4MB**. Switching to `ring` saves ~4MB and compiles faster:
  ```toml
  aws-config = { version = "1", features = ["rustls-tls"] }
  ```
- reqwest default features include cookies, multipart, gzip, brotli, deflate — disable all unused:
  ```toml
  reqwest = { version = "0.12", default-features = false, features = ["json", "stream", "rustls-tls"] }
  ```
  Saves ~2–5MB and 30–60s compile time.

### Compile Time Management

- `aws-sdk-bedrockruntime` is one of the slowest-compiling AWS SDK crates — known issue (awslabs/aws-sdk-rust #113)
- For development builds, use a separate profile with `lto = false`, `codegen-units = 16`, `opt-level = 0`
- `sccache` or `cargo-chef` in Docker can cache the dependency compilation layer across rebuilds
- Keep `codegen-units = 1` only in the release profile

---

## 6. Migration Strategy

### Phase 1: Parallel Testing (No Cutover Risk)

Run Rust proxy on a different port while Python remains on 47000:

```bash
PROXY_PORT=47001 ./target/release/claude-proxy-rs
```

Verify with `lsof -i :47001 -sTCP:LISTEN -P -n` (macOS; `ss` is Linux-only).

Required env vars: same as Python proxy (`CLAUDE_CODE_OAUTH_TOKEN`, `AWS_PROFILE`, `AWS_REGION`, `COOLDOWN_SECONDS`, `REQUEST_TIMEOUT`, `BEDROCK_MAX_RETRIES`, `STAPLER_COMPRESS`) plus `PROXY_PORT=47001`.

### Phase 2: Smoke Tests Before Cutover

Minimum viable wire-compatibility checks against port 47001:

1. `curl http://localhost:47001/health` → `{"status":"ok"}` with 200
2. `curl http://localhost:47001/metrics` → valid JSON with provider counts
3. Real SSE streaming request to `/v1/messages` — verify all event types arrive and connection closes cleanly
4. OpenAI-compat path: `POST /v1/chat/completions` with a simple message
5. Manually provoke a 429 from Anthropic (or mock it) — verify Bedrock fallback triggers and cooldown activates
6. SSO expiry path: expire the SSO token, verify 503 + clear error message is returned

### Phase 3: Soak Period

Run Rust proxy on port 47001 for **2–3 days** with real Claude Code traffic (re-point a test client via `ANTHROPIC_BASE_URL=http://localhost:47001`). Compare against Python proxy on 47000:

- Request error rates (5xx, timeouts)
- SSE stream completion rates
- Bedrock fallback trigger accuracy
- Memory: `ps aux | grep claude-proxy` — expect < 50MB vs Python's ~150MB+
- CPU under concurrent streaming load

### Phase 4: LaunchAgent Cutover

Atomic swap — the plist `ProgramArguments` path changes from old binary to new:

```bash
# 1. Stop old service
launchctl unload ~/Library/LaunchAgents/com.claude-proxy.plist

# 2. Swap binary (keep backup)
cp /usr/local/bin/claude-proxy /usr/local/bin/claude-proxy.python.bak
cp ./target/release/claude-proxy-rs /usr/local/bin/claude-proxy

# 3. Reload
launchctl load ~/Library/LaunchAgents/com.claude-proxy.plist
```

Use `unload`/`load` (not `kickstart`) — the binary path change requires plist re-read.

**Port hold window**: There is a ~100ms window between `unload` and `load` where port 47000 is free. Claude Code retries on connection refused — this is safe.

**Crash loop detection**: After cutover, check `launchctl list | grep claude-proxy` for non-zero exit codes. launchd will throttle restart attempts after repeated failures, masking a crash loop.

### Phase 5: Rollback (< 10 seconds)

```bash
launchctl unload ~/Library/LaunchAgents/com.claude-proxy.plist
cp /usr/local/bin/claude-proxy.python.bak /usr/local/bin/claude-proxy
launchctl load ~/Library/LaunchAgents/com.claude-proxy.plist
```

### Key Risks Summary

| Risk | Likelihood | Mitigation |
|---|---|---|
| SSO refresh hangs under LaunchAgent | High | Return 503 immediately; require manual `aws sso login` |
| Axum 2MB body limit breaks large tool results | High | Set `DefaultBodyLimit::max(50MB)` per route |
| Content-Length mismatch after JSON mutation | High | Strip `Content-Length`/`Transfer-Encoding` before forwarding |
| reqwest connection pool exhaustion under 50+ SSE streams | Medium | Separate streaming client with `pool_max_idle_per_host(0)` |
| `WorkerGuard` dropped early → log loss on shutdown | Medium | Hold guard in `main` for process lifetime |
| Binary > 30MB (NFR-1.2) | Medium | Use `ring` over `aws-lc-rs`, disable unused reqwest features, full release profile |
| Byte-size log rotation not in `tracing_appender` | Low | Use `rolling_file` crate for 10MB × N rotation |
