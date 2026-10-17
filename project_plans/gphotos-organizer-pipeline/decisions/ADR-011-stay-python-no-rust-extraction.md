# ADR-011: Stay in Python inside gphotos-organizer; do not extract a standalone Rust product (yet)

**Status**: Accepted · **Plan**: cross-cutting (informs ADR-001, ADR-002, ADR-004)

## Context
Owner asked (2026-10-16) whether to extract the pipeline into a standalone Rust product. Evidence in `research/`: the ML parts (InsightFace, scikit-learn HDBSCAN, CLIP-style embeddings) are Python-first (`research/stack.md`, `research/build-vs-buy.md`); the workload is a one-off ~17k-image batch dominated by model inference and exiftool/rclone subprocesses and quotas, not glue-code speed; `research/features.md` found no local tool that dates undated scans, but no evidence of demand beyond the owner; InsightFace pretrained weights are non-commercial (ADR-006), which constrains distribution; Google Photos remediation relies on unofficial APIs that may break. Rust ML equivalents (HDBSCAN, CLIP preprocessing) were not evaluated.

## Decision
Keep the pipeline in Python in `stapler-scripts/gphotos-organizer`. Keep boundaries language-neutral so a Rust core can replace parts later: SQLite as the shared store (ADR-002), JSON `Evidence` records, ML plugins as a separate script talking only through the schema (ADR-004), and golden-file tests for fusion, guards, journal and audit (usable as a port-conformance suite).

## Revisit when any of these holds
- Someone besides the owner wants it and the owner accepts support plus the licensing work (license-clean models, biometric-data handling).
- A license-clean face model meets the accuracy target on the owner's anchor photos.
- The two-environment Python deployment becomes the main pain.
- Fusion/guards/journal/audit/review are stable and a single fast binary is wanted.

## Consequences
Fast iteration on the unproven parts (fusion accuracy, remediation). Extraction later is a port of the core against an existing schema and test suite, not a redesign. Cost: no Rust single-binary benefits now.

## Alternatives rejected
Rust rewrite now (rework of mature Python ML libraries before the design settles); Rust core with Python plugins from day one (extra FFI/schema ceremony before any plugin exists).
