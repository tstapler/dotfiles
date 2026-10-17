# ADR-002: Two-store persistence (derived `pipeline.db` + source-of-truth `state.db`) keyed by a metadata-insensitive `ContentKey`

**Status**: Accepted; amended 2026-10-16 after architecture review (rollback destroyed undo records); hash-format details pending spike (Story 2.2a) · **Plan**: Stories 2.2, 2.4, 8.3

## Context
~17k files, incremental reruns, confidential face embeddings, report queries. EXIF writes change file bytes, so a sha256-of-bytes key would invalidate the cache after every write (`research/architecture.md` s8, `research/pitfalls.md` s3).

The first draft put every table in one SQLite file and documented rollback as "delete `pipeline.db`". That file mixed recomputable caches (evidence, fusion decisions) with irreplaceable data (the write journal that makes `undo` possible, owner face labels and constraints, owner anchor pins). Following the rollback after any `--apply` would have destroyed the undo records, violating the requirements' "every write is reversible".

## Decision
- **Two stores, classified by recoverability.**
  - `~/.local/share/gphotos-organizer/pipeline.db` (DERIVED, WAL, mode 600): `files, evidence, decisions, faces, clusters, embeddings, anchors, calibration, dup_groups, uploads_observed, audit_runs, run_metrics, schema_version` (the last additions cover Stories 5.2 `anchors`, 5.3 `calibration`, 6.1 `dup_groups`, 6.2 `embeddings`). Safe to delete and rebuild.
  - `~/.local/share/gphotos-organizer/state.db` (SOURCE OF TRUTH, WAL, mode 600): `write_journal, labels, constraints, anchor_pins, schema_version`. Plus append-only files: `journals/<run_id>.jsonl` (an fsynced mirror of every journal row), `journals/state-events.jsonl` (label, constraint and pin changes), `review/decisions.jsonl`, `review/ids.jsonl` (typed review-item aliases, ADR-009), `placeholders.jsonl`. `state.db` is backed up to `backups/state-<ts>.db` with the SQLite backup API (or `VACUUM INTO`, never `cp` of a live WAL file) before every `--apply`. Also source of truth: `placeholders-labels.jsonl` and `backup-attestation.json`. `DATA/prewrite/<run_id>/` holds local pre-write byte snapshots (large; removed only by `prewrite purge`). Rollback never deletes any of these.
- **Single-writer rule.** Only `cli.py` writes `state.db`. `analyze_ml.py` (Python 3.12) writes only `evidence, faces, clusters, embeddings, calibration` rows and `run_metrics` rows (`holdout_mae`, Story 6.3) in `pipeline.db` and opens `state.db` with `mode=ro` (it reads labels and constraints). Both processes set `PRAGMA busy_timeout` and retry on `SQLITE_BUSY`; one `analyze` runs at a time (`DATA/analyze.lock`). The ML script refuses to start when either store's applied-migration set differs from what the code expects.
- **Migrations are per epic and independent**: files named by owning story (`migrations/pipeline/s0403_faces.sql`), applied in name order, recorded by name in `schema_version`. `s0202_initial` creates only `files, evidence, decisions` (pipeline) and nothing but `schema_version` (state); each later story ships its own table migration (state: `s0803_write_journal`, `s0404_labels_constraints`, `s0502_anchor_pins`; pipeline: `s0403_faces`, `s0404_clusters`, `s0502_anchors`, `s0503_calibration`, `s0601_dup_groups`, `s0602_embeddings`, `s0903_uploads_observed`, `s0909_audit_runs`, `s1002_run_metrics`). No up-front 12-table schema.
- **Write state is not stored on `decisions`.** `DecisionStatus` holds fusion outcomes only (Anchor / Eligible / Review / Conflict / UserOverride); `WriteState` (NotWritten / Pending / Verified / Mismatch / Reverted) is a join over `write_journal` (Story 8.6). `fuse` can therefore never clobber or go stale against write state.
- `ContentKey` = pixel-stream hash (`exiftool -ImageDataMD5`) where supported, else sha256 of bytes captured before any write and pinned via a `(path, size, mtime_ns)` map. Evidence rows keyed by `(content_key, plugin, plugin_version, params_hash, kind, seq)`; version bumps keep old rows (stale, for audit).
- `album_mapping.json` and `upload_manifest.json` keep their format and get atomic writes. Their paths come from `LegacyPaths` (the manifest lives at the repo root, not under `G/`; CLI defaults were cwd-relative).

## Spike outcome
*(To fill in Story 2.2a: per-format stability of `ImageDataMD5` across a journaled write for JPEG, PNG, TIFF, HEIC, MP4.)*

## Consequences
SQL aggregates feed the run report; embeddings are BLOBs (about 2 KiB per face). A failed hash-stability result for a format forces the pinned-sha256 path for it. Two files to open instead of one; in exchange, "delete the derived DB" is always a safe reset and undo survives it (acceptance tests in Stories 2.2, 4.5, 8.3, 8.5). Deviation from requirements' "cache beside the manifest": everything stays under `DATA/` for privacy and data residency.

## Alternatives rejected
JSONL for everything (no indexed lookup, torn last line, base64 bloat; kept only for the append-only mirrors); one SQLite file with a "don't delete these tables" rule (rollback instructions drift, a single `rm` loses undo); sha256-of-bytes only (cache invalidated by every write).
