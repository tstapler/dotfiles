# ADR-001: stdio subprocess per server as proxy frontend transport

**Date**: 2026-07-02
**Status**: Accepted
**Deciders**: Tyler Stapler
**Context**: mcp-context-filter Phase 1 architecture

---

## Context and Problem Statement

The MCP proxy needs a frontend transport — the mechanism by which Claude Code communicates with the proxy. Three candidate architectures were evaluated:

**A — stdio subprocess per server**: Claude Code spawns the `mcp-proxy` binary as a child process (one invocation per configured server). All MCP communication happens over stdin/stdout using JSON-RPC 2.0.

**B — HTTP sidecar (single long-running server)**: A single `mcp-proxy` process starts as a background service, listens on a loopback TCP port, and Claude Code connects to it via Streamable HTTP. One process manages all servers.

**C — Embedded Tokio task in claude-proxy-rs main binary**: MCP proxy logic runs as an async task inside the existing Axum HTTP server binary, bridging stdio from a Claude Code subprocess to upstream.

---

## Decision Drivers

- Claude Code's preferred MCP transport is stdio (spec: "Clients SHOULD support stdio whenever possible")
- No port management or background service management desired
- Must work with how Claude Code configures MCP servers (`.mcp.json` command + args format)
- Admin-provisioned cloud connectors cannot be modified; proxy must wrap them locally
- Existing `claude-proxy-rs` binary is an HTTP server — mixing it with stdio changes startup semantics

---

## Decision

**Chosen: Option A — stdio subprocess per server.**

One `mcp-proxy` binary invocation per proxied server. Claude Code spawns it via `.mcp.json`:

```json
{
  "mcp-proxy-slack": {
    "command": "/path/to/mcp-proxy",
    "args": ["--server", "slack", "--config", "~/.claude/mcp-proxy.toml"]
  }
}
```

The binary is a new `[[bin]]` target in the existing `claude-proxy-rs` Cargo.toml, sharing workspace deps but producing a separate binary.

---

## Consequences

**Positive**:
- Claude Code manages the subprocess lifecycle (starts on session open, kills on session close)
- Zero port conflicts; no background service to manage
- Auth credentials can be passed as env vars in `.mcp.json` `env` block
- Clean operational model: one process per server, one concern per process
- Consistent with the pattern used by `stephenlacy/mcp-proxy` and `tidewave-ai/mcp_proxy_rust`

**Negative**:
- N processes for N configured servers (acceptable for single-user, 10–20 servers)
- Session startup multiplies the N × upstream connection latency serially (Claude Code starts proxies in parallel, so practical impact is the slowest upstream)

**Rejected — Option B (HTTP sidecar)**:
- Requires port management and a system service (launchd plist)
- Startup ordering: Claude Code might connect before the sidecar is ready
- More complex rollback (must stop the sidecar, not just edit `.mcp.json`)

**Rejected — Option C (embedded Tokio task)**:
- stdio and Axum HTTP server are fundamentally different execution models; mixing them complicates the binary's stdin ownership
- `claude-proxy-rs` runs as a persistent HTTP server; stdio MCP is request-driven — the lifecycles are different
