# ADR-007: Request Body Manipulation — serde_json::Value

**Status**: Accepted
**Date**: 2026-06-17

## Context

FR-1.6 requires stripping specific fields from request bodies before forwarding (tool fields, message content blocks, top-level Bedrock-only fields). The proxy must not silently drop unknown fields that are valid for the target provider. The proxy also cannot stream-mutate JSON — it must buffer the full body, parse, mutate, and re-serialize before forwarding.

Two approaches exist: typed structs (deserialize into known shapes) or dynamic `serde_json::Value` (preserve everything, remove selectively).

## Decision

Use **`serde_json::Value`** for all request body manipulation.

Parse with `serde_json::from_slice` (zero-copy from `Bytes`, avoids extra UTF-8 allocation vs `from_str`). Mutate via `as_object_mut().remove(key)` and `content.retain(|block| ...)`. Re-serialize with `serde_json::to_vec`.

## Alternatives Considered

| Option | Rejected because |
|--------|-----------------|
| Typed structs with `#[serde(flatten)] extra: HashMap<String, Value>` | `#[serde(flatten)]` is incompatible with `#[serde(deny_unknown_fields)]`; combining `flatten` with untagged enums is a known bug (serde issue #1600) causing silent field drops on nested structures — unacceptable for a proxy whose correctness depends on forwarding all valid fields |
| Fully typed structs without flatten | Drops any field not explicitly defined in the struct — the proxy would silently lose new API fields added by Anthropic or Claude Code, causing mysterious provider errors |
| `simd-json` | Mutates the input buffer in-place during string unescaping; requires `Vec<u8>` not `&[u8]`; awkward in proxy code where the original body may need to be logged or retried after mutation |
| `sonic-rs` | ~7x faster than serde_json for large payloads; valid upgrade path if profiling flags JSON as a bottleneck; not justified upfront since request bodies are 2–20KB and network latency (100–5000ms) dominates completely |

## Consequences

- Axum's `Json`, `Bytes`, and `String` extractors hard-limit bodies to **2MB by default** — must apply `DefaultBodyLimit::max(50 * 1024 * 1024)` per route on `/v1/messages`, `/chat/completions`, `/v1/chat/completions` (tool results with base64 images can exceed 2MB)
- `Content-Length` must be dropped from forwarded headers after body mutation — axum/hyper do not rewrite it automatically; sending the original value causes the upstream to reject with a length mismatch; strip `Content-Length` and `Transfer-Encoding` from the outgoing reqwest request headers and let reqwest compute the correct value from the new body bytes
- Peak memory under load: 10MB body × 50 concurrent streams = ~1.5GB from body buffering; `from_slice` avoids one extra allocation per request vs `from_str`
- `sonic-rs` with `LazyValue` for zero-copy field inspection is a documented upgrade path if JSON processing ever appears in profiling results
