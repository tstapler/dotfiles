# ADR-003: Streamable HTTP as primary upstream transport, SSE as legacy fallback

**Date**: 2026-07-02
**Status**: Accepted
**Deciders**: Tyler Stapler
**Context**: mcp-context-filter — upstream (proxy → cloud connector) transport

---

## Context and Problem Statement

The proxy makes outbound connections to upstream cloud MCP connectors (Atlassian Rovo, Slack, etc.). These connectors have historically used HTTP/SSE (server-sent events). Two transport options exist for new clients:

| Transport | MCP spec | Status |
|-----------|---------|--------|
| HTTP + SSE | 2024-11-05 | **Deprecated** — Atlassian EOL June 30, 2026 |
| Streamable HTTP | 2025-03-26 | Current standard |

---

## Decision

**Chosen: Streamable HTTP as primary transport with SSE as legacy fallback.**

Connection sequence:
1. Attempt Streamable HTTP (`POST /mcp` with `Accept: application/json, text/event-stream`)
2. If upstream returns HTTP 404 or 405, fall back to SSE transport (`GET /sse`)
3. Log which transport was negotiated at DEBUG level

---

## Decision Drivers

- **Atlassian SSE end-of-life**: Atlassian Rovo's HTTP+SSE transport has a confirmed end-of-life of June 30, 2026. The proxy must support Streamable HTTP to work with Rovo on or after this date.
- **Streamable HTTP is the MCP 2025-03-26 standard**: New MCP servers will implement Streamable HTTP, not SSE. Starting with Streamable HTTP means the proxy stays relevant as the ecosystem evolves.
- **SSE pitfalls documented**: SSE requires a persistent connection held open indefinitely; no reconnect semantics are defined in the protocol; backpressure is undefined; DNS/VPN changes break it irrecoverably. Streamable HTTP uses per-request POST, which handles connection interruptions gracefully.
- **`rmcp` provides both transports**: The `transport-streamable-http-client` and `transport-sse` features are both available; no additional implementation cost.

---

## Implementation Note

The `MCP-Protocol-Version` header must be forwarded on every post-initialize request per the Streamable HTTP spec. Omitting it causes upstream servers to return `400 Bad Request`.

Backpressure on the SSE fallback path: use `tokio::sync::mpsc` with bounded channel capacity = 64 between the upstream SSE reader task and the downstream stdio writer. This prevents unbounded buffering if upstream sends faster than downstream consumes.

---

## Consequences

**Positive**:
- Proxy works with Atlassian Rovo post–June 30, 2026 (SSE EOL)
- Streamable HTTP: per-request connections; no long-lived connection management
- Automatic compatibility with new MCP servers

**Negative**:
- Two transport implementations to maintain (Streamable HTTP + SSE)
- Transport negotiation adds one extra HTTP round-trip on first connection to legacy SSE servers
- SSE backpressure requires explicit bounded channel management
