# Build vs. Buy: MCP Proxy Implementation Options

**Date**: 2026-07-02
**Author**: Research agent
**Scope**: mcp-context-filter Phase 1–3

---

## Context

claude-proxy-rs is a Rust/Axum HTTP proxy for Claude API requests with Bedrock fallback. It has zero MCP awareness — it operates entirely at the HTTP message layer, never touching MCP server lifecycles or tool schemas. Any MCP proxy capability must be added as a new binary or crate within the workspace.

The requirement is a config-driven, per-server tool allowlist that intercepts `tools/list`, filters to a named set, and forwards `tools/call` transparently — for both stdio and HTTP/SSE MCP upstream transports.

---

## Option 1: atlassian-labs/mcp-compressor

**Verdict: Viable — for Phase 2 only. Wrong paradigm for Phase 1.**

| Attribute | Value |
|-----------|-------|
| Language | Rust (66%), TypeScript (19%), Python (13%) |
| License | Apache-2.0 |
| Stars | 91 |
| Latest release | v0.31.3 (Jun 28, 2026) — 508 commits, actively maintained |
| Rust SDK | `CompressorClient` builder API, embeddable in-process |

### What it does

mcp-compressor replaces the upstream tool list with exactly 2 meta-tools: `get_tool_schema(tool_name)` and `invoke_tool(tool_name, input)`. The model must ask for a schema before calling any tool. This achieves 70–99% token reduction on the initial tool list.

### Gap analysis vs. Phase 1 requirements

The fundamental interaction model is incompatible with the allowlist requirement. The requirement is to expose a small, named set of tools with their full schemas upfront so Claude can call them directly — the same way it calls native tools. mcp-compressor's 2-meta-tool pattern requires Claude to first discover what tools exist and then request their schemas, which changes model behavior and adds round-trip latency.

There is no config-driven per-server allowlist. There is no TOML configuration for "expose only these 5 tools from this server." The tool filter feature mentioned in docs controls what tools the compressor indexes, not what it exposes with full schemas.

### Phase 2 viability

The Rust SDK is the right dependency for Phase 2 (schema compression). The `CompressionLevel` enum and `CompressorClient` builder provide tested, production-quality schema stripping logic. Adding `mcp-compressor` as a `[dependency]` and calling its compression utilities is more correct than reimplementing schema trimming by hand.

### Fork delta

Forking to add allowlist behavior would require rewriting the core protocol layer, which is the majority of the codebase. The benefit of using it as a library (Phase 2) outweighs the cost of forking it.

---

## Option 2: pro-vi/mcp-filter

**Verdict: Viable — as reference implementation and optional sidecar fallback.**

| Attribute | Value |
|-----------|-------|
| Language | Python 3.10+ |
| License | MIT |
| Stars | Not publicly stated (listed on lobehub.com) |
| Latest release | Active; v0.2.0 schema pruning planned |
| Deploy model | Standalone binary, run via `uvx mcp-filter run ...` |

### What it does

mcp-filter is a pure allowlist proxy. It intercepts `tools/list`, filters to the explicitly allowed tool names or regex patterns, and forwards `tools/call` transparently. Supports stdio and HTTP/SSE upstream. Demonstrated 72% token reduction in the README (50k → 13.7k tokens) for a real Claude Code session.

This is the closest existing match to Phase 1 requirements.

### Gap analysis

- Python runtime adds a process and startup latency. For a local personal proxy this is acceptable, but it requires Python 3.10+ on the host.
- No TOML config file: allowlists are CLI args only. The planned v0.2.0 roadmap doesn't add config file support.
- No token counting metrics or tool call frequency tracking for allowlist pruning.
- No auto-allowlist generation from session history.
- No integration with claude-proxy-rs dashboard or metrics.
- The deny-pattern approach is add-on to the allowlist, not the primary mechanism.

### Sidecar option

mcp-filter works today and can be used immediately as a sidecar while Phase 1 of the native Rust proxy is built. Installed via `uv tool install mcp-filter`, invoked from `mcp.json` with zero Rust code. This covers the most urgent token reduction need (Atlassian Rovo, Slack) in days rather than weeks.

---

## Option 3: ThomasTartrau/mcp-rtk

**Verdict: Not recommended for this use case.**

| Attribute | Value |
|-----------|-------|
| Language | Rust |
| License | MIT |
| Stars | 3 |
| Latest release | 8 tags, 30 commits — early stage |

### What it does — and what it does not do

mcp-rtk compresses tool **responses** after a tool call completes, through an 8-stage filter pipeline (strip nulls, condense users, truncate strings, etc.). It sits between Claude and the MCP server as a stdio wrapper.

It does **not** filter or compress the `tools/list` response. It does not address schema tokens at session start. The problem statement in requirements.md is 42.6k tokens consumed by tool schemas before any work happens. mcp-rtk saves tokens on tool call results, which is a different problem.

With 3 stars and 30 commits, maturity is too low for a production dependency. However, the hot-reloadable TOML preset system is good design that informs the mcp-proxy.toml format for Phase 2 response filtering (if that is ever added).

---

## Option 4: Dumbris/mcpproxy

**Verdict: Not recommended for adoption. Recommended as Phase 3 architecture reference.**

| Attribute | Value |
|-----------|-------|
| Language | Python + Faiss + SQLite |
| License | Not stated in search results |
| Stars | Listed on PyPI as `smart-mcp-proxy` |
| Deploy model | `pip install smart-mcp-proxy` |

### What it does

mcpproxy federates multiple MCP servers behind a single `retrieve_tools` meta-function. The agent passes a natural-language query; the proxy scores the full tool corpus via BM25 or HuggingFace embeddings (Faiss-backed), returns the top-K tools, and emits `notifications/tools/list_changed` to register them dynamically.

### Why it is not adoptable directly

- Python + Faiss + ML deps violate the constraint "no external SaaS dependencies; all data local." The HuggingFace backend sends tool descriptions to external APIs.
- The BM25 backend (pure lexical) is the closest to Phase 3 requirements and is adoptable as a design pattern.
- mcpproxy's MCP spec compliance detail is notable: it emits `notifications/tools/list_changed` properly, which is exactly the open question in requirements.md Section "Rabbit Holes" — dynamic tool re-registration. This confirms the spec does support it.

### Phase 3 reference value

The architecture (SQLite for persistence, BM25 for scoring, `retrieve_tools` meta-function, `DYNAMIC` vs `CALL_TOOL` modes) is the right blueprint for Phase 3. The implementation language is wrong, but the design can be replicated in Rust.

---

## Option 5: ooples/token-optimizer-mcp

**Verdict: Not recommended. Wrong problem domain.**

| Attribute | Value |
|-----------|-------|
| Language | TypeScript |
| License | Open source (ooples org) |
| Stars | 407+ |

### What it does

token-optimizer-mcp is a caching and compression layer for tool *results*. It stores compressed tool call outputs in SQLite using Brotli compression and provides 61 tools for file operations, API caching, and context window management. Tiktoken for token counting.

It does not filter tool schemas at session start. The 42.6k token problem is entirely unaddressed. This tool is solving a different problem (reducing repetitive tool result tokens across a long session) which is out of scope for Phases 1–2.

---

## Option 6: rmcp (Official Rust MCP SDK)

**Verdict: Recommended — use as a transport crate, not a framework.**

| Attribute | Value |
|-----------|-------|
| Language | Rust |
| License | Apache-2.0 (under modelcontextprotocol org) |
| Version | v1.8.0 |
| Maintainer | Anthropic / modelcontextprotocol GitHub org |

### What it provides

rmcp is the official Rust SDK for MCP. It provides pluggable stdio and HTTP/SSE transports with a `Transport` trait, type-safe JSON-RPC message types, and a service layer for building MCP servers and clients. The `tools/list`, `tools/call`, and `notifications/tools/list_changed` message types are all defined.

At v1.8.0 with official maintainer backing, this is stable enough for production use. The Apache-2.0 license is compatible with the dotfiles repo.

### How to use it

Add `rmcp` to claude-proxy-rs's Cargo.toml and use its `ClientHandler` and `ServerHandler` traits for the proxy's upstream connection and Claude-facing server respectively. This avoids implementing JSON-RPC framing over stdio from scratch, which is error-prone (especially around partial reads, newline framing, and backpressure).

Note: the `4t145/rmcp` crate on crates.io (the non-official one) has more downloads historically but is not under the official org. Prefer `rmcp` from `modelcontextprotocol/rust-sdk`.

---

## Option 7: Fork/Adapt mcp-compressor into claude-proxy-rs

**Verdict: Not recommended. Use as a library dependency instead.**

### Delta analysis

The mcp-compressor codebase is a polyglot monorepo (Rust core + TypeScript + Python bindings). The Rust portion is the core compression engine. Forking and adapting it to add an allowlist layer on top of its paradigm would require:

1. Bypassing the 2-meta-tool architecture entirely
2. Adding TOML config parsing for per-server allowlists
3. Adding `tools/call` pass-through without the `invoke_tool` wrapper
4. Adding token counting and frequency metrics

That is equivalent to building from scratch with the compression logic borrowed from mcp-compressor. The cleaner path is to use mcp-compressor as a library crate for Phase 2 compression and build the allowlist layer independently.

**Integration risk**: mcp-compressor's Rust crate API is currently the `CompressorClient` builder, which spawns a local session proxy. Embedding it in-process for Phase 2 schema compression (not the full 2-meta-tool proxy) requires using its internal compression utilities directly, which may not be a stable public API. Check `mcp-compressor/crates/` for internal crate structure before committing to this path.

---

## Option 8: Build from Scratch — Phase 1 Allowlist Proxy

**Verdict: Recommended. Estimated 1–2 weeks for Phase 1.**

### Implementation scope

A new binary `mcp-proxy` in the claude-proxy-rs workspace. Core logic:

1. **JSON-RPC stdio proxy loop**: Read JSON-RPC messages from Claude Code over stdin, forward to upstream server (spawned subprocess for stdio servers or HTTP client for SSE servers), intercept `tools/list` responses to filter to the configured allowlist, pass all other messages through unmodified.

2. **HTTP/SSE upstream**: Connect to remote MCP endpoint using the existing `reqwest` and `eventsource-stream` deps already in Cargo.toml. The existing SSE handling in `main.rs` is a working reference for backpressure and connection lifetime handling.

3. **TOML config**: `mcp-proxy.toml` with per-server blocks: `[server.atlassian]`, `allowed_tools = [...]`. Load at startup; support `SIGHUP` reload (one-liner with `tokio::signal`).

4. **Transport**: Use `rmcp` for JSON-RPC framing over stdio rather than implementing it by hand. Fall back to raw stdin/stdout line-by-line if rmcp's API surface proves inconvenient.

### What already exists in claude-proxy-rs

- `tokio` (full features): async I/O, `Command` for spawning subprocesses, signal handling
- `reqwest` (stream + rustls): HTTP client for SSE upstream connections
- `eventsource-stream`: SSE parsing, already used in production
- `serde_json::Value`: JSON-RPC message parsing without generated types
- `tracing` + rolling file logger: metrics and debug logging infrastructure
- Pattern for config structs: `Config::from_env()` in `config.rs`

The Phase 1 proxy is a new binary with approximately 500–800 lines of Rust. The SSE upstream path is the highest risk and should be prototyped first (per requirements.md Feasibility Risks #1).

### Phase 1 does not need

- rmcp server implementation (just JSON-RPC pass-through)
- Embedding algorithms, Faiss, or SQLite
- Schema compression (Phase 2)
- Dynamic tool re-registration (Phase 3)

### Phase 2 addition (2 weeks)

Add schema compression to the `tools/list` response by trimming `description` fields and deduplicating `$ref` patterns. Either implement this directly (straightforward JSON manipulation) or pull in mcp-compressor's Rust compression utilities as a `[dependency]`.

### Phase 3 addition (2–3 weeks)

Replace per-server allowlist with a `search_tools(query)` meta-tool backed by in-memory BM25 search over the full tool corpus. Use the `bm25` crate (not `tantivy` — full-text indexing is overkill for 200 tools). SQLite persistence for the tool corpus index via `rusqlite` or a simple JSON file.

---

## BM25 vs tantivy for Phase 3

**Verdict: Use `bm25` crate. Do not write bespoke BM25 logic.**

| Crate | Fit | Notes |
|-------|-----|-------|
| `bm25` (crates.io) | Best fit | Lightweight in-memory search, built-in tokenizer with stemming, designed for exactly this use case |
| `bm25_turbo` | Overkill | Pre-computed indices for 8M+ docs; startup cost is wrong for 200 tools |
| `tantivy` | Overkill | Lucene-class engine; adds significant compile time and binary size for 200 documents |
| `probly-search` | Viable | Trie-based inverted index, low memory, mobile-targeted |
| LLM-generated BM25 | Not recommended | BM25 has correctness edge cases (IDF with single-doc corpus, tokenization boundaries, scoring normalization). A bespoke implementation from an LLM is a correctness risk; the `bm25` crate is 4 lines of API and battle-tested. |

---

## Summary Table

| Option | Phase | Verdict | Reason |
|--------|-------|---------|--------|
| mcp-compressor (adopt) | 1 | Not recommended | Wrong paradigm: 2-meta-tool model, not allowlist |
| mcp-compressor (library dep) | 2 | Viable | Use compression utilities only; check internal API stability |
| pro-vi/mcp-filter (sidecar) | 1 | Viable | Immediate: deploy as Python sidecar while Rust proxy is built |
| mcp-rtk | 1–2 | Not recommended | Compresses responses, not schemas; 3 stars |
| Dumbris/mcpproxy | 3 | Viable (reference only) | Phase 3 architecture; confirms `tools/list_changed` is spec-compliant |
| ooples/token-optimizer-mcp | — | Not recommended | Wrong problem domain (response caching) |
| rmcp (crate) | 1 | Recommended | Official transport layer; use as dep, not as framework |
| Build from scratch + rmcp | 1 | Recommended | 1–2 weeks; existing deps cover 80% of scaffolding |
| `bm25` crate | 3 | Recommended | Right size for 200-tool corpus; do not handroll BM25 |

---

## Recommended Path

**Phase 1 (weeks 1–2):** Build `mcp-proxy` binary in claude-proxy-rs workspace using `rmcp` for transport and `serde_json::Value` for allowlist filtering. TOML config. SSE upstream prototype in week 1.

**Immediate bridge (today):** Deploy `mcp-filter` (Python sidecar via `uvx`) to cover Atlassian and Slack while the Rust proxy is being built. This unblocks the token reduction goal immediately.

**Phase 2 (weeks 3–4):** Add schema compression inline. Evaluate mcp-compressor Rust internals for reuse; fallback to hand-written JSON field stripping (simpler than it sounds).

**Phase 3 (weeks 5–6):** `search_tools` meta-tool backed by `bm25` crate. Use mcpproxy's DYNAMIC mode (with `notifications/tools/list_changed`) as the design reference.
