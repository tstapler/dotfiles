# Feature Research: claude-proxy-rs

## 1. Open-Source Rust LLM Proxy Implementations

### Production-Quality Projects

**[LeenHawk/gproxy](https://github.com/LeenHawk/gproxy)** — 154 stars, v1.0.22 (May 2026)
The most complete Rust LLM proxy. Built on Axum + SeaORM, ships as a single static binary. Supports OpenAI, Anthropic, Gemini, DeepSeek, Groq, OpenRouter, NVIDIA, plus any OpenAI-compatible endpoint.

Relevant features:
- Full SSE streaming passthrough
- Cross-protocol translation (OpenAI client → Claude upstream and vice versa)
- Two routing modes: model-name-encoded (`/v1/`) and URL-scoped (`/{provider}/v1/`)
- Claude prompt cache breakpoints and request rewrite rules
- Published crates: `gproxy-protocol`, `gproxy-channel`, `gproxy-engine` (clean layered separation)

**License: AGPL-3.0** — embedding requires open-sourcing your project. Usable for pattern study only; cannot be linked.

**[AprilNEA/BYOKEY](https://github.com/AprilNEA/BYOKEY)** — 125 stars, v1.2.0 (April 2026)
OAuth-first proxy converting Claude Pro/Copilot subscriptions to API endpoints. MIT/Apache-2.0. Active (265 commits, 32 releases). No retry/fallback routing; niche use case but useful for OAuth forwarding patterns.

**[api7/aisix-archived](https://github.com/api7/aisix-archived)** — 57 stars (archived March 2026)
From the Apache APISIX team. etcd-backed config, OpenTelemetry tracing, Prometheus metrics, streaming for OpenAI/Anthropic/Gemini/DeepSeek. Archived before fallback routing was implemented — useful for observability/tracing patterns.

### No Reusable Library on crates.io
No Rust crate provides routing/proxy logic as a standalone library. All production work ships as binaries.

### Patterns Worth Borrowing
- **Three-crate separation** (gproxy): protocol types / per-provider channel logic / routing engine — maps directly to the planned `src/providers/`, `src/compression/`, `src/metrics/` module structure
- **Credential affinity**: sticky-route retries to last-successful credential before falling back
- **Two-tier routing**: model-name-encoded vs URL-path provider selection handles both OpenAI SDK clients and explicit routing cleanly

---

## 2. SSE Streaming in Rust (axum)

**Crate versions**: axum `0.8.9`, eventsource-stream `0.2.3`, reqwest `0.12`

### Handler Return Type
```rust
async fn sse_handler() -> Sse<impl Stream<Item = Result<Event, Infallible>>>
```

`Sse<S>` wraps any `Stream<Item = Result<Event, E>>`. The error type must implement `Into<Box<dyn std::error::Error + Send + Sync>>`.

### reqwest → axum SSE Proxy (canonical pattern)

```toml
# Cargo.toml
axum = "0.8"
reqwest = { version = "0.12", features = ["stream"] }
eventsource-stream = "0.2"
futures-util = "0.3"
```

```rust
use axum::response::sse::{Event, Sse};
use eventsource_stream::Eventsource;
use futures_util::StreamExt;
use std::convert::Infallible;

async fn proxy_sse() -> Sse<impl futures_util::Stream<Item = Result<Event, Infallible>>> {
    let upstream = reqwest::Client::new()
        .post("https://api.anthropic.com/v1/messages")
        .send()
        .await
        .expect("upstream request failed");

    let stream = upstream
        .bytes_stream()          // Stream<Item = Result<Bytes, reqwest::Error>>
        .eventsource()           // Stream<Item = Result<eventsource_stream::Event, _>>
        .map(|result| {
            let ev = result.expect("SSE parse error");
            // ev: eventsource_stream::Event { event, data, id, retry }
            let mut axum_ev = Event::default().data(ev.data);
            if !ev.event.is_empty() { axum_ev = axum_ev.event(ev.event); }
            if !ev.id.is_empty()    { axum_ev = axum_ev.id(ev.id); }
            Ok::<Event, Infallible>(axum_ev)
        });

    Sse::new(stream).keep_alive(axum::response::sse::KeepAlive::default())
}
```

**`eventsource-stream`** provides the `.eventsource()` extension (via `Eventsource` trait) on any `Stream<Item = Result<Bytes, E>>`. It handles SSE line parsing with nom, correctly accumulating partial chunks across byte boundaries.

### Key Gotchas
- **Error mid-stream**: Use `filter_map` to log and skip parse errors, or emit a terminal error event and end the stream — axum closes SSE when the stream returns `None`
- **`[DONE]` termination**: Check `ev.data == "[DONE]"` and stop before forwarding that item
- **Backpressure**: No explicit buffering needed — Tokio's async back-pressure flows through the chain
- **Connection drops**: When downstream client disconnects, axum drops the response future → drops the stream → drops `reqwest::Response` → upstream TCP connection closes. No explicit cleanup required.
- **Keep-alive**: `KeepAlive::default()` sends `: keep-alive` comments every 15s — important for load balancers

---

## 3. AWS Bedrock Rust SDK

**Current version**: `aws-sdk-bedrockruntime = "1.135.0"` (June 2026)

### Cargo.toml
```toml
[dependencies]
aws-config = { version = "1.1.7", features = ["behavior-version-latest"] }
aws-sdk-bedrockruntime = "1.135.0"
tokio = { version = "1", features = ["full"] }
```

No need to add `aws-smithy-eventstream` directly — it's a transitive dep. The SDK exposes `EventReceiver` via `aws_sdk_bedrockruntime::primitives::event_stream`.

### `converse_stream` Return Types
```rust
pub struct ConverseStreamOutput {
    pub stream: EventReceiver<
        types::ConverseStreamOutput,       // event enum (#[non_exhaustive])
        types::error::ConverseStreamOutputError,
    >,
}

// Event enum — always add `_ => {}` arm
pub enum ConverseStreamOutput {
    ContentBlockDelta(ContentBlockDeltaEvent),
    ContentBlockStart(ContentBlockStartEvent),
    ContentBlockStop(ContentBlockStopEvent),
    MessageStart(MessageStartEvent),
    MessageStop(MessageStopEvent),
    // non_exhaustive
}
```

### Canonical Streaming Loop
```rust
let config = aws_config::load_from_env().await;
let client = aws_sdk_bedrockruntime::Client::new(&config);

let mut response = client
    .converse_stream()
    .model_id("anthropic.claude-3-5-sonnet-20241022-v2:0")
    .messages(
        types::Message::builder()
            .role(types::ConversationRole::User)
            .content(types::ContentBlock::Text("Hello".into()))
            .build()
            .unwrap(),
    )
    .send()
    .await?;

let mut stream = response.stream;
loop {
    match stream.recv().await? {
        Some(event) => match event {
            types::ConverseStreamOutput::ContentBlockDelta(e) => {
                if let Some(types::ContentBlockDelta::Text(text)) = e.delta {
                    print!("{}", text);
                }
            }
            types::ConverseStreamOutput::MessageStop(_) => break,
            _ => {}
        },
        None => break,
    }
}
```

### Critical Gotchas
- **No `Stream` trait impl** — `EventReceiver` does NOT implement `futures::Stream`. Only `recv()` works; cannot use `.next()` or `StreamExt`.
- **`#[non_exhaustive]` enum** — always include `_ => {}` arm; the enum grows with SDK updates
- **`recv()` requires `&mut self`** — single-consumer only; cannot share across tasks
- **`invoke_model_with_response_stream`** body is a public field (`response.body`), not a method call; contains raw bytes requiring model-specific JSON parsing
- **`!Freeze` on EventReceiver** — keep in a `let mut` local; holding across awaits may require boxing

### Impact on FR-4.8 (Non-blocking AWS calls)
`EventReceiver::recv()` is already async and runs on Tokio — no thread pool needed for the stream iteration itself. AWS credential loading via `aws_config::load_from_env()` is also async. The requirement to run in a "dedicated thread pool" is likely a Python-era concern (boto3 is sync); in Rust, the existing Tokio runtime handles this natively.

---

## 4. Rust Text/Semantic Compression Crates

### Token Counting
- **`tiktoken-rs`** v0.12.0 (Apr 2026, Rust 1.85+) — OpenAI BPE tokenizer, token counting/encoding for compression ratio tracking (FR-5.7)
- **`tiktoken`** — alternative claiming 15-40× faster on ASCII text

### Compression Pipeline Crates (directly relevant to FR-5)
- **`trimcp`** v0.1.3 (Mar 2026) — Rust MCP proxy with compression pipeline: consecutive line dedup → `line (xN)`, JSON minification, ANSI stripping. Reports 84k→31k tokens (62%) on real sessions. Has optional BM25-based semantic code indexing. Closest existing Rust implementation to the planned LogCrunch/SemanticDedup stages.
- **`sqz`** (sqz-engine, sqz-mcp, sqz-wasm) — Content-aware dedup: identical file reads across a session sent once + 13-token reference. Reports 24.7% average, up to 92% on read-heavy workloads.
- **`compression-prompt`** v0.1.x — Statistical filtering, no ML/neural component. Claims 50% token reduction at 91% quality retention, <1ms latency. Identifies low-information sentences statistically.

### Retrieval/Selection (useful for compression scoring)
- **`bm25`** v2.3.2 (1.2M downloads) — For selecting which chunks to include; also used in trimcp for semantic indexing
- **`bm25_turbo`** — Precomputed sparse matrices variant

### What Doesn't Exist in Rust
- Neural summarization / extractive compression
- Embedding-based semantic deduplication (needs candle/ort or an external API call)

### Recommendation for FR-5
`trimcp`'s pipeline covers LogCrunch (line dedup) and JSON minification stages. `compression-prompt` is worth evaluating for the Abbrev/NL stages. The SemanticDedup (SimHash) stage will need custom implementation — `simhash` crate exists but has no LLM-specific tuning. The tree-sitter-based Neurosyntax stage can use the `tree-sitter` crate directly.

---

## 5. claw-compactor

**Source**: https://github.com/open-compress/claw-compactor — MIT license, 2.2k stars, v7.1.0

### What It Does
LLM token compression engine using a 14-stage "Fusion Pipeline." Stages run sequentially on LLM context (chat messages, code, JSON, logs, diffs). Claims 15–82% token reduction with zero LLM inference cost and full reversibility.

### The 14 Stages
1. **QuantumLock** — KV-cache alignment for system prompts
2. **Cortex** — content-type + language auto-detection (16 languages)
3. **Photon** — base64 image compression
4. **RLE** — path shorthands, IP prefix compression, enum compaction
5. **SemanticDedup** — SimHash fingerprint deduplication
6. **Ionizer** — JSON array statistical sampling + schema discovery
7. **LogCrunch** — folds repeated log lines with counts
8. **SearchCrunch** — deduplicates grep/search results
9. **DiffCrunch** — folds unchanged diff context lines
10. **StructuralCollapse** — merges import blocks, collapses repeated patterns
11. **Neurosyntax** — AST-aware code compression via tree-sitter (regex fallback)
12. **Nexus** — token-level stopword removal (no model required)
13. **TokenOpt** — format optimization, whitespace normalization
14. **Abbrev** — NL abbreviation (never touches code/JSON)

### Rust Reimplementability: High Confidence
All 14 stages are algorithmic, not ML-based:
- SimHash, RLE, regex transforms, JSON sampling — all straightforward in Rust
- tree-sitter for Neurosyntax: the `tree-sitter` crate is a direct Rust binding to the same C library — maps cleanly
- The immutable pipeline architecture (`FusionContext` frozen dataclass) translates naturally to Rust's ownership model
- No Python-specific magic; it's a typed pipeline of pure functions
- ~12,000 lines of pure Python, 1,600+ tests — substantial but tractable port

### Comparison with Existing Proxy (FR-5 gap analysis)
The current Python proxy's `SmartCrusher`/`CodeCompressor` appears to be a partial implementation of the claw-compactor pipeline. The Rust rewrite should implement the full pipeline natively rather than shelling out to Python.

### Similar Packages Considered
- **LLMLingua-2** (Microsoft) — perplexity-based token dropping; requires `torch`/`transformers`; lossy; ~300ms/call — not suitable
- **SelectiveContext** — self-information scoring; also requires `torch`; lossy — not suitable

---

## Decision Summary

| Area | Recommendation |
|------|---------------|
| Proxy framework | axum `0.8` — no existing Rust proxy worth forking (AGPL or incomplete) |
| SSE streaming | `eventsource-stream` `0.2` + axum `Sse<>` — well-established pattern |
| Bedrock SDK | `aws-sdk-bedrockruntime` `1.135.0` — no thread pool needed, async-native |
| Compression pipeline | Implement claw-compactor stages natively in Rust (MIT license, algorithmic) |
| Token counting | `tiktoken-rs` `0.12` for FR-5.7 metrics |
| Log/line dedup | Study `trimcp` patterns (MIT); implement LogCrunch stage similarly |
