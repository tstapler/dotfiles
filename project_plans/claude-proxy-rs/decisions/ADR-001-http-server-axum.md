# ADR-001: HTTP Server — axum 0.8.9

**Status**: Accepted
**Date**: 2026-06-17

## Context

The proxy needs an HTTP server that handles SSE streaming for Anthropic and Bedrock responses, applies middleware (tracing, timeouts, compression), and integrates cleanly with the async ecosystem. The choice affects every layer of the application.

## Decision

Use **axum 0.8.9** as the HTTP server framework.

## Alternatives Considered

| Option | Rejected because |
|--------|-----------------|
| actix-web 4.13.0 | No built-in SSE type (requires `actix-web-lab`); uses its own `Transform` trait that is incompatible with Tower middleware — a hard constraint for this project's timeout/tracing/auth stack |
| raw hyper 1.10.1 | Application-level complexity with no benefit: full SSE byte formatting written by hand, no router, no middleware — appropriate for building frameworks, not proxy applications |

## Consequences

- SSE forwarding uses `axum::response::sse::Sse<S>` with `reqwest`'s `.bytes_stream()` as the stream source — zero glue adapter code required
- Tower middleware (`tower-http` `TraceLayer`, `TimeoutLayer`, `CompressionLayer`) attaches via `.layer()` with no custom integration; `CompressionLayer` explicitly skips `text/event-stream` via `NotForContentType::SSE` so SSE streams are safe
- `TimeoutLayer` times out handler startup (headers), not body streaming — long-lived SSE connections are not killed
- `ResponseBodyDeadlineLayer` must never be applied globally; it wraps the body stream and would kill SSE connections
- Nginx/load balancer buffering requires `X-Accel-Buffering: no` on SSE responses — axum does not set this automatically
