# ADR-007: Stdio upstream transport excluded from Phase 1 scope

**Date**: 2026-07-02
**Status**: Accepted
**Deciders**: Tyler Stapler

---

## Context

`requirements.md` In Scope states the proxy wraps "HTTP/SSE or stdio" upstream MCP servers. The Phase 1 implementation plan covers Streamable HTTP (primary) and SSE (fallback) upstream transports but contains no story for connecting to stdio-based upstream servers.

The core token-reduction problem motivating this project is admin-provisioned cloud connectors (Atlassian Rovo ~13k tokens, Slack ~9.5k, plus others) — all of which expose HTTP/SSE or Streamable HTTP endpoints. Local stdio-based servers are:

1. Already small in practice (locally authored tools rarely register 50+ tools).
2. Not the source of the 42.6k-token baseline documented in requirements.md.
3. Significantly more complex to proxy correctly: a stdio upstream requires the proxy to spawn a subprocess, manage its lifecycle, bridge two stdio channels (Claude Code → proxy → upstream subprocess), and handle process exit/restart — all with no timeout on process startup, no URL-level liveness check, and no reconnect semantics.

Phase 1 appetite is 3–6 weeks. Adding stdio upstream support would introduce subprocess lifecycle management, PTY handling (or raw pipe mode), and process-restart logic, adding at minimum 1–2 weeks of scope with zero contribution to the primary success metric.

---

## Decision

**Stdio upstream transport is explicitly out of Phase 1 scope.**

Phase 1 supports only Streamable HTTP (primary) and SSE (legacy fallback, non-Atlassian) upstream transports. The `UpstreamTransport::Stdio` enum variant in the Domain Glossary remains as a forward-declared type but is not implemented until a future phase.

The requirements.md In Scope section will be understood as aspirational for the full multi-phase feature; Phase 1 scope is authoritative for Phase 1 delivery.

---

## Rationale

- **Zero token impact**: all servers responsible for the 42.6k-token baseline use HTTP-based transports. Stdio upstream support does not advance the primary success metric.
- **Scope protection**: subprocess lifecycle management is a distinct implementation surface, not incrementally deliverable alongside HTTP transport.
- **Reversible**: the `UpstreamTransport` enum already includes `Stdio` as a variant. A future story adding `upstream_command = [...]` support in `mcp-proxy.toml` and a corresponding `UpstreamClient` implementation in `src/mcp_proxy/upstream.rs` can be added without architectural changes.

---

## Consequences

- `mcp-proxy.toml` `[servers.<name>]` blocks must specify `upstream_url` (not `upstream_command`) in Phase 1. Config validation (`Story 1.2.2` AC 1) returns an error if `upstream_command` is provided without a future stdio-support story implemented.
- requirements.md In Scope text remains unchanged but is qualified by this ADR: HTTP/SSE upstream is Phase 1; stdio upstream is a future phase item.
- If a user attempts to configure a stdio upstream in Phase 1, `mcp-proxy validate` should print: "stdio upstream transport is not yet supported (ADR-007). Use upstream_url for HTTP/Streamable HTTP servers."
