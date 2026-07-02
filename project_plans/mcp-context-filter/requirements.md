# Requirements: mcp-context-filter

**Date**: 2026-07-02
**Type**: feature addition
**Complexity**: 3 — system design with external MCP protocol integration

## Problem Statement

Admin-provisioned MCP cloud connectors (Atlassian Rovo ~13k tokens, Slack ~9.5k, plus 12 others) consume 42.6k tokens (21% of the context window) in tool schema metadata at every session start — before any work happens. Claude Code has no built-in mechanism to filter individual tools within a server or compress schema definitions. This wastes context budget on tools that will never be called, degrading effective reasoning depth for every session.

## Baseline

Today:
- 42.6k tokens consumed by MCP tool schemas at session start (21% of 200k window)
- 12 servers denied wholesale (blunt instrument — cannot keep useful servers while filtering their large schemas)
- Gmail and Google Calendar kept off but not deniable without losing future auth ability
- Zero ability to expose only the 5–10 tools actually used from a 40-tool server (e.g., Slack)

## Users / Consumers

- Tyler Stapler (primary) — Claude Code CLI sessions on macOS
- Potentially other dotfiles repo users who adopt the tool

## Success Metrics

- Reduce MCP schema token footprint from ~42.6k to ≤10k tokens at session start (>75% reduction)
- Phase 1 (allowlist): ≥50% reduction with zero breaking of currently-used tools
- Phase 2 (compression): additional ≥20% reduction on top of Phase 1
- Phase 3 (dynamic discovery): approach 95% reduction for large server catalogs
- Zero regressions: all tools used in the past 30 days still accessible

## Appetite

Large (3–6 weeks)
*(Scope must fit the appetite. If it doesn't fit, cut scope — do not move the deadline.)*

## Constraints

- Must live within or alongside claude-proxy-rs (Rust/Axum codebase in `stapler-scripts/claude-proxy-rs/`)
- Must work with Claude Code's MCP transport model (stdio for local servers; HTTP/SSE for cloud connectors)
- Admin-provisioned cloud connectors cannot be modified; proxy must wrap them locally
- No external SaaS dependencies beyond what claude-proxy-rs already uses
- Must not require any changes to Claude Code itself

## Non-functional Requirements

- **Performance SLO**: Tools/list response latency ≤200ms overhead vs. direct server call (Phase 1), ≤500ms (Phase 3 with embedding lookup)
- **Scalability**: Single-user local proxy; 10–20 MCP servers, up to 200 tools total
- **Security classification**: Internal — handles OAuth tokens for cloud connectors; tokens must not be logged
- **Data residency**: All data local (macOS); embedding model can be local (e.g., ONNX) to avoid sending tool descriptions to external APIs

## Scope

### In Scope

**Phase 1 — Tool Allowlist Proxy**
- An MCP stdio server in claude-proxy-rs that wraps an upstream MCP server (HTTP/SSE or stdio)
- Config-driven per-server allowlist: `mcp-proxy.toml` specifying which tools to expose per server
- Intercepts `tools/list` → filters to allowed tools → returns compressed schema list
- Forwards `tools/call` to upstream transparently
- Auto-generates starter allowlist config from a dry-run session scan (which tools were actually called in the last N sessions)
- Claude Code config helper: generates `deniedMcpServers` entries for originals and adds local proxy entries

**Phase 2 — Schema Compression**
- Strip verbose descriptions from tool schemas (keep name + one-line summary)
- JSON `$ref` deduplication for repeated schema patterns
- Compression level config: off / light / aggressive
- Baseline token counting before/after compression (logged to metrics)

**Phase 3 — Dynamic Tool Discovery**
- Single `search_tools(query)` meta-tool per proxied server
- BM25 or lightweight embedding-based search over the full tool catalog
- On search call: return top-K matching tool schemas, register them for the session
- Tools expire from active set when not called within N turns

### Out of Scope

- Modifying upstream MCP server implementations
- Building a general-purpose MCP gateway for teams / multi-user scenarios
- Web UI / dashboard for tool management (metrics only via existing claude-proxy-rs dashboard)
- Changing Claude Code source code or patching its binaries
- Windows or Linux support (macOS only for Phase 1-2; Linux considered in Phase 3)
- Server-side tool schema caching across users

## Rabbit Holes

- **OAuth token forwarding**: Cloud connectors (Slack, Atlassian) require the user's OAuth token. The proxy must pass-through auth without storing it. Need to understand how Claude Code injects auth into cloud connector requests and replicate that in the proxy. This could be complex if tokens are managed by the claude.ai session layer.
- **SSE transport proxying**: HTTP/SSE MCP servers use server-sent events for streaming. Proxying SSE in Rust requires careful handling of backpressure and connection lifetimes — the existing `compression/` module may need extension.
- **Allowlist bootstrapping**: Auto-generating an allowlist from session history requires parsing Claude Code's conversation logs or MCP call history, which may not be straightforwardly accessible.
- **Dynamic tool re-registration**: Phase 3 requires tools to appear/disappear from the active tool list within a session. MCP protocol may not support dynamic tool list changes after `initialize` without a server restart — needs protocol research.

## Alternatives Considered

- **atlassian-labs/mcp-compressor**: External project, Rust SDK available, would require running a separate binary. Good prior art but doesn't integrate with existing claude-proxy-rs setup or provide allowlist config management.
- **pro-vi/mcp-filter**: npm/Node.js, doesn't integrate with Rust toolchain. Good reference for allowlist design patterns.
- **Dumbris/mcpproxy**: Python + Faiss + heavy ML deps — overkill for Phase 1. Architecture reference for Phase 3.
- **Deny entire servers**: Already done for 12 servers. Insufficient — can't keep Slack/Atlassian accessible while reducing their footprint.

## Feasibility Risks

1. **MCP SSE proxy complexity**: Proxying HTTP/SSE MCP servers requires the proxy to act as a local HTTP server AND make outbound SSE connections with auth forwarding. This is the highest-risk piece — needs a prototype in Phase 1.
2. **Tool dynamic re-registration**: MCP spec may not allow tools to be added to a running session. If so, Phase 3 dynamic discovery would need a workaround (e.g., always registering the search_tools meta-tool plus a fixed max-K tool slots).
3. **Cloud connector auth token access**: Admin-provisioned connectors manage auth via the claude.ai session layer. The local proxy may not have access to those tokens. Fallback: user manually configures API keys in `mcp-proxy.toml`.

## Observability Requirements

- Token counts before/after proxy for each server (logged to existing claude-proxy-rs metrics)
- Tool call frequency per tool (to inform allowlist pruning)
- Proxy overhead latency histogram (p50/p99)
- Alert condition: if upstream server unreachable for >5 seconds, fail fast with clear error

## Risk Control

- Feature flag: `enabled = true/false` in the `[global]` section of `mcp-proxy.toml` to bypass entirely (default: true)
- Rollback procedure: set flag to false or remove local proxy entries from Claude Code config; original servers restored in next session
- Staged rollout: Phase 1 (allowlist) deployed and validated for ≥1 week before starting Phase 2
- No database migrations or shared state — all config is local TOML files

## Open Questions

1. How does Claude Code pass OAuth tokens to admin-provisioned cloud connectors? Is there a hook or is it managed entirely by the claude.ai layer?
2. Does the MCP protocol support dynamic tool list updates within an active session (`notifications/tools/list_changed`)?
3. Does claude-proxy-rs currently have any MCP-awareness, or is it purely an HTTP messages proxy?
4. What is the best local embedding model (ONNX-compatible) for Phase 3 that balances quality vs. inference latency on macOS?
