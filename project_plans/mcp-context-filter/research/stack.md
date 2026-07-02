# Stack Research: mcp-context-filter

**Date**: 2026-07-02
**Author**: research agent
**Status**: draft

---

## Executive Summary

The right stack is `rmcp` v0.16 as the MCP protocol layer (official Anthropic/modelcontextprotocol Rust SDK), plugged into the existing `axum`/`tokio`/`reqwest` stack in `claude-proxy-rs`. Phase 3 tool search uses `bm25` (lightweight, in-memory, zero deps) for lexical search, upgrading to `fastembed-rs` (ONNX, BGE-small-en) for semantic search. The proxy architecture is **stdio-in / HTTP-SSE-out**: Claude Code spawns the proxy as a stdio MCP subprocess; the proxy connects upstream to cloud connectors via Streamable HTTP or legacy SSE.

---

## Problem Context

The MCP proxy needs to:

1. Present as an MCP server to Claude Code (consumer-side)
2. Act as an MCP client to upstream cloud connectors (Slack, Atlassian, etc.)
3. Intercept `tools/list`, filter/compress it, and forward `tools/call` transparently
4. Phase 3: expose a `search_tools` meta-tool backed by BM25 or embeddings

All of this must integrate into the existing `claude-proxy-rs` Rust/Axum codebase without external SaaS dependencies.

---

## Question 1: MCP Protocol SDK — Which Rust Crate?

### Options

| Crate | Maintainer | crates.io version | MCP spec | Maturity | Notes |
|---|---|---|---|---|---|
| `rmcp` | modelcontextprotocol (Anthropic) | 0.16.0 | 2025-06-18 | Production | Official SDK |
| `rust-mcp-sdk` | community | 0.x | 2025-03-26 | Beta | Not official |
| `mcpserver` | community | 0.3 | partial | Alpha | JSON-RPC only, no transport |
| Roll own | — | — | any | — | High maintenance |

### Verdict: **`rmcp` v0.16** is the clear choice

`rmcp` is the official Rust SDK from the `modelcontextprotocol` GitHub org (same org as the spec, same Anthropic project). As of v0.16.0:

- Implements MCP spec 2025-06-18 (latest)
- Declares `tools.listChanged: true` capability with built-in `notifications/tools/list_changed` support
- Ships both **server** and **client** roles — exactly what a proxy needs
- **Transport feature flags**:
  - `transport-io` — stdio (for the server-side that Claude Code spawns)
  - `transport-sse` — SSE client (for connecting to upstream cloud connectors)
  - `transport-streamable-http-client` / `transport-streamable-http-server` — Streamable HTTP (2025-03-26 spec, successor to SSE)
  - `transport-child-process` — spawn local MCP subprocesses as a client
- Axum-compatible via `StreamableHttpService` that can be nested into an Axum router
- Macros: `#[tool]`, `#[tool_box]` for ergonomic tool definition (useful for the `search_tools` meta-tool in Phase 3)
- OAuth 2.0 support built-in (`auth` feature)
- Tokio 1.x runtime (already in claude-proxy-rs)

**Cargo.toml addition**:
```toml
rmcp = { version = "0.16", features = [
    "server",
    "client",
    "transport-io",           # stdio server for Claude Code
    "transport-sse",          # SSE client to upstream cloud connectors
    "transport-streamable-http-client",  # Streamable HTTP upstream
] }
```

**Compatibility risk**: `rmcp` pulls in its own `axum` dependency. The existing codebase uses `axum = "0.8"`. Check that rmcp 0.16's axum dependency resolves to 0.8 (not 0.7) before finalizing. Run `cargo tree -p rmcp | grep axum` after adding.

---

## Question 2: JSON-RPC 2.0 — Separate Crate?

**No separate JSON-RPC crate needed.** `rmcp` handles all JSON-RPC 2.0 framing internally. It exposes typed Rust structs for all MCP messages (e.g., `ListToolsResult`, `CallToolRequest`). The proxy code works with these types; `serde_json` (already in Cargo.toml) is sufficient for any custom serialization.

If a thin JSON-RPC helper is ever needed outside `rmcp` context, `jsonrpc-core ^18` is the established choice and is already proven with `axum` + `tokio` stacks.

---

## Question 3: SSE/HTTP Transport — What's Already There vs. What's New

### Existing in claude-proxy-rs

```toml
reqwest = { version = "0.13", features = ["json", "stream", "rustls"] }
eventsource-stream = "0.2"
axum = { version = "0.8", features = ["macros"] }   # already has SSE via axum::response::sse
```

The existing `main.rs` already:
- Proxies SSE streams from Anthropic/Bedrock upstream using `reqwest` stream + `eventsource-stream`
- Emits SSE to downstream clients via `axum::response::sse::Sse`

### What `rmcp` adds for the MCP proxy

`rmcp`'s `transport-sse` feature wraps exactly `reqwest` + SSE into a typed MCP transport. Rather than rolling a custom SSE-to-MCP framing layer, `rmcp`'s `SseTransport` handles:
- Connection lifecycle and reconnection
- SSE frame parsing into JSON-RPC messages
- Auth header passthrough

For the **upstream cloud connector client** (HTTP/SSE or Streamable HTTP), `rmcp` client with `transport-sse` or `transport-streamable-http-client-reqwest` is the right abstraction.

For the **stdio server** (what Claude Code spawns), `rmcp`'s `transport-io` wraps `tokio::io::stdin()` / `tokio::io::stdout()`.

**Auth token forwarding**: When Claude Code talks to an admin-provisioned cloud connector, it injects `Authorization: Bearer <token>` into the outbound HTTP request. The proxy must capture this from the incoming MCP session context and forward it. `rmcp`'s `SseTransport` accepts a `reqwest::Client` with custom headers configured — this is the hook point.

### Existing `compression/` module compatibility

The compression module operates on `serde_json::Value` (message bodies). MCP tool schema filtering (Phase 1) and compression (Phase 2) work at the same JSON level — the proxy intercepts `tools/list` response JSON, manipulates it, and returns it. No changes to the compression module are required; Phase 2 can reuse `TextCompressor` for description stripping if desired, or write a purpose-built `ToolSchemaCompressor`.

---

## Question 4: Embedding / BM25 for Phase 3 Tool Search

Phase 3 requires a `search_tools(query)` meta-tool that searches a catalog of up to 200 tools by semantic or lexical similarity. SLO: ≤500ms overhead.

### Option A: BM25 — `bm25` crate (Michael-JB)

**Recommended for Phase 3 initial implementation.**

- Crate: [`bm25`](https://crates.io/crates/bm25)
- Pure Rust, no native dependencies, no file I/O, no model downloads
- In-memory index; for 200 tools: index build ~1ms, query ~sub-millisecond
- Features: multilingual tokenizer with stemming, stop word removal, Unicode normalization
- BM25Scorer + BM25SearchEngine API — no external DBs needed
- WebAssembly-compatible (index can be rebuilt from TOML config on each proxy start)

**Usage pattern**:
```rust
let index = bm25::SearchEngine::new();
for tool in tools {
    index.add_document(tool.name.clone(), &format!("{} {}", tool.name, tool.description));
}
let results = index.search("list slack messages", 5);
```

Index rebuild on config change is fast enough to do in the startup path.

### Option B: `fastembed-rs` — Dense Embeddings (Phase 3 stretch / upgrade)

For semantic similarity (handles paraphrases that BM25 misses):

- Crate: [`fastembed`](https://crates.io/crates/fastembed)
- Uses `ort` (ONNX Runtime) for inference — no Python, no network calls after first download
- Default model: `BGE-small-en-v1.5` (~65MB ONNX file, cached at `~/.cache/fastembed`)
- Inference on macOS M-series: ~10–30ms per query (well within 500ms SLO)
- Synchronous API (no extra tokio overhead)
- Quantized variants available (`BGESmallENV15Q`) for ~50% size reduction

**Trade-offs vs BM25**:
- First run: downloads ~65MB model (once, then cached)
- Adds compile-time dependency on ONNX Runtime shared library (distributed via the `ort` crate, auto-downloaded by build script)
- 3–5x richer semantic matching for tool name/description search

**Recommendation**: Ship Phase 3 with `bm25`. Add `fastembed` as an opt-in feature flag (`mcp-proxy-embedding`) for users who want semantic search. BM25 covers the primary use case (users know the tool name or domain keyword); embeddings are a secondary enhancement.

### Option C: `tantivy`

Not recommended. Tantivy is a full Lucene-equivalent search engine with an on-disk index, complex schema definition, and significant binary size overhead. Overkill for an in-memory catalog of 200 tools. Use `bm25` instead.

---

## Question 5: Dynamic Tool Re-registration (Phase 3)

**The MCP spec fully supports dynamic tool updates** via `notifications/tools/list_changed`.

From the spec (2025-06-18):
- Server declares `"tools": { "listChanged": true }` in `initialize` response capabilities
- Server sends `{"jsonrpc":"2.0","method":"notifications/tools/list_changed"}` (no params, no response expected) when the active tool list changes
- Client must call `tools/list` again to fetch the updated list

**`rmcp` supports this natively**: the server handler can call `peer.notify_tools_list_changed()` (or equivalent API per rmcp 0.16 docs) from any async context.

**Claude Code support status**: Unknown. Community reports show Gemini CLI and LibreChat don't yet respond to this notification (they keep the stale list). Claude Code's behavior is unconfirmed. **Treat dynamic re-registration as a rabbit hole** (flagged in requirements):

- Phase 3 fallback strategy: always include `search_tools` in the static tool list plus a fixed K "active slot" tools (e.g., 10). Search populates slots; slots don't disappear. This is safe even if Claude Code ignores `tools/list_changed`.
- If Claude Code does honor `notifications/tools/list_changed`, the session-TTL expiration feature can use it to shrink the active set after N turns.

---

## Question 6: Proxy Communication Architecture — How Does Claude Code Talk to the Proxy?

### The Two Transport Models

Claude Code supports two MCP transport types:
1. **stdio** — spawns a local process, communicates via stdin/stdout
2. **HTTP/SSE or Streamable HTTP** — connects to a running HTTP server (local or remote)

### Recommended Architecture: stdio MCP server (local subprocess)

**Claude Code config** (in `.claude/settings.json` `mcpServers`):
```json
{
  "mcp-proxy-slack": {
    "command": "claude-proxy-rs",
    "args": ["mcp-proxy", "--server", "slack-connector"],
    "type": "stdio"
  }
}
```

**Data flow**:
```
Claude Code
  │ (stdio JSON-RPC)
  ▼
claude-proxy-rs --mcp-proxy (new binary mode or subcommand)
  │ intercepts tools/list, filters, forwards tools/call
  │ (HTTP/SSE or Streamable HTTP with auth headers)
  ▼
Upstream cloud connector (Atlassian Rovo, Slack, etc.)
```

**Why stdio over HTTP local server**:
- Claude Code already manages the stdio subprocess lifecycle (starts on session start, kills on exit)
- No port management, no localhost binding conflicts
- Zero latency for connection setup (no TCP handshake overhead)
- Simpler auth token passthrough: Claude Code injects the connector's Bearer token into the stdio session context; the proxy receives it in the MCP `initialize` request or via environment variables
- This is exactly the pattern used by `stephenlacy/mcp-proxy` and `tidewave-ai/mcp_proxy_rust`

**Implementation**: The proxy binary gets a new subcommand `mcp-proxy`:
```
claude-proxy-rs mcp-proxy --config ~/.config/mcp-proxy.toml --server <server-name>
```

This keeps it as a single binary with multiple modes, consistent with the existing `claude-proxy-rs` structure. The new `mcp/` module in `src/` follows the same pattern as `providers/` and `compression/`.

### Auth Token Forwarding

The critical open question: how does Claude Code pass OAuth tokens for admin-provisioned connectors?

**Hypothesis (to verify in Phase 1 prototype)**:
- For HTTP/SSE connectors configured in Claude Code, the tokens are stored encrypted in Claude Code's local keychain/state
- When the proxy pretends to be the stdio shim for a connector, it does NOT automatically receive those tokens
- Two fallback approaches:
  1. User configures API keys in `mcp-proxy.toml` (explicit, always works)
  2. The proxy reads Claude Code's MCP connector config and reuses the same auth headers Claude Code would send (requires reverse-engineering Claude Code's config storage — rabbit hole)
- **Phase 1 decision**: implement explicit API key config in `mcp-proxy.toml`; investigate token forwarding in a spike before Phase 2

---

## Question 7: TOML Config — Library Choice

The existing codebase uses env vars (`Config::from_env()`). The new `mcp-proxy.toml` file requires a TOML parser.

**Recommendation**: `toml` crate v0.8 (already an indirect dependency via Cargo's own machinery, safe to add directly):
```toml
toml = "0.8"
```

Alternatively, `config` crate (supports TOML + env var layering) but adds complexity. Keep it simple: `toml::from_str` + serde.

---

## Recommended Stack Summary

| Concern | Crate(s) | Version | Notes |
|---|---|---|---|
| MCP protocol (server + client) | `rmcp` | 0.16 | Official SDK, all transports |
| HTTP/SSE transport | existing `reqwest` + `eventsource-stream` | 0.13 / 0.2 | Already in Cargo.toml |
| Axum SSE server | existing `axum` | 0.8 | Already in Cargo.toml |
| JSON-RPC 2.0 | via `rmcp` | — | No separate crate needed |
| Phase 3 lexical search | `bm25` | latest (0.1.x) | Pure Rust, in-memory, zero deps |
| Phase 3 semantic search | `fastembed` | latest | ONNX, BGE-small-en, optional feature flag |
| TOML config | `toml` | 0.8 | Simple serde-based parsing |
| Async runtime | existing `tokio` | 1.52 | Already in Cargo.toml |
| Token counting | existing `tiktoken-rs` | 0.5 | Already in Cargo.toml, use for Phase 2 metrics |

---

## Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| `rmcp` axum version conflict (0.7 vs 0.8) | High | Verify `cargo tree` before merging; file issue with rmcp upstream if needed |
| Claude Code does not honor `tools/list_changed` | Medium | Use fixed-K slot approach in Phase 3 as fallback |
| Auth token access for admin connectors | High | Phase 1: explicit TOML config. Prototype token forwarding as a spike |
| SSE backpressure with long-lived connectors | Medium | `rmcp` handles reconnection; add circuit breaker at proxy layer |
| `fastembed` model download at first startup | Low | Gate behind opt-in feature flag; pre-seed model in dotfiles bootstrap script |

---

## References

- [rmcp on crates.io](https://crates.io/crates/rmcp)
- [modelcontextprotocol/rust-sdk on GitHub](https://github.com/modelcontextprotocol/rust-sdk)
- [rmcp docs.rs](https://docs.rs/rmcp)
- [MCP spec: tools/list_changed](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
- [MCP transport spec (2025-11-25)](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [stephenlacy/mcp-proxy (prior art)](https://github.com/stephenlacy/mcp-proxy)
- [tidewave-ai/mcp_proxy_rust (prior art)](https://github.com/tidewave-ai/mcp_proxy_rust)
- [bm25 crate (Michael-JB)](https://github.com/Michael-JB/bm25)
- [fastembed-rs on crates.io](https://crates.io/crates/fastembed)
- [Claude Code MCP docs](https://code.claude.com/docs/en/mcp)
- [Shuttle: Build a stdio MCP Server in Rust](https://www.shuttle.dev/blog/2025/07/18/how-to-build-a-stdio-mcp-server-in-rust)
- [Shuttle: Build SSE MCP Server with OAuth in Rust](https://www.shuttle.dev/blog/2025/08/13/sse-mcp-server-with-oauth-in-rust)
