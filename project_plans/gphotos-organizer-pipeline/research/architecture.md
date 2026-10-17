# Research: Architecture for a pluggable analysis pipeline (gphotos-organizer)

**Date**: 2026-10-16 · **Scope**: `stapler-scripts/gphotos-organizer/` · **Requirements**: `../requirements.md`
**Confidence labels**: VERIFIED = file opened this session (path:line cited). INFERRED = reasoned, not run. External-library claims (pluggy, InsightFace, etc.) are INFERRED from general knowledge; other research dimensions own the verification.

## 1. Current pipeline (VERIFIED)

```
scan_cmd ──► scanner.scan_usb_drive ──► album_mapping.json (ScanResults)      cli.py:51
infer_cmd ─► ai_enrich.enrich_mapping_data (folder-name regex, hardcoded       cli.py:109, ai_enrich.py:12-45
             family events) mutates AlbumMapping in place
review_cmd / update-album ─► manual override of album date                     cli.py:155, 221
fix-metadata ─► metadata.update_album_metadata ─► exiftool argfile per chunk   cli.py:301, metadata.py:100
upload ─► uploader.upload_album_to_gphotos ─► `rclone copy` per album          cli.py:363, uploader.py:83
          └► upload_manifest.json (UploadManifest.completed_albums[album_id])
```

Key structural facts:

- **Album is the unit of everything.** `AlbumMapping` carries one `inferred_date`/`date_confidence`/`date_source` string triple (models.py:24-39). There is no per-file entity anywhere; `ScanResults` holds only `FileStats` counts (models.py:15-21), not file paths or hashes.
- **Per-file dates are synthesized at write time**, not stored: `infer_file_specific_date(name, album_base_dt, idx*offset)` regex-parses the filename, else `base + index*5s` (metadata.py:38-62, 156). This is where a per-file inferred date must replace the synthesis.
- **EXIF writes are irreversible today**: `-overwrite_original` is on by default (metadata.py:105, 159-160) and no original values are recorded. This directly violates the requirements' "recorded original-value journal" risk control.
- **`metadata_status = "fixed"` is set only in the `--apply` branch** (cli.py:353-354) and `update_album_metadata` counts a chunk as updated even on non-zero exiftool exit (metadata.py:196-200). So "truthful status" (scope item 6) needs per-file write results, not album-level flags.
- **Persistence is whole-file JSON rewrite** (`mapping_file.write_text(json.dumps(...))`, cli.py:357, 435) — non-atomic; a crash mid-write corrupts the only source of truth. The manifest is written after each album (uploader.py:120-130), also non-atomic.
- **Upload is album-granular and date-blind**: rclone copies the folder; nothing gates on date confidence (uploader.py:96-108). The "do not upload `2021 random photos`" constraint is not enforced in code.
- **Single-file CLI shell**: `cli.py` has the PEP 723 header (cli.py:2-9), flat sibling imports (`from metadata import ...`, cli.py:28-40), and a Typer app. Siblings are plain modules, no package.
- No tests exist in the directory (Glob of `*.py` shows none); the repo convention is plain-function tests (memory: `pi_llm_sync_conventions`).

## 2. Where analysis stages plug in

Insert a new **per-file stage between `scan` and `fix-metadata`**, leaving `scan`, `upload`, and `rclone` mechanics untouched:

```
scan ─► [NEW] index (enumerate files, content hash, album ctx) ─► [NEW] analyze (plugins, cached)
     ─► [NEW] fuse (evidence → DateDecision per file, with guards) ─► [NEW] review list
     ─► fix-metadata (REFACTORED: consumes DateDecisions, writes journal) ─► [NEW] audit ─► upload (gated)
```

`ai_enrich`'s existing folder/filename heuristics become the first two plugins (folder-year, filename-date) so the legacy path and the new path are the same path.

## 3. Plugin mechanism comparison

Context: one `uv run` PEP 723 script, one operator, 3-5 plugins, heavy optional deps (face/age models, onnxruntime) that must NOT load unless the plugin is enabled.

| Mechanism | Fit for uv-script | Verdict |
|---|---|---|
| **Entry points (`importlib.metadata`)** | Needs an installed distribution with `pyproject.toml`; a PEP 723 script has none. Discovery would find nothing unless packaged. | Reject: forces packaging that the repo's script convention avoids (INFERRED). |
| **pluggy** | Adds a dependency and hook-spec/marker ceremony; designed for third-party ecosystems and many-to-many hooks (pytest). Requirements explicitly warn about plugin-framework over-engineering. | Reject: ceremony exceeds 3-5 in-repo plugins. |
| **Directory discovery** (`plugins/*.py` via `importlib`) | Works with scripts; "drop a file" matches "add a plugin without editing cli.py core flow". Costs: import-time side effects, implicit load order, harder static typing/testing, silent breakage on import error. | Acceptable, but unneeded magic. |
| **Explicit registry** (`@register` decorator or dict in `plugins/__init__.py`) | Trivial, greppable, lazy-importable (store dotted path, import only if enabled). Adding a plugin = new file + one registry line. | **Good**; the line edit is in the registry, not in `cli.py` core flow, which satisfies the success metric. |
| **`typing.Protocol`** | Not a discovery mechanism; it is the *contract* type. Structural typing means plugins need not import a base class. | **Use alongside registry** for the contract. |

**Recommendation: explicit lazy registry + `Protocol` contract + optional directory-scan escape hatch.** Registry maps `name -> "pkg.module:Class"` strings; only enabled plugins are imported, so heavy deps (and their PEP 723 declarations) stay isolated. Heavy-dep problem: PEP 723 deps are fixed per script, so heavy plugins should either (a) be run as `uv run --with insightface ...` subprocess stages writing to the shared cache, or (b) live in a second PEP 723 script (`analyze_faces.py`) that shares only the cache schema. Decision (a)/(b) is for the plan; the cache being the integration point makes both viable. This is the main architectural risk of the single-script constraint (INFERRED).

## 4. Plugin contract

```python
class AnalysisPlugin(Protocol):
    name: str                 # stable id, part of cache key
    version: str              # bump invalidates cached results
    requires_cloud: bool      # gated by --allow-cloud
    scope: Literal["file", "album", "corpus"]   # corpus = needs all files (face clustering, anchor calibration)
    def analyze(self, ctx: FileContext) -> list[Evidence]: ...
```

Inputs, `FileContext` (frozen): `path`, `content_hash` (sha256 of bytes; cache key), `album` (id, folder_name, folder_year bounds, album_date), `exif_snapshot` (existing date fields), `prior: dict[plugin_name, list[Evidence]]` (only for plugins declaring `after=[...]`, so ordering is an explicit DAG, not registry order), `config`.

Output, `Evidence` (pydantic, immutable):

| Field | Type | Notes |
|---|---|---|
| `kind` | `"date" \| "person" \| "age" \| "era" \| "location"` | tagged union by kind |
| `value` | for dates: **interval** `[earliest, latest]` plus optional point estimate | intervals, not points, so fusion can intersect and "unknown" is representable |
| `confidence` | float 0-1, **calibrated** per plugin (anchor-derived), not raw model score | uncalibrated scores break fusion |
| `provenance` | `{plugin, plugin_version, model_id, inputs (e.g. cluster_id, person_id, age_est), cost: local\|cloud}` | needed for review list and "which plugins voted" |
| `abstain` | bool | plugins must be able to say "no signal" instead of guessing (Rabbit Hole 1) |

Corpus-scope plugins (face clustering, anchor calibration) run as separate passes producing per-file Evidence from corpus state (e.g., cluster id), cached with a corpus-state key.

## 5. Cache: SQLite vs JSONL

Requirement: ~17k files, per-file-hash keyed, incremental reruns, stays local, holds face embeddings (confidential), concurrent-safe enough for a single operator, queryable for the report (confidence histogram, error by decade).

| | SQLite | JSONL |
|---|---|---|
| Lookup by (hash, plugin, version) | indexed PK | full scan or in-memory dict rebuild |
| Atomicity / crash safety | transactions, WAL | append is mostly safe; torn last line possible; compaction needed |
| Report queries | SQL aggregates | load everything |
| Embeddings | BLOB column | base64 bloat |
| Dependency | stdlib `sqlite3` | stdlib |
| Diff-ability / hand-editing | needs a tool | greppable |

**Recommendation: SQLite (stdlib), one file `pipeline.db` beside the manifest, gitignored and outside dotfiles tracking.** Tables: `files(hash PK, path, album_id, size, mtime)`, `evidence(hash, plugin, plugin_version, kind, payload_json, confidence, created_at; PK hash+plugin+plugin_version+kind+seq)`, `decisions(hash PK, date, interval, confidence, status, fused_from_json, decided_at)`, `write_journal(...)`, `uploads_observed(...)`. Keep `album_mapping.json` and `upload_manifest.json` as-is (they are an existing contract); export JSONL on demand for the review list. Fix the existing non-atomic JSON writes with temp-file + `os.replace` at the same time.

Cache invariants: key is **content hash**, so a moved/renamed file reuses results; a duplicate file under two albums shares evidence but has two `files` rows keyed by path. Changing a plugin's `version` or config hash makes old rows stale (kept, not deleted, for audit). Hashing 17k images is I/O-bound on the USB drive; store `(path,size,mtime)->hash` to skip rehash (INFERRED to matter; not measured).

## 6. Evidence fusion

Goal: per file, produce a `DateDecision {interval, point, confidence, status, voters}`.

Options:

1. **Bayesian**: prior over years (from folder bounds), per-plugin likelihood over years, multiply, normalize; confidence = posterior mass in the chosen window. Principled, handles multiple weak votes, but needs calibrated likelihoods (anchors may be too sparse, Feasibility Risk 3) and assumes conditional independence (age estimates and era classifier on the same pixels are not independent, so naive product overconfidence is likely).
2. **Weighted interval intersection**: each plugin gives a hard-ish interval at some coverage level; intersect strong ones; use weighted vote/median inside the intersection. Simple, explainable, degrades gracefully; poor at representing soft evidence.

**Recommendation: two-layer.** Layer A is deterministic **hard constraints that prune the year axis first** (never overridden by any score). Layer B is a discretized per-year log-score (Bayesian-flavored: sum of weighted per-plugin log-likelihoods over the surviving years, with a dependence discount so correlated plugins cannot jointly exceed a cap). Output is the highest-mass contiguous window; confidence = mass inside it. The discretized year axis keeps it explainable and cheap, and `abstain` evidence contributes nothing. If fewer than a configurable number of independent voters survive, status = `review`.

**Hard sanity constraints (Layer A), each recorded as a named guard in provenance:**

| Guard | Rule | Source |
|---|---|---|
| Birth/death bounds | person P appears (identified) in photo ⇒ date in `[birth(P), death(P)]`; apparent age a ⇒ date ≈ birth(P)+a (a soft vote, the bound is hard) | owner-provided people table |
| Folder-year bounds | a folder name containing year Y ⇒ date in `[Y-k, Y+k]` with k configurable; widen to open-ended only by explicit owner override | scanner/ai_enrich folder year |
| Anchors | files with trusted known dates (real EXIF from camera, dated filenames) are fixed points, never re-inferred; used to calibrate plugin error by decade | EXIF snapshot, anchor list |
| Upload-window ceiling | inferred date may not exceed latest anchor-derivable bound; no pre-1995 scan can resolve to "now" (Success Metric 1) | requirements |
| Physical plausibility | not in the future; not before photography/format era implied by medium (e.g., a color print before 1935) | static table |

Contradictions (guards leave empty interval) ⇒ status `conflict`, always to the review list, never written.

Thresholds: `--min-confidence` gates EXIF writes; below it ⇒ review list. Anchor-held-out error per decade feeds the per-run report.

## 7. Review list

A view over `decisions WHERE status IN ('review','conflict')` plus the 132 album-level flags (`needs_review`/`flag_reasons`, models.py:34-36; whether they merge is the owner open question — recommended **yes, as one list with a `source` column**, since album flags are just a coarser reason code). Each row: thumbnail path, album, candidate interval, confidence, voters + provenance, guards fired. Owner resolution writes an `Evidence(kind=date, provenance=user_override, confidence=1.0, hard=True)` row; it is an anchor from then on, which also improves calibration. Delivery: `review export` to a markdown/CSV file and `review apply <file>` to ingest decisions (no web UI is in scope).

## 8. EXIF write journal (reversibility)

Replace `-overwrite_original` (metadata.py:105,159) with a journal-first protocol:

1. Before any write batch, read current values for the tags to be written (`exiftool -json -DateTimeOriginal -CreateDate -ModifyDate -GPS* -Keywords ...`) and insert into `write_journal(run_id, hash, path, tag, old_value, new_value, content_hash_before, written_at, status)` and commit.
2. Write via exiftool with `-P` (preserve mtime). Do NOT use `-overwrite_original`; either keep exiftool's `_original` sibling until a `commit` step, or journal-only. Journal-only is recommended because `_original` files double disk on a USB drive and confuse `rclone copy` include filters (rclone copies `*.JPG_original`? No: filters are by extension list, uploader.py:100-101, so `_original` is excluded; INFERRED safe, not tested).
3. After write, re-read the tags (read-back rule) and set `status=verified` or `mismatch`; `metadata_status` derives from these rows, not from an album flag.
4. `undo --run <id>` replays `old_value`. Note the content hash changes after a write, so the cache key must be the hash of the **pre-write** bytes, stored as `content_hash_before`, or the key must be pixel-data-only. Hashing the image pixel stream (not file bytes) avoids invalidating the cache after EXIF edits; **recommendation: key on a hash that ignores metadata** (e.g., `exiftool -ImageDataMD5`, or hash file bytes once and pin it via `(path,size,mtime)` map recorded pre-write). This is the one subtle consistency trap in the design.

Crash safety: a journal row exists before the write, so a crash leaves `status=pending` rows that a `recover` step reconciles by re-reading the file.

## 9. Audit and remediation of already-uploaded items

Facts (VERIFIED from code): the manifest only says an album's `rclone copy` exited 0 (uploader.py:112-130); it cannot say what dates Google Photos holds. Whether the Library API/rclone can read per-item dates, and whether any API edits date or deletes, is the open question owned by the Google Photos research dimension; this document designs for both outcomes.

Audit flow: `audit` enumerates remote items (via whatever read route research confirms; rclone `lsjson` on `gphotos:media/by-month` is a candidate, INFERRED), stores them in `uploads_observed(remote_id, filename, remote_date, album, observed_at)`, joins to local `files` by filename+size (content hash if available), and flags items whose remote date falls in the upload window or violates the decision's interval. Output feeds the same review list with `source=audit`.

Remediation is a strategy chosen by capability, behind one interface:

| Capability found | Action |
|---|---|
| API can edit date | `RemediationStrategy.apply` patches the date |
| Only delete/re-upload possible | write corrected EXIF locally (journaled), emit a "trash these N items, then re-upload" worklist; re-upload through the normal gated upload |
| Web-UI only | emit a worklist grouped by album with target dates for manual "Edit date & time" |

Upload gate: `upload` refuses an album unless every file has a `decisions` row with status `written` or `anchor`, and the album is not on a deny list (`2021 random photos`). This enforces the constraint that is currently only documentation. Existing manifest entries (604 albums) are grandfathered as `uploaded_unverified` until the audit confirms them.

## 10. Data flow and consistency requirements

```
USB files ──hash──► files(hash) ──► plugins ──► evidence ──fuse──► decisions ──► review (owner) ─┐
                                                                         │                      │
                                                  write_journal ◄── gate(min-confidence) ◄──────┘
                                                        │ exiftool write + read-back
                                                        ▼
                                              upload gate ──► rclone ──► manifest ──► audit ──► remediation
```

Requirements:

- **C1 Single writer of truth per concern**: evidence is append-only; decisions are derived and recomputable from evidence + guards; write_journal and manifest are the only records of side effects.
- **C2 Journal-before-write, verify-after-write**: no exiftool write without a committed journal row; status flips only on read-back.
- **C3 Idempotency**: rerunning any stage with unchanged (hash, plugin version, config) is a no-op; fusion is a pure function so `fuse` can always be rerun after a threshold change without re-analysis.
- **C4 Atomic persistence**: SQLite transactions for new state; temp-file + `os.replace` for the legacy JSON files.
- **C5 Cache key stability across writes**: key must survive EXIF edits (see section 8).
- **C6 Dry-run default** retained for every mutating command (`--apply`, cli.py:310-314 convention); cloud plugins require `--allow-cloud`; the run report records which plugins used cloud.
- **C7 Privacy**: DB and embeddings in a gitignored local dir (e.g. alongside `album_mapping.json`, which sits in the repo dir today; ensure the path is in `.gitignore` or relocated to `~/.local/share/gphotos-organizer/`; the repo tracks `stapler-scripts/` so this matters).
- **C8 Truthful status**: `metadata_status`/`upload_status` become derived views over journal/manifest/audit, not hand-set flags (cli.py:354, 432).

## 11. Recommended module layout

Keep flat-sibling imports (matches current convention, cli.py:28-40) but group the new code in a package so `cli.py` stays a thin Typer shell:

```
gphotos-organizer/
  cli.py                  # Typer commands only; adds: analyze, fuse, review, audit, undo
  models.py               # existing; add FileRecord, Evidence, DateDecision (or models_pipeline.py)
  scanner.py ai_enrich.py locations.py report.py uploader.py   # existing
  metadata.py             # refactored: takes DateDecisions, writes via journal
  pipeline/
    contract.py           # AnalysisPlugin Protocol, FileContext, Evidence
    registry.py           # name -> lazy "module:Class", enable flags, DAG order
    store.py              # sqlite schema + access (files, evidence, decisions, journal, uploads_observed)
    fusion.py             # guards + scoring; pure functions
    journal.py            # exiftool read/write/verify/undo
    audit.py              # remote enumeration + RemediationStrategy
  plugins/
    folder_year.py filename_date.py   # extracted from scanner/ai_enrich
    faces.py age.py anchors.py era.py cloud_vision.py
  tests/                  # plain-function tests: fusion.py and guards first (pure, highest value)
```

## 12. Disposition for touched code

| Code | Disposition | Why |
|---|---|---|
| `cli.py` | **Extend as-is** | Typer subcommands are additive; new commands do not require restructuring existing ones. Only `fix-metadata`/`upload` bodies change (they call the refactored layers). |
| `scanner.py` | **Extend as-is** | Album enumeration is correct; the new per-file `index` stage sits after it. |
| `ai_enrich.py` | **Isolate via seam** | Hardcoded family-event dates (ai_enrich.py:36-45) are data, not logic; wrap its heuristics as `folder_year`/`event` plugins, leave the old function callable for `infer` until parity is shown. |
| `metadata.py` | **Refactor-first** | It fuses date synthesis, tag generation, GPS, exiftool I/O, and `-overwrite_original` in one 110-line function (metadata.py:100-209) with no read-back and a success-on-failure path (196-200). A journal cannot be bolted on; split into plan (what to write) / apply (journaled write) first. |
| `uploader.py` | **Isolate via seam** | rclone copy and quota handling are sound and recent; add a gate predicate and `audit` beside it without editing `_run_rclone`/`QuotaExceeded`. |
| `models.py` | **Extend as-is** | Add per-file models; keep `AlbumMapping`/`ScanResults`/`UploadManifest` field-compatible so existing JSON loads. |
| `report.py` | **Extend as-is** | Add plugin counts, histogram, per-decade error sections. |

## 13. Event-Command-Policy table

| Event (past tense) | Actor | Command | Policy (when event, then...) | Aggregate / system | Hot spot |
|---|---|---|---|---|---|
| AlbumsScanned | Operator | `scan` | then index files | scanner / mapping JSON | |
| FilesIndexed | System | `index` | then enqueue enabled plugins whose (hash, version) is uncached | `files` | Hash stability across EXIF writes (C5) |
| EvidenceRecorded | Plugin | `analyze` | append evidence; never mutate prior rows | `evidence` | Cloud plugin runs only if `--allow-cloud` |
| CorpusPassCompleted | System | `cluster-faces` / `calibrate-anchors` | then plugins with `after=` this pass may run | corpus plugins | Cluster drift across decades; manual merge |
| PersonLabeled | Operator | `label-cluster` | then recompute dependent decisions | people table | Owner birth-date input is a blocker |
| DateDecided | Fusion | `fuse` | if guards leave a window and confidence >= threshold then `eligible-for-write` else `review` | `decisions` | Dependence discount calibration |
| ConflictDetected | Fusion | (auto) | if guards empty the interval then `conflict`, never write | `decisions` | |
| ReviewResolved | Operator | `review apply` | record user_override evidence as hard anchor, re-run `fuse` | `evidence` | Merge album flags into same list (owner) |
| WriteApproved | Operator | `fix-metadata --apply` | only for `eligible` rows; dry-run otherwise | write planner | |
| OriginalValuesJournaled | System | (precondition) | if journal row not committed then block write | `write_journal` | |
| ExifWritten | exiftool | `apply` | then read back; on mismatch mark `mismatch` and halt album | `write_journal` | Current code reports success on non-zero exit |
| ExifVerified | System | (auto) | then `metadata_status` derives to fixed | `write_journal` | |
| WriteReverted | Operator | `undo --run` | replay old_value, mark `reverted` | `write_journal` | |
| UploadGateEvaluated | System | `upload` | if any file undecided/conflict or album denied then refuse; else proceed | upload gate | Deny list: `2021 random photos` |
| AlbumUploaded | rclone | `upload --apply` | then record manifest entry | `UploadManifest` | `uploaded_unverified` for the 604 legacy albums |
| QuotaExceeded | Google Photos | (HTTP 429) | sleep to 00:05 Pacific, retry | uploader | Untested against real quota |
| RemoteItemsObserved | System | `audit` | then join to local decisions | `uploads_observed` | API read capability unverified |
| MisdatedItemFlagged | Audit | (auto) | if remote date in upload window or outside decision interval then add to review list (`source=audit`) and select remediation strategy | review list | |
| RemediationPlanned | Operator | `audit --plan` | per capability: API patch, trash+reupload worklist, or web-UI worklist | remediation strategy | Dedup on re-upload; deletion may be UI-only |

## 14. Risks and open items for the plan

1. **Heavy-dependency isolation under PEP 723** (face/age models) is the real architectural constraint; decide subprocess `uv run --with` vs second script before the plan.
2. **Cache key vs EXIF edits** (section 8) must be settled up front; a wrong choice silently invalidates the cache after every write.
3. **Fusion calibration** depends on anchor density, which is unknown; ship Layer A guards and review flow before Layer B scoring so the pipeline is safe even with weak statistics.
4. **Remediation shape** depends on Google Photos API research; the strategy interface isolates that uncertainty.
5. Existing `album_mapping.json` is in the repo directory; confirm it and the new DB are untracked (data residency).
