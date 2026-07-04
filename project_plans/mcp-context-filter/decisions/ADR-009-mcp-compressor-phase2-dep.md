# ADR-009: mcp-compressor Evaluation — Build Inline vs. Adopt Dependency

**Status**: Decided — Build inline  
**Date**: 2026-07-04  
**Spike**: Story 2.0.1 — evaluated mcp-compressor-core 0.31.3 (latest on crates.io)

---

## Context

Phase 2 adds schema compression to reduce token count of `tools/list` responses. Before
implementing `SchemaCompressor`, Story 2.0.1 requires evaluating whether the
`mcp-compressor-core` crate (from atlassian-labs/mcp-compressor, Apache-2.0) has a
stable public Rust API we can wrap instead of building inline.

---

## Evidence

### Public API surface

`mcp-compressor-core 0.31.3` exports:

| Item | Stability |
|------|-----------|
| `compression::CompressionEngine` | `pub` — stable, heavily tested |
| `compression::CompressionLevel` | `pub` enum: Low/Medium/High/Max |
| `server::CompressedServer` | `pub` — full server implementation |
| `server::ToolCache` | `pub` |
| `server::connect` | `pub(crate)` — internal |
| `server::dynamic_http_client` | `pub(crate)` — internal |

License: **Apache-2.0** — compatible with this project.

### Interface mismatch (blocking)

`CompressionEngine` formats tools as **XML-like strings**:

```
<tool>name(arg1, arg2): First sentence of description</tool>
```

This is a *text representation* for inserting tool context into an LLM system prompt. It
does **not** transform `rmcp::model::Tool` JSON Schema objects. Our use case requires:

```
rmcp::model::Tool { name, description, input_schema } 
    → rmcp::model::Tool { name, description_truncated, input_schema_inlined }
```

…so that the compressed tool can be returned from `tools/list` and remain directly
invocable via `tools/call` without any extra round-trip.

### 2-meta-tool model is incompatible

`CompressedServer` implements the "2-extra-meta-tool" model: it exposes `list_tools` and
`get_schema` as MCP tools. Claude Code must call `list_tools` to discover names, then
`get_schema` to retrieve the full schema before calling a tool. This matches
mcp-compressor's design intent but:

1. Adds 1–2 extra LLM round-trips per tool call
2. Requires the LLM to know about the meta-tool protocol
3. Breaks direct tool invocation — already rejected in plan.md Pattern Decisions as
   "requires LLM extra round-trip; changes interaction model"

### Our approach requires

- Compress `description` fields at the sentence boundary (JSON field, not text)
- Inline `$ref` pointers in `input_schema` (JSON Schema transformation)
- Return standard `rmcp::model::Tool` objects from `tools/list`
- No protocol change visible to Claude Code

None of these are provided by `CompressionEngine` or `CompressedServer`.

---

## Decision

**Build inline.** `mcp-compressor-core` solves a different problem (in-prompt text
compression via meta-tools) than we need (in-protocol JSON Schema compression on
`tools/list` responses). Adopting it would require wrapping around the wrong abstraction
and still implementing all the JSON manipulation ourselves.

Epic 2.1 proceeds as designed in plan.md: `SchemaCompressor` in
`src/bin/mcp-proxy/compress.rs` with inline first-sentence extraction (Story 2.1.1)
and `$ref` inlining + `examples` stripping (Story 2.1.2).

---

## Consequences

- No new dependency required for Phase 2
- `SchemaCompressor` is ~200 LOC of pure functions with zero I/O — trivially testable
- Compression levels map to plan.md's `Light` (first sentence) and `Aggressive` ($ref inlining)
- The `CompressionLevel` enum naming in `mcp-compressor` (Low/Medium/High/Max) is NOT adopted
  to avoid confusion with our different semantics (Off/Light/Aggressive per plan.md)
