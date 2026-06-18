# Implementation Plan: claude-proxy-rs

## Overview

Full Rust rewrite of `stapler-scripts/claude-proxy/` (Python/FastAPI) as a single self-contained binary using axum 0.8.9, tokio, reqwest 0.13, and aws-sdk-bedrockruntime. The binary preserves every production feature (OAuth forwarding, Bedrock fallback, SSE streaming, compression, cache alignment, session mining, shared memory) while delivering sub-100ms startup, <50MB idle RSS, and no GIL. It is a drop-in replacement for the macOS LaunchAgent on port 47000 with identical environment variables.

**Post-adversarial-review note (2026-06-17):** This plan was reviewed against the live Python proxy source. Three blockers and nine concerns were identified and addressed inline below. Key fixes: Epic 6 now scopes compression to a port of the observable `claw_compactor` contract (Rewind markers, floor, tool-pair guard) rather than novel algorithm invention; Story 4.3 corrected from `converse_stream` to `invoke_model_with_response_stream`; crate versions verified and corrected (`gaoya → lshdedup-core`, `nix features → "term"`, `tiktoken-rs → "0.5"`, `aws-smithy-http-client` pinned); tool-pair orphan guard added; system prompt edge cases specified; SSO lock guard added.

---

## Epic 1: Project Scaffold & Core HTTP Server

### Story 1.1: Cargo workspace and module layout

- [ ] Task: Create `stapler-scripts/claude-proxy-rs/Cargo.toml` with workspace root and `[package]` for the `claude-proxy-rs` binary crate
- [ ] Task: Add all dependencies to `Cargo.toml`:
  ```toml
  axum = { version = "0.8", features = ["sse"] }
  tower = "0.5"
  tower-http = { version = "0.7", features = ["trace", "timeout"] }
  reqwest = { version = "0.13", default-features = false, features = ["json", "stream", "rustls-tls"] }
  eventsource-stream = "0.2"
  tokio = { version = "1.52", features = ["full"] }
  tokio-util = { version = "0.7", features = ["sync", "task-tracker"] }
  tokio-stream = "0.1"
  futures-util = "0.3"
  aws-sdk-bedrockruntime = "1.135"
  aws-config = { version = "1.8", features = ["behavior-version-latest"] }
  # Pin aws-smithy-http-client to the version pulled transitively by aws-sdk-bedrockruntime 1.135
  # Wildcard (*) is not allowed in published crates and trips cargo-deny — pin explicitly
  aws-smithy-http-client = { version = "0.62", features = ["rustls-ring"] }
  serde = { version = "1", features = ["derive"] }
  serde_json = "1"
  moka = { version = "0.12", features = ["future"] }
  tokio-retry = "0.3"
  backoff = { version = "0.4", features = ["tokio"] }  # Retry-After header parsing (Story 5.1)
  tracing = "0.1"
  tracing-subscriber = { version = "0.3", features = ["env-filter"] }
  tracing-appender = "0.2"
  rolling-file = "0.2"
  anyhow = "1"
  uuid = { version = "1", features = ["v4"] }
  # nix 0.29: isatty is in the "term" feature group (not "unistd") — "unistd" controls getpid/getuid
  nix = { version = "0.29", features = ["term"] }
  # simhash: use the "simhash" crate by Michael Sproul (not simsearch/rsim)
  # verify with: cargo search simhash | grep "Simhash fingerprint"
  simhash = "0.1"
  # gaoya does not have a 0.2 release on crates.io; use lshdedup-core which is purpose-built for dedup
  # Alternative: implement 128-function MinHash directly using sha2 + bitwise ops
  lshdedup-core = "0.1"
  # tiktoken-rs is at 0.5.x on crates.io — not 0.12; cl100k_base counts OpenAI tokens not Claude tokens;
  # use only for approximate relative comparisons; switch to byte_len/4 for cache threshold checks
  tiktoken-rs = "0.5"
  regex = "1"
  once_cell = "1"
  chrono = { version = "0.4", features = ["serde"] }
  ```
- [ ] Task: Add release profile to `Cargo.toml`:
  ```toml
  [profile.release]
  opt-level = "z"
  lto = "fat"
  codegen-units = 1
  strip = "symbols"
  panic = "abort"
  ```
- [ ] Task: Add dev profile for fast incremental builds:
  ```toml
  [profile.dev]
  opt-level = 0
  lto = false
  codegen-units = 16
  ```
- [ ] Task: Create module skeleton under `src/`:
  ```
  src/
    main.rs
    config.rs
    auth.rs
    fallback.rs
    dashboard.rs
    providers/
      mod.rs
      anthropic.rs
      bedrock.rs
    compression/
      mod.rs
      engine.rs
      rewind.rs
      smart_crusher.rs
      code_compressor.rs
      text_compressor.rs
    metrics/
      mod.rs
      counters.rs
      histogram.rs
    system_prompt/
      mod.rs
      cache_aligner.rs
      verbosity.rs
    learn/
      mod.rs
      transcript.rs
      patterns.rs
    memory/
      mod.rs
      store.rs
      dedup.rs
  ```
- [ ] Task: Create `Makefile` with targets: `build`, `install`, `dev`, `start`, `stop`, `restart`, `status`, `logs`, `test`; `dev` target runs `PROXY_PORT=47001 cargo run` against the live system with Python proxy still on 47000

### Story 1.2: Configuration via environment variables

- [ ] Task: Implement `src/config.rs` — read all env vars at startup with defaults:
  - `PROXY_PORT` (default 47000)
  - `COOLDOWN_SECONDS` (default 300)
  - `REQUEST_TIMEOUT` (default 300)
  - `BEDROCK_MAX_RETRIES` (default 3)
  - `STAPLER_COMPRESS` (default 1)
  - `COMPRESS_FLOOR_BYTES` (default 4096)
  - `CACHE_ALIGNER` (default 1)
  - `VERBOSITY_LEVEL` (default 2, 0=off)
  - `MEMORY_MAX_ENTRIES` (default 1000)
  - `AWS_PROFILE`, `AWS_REGION`, `CLAUDE_CODE_OAUTH_TOKEN`
- [ ] Task: Add `AppState` struct holding `Arc<FallbackState>`, `Arc<Metrics>`, `Arc<RewindCache>`, `Arc<MemoryStore>`, `CancellationToken`, `TaskTracker`, streaming `reqwest::Client`, pooled `reqwest::Client`; derive `Clone`

### Story 1.3: Logging subsystem

- [ ] Task: Implement `init_logging()` in `src/main.rs` using `rolling-file` + `tracing_appender::non_blocking`. The `rolling-file` crate's `BasicRollingFileAppender` implements `std::io::Write` — wrap it in `tracing_appender::non_blocking(appender)` to get a `(NonBlocking, WorkerGuard)`. `NonBlocking` implements the `MakeWriter` trait required by `tracing_subscriber::fmt::Layer::with_writer(writer)`. This adapter pattern is what makes size-based rotation work with tracing:
  - App log: `/tmp/claude-proxy.app.log` 10MB × 10 files (`RollingConditionBasic::new().max_size(10*1024*1024)`, keep 10)
  - HTTP log: `/tmp/claude-proxy.http.log` 10MB × 5 files
  - Route events to correct file via `filter_fn` predicates on `tracing_subscriber::registry()` multi-layer (target `"http_access"` → http file; everything else → app file)
- [ ] Task: Store `WorkerGuard` handles in `main` scope for process lifetime (never drop early — dropping flushes and closes the writer channel, causing log loss on shutdown per pitfalls research)
- [ ] Task: Log slow requests (>30s) and blocking requests (>60s) with distinct log levels (WARN vs ERROR)

### Story 1.4: axum router and shutdown wiring

- [ ] Task: Build `Router` with all routes in `src/main.rs`; apply `DefaultBodyLimit::max(50_000_000)` to all message routes (NOT globally — only `/v1/messages`, `/chat/completions`, `/v1/chat/completions`)
- [ ] Task: Apply `TraceLayer` outermost + `TimeoutLayer` (5s handler startup, not body stream)
- [ ] Task: Wire graceful shutdown: `CancellationToken` broadcast into SSE handlers via `take_until`; `TaskTracker` drain counter; `axum::serve(...).with_graceful_shutdown(signal_future)`; 30s hard timeout via `tokio::time::timeout`
- [ ] Task: Implement `GET /` returning proxy info JSON; `GET /health` returning `{"status":"ok"}` with 200
- [ ] Task: Build `tokio::runtime::Builder` explicitly in `main()` — `new_multi_thread().enable_all().thread_name("proxy-worker")` — not the `#[tokio::main]` macro

---

## Epic 2: Core Proxy — Request Pipeline

### Story 2.1: Request body extraction and cleaning

- [ ] Task: Implement request body extraction as `Bytes` (not `Json<T>` — avoid typed deserialization), then `serde_json::from_slice` (zero-copy, no UTF-8 allocation overhead vs `from_str`)
- [ ] Task: Implement `clean_request_body(body: &mut Value)` in `src/providers/mod.rs`:
  - Strip top-level fields: `defer_loading`, `input_examples`, `custom`, `cache_control`, `output_config`, `context_management`
  - Walk `messages[*].content[*]` and `retain` only blocks where `type` is in `{"text", "image", "document", "search_result", "tool_use", "tool_result"}` — remove `tool_reference`
  - Strip `cache_control`, `defer_loading`, `input_examples`, `custom` from each element of `tools[*]`
- [ ] Task: Strip `Content-Length` and `Transfer-Encoding` from forwarded headers before building the outgoing reqwest request (prevents mismatch after body mutation)
- [ ] Task: Generate 8-char request ID with `uuid::Uuid::new_v4().to_string()[..8]`; return in `X-Request-ID` response header

### Story 2.2: OpenAI compatibility translation

- [ ] Task: Implement `translate_openai_to_anthropic(openai_body: Value) -> Value` in `src/providers/mod.rs`: map `messages`, `model`, `max_tokens` (default 1024), `temperature`, `stream`
- [ ] Task: Implement `translate_anthropic_to_openai(anthropic_resp: Value) -> Value` for non-streaming path: wrap in `choices[0].message` with `finish_reason = "stop"`
- [ ] Task: Route `POST /chat/completions` and `POST /v1/chat/completions` through translation layer before and after main message pipeline
- [ ] Task: Implement `GET /v1/models` endpoint returning the same model list as Python proxy

### Story 2.3: Non-streaming request path

- [ ] Task: Full-body buffering for non-streaming: read body, clean, compress (if enabled), system-prompt-pipeline, forward, receive full response `Value`, return as `Json`
- [ ] Task: Log per-request structured fields: `request_id`, `model`, `max_tokens`, `stream`, `message_count`, `msg_types`, `beta`

### Story 2.4: SSE streaming passthrough

- [ ] Task: Use dedicated `streaming_client: reqwest::Client` built with `pool_max_idle_per_host(0)` (prevents connection pool exhaustion under 50+ concurrent streams per pitfalls research); `.connect_timeout(5s)` + `.read_timeout(30s)` — NEVER `.timeout()` (wall-clock deadline kills long SSE streams)
- [ ] Task: Pipe `reqwest::Response.bytes_stream().eventsource()` → `axum::response::sse::Sse<S>` via `StreamExt::map`; preserve `event`, `data`, `id` fields from each `eventsource_stream::Event`
- [ ] Task: Add `KeepAlive::new().interval(Duration::from_secs(15))` to `Sse::new(stream)` (guards against half-open connections on Bedrock which may not send native pings)
- [ ] Task: Set SSE response headers: `Cache-Control: no-cache`, `X-Accel-Buffering: no`, `X-Request-ID`
- [ ] Task: Wire `CancellationToken` into SSE stream via `take_until(token.cancelled())` so shutdown emits a terminal `event: error / data: {"type":"server_shutdown","retry":5000}` event before stream closes
- [ ] Task: Register `TaskTracker::token()` guard in each SSE handler so graceful shutdown waits for all active streams

### Story 2.5: Endpoint error handlers and missing endpoints

- [ ] Task: Handle `POST //v1/messages` (double-slash) and `POST /v1/v1/messages` (double-v1) with 400 + descriptive error message (matches Python proxy behavior)
- [ ] Task: Implement `POST /v1/messages/dry-run` — run compression pipeline only, no upstream call, return before/after token counts and compressed body
- [ ] Task: Implement `POST /v1/messages/count_tokens` — passthrough to Anthropic API only (Bedrock does not support token counting); record `count_tokens_total` and `count_tokens_failures` counters; handle 401 gracefully (known Claude Code bug — log at INFO not ERROR)
- [ ] Task: Implement `POST /api/event_logging/batch` — LiteLLM telemetry stub; accept body and return `{"status":"success"}` silently; prevents 404 errors on LiteLLM side
- [ ] Task: Implement `GET /requests` (no path parameter) — return last 100 request details from ring buffer (newest first); matches Python proxy `GET /requests` endpoint at line 1135

---

## Epic 3: Anthropic Provider

### Story 3.1: Anthropic HTTP client

- [ ] Task: Implement `src/providers/anthropic.rs` — `AnthropicProvider` struct holding base URL (default `https://api.anthropic.com`)
- [ ] Task: Forward headers: `Authorization` (from `Bearer sk-ant-oat-*`), `anthropic-version`, `anthropic-beta` — pass through as-is without modification
- [ ] Task: Model name normalization: strip `us.anthropic.` prefix and `:v1:0` suffix if present (Claude Code sends Bedrock-format model names to the Anthropic endpoint occasionally)
- [ ] Task: Non-streaming path: `POST /v1/messages`, deserialize response `Value`, return to handler
- [ ] Task: Streaming path: forward as SSE using dedicated streaming client, return `reqwest::Response` for `bytes_stream()` extraction in caller

### Story 3.2: Authentication

- [ ] Task: Implement `src/auth.rs` — extract token from `Authorization: Bearer <token>` header; fall back to `CLAUDE_CODE_OAUTH_TOKEN` env var; map `sk-ant-oat-*` tokens as OAuth (forward as `Authorization: Bearer`) and `sk-ant-api-*` tokens as API key (forward as `x-api-key`)
- [ ] Task: Return `AuthError` (→ 401) when no token found and env var is unset

---

## Epic 4: Bedrock Provider

### Story 4.1: AWS SDK client setup

- [ ] Task: Implement `src/providers/bedrock.rs` — build `aws_sdk_bedrockruntime::Client` from `aws_config::load_from_env().await` at startup; store in `AppState`
- [ ] Task: Add `aws-smithy-http-client = { features = ["rustls-ring"] }` to Cargo.toml (REQUIRED — prevents "no process-level CryptoProvider" panic at startup from TLS conflict between aws-lc-rs and ring, per stack research GH #1264)

### Story 4.2: Model name normalization and beta filtering

- [ ] Task: Implement `normalize_bedrock_model(model: &str) -> String`: strip Anthropic-format model names and add `us.anthropic.` prefix + version suffix; load `config/bedrock_models.json` file (same as Python); hardcoded fallback map for common models
- [ ] Task: Port `BEDROCK_BETA_COMPATIBILITY` table from `providers/bedrock.py` to a `static BEDROCK_BETA_COMPAT: LazyLock<HashMap<&str, Vec<&str>>>` in Rust; filter `anthropic-beta` header value against this table using the normalized model name; convert surviving betas to `anthropic_beta: [...]` array in request body
- [ ] Task: Implement thinking budget validation before forwarding to Bedrock:
  - If `budget_tokens > max_tokens` and `max_tokens < 1024`: remove `thinking` block entirely
  - If `budget_tokens > max_tokens` and `max_tokens >= 1024`: cap `budget_tokens` to `max_tokens`
  - If `budget_tokens < 1024`: raise to 1024

### Story 4.3: invoke_model_with_response_stream streaming loop

**Correction from adversarial review:** `converse_stream` uses a different request format and different event type names than the Anthropic API; it cannot accept `anthropic_version`, `thinking`, or `anthropic_beta` fields in the body. The Python proxy uses `invoke_model_with_response_stream` with a raw JSON body. Use `invoke_model_with_response_stream` to match the Python proxy.

- [ ] Task: Use `client.invoke_model_with_response_stream()` with `.model_id(&bedrock_model_id).body(Blob::new(json_bytes)).content_type("application/json")` — the body is the Anthropic-format JSON (after beta filtering and field cleaning); this matches Python proxy `bedrock.py` line 817
- [ ] Task: Iterate the response via `response.body` (a public field returning `EventReceiver<ResponseStream, ResponseStreamError>`); use `stream.recv().await?` loop (no `StreamExt` — `EventReceiver` does NOT implement `futures::Stream`); always include `_ => {}` arm on the non-exhaustive enum
- [ ] Task: Each `ResponseStream::Chunk(chunk)` contains raw bytes; parse `chunk.bytes` as `serde_json::Value`; the event data is Anthropic SSE JSON format (same as Anthropic direct) so re-emit as `data: <json>\n\n` without translation
- [ ] Task: Extract `amazon-bedrock-invocationMetrics` from `message_stop` event JSON field; record `invocationLatency` and `firstByteLatency` in metrics; emit `ping` keep-alive comments every 15s if no events received

### Story 4.4: AWS SSO credential watcher

- [ ] Task: Implement `CredentialWatcher` in `src/providers/bedrock.rs`:
  - Read `~/.aws/sso/cache/<hash>.json` files using `tokio::fs::read_to_string` (async — never `std::fs`)
  - Parse `expiresAt` RFC3339 field from each file; find the soonest expiry
  - Cache result with 30s TTL using `moka::future::Cache<(), CredentialStatus>`
- [ ] Task: Detect no-TTY condition before running `aws sso login`: use `nix::unistd::isatty(std::io::stdin())` with `nix = { features = ["term"] }` (NOT `"unistd"` — `isatty` moved to the `"term"` feature group in nix 0.27+); if no TTY → immediately return 503 with `{"error":"bedrock_credentials_expired","action":"run 'aws sso login --profile <profile>'"}`
- [ ] Task: SSO subprocess lock: hold an `OnceLock<tokio::sync::Mutex<()>>` process-wide; acquire the mutex before spawning `aws sso login` so only one subprocess runs at a time even under concurrent requests (prevents multiple browser tabs opening — the Python proxy uses `SSO_LOCK_FILE` with `O_CREAT|O_EXCL` for the same purpose); release on subprocess completion
- [ ] Task: If TTY present and credentials expiring within 5 minutes → acquire SSO lock → `tokio::process::Command::new("aws").args(["sso","login","--profile",profile]).status().await`; log outcome; release lock; proceed with request
- [ ] Task: On `ExpiredTokenException` mid-stream — emit SSE error event with credentials-expired message; do NOT add Bedrock to cooldown

---

## Epic 5: Fallback State Machine

### Story 5.1: Provider state and cooldown

- [ ] Task: Implement `src/fallback.rs` with `ProviderState` enum (`Normal` | `Cooldown { until: Instant }`) and `FallbackState { inner: Arc<RwLock<ProviderState>>, cooldown_secs: u64 }`
- [ ] Task: Implement methods: `should_use_fallback()` (read lock), `enter_cooldown()` (write lock), `try_exit_cooldown()` (write lock with atomic check-and-clear); use `tokio::sync::RwLock` (not `std::sync` — read lock across await points)
- [ ] Task: Bedrock invariant: no `enter_cooldown` call path for Bedrock provider; Bedrock only uses `tokio-retry` for transient timeout errors (not for 429/auth errors)
- [ ] Task: Log `Retry-After` header value from Anthropic 429 responses and use it as the cooldown duration when present (use `backoff` crate for `Retry-After` parsing as supplemental to the custom state machine)
- [ ] Task: On 429 from Anthropic: call `enter_cooldown()`, record `fallback` metric, route next request to Bedrock

### Story 5.2: Retry orchestration

- [ ] Task: Implement `dispatch_with_fallback(body, auth, headers, request_id)` in `src/fallback.rs` — iterate providers, skip cooldown providers, use `tokio-retry` for transient errors on Bedrock (`ExponentialBackoff` 2s/4s/8s up to `BEDROCK_MAX_RETRIES`)
- [ ] Task: Error classification: `ValidationError` (4xx) → return immediately, no fallback; `AuthError` (401) → return immediately; `RateLimitError` (429) → Anthropic cooldown + fallback; `TimeoutError` → Bedrock retry only; `ModelUnsupportedError` → skip provider silently
- [ ] Task: Both streaming and non-streaming paths share the same dispatch logic; streaming returns a `BoxStream<Result<Event, BoxError>>`

---

## Epic 6: Compression Engine

**Scope note from adversarial review:** The Python proxy delegates all compression to the third-party `claw_compactor` Python library (`FusionEngine`). There is no Rust equivalent. Implementing the full 14-stage FusionEngine pipeline from scratch (SmartCrusher field-frequency analysis, tree-sitter AST compression, etc.) is novel research, not a porting task. Epic 6 is therefore scoped to: (a) the observable API contract that the Python proxy exposes at the `/v1/messages` boundary — floor check, double-compression guard, tool-pair orphan guard, Rewind marker detection, Rewind tool injection, compression metrics; and (b) a lightweight native text compressor that provides meaningful compression without requiring algorithmic invention. The algorithmic compression stages (SmartCrusher, CodeCompressor, full FusionEngine pipeline) are deferred to a future Epic 6b after the base proxy is running.

### Story 6.1: Compression pipeline framework and guards

- [ ] Task: Define `CompressionContext` struct in `src/compression/engine.rs` carrying `messages: Vec<Value>`, `byte_len: usize`, `stats: CompressionStats`; pipeline runs stages sequentially, each stage returns modified `Vec<Value>` or passes through unchanged; stages are pluggable (register via `Vec<Box<dyn CompressorStage>>`) so algorithmic stages can be added later without restructuring
- [ ] Task: Implement compression floor check: skip all compression if `byte_len < COMPRESS_FLOOR_BYTES` (env-configured, default 4096); return `stats.skipped = "below_floor"`
- [ ] Task: Implement double-compression guard: scan all message text content for `[N items compressed to M. Retrieve: hash=XXXX]` pattern using `LazyLock<Regex>`; skip pipeline if any match found; return `stats.skipped = "already_compressed"`
- [ ] Task: Implement `_validate_tool_pairs(messages: &[Value]) -> (bool, Vec<String>)` — port of Python `compactor.py` lines 167-214: for each `user` message, collect `tool_result.tool_use_id` values; verify the preceding `assistant` message has matching `tool_use.id` values; return `(false, orphaned_ids)` if any tool_result has no matching tool_use. If validation fails, revert to original messages and return `stats.skipped = "tool_pair_broken"`. **Without this guard Bedrock and Anthropic reject requests with `ValidationException: unexpected tool_use_id found in tool_result blocks` — this is a documented production failure in the Python proxy's CLAUDE.md.**
- [ ] Task: `tool_use` and `tool_result` blocks pass through all stages untouched (FR-5.4 hard requirement); only `text` blocks in `user` and `assistant` messages are eligible for compression

### Story 6.2: Native text compressor (in-scope for Phase 1)

The native text compressor handles the most common high-value case: long log output and repeated content in tool results. Algorithm is fully specified here (no ambiguity):

- [ ] Task: Implement `src/compression/text_compressor.rs` with the following fully-specified stages:
  - **ANSI strip**: remove all ANSI escape sequences matching `\x1b\[[0-9;]*[mGKHFJABCDEFGHfils]` using `LazyLock<Regex>`
  - **Log dedup**: scan lines sequentially; when the same line appears consecutively, fold to `<line> (×N)` where N is the repeat count; minimum 2 repetitions to trigger; never fold lines that are empty or contain only whitespace
  - **Blank line normalization**: collapse 3+ consecutive blank lines to 2 blank lines
  - **Output**: return the transformed string; if output is longer than input, return the original unchanged
- [ ] Task: Route only `text` blocks from `user` messages (not `assistant` messages — compressing model output is lossy and breaks Rewind) through the text compressor; skip blocks shorter than 256 bytes

### Story 6.3: SmartCrusher and CodeCompressor (deferred to Epic 6b)

These stages require algorithmic specification work that is out of scope for the initial proxy rewrite. Defer until Epic 6b. For Phase 1, the `ContentType` router simply returns `TextCompressor` for all eligible blocks.

- [ ] Task: Add `// TODO(epic-6b): SmartCrusher for JSON arrays` and `// TODO(epic-6b): CodeCompressor for code blocks` stub comments in `src/compression/engine.rs` to mark the extension points; add `detect_content_type()` returning `ContentType::Text` for all inputs as a placeholder

### Story 6.4: Rewind store

- [ ] Task: Implement `src/compression/rewind.rs` — `moka::future::Cache<String, Arc<Vec<u8>>>` built with `.max_capacity(500).time_to_live(Duration::from_secs(600))`; wrap values in `Arc<Vec<u8>>` (avoids payload copy on cache hit)
- [ ] Task: `rewind_store(hash: &str, original: Vec<u8>)` — async insert
- [ ] Task: `rewind_retrieve(hash: &str) -> Option<Arc<Vec<u8>>>` — sync get (only clones the `Arc` pointer)
- [ ] Task: Inject `rewind_retrieve` tool definition into `tools[]` array when Rewind markers are present in compressed messages (idempotent — check for existing definition before inserting)

### Story 6.5: Compression metrics

- [ ] Task: Track `tokens_before`, `tokens_after`, `requests_compressed`, `tokens_saved` using `AtomicU64` counters in `src/metrics/counters.rs`; use `tiktoken-rs 0.5` for approximate token counting (cl100k_base encoding — note: this is the OpenAI tokenizer, not Claude's; counts will be approximate but consistent for ratio comparison; for absolute accuracy use `byte_len / 4` approximation which is what Story 7.1 already uses for cache threshold)
- [ ] Task: Compute `avg_compression_ratio` as `tokens_saved / tokens_before` on read

---

## Epic 7: System Prompt Pipeline (CacheAligner + Verbosity Steering)

### Story 7.1: Unified system prompt transformation

- [ ] Task: Implement `transform_system_prompt(body: &mut Value, verbosity_level: u8, is_continuation: bool)` in `src/system_prompt/mod.rs` — single pass, not two separate passes (per headroom-features research Decision 1: independent passes can corrupt each other's output)
- [ ] Task: Pipeline order within the single pass — handle all four `system` field states explicitly:
  1. **No `system` field at all** (common — Claude Code frequently omits it): if `is_continuation && verbosity_level > 0`, create `system: [{"type":"text","text":"<verbosity_suffix>"}]` with NO `cache_control` (nothing to cache); if verbosity off, leave `system` absent entirely
  2. **`system` is a plain string**: convert to array `[{"type":"text","text":"<original>"}]`; proceed to step 3
  3. **`system` is already an array**: use as-is
  4. Detect volatile content in last original block text (ISO 8601 timestamps `\d{4}-\d{2}-\d{2}T`, UUIDs `[0-9a-f]{8}-[0-9a-f]{4}` via `LazyLock<Regex>`) — if found, do NOT add `cache_control` and log a warning at DEBUG level
  5. **Below threshold (estimated tokens < 1,024, i.e., last original block byte_len < 4,096)**: do NOT add `cache_control`; if `is_continuation && verbosity_level > 0`, still append verbosity suffix as new uncached block
  6. **Stable and ≥ 1,024 estimated tokens**: add `cache_control: {"type":"ephemeral"}` to the last original block; if `is_continuation && verbosity_level > 0`, append verbosity suffix as new uncached block after it
  7. Re-serialize `system` as the updated array
- [ ] Task: Handle incoming system array that already has `cache_control` on last block: keep the cache marker on that original block; append verbosity suffix as a new uncached block after it (do not move or duplicate the `cache_control`)

### Story 7.2: CacheAligner

- [ ] Task: Implement `src/system_prompt/cache_aligner.rs` — normalize tool definitions for cache stability: sort `tools[]` array alphabetically by `name`, sort parameter `properties` keys canonically (alphabetical); this prevents Go/Swift JSON key randomization from busting cache
- [ ] Task: Configurable via `CACHE_ALIGNER` env var (default on); if disabled, skip normalization entirely
- [ ] Task: Track `cache_hits_estimated` (requests where `cache_read_input_tokens > 0` extracted from SSE `message_start` event) and `cache_misses_estimated` in `AtomicU64` counters

### Story 7.3: Verbosity steering

- [ ] Task: Implement `src/system_prompt/verbosity.rs` — level-to-suffix map:
  - Level 1: `"Be concise."`
  - Level 2: `"Be terse. Skip preamble. Answer directly without restating context."`
  - Level 3: `"Be extremely terse. One sentence per idea. No preamble, no summary, no context restatement. Code only when asked."`
- [ ] Task: Implement `is_continuation_turn(last_human_message: &Value) -> bool`: count `tool_result` blocks vs `text` blocks in last human message content array; continuation = `tool_results > 0 && text_blocks == 0`
- [ ] Task: Verbosity suffix only applied on continuation turns (FR-9.2); new question turns receive no suffix
- [ ] Task: Track `verbosity_applied_count` metric and placeholder `output_tokens_saved_estimate` (always 0 — counterfactual, note confidence band in metrics JSON)

---

## Epic 8: headroom learn — Session Mining

### Story 8.1: JSONL transcript parser

- [ ] Task: Implement `src/learn/transcript.rs` — iterate `~/.claude/projects/` subdirectories; for each `*.jsonl` file, parse line-by-line with `serde_json::from_str::<TranscriptEntry>` per line; silently skip lines that fail to deserialize (schema is unstable per FR-8 notes)
- [ ] Task: Define minimal `TranscriptEntry` struct with `#[serde(rename)]` for camelCase fields; use `serde_json::Value` for `message.content` (untagged string-or-array)
- [ ] Task: Skip entries where `isSidechain == true` (sub-agent messages from Agent tool spawns — not correction signals from the human user)
- [ ] Task: Extract only `type == "user"` entries with plain-string `message.content` under ~300 chars for correction pattern matching

### Story 8.2: Correction pattern detection

- [ ] Task: Implement `src/learn/patterns.rs` — three `LazyLock<Regex>` tiers:
  - `CORRECTION_DIRECT`: explicit negation/redirect phrases (`"no, don't"`, `"stop doing"`, `"always use X instead"`)
  - `CORRECTION_FRUSTRATION`: frustration signals (`"I told you to not"`, `"that's wrong"`, `"how many times"`, `"read the instructions again"`)
  - Structural Tier 3: walk `parentUuid` linked list; flag `assistant(tool_use) → user(tool_result is_error=true)` loops repeating ≥ 2 consecutive times for same tool name
- [ ] Task: Score corrections by recency (recent sessions weighted 2×) and frequency (appears in 3+ separate sessions → strong candidate); output `Vec<LearnedCorrection>` with text, source session IDs, confidence score
- [ ] Task: Write staging output to `/tmp/headroom-learn-staging.md` — NEVER write to `~/.claude/projects/*/memory/` or `CLAUDE.md` without explicit `learn-apply` confirmation

### Story 8.3: Admin API endpoints

- [ ] Task: Implement `GET /admin/learn-preview` — run transcript parsing and pattern detection, return `Vec<LearnedCorrection>` as JSON without writing anything to disk
- [ ] Task: Implement `POST /admin/learn-apply` — write staged corrections to `/tmp/headroom-learn-staging.md` only; return count of patterns written; require explicit user confirmation (no auto-write to memory files)
- [ ] Task: Implement `POST /admin/learn-verbosity` — analyze output lengths from past sessions; suggest optimal `VERBOSITY_LEVEL` setting based on session patterns; return recommendation JSON

---

## Epic 9: Cross-Agent SharedContext Memory

### Story 9.1: Memory store

- [ ] Task: Implement `src/memory/store.rs` — `moka::future::Cache<String, MemoryEntry>` with `.max_capacity(MEMORY_MAX_ENTRIES).time_to_live(duration)`; `MemoryEntry` holds: `value_compressed: Arc<Vec<u8>>`, `value_original: Arc<Vec<u8>>`, `agent_id: String`, `user_agent: String`, `created_at: DateTime<Utc>`, `size_before: usize`, `size_after: usize`
- [ ] Task: Per-entry TTL: default 24h, configurable per-entry via request header `X-TTL-Seconds`; LRU eviction when capacity exceeded (moka handles this automatically)
- [ ] Task: Compress stored value through the FR-5 compression pipeline before storing (`size_after` = compressed size)

### Story 9.2: Similarity deduplication

**Crate note from adversarial review:** `gaoya` is not at 0.2 on crates.io (exists at 0.1.x at best with unstable API). Use `lshdedup-core` instead, or implement the MinHash tier directly using `sha2` + bitwise operations. Verify `simhash` crate identity — use the one by Michael Sproul that provides a `Simhash` trait (not `simsearch` or `rsim`).

- [ ] Task: Implement `src/memory/dedup.rs` — `SimHashIndex` holding `HashMap<String, u64>` (key → SimHash fingerprint); on each `PUT`, compute SimHash of new value, XOR against all existing fingerprints, count set bits (Hamming distance); if any entry has Hamming ≤ 6 → escalate to MinHash tier; this eliminates the vast majority of pairwise comparisons at negligible O(1) cost
- [ ] Task: MinHash tier using `lshdedup-core` (or direct implementation): 128 hash functions, ~16 bands configuration for ≈0.94 Jaccard threshold on word 5-shingles; wrap index in `Arc<Mutex<>>` (not `Send` by default); verify the specific API from `lshdedup-core` docs before writing task details
- [ ] Task: Wrap MinHash signing in `tokio::task::spawn_blocking` (CPU-bound; must not block async runtime — MinHash signing on 100KB inputs takes 1-5ms)
- [ ] Task: Exact Jaccard verification step: when MinHash finds a candidate, compute exact Jaccard on word 5-shingles; if `>= 0.95` → update existing entry (provenance + timestamp updated, same key), return 200 with `{"action":"updated","key":"existing_key"}`; else → insert new entry
- [ ] Task: **Never use `strsim::normalized_levenshtein` on large inputs** — it is O(n²) with no early exit; benchmarks show ~10 seconds per 100KB comparison, which would block the async runtime

### Story 9.3: Memory HTTP endpoints

- [ ] Task: Implement `PUT /memory/{key}` — store value, run dedup, return `{"action":"created"|"updated","key":"...","size_before":N,"size_after":M}`
- [ ] Task: Implement `GET /memory/{key}` — return compressed summary; `GET /memory/{key}?full=true` — return original bytes
- [ ] Task: Implement `GET /memory` — list all keys with metadata: `agent_id`, `user_agent`, `size_before`, `size_after`, `created_at`, `ttl_remaining_secs`
- [ ] Task: Record `X-Agent-ID` header (or `User-Agent` fallback) as `agent_id` in `MemoryEntry` for agent provenance tracking

---

## Epic 10: Metrics & Dashboard

### Story 10.1: Atomic counters and rolling histogram

- [ ] Task: Implement `src/metrics/counters.rs` — `pub static COUNTERS: Counters` struct of `AtomicU64` fields: `req_anthropic`, `req_bedrock`, `req_failed`, `err_timeout`, `err_auth`, `err_rate_limit`, `fallback_count`, `tokens_before`, `tokens_after`, `requests_compressed`, `cache_hits_estimated`, `cache_misses_estimated`, `verbosity_applied`, `count_tokens_total`, `count_tokens_failures`
- [ ] Task: Implement `src/metrics/histogram.rs` — `RollingLatency` struct with `Mutex<VecDeque<(Instant, f64)>>` and 15-minute sliding window; `record(secs: f64)`, `percentile(p: f64) -> Option<f64>`, `chart_data() -> Vec<(u64, f64)>` (30s buckets); `OnceLock<RollingLatency>` initialized in `main()`
- [ ] Task: Implement rolling 15-min RPM counter: `VecDeque<(Instant, u32)>` one entry per second, pruned on read
- [ ] Task: Ring buffer for last 100 request details (for dashboard "Recent Requests" table): `Mutex<VecDeque<RequestDetail>>`; `RequestDetail` holds `request_id`, `model`, `provider`, `duration_ms`, `first_byte_ms`, `tokens_before`, `tokens_after`, `compressed`, `stream`, `msg_types`, `message_count`, `timestamp`

### Story 10.2: Metrics endpoint

- [ ] Task: Implement `GET /metrics` returning full JSON struct matching current Python proxy `/metrics` output shape (wire-compatible):
  - `summary`: `total_requests`, `total_success`, `total_errors`, `success_rate`, `error_rate`, `total_fallbacks`
  - `providers`: per-provider request/error counts
  - `cooldowns`: `{anthropic: {cooling_down: bool, remaining_seconds: N}}`
  - `rpm_data`: 15-min chart buckets
  - `duration_distribution`: histogram buckets
  - `compression`: token stats, avg ratio
  - `recent_requests`: last 20 `RequestDetail` entries
  - `recent_errors`: last 20 error events
  - `count_tokens`: total, failures, failure_rate, last_count, last_model
  - `provider_latency`: per-provider avg_duration_ms, avg_first_byte_ms
- [ ] Task: Implement `src/metrics/error_tracker.rs` — `ErrorTracker` struct with `Mutex<VecDeque<ErrorRecord>>` (max 100 entries) and `HashMap<String, AggregatedError>` keyed by fingerprint; `ErrorRecord` holds `timestamp`, `error_type`, `provider`, `model`, `message`; fingerprint = first 8 chars of `sha256(error_type + ":" + first_100_chars_of_message)`; `AggregatedError` holds `fingerprint`, `error_type`, `provider`, `count`, `first_seen`, `last_seen`, `message`; expose `push(record)`, `get_recent(limit) -> Vec<ErrorRecord>`, `get_summary(limit) -> Vec<AggregatedError>`. The Python proxy has `error_tracker.py` with 38 test functions; this is a distinct module, not just a few counters. **Flagged by validation plan: must task out before Epic 10 implementation.**
- [ ] Task: Implement `GET /errors/summary` endpoint calling `error_tracker.get_summary(100)` returning `{"errors": [...], "total": N}` — matches Python proxy `GET /errors/summary` response shape
- [ ] Task: Implement `GET /requests/{request_id}?stage=original|compressed` endpoint — look up request body snapshots from a ring buffer `moka::sync::Cache<String, RequestSnapshot>` (200 entries, 30-min TTL); `RequestSnapshot` holds original and compressed body `Arc<Value>`

### Story 10.3: Dashboard HTML

- [ ] Task: Port dashboard HTML/JS from Python proxy `main.py` `DASHBOARD_HTML` constant into `src/dashboard.rs` as a `const &str`; return from `GET /dashboard` as `text/html; charset=utf-8`; the JS polls `/metrics` and `/errors/summary` every 30s
- [ ] Task: Verify Chart.js CDN URL remains the same (`chart.js@4.4.0`) and all chart IDs match the JS selectors
- [ ] Task: Tokio event loop lag probe (replacement for Python's asyncio lag): spawn a background task at startup that sleeps 1s via `tokio::time::sleep(Duration::from_secs(1))` and measures wall-clock skew (`start.elapsed().as_millis() - 1000`); record to a rolling `VecDeque<(Instant, f64)>` in `LATENCY`; expose as `current_lag_ms` and `lag_data` fields in `/metrics` response. This is semantically equivalent to the Python `_monitor_event_loop_lag()` function and keeps the dashboard lag chart working. Note: Tokio's multi-thread runtime distributes I/O across worker threads, so measured lag here reflects scheduling skew rather than single-threaded event loop contention.
- [ ] Task: Add `current_lag_ms` and `lag_data` (30s buckets over 15 min) to the `/metrics` JSON struct so dashboard JS `data.current_lag_ms` and `data.lag_data` references resolve without 404 or undefined errors
- [ ] Task: Add `/admin/learn-preview` results panel to dashboard HTML (collapsible section showing staged corrections)

---

## Epic 11: Testing & Migration

### Story 11.1: Integration test suite

- [ ] Task: Create `tests/integration/` with axum `TestClient` (or `axum-test` crate); all tests bind to port 47001 to avoid conflict with running Python proxy
- [ ] Task: Test `GET /health` → `{"status":"ok"}` 200
- [ ] Task: Test `GET /metrics` → valid JSON with expected top-level keys
- [ ] Task: Test `POST /v1/messages` non-streaming with mock Anthropic upstream (mockito or wiremock-rs); verify `X-Request-ID` header returned
- [ ] Task: Test `POST /v1/messages` streaming with mock upstream emitting 3 SSE events; verify all 3 arrive at client, connection closes cleanly
- [ ] Task: Test body cleaning: send request with `defer_loading`, `tool_reference`, `context_management` fields; verify they are absent in forwarded request (via mock server capture)
- [ ] Task: Test cooldown state machine: mock Anthropic returning 429; verify second request goes to Bedrock mock; verify cooldown clears after configured duration
- [ ] Task: Test compression floor: body < 4096 bytes passes through unmodified (no Rewind markers)
- [ ] Task: Test double-compression guard: body with existing Rewind marker passes through unmodified
- [ ] Task: Test system prompt pipeline: verify 2-block array output with `cache_control` on block 0 and verbosity suffix on block 1
- [ ] Task: Test `PUT /memory/{key}` + `GET /memory/{key}?full=true` round-trip
- [ ] Task: Test `GET /admin/learn-preview` with synthetic JSONL transcript fixtures containing Tier 1 correction patterns

### Story 11.2: Smoke tests and soak period

- [ ] Task: Manual smoke test checklist (encoded in `Makefile smoke` target):
  1. `curl http://localhost:47001/health` → `{"status":"ok"}`
  2. `curl http://localhost:47001/metrics` → valid JSON
  3. Real SSE request to `/v1/messages` — verify all event types arrive
  4. `POST /v1/chat/completions` OpenAI-compat path
  5. Dashboard renders at `http://localhost:47001/dashboard`
- [ ] Task: Run on port 47001 for 2–3 days alongside Python proxy on 47000; compare error rates, memory (`ps aux | grep claude-proxy-rs` → expect <50MB), startup time (`time ./claude-proxy-rs --help` → <100ms)
- [ ] Task: Verify binary size after `cargo build --release`: strip with `strip target/release/claude-proxy-rs`; confirm < 30MB (use `ring` over `aws-lc-rs` and disable unused reqwest features as documented in pitfalls research if size exceeds target)

### Story 11.3: LaunchAgent migration and Makefile install

- [ ] Task: Implement `make install` target: `cargo build --release`, strip binary, copy to `/usr/local/bin/claude-proxy-rs`; update `com.claude-proxy.plist` `ProgramArguments` to point at new binary
- [ ] Task: Cutover procedure (encode in `Makefile cutover`):
  ```
  launchctl unload ~/Library/LaunchAgents/com.claude-proxy.plist
  cp /usr/local/bin/claude-proxy /usr/local/bin/claude-proxy.python.bak
  cp ./target/release/claude-proxy-rs /usr/local/bin/claude-proxy
  launchctl load ~/Library/LaunchAgents/com.claude-proxy.plist
  ```
- [ ] Task: Rollback target `make rollback`: swap `.python.bak` back, reload plist (< 10 second recovery per migration research)
- [ ] Task: Post-cutover monitoring: `launchctl list | grep claude-proxy` for non-zero exit codes; `tail -f /tmp/claude-proxy.app.log` for first 30 minutes

---

## ADRs Required

The following technology choices are novel enough to warrant Architecture Decision Records in `project_plans/claude-proxy-rs/decisions/`:

1. **ADR-001: TLS provider — ring over aws-lc-rs**
   Decision: Use `aws-smithy-http-client = { version = "0.62", features = ["rustls-ring"] }` to force the AWS SDK to use `ring` instead of `aws-lc-rs` (pin to a specific version — wildcard `"*"` trips cargo-deny). Rationale: prevents silent TLS conflict that causes "no process-level CryptoProvider" panic (GH #1264); reduces binary size by ~4MB; eliminates C/CMake build-time dependency.

2. **ADR-002: serde_json::Value for body manipulation (no typed structs)**
   Decision: All request/response bodies are handled as `serde_json::Value`, not typed Rust structs. Rationale: typed structs with `#[serde(deny_unknown_fields)]` would drop unknown fields silently; the proxy must be forward-compatible with new Claude Code fields; `#[serde(flatten)]` + untagged enums has a known serde bug (#1600) that would affect tool content arrays.

3. **ADR-003: Custom RwLock fallback state machine (no circuit-breaker crate)**
   Decision: Roll a custom ~40-line `FallbackState` with `tokio::sync::RwLock<ProviderState>` instead of using `failsafe` or `tokio-retry` for provider-level state. Rationale: all existing circuit-breaker crates model failure-rate thresholds, not a single-event 429 → fixed-wall-clock-cooldown pattern; `AtomicBool` is insufficient because the expiry check + state transition must be atomic.

4. **ADR-004: Separate streaming reqwest::Client with pool_max_idle_per_host(0)**
   Decision: Use two distinct `reqwest::Client` instances — pooled for short requests, non-pooled for streaming. Rationale: long-lived SSE connections hold pool slots permanently; under 50+ concurrent streams the default pool is exhausted, starving health checks and non-streaming requests.

5. **ADR-005: SimHash + MinHash two-tier dedup (no strsim) via lshdedup-core**
   Decision: Use `simhash` O(1) Hamming pre-filter + `lshdedup-core` MinHash for the ~5% of candidates that pass, wrapped in `spawn_blocking`. (`gaoya` rejected — not at 0.2 on crates.io, unstable API.) Rationale: `strsim::normalized_levenshtein` is O(n²) with no early exit — blocks the async runtime for ~10 seconds on 100KB entries; Jaccard on word 5-shingles is the semantically correct definition of "≥95% similar" for long documents.

6. **ADR-006: Single-pass system prompt pipeline (FR-7 + FR-9 coupled)**
   Decision: CacheAligner and verbosity steering share one pass over the `system` field, not independent passes. Rationale: if FR-7 adds `cache_control` to block 0 and FR-9 independently appends to that same block, the hash of block 0 changes → cache bust on every request; the only safe pattern is block 0 gets `cache_control`, block 1 gets the verbosity suffix with no `cache_control`.

7. **ADR-007: invoke_model_with_response_stream over converse_stream for Bedrock**
   Decision: Use `invoke_model_with_response_stream` with the raw Anthropic-format JSON body, matching the Python proxy. Rationale: `converse_stream` uses a different request format that does not accept `anthropic_version`, `thinking`, or `anthropic_beta` fields, and produces different event type names; switching would require a full Anthropic↔Converse translation spec; the existing Python proxy's Bedrock path emits Anthropic SSE format directly from `invoke_model_with_response_stream` chunks.

8. **ADR-008: Phase-scoped compression (Epic 6 deferred algorithmic stages)**
   Decision: Epic 6 Phase 1 implements only the compression pipeline framework (floor check, tool-pair guard, double-compression guard, Rewind store, native log-dedup text compressor). SmartCrusher and CodeCompressor are deferred to Epic 6b. Rationale: the Python proxy delegates all compression to `claw_compactor` (third-party Python library with no Rust equivalent); implementing the full 14-stage FusionEngine from scratch is original research requiring algorithmic specification work that exceeds the scope of this rewrite; the Phase 1 text compressor (ANSI strip + log dedup + blank normalization) handles the most common high-value case with a fully-specified algorithm.

---

## Summary

- **Epics**: 11 (plus deferred Epic 6b for algorithmic compression)
- **Stories**: 35
- **Tasks**: 131
- **ADRs flagged**: 8
- **Adversarial review blockers resolved**: 3 (compression scope, `gaoya` crate, `nix` feature flag)
- **Adversarial review concerns resolved**: 9 (converse_stream→invoke_model, tool-pair guard, rolling-file adapter, system prompt edge cases, tiktoken-rs version, SSO lock, `backoff` dep, dashboard lag chart, missing endpoints)
- **Validation plan concern resolved**: 1 (`error_tracker.rs` module added to Story 10.2)
