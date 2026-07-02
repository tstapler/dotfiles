# Research: MCP Proxy Pitfalls & Risk Areas

**Date**: 2026-07-02
**Phase**: 2 — Research
**Parent**: requirements.md

## Design Review Template

### What Is Being Built

A Rust MCP proxy (`mcp-context-filter`) that wraps admin-provisioned cloud MCP servers, intercepts `tools/list`, filters/compresses tool schemas, and forwards `tools/call` upstream. Three phases: allowlist (Phase 1), schema compression (Phase 2), dynamic discovery via BM25/embeddings (Phase 3).

---

## Risk Area 1: OAuth Token Forwarding

### What Could Go Wrong

Admin-provisioned cloud connectors (Slack, Atlassian Rovo) use OAuth 2.1 managed entirely by the `claude.ai` session layer via `mcp-proxy.anthropic.com`. The token is **not available as a bearer token in a local config**; it is injected by Anthropic's backend proxy, not by Claude Code directly.

Key confirmed pitfalls:

- **Token is opaque to local processes.** The `claudeai-proxy` (Anthropic's cloud-side proxy) holds the OAuth token. A local stdio proxy wrapping an admin-provisioned HTTP/SSE connector will not have access to these tokens at all — there is no hook or environment variable exposing them. The local proxy intercepts a *stdio* session, not the upstream HTTPS/OAuth session.
- **OAuth token refresh is broken via the proxy path.** Even in Anthropic's own proxy, token refresh has been confirmed as never attempted for connectors going through `mcp-proxy.anthropic.com`. The fix applied to Claude Code's direct HTTP path (v2.1.59+) was never ported to the proxy path. Any custom local proxy inherits this brittleness.
- **Static bearer tokens are not supported.** The admin connector UI only accepts OAuth 2.1 client credentials; there is no static bearer token field. Fallback: users manually configure API keys directly in `mcp-proxy.toml` (outside the claude.ai auth flow entirely).
- **S256 PKCE is required.** If the proxy ever needs to initiate its own OAuth flow (Phase 3 scenarios), it must implement `code_challenge_method=S256`. Token endpoint must accept `application/x-www-form-urlencoded`, not JSON.
- **No delegation semantics.** The OAuth token's `sub` claim is the user; there is no `act` claim distinguishing Claude-as-agent from the user. The proxy cannot verify whether a token was issued for agent use.

### Design Constraints

The Phase 1 proxy intercepts stdio between Claude Code and a local MCP server stub — it does **not** sit on the HTTP path between claude.ai and upstream cloud connectors. This means the proxy cannot and should not attempt to forward OAuth tokens. The realistic architecture:

1. Keep admin-provisioned cloud connectors (Slack, Atlassian) configured directly in Claude Code (not wrapped by the local proxy).
2. The local proxy wraps only servers where Claude Code makes the outbound call — i.e., local stdio servers or servers where the proxy itself has credentials.
3. For cloud connectors, use the `deniedMcpServers` approach to hide them from Claude Code, then re-expose them via the local proxy only if the user has their own API key configured in `mcp-proxy.toml`.

**Security requirement (from requirements.md):** Tokens must not be logged. Add an explicit deny-list of field names (`token`, `authorization`, `bearer`, `api_key`, `secret`) to the metrics/logging layer.

**Sources:**
- [OAuth token refresh never attempted for proxy path — Issue #228](https://github.com/anthropics/claude-ai-mcp/issues/228)
- [claudeai-proxy not forwarding OAuth flow — Issue #248](https://github.com/anthropics/claude-ai-mcp/issues/248)
- [Claude Connector Authentication docs](https://claude.com/docs/connectors/building/authentication)
- [OAuth tokens fail to persist across restart — Issue #52565](https://github.com/anthropics/claude-code/issues/52565)

---

## Risk Area 2: SSE Proxy Pitfalls

### What Could Go Wrong

The MCP HTTP/SSE transport has known, documented problems that motivated its deprecation in May 2025 in favour of Streamable HTTP:

- **Persistent connection requirement.** Old SSE requires a connection held open indefinitely, even when idle, creating a resource drain in the proxy. Any network hiccup (sleep/wake, VPN change) breaks it irrecoverably — there is no reconnect built into the protocol.
- **Atlassian deprecation deadline.** Atlassian Rovo's HTTP+SSE transport is deprecated with end-of-life on **30 June 2026**. The proxy must support Streamable HTTP (POST + optional SSE response) to work with Rovo post-deprecation.
- **Backpressure is not defined in SSE.** The proxy must implement its own flow control; if upstream sends events faster than Claude Code consumes them, the proxy's internal buffer will grow unbounded. Use `tokio::sync::mpsc` with bounded channels (`capacity = 64` or similar).
- **Protocol version header.** Streamable HTTP requires `MCP-Protocol-Version` on every subsequent request after initialize. If the proxy strips or fails to forward this header, the upstream returns `400 Bad Request`.
- **DNS rebinding.** A local MCP proxy listening on `127.0.0.1` without auth is vulnerable to DNS rebinding from malicious sites. The proxy should bind to a specific port with a random token or use Unix domain sockets.
- **Connection lifetime tracking.** If the upstream SSE connection dies, the proxy must propagate the error to Claude Code immediately rather than silently queuing requests that will never be answered.

### Design Requirements

- Support both SSE (legacy) and Streamable HTTP transports.
- Use bounded async channels between the upstream SSE reader and the downstream stdio writer.
- Forward `MCP-Protocol-Version` header verbatim from the `initialize` handshake.
- Implement a 5-second upstream liveness check (aligns with the requirements.md alerting condition).
- Prefer Unix domain socket or a loopback-only listener for the local proxy endpoint.

**Sources:**
- [MCP SSE Transport deprecation — Atlassian notice](https://community.atlassian.com/forums/Atlassian-Remote-MCP-Server/HTTP-SSE-Deprecation-Notice/ba-p/3205484)
- [MCP Transports specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [Why MCP moved away from SSE — Auth0](https://auth0.com/blog/mcp-streamable-http/)
- [SSE MCP server with OAuth in Rust — Shuttle](https://www.shuttle.dev/blog/2025/08/13/sse-mcp-server-with-oauth-in-rust)

---

## Risk Area 3: MCP Protocol Compliance — Tool Schema Breakage

### What Could Go Wrong

Claude Code uses tool schemas for grounding — it reads descriptions and parameter schemas to decide how to form a tool call. A proxy that mutates schemas incorrectly will cause silent misbehaviour, not loud errors:

- **`$ref` and `oneOf` break cross-client.** Optional fields combined with `$ref` that pass Claude Desktop can hard-fail in other clients. Compression that introduces `$ref` deduplication (Phase 2) may produce schemas that Claude Code rejects or misinterprets. Safe compression must produce flat, self-contained JSON Schema objects with no `$ref`.
- **Tool search deferred discovery and `tool_reference` blocks.** Claude Code's tool search (`ENABLE_TOOL_SEARCH`) is disabled by default when `ANTHROPIC_BASE_URL` points to a non-first-party host because most proxies don't forward `tool_reference` blocks. If claude-proxy-rs is already rewriting the base URL, tool search may already be disabled. The Phase 3 `search_tools` meta-tool approach sidesteps this by being an explicit tool call rather than a protocol-level feature.
- **Description truncation changes grounding quality.** Phase 2 aggressive compression strips descriptions. If descriptions drop below the information Claude needs to select the correct tool, it will use the wrong tool or hallucinate parameters — no error is surfaced, only wrong behaviour.
- **`alwaysLoad` flag.** If the proxy does not set this for servers where the user always wants all tools visible, Claude Code may defer discovery and the tools will appear unavailable until a search is performed.
- **Input validation changed in spec 2025-11-25.** Input validation errors must be returned as Tool Execution Errors, not Protocol Errors, to allow model self-correction. A proxy returning protocol errors on bad inputs breaks Claude's retry loop.

### Design Requirements

- Phase 2 compression must produce flat JSON Schema (no `$ref`, no `oneOf` in compressed output).
- Add a schema round-trip test: compress → parse → verify parameter names and types are unchanged.
- Keep at minimum: `name`, `description` (one-line), `parameters.properties` (name + type + required flag). Strip `examples`, `default`, verbose `description` on individual properties.
- Return tool validation errors as `ToolError` (MCP error code in the tool result), not as JSON-RPC errors.

**Sources:**
- [MCP Tools design guide — Apigene](https://apigene.ai/blog/mcp-tools)
- [Claude Code MCP docs](https://code.claude.com/docs/en/mcp)
- [ENABLE_TOOL_SEARCH and non-first-party proxy — Claude Code](https://code.claude.com/docs/en/mcp)
- [MCP Schema Validation Policy — MuleSoft](https://docs.mulesoft.com/gateway/latest/policies-included-mcp-schema-validation)

---

## Risk Area 4: Filtering Safety — Mid-Session Tool Blocking

### What Could Go Wrong

If the allowlist in `mcp-proxy.toml` accidentally excludes a tool that Claude is mid-session trying to use, the failure mode depends on how the proxy surfaces the error:

- **Silent missing tool.** If the proxy simply omits the tool from `tools/list`, Claude never knows the tool exists. It will attempt to accomplish the task another way or fail without explanation. No error is raised; the session continues on a degraded path.
- **Hard error on `tools/call`.** If Claude discovers a tool via one path (e.g., cached from a previous session) but the proxy's allowlist blocks it, calling it will return an error. Claude Code has been observed to hang indefinitely when a proxy silently drops a `tool_result` — the CLI waits for the complete set of tool results before continuing.
- **Session freeze on connection failure.** If the upstream server becomes unreachable (or the proxy fails to start it), Claude Code enters a running state that cannot proceed and appears frozen.
- **Pattern mismatch in managed allowlist.** If `allowedMcpServers` patterns in Claude Code's managed settings don't match the proxy server name, the proxy server itself silently never starts — tools appear as completely missing.

### Design Requirements

- On startup, validate that all servers referenced in `mcp-proxy.toml` are reachable; emit a structured error and exit if any are not (`mcp_proxy_enabled = false` fallback).
- On `tools/call` for a tool not in the active allowlist, return a proper MCP `ToolError` with a descriptive message: `"Tool '<name>' is not in the active allowlist. Check mcp-proxy.toml."` — never silently drop the result.
- Implement the `feature_flag: mcp_proxy_enabled = false` bypass from requirements.md to ensure rollback is always available.
- Log all filtered `tools/call` attempts at WARN level (without logging argument values that may contain PII/tokens).
- For Phase 3: when a tool expires from the active set, return `ToolError` with a message indicating the user should re-run `search_tools` to re-register it.

**Sources:**
- [MCP proxy silently hangs on tool_use results — Issue #38437](https://github.com/anthropics/claude-code/issues/38437)
- [Claude Code drops HTTP MCP tools mid-session — Issue #4598](https://github.com/anthropics/claude-code/issues/4598)
- [Session freeze on blocked MCP server — Issue #28067](https://github.com/anthropics/claude-code/issues/28067)
- [Claude Code error reference](https://code.claude.com/docs/en/errors)

---

## Risk Area 5: Version Drift — Upstream Tool Catalog Changes

### What Could Go Wrong

Upstream MCP servers (Slack, Atlassian) update their tool catalogs without notice. The proxy's cached or hardcoded allowlist becomes stale:

- **Silent parameter rename.** If an upstream tool renames a parameter (e.g., `query` → `search_query`), the proxy forwards the call with the old parameter name. The upstream server silently ignores the unknown field and searches for nothing. The LLM receives empty results and reasons around them rather than detecting the failure.
- **Tool renamed or removed.** A tool in the allowlist no longer exists upstream. The proxy returns it in `tools/list` (since it's in the allowlist config), Claude calls it, and the upstream returns a `MethodNotFound` error. If the proxy does not translate this into a clear `ToolError`, Claude may retry in a loop.
- **Schema drift in `tools/list` response.** The upstream changes a required parameter to optional, or adds a new required parameter. Calls with old signatures silently fail or behave incorrectly.
- **Stale proxy-side tool schema cache.** If the proxy caches the upstream `tools/list` response (for performance), and the upstream updates its schemas, the proxy serves stale schemas indefinitely until the cache is invalidated.

### Design Requirements

- Cache upstream `tools/list` responses with a TTL (default: 5 minutes for Phase 1, configurable). On cache miss or startup, always re-fetch from upstream.
- On `tools/call` failure with upstream error code indicating unknown method or invalid params, log a WARNING: `"Upstream returned error for tool '<name>' — schema may have drifted. Run 'mcp-proxy refresh' to re-sync."`.
- Add a `mcp-proxy refresh` CLI subcommand that clears the schema cache and re-fetches all upstream `tools/list` responses, printing a diff of added/removed/changed tools.
- For Phase 3: validate that tools in the BM25/embedding index still exist in the upstream catalog on each session start.

**Sources:**
- [Schema drift is the new dependency hell — DEV Community](https://dev.to/nesquikm/my-mcp-tools-broke-silently-schema-drift-is-the-new-dependency-hell-5c49)
- [Stale tools cache after reconfiguration — Kong Gateway changelog](https://developer.konghq.com/gateway/changelog/)
- [FastMCP changelog — stale catalog fixes](https://gofastmcp.com/changelog)
- [MCP spec changelog 2025-11-25](https://modelcontextprotocol.info/specification/2025-11-25/changelog/)

---

## Risk Area 6: Phase 3 Search Quality — Silent False Negatives

### What Could Go Wrong

Phase 3 exposes a `search_tools(query)` meta-tool. If it returns wrong results or misses the correct tool, Claude silently fails to find the capability it needs:

- **BM25 alone misses semantic queries.** BM25 is exact-term matching. A query like "notify the team" will miss `slack_send_message` because no terms overlap. Anthropic's own tool search uses BM25 internally but has confirmed 34% accuracy on a 2,792-tool dataset with BM25 alone vs. 94% with hybrid BM25+embeddings.
- **Embeddings silently miss exact tool names.** Pure vector search pools all tokens into a fixed vector, destroying lexical identity. "github_create_pull_request" as a query may return semantically similar but incorrect tools. The LLM receives plausible-looking wrong tools and attempts to call them.
- **False negatives cause zero-error failures.** When `search_tools` returns no results or wrong results, Claude does not raise an error — it reasons around the absence. This is the hardest failure mode to detect and debug.
- **Embedding model quality on tool descriptions.** General-purpose embedding models trained on natural language underperform on short, terse tool descriptions (e.g., `"Lists issues in a repository"`). Domain-specific or code-oriented models (e.g., `all-MiniLM-L6-v2`, `bge-small-en`) outperform general models on this distribution.
- **Index staleness.** If tools are added to the upstream catalog but the embedding index is not rebuilt, new tools are invisible to semantic search even if BM25 would find them by name.

### Design Requirements

- Phase 3 must implement **hybrid BM25 + embedding search** (not BM25 alone) given the confirmed accuracy gap.
- For the ONNX local embedding model, prefer `bge-small-en-v1.5` or `all-MiniLM-L6-v2` (both ONNX-compatible, ~23MB, sub-50ms on M-series Mac).
- Return the top-K results with a confidence score; if the highest score is below a threshold (tunable, default 0.3), return the results but add a metadata field `"low_confidence": true` so the caller can surface a warning.
- Rebuild the BM25 index and invalidate the embedding index on every upstream `tools/list` cache refresh (see Risk Area 5).
- Add an integration test: given a known query, assert the expected tool appears in top-3 results.

**Sources:**
- [Beyond BM25: The Future of MCP Tool Discovery — MCPProxy](https://mcpproxy.app/blog/2026-03-15-beyond-bm25-tool-discovery/)
- [BM25 vs vector search for MCP tool discovery — StackOne](https://www.stackone.com/blog/mcp-tool-search-bm25-tfidf-hybrid/)
- [Hybrid search in production — TianPan.co](https://tianpan.co/blog/2026-04-12-hybrid-search-production-bm25-dense-embeddings)
- [BM25 vs vector search production pitfalls — DEV Community](https://dev.to/aloknecessary/bm25-vs-vector-search-choosing-the-right-retrieval-strategy-for-production-systems-599n)

---

## Risk Area 7: Async/Concurrency Pitfalls in Rust (Tokio)

### What Could Go Wrong

The proxy will have concurrent async tasks: upstream SSE reader, downstream stdio writer, schema cache manager, metrics recorder. The following are the documented failure modes for this pattern:

- **`std::sync::Mutex` held across `.await` — deadlock.** This is the most common async Rust trap. If a `std::sync::MutexGuard` is held when an `.await` is reached, other tasks on the same executor thread cannot acquire it, causing a deadlock. The compiler does not warn about this when the guard type implements `Send`.
- **Single Tokio mutex, no resource held at deadlock.** A documented Tokio-specific trap: futures can stop polling without holding a resource (if they are paused or dropped improperly), causing other waiters to block forever on the semaphore/mutex. Standard deadlock detection tools miss this because no thread holds a lock.
- **`block_on` inside `spawn_blocking` with `tokio::sync::Mutex`.** Mixing `block_on` and async mutexes in blocking contexts creates a three-way deadlock between the OS scheduler, Tokio's task scheduler, and the semaphore. Never call `block_on` in a `spawn_blocking` closure that touches async mutexes.
- **Mutex poisoning on panic.** If a task panics while holding a `std::sync::Mutex`, the mutex is poisoned and all future attempts to lock it return `PoisonError`. In a long-running proxy, this causes total service failure.
- **Long-held guards blocking I/O.** Keeping a `MutexGuard` alive across I/O operations (upstream HTTP call, disk write) blocks other tasks from acquiring shared state, causing latency spikes or starvation.

### Design Requirements

- Use `tokio::sync::Mutex` by default for all shared state that may be accessed across `.await` points.
- For the schema cache (read-heavy, infrequent writes): use `tokio::sync::RwLock` to allow concurrent reads without blocking.
- Prefer **message passing via `tokio::sync::mpsc` channels** over shared mutex for the upstream SSE reader ↔ downstream stdio writer communication.
- Never hold a lock guard across an `.await` — enforce via code review checklist.
- For the metrics store (high-write): use `dashmap` (lock-free concurrent hashmap) or per-server `AtomicU64` counters rather than a global mutex.
- Use `Arc<RwLock<SchemaCache>>` pattern: acquire write lock only during cache refresh, acquire read lock for all `tools/list` responses.

**Sources:**
- [Deadlocking Tokio Mutex without holding lock — e6data](https://www.e6data.com/blog/deadlocking-tokio-mutex-without-holding-lock/)
- [How to deadlock Tokio with a single mutex — Turso](https://turso.tech/blog/how-to-deadlock-tokio-application-in-rust-with-just-a-single-mutex)
- [Tokio shared state tutorial](https://tokio.rs/tokio/tutorial/shared-state)
- [`block_in_place` + `block_on` + `tokio::sync::Mutex` deadlock — Issue #7892](https://github.com/tokio-rs/tokio/issues/7892)
- [Mastering Rust Arc and Mutex — Medium](https://medium.com/@Murtza/mastering-rust-arc-and-mutex-a-comprehensive-guide-to-safe-shared-state-in-concurrent-programming-1913cd17e08d)

---

## Risk Area 8: Config Errors — Malformed TOML or Dead Server References

### What Could Go Wrong

`mcp-proxy.toml` is the single point of configuration. Errors here are startup-time failures or silent runtime degradation:

- **Malformed TOML.** A syntax error causes the proxy to fail to start entirely. Claude Code will see the stdio server exit with a non-zero code. If the error message isn't surfaced clearly, the user sees tools as simply missing.
- **Server name referenced in allowlist but not in `[servers]` table.** The proxy starts but the referenced server entry is a no-op. All calls to that server's tools silently fail.
- **Server URL unreachable at startup.** If `mcp_proxy_enabled = true` but the upstream URL is a 404 or the process isn't running, the proxy should fail fast with a clear error (requirements.md: "Alert condition: if upstream server unreachable for >5 seconds, fail fast with clear error").
- **`deniedMcpServers` not updated after adding proxy.** If the user adds the local proxy to Claude Code config but forgets to add the original server to `deniedMcpServers`, both the proxy and the original server are loaded. Claude Code sees duplicate tools; calling either is undefined behaviour depending on which server responds first.
- **Phase 3 embedding model path misconfigured.** If the ONNX model file path in `mcp-proxy.toml` is wrong, the proxy should fall back to BM25-only mode with a warning, not crash.

### Design Requirements

- On startup, validate `mcp-proxy.toml` fully before starting any async work: parse TOML, check all `[servers]` sections have required fields, attempt a HEAD/ping to each upstream URL (with 5s timeout).
- Emit structured startup errors with actionable messages: `"Error: server 'atlassian-rovo' referenced in allowlist but not defined in [servers]. Add [servers.atlassian-rovo] to mcp-proxy.toml."`.
- Provide a `mcp-proxy validate` subcommand that runs all startup checks without starting the server.
- Detect duplicate tool names across proxied servers and warn at startup.
- For Phase 3: if ONNX model is missing or fails to load, fall back to BM25 and log `WARN: embedding model unavailable, using BM25 fallback`.

**Sources:**
- [Troubleshoot MCP Server for Claude integrations](https://www.blockchain-council.org/claude-ai/troubleshoot-mcp-server-for-claude-integrations-common-errors-debugging-fixes/)
- [Claude Code MCP error reference](https://code.claude.com/docs/en/errors)
- [Session freeze on unreachable MCP server — Issue #28067](https://github.com/anthropics/claude-code/issues/28067)

---

## Synthesis: Top 5 Highest-Risk Items

| Rank | Risk | Likelihood | Impact | Mitigation |
|------|------|-----------|--------|------------|
| 1 | OAuth tokens for admin-provisioned cloud connectors are inaccessible to a local proxy | High | High | Do not wrap cloud connectors that use claude.ai OAuth; use per-user API keys in config instead |
| 2 | `notifications/tools/list_changed` ignored by Claude Code | High | High | Phase 3 dynamic discovery cannot rely on this notification; use explicit `search_tools` meta-tool instead |
| 3 | `std::sync::Mutex` held across `.await` causes silent deadlock | Medium | Critical | Enforce `tokio::sync::Mutex` for all shared state; code review checklist item |
| 4 | Upstream schema drift causes silent wrong-tool selection | Medium | High | TTL-based schema cache + `mcp-proxy refresh` + startup schema validation |
| 5 | Phase 3 BM25-only search causes silent false negatives (34% accuracy) | High | Medium | Implement hybrid BM25+embeddings from the start; BM25-only is not acceptable for Phase 3 |

---

## Open Questions Updated

1. **OAuth architecture confirmation needed.** Can we confirm that local stdio proxy does NOT sit on the HTTP path for admin-provisioned cloud connectors? If so, the OAuth forwarding rabbit hole from requirements.md is not applicable to Phase 1 at all.
2. **`notifications/tools/list_changed` in Claude Code.** Confirmed broken as of Issue #13646. Phase 3 must use the explicit `search_tools` meta-tool approach, not dynamic tool re-registration.
3. **Atlassian SSE end-of-life 30 June 2026.** Proxy must support Streamable HTTP before this date to maintain Rovo connectivity.
4. **`ENABLE_TOOL_SEARCH` interaction.** If claude-proxy-rs sets `ANTHROPIC_BASE_URL`, Claude Code's built-in tool search is already disabled. The Phase 3 `search_tools` meta-tool may be the only path to deferred discovery.
