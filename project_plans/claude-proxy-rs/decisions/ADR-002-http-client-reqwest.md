# ADR-002: HTTP Client — reqwest 0.13 with read_timeout; Separate Streaming Client

**Status**: Accepted
**Date**: 2026-06-17

## Context

The proxy must make upstream HTTP requests to both Anthropic and AWS Bedrock, including long-lived SSE streaming connections. The client must handle connection pooling, TLS, and timeouts correctly for 50+ concurrent streaming requests (NFR-1.4). A naive configuration will either kill long-lived SSE streams or exhaust the connection pool.

## Decision

Use **reqwest 0.13** as the upstream HTTP client with these specific configurations:

1. **Timeout**: Set `connect_timeout` + `read_timeout`. Never set `.timeout()` on the streaming client.
2. **Streaming client**: Create a dedicated `reqwest::Client` with `pool_max_idle_per_host(0)` for SSE connections.
3. **SSE parsing**: Use `eventsource-stream 0.2.x` to parse upstream SSE frames (not `reqwest-eventsource`).

## Alternatives Considered

| Option | Rejected because |
|--------|-----------------|
| `reqwest` with `.timeout()` for SSE | `.timeout()` is a hard wall-clock deadline from connect through full body drain — it kills long-lived SSE streams after N seconds regardless of activity |
| `reqwest-eventsource 0.6.0` | Wraps reqwest + eventsource-stream into a typed `EventSource` consumer with reconnect logic — correct for *consuming* SSE from a backend, wrong for a *forwarding* proxy that re-emits frames verbatim |
| `ureq` | Blocking API; incompatible with tokio async runtime |
| raw hyper 1.10.1 direct | No connection pooling, no TLS, no retry — significant plumbing for no measurable gain (reqwest is built on hyper 1.x internally) |
| Single shared `reqwest::Client` for all requests | Long-lived SSE connections hold pool slots permanently, starving short requests under 50+ concurrent streams |

## Consequences

- `connect_timeout` applies to TCP + TLS handshake only; `read_timeout` resets on each received chunk — correct behavior for streaming
- A separate pooled client for short requests (health checks, non-streaming calls) preserves connection reuse where appropriate
- `pool_max_idle_per_host(0)` on the streaming client ensures each SSE stream uses its own connection and closes it when done
- `eventsource-stream`'s `.eventsource()` extension trait handles `data: ...\n\n` framing, multi-line data, event type, and id fields per spec; the resulting `Stream<Item>` feeds directly into `axum::response::sse::Sse<S>`
- reqwest 0.13 built-in retry (`.retry(policy)`) applies only to initial connection attempts — never configure retry for mid-stream SSE connections
