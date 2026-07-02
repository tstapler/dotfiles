# ADR-002: rmcp v0.16 as the MCP protocol layer

**Date**: 2026-07-02
**Status**: Accepted
**Deciders**: Tyler Stapler
**Context**: mcp-context-filter — MCP JSON-RPC transport selection

---

## Context and Problem Statement

The proxy needs to:
1. Act as an MCP **server** to Claude Code (via stdio)
2. Act as an MCP **client** to upstream cloud connectors (via HTTP)

Both roles must be implemented in Rust and integrate with the existing `tokio` + `reqwest` stack.

Options evaluated:

| Crate | Maintainer | MCP spec | Notes |
|-------|-----------|---------|-------|
| `rmcp` v0.16 | modelcontextprotocol (Anthropic) | 2025-06-18 | Official SDK; both server + client roles |
| `rust-mcp-sdk` | community | 2025-03-26 | Not official; older spec |
| Roll own JSON-RPC over stdio | — | any | High maintenance; framing edge cases |

---

## Decision

**Chosen: `rmcp` v0.16 from the `modelcontextprotocol` GitHub org (official Anthropic Rust SDK).**

Cargo.toml addition:
```toml
rmcp = { version = "0.16", features = [
    "server",
    "client",
    "transport-io",
    "transport-sse",
    "transport-streamable-http-client",
] }
```

---

## Decision Drivers

- Official SDK from the same org that maintains the MCP spec — highest confidence in spec compliance
- Implements spec 2025-06-18 (latest); `notifications/tools/list_changed` supported
- Ships both server and client roles — no need to mix crates
- `transport-io` = stdio server for Claude Code; `transport-streamable-http-client` = Streamable HTTP upstream client
- `#[tool]` and `#[tool_box]` macros simplify the `search_tools` meta-tool in Phase 3
- Apache-2.0 license — compatible with dotfiles repo
- Tokio 1.x runtime — matches existing `claude-proxy-rs` dependency

---

## Risks and Mitigations

**Risk**: `rmcp` v0.16 may pull in axum 0.7 instead of 0.8 (existing dependency).
**Mitigation**: Run `cargo tree -p rmcp | grep axum` before merging. If version conflict exists, either pin or use `[patch]` in workspace Cargo.toml.

**Risk**: `rmcp` API may change between 0.16.x patch versions.
**Mitigation**: Pin to `rmcp = "0.16.0"` (exact version) until the proxy is stable.

---

## Consequences

**Positive**:
- All JSON-RPC 2.0 framing over stdio is handled by rmcp — no custom line-buffering code
- SSE and Streamable HTTP transports implemented and tested upstream
- Axum-compatible via `StreamableHttpService` if an HTTP-facing mode is ever needed

**Negative**:
- Additional compile-time dependency; compile time increases (~30s on first build)
- Minor: the `rmcp` crate namespace differs between `4t145/rmcp` (older, more crates.io downloads) and the official `modelcontextprotocol/rust-sdk` — must add via git or wait for official crates.io publish under the new org slug
