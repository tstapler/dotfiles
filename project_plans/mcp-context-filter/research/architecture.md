# Architecture Research: MCP Context Filter Proxy

**Date**: 2026-07-02
**Researcher**: Claude (Sonnet 4.6)
**Phase gate**: Research → Planning
**Feature**: mcp-context-filter (3-phase MCP proxy)

---

## Design Review Template

### Problem Statement (restated)

42.6k tokens (21% of 200k window) consumed by 14 admin-provisioned MCP cloud connector schemas at every Claude Code session start. Need a local proxy that sits between Claude Code and upstream servers to filter, compress, and dynamically serve tools.

---

## Section 1: Transport Architecture Decision

### Question: stdio proxy vs. HTTP proxy?

**Answer: stdio is the right transport for the proxy frontend.**

Claude Code discovers and launches MCP servers in two ways:
1. **stdio** — Claude Code spawns the server as a subprocess, communicates via stdin/stdout JSON-RPC. Config format: `{ "serverName": { "command": "/path/to/binary", "args": [...] } }` in `.mcp.json` files placed at `~/.claude/` or project root.
2. **HTTP/SSE (Streamable HTTP)** — Claude Code connects to a pre-running HTTP server. Admin-provisioned cloud connectors use this: they have `mcpsrv_` IDs in the auth cache and appear as `claude.ai [ServerName]` entries injected by the claude.ai session layer.

For local proxy purposes, **stdio is correct** because:
- Claude Code supports and prefers stdio (`Clients SHOULD support stdio whenever possible` per spec)
- A stdio server binary is configured with a simple `.mcp.json` entry — no port conflicts, no background service management
- The proxy backend (outbound calls to upstream cloud servers) uses HTTP/SSE — this is independent of the frontend transport

**Admin-provisioned connector interception pattern**:
Admin-provisioned servers (Atlassian Rovo, Slack, etc.) cannot be modified. The workaround is:
1. Add the real upstream URL + auth to `mcp-proxy.toml`
2. Add the admin server's name to `deniedMcpServers` in `~/.claude/settings.json`
3. Add the local proxy entry to a project/user `.mcp.json` pointing to the proxy binary

### Question: New Axum routes vs. separate binary vs. separate Tokio task?

**Answer: New `[[bin]]` target in the existing Cargo.toml, separate binary.**

Rationale:
- The existing `claude-proxy-rs` binary is an HTTP server (Axum + Tokio). An MCP stdio server runs by reading stdin/writing stdout — fundamentally different execution model. Mixing both into one binary would require spawning the stdio logic in a separate Tokio task and would complicate the binary's startup semantics.
- A `[[bin]]` target shares the workspace's `Cargo.toml` dependencies and Rust toolchain but produces a separate binary (`mcp-proxy`). This keeps shared code (config parsing, metrics, auth helpers) reusable.
- Claude Code spawns the proxy as a subprocess per-server — having a dedicated binary is cleaner operationally.

**Implementation path**:
```toml
# Cargo.toml addition
[[bin]]
name = "mcp-proxy"
path = "src/bin/mcp-proxy/main.rs"
```

Add `rmcp` (official MCP Rust SDK, `modelcontextprotocol/rust-sdk`) for the MCP protocol layer.

### Question: How does Claude Code do transport negotiation?

Claude Code uses the config entry's `command` field to determine transport:
- If `command` is present → stdio subprocess
- If `url` is present (or plugin manifests specify an HTTP URL) → Streamable HTTP client

There is no runtime negotiation for stdio; the protocol version is negotiated during the `initialize` handshake via `protocolVersion` field in `InitializeRequest`/`InitializeResult`.

---

## Section 2: mcp-proxy.toml Config Structure

```toml
# Global feature flag — set false to bypass proxy entirely
enabled = true

# Dry-run mode: proxy passes all tools through, just logs token counts
dry_run = false

# Per-server configuration
[servers.atlassian_rovo]
display_name = "Atlassian Rovo (proxied)"
upstream_url = "https://mcp.atlassian.com/v1/mcp"
# auth: "oauth" triggers stored OAuth token flow; "bearer" uses explicit token
auth = "oauth"
# Allowlist: empty = pass all (use dry_run first to discover)
allowed_tools = [
  "search",
  "getJiraIssue",
  "createJiraIssue",
  "editJiraIssue",
  "addCommentToJiraIssue",
  "searchJiraIssuesUsingJql",
  "getConfluencePage",
  "searchConfluenceUsingCql",
]
# Phase 2 compression level: off | light | aggressive
compression = "light"

[servers.slack]
display_name = "Slack (proxied)"
upstream_url = "https://mcp.slack.com/v1/mcp"
auth = "oauth"
allowed_tools = [
  "slack_send_message",
  "slack_read_channel",
  "slack_read_thread",
  "slack_search_public",
  "slack_search_users",
  "slack_search_channels",
]
compression = "light"

[servers.brave_search]
display_name = "Brave Search (proxied)"
# stdio upstream also supported
upstream_command = "/path/to/brave-mcp"
upstream_args = ["--api-key", "${BRAVE_API_KEY}"]
allowed_tools = ["brave_web_search"]
compression = "off"

[compression]
# Phase 2 defaults
max_description_chars = 120        # truncate to first sentence up to N chars
strip_examples = true              # remove `examples` fields from JSON Schema
inline_refs = true                 # resolve $ref inline (remove $defs)
strip_default_descriptions = true  # remove descriptions that match field name

[phase3]
# Phase 3 dynamic discovery (off by default)
enabled = false
search_backend = "bm25"            # bm25 | embedding
top_k = 8                          # tools returned per search_tools() call
tool_expiry_turns = 5              # remove tool from active set after N quiet turns
embedding_model = ""               # path to ONNX model (Phase 3 only)

[metrics]
token_count_log = true
call_frequency_log = true
latency_histogram = true
```

**Claude Code config update** (`~/.claude/settings.json` fragment to add):
```json
{
  "deniedMcpServers": [
    { "serverName": "claude.ai Atlassian Rovo" },
    { "serverName": "claude.ai [beta] Snowflake Agents" }
  ]
}
```

**`.mcp.json` entry** (placed at `~/.claude/.mcp.json` or project root):
```json
{
  "mcp-proxy-atlassian": {
    "command": "/path/to/mcp-proxy",
    "args": ["--server", "atlassian_rovo", "--config", "~/.config/mcp-proxy.toml"]
  },
  "mcp-proxy-slack": {
    "command": "/path/to/mcp-proxy",
    "args": ["--server", "slack", "--config", "~/.config/mcp-proxy.toml"]
  }
}
```

One binary invocation per proxied server is the cleanest model — each instance handles one upstream server's allowlist + compression.

---

## Section 3: Schema Compression — Token Waste Analysis

### Where tokens are wasted in JSON Schema

Based on analysis of typical MCP server schemas (Atlassian ~13k tokens, Slack ~9.5k):

| Source | Token fraction | Compressibility |
|--------|---------------|-----------------|
| `description` fields (tool level) | ~35% | High — truncate to first sentence |
| `description` fields (parameter level) | ~25% | Medium — truncate to 80 chars |
| `$defs` / `$ref` boilerplate | ~15% | High — inline or deduplicate |
| `examples` arrays in JSON Schema | ~10% | Aggressive — strip entirely |
| `title` fields duplicating `name` | ~5% | Aggressive — strip if redundant |
| Required structural keys | ~10% | None — required by protocol |

### Description truncation algorithm

```
light:
  tool.description = first_sentence(description, max_chars=200)
  param.description = first_sentence(description, max_chars=120)
  strip examples: false
  strip $defs: false

aggressive:
  tool.description = first_sentence(description, max_chars=80)
  param.description = truncate(description, max_chars=50)
  strip examples: true
  inline $refs: true (eliminates $defs section)
  strip redundant titles: true
```

**First-sentence extraction**: Split on `. ` or `\n`, take first segment, append `…` if truncated. Avoid breaking mid-word. Prefer sentence-final `.` over arbitrary char truncation.

**$ref inlining**: Walk the schema, resolve `$ref` pointers against `$defs`, inline the definition at each usage site, then drop `$defs`. If a definition is used >3 times and is large (>200 chars when serialized), keep as `$ref` to avoid expansion blowup.

**Safety constraint**: Never truncate `enum` values or `required` arrays — these affect tool correctness.

### Expected token reduction per phase

| Phase | Mechanism | Expected reduction from baseline |
|-------|-----------|----------------------------------|
| Phase 1 (allowlist only) | Drop unused tools | 50–70% |
| Phase 2 light compression | Truncate descriptions | +10–15% |
| Phase 2 aggressive | Truncate + strip examples + inline refs | +15–25% |
| Phase 3 dynamic | Only active tools in context | Approaches 90–95% |

---

## Section 4: Dynamic Tool Discovery (Phase 3)

### Does MCP support dynamic tool list changes within a session?

**Yes, via `notifications/tools/list_changed`.**

The MCP spec (2025-03-26 and later) explicitly supports this:
```json
{
  "capabilities": { "tools": { "listChanged": true } }
}
```
When `listChanged: true` is declared in `InitializeResult`, the server may send:
```json
{ "jsonrpc": "2.0", "method": "notifications/tools/list_changed" }
```
The client (Claude Code) is then expected to re-fetch `tools/list`.

**Implementation note**: Claude Code's handling of `tools/list_changed` notifications needs empirical verification in Phase 3. If Claude Code does not re-fetch on notification, the fallback is to always expose: `search_tools(query)` + top-K most-called tools from session history + a fixed number of "hot" slots.

### BM25 over 200 tools — memory and latency

**Verdict: Trivially fast. No concern.**

The `bm25` crate (Michael-JB/bm25, docs.rs/bm25) provides an in-memory search engine. For 200 documents (tool descriptions averaging 50–200 tokens):
- Index build time: <10ms
- Query latency: <1ms (sub-millisecond at this corpus size)
- Memory: ~500KB for 200 documents

The `bm25_turbo` crate achieves 28,217 queries/second on 8.8M documents — 200 documents is effectively zero overhead.

**BM25 or embedding?** BM25 is correct for Phase 3 (local, no external API, <1ms latency). Embedding-based search (Phase 3 option) would require an ONNX model (~50MB+, 10–50ms inference) and is only warranted if semantic search quality proves necessary.

### Phase 3 workaround if `listChanged` is not honored

If Claude Code does not re-fetch on notification:
1. Always expose `search_tools(query: string, server: string) -> ToolList` as a permanent meta-tool per server
2. `search_tools` returns full schemas for top-K matches as text in the response
3. The model calls `invoke_tool(name, args)` which the proxy routes upstream
4. No dynamic tool registration needed — model works via the meta-tool pair

This is essentially the atlassian-labs/mcp-compressor "Pattern 1" architecture (see prior art).

---

## Event-Command-Policy Table

| Event | Actor | Command | Policy |
|-------|-------|---------|--------|
| Claude Code session starts | Claude Code | Spawns `mcp-proxy --server slack` subprocess | One subprocess per server in `.mcp.json` |
| `initialize` request arrives on stdin | mcp-proxy | Read upstream server URL + auth from `mcp-proxy.toml`; connect to upstream via HTTP/SSE; complete MCP handshake | Fail fast if upstream unreachable: return error in `InitializeResult` |
| `tools/list` request arrives | mcp-proxy | Fetch upstream `tools/list`; filter to `allowed_tools`; apply compression pipeline; return filtered list | Cache upstream tool list for session lifetime; only re-fetch on upstream `listChanged` |
| `tools/call` request arrives | mcp-proxy | Forward to upstream verbatim (no modification) | Log tool name + latency to metrics; do NOT log arguments (may contain secrets) |
| Upstream server unreachable >5s | mcp-proxy | Return JSON-RPC error `-32603` with `"upstream server unreachable"` message | Alert threshold from requirements |
| `mcp_proxy_enabled = false` in config | mcp-proxy | Exit with code 0 immediately | Claude Code will fail to spawn; entry should be removed from `.mcp.json` when disabled |
| Phase 3: `search_tools(query)` called | mcp-proxy | Run BM25 query over full tool catalog; return top-K tool schemas as text in tool result | K=8 default; schemas returned as full JSON in text content |
| Phase 3: `notifications/tools/list_changed` to be sent | mcp-proxy | After `search_tools` call resolves new tools, send notification; Claude Code re-fetches `tools/list` | Only if Claude Code empirically handles re-fetch; otherwise use meta-tool pattern |
| Tool not in allowlist is called | mcp-proxy | Return error result: `"Tool [name] is not in the allowed list for this server"` | Log attempted call for allowlist auditing |
| Session ends (stdin closes) | mcp-proxy | Disconnect from upstream; flush metrics; exit | Graceful shutdown via stdin EOF detection |

---

## Section 5: Auth Rabbit Hole Resolution

**Key finding**: Admin-provisioned connectors (Atlassian Rovo, Slack, Gmail, etc.) have `mcpsrv_` IDs in Claude Code's auth cache. Their OAuth tokens are managed by the claude.ai session layer and are NOT accessible to a local proxy without separate auth configuration.

**Practical path**:
1. For servers like Atlassian MCP (`https://mcp.atlassian.com/v1/mcp`) and Slack MCP, OAuth is standard browser-based. The proxy can run its own OAuth flow (as mcp-compressor does) and store tokens in a local keychain.
2. Use the `auth = "oauth"` config option in `mcp-proxy.toml`; on first run, proxy opens browser OAuth flow and stores token.
3. For servers that genuinely require the claude.ai session token (claude.ai-specific proxy URLs), the proxy cannot easily intercept these — those servers should remain in `deniedMcpServers` rather than proxied.

**Risk level**: Medium-High. Phase 1 should prototype with a single server (e.g., brave-search which uses an API key, or a non-claude.ai server) before tackling OAuth-gated cloud connectors.

---

## Section 6: Prior Art Analysis

### atlassian-labs/mcp-compressor

- Rust crate `mcp_compressor` (crates/mcp-compressor in monorepo)
- Supports: stdio frontend, HTTP/SSE backend, OAuth, compression levels (low/medium/high/max)
- Architecture: `CompressorClient::builder().server(...).compression_level(...).build().connect().await`
- **Recommendation**: Evaluate embedding `mcp_compressor` as a library crate dependency rather than reimplementing compression. The crate handles SSE transport, OAuth flow, and compression in ~66% Rust. Would save 2–3 weeks of Phase 1+2 work.

### pro-vi/mcp-filter (Node.js)

- Allowlist pattern: `allowed_tools` per server in config
- Relevant for: allowlist config schema design

### Dumbris/mcpproxy (Python)

- Faiss + embedding for Phase 3 dynamic discovery
- Architecture reference for BM25/embedding fallback pattern

---

## Section 7: Key Risks and Open Questions

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | Claude Code does not honor `notifications/tools/list_changed` | Medium | Phase 3 only | Use meta-tool pattern as fallback |
| R2 | OAuth tokens for claude.ai-proxied servers not obtainable | High | Phase 1 scope | Start with API-key servers; OAuth flow for direct-URL servers |
| R3 | SSE backpressure in reqwest when proxying large tool results | Low | Phase 1 | Use `eventsource-stream` (already in Cargo.toml) |
| R4 | `mcp_compressor` crate license incompatibility (Apache-2.0) | Low | All phases | Apache-2.0 is compatible; verify before embedding |

### Open questions mapped to requirements

| Requirements Q# | Question | Research finding |
|----------------|----------|-----------------|
| Q1 | How does Claude Code pass OAuth to admin connectors? | Via claude.ai session layer; local proxy cannot intercept without separate OAuth |
| Q2 | Does MCP support dynamic tool list updates within session? | Yes — `notifications/tools/list_changed` in spec; Claude Code support needs empirical verification |
| Q3 | Does claude-proxy-rs have MCP awareness? | No — purely HTTP messages proxy. MCP proxy is a new concern. |
| Q4 | Best local embedding model for Phase 3? | BM25 sufficient for Phase 3; skip embedding unless quality inadequate. If embedding needed: `nomic-embed-text` via candle or onnxruntime (50MB, ~10ms on Apple Silicon) |

---

## Sources

- [MCP Transports Spec](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)
- [MCP Tools Spec](https://modelcontextprotocol.io/specification/2025-03-26/server/tools)
- [atlassian-labs/mcp-compressor](https://github.com/atlassian-labs/mcp-compressor)
- [mcp-compressor auth docs](https://atlassian-labs.github.io/mcp-compressor/usage/auth-and-remote/)
- [mcp-compressor how-it-works](https://atlassian-labs.github.io/mcp-compressor/concepts/how-it-works/)
- [rmcp official Rust SDK](https://github.com/modelcontextprotocol/rust-sdk)
- [bm25 crate](https://docs.rs/bm25)
- [bm25_turbo crate](https://lib.rs/crates/bm25_turbo)
- [Claude Code MCP docs](https://docs.anthropic.com/en/docs/claude-code/mcp)
