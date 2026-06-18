# ADR-009: Similarity Detection — SimHash Pre-filter + gaoya MinHash LSH in spawn_blocking

**Status**: Accepted
**Date**: 2026-06-17

## Context

FR-10.4 requires auto-dedup for the SharedContext memory store: if a new value is ≥95% similar to an existing entry, update rather than create a new one. Entries can be up to 100KB. The similarity check must not block the async runtime.

A naive similarity approach using edit distance on 100KB inputs will block the async runtime for seconds per comparison, degrading all concurrent requests.

## Decision

Use a **two-tier approach**:

**Tier 1 — SimHash 64-bit pre-filter (O(1) compare)**:
Use the `simhash` crate. On every `PUT /memory/{key}`, hash the new value to a 64-bit fingerprint. XOR with each existing fingerprint and count set bits (Hamming distance). If Hamming distance > 6 bits, skip — no similarity check needed. This eliminates the vast majority of pairwise comparisons at negligible cost.

**Tier 2 — gaoya MinHash + LSH (1–5ms, async-safe)**:
For the ~5% of candidates that pass the Hamming pre-filter (distance ≤ 6), use `gaoya`'s `MinHasher32` + `MinHashIndex` with 128 hash functions and 16 bands × 8 rows (targeting ~0.94 Jaccard threshold). Run inside `tokio::task::spawn_blocking` to avoid blocking the runtime. The 95% similarity threshold is defined as Jaccard similarity on word 5-shingles.

```toml
simhash = "0.1"   # 115K downloads — simple 64-bit LSH pre-filter
gaoya = "0.2"     # 11K downloads — MinHash + LSH index
```

## Alternatives Considered

| Option | Rejected because |
|--------|-----------------|
| `strsim::normalized_levenshtein` | O(n²) with no early-exit optimization — benchmarks show ~10 seconds per comparison on 100KB inputs; would block the async runtime and stall all concurrent requests for the duration |
| `rapidfuzz` Levenshtein with cutoff | Myers algorithm with early exit; ~1–10ms on 100KB with a tight cutoff threshold; edit distance is order-sensitive (moving a paragraph counts as ~2× its length in edits) — semantically wrong for document-level dedup where paragraph reordering should not count as dissimilarity |
| Jaccard shingles without LSH (exact) | O(n log n) per comparison; correct semantics; but requires comparing every new entry against all existing entries — O(N) comparisons per write, unacceptable as the store grows |
| SimHash alone (no MinHash verification) | SimHash Hamming distance is an approximate pre-filter; false positives exist; must verify candidates with exact Jaccard before updating |

## Consequences

- The 95% similarity threshold is defined as **Jaccard on word 5-shingles**, not edit distance: 95% of all 5-word windows must be identical; one rewritten paragraph in 20 yields ~85–90% Jaccard (correctly failing the 95% threshold)
- `MinHashIndex` is not `Send` by default — wrap in `Arc<Mutex<MinHashIndex<...>>>` or use a dedicated worker task for index operations
- `spawn_blocking` tasks cannot be aborted once started — keep MinHash signing bounded (1–5ms for 100KB) to avoid blocking shutdown for extended periods
- The `simhash` pre-filter reduces MinHash invocations to a small fraction of writes; at 1000-entry store capacity (FR-10.6), worst-case MinHash work is bounded and manageable
- `gaoya`'s `MinHashIndex` stores signatures per key; the full dedup write path is: compute SimHash → Hamming pre-filter → if candidate: `spawn_blocking` MinHash → verify Jaccard → update or insert
