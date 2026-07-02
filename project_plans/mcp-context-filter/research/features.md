# Research: MCP Context Filter — Feature Landscape & Edge Cases

**Date**: 2026-07-02
**Researcher**: Claude (Sonnet 4.6)
**Purpose**: Inform Phase 1–3 design of the mcp-context-filter proxy in claude-proxy-rs

---

## Summary

The MCP protocol provides clean hooks for tool list interception (`tools/list`) and call forwarding (`tools/call`), and supports dynamic tool registration via `notifications/tools/list_changed` — but client support for this notification is uneven (Claude Code likely supports it; the web client does not). Three prior-art tools address the same problem differently: `pro-vi/mcp-filter` (allowlist, Node), `atlassian-labs/mcp-compressor` (two-tool wrapper, Rust/TS/Python), and `Dumbris/mcpproxy` (semantic FAISS search, Python). None integrate with an existing Rust/Axum proxy. The highest-risk design question is auth token forwarding: admin-provisioned cloud connectors use OAuth 2.1 Bearer tokens managed by the claude.ai session layer, and there is no documented mechanism for a local stdio proxy to intercept and replay those tokens — this requires prototyping before committing to Phase 1 scope.

---

## Options Surveyed

### Option A — Allowlist Proxy (pro-vi/mcp-filter pattern)
Static per-server allowlist in config. `tools/list` filters to declared tools; `tools/call` forwards verbatim. Node.js reference: [github.com/pro-vi/mcp-filter](https://github.com/pro-vi/mcp-filter). Also `@respawn-app/tool-filter-mcp` (regex denylist variant).

### Option B — Two-Tool Compression Wrapper (atlassian-labs/mcp-compressor pattern)
Replace full tool inventory with two generic wrapper tools: `get_tool_schema(tool_name)` and `invoke_tool(tool_name, tool_input)`. Optional third tool `list_tools()` at max compression. Rust SDK available. Reduces initial tokens by 70–97%. Reference: [github.com/atlassian-labs/mcp-compressor](https://github.com/atlassian-labs/mcp-compressor).

### Option C — Semantic Tool Discovery (Dumbris/mcpproxy pattern)
Index all tool descriptions as embeddings (FAISS + SQLite). Expose a single `retrieve_tools(query)` meta-tool. On call: return top-K matching schemas, emit `notifications/tools/list_changed` to register them for the session. Python + heavy ML deps. Reference: [github.com/Dumbris/mcpproxy](https://github.com/Dumbris/mcpproxy).

### Option D — BM25 Lexical Search (lightweight Phase 3 variant)
Same meta-tool pattern as C, but use BM25 instead of embeddings. ~87% top-5 recall, no GPU/ONNX dependency. Appropriate as Phase 3 starting point before adding embedding upgrade path.

### Option E — Schema Field Stripping (description compression)
Keep all tools in `tools/list` but strip verbose `description` fields, truncate `title` to 60 chars, drop optional JSON Schema annotations (`examples`, `default`, `$comment`). Complementary to A–D.

---

## Trade-off Matrix

| Approach | Token Reduction | Phase | Complexity | LLM Usability Risk | Auth Sensitivity |
|---|---|---|---|---|---|
| A: Allowlist | 50–75% (depends on config quality) | 1 | Low | None — full schemas exposed | None — proxy transparent |
| E: Schema stripping | +20% on top of A | 2 | Low | Low — names intact, descriptions shorter | None |
| B: Two-tool wrapper | 70–97% | 2+ | Medium | Medium — LLM must call get_tool_schema first | None |
| D: BM25 meta-tool | ~90%+ on large catalogs | 3 | Medium | Medium — recall misses on synonym gap | None |
| C: FAISS semantic | ~95%+ | 3+ | High | Low — better recall than BM25 | None |

Recommendation for phasing: A in Phase 1, E in Phase 2, D in Phase 3 (FAISS as optional upgrade).

---

## MCP Protocol Reference

### tools/list request/response (JSON-RPC 2.0)

```jsonc
// Request
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": { "cursor": "optional-pagination-cursor" }
}

// Response — array of ToolDefinition objects
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "search_issues",           // filterable field — proxy intercepts here
        "description": "Search Jira...",   // compressible field
        "inputSchema": {                   // JSON Schema object — can contain $ref, $defs
          "type": "object",
          "properties": { ... },
          "required": [ ... ]
        },
        "annotations": {                   // optional; hints for clients
          "readOnlyHint": true,
          "destructiveHint": false,
          "idempotentHint": true,
          "openWorldHint": false
        }
      }
    ],
    "nextCursor": "cursor-for-next-page"  // pagination — proxy must handle multi-page upstream
  }
}
```

**Fields the proxy can filter or transform:**
- `name` — used for allowlist matching
- `description` — primary compression target
- `inputSchema.description` fields on properties — secondary compression target
- `annotations` — can be preserved or stripped; no LLM impact
- `inputSchema.$defs` + `$ref` — deduplication target; some clients (VS Code Copilot) fail on unresolved `$ref` — proxy should optionally inline refs

### tools/call request/response

```jsonc
// Request
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "search_issues",
    "arguments": { "query": "open bugs" }
  }
}

// Success response
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [ { "type": "text", "text": "..." } ],
    "isError": false
  }
}

// Tool execution failure (upstream returned error)
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [ { "type": "text", "text": "Upstream returned 500: Internal Server Error" } ],
    "isError": true    // LLM sees this and can self-correct
  }
}

// Protocol-level error (method not implemented, malformed request)
{
  "jsonrpc": "2.0",
  "id": 2,
  "error": {
    "code": -32601,
    "message": "Method not found",
    "data": "Tool 'search_issues' does not exist"
  }
}
```

**Key distinction for the proxy:**
- Upstream transport failures (HTTP 5xx, connection refused, timeout) → translate to `isError: true` result so LLM can reason about the failure
- Protocol errors (-32601, -32602, -32603) → pass through as-is; Claude Code surfaces these in the UI rather than to the LLM

### initialize handshake — what the proxy must declare

The proxy acts as the MCP server Claude Code connects to. It must respond to `initialize` with:

```jsonc
{
  "jsonrpc": "2.0",
  "id": 0,
  "result": {
    "protocolVersion": "2025-11-25",    // negotiate with upstream; advertise same version
    "capabilities": {
      "tools": {
        "listChanged": true             // MUST declare if proxy will emit notifications/tools/list_changed (Phase 3)
      }
    },
    "serverInfo": {
      "name": "mcp-context-filter",
      "version": "0.1.0"
    },
    "instructions": "This proxy exposes a filtered subset of upstream tools."
  }
}
```

The proxy must complete its own `initialize` handshake with the upstream server before it can respond to Claude Code's `initialize`. This means proxy startup has two serial round trips before any tool call can succeed.

### notifications/tools/list_changed — Phase 3 dynamic discovery

```jsonc
// Server → Client notification (no response expected)
{ "jsonrpc": "2.0", "method": "notifications/tools/list_changed" }
```

**How dynamic discovery works:**
1. Proxy declares `capabilities.tools.listChanged: true` in its `initialize` response.
2. LLM calls the meta-tool `search_tools(query)`.
3. Proxy selects top-K matching tools from the full catalog index.
4. Proxy sends `notifications/tools/list_changed` to Claude Code.
5. Claude Code re-calls `tools/list`; proxy now returns the K newly active tools.
6. LLM can call those tools normally.

**Client support gap:** The PulseMCP article notes that many MCP clients do not support `notifications/tools/list_changed`. For Claude Code specifically, the Gemini CLI GitHub issue #13850 shows this was only recently added to Gemini CLI (2025) — Claude Code's support status needs confirmation via testing. If unsupported, Phase 3 falls back to the always-registered meta-tool approach: `search_tools` returns schema text in its response (no re-registration needed), and the LLM calls `invoke_tool(name, args)` as a separate step.

---

## Risk and Failure Modes

### R1 — Auth Token Forwarding (HIGH RISK, Phase 1 blocker)
Admin-provisioned connectors (Slack, Atlassian Rovo) use OAuth 2.1 Bearer tokens managed by the claude.ai session layer. The token is injected at the HTTP level by Claude Code when it connects to the cloud connector URL. If Claude Code is configured to use a local stdio proxy instead of the direct HTTP/SSE URL, the proxy receives stdio stdio and has no mechanism to obtain the upstream OAuth token.

Known pattern from the connector bug tracker: even when OAuth completes, claude.ai sometimes fails to forward the Bearer token to the upstream MCP server (anthropics/claude-ai-mcp issues #393, #46140). This suggests the token injection mechanism is fragile.

**Mitigation options:**
- Phase 1 fallback: user manually copies API token (Atlassian API key, Slack bot token) into `mcp-proxy.toml`; proxy injects it as `Authorization: Bearer` on outbound HTTP calls.
- Long-term: investigate if Claude Code stdio transport passes auth env vars or a credentials file that the proxy can read.

### R2 — SSE Transport Proxying (MEDIUM RISK)
Cloud MCP connectors use HTTP/SSE (Slack, Atlassian) or Streamable HTTP (newer). Proxying requires the proxy to act as both an SSE server (toward Claude Code stdio bridge) and an SSE client (toward upstream). The 2025-11-25 MCP spec deprecates SSE in favor of Streamable HTTP, but existing admin-provisioned connectors may still use SSE. Backpressure and connection lifetime handling in Axum's SSE support needs validation under load.

**Note:** Streamable HTTP is now the recommended transport. New connectors likely use it; legacy ones may still be SSE.

### R3 — Dynamic Tool Re-registration in Active Session (MEDIUM RISK, Phase 3 only)
If Claude Code does not process `notifications/tools/list_changed`, Phase 3 dynamic discovery cannot work as designed. The fallback (LLM calls `search_tools` → receives schema text → calls `invoke_tool`) avoids the need for re-registration but requires two LLM round trips per tool use and loses JSON Schema validation on the invocation.

### R4 — JSON Schema `$ref` Resolution (LOW-MEDIUM RISK)
Tool schemas from large servers (Atlassian, GitHub) can contain nested `$ref` and `$defs`. Some MCP clients fail on unresolved refs (confirmed for VS Code Copilot). The proxy's compression layer must handle:
- Circular references (drop recursive property at detected cycle depth)
- Multi-level nesting (no published depth limit in spec; FastMCP uses a practical limit)
- Schema deduplication via `$ref` that reduces token count when same schema referenced multiple times

### R5 — Pagination in tools/list (LOW RISK)
The `tools/list` method supports a `cursor` pagination field. Large servers may paginate their tool list. The proxy must fetch all pages from upstream and merge before filtering/responding. Failure to do so silently drops tools from pages 2+.

### R6 — Tool Not in Allowlist Called by LLM (HANDLED BY DESIGN)
If Claude Code calls `tools/call` for a tool the proxy filtered out (e.g., LLM hallucinated a tool name, or config was recently changed), the proxy should return `-32601 Method not found` with a clear message. Because the tool was not in `tools/list`, the LLM should not normally attempt to call it — but if it does, the `-32601` error is visible in Claude Code's UI, not surfaced to the LLM as an `isError`. This means the LLM will not self-correct; the user must investigate. Mitigation: proxy log a warning with the tool name for observability.

### R7 — Allowlist Bootstrap Accuracy (LOW RISK, operational)
Auto-generating an allowlist from session history requires parsing MCP call logs. Claude Code does not expose a structured MCP call log file. Fallback: parse `~/.claude/` conversation JSONL for tool call entries. Unconfirmed whether this data is accessible or in a stable format.

---

## Migration and Adoption Cost

- **For Tyler (primary user):** Add proxy entries to Claude Code `.mcp.json`; mark originals as `disabled`. Estimated 30 min for initial setup + 1 hr for allowlist tuning per server.
- **For dotfiles users:** Opt-in; copy `mcp-proxy.toml.example` and run `mcp-filter init` equivalent. No breaking changes to existing setups.
- **Rollback:** Set `mcp_proxy_enabled = false` in `mcp-proxy.toml` or remove proxy entries from `.mcp.json`. Original servers re-enabled in next Claude Code session.
- **Dependency on claude-proxy-rs:** The proxy is an additional binary compiled from the same repo. No new runtime deps for Phase 1 (pure Rust). Phase 3 adds ONNX runtime for local embeddings (~50 MB download).

---

## Operational Concerns

- **Token metering:** Proxy must count tokens before and after filtering. Use `tiktoken` or a simple byte-estimate heuristic (1 token ≈ 4 bytes for JSON). Log per-server before/after to the existing claude-proxy-rs metrics endpoint.
- **Connection lifecycle:** Each Claude Code session starts a new MCP connection. Proxy must support multiple concurrent connections (e.g., sub-agents). Axum handles this natively but needs testing.
- **Upstream reconnect:** If upstream HTTP/SSE connection drops, proxy should reconnect with exponential backoff and surface `isError: true` on any pending `tools/call` rather than hanging indefinitely. SLO: fail fast after 5 seconds per requirements.
- **Secret hygiene:** OAuth tokens in auth headers must not appear in proxy debug logs. Use a log filter that redacts `Authorization: Bearer *` and any field named `token`, `key`, or `secret`.
- **Config hot reload:** Allowlist changes in `mcp-proxy.toml` require proxy restart (Phase 1). No hot reload needed — Claude Code sessions are short-lived.

---

## Prior Art and Lessons Learned

### pro-vi/mcp-filter (Node.js)
- **What it does:** Static allowlist/denylist with optional rename prefix to avoid tool name collisions across servers. Multi-upstream support (`--upstream NAME=cmd`).
- **Key lesson:** Rename prefix is valuable when running multiple proxied servers side by side — tool name collisions are real. The proxy should namespace tools as `<server>__<tool>` or enforce unique names across servers.
- **What it lacks:** No schema compression (full schemas still exposed), no dynamic discovery, no Rust implementation.
- Real-world result: 72% token reduction on a 50k-token baseline by allowlisting ~10 tools from each of several large servers.

### atlassian-labs/mcp-compressor (Rust SDK available)
- **What it does:** Replaces tool inventory with 2–3 generic wrapper tools. 70–97% initial token reduction. Available in Rust, TypeScript, Python.
- **Key lesson:** The two-tool pattern (get_schema + invoke_tool) is elegant but changes the LLM interaction model. The LLM must make one extra round-trip per new tool use. Works best when the LLM is predictable about which tools it needs. Atlassian uses this in Rovo Dev production.
- **What it lacks:** No allowlist support (all tools accessible via invoke_tool), no search/discovery, no integration with an existing proxy codebase.
- **Rust integration path:** The Rust SDK (`mcp-compressor/rust`) could potentially be vendored into claude-proxy-rs as a library rather than an external binary.

### Dumbris/mcpproxy (Python)
- **What it does:** FAISS + SQLite vector store, hybrid BM25+semantic search, `notifications/tools/list_changed` compliant, `retrieve_tools(query)` meta-tool.
- **Key lesson:** Phase 3 implementation pattern is well-validated. The FAISS + SQLite persistence layer is the right architecture for local-first deployments. BM25 alone achieves ~87% top-5 recall; FAISS hybrid search improves this to ~95%+.
- **What it lacks:** Python + heavy ML deps (FastMCP, sentence-transformers, FAISS). Not suitable for embedding directly in claude-proxy-rs without FFI.
- **Phase 3 takeaway:** Use `candle` (Rust ML) or `ort` (ONNX Runtime Rust bindings) for local embeddings instead of Python. BM25 in pure Rust (`bm25` crate or manual implementation) for Phase 3 starting point.

### @respawn-app/tool-filter-mcp (Node.js)
- **What it does:** Regex-based denylist (not allowlist). Ships a `--list-tools` command that outputs tool names/schemas in table, CSV, or JSON format.
- **Key lesson:** A `--list-tools` dry-run CLI command is essential for allowlist bootstrapping. Build this into `mcp-filter list-tools --server <name>` as part of Phase 1.

### Atlassian Rovo Tool Catalog (real-world data point)
- Speakeasy catalogs 31 tools; PolicyLayer reports 20. Variation due to authentication method (API token vs OAuth exposes different tool subsets) and snapshot timing.
- Atlassian's own blog confirms 30k+ tokens for tool descriptions across multiple servers.
- Schema complexity: Jira/Confluence schemas use nested `$ref` for ARI (Atlassian Resource Identifier) types, issue field definitions, and ADF (Atlassian Document Format) body structures. ADF schemas in particular can be deeply nested (4–5 levels) with `oneOf`/`anyOf` unions.

### Slack MCP Tool Catalog (real-world data point)
- Official Slack MCP server (`mcp.slack.com/mcp`) has 10–15 tools based on category descriptions. The claude.ai Slack connector (visible in this session) exposes approximately 15+ tools with detailed schemas (~500 tokens per tool = ~7,500–9,500 tokens total, matching the ~9.5k figure in requirements).
- Tool complexity: Slack's canvas tools have deeply nested markdown content schemas. Message search tools have complex filter parameter schemas. Schema nesting depth: 3–4 levels typical.

### Claude Code MCP Auth Delivery Pattern
- For stdio servers: Claude Code launches the binary and passes environment variables. Auth tokens can be delivered via env vars in `.mcp.json` `env` block.
- For HTTP/SSE cloud connectors: Claude Code manages OAuth 2.1 + PKCE tokens internally. The Bearer token is injected as `Authorization: Bearer <token>` on each HTTP request. **There is no documented mechanism for a local proxy to intercept these tokens.**
- The local proxy wrapping a cloud connector must therefore handle auth itself: either via user-provided API key in `mcp-proxy.toml`, or by acting as the OAuth client (implementing the PKCE flow on behalf of the user). The latter is the correct long-term approach but is high complexity for Phase 1.
- Known bug: even in the managed flow, claude.ai sometimes completes OAuth but never sends the Bearer token (anthropics/claude-ai-mcp #393). This may not affect Claude Code CLI, which has a separate auth stack.

---

## Open Questions

1. **Does Claude Code CLI support `notifications/tools/list_changed`?** Must confirm by testing. If not, Phase 3 must use the `invoke_tool` fallback pattern instead of dynamic re-registration.

2. **How does Claude Code pass OAuth tokens to HTTP/SSE MCP servers configured in `.mcp.json`?** Is there a `headers` field? An `authToken` field? Or does it use a pre-configured env var? This is the Phase 1 auth rabbit hole and must be prototyped before designing the proxy's outbound auth mechanism.

3. **Does claude-proxy-rs currently have any MCP protocol parsing, or is it purely an HTTP message proxy?** If it is purely HTTP, the proxy will need to implement full JSON-RPC 2.0 message parsing and routing, which is non-trivial.

4. **What format does Claude Code use for MCP call logs?** The `~/.claude/` directory presumably has JSONL conversation logs. Do these include MCP tool call names and arguments? This determines the feasibility of auto-generating allowlists from history.

5. **What is the token counting method used by Claude Code?** If token counts in the requirements (42.6k, 13k, 9.5k) are based on Claude's tokenizer (cl100k_base or similar), the proxy should use the same tokenizer for accurate before/after metrics, not a byte estimate.

---

## Recommendation

**Phase 1 design is sound and low-risk for the allowlist filtering mechanism itself.** The primary risk is auth token forwarding for cloud connectors — this should be prototyped in week 1 before committing to the full Phase 1 scope. If auth forwarding proves intractable without manual API key config, document it as a known limitation and proceed with API-key-based auth for Slack and Atlassian.

**Phase 2 schema compression** should be implemented as field stripping (remove `description` from `inputSchema` properties, truncate top-level `description` to 80 chars) rather than the full two-tool wrapper pattern. The two-tool wrapper changes the LLM interaction model in ways that may break existing workflows; field stripping is transparent.

**Phase 3 dynamic discovery** should start with BM25 (pure Rust, no ML deps) exposing a `search_tools(query)` meta-tool, with the `invoke_tool` fallback for clients that don't support `list_changed`. Add ONNX/candle-based embedding as an optional upgrade.

**Prior art gap:** No existing tool combines allowlist config + schema compression + auth forwarding + dynamic discovery in a single Rust binary. The closest is mcp-compressor (Rust, compression only) + mcp-filter (Node, allowlist only). The integration work in claude-proxy-rs is the unique contribution.
