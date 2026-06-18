# Requirements: claude-proxy-rs

## Problem Statement

The existing `stapler-scripts/claude-proxy/` is a Python/FastAPI proxy (~460 lines + providers + compressor) running under uvicorn. It works correctly but carries all of Python's runtime overhead: GIL contention under load, multi-MB interpreter startup, memory pressure from async Python, and event loop lag under concurrent streaming requests. The goal is a full Rust rewrite that preserves every production feature while delivering Rust's performance characteristics: no GIL, zero-cost async, small single binary, fast startup.

## Existing System (source of truth)

**Location**: `stapler-scripts/claude-proxy/`
**Language**: Python 3.12+, FastAPI, uvicorn, httpx, boto3
**Deployment**: macOS LaunchAgent (`com.claude-proxy.plist`), port 47000

### Current architecture
```
Claude Code → FastAPI Proxy (port 47000) → Anthropic API (OAuth, primary)
                                         ↓ on 429 + 5-min cooldown
                                      AWS Bedrock (fallback, never rate-limited)
```

### Current endpoints
- `GET /` — proxy info
- `GET /health` — health check
- `GET /dashboard` — browser monitoring UI (requests/min, provider usage, lag chart)
- `GET /metrics` — JSON metrics
- `POST /v1/messages` — Anthropic Messages API (Claude Code)
- `POST /chat/completions` — OpenAI-compatible
- `POST /v1/chat/completions` — OpenAI-compatible (LiteLLM)

## Functional Requirements

### FR-1: Proxy Core
- FR-1.1: Listen on configurable port (default 47000)
- FR-1.2: Accept `POST /v1/messages` in Anthropic Messages API format
- FR-1.3: Accept `POST /chat/completions` and `POST /v1/chat/completions` in OpenAI format; translate to Anthropic format before forwarding
- FR-1.4: Forward `anthropic-version`, `anthropic-beta`, and `Authorization` headers
- FR-1.5: Assign a unique 8-char request ID to every request; return it in `X-Request-ID` response header
- FR-1.6: Request body cleaning — strip fields Claude Code sends that cause provider 400 errors:
  - Tool fields: `defer_loading`, `input_examples`, `custom`, `cache_control`
  - Message content: remove `tool_reference` type from tool results
  - Top-level Bedrock-only fields: `output_config`, `context_management`

### FR-2: Streaming
- FR-2.1: Support SSE streaming for all message endpoints (both providers)
- FR-2.2: Forward ALL SSE event types from both providers: `message_start`, `content_block_start`, `content_block_delta`, `content_block_stop`, `message_delta`, `message_stop`, `ping`
- FR-2.3: Graceful shutdown: in-flight streaming requests receive an SSE error event with retry instructions; new requests receive 503

### FR-3: Authentication
- FR-3.1: Accept `Authorization: Bearer sk-ant-oat-*` OAuth tokens
- FR-3.2: Forward OAuth token to Anthropic API as `x-api-key` header
- FR-3.3: Support configuring the OAuth token via `CLAUDE_CODE_OAUTH_TOKEN` environment variable

### FR-4: AWS Bedrock Fallback
- FR-4.1: On 429 from Anthropic, switch to Bedrock and enter a configurable cooldown period (default 300s) before retrying Anthropic
- FR-4.2: Bedrock is never placed in cooldown (always available as fallback)
- FR-4.3: Bedrock timeout retries: up to `BEDROCK_MAX_RETRIES` (default 3) on timeout errors
- FR-4.4: Model name normalization: translate Claude Code's Bedrock model format to Anthropic's format (e.g. `us.anthropic.claude-sonnet-4-20250514-v1:0` → `claude-sonnet-4-20250514`)
- FR-4.5: Beta feature forwarding to Bedrock: translate `anthropic-beta` header to `anthropic_beta` array in Bedrock request body; filter based on model compatibility (see current CLAUDE.md beta compatibility table)
- FR-4.6: Thinking budget validation for Bedrock: if `budget_tokens > max_tokens` and `max_tokens < 1024`, disable thinking; if `budget_tokens > max_tokens` and `max_tokens >= 1024`, cap to `max_tokens`; if `budget_tokens < 1024`, raise to 1024
- FR-4.7: Proactive AWS credential refresh: check credential expiry before each Bedrock request; refresh via `aws-sso-lib` equivalent (or shell out to `aws sso login`) when expiring within 5 minutes; cache credential validity for 30s
- FR-4.8: All boto3/AWS calls must be non-blocking (run in dedicated thread pool, min 20 threads)

### FR-5: Compression (Rust-native rewrite)
- FR-5.1: Every `/v1/messages` request is compressed before forwarding (unless `STAPLER_COMPRESS=0`)
- FR-5.2: Skip compression for requests smaller than `COMPRESS_FLOOR_BYTES` (default 4096 bytes)
- FR-5.3: Content-type-aware routing: JSON arrays/objects → SmartCrusher; code blocks → CodeCompressor; natural language / logs → text compressor
- FR-5.4: `tool_use` and `tool_result` blocks pass through untouched — only natural-language and log content is compressed
- FR-5.5: Reversible compression (CCR/Rewind): when lossy compression occurs, store original in in-memory LRU (500 entries, 10-min TTL); embed marker in compressed text: `[N items compressed to M. Retrieve: hash=XXXX]`; inject `rewind_retrieve` tool into `tools[]` array
- FR-5.6: Double-compression guard: never compress an already-compressed turn (detect existing Rewind markers)
- FR-5.7: Track compression metrics: `total_tokens_before`, `total_tokens_after`, `total_tokens_saved`, `total_requests_compressed`, `avg_compression_ratio`

### FR-6: Metrics & Monitoring
- FR-6.1: `GET /health` returns `{"status": "ok"}` with 200
- FR-6.2: `GET /metrics` returns JSON with: request counts by provider, error counts, compression stats, current event loop lag (if measurable), recent errors
- FR-6.3: `GET /dashboard` serves an HTML page with live charts (15-min history) for: requests/min, provider distribution, duration histogram, compression savings
- FR-6.4: Log slow requests (>30s) and blocking requests (>60s) with distinct markers
- FR-6.5: Rotating log files:
  - Application log (`/tmp/claude-proxy.app.log`): fallback logic, provider switches, lag warnings — 10MB × 10 files
  - HTTP log (`/tmp/claude-proxy.http.log`): raw HTTP — 10MB × 5 files
  - Access log (`/tmp/claude-proxy.log`): per-request access — managed by server

## Non-Functional Requirements

### NFR-1: Performance
- NFR-1.1: Binary startup time < 100ms
- NFR-1.2: Binary size < 30MB (stripped release build)
- NFR-1.3: Memory usage < 50MB idle (vs Python's ~150MB+)
- NFR-1.4: Handle 50+ concurrent streaming requests without event loop degradation
- NFR-1.5: No GIL — Rust's async runtime (tokio) with true parallelism

### NFR-2: Deployment
- NFR-2.1: Single self-contained binary (no Python runtime, no uv, no virtualenv)
- NFR-2.2: Same macOS LaunchAgent deployment (`com.claude-proxy.plist`) — drop-in replacement
- NFR-2.3: Same environment variables as current proxy (`CLAUDE_CODE_OAUTH_TOKEN`, `AWS_PROFILE`, `AWS_REGION`, `PROXY_PORT`, `COOLDOWN_SECONDS`, `REQUEST_TIMEOUT`, `BEDROCK_MAX_RETRIES`, `STAPLER_COMPRESS`, `COMPRESS_FLOOR_BYTES`)
- NFR-2.4: Makefile targets: `make build`, `make install`, `make dev`, `make start`, `make stop`, `make restart`, `make status`, `make logs`, `make test`

### NFR-3: Correctness
- NFR-3.1: All existing tests in `tests/` must pass (translated to Rust integration tests)
- NFR-3.2: Proxy must be wire-compatible with Claude Code (no client-side changes needed)
- NFR-3.3: Proxy must be wire-compatible with LiteLLM on the `/v1/chat/completions` path

### NFR-4: Maintainability
- NFR-4.1: Rust edition 2021, `cargo clippy` clean at `--deny warnings`
- NFR-4.2: Module structure mirrors current Python layout: `src/providers/`, `src/compression/`, `src/metrics/`, `src/auth.rs`, `src/fallback.rs`
- NFR-4.3: All structs and key functions documented

### FR-7: CacheAligner (Anthropic KV Cache Optimization)
- FR-7.1: Before forwarding each request, stabilize the message prefix so Anthropic's prompt cache boundaries are hit consistently across turns
- FR-7.2: Track estimated cache hit/miss rate in metrics (`cache_hits_estimated`, `cache_misses_estimated`)
- FR-7.3: CacheAligner must not change message semantics — it only reorders/normalizes prefix content that is stable across turns (e.g., system prompt, tool definitions)
- FR-7.4: Configurable via `CACHE_ALIGNER=1` (default on); killswitch `CACHE_ALIGNER=0`

### FR-8: headroom learn → MEMORY.md Automation
- FR-8.1: After each session (or on-demand via `POST /admin/learn`), mine the Claude Code conversation history for failure patterns
- FR-8.2: Detect failure patterns: repeated corrections, error recovery loops, explicit user corrections ("no, don't", "stop doing", "always use X instead")
- FR-8.3: Write discovered patterns to a staging file (`/tmp/headroom-learn-staging.md`) — never auto-write to `~/.claude/projects/*/memory/` or `CLAUDE.md` without explicit confirmation
- FR-8.4: Expose `GET /admin/learn-preview` to show what would be written; require `POST /admin/learn-apply` to actually persist
- FR-8.5: Source conversation history from Claude Code's JSONL transcripts at `~/.claude/projects/`

### FR-9: Output Token Reduction (Verbosity Steering)
- FR-9.1: Append a short verbosity-steering instruction to the END of the system prompt before forwarding (so existing system prompt prefix is cache-stable): e.g., `"Be terse. Don't restate context. Answer directly."`
- FR-9.2: Only activate for "continuation" turns (model resuming after tool results) — not for new questions or turns with errors; detect via heuristics on the last human message
- FR-9.3: Configurable verbosity level: `VERBOSITY_LEVEL=0` (off), `1` (light), `2` (moderate, default), `3` (aggressive)
- FR-9.4: Track output token savings estimate in metrics (with confidence band note — counterfactual)
- FR-9.5: `POST /admin/learn-verbosity` — analyze past sessions to auto-select the verbosity level that matches the user's implicit preferences

### FR-10: Cross-Agent SharedContext Memory
- FR-10.1: In-memory key-value store for compressed context passing between agents (Claude Code, any OpenAI-compatible client)
- FR-10.2: `PUT /memory/{key}` stores a value (compressed via FR-5 pipeline)
- FR-10.3: `GET /memory/{key}` retrieves compressed summary; `GET /memory/{key}?full=true` retrieves original
- FR-10.4: Auto-dedup: if a value is ≥95% similar to an existing entry, update rather than create a new one
- FR-10.5: Agent provenance tracking: each entry records which `User-Agent` or `X-Agent-ID` stored it
- FR-10.6: TTL configurable per entry (default 24h); LRU eviction when store exceeds `MEMORY_MAX_ENTRIES` (default 1000)
- FR-10.7: `GET /memory` — list all keys with metadata (agent, size_before, size_after, created_at, ttl_remaining)

## Out of Scope

- Parallel/multi-worker mode (tokio's async handles concurrency natively; no need for multiple OS processes)
- Windows support (macOS LaunchAgent deployment only, Linux nice-to-have)
- GUI configuration (environment variables are sufficient)
- py-spy / Python profiling tooling (replaced by Rust-native profiling)

## Success Criteria

1. All FR-1 through FR-6 requirements implemented and passing tests
2. `make install` produces a working LaunchAgent replacement with zero Claude Code client changes
3. Memory usage < 50MB idle measured via `ps aux`
4. Startup time < 100ms measured via `time ./claude-proxy-rs --help`
5. Compression ratios equal or better than Python FusionEngine measured on same request corpus
6. CacheAligner increases estimated Anthropic cache hit rate (measured via `X-Cache` response headers or token billing)
7. `headroom learn` staging output correctly identifies at least 3 real correction patterns from existing session history
8. Verbosity steering measurably reduces output length on continuation turns (manual spot-check)
9. Zero regressions in Claude Code daily usage over a 1-week soak period
