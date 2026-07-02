# Implementation Plan: mcp-context-filter

Feature: MCP server proxy with 3-phase token reduction (allowlist → compression → dynamic discovery)
Date: 2026-07-02
Status: Ready for implementation
ADRs: ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007

---

## Domain Glossary

| Term | Type | Definition |
|------|------|------------|
| `ProxiedServer` | struct | One entry in mcp-proxy.toml representing a single upstream MCP server |
| `UpstreamClient` | trait | The outbound rmcp client connection to the upstream server |
| `AllowList` | type alias | `Vec<String>` — the per-server set of permitted tool names |
| `RawCatalog` | struct | The unmodified set of `ToolDefinition` objects received from an upstream server; never filtered or compressed |
| `ProcessedCatalog` | struct | The filtered and/or compressed result derived from a `RawCatalog`; stored in cache and sent to Claude Code |
| `SchemaCompressor` | struct | Transforms a `RawCatalog` into a `ProcessedCatalog` by stripping verbose description fields |
| `CompressionLevel` | enum | `Off | Light | Aggressive` — controls how aggressively descriptions are truncated |
| `BM25Index` | struct | In-memory BM25 search index over a `RawCatalog` for Phase 3 discovery |
| `ActiveSlot` | struct | One tool currently registered in the active set for a Phase 3 session |
| `ActiveSlotPool` | struct | Fixed-K pool of `ActiveSlot`s; evicts on quiet-turn expiry |
| `SearchMetaTool` | struct | The `search_tools(query)` meta-tool exposed in Phase 3 |
| `SessionMetrics` | struct | Per-session token counts and tool call frequencies |
| `TokenBudget` | struct | Before/after token counts produced by `tiktoken-rs` |
| `SchemaDrift` | enum variant | `Added | Removed | Changed` — result of comparing allowlist to upstream catalog |
| `SchemaCache` | struct | `Arc<RwLock<CachedCatalog>>` with TTL-backed invalidation |
| `McpProxyConfig` | struct | Root serde-deserialized struct for mcp-proxy.toml |
| `UpstreamTransport` | enum | `StreamableHttp | Sse | Stdio` — the protocol used to reach the upstream server |
| `AllowListBootstrap` | concept | The `init` → observe → `analyze` workflow for generating the first allowlist |
| `ProxyMode` | enum | `Observe (no filtering, log calls) | Filter (allowlist active)` |
| `ToolNotAllowedError` | error variant | Returned as JSON-RPC -32601 when a tool is called outside the allowlist |

---

## Pattern Decisions

| Decision | Chosen | Rejected | Reason Chosen | Rejected Weakness |
|----------|--------|----------|---------------|-------------------|
| Proxy frontend transport | stdio subprocess per server | HTTP sidecar (single process) | Claude Code manages lifecycle; no port conflicts; zero TCP handshake | Requires port management, startup ordering, and a long-lived background process |
| Proxy frontend transport | stdio subprocess per server | Embedded Tokio task in claude-proxy-rs main binary | Fundamentally different execution model (stdio vs HTTP server); clean operationally | Mixing stdin/stdout with an Axum HTTP server complicates binary startup semantics |
| MCP protocol layer | `rmcp` v0.16 (official SDK) | `rust-mcp-sdk` (community) | Official Anthropic org; latest spec; both server+client roles | Not official; older spec; lower maintenance commitment |
| Upstream transport | Streamable HTTP (primary), SSE (fallback) | SSE only | Atlassian SSE end-of-life June 30, 2026; Streamable HTTP is MCP 2025-06-18 standard | Legacy SSE: no reconnect, persistent connection drain, deprecated |
| Phase 1 auth | Explicit API key in mcp-proxy.toml | OAuth token forwarding | Admin-provisioned OAuth tokens are managed by Anthropic's cloud proxy; inaccessible locally | Token refresh broken on proxy path; S256 PKCE required; fragile; implementation weeks not days |
| Phase 3 search | BM25 + fastembed hybrid (fastembed default-on; opt-out via `--no-default-features`) | BM25 alone as default | BM25-only confirmed 34% recall on tool discovery; hybrid reaches 94%; default install must not silently miss 2/3 of relevant tools | BM25-only default: produces false negatives with no error signal; user has no indication that tools exist but are not found |
| Phase 3 list update | Fixed-K active slot pool (primary path) | notifications/tools/list_changed | Claude Code confirmed not handling the notification (Issue #13646) | Dynamic re-registration requires client support that is absent in Claude Code CLI |
| Schema compression | Inline field stripping | Adopt mcp-compressor 2-meta-tool interface | 2-meta-tool breaks direct tool invocation; requires LLM extra round-trip | Changes interaction model; LLM must ask for schema before calling any tool |

---

## Observability Plan

Logs:
- `INFO mcp_proxy: session_start server=<name> filtered=<n>/<total> tokens_before=<n> tokens_after=<n> pct_saved=<n>%` — emitted once per session start
- `WARN mcp_proxy: tool_not_in_allowlist tool=<name> server=<name> hint="add to [servers.<name>].allow in mcp-proxy.toml"` — once per blocked call per session
- `WARN mcp_proxy: allowed_tool_missing_upstream tool=<name> server=<name> hint="run mcp-proxy sync"` — once per stale allowlist entry per session start
- `WARN mcp_proxy: upstream_unreachable server=<name> url=<url> timeout_ms=5000 consecutive_failures=<n> hint="run: curl -s <url>/health"` — on connection failure
- `DEBUG mcp_proxy: tools_list_request server=<name> upstream_ms=<n> tools_returned=<n> tools_filtered=<n>` — per request at DEBUG level only
- Never log: OAuth tokens, Bearer headers, tool call arguments, any field named `token`, `authorization`, `api_key`, `secret`

Metrics (emitted to existing claude-proxy-rs metrics store):
- `mcp_filter_tokens_before{server}` — gauge, updated per session start
- `mcp_filter_tokens_after{server}` — gauge, updated per session start
- `mcp_filter_tools_blocked{server}` — counter, incremented per filtered tool call
- `mcp_filter_tool_calls{server,tool}` — counter, incremented per upstream call
- `mcp_filter_upstream_latency_ms{server}` — histogram (p50/p99), per upstream tools/call

Alerts (existing claude-proxy-rs dashboard extension):
- Upstream unreachable for >5s → surface as alert row in dashboard "MCP Filter" section
- Allowlist staleness: any allowed tool not seen in upstream for >7 days → "possibly removed" badge

---

## Risk Control

Feature flag: `enabled = true/false` in `mcp-proxy.toml` global section (default: true)
Rollback procedure: set `enabled = false` and restart, OR remove the proxy's `.mcp.json` entries and re-enable original servers via removing `deniedMcpServers` entries. Original admin-provisioned servers restored on next Claude Code session start.
Staged rollout:
- Phase 1 deployed and validated for ≥1 week before starting Phase 2
- Phase 2 deployed with compression_level = "off" initially; tighten to "light" after validation
- Phase 3 deployed with phase3.enabled = false; opt-in per server

---

## Unresolved Questions

- [ ] **Axum version gate (go/no-go before any code is written):** In a throwaway workspace, run `cargo add rmcp@0.16` then `cargo tree -p rmcp | grep axum`. Decision tree:
  - If `cargo tree -p rmcp | grep axum` shows `axum 0.8.x` → no conflict; proceed to Story 1.1.1.
  - If shows `axum 0.7.x` → three resolution options in order of preference:
    1. **(Preferred)** Vendor rmcp locally and patch its `Cargo.toml` axum dependency to `0.8` via `[patch.crates-io]` in the workspace root. Keeps a single binary with a single axum instance.
    2. **(Acceptable)** Pin axum to `0.7` in the claude-proxy-rs workspace root `Cargo.toml`, acceptable only if rmcp is the sole axum consumer in the workspace.
    3. **(Fallback)** Run mcp-proxy as a completely separate Cargo workspace with its own `Cargo.lock`, giving it its own axum version resolution. Means two separate binaries but fully avoids version unification.
  - Document the chosen option as an addendum to ADR-001.
  - Blocks: ALL stories — resolve before Story 1.1.1 begins — owner: implementer
- [ ] Is mcp-compressor's Rust compression API a stable public interface (not `pub(crate)` internals)? Blocks: Epic 2.2 — owner: implementer (check `crates/mcp-compressor/src/lib.rs` exports)
- [ ] Does Claude Code CLI pass `Authorization: Bearer` headers via env vars to stdio subprocess entries in `.mcp.json`? Blocks: Story 1.8.2 init design — owner: implementer (prototype test with a controlled server)
- [ ] Exact token counting method: does Claude Code use cl100k_base or the newer tiktoken model for the 42.6k baseline number? Blocks: Story 1.7.1 accuracy — owner: empirical test with tiktoken-rs `cl100k_base` vs `o200k_base`

---

## Dependency Visualization

```
Phase 1 (Must ship before Phase 2)
──────────────────────────────────

  [1.1 Binary Setup]
       │
       ▼
  [1.2 Config (TOML)]
       │
       ▼
  [1.3 stdio MCP server (rmcp)]──────────────[1.4 Upstream Client]
       │                                              │
       └──────────────────────────┐                  │
                                  ▼                  ▼
                          [1.5 Allowlist Filter + SchemaCache]
                                  │
                          [1.6 tools/call forward]
                                  │
              ┌───────────────────┴───────────────────┐
              ▼                                       ▼
       [1.7 Metrics]                        [1.8 CLI subcommands]
                                                      │
                                            [1.9 Config helper]

Phase 2 (Requires Phase 1 complete)
──────────────────────────────────

  [2.1 Compression pipeline]────[2.2 mcp-compressor eval]
              │
  [2.3 Dashboard integration]

Phase 3 (Requires Phase 1 complete; Phase 2 optional)
──────────────────────────────────────────────────────

  [3.1 BM25 index + search_tools]
              │
  [3.2 Active slot management]
              │
  [3.3 fastembed feature flag] (independent of 3.2; parallel)
```

---

## Phase 1: Tool Allowlist Proxy

### Epic 1.0: Pre-implementation Spikes

**Goal**: Empirically verify infrastructure assumptions before writing proxy code. Both spikes in this epic are blockers for downstream epics.

---

#### Story 1.0.1: Empirical validation — confirm admin-provisioned upstream URLs reachable from local subprocess

Verify whether URLs exposed via admin-provisioned `.mcp.json` entries in `settings.json` are reachable from a local shell process, and whether Claude Code injects any auth credentials into stdio subprocess env vars at startup.

**Acceptance criteria**

1. Run `curl -v <atlassian-upstream-url>` from a local shell process and confirm whether it returns HTTP 200 (URL publicly reachable) or 403/401 (URL is behind the claude.ai authentication layer and inaccessible locally).
   - Given: The upstream URL extracted from `settings.json` for the admin-provisioned Atlassian server
   - When: `curl -v <atlassian-upstream-url>` is run directly in a local shell (not via Claude Code)
   - Then: Document the HTTP response code; HTTP 200 → URL reachable without auth; HTTP 401/403 → URL requires Anthropic cloud auth and is inaccessible to local proxy

2. Build a minimal Rust stdio MCP server entry, register it in `.mcp.json`, and log all env vars injected at startup to confirm whether `ANTHROPIC_API_KEY` or any MCP-specific auth variable is present.
   - Given: A minimal `fn main()` binary that writes `std::env::vars()` to stderr and then runs the MCP handshake loop
   - When: Claude Code starts a session with this binary registered as a stdio subprocess
   - Then: Captured stderr log shows which env vars were injected; confirm presence or absence of `ANTHROPIC_API_KEY`, `MCP_AUTH_TOKEN`, or any `Authorization`-style variable

3. Document findings in `project_plans/mcp-context-filter/decisions/spike-oauth-reachability.md`.
   - If URL is NOT reachable → record as BLOCKER in ADR-004 addendum; adopt explicit API key auth (already the design decision per ADR-004); confirm no alternative path exists
   - If URL is reachable → record the HTTP auth header format required; update Story 1.4.1 to use it

4. Make a live HTTP request to `https://mcp.atlassian.com/mcp` with `Authorization: Bearer <user-atlassian-api-token>` (from `mcp-proxy.toml`) and a valid MCP initialize body. Expected: HTTP 200 (success) or HTTP 401/403 (auth rejected but endpoint reachable and NOT gated behind Anthropic's proxy). Record result in `spike-oauth-reachability.md`:
   - If HTTP 200 with a valid MCP response: record "API key auth works; proceed with ADR-004 as designed."
   - If HTTP 401: record "API key format may need adjustment; test with Atlassian REST API token format."
   - If the endpoint redirects to or returns Anthropic's mcp-proxy.anthropic.com domain: record as a **CRITICAL FINDING** in `spike-oauth-reachability.md` and escalate to human before Phase 1 implementation begins.
   Also make an equivalent live request to `https://mcp.slack.com/mcp` with a Slack Bot token and record the result in `spike-oauth-reachability.md`.

**Tasks**

- Task 1.0.1.1 (~30 min spike) — Run `curl -v` against Atlassian upstream URL; run minimal Rust stdio binary to capture injected env vars; make live authenticated requests to `https://mcp.atlassian.com/mcp` (Atlassian API token) and `https://mcp.slack.com/mcp` (Slack Bot token); write all findings to `project_plans/mcp-context-filter/decisions/spike-oauth-reachability.md` (files: throwaway `src/bin/env-probe/main.rs` + spike findings doc)

> **Blocks**: ALL of Epic 1.4 (upstream client), Epic 1.8 (init subcommand auth flow). Do not begin Epic 1.4 until this spike is complete and findings documented.

---

### Epic 1.1: Cargo Workspace Integration

**Goal**: `mcp-proxy` binary builds from the existing claude-proxy-rs Cargo workspace.

---

#### Story 1.1.1: Add `[[bin]]` target and new deps to Cargo.toml

Add the `mcp-proxy` binary declaration and new crate dependencies.

**Acceptance criteria**

1. Running `cargo build --bin mcp-proxy` succeeds (binary may be empty stub).
   - Given: Cargo.toml has the new `[[bin]]` entry and `src/bin/mcp-proxy/main.rs` exists with `fn main() {}`
   - When: `cargo build --bin mcp-proxy` is run
   - Then: Exit code 0; binary at `target/debug/mcp-proxy`

2. `cargo check` passes after adding `rmcp`, `toml`, `bm25`, `dashmap`, and `clap` deps.
   - Given: Cargo.toml includes `rmcp = { version = "0.16", features = ["server","client","transport-io","transport-sse","transport-streamable-http-client"] }`, `toml = "0.8"`, `bm25 = "0.1"`, `dashmap = "5"`, `clap = { version = "4", features = ["derive"] }`
   - When: `cargo check` is run
   - Then: No compilation errors; `cargo tree -p rmcp | grep axum` shows axum 0.8.x (not 0.7)

**Tasks**

- Task 1.1.1.0 — **[GO/NO-GO GATE — both steps must pass before Task 1.1.1.1]**
  - **Step 1 — axum version check**: In a throwaway workspace, run `cargo add rmcp@0.16 && cargo tree -p rmcp | grep axum`. Decision tree:
    - `axum 0.8.x` → no conflict; proceed to Step 2.
    - `axum 0.7.x` → apply resolution from Unresolved Questions (vendor + patch preferred); document choice in ADR-001 addendum before proceeding.
  - **Step 2 — Atlassian Streamable HTTP gate**: Make an authenticated request to the Atlassian MCP endpoint: `POST https://mcp.atlassian.com/mcp` with header `Accept: application/json, text/event-stream`. Decision tree:
    - HTTP 200 or 401 → endpoint accepts Streamable HTTP; proceed to Story 1.1.1.
    - HTTP 405 or 404 → endpoint does not accept Streamable HTTP; document finding as ADR-003 addendum and investigate alternative Atlassian endpoint before proceeding.
  - Both Step 1 and Step 2 must pass before Story 1.1.1 begins. (files: none — verification only)
- Task 1.1.1.1 — Add `[[bin]]` section and new deps to Cargo.toml (files: `stapler-scripts/claude-proxy-rs/Cargo.toml`)
- Task 1.1.1.2 — Create `src/bin/mcp-proxy/main.rs` with `fn main() {}` placeholder (files: `src/bin/mcp-proxy/main.rs`)

---

#### Story 1.1.2: Create module skeleton

Stub out the module files so that the binary compiles with all module declarations in place.

**Acceptance criteria**

1. All module files compile with empty / todo!() bodies.
   - Given: `main.rs` declares `mod mcp_proxy;` and `src/mcp_proxy/mod.rs` declares `pub mod pipeline; pub mod allowlist; pub mod upstream; pub mod server; pub mod config; pub mod cache; pub mod search; pub mod slots;`
   - When: `cargo build --bin mcp-proxy`
   - Then: No "file not found for module" errors

**Tasks**

- Task 1.1.2.1 — Create `src/mcp_proxy/mod.rs` declaring all submodules; create stub files: `src/mcp_proxy/pipeline.rs`, `src/mcp_proxy/allowlist.rs`, `src/mcp_proxy/upstream.rs`, `src/mcp_proxy/server.rs`, `src/mcp_proxy/config.rs`, `src/mcp_proxy/cache.rs`, `src/mcp_proxy/search.rs`, `src/mcp_proxy/slots.rs`; create `src/bin/mcp-proxy/metrics.rs`, `src/bin/mcp-proxy/cli.rs` (files: `src/mcp_proxy/mod.rs` + 8 submodule stubs + 2 bin-local files)
- Task 1.1.2.2 — Define `ToolListPipeline` and `ToolCallPipeline` traits in `src/mcp_proxy/pipeline.rs`; `server.rs` calls these trait methods; concrete implementations live in `allowlist.rs` (filter guard), `upstream.rs` (forwarding), `slots.rs` (slot updates), and `src/bin/mcp-proxy/metrics.rs` (token counting) — `server.rs` wires the stages but owns none of them (files: `src/mcp_proxy/pipeline.rs`)

---

### Epic 1.2: TOML Configuration

**Goal**: `McpProxyConfig` struct parses `mcp-proxy.toml` and validates before any async work begins.

---

#### Story 1.2.1: Define McpProxyConfig and ServerConfig structs

**Acceptance criteria**

1. Example mcp-proxy.toml parses without error.
   - Given: The reference TOML from architecture.md with `[global]`, `[servers.slack]`, `[servers.atlassian]`, `[compression]`, `[phase3]`, `[metrics]` sections
   - When: `toml::from_str::<McpProxyConfig>(config_text)` is called
   - Then: Returns `Ok(config)` with `config.servers["slack"].allow` containing the 8 Slack tool names

2. Unknown field produces a "did you mean" hint.
   - Given: TOML with `alowlist = [...]` instead of `allow = [...]`
   - When: Config is parsed
   - Then: Error message contains the field name and is actionable

**Tasks**

- Task 1.2.1.1 — Write `McpProxyConfig`, `GlobalConfig`, `ServerConfig`, `CompressionConfig`, `Phase3Config`, `MetricsConfig` structs with `#[derive(Deserialize)]` (files: `src/bin/mcp-proxy/config.rs`)
- Task 1.2.1.2 — Write a unit test loading the example TOML string (files: `src/bin/mcp-proxy/config.rs`)

---

#### Story 1.2.2: Config validation

Validate all semantic constraints before starting async work: upstream URLs reachable, no duplicate tool names across servers, Phase 3 model path exists (if set).

**Acceptance criteria**

1. Missing upstream_url exits with a structured error.
   - Given: `[servers.test]` block with no `upstream_url` and no `upstream_command`
   - When: `McpProxyConfig::validate()` is called
   - Then: Returns `Err` containing "server 'test' has no upstream_url or upstream_command"

2. Unreachable upstream URL fails fast within 5 seconds.
   - Given: `upstream_url = "https://127.0.0.1:19999/mcp"` (nothing listening)
   - When: `validate()` calls the HEAD check with 5-second timeout
   - Then: Returns `Err` within 5100ms with the URL and a diagnostic hint

3. Duplicate tool names across servers produce a WARN (not error).
   - Given: Two servers both allow a tool named `search`
   - When: `validate()` runs
   - Then: WARN log line mentions both server names; validate() returns `Ok`

**Tasks**

- Task 1.2.2.1 — Write `McpProxyConfig::validate(&self) -> Result<(), Vec<ConfigError>>` with URL reachability check (files: `src/bin/mcp-proxy/config.rs`)
- Task 1.2.2.2 — Write unit tests for validation errors (files: `src/bin/mcp-proxy/config.rs`)

---

### Epic 1.3: MCP stdio Server (rmcp)

**Goal**: The proxy presents as a valid MCP server to Claude Code over stdin/stdout.

---

#### Story 1.3.1: Initialize handshake over stdio

**Acceptance criteria**

1. Proxy responds to `initialize` with a valid `InitializeResult`.
   - Given: `echo '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2025-06-18","clientInfo":{"name":"test","version":"1.0"},"capabilities":{}}}' | mcp-proxy --server test-server --config /tmp/test.toml`
   - When: The binary reads from stdin and writes to stdout
   - Then: stdout contains `{"jsonrpc":"2.0","id":0,"result":{"protocolVersion":"2025-06-18","serverInfo":{"name":"mcp-context-filter","version":"0.1.0"},"capabilities":{"tools":{"listChanged":true}}}}`

**Tasks**

- Task 1.3.1.1 — Implement rmcp `ServerHandler` with `handle_initialize` (files: `src/mcp_proxy/server.rs`)
- Task 1.3.1.2 — Wire `main.rs` to run the stdio server for the `--server <name>` subcommand (files: `src/bin/mcp-proxy/main.rs`)

---

#### Story 1.3.2: Proxy pass-through for non-intercepted methods

**Acceptance criteria**

1. `prompts/list` and other non-tool methods are forwarded to upstream and the response returned verbatim.
   - Given: Upstream server implements `prompts/list`
   - When: Claude Code sends `prompts/list` to the proxy
   - Then: Proxy returns the upstream response unchanged, with the same `id`

**Tasks**

- Task 1.3.2.1 — Add pass-through handler in `server.rs` that forwards unrecognized methods to upstream via `UpstreamClient` (files: `src/mcp_proxy/server.rs`)

---

### Epic 1.4: Upstream Client Connection

**Goal**: Proxy connects to upstream MCP servers via Streamable HTTP (primary) or SSE (fallback).

---

#### Story 1.4.1: Streamable HTTP upstream client

**Acceptance criteria**

1. Proxy retrieves upstream `tools/list` over Streamable HTTP.
   - Given: An upstream server listening at `http://localhost:18080/mcp` (Streamable HTTP)
   - When: `UpstreamClient::connect(config).await` is called
   - Then: `client.list_tools().await` returns a non-empty `RawCatalog` within 200ms

2. `MCP-Protocol-Version` header is forwarded on every request after initialize.
   - Given: Upstream server requires the version header
   - When: Proxy sends a `tools/list` request
   - Then: Outbound HTTP request contains `MCP-Protocol-Version: 2025-06-18`

**Tasks**

- Task 1.4.1.1 — Implement `UpstreamClient` using rmcp `transport-streamable-http-client` feature (files: `src/bin/mcp-proxy/upstream.rs`)
- Task 1.4.1.2 — Ensure `MCP-Protocol-Version` header is injected on post-initialize requests (files: `src/bin/mcp-proxy/upstream.rs`)

---

#### Story 1.4.2: SSE transport fallback

> **Note — Atlassian SSE end-of-life**: Atlassian deprecated and disabled SSE transport for Atlassian-hosted servers (Rovo, Jira, Confluence) on June 30, 2026. SSE fallback is explicitly NOT supported for Atlassian-hosted servers. The proxy MUST return a clear error if configured to use SSE with an Atlassian upstream, directing the user to update their `mcp-proxy.toml` to use `transport = 'streamable-http'`. SSE fallback remains supported for non-Atlassian legacy servers only.

**Acceptance criteria**

1. When Streamable HTTP connect returns 404 or 405 for a non-Atlassian server, proxy retries via SSE transport.
   - Given: Non-Atlassian upstream server supports only SSE (legacy)
   - When: Proxy attempts Streamable HTTP and receives 404
   - Then: Proxy falls back to SSE transport; `client.list_tools()` succeeds

2. Atlassian-hosted upstream configured with SSE transport returns a clear error.
   - Given: `[servers.atlassian]` block has `transport = "sse"` (or Streamable HTTP fails and fallback would be SSE for an Atlassian URL)
   - When: Proxy attempts to connect to the Atlassian upstream
   - Then: Proxy returns a JSON-RPC -32603 error with message: "SSE transport is not supported for Atlassian-hosted servers (deprecated June 30, 2026). Update mcp-proxy.toml: set transport = 'streamable-http' for this server."
   - And: No SSE connection attempt is made to the Atlassian endpoint

**Tasks**

- Task 1.4.2.1 — Add transport negotiation: try StreamableHttp, catch 404/405, retry with SseTransport for non-Atlassian servers only; detect Atlassian-hosted URLs (*.atlassian.net, *.atlassian.com, rovo.atlassian.com) and return a structured error if SSE would be used (files: `src/bin/mcp-proxy/upstream.rs`)

---

#### Story 1.4.3: 5-second upstream liveness check and fail-fast

**Acceptance criteria**

1. Upstream unreachable for 5 seconds produces a -32603 error to Claude Code.
   - Given: Upstream URL is unreachable (port closed)
   - When: Claude Code sends `tools/list` to the proxy
   - Then: Proxy returns `{"jsonrpc":"2.0","id":1,"error":{"code":-32603,"message":"upstream server unreachable: <server-name> (timeout after 5000ms)"}}` within 5100ms
   - And: WARN log line emitted with `consecutive_failures` and diagnostic hint

2. Upstream reconnects after transient failure.
   - Given: Upstream was down for 3s and recovers
   - When: Next `tools/list` request arrives after recovery
   - Then: Proxy reconnects and returns a successful result

**Tasks**

- Task 1.4.3.1 — Wrap all upstream calls with a 5-second `tokio::time::timeout`; propagate as -32603 on expiry (files: `src/bin/mcp-proxy/upstream.rs`)
- Task 1.4.3.2 — Add reconnection logic with exponential backoff on transient failures (files: `src/bin/mcp-proxy/upstream.rs`)

---

#### Story 1.4.4: tools/list latency benchmark

Verify Phase 1 adds ≤200ms overhead vs direct server call for tools/list.

**Acceptance criteria**

1. Benchmark test measures proxy overhead: `time(tools/list via proxy) - time(tools/list direct)` for 100 calls. p99 overhead ≤200ms.
   - Given: mcp-proxy running with Atlassian server configured, 11 tools in allowlist
   - When: tools/list called 100 times via proxy
   - Then: p50 overhead < 50ms; p99 overhead < 200ms (measured via tokio::time::Instant)

2. Benchmark results logged at INFO on first call per session: `mcp_filter: overhead_p99_ms=<n> for server=atlassian`

**Tasks**

- Task 1.4.4.1 (~1h) — Write `benches/tools_list_overhead.rs` using criterion crate; baseline = direct HTTP call to upstream mock, proxy = same call via mcp-proxy; add criterion as dev-dep in Cargo.toml (files: `benches/tools_list_overhead.rs`, `Cargo.toml`)

---

### Epic 1.5: Allowlist Filtering and Schema Cache

**Goal**: `tools/list` returns only allowed tools; stale allowlist entries produce WARN at session start.

---

#### Story 1.5.1: Intercept tools/list and apply allowlist

**Acceptance criteria**

1. Only allowed tools are returned in `tools/list`.
   - Given: Upstream returns 38 Slack tools; `allow = ["slack_send_message", "slack_read_channel"]`
   - When: Claude Code calls `tools/list`
   - Then: Response contains exactly 2 tools: `slack_send_message` and `slack_read_channel`

2. Dry-run mode passes all tools through unchanged.
   - Given: `dry_run = true` in `[global]`
   - When: Claude Code calls `tools/list`
   - Then: All 38 tools returned; INFO log shows "dry-run mode — no filtering applied"

**Tasks**

- Task 1.5.1.1 — Implement `filter_catalog(catalog: &RawCatalog, allow: &AllowList, dry_run: bool) -> ProcessedCatalog` (files: `src/mcp_proxy/allowlist.rs`)
- Task 1.5.1.2 — Wire `filter_catalog` into `ToolListPipeline` implementation; `server.rs` delegates `tools/list` to the pipeline (files: `src/mcp_proxy/pipeline.rs`)

---

#### Story 1.5.2: Upstream schema cache with TTL

**Acceptance criteria**

1. A second `tools/list` within TTL does not call upstream.
   - Given: TTL = 300s; upstream `tools/list` called once at t=0
   - When: Another `tools/list` arrives at t=10s
   - Then: Upstream receives only 1 HTTP request total

2. Cache is invalidated after TTL expiry.
   - Given: TTL = 300s; upstream called at t=0
   - When: Next request arrives at t=301s
   - Then: Upstream receives a second HTTP request

**Tasks**

- Task 1.5.2.1 — Implement `SchemaCache` with `Arc<RwLock<Option<(ProcessedCatalog, Instant)>>>` and configurable TTL (files: `src/mcp_proxy/cache.rs`)

---

#### Story 1.5.3: Schema drift detection at session start

**Acceptance criteria**

1. Allowed tool absent from upstream catalog produces a WARN with remediation hint.
   - Given: `allow = ["slack_create_canvas_v1"]`; upstream catalog contains only `slack_create_canvas_v2`
   - When: Proxy starts and fetches upstream catalog
   - Then: WARN log: `allowed_tool_missing_upstream tool=slack_create_canvas_v1 server=slack hint="run mcp-proxy sync"`

**Tasks**

- Task 1.5.3.1 — Add `detect_drift(allow: &AllowList, catalog: &RawCatalog) -> Vec<SchemaDrift>` called at startup; emit WARN per missing tool (files: `src/mcp_proxy/allowlist.rs`)

---

### Epic 1.6: tools/call Forwarding and Error Handling

**Goal**: `tools/call` is forwarded transparently; blocked calls and upstream errors are handled cleanly.

---

#### Story 1.6.1: Transparent tools/call forwarding

**Acceptance criteria**

1. `tools/call` for an allowed tool reaches upstream unchanged.
   - Given: `slack_send_message` is in the allowlist; upstream is running
   - When: `tools/call {"name":"slack_send_message","arguments":{"channel_id":"C123","message":"hi"}}` arrives
   - Then: Upstream receives the identical call; the response is returned to Claude Code verbatim

**Tasks**

- Task 1.6.1.1 — Implement `ToolCallPipeline` in `pipeline.rs`: check allowlist via `allowlist.rs`, forward to `UpstreamClient`, return response (files: `src/mcp_proxy/pipeline.rs`)

---

#### Story 1.6.2: Block tools/call for filtered tools

**Acceptance criteria**

1. Calling a filtered tool returns -32601 with an allowlist hint.
   - Given: `slack_create_canvas` is NOT in the allowlist
   - When: `tools/call {"name":"slack_create_canvas","arguments":{}}` arrives
   - Then: Response is `{"jsonrpc":"2.0","id":N,"error":{"code":-32601,"message":"tool not found: slack_create_canvas (tool exists but is not in allowlist)","data":{"tool":"slack_create_canvas","server":"slack","allowlist_hint":"add to mcp-proxy.toml to enable"}}}`
   - And: WARN log emitted at WARN level (not ERROR)

**Tasks**

- Task 1.6.2.1 — Add `AllowList::check_call` in `allowlist.rs` returning `ToolNotAllowedError` with structured -32601 and `allowlist_hint` data field; `ToolCallPipeline` calls this before forwarding (files: `src/mcp_proxy/allowlist.rs`)

---

#### Story 1.6.3: Translate upstream transport errors to ToolResult errors

**Acceptance criteria**

1. Upstream HTTP 500 is returned as `isError: true` ToolResult (not a protocol error).
   - Given: Upstream returns HTTP 500 for a `tools/call`
   - When: The proxy receives the 500 response
   - Then: Claude Code receives `{"result":{"content":[{"type":"text","text":"Upstream returned 500: Internal Server Error"}],"isError":true}}` — no JSON-RPC error field

**Tasks**

- Task 1.6.3.1 — Wrap upstream `tools/call` response; translate HTTP errors and transport failures to `CallToolResult { is_error: true, content: [...] }` (files: `src/bin/mcp-proxy/upstream.rs`)

---

### Epic 1.7: Session Metrics and Token Counting

**Goal**: Token savings are logged at every session start; tool call frequency is persisted for allowlist analysis.

---

#### Story 1.7.1: Token count before/after filtering

**Acceptance criteria**

1. Session start INFO log shows before/after token counts and percentage saved.
   - Given: Upstream returns a 38-tool Slack catalog (~9,500 tokens); allowlist has 8 tools
   - When: Session starts and `tools/list` filtering completes
   - Then: INFO log: `session_start server=slack filtered=30/38 tokens_before=9500 tokens_after=1800 pct_saved=81%`
   - And: `mcp_filter_tokens_before{server="slack"}` gauge is set to 9500

**Tasks**

- Task 1.7.1.0 (~30 min spike) — Empirically determine tokenizer model: run `tiktoken-rs cl100k_base` and `tiktoken-rs o200k_base` on a captured Atlassian tools/list JSON response. Compare each count to the known baseline of ~13,000 tokens for the 42-tool Atlassian server. The model that matches within 5% is the correct model. Record result in `project_plans/mcp-context-filter/decisions/spike-tokenizer-model.md` and update ADR-008 with the decision. Use that model constant in Tasks 1.7.1.1 and 1.7.1.2. (files: `project_plans/mcp-context-filter/decisions/spike-tokenizer-model.md`, `project_plans/mcp-context-filter/decisions/ADR-008-tokenizer-model.md`)
- Task 1.7.1.1 — Implement `count_tokens_cl100k(schema_json: &str) -> usize` using `tiktoken-rs` `cl100k_base` encoding (files: `src/bin/mcp-proxy/metrics.rs`)
- Task 1.7.1.2 — Call token counter on pre- and post-filter catalogs; emit INFO log and update metrics gauges (files: `src/bin/mcp-proxy/metrics.rs`)

---

#### Story 1.7.2: Tool call frequency logging

**Acceptance criteria**

1. Each tool call is counted; counts are flushed to `~/.claude/mcp-proxy-calls.log` at session end.
   - Given: Session makes 5 calls to `slack_send_message` and 2 to `slack_read_channel`
   - When: Session ends (stdin EOF)
   - Then: `mcp-proxy-calls.log` contains a JSON line `{"date":"2026-07-02","server":"slack","tool":"slack_send_message","calls":5}` and similarly for `slack_read_channel`

**Tasks**

- Task 1.7.2.1 — Use `DashMap<String, AtomicU64>` as per-tool call counter; flush to JSONL on stdin EOF (files: `src/bin/mcp-proxy/metrics.rs`)
- Task 1.7.2.2 — **[Concurrent write safety]** In observe mode (Story 1.8.x), up to 14 simultaneous `mcp-proxy` subprocesses may write to the same `~/.claude/mcp-proxy-calls.log`. Open the log with `OpenOptions::append(true).open(path)` — POSIX guarantees atomicity for writes ≤ `PIPE_BUF` (4096 bytes) on append-only file descriptors; each JSONL line must be serialized in a single `write()` call to stay within this bound. If cross-platform safety beyond POSIX is needed, add `fs2` crate for advisory file locking as a fallback. (files: `src/bin/mcp-proxy/metrics.rs`)

---

### Epic 1.8: CLI Subcommands

**Goal**: `validate`, `init`, `analyze`, and `sync` subcommands support the full operator lifecycle.

---

#### Story 1.8.1: `mcp-proxy validate` subcommand

**Acceptance criteria**

1. `validate` exits 0 when config is valid and all upstreams are reachable.
   - Given: A valid `mcp-proxy.toml` with reachable upstream URLs
   - When: `mcp-proxy validate --config ~/.claude/mcp-proxy.toml`
   - Then: Exit code 0; stdout: "Config valid. All 3 upstream servers reachable."

2. `validate` exits 1 with a human-readable error when a URL is unreachable.
   - Given: `upstream_url = "https://dead.example.com/mcp"`
   - When: `mcp-proxy validate`
   - Then: Exit code 1; stderr: "Error: server 'dead-server' upstream unreachable (5000ms timeout) — check URL or run with RUST_LOG=debug for details"

**Tasks**

- Task 1.8.1.1 — Implement `validate` subcommand using `clap`; call `McpProxyConfig::validate()` and print results (files: `src/bin/mcp-proxy/main.rs`, `src/bin/mcp-proxy/cli.rs`)

---

#### Story 1.8.2: `mcp-proxy init` subcommand

**Acceptance criteria**

1. `init` reads Claude Code `settings.json` and writes an observe-mode `mcp-proxy.toml`.
   - Given: `~/.claude/settings.json` has 3 admin-provisioned MCP servers with known URLs
   - When: `mcp-proxy init --output ~/.claude/mcp-proxy.toml`
   - Then: Output file contains one `[servers.<name>]` block per server; `allow = []` (observe mode, no filtering); inline comments show estimated token counts; stdout prints the summary table

2. `init` prints the total token cost summary.
   - Given: 14 servers totalling ~42,600 tokens
   - When: `mcp-proxy init`
   - Then: Stdout contains "Total: 187 tools, ~42,600 tokens (21% of 200k context window)" and "Running in OBSERVE mode..."

**Tasks**

- Task 1.8.2.1 — Implement `init` subcommand: parse `~/.claude/settings.json` for MCP server URLs; write observe-mode TOML with token-math comments (files: `src/bin/mcp-proxy/cli.rs`)
- Task 1.8.2.2 — Parse Claude Code `settings.json` MCP server blocks (`mcpServers` entries with `url` fields) (files: `src/bin/mcp-proxy/cli.rs`)

---

#### Story 1.8.3: `mcp-proxy analyze` subcommand

**Acceptance criteria**

1. `analyze` reads `mcp-proxy-calls.log` and offers to tighten the allowlist.
   - Given: Log file with 7 days of call counts; 8 tools called ≥1 time, 30 tools never called
   - When: `mcp-proxy analyze --days 7 --min-calls 1`
   - Then: Stdout shows a frequency table; prompts "28 tools never called (estimated 18,400 tokens saved). Apply? [Y/n]"; on Y, rewrites the `allow` list in `mcp-proxy.toml`

**Tasks**

- Task 1.8.3.1 — Implement `analyze` subcommand: parse JSONL call log, compute per-tool call counts, print frequency table, prompt to rewrite config (files: `src/bin/mcp-proxy/cli.rs`)

---

#### Story 1.8.4: `mcp-proxy sync` subcommand

**Acceptance criteria**

1. `sync` prints a diff of current allowlist vs upstream catalog.
   - Given: Allowlist has `slack_create_canvas_v1`; upstream catalog has `slack_create_canvas_v2`
   - When: `mcp-proxy sync --server slack`
   - Then: Stdout: `- slack_create_canvas_v1 (removed from upstream)` and `+ slack_create_canvas_v2 (new in upstream)`

**Tasks**

- Task 1.8.4.1 — Implement `sync` subcommand: connect to upstream, fetch tools/list, diff against config allowlist, print added/removed (files: `src/bin/mcp-proxy/cli.rs`, `src/bin/mcp-proxy/upstream.rs`)

---

#### Story 1.8.5: API key acquisition guide in `--help` output

Context: Admin-provisioned Slack/Atlassian connectors authenticate via Anthropic's OAuth proxy (inaccessible to the local proxy). To proxy these servers, users must obtain direct API tokens. This story ensures those instructions are surfaced at the point of need.

**Acceptance criteria**

1. `mcp-proxy --help` includes per-server API key acquisition instructions.
   - Given: `mcp-proxy --help` or `mcp-proxy init --help` is run
   - When: The help text is displayed
   - Then: Output includes: "To proxy Slack, create a Slack Bot Token at api.slack.com/apps. To proxy Atlassian, create an API token at id.atlassian.com/manage-profile/security/api-tokens."

2. `mcp-proxy init` prints API key acquisition instructions after generating the config.
   - Given: `mcp-proxy init` runs and detects one or more admin-provisioned servers (no direct URL accessible)
   - When: Init completes
   - Then: Stdout prints the acquisition instructions for each server type detected, with the specific API key field name to add in `mcp-proxy.toml`

**Tasks**

- Task 1.8.5.1 — Add API key acquisition instructions as static text in `--help` output via clap `about`/`long_about` on the `init` and top-level commands; add a `print_api_key_guidance(servers: &[ServerConfig])` helper that prints per-server acquisition URLs based on known server types (slack, atlassian) (files: `src/bin/mcp-proxy/cli.rs`)

---

### Epic 1.9: Claude Code Config Helper

**Goal**: One command writes the proxy entries directly into Claude Code config files — no manual JSON editing required.

---

#### Story 1.9.1: `mcp-proxy install` subcommand

**Acceptance criteria**

1. `install` writes proxy entries directly to `~/.claude/settings.json` without any manual editing.
   - Given: `mcp-proxy.toml` has `[servers.slack]` and `[servers.atlassian]` configured
   - When: `mcp-proxy install`
   - Then: `~/.claude/settings.json` is updated in-place with one `mcpServers` entry per proxied server (using the mcp-proxy binary path) and the original server names added to `deniedMcpServers`; stdout prints a summary of changes made

2. `--dry-run` flag prints a diff without writing.
   - Given: `mcp-proxy install --dry-run`
   - When: The subcommand runs
   - Then: stdout prints a unified diff showing what would be added/changed in `~/.claude/settings.json`; the file is not modified; exit code 0

3. `install` prints API key acquisition instructions for servers requiring user-supplied credentials.
   - Given: One or more configured servers use `api_key` authentication (not OAuth pass-through)
   - When: `install` completes
   - Then: stdout includes acquisition instructions for each such server, e.g.: "To proxy Slack, create a Slack Bot Token at api.slack.com/apps. To proxy Atlassian, create an API token at id.atlassian.com/manage-profile/security/api-tokens."

**Tasks**

- Task 1.9.1.1 — Implement `install` subcommand: parse `~/.claude/settings.json`, compute `mcpServers` and `deniedMcpServers` additions, write changes in-place with atomic file replacement (files: `src/bin/mcp-proxy/cli.rs`)
- Task 1.9.1.2 — Implement `--dry-run` flag: compute diff and print without writing (files: `src/bin/mcp-proxy/cli.rs`)
- Task 1.9.1.3 — After writing, print API key acquisition instructions for any server configured with `auth = "api_key"` (files: `src/bin/mcp-proxy/cli.rs`)

---

#### Story 1.9.2: `mcp-proxy uninstall` subcommand

**Acceptance criteria**

1. `uninstall` removes proxy entries from `~/.claude/settings.json` and restores original server entries.
   - Given: `install` was previously run; `~/.claude/settings.json` contains mcp-proxy `mcpServers` entries and `deniedMcpServers` entries for the original servers
   - When: `mcp-proxy uninstall`
   - Then: Proxy-added `mcpServers` entries are removed; original server names are removed from `deniedMcpServers`; stdout prints "Removed N proxy entries; restored M original server entries"

2. `uninstall` is a no-op when proxy is not installed.
   - Given: `~/.claude/settings.json` has no mcp-proxy entries
   - When: `mcp-proxy uninstall`
   - Then: Exit code 0; stdout: "No mcp-proxy entries found in settings.json — nothing to remove"

**Tasks**

- Task 1.9.2.1 — Implement `uninstall` subcommand: parse `~/.claude/settings.json`, identify and remove mcp-proxy `mcpServers` entries (identified by binary path containing `mcp-proxy`), remove associated `deniedMcpServers` entries, write changes in-place (files: `src/bin/mcp-proxy/cli.rs`)

---

## Phase 2: Schema Compression

### Epic 2.0: Pre-implementation Spike

**Goal**: Evaluate mcp-compressor as a library dependency before building inline compression. This spike gates Epic 2.1's implementation approach.

---

#### Story 2.0.1: Spike — Evaluate mcp-compressor Rust library API before building inline compression

**Acceptance criteria**

1. Decision is documented in ADR-008 with evidence before any Epic 2.1 work begins.
   - Given: `crates/mcp-compressor/src/lib.rs` from atlassian-labs/mcp-compressor inspected
   - When: Public API surface verified for stability (not `pub(crate)` internals) and Apache-2.0 license compatibility
   - Then: ADR-008 states either "adopt mcp-compressor as dep" (Epic 2.1 becomes a thin wrapper) or "build inline" (Epic 2.1 proceeds as designed) with rationale

**Tasks**

- Task 2.0.1.1 — Inspect mcp-compressor Rust crate public API (`crates/mcp-compressor/src/lib.rs` exports); check license; write ADR-008 (files: `project_plans/mcp-context-filter/decisions/ADR-008-mcp-compressor-phase2-dep.md`)

> **Blocks**: Epic 2.1 implementation approach. If mcp-compressor has a stable public Rust API, Epic 2.1 becomes a thin wrapper around it rather than an inline implementation — the Stories below remain valid as acceptance tests regardless of approach chosen.

---

### Epic 2.1: Compression Pipeline

**Goal**: `SchemaCompressor` reduces token count of a `RawCatalog` to produce a `ProcessedCatalog` without breaking tool correctness.

> **Note**: Implementation approach (inline vs. mcp-compressor dep) is determined by Story 2.0.1. The acceptance criteria below apply to both approaches.

---

#### Story 2.1.1: Light compression mode

Truncate `description` fields at sentence boundary; preserve all structural fields.

**Acceptance criteria**

1. Light mode truncates tool `description` to first sentence (max 200 chars).
   - Given: Tool with `description = "Search Jira issues using JQL. Supports advanced filters including project, assignee, status, and custom fields. Returns paginated results."` (175 tokens)
   - When: `SchemaCompressor::new(CompressionLevel::Light).compress(catalog)`
   - Then: Result tool has `description = "Search Jira issues using JQL."` (6 tokens)

2. All `required` arrays and `enum` values are preserved unchanged.
   - Given: Tool schema with `"required": ["channel_id", "message"]` and param with `"enum": ["public", "private"]`
   - When: Light compression applied
   - Then: Compressed schema has identical `required` array and `enum` values

**Tasks**

- Task 2.1.1.1 — Implement `SchemaCompressor` struct with `compress(catalog: RawCatalog) -> ProcessedCatalog` method; first-sentence extraction using `. ` / `\n` split (files: `src/bin/mcp-proxy/compress.rs`)
- Task 2.1.1.2 — Unit tests: round-trip preservation of `required`, `enum`, parameter `type` fields (files: `src/bin/mcp-proxy/compress.rs`)

---

#### Story 2.1.2: Aggressive compression mode

Strip `examples` arrays, inline `$ref`, remove redundant `title` fields.

**Acceptance criteria**

1. Aggressive mode produces flat JSON Schema with no `$defs` or `$ref`.
   - Given: Atlassian tool schema with `$defs` section and `$ref: "#/$defs/AdfDocument"` used in 3 properties
   - When: `SchemaCompressor::new(CompressionLevel::Aggressive).compress(catalog)`
   - Then: Output schema has no `$defs` key; all 3 `$ref` pointers are inlined; JSON is self-contained

2. Aggressive mode strips `examples` arrays.
   - Given: Property with `"examples": ["Q2 planning", "sprint review"]`
   - When: Aggressive compression applied
   - Then: Property has no `examples` field

3. Circular `$ref` is handled safely (no infinite loop).
   - Given: Schema with `A -> $ref B -> $ref A` circular reference
   - When: Aggressive compression applied
   - Then: Inlining terminates; one level inlined; second occurrence left as-is or dropped (implementation choice); no panic

**Tasks**

- Task 2.1.2.1 — Implement `$ref` inlining with cycle detection (max 3 levels) in `SchemaCompressor` (files: `src/bin/mcp-proxy/compress.rs`)
- Task 2.1.2.2 — Implement `examples` field stripping and redundant `title` removal (files: `src/bin/mcp-proxy/compress.rs`)
- Task 2.1.2.3 — Unit test: circular schema input does not panic (files: `src/bin/mcp-proxy/compress.rs`)

---

### Epic 2.2: mcp-compressor Crate Evaluation

> **Moved to Story 2.0.1** — This evaluation was resequenced to run as a pre-implementation spike before Epic 2.1, so that if mcp-compressor has a stable public API, Epic 2.1's implementation approach changes before any code is written. See Story 2.0.1 and ADR-008 for the evaluation and decision.

---

### Epic 2.3: Dashboard Integration

**Goal**: MCP filter metrics appear in the existing claude-proxy-rs dashboard.

---

#### Story 2.3.1: Add MCP Filter section to dashboard metrics

**Acceptance criteria**

1. Dashboard `/metrics` endpoint exposes MCP filter gauges.
   - Given: A session completed with slack proxy filtering 30/38 tools
   - When: `curl http://localhost:8080/metrics`
   - Then: Response contains `mcp_filter_tokens_before{server="slack"} 9500` and `mcp_filter_tokens_after{server="slack"} 1800`

**Tasks**

- Task 2.3.1.1 — Expose mcp-proxy metrics via a shared metrics file or IPC to `claude-proxy-rs` dashboard (files: `src/bin/mcp-proxy/metrics.rs`, `src/dashboard.rs`)

---

## Phase 3: Dynamic Tool Discovery

### Epic 3.0: Pre-implementation Spike

**Goal**: Verify the active slot mechanism's core assumption — that Claude Code re-issues `tools/list` after a `search_tools` ToolResult — before designing and building Epic 3.2.

---

#### Story 3.0.1: Spike — Verify whether Claude Code issues a second tools/list RPC after search_tools returns a ToolResult

Epic 3.2 (Active Slot Management) assumes that when `search_tools` returns tool schemas in a ToolResult, Claude Code will issue a follow-up `tools/list` RPC to register them. This assumption must be empirically verified — if Claude Code does not re-issue `tools/list`, the entire dynamic registration path is broken and the inline-schema fallback (Story 3.2.1 AC3) becomes the only viable mechanism.

**Acceptance criteria**

1. Build a minimal MCP stdio server that exposes only `search_tools` and captures the RPC sequence.
   - Given: A minimal Rust stdio MCP server where `search_tools` returns a ToolResult containing one tool schema (e.g. `slack_send_message` definition as JSON)
   - When: The server is registered in `.mcp.json` and a Claude Code session starts; LLM calls `search_tools`
   - Then: Captured stdio transcript is recorded showing every JSON-RPC message in sequence (both directions)

2. Determine whether Claude Code issues a second `tools/list` call after `search_tools` returns.
   - Given: The captured transcript from AC1
   - When: Transcript is inspected for `tools/list` requests after the initial session-start `tools/list`
   - Then: Document outcome: YES (second `tools/list` seen) or NO (no follow-up `tools/list`)

3. Document findings in `project_plans/mcp-context-filter/decisions/spike-phase3-toolslist.md`.
   - If YES (`tools/list` re-issued) → Epic 3.2 slot-registration design is valid; proceed as designed
   - If NO (`tools/list` not re-issued) → Epic 3.2 must rely solely on the inline-schema-in-ToolResult fallback (Story 3.2.1 AC3); document as ADR-006 addendum; update Epic 3.2 stories to remove `notifications/tools/list_changed` as primary path

**Tasks**

- Task 3.0.1.1 (~2h spike) — Build minimal test stdio server (throwaway `src/bin/toolslist-probe/main.rs`); register in test `.mcp.json`; capture RPC sequence in a new Claude Code session; inspect transcript for second `tools/list`; write findings to `project_plans/mcp-context-filter/decisions/spike-phase3-toolslist.md` (files: throwaway binary + spike findings doc)

> **Blocks**: Epic 3.2 (Active Slot Management). Do not begin Story 3.2.1 until spike findings are documented.

---

### Epic 3.1: BM25 Search Index and search_tools Meta-Tool

**Goal**: The `search_tools(query)` meta-tool enables LLM-driven deferred tool discovery from the full upstream catalog.

---

#### Story 3.1.1: Build BM25 index over full RawCatalog

**Acceptance criteria**

1. BM25 index over 200 tools builds in under 100ms.
   - Given: A `RawCatalog` with 200 tools; each with name and description
   - When: `BM25Index::build(catalog).await`
   - Then: Index built; elapsed time < 100ms; `index.len() == 200`

2. Semantic query finds the correct tool in top-3.
   - Given: Index contains `slack_send_message` with description "Sends a message to a Slack channel"
   - When: `index.search("send a message", 5)`
   - Then: `slack_send_message` appears in position 0, 1, or 2 of results

**Tasks**

- Task 3.1.1.1 — Add `bm25 = "0.1"` to Cargo.toml; implement `BM25Index::build(catalog: &RawCatalog) -> Self` indexing `"{name} {description}"` per tool (files: `Cargo.toml`, `src/mcp_proxy/search.rs`)
- Task 3.1.1.2 — Integration test: `search("send message slack")` returns `slack_send_message` in top-3 (files: `src/bin/mcp-proxy/search.rs`)

---

#### Story 3.1.2: Implement search_tools meta-tool

**Acceptance criteria**

1. `search_tools(query, top_k)` returns full tool schemas as JSON in the tool result.
   - Given: Phase 3 enabled; BM25 index built over 200 tools
   - When: LLM calls `search_tools({"query":"send message","top_k":5})`
   - Then: Tool result content contains the 5 matching `ToolDefinition` objects serialized as JSON text

2. Low confidence flag is set when best score is below 0.3.
   - Given: Query with no keyword overlap to any tool ("xyzzy frobulate")
   - When: `search_tools({"query":"xyzzy frobulate"})`
   - Then: Result JSON includes `"low_confidence": true` at the top level

**Tasks**

- Task 3.1.2.1 — Implement `search_tools` as an rmcp `#[tool]` handler; call `BM25Index::search`; serialize matching `ToolDefinition`s as JSON text (files: `src/bin/mcp-proxy/search.rs`)
- Task 3.1.2.2 — Add confidence scoring; include `"low_confidence": true` when max BM25 score < 0.3 (files: `src/bin/mcp-proxy/search.rs`)

---

### Epic 3.2: Active Slot Management

**Goal**: Tools returned by `search_tools` are registered in the active set so Claude Code can call them directly; slots expire after N quiet turns.

---

#### Story 3.2.1: Fixed-K active slot pool

**Acceptance criteria**

1. Tools returned by `search_tools` appear in the next `tools/list` response.
   - Given: `search_tools("send message")` returns `[slack_send_message, slack_send_message_draft]`
   - When: Claude Code calls `tools/list` after the search
   - Then: `tools/list` response includes `slack_send_message` and `slack_send_message_draft` (plus `search_tools` itself)

2. Slot pool respects the `top_k` capacity limit.
   - Given: `phase3.top_k = 10`; search returns 8 tools; pool already has 5 tools
   - When: New search returns 8 more tools
   - Then: Pool total is capped at 10; least-recently-used tools are evicted first

3. Fallback path: when Claude Code does not support `notifications/tools/list_changed`, discovered tools are returned inline in ToolResult text.
   - Given: Claude Code does not issue a second `tools/list` after a `search_tools` call (Issue #13646 — confirmed behavior)
   - When: `search_tools` is called
   - Then: Discovered tool schemas are returned inline in the `ToolResult` content text (as serialized JSON) so the LLM can invoke them via the `call_discovered_tool` meta-tool
   - And: The active slot pool updates without error (slots are maintained for the `tools/list` path if Claude Code ever re-fetches)
   - And: No error is logged or returned due to the missing `list_changed` notification support

**Tasks**

- Task 3.2.1.1 — Implement `ActiveSlotPool` with LRU eviction up to capacity K (files: `src/bin/mcp-proxy/slots.rs`)
- Task 3.2.1.2 — After `search_tools` call, update `ActiveSlotPool`; `ToolListPipeline` reads the pool to include updated tools in the next `tools/list` response (files: `src/mcp_proxy/slots.rs`, `src/mcp_proxy/pipeline.rs`)

---

#### Story 3.2.2: Tool expiry after N quiet turns

**Acceptance criteria**

1. A tool not called for `tool_expiry_turns` turns is removed from the active set.
   - Given: `tool_expiry_turns = 5`; `slack_send_message` in active set; 5 consecutive turns with no call to it
   - When: Turn 6 arrives
   - Then: `slack_send_message` is evicted from active set; `tools/list` no longer includes it

2. Expired tool call returns ToolError with re-search hint.
   - Given: `slack_send_message` was evicted after quiet-turn expiry
   - When: LLM calls `tools/call {"name":"slack_send_message"}`
   - Then: Returns `ToolError`: "Tool slack_send_message has expired from the active set. Call search_tools to re-register it."

**Tasks**

- Task 3.2.2.1 — Add quiet-turn counter per slot; increment on each `tools/call` for any other tool; evict slot when counter >= `tool_expiry_turns` (files: `src/bin/mcp-proxy/slots.rs`)
- Task 3.2.2.2 — Return descriptive ToolError for expired-slot `tools/call`; `ActiveSlotPool::check_call` handles detection and error construction; `ToolCallPipeline` delegates to it (files: `src/mcp_proxy/slots.rs`)

---

#### Story 3.2.3: Conditional notifications/tools/list_changed

**Acceptance criteria**

1. Proxy attempts to send `notifications/tools/list_changed` after slot update.
   - Given: Phase 3 enabled; `ActiveSlotPool` updated with 3 new tools
   - When: Proxy attempts to send `notifications/tools/list_changed`
   - Then: Notification is sent without blocking; if Claude Code ignores it, no error occurs

**Tasks**

- Task 3.2.3.1 — Send `notifications/tools/list_changed` after `ActiveSlotPool` mutation; suppress send errors (Claude Code may ignore the notification) (files: `src/mcp_proxy/server.rs`)

---

### Epic 3.3: fastembed-rs Semantic Search (Default-on; opt-out via `--no-default-features`)

**Goal**: Hybrid BM25 + dense embedding search enabled by default. The `semantic-search` Cargo feature is listed in `[features] default`, so a plain `cargo build --bin mcp-proxy` includes fastembed and the ONNX runtime. Users who need minimal dependencies (CI environments, resource-constrained deployments, faster builds) can opt out by building with `cargo build --bin mcp-proxy --no-default-features`, which produces a BM25-only binary. The BM25-only path emits a startup WARN and a WARN on any `search_tools` call that returns 0 results, making the recall limitation visible rather than silent.

---

#### Story 3.3.1: fastembed hybrid search enabled by default (opt-out via `--no-default-features`)

**Acceptance criteria**

1. `cargo build --bin mcp-proxy` (no extra flags) compiles with fastembed enabled by default.
   - Given: `fastembed` is an optional dep in Cargo.toml included in `[features] default = ["semantic-search"]`
   - When: `cargo build --bin mcp-proxy` with no feature flags
   - Then: Build succeeds; binary size increases by approximately 5MB vs BM25-only (ONNX runtime linked); no startup WARN about disabled semantic search

2. BM25-only opt-out build compiles and emits startup WARN.
   - Given: User builds with `--no-default-features` to exclude the `semantic-search` feature
   - When: `cargo build --bin mcp-proxy --no-default-features` then proxy is started
   - Then: Build succeeds without ONNX runtime; on startup proxy logs `WARN mcp_proxy: semantic search disabled (built without semantic-search feature); BM25-only search has ~34% recall on semantic queries`
   - And: Any `search_tools` call returning 0 results logs `WARN mcp_proxy: search_tools returned 0 results in BM25-only mode; semantic queries like "notify the team" may require semantic-search enabled build`

3. Hybrid search improves recall for semantic queries.
   - Given: Default build (semantic-search feature enabled); BGE-small-en-v1.5 model loaded
   - When: `search_tools({"query":"notify the team"})`
   - Then: `slack_send_message` appears in top-3 (would be missed by BM25 alone)

**Tasks**

- Task 3.3.1.1 — Add `fastembed = { version = "4", optional = true }` to Cargo.toml with `[features] default = ["semantic-search"]` and `semantic-search = ["dep:fastembed"]`; gate embedding code with `#[cfg(feature = "semantic-search")]` (files: `Cargo.toml`, `src/bin/mcp-proxy/search.rs`)
- Task 3.3.1.2 — Implement hybrid scoring: `score = 0.7 * bm25_score + 0.3 * cosine_similarity` when embedding enabled (files: `src/bin/mcp-proxy/search.rs`)
- Task 3.3.1.3 — Add WARN log on BM25-only startup and on zero-result `search_tools` calls when `#[cfg(not(feature = "semantic-search"))]`; include recall caveat text in the `search_tools` ToolResult when running BM25-only and results are empty (files: `src/bin/mcp-proxy/search.rs`)

---

#### Story 3.3.2: Graceful fallback when embedding model unavailable

**Acceptance criteria**

1. Proxy starts with BM25-only when embedding model path is wrong or file missing.
   - Given: `phase3.embedding_model = "/nonexistent/model.onnx"`
   - When: Proxy starts with `--features semantic-search`
   - Then: WARN log: "embedding model unavailable at /nonexistent/model.onnx — using BM25 fallback"; proxy starts successfully

**Tasks**

- Task 3.3.2.1 — Wrap ONNX model load in `match`; on error, log WARN and continue with `SearchBackend::Bm25Only` (files: `src/bin/mcp-proxy/search.rs`)
