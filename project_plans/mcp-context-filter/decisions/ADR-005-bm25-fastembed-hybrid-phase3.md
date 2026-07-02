# ADR-005: BM25 as default Phase 3 search; fastembed hybrid behind feature flag

**Date**: 2026-07-02
**Status**: Accepted
**Deciders**: Tyler Stapler
**Context**: mcp-context-filter Phase 3 — tool discovery search backend

---

## Context and Problem Statement

Phase 3 exposes a `search_tools(query)` meta-tool that searches the full upstream tool catalog. Three search backends were evaluated:

| Backend | Recall (top-5) | Latency | Deps | Notes |
|---------|--------------|---------|------|-------|
| BM25 alone (`bm25` crate) | ~34% on semantic queries | <1ms | Zero native | Misses "notify the team" → `slack_send_message` |
| Dense embeddings alone (`fastembed-rs`) | ~80% | 10–30ms | ONNX runtime (~65MB) | Misses exact tool name matches |
| Hybrid BM25 + embeddings | ~94% | 10–30ms | ONNX runtime | Best recall; slightly higher latency |

The pitfalls research (Risk Area 6) confirms: **BM25 alone achieves only 34% accuracy on a 2,792-tool dataset**. Anthropic's own internal tool search uses BM25 but reaches higher recall via hybrid search. A 34% recall rate means 2 in 3 semantic queries would silently fail to surface the correct tool — unacceptable as the primary Phase 3 search mechanism.

---

## Decision

**Chosen: BM25 as default (always compiled); fastembed hybrid search behind `semantic-search` Cargo feature flag.**

**Default (no feature flag)**:
- `bm25` crate: pure Rust, no native deps, in-memory, builds in any environment
- Index builds in <10ms for 200 tools; query latency <1ms
- Covers exact-keyword and stemming-based matches well (tool names, domain keywords)

**Opt-in (`--features semantic-search`)**:
- `fastembed` crate with BGE-small-en-v1.5 (or bge-micro-v2 quantized, ~23MB)
- Hybrid scoring: `score = 0.7 × bm25 + 0.3 × cosine_similarity`
- Weights tuned for tool-name-biased corpus (BM25 stronger on terse tool names; embeddings add semantic coverage)
- Graceful fallback to BM25-only if ONNX model file is missing

**Why not BM25-only as the final design:**

The pitfalls research is unambiguous: BM25-only produces false negatives that are **invisible to the user** (no error raised; Claude reasons around the absence). The 34% accuracy figure is the measured production rate. Given the proxy's entire purpose is to ensure Claude can find the tools it needs, a search mechanism with 66% failure rate on semantic queries is not acceptable as a shipped product.

The `semantic-search` feature flag approach allows Phase 3 to ship fast (BM25 only) while the hybrid upgrade path is ready for users who want higher accuracy.

---

## Cargo additions

```toml
bm25 = "0.1"                                    # always-on
fastembed = { version = "4", optional = true }  # semantic-search feature
```

```toml
[features]
semantic-search = ["dep:fastembed"]
```

---

## Consequences

**Positive**:
- Phase 3 ships with no native deps (BM25-only); compiles in any environment including CI
- Users with macOS Apple Silicon get near-instant model inference (~10ms) with the semantic flag
- Feature flag pattern allows incremental adoption: `cargo install --features semantic-search`
- BM25 covers the common case (user knows the tool name or domain keyword)

**Negative**:
- BM25-only default has known false-negative rate for semantic queries
- `fastembed` feature adds ~65MB ONNX model download on first run (cached after)
- Hybrid weight tuning (0.7/0.3) is based on general guidance, not tool-catalog-specific benchmarks; may need empirical adjustment
