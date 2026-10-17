# Implementation Plan: gphotos-organizer-pipeline

**Feature**: Pluggable, local-first photo-dating pipeline (evidence plugins -> guarded fusion -> review -> journaled EXIF writes -> gated upload -> audit/remediation) for `stapler-scripts/gphotos-organizer`.
**Date**: 2026-10-16
**Status**: Ready for implementation
**ADRs**: ADR-001 plugin registry, ADR-002 two-store persistence (derived `pipeline.db` + source-of-truth `state.db`) + ContentKey, ADR-003 two-layer fusion, ADR-004 ML runtime isolation, ADR-005 local-by-default / `--allow-cloud`, ADR-006 face models + licensing, ADR-007 EXIF plan/apply + journal + year-precision policy, ADR-008 remediation strategy interface, ADR-009 review surface, ADR-010 era-by-appearance, ADR-011 stay Python / no Rust extraction (all in `project_plans/gphotos-organizer-pipeline/decisions/`)

**Plan size (recounted after triad repair pass 3, 2026-10-16)**: 10 epics, 72 stories, 209 tasks, 13 agent waves (the earlier repair pass added Stories 5.6 and 8.8; triad repair pass 1 added Stories 1.12, 1.13, 1.14, 7.5, 7.6 and 24 tasks, two of them from splitting Tasks 1.2b and 1.11b; triad repair pass 2 added 8 tasks: 1.13c, 4.5e, 7.2f, 7.3f, 7.4e, 7.6e, 8.8d, 10.3c, and no story; triad repair pass 3 added 6 tasks: 1.13d, 7.1c, 7.2g, 7.4f, 7.6f, 10.3d, and no story). **Total effort is about 31.3M CU (XL), an INFERRED, uncalibrated figure** (ESTIMATION.md class midpoints, not a measurement of this pipeline); it is gated by the W5 and W9 overrun checkpoints (Effort section), which recalibrate it before the next wave starts. Every story carries a `**Depends on**` line, and `waves.py --check` fails when any of those lines and its `DEPS` table differ in either direction. (recount with `grep -c '^### Epic', `grep -c '^#### Story'`, `grep -c '^##### Task'`, or run `python3 implementation/waves.py --check`, which also recomputes the waves, the same-wave file collisions and the effort table; wave count from the Dependency Visualization).

Path shorthand used throughout: `G/` = `stapler-scripts/gphotos-organizer/` (repo-relative, expand literally). `DATA/` = the runtime data dir `~/.local/share/gphotos-organizer/` (never inside the dotfiles tree). Evidence labels: VERIFIED = cited research file opened this session; INFERRED / UNVERIFIED as in `research/*.md`.

**Owner decisions honored**: analysis is local by default, cloud plugins only behind `--allow-cloud`; full scope, no downscaling; `2021 random photos` (album id `9102dede1a50`, 9,161 files) deny-listed in code (keyed on both id and folder name, enforced at the upload gate) until its dates resolve; the legacy background upload loop is STOPPED by the owner (not merely checked) until Story 9.2 lands, because old code in a running process cannot be gated; the 23 remaining small albums (about 227 files) wait for the gated uploader (decision recorded under Risk Control and Pre-implementation Owner Checklist item 1).

**Privacy rule for a public repo (pre-mortem failure mode 8)**: `origin` of the dotfiles repo is `https://github.com/tstapler/dotfiles` (public, `git remote -v`), and these planning documents name real albums and people. Therefore: PR descriptions, test output pasted as evidence, logs and report files carry **counts and album ids only, never album titles, person names, birth/death dates or raw file paths** (paths are hashed or shown relative to an album id); `--show-names` output never goes into a PR. Where the planning artifacts themselves live is an owner decision made before the first commit (Owner Checklist item 5).

**State on 2026-10-16** (requirements baseline): 604/628 albums in `upload_manifest.json` (7,757 of 17,145 media files; `album_mapping.json` totals 17,255 files including non-media sidecars); the 604 are grandfathered as `uploaded_unverified` (Story 1.7, 9.2). `album_mapping.json` stores `flagged_albums_count: 138`, but only 137 albums have `needs_review=True` and `flag_severity != none` (recounted by script, 2026-10-16). **This plan, ADR-009 and requirements use 137 everywhere**; 138 (the stored counter) and 132 (earlier docs) are historical, and examples that use other totals are illustrative.

**Measured fact that reshapes the plan (VERIFIED by the coordinator, `exiftool -r -T -fast2 -DateTimeOriginal` over the jpg/jpeg/png on the drive `/run/media/tstapler/EE5B-3D9B`, 2026-10-16)**: of 15,943 dated images in the latest run (16,044 in an earlier run), 9,460 are dated January 1 of some year (placeholder candidates); a further 5,926 are NOT Jan 1 but carry a `12:MM:SS` time-of-day, and 3,162 of those are exactly `12:00:SS` with SS a multiple of 5, the legacy 5-second-offset signature. So Jan 1 alone under-detects legacy placeholders, and "not Jan 1" never implies genuine. Not proven: that the signature-bearing files (3,162 strict, up to 5,926) are all legacy placeholders (most probably are), or that Jan-1 files at other times of day were written by the legacy tool (no count is derived for them: the 9,460 and 5,926 figures come from the one latest run, not from mixing runs); they stay `Suspect` until corroborated. The legacy `fix-metadata --apply` evidently wrote placeholders at scale even though every album still shows `metadata_status=pending`. Consequences handled by Stories 1.9 (five-signal detector with an explicit truth table), 1.11 (legacy apply lock), 3.4 (anchors admit only `Genuine`), 8.7 (journaled revert of `LegacyPlaceholder` only; `Suspect` goes to review) and 9.9 (audit sees them).

---

## Domain Glossary
*(Exact names are used in code, tests and comments.)*

| Term | Definition | Notes |
|------|-----------|-------|
| `ContentKey` | Stable identity of a file's image content, computed before any write (pixel-stream hash via `exiftool -ImageDataMD5`; sha256 of bytes for formats without it); cache key for all evidence | Newtype over `str`; survives EXIF edits (ADR-002) |
| `PartialDate` | A date with explicit `precision` (day / month / year / range / decade) and bounds | Construct-only via `PartialDate.day()/.month()/.year()/.range()/.decade()`, which derive bounds from precision; `precision==Day` implies `earliest==latest`; no `is_placeholder` field (illegal states unrepresentable). Never renders as a full timestamp unless precision is Day |
| `DatePrecision` | Enum: Day / Month / Year / Range / Decade / Unknown | Sum type, exhaustive `match` |
| `DateInterval` | Closed interval `[earliest, latest]` of dates plus optional point estimate | What every date `Evidence` carries; intersectable |
| `PlaceholderDate` | A fabricated full timestamp (e.g. Jan 1 noon for a year-only folder) | This tool never writes one except through `YearPrecisionPolicy` rule 3 (owner opt-in, marked, journaled) |
| `PlaceholderClass` | Enum: Genuine / Suspect / LegacyPlaceholder, assigned by the detector (Story 1.9) to an EXIF date already on disk from five independent signals (time signature, Jan 1, no Make/Model, folder-date match, per-folder 5-second ladder) via an explicit truth table | Only `Genuine` (detector rule 4 or owner `confirm-genuine`) is anchor-eligible; `Suspect` and `LegacyPlaceholder` are never `Anchor` evidence; a lone signal is `Suspect`; "not Jan 1" never implies `Genuine` |
| `LegacyPlaceholder` | An EXIF date classified as written by the legacy `fix-metadata --apply`: at least two of {time-of-day `12:00:00 + 5k s`, Jan 1, per-folder 5-second ladder}, or one of them plus absent `Make`/`Model` plus a date equal to the folder/filename date | Measured: 9,460 Jan-1 candidates; 5,926 non-Jan-1 files at `12:MM:SS`, 3,162 of them strict `12:00:SS` (5 s multiples); classification of each file is NOT proven by the measurement alone; quarantined by 1.9, optionally reverted by 8.7 (this class only); owner `confirm-genuine` overrides |
| `YearPrecisionPolicy` | The single rule for any decision coarser than Day (Year / Range / Decade; Month included; `Unknown` is held by the same gate): (1) never write a fabricated month/day into `DateTimeOriginal` by default; (2) record the year in XMP `dc:Subject` / IPTC keyword `gpo-year:<YYYY>`; (3) only if the owner releases an album with `--allow-year-precision` (needed because an undated upload lands on the upload date, UNVERIFIED until Story 9.1 item 5), write a mid-period noon date (July 1 for Year) carrying the `gpo-date-inferred:<precision>` marker, journaled and listed in the review list as `source=year_precision`. The owner can veto rule 3; vetoed files simply stay un-uploaded | Stated identically in Story 1.5, Story 8.4 and ADR-007 |
| `EvidenceKind` | Enum: Date / Person / Age / Era / Location | Tagged union discriminator |
| `Evidence` | Sum type `Observation(kind, value, Confidence, Provenance) \| Abstention(plugin, reason)`; immutable | Append-only rows in `evidence` table; an abstention cannot carry a value and an observation cannot abstain (no `abstain: bool`) |
| `Confidence` | Float from 0 to 1, calibrated against anchors, not a raw model score | Newtype; uncalibrated plugins capped by `weight_cap` |
| `Provenance` | plugin name+version, model id, inputs (cluster_id, person_id, age_est), `cost: local|cloud` | Required on every Evidence |
| `AnalysisPlugin` | `typing.Protocol`: `name`, `version`, `requires_cloud`, `scope`, `runtime`, `after`, `analyze(ctx)` | Structural contract (ADR-001) |
| `PluginScope` | Enum: File / Album / Corpus | Corpus plugins (face clustering, calibration) run as passes |
| `PluginRuntime` | Enum: Core / Ml | Core runs inside `cli.py` env; Ml runs in `G/analyze_ml.py` (ADR-004) |
| `PluginRegistry` | Maps plugin name -> lazy `"module:Class"` string, enable flags, DAG order | Imports only enabled plugins |
| `FileContext` | Frozen input to `analyze`: path, `ContentKey`, album context, `ExifSnapshot`, `prior` evidence, config | |
| `ExifSnapshot` | Existing date-related tags read before any write (DateTimeOriginal, CreateDate, ModifyDate, Software, GPS) | Also the journal's old values |
| `FileRecord` | Row in `files`: path, size, mtime_ns, `ContentKey`, album_id, media class | One row per path (duplicates share a `ContentKey`) |
| `Guard` | Named hard constraint that prunes the year axis (`BirthDeathBounds`, FolderYearBounds, Anchor, UploadWindowCeiling, PhysicalPlausibility) | Fired guards recorded in provenance |
| `DateDecision` | Fusion output per file: interval, point, `Confidence`, `DecisionStatus`, voters, guards fired | Derived and recomputable from evidence |
| `DecisionStatus` | Enum of fusion outcomes only: Anchor / Eligible / Review / Conflict / UserOverride | Conflict is never written. Write state is NOT stored here |
| `WriteState` | Enum: NotWritten / Pending / Verified / Mismatch / Reverted, a read-only join over `write_journal` rows (Story 8.6) | The only place write state is expressed; `fuse` can never clobber it |
| `Anchor` | File whose date is trusted (camera EXIF classified `Genuine`, dated filename, owner-pinned album, `UserOverride`) | Fixed point in fusion; calibration truth. Trusted is not the same as on disk: only a `source=exif` anchor already has its date in the file. Filename, owner-album and `UserOverride` anchors get a journaled write from `plan` (Story 8.4) and count as upload-ready only after that write is `Verified` (see `UploadGate`) |
| `OnDiskDate` | The capture date physically present in a file's EXIF (`DateTimeOriginal`) together with its `PlaceholderClass` | `OnDiskDate` is "backed" when it is `Genuine` and equals the decision's Day-precision date; the gate and `plan` both use this one predicate (`write_state.on_disk_backed`, Story 8.6) |
| `BackupAttestation` | `DATA/backup-attestation.json`: a verified second copy of the whole drive on a different physical medium (checksum manifest of every file, verification time, medium id) | Hard precondition for any real `--apply` of Stories 8.4 and 8.7 (Story 8.8); never stored on the source drive |
| `PrewriteSnapshot` | `DATA/prewrite/<run_id>/<ContentKey>.bin`: local copy of a file's bytes taken before its first write in a run | Kept until the run is `Verified` AND the owner runs `prewrite purge`; makes a damaged file recoverable, which tag-only journal rows cannot (Story 8.8) |
| `AnchorCensus` | Read-only count of anchors per decade x color/B&W (and per person once labels exist) from `Genuine` EXIF, dated filenames, owner-pinned albums and `UserOverride`, with a go/no-go verdict | Story 5.6; gates ML spend (4.3, 6.2) |
| `Coverage` | Per album and audit source: `observable` or `unobservable`, plus `baseline_count` (remote items seen before any trash) | `AuditClear` counts "zero surviving copies" only when `observable` and `baseline_count > 0` (Stories 9.3, 9.9) |
| `HoldOut` | Deterministic subset of anchors (hash-seeded) excluded from calibration and used for error reporting | |
| `Person` | Entry in `DATA/people.toml`: name, aliases, birth, death | Owner-supplied, local only |
| `FaceId` | Stable face identity = (`ContentKey`, bbox) | Labels keyed by `FaceId`, never by cluster index |
| `FaceCluster` | HDBSCAN cluster of L2-normalised embeddings; versioned by `cluster_run_id` | Noise (-1) stays unknown |
| `ClusterConstraint` | Owner must-link / cannot-link between `FaceId`s or clusters | Persistent; overrides algorithm on rerun |
| `CalibrationCurve` | Per plugin, per decade, per color/B&W: error sigma and reliability from anchors | Feeds `Confidence` and weight cap |
| `WritePlan` | `plan.jsonl`: intended EXIF writes with old value, new value, confidence, provenance, plan hash | `--apply` consumes it |
| `WriteRun` | One apply invocation, id `run_id` | Unit of `undo` |
| `JournalEntry` | Row in `state.db` `write_journal`: run_id, ContentKey, path, tag, old_value, new_value, status (Pending / Verified / Mismatch / Reverted), plus pre-write `sha256`, size, `mtime_ns`, exiftool version, plan hash and the exact tag-argument list | Committed (and mirrored to `DATA/journals/<run_id>.jsonl`, append-only, fsynced) before the write; captures more than tags so a damaged file is diagnosable |
| `DerivedStore` | `DATA/pipeline.db`: recomputable tables `files, evidence, decisions, faces, clusters, embeddings, anchors, calibration, dup_groups, uploads_observed, audit_runs, run_metrics, schema_version` | Safe to delete and rebuild; rollback may delete it. `analyze_ml.py` writes `evidence, faces, clusters, embeddings, calibration` and `run_metrics` (`holdout_mae`) rows only |
| `StateStore` | `DATA/state.db` plus `DATA/journals/*.jsonl`, `DATA/review/decisions.jsonl`, `DATA/review/ids.jsonl`, `DATA/placeholders.jsonl`, `DATA/placeholders-labels.jsonl` and `DATA/backup-attestation.json`: `write_journal, labels, constraints, anchor_pins, schema_version` | Source of truth for undo records and owner input; never deleted by rollback; backed up to `DATA/backups/` (SQLite backup API, not `cp`) before every `--apply`; only `cli.py` writes it |
| `ReviewItem` | One entry in the review list: source (File / Album / Audit / YearPrecision / Placeholder; exactly these five), candidate interval, voters, guards | One list for per-file decisions and the flagged albums (137 today). Cluster-label items are not `ReviewItem`s; they are `ReviewDecision(kind=cluster_label)` handled through the review-kind handler registry (Story 7.2, 4.5) |
| `ReviewDecision` | Line in `DATA/review/decisions.jsonl`: item (typed id such as `F42`, `A7`, `Y77`, `U310`, `P4021`, `C12`), item_key (the stable key: `ContentKey`, album id, ...), kind (`file`, `album_date`, `cluster_label`, `face_member`, `cluster_link`, `year_precision`, `audit`, `placeholder`, `group`, `remediation`; one snake_case spelling), action (accept / reject / set / skip / done / waive / merge / retract; there is no `split` action, a split is two `face_member` rejects sharing a `batch_id`, and `merge` is one terminal-only `cluster_link` line), value or name, optional `face`/`face_id`/`cluster_run_id`, `import_id`, `group_id` or `batch_id`, `decided_at` (imported lines), ts | Append-only, latest wins, folded by `(kind, item_key)`. A `group` line is the handle of a group decision whose per-file owner records are written when it is applied (never expanded at read time). Meaning of accept/reject/skip per source, whether a reject is terminal or parks the item, and for cluster versus face cards is fixed in ADR-009 and UX S2/S3. Typed aliases are allocated in the append-only `DATA/review/ids.jsonl` |
| `UploadGate` | Predicate: album uploadable iff (1) the album is not on the `DenyList`, (2) a placeholder scan exists and the album has no unscanned or non-`Genuine` dateable file that lacks a resolved decision (Story 1.6 global fail-closed rule, v0 until 9.2), (3) every file is either `WriteState == Verified` or an `Anchor` whose `OnDiskDate` is backed (`source=exif`, `Genuine`, equals the decision); `UserOverride` and filename/owner-album anchors therefore pass only after the Verified write `plan` emits for them, (4) no year-precision file is held, and (5) `AuditClear(album)` holds. Videos are not exempt (decisions + `WriteState` apply to them like any file) | Enforced inside `upload_album_to_gphotos` (Stories 1.6, 9.2), not only in `upload_cmd` |
| `AuditClear` | Predicate: a completed `audit` exists that is newer than the album's last write, lists zero suspicious items for the album, and has `Coverage == observable` for that album; for `generation>=2`, additionally zero surviving remote copies AND `baseline_count > 0` recorded before any trash | Escape hatch `--allow-unaudited`, loud and logged; an `unobservable` album can only proceed through Takeout (Story 9.4) or the typed `--i-verified-trash <album>` (logged, followed by a post-upload duplicate check) |
| `DenyList` | Album ids and normalised folder names never uploaded until explicitly released (`2021 random photos` = id `9102dede1a50`) | Code constant keyed on BOTH id and folder name + `DATA/deny.toml`; `deny release` needs zero Review/Conflict decisions and a typed album id |
| `ObservedRemoteItem` | Row in `uploads_observed`: remote id, filename, remote date, album, source (rclone / takeout / picker), observed_at | Coverage is scoped by source |
| `UploadWindow` | Date range during which uploads happened (from manifest timestamps) | Remote dates inside it for old photos are suspicious |
| `RemediationStrategy` | Protocol: `plan(flagged) -> RemediationWorklist`, `apply()` where the capability exists | Strategies: WebUiWorklist, TrashReupload, UnofficialToolkit (opt-in) |
| `RemediationWorklist` | Ordered per-album list of remote items with target dates and instructions | Done-state recorded as `ReviewDecision(action=done)` |
| `CloudPolicy` | Run-scoped object: `allow_cloud`, sample cap, spend cap, send log | Default deny |
| `DataDir` | Resolved runtime directory (dbs, review, thumbs, journals, backups, models) with 700/600 perms | Outside git |
| `LegacyPaths` | Resolved absolute paths of `album_mapping.json` and `upload_manifest.json` (the latter lives at the repo root, `/home/tstapler/dotfiles/upload_manifest.json`) from env `GPHOTOS_MAPPING` / `GPHOTOS_MANIFEST`, else `DATA/config.toml [paths]`, else repo root derived from `__file__` | Replaces cwd-relative defaults; a missing manifest while the mapping shows uploaded albums is a hard error |
| `RunReport` | Per-run summary row set: counts per plugin, confidence histogram, error by decade, flagged, written, quota events, review burden, remediation counts | |
| `ConfirmationTier` | T0 dry-run, T1 immediate (one item or small write, one-command undo), T1a preview then `--apply`, T1+ explicit override flag (journaled; the refusal or dry-run that precedes it is the preview), T2 typed token for writes and uploads, T3 typed token plus a checked precondition for purges and gate overrides; the token is a count never on the command line (a colliding candidate falls back to the next count, else a clean refusal) and never printed in the prompt | One helper (`pipeline/confirm.py`, Story 1.13); table in UX S12 |

(54 terms.)

---

## Pattern Decisions

**Step 0.5 alternatives considered** (one strength / one weakness each):
1. *Monolithic extension of `cli.py`/`ai_enrich.py`* (add stages inline). Strength: no new structure. Weakness: violates the "add a plugin without editing `cli.py`" metric and perpetuates the per-album, date-blind design.
2. *Adopt Immich/digiKam as backend, import labels*. Strength: polished face review UI. Weakness: a server stack plus schema-coupled import to solve a dating problem they do not solve (research/build-vs-buy.md section 1E).
3. **Chosen: thin in-repo pipeline** (Protocol + lazy registry + SQLite evidence store + pure fusion + journaled writes). Strength: matches uv-script CLI, testable pure core. Weakness: more code to own; mitigated by building only the ~40-line registry and leaning on libraries for models.

| Component | Pattern Chosen | Source | Alternative Rejected | Reason |
|-----------|---------------|--------|---------------------|--------|
| Plugin discovery | Explicit lazy registry + `typing.Protocol` | GoF Strategy / architecture.md s3 | pluggy; entry points; directory scan | Entry points need a package; pluggy ceremony exceeds 3-5 plugins; registry line edit is outside `cli.py` core flow (ADR-001) |
| Pipeline commands | Service Layer (`pipeline/*.py`) behind thin Typer commands | PoEAA (Fowler) | Transaction Script in `cli.py` | Cross-stage invariants (journal-before-write, gate) need one home; `cli.py` stays a shell |
| Persistence | Repository over SQLite (`pipeline/store.py`) + Unit of Work per batch | PoEAA | JSONL files; ORM | Indexed (hash, plugin, version) lookups, crash-safe batches, SQL for reports (ADR-002) |
| Evidence | Immutable value objects, append-only | Event-sourcing-lite | Mutable per-album triple (`inferred_date`/`date_confidence`/`date_source`) | Reproducibility; any plugin removable without redoing others |
| Fusion | Pure functions; Layer A guards (Specification pattern) then Layer B scoring | GoF Strategy/Specification | Single Bayesian product | Guards must never be overridable; naive product double-counts correlated plugins (ADR-003) |
| `DateDecision.status` | Sum type (enum + exhaustive `match`), fusion outcomes only; `WriteState` is a join over the journal | type-driven-design | string flags; persisting `Written`/`Reverted` on `decisions` | Exhaustive handling; kills free-form `metadata_status` strings (B10); one source of truth for write state |
| `ContentKey`, `FaceId`, `Confidence`, `PartialDate`, `Evidence` | Newtypes / value objects; `PartialDate` constructor-only (derives bounds from precision); `Evidence = Observation \| Abstention` | type-driven-design | raw str/float/datetime; `abstain: bool` + nullable value | Prevent mixing ids; illegal states (Day precision with a multi-year interval, abstain with a value) are unconstructible |
| Persistence boundary | Two stores: `pipeline.db` (derived) and `state.db` + JSONL (source of truth) | Aggregate-boundary split (ADR-002) | One SQLite file for everything | Rollback and rebuilds may discard derived data; undo records and owner labels must survive |
| EXIF writes | Command + Memento (journal) with plan/apply split | GoF Command/Memento | in-place `-overwrite_original` | Reversibility requirement (ADR-007) |
| Legacy `ai_enrich` | Adapter / Anti-corruption seam | GoF Adapter | Rewrite in place | Hardcoded family-event data stays callable until parity shown |
| `uploader.py` | Decorator-style gate predicate beside unchanged `_run_rclone` | GoF Decorator | Edit rclone loop | Quota handling is sound and recent |
| Remediation | Strategy | GoF | One hardwired path | Capability is unknown/partial; strategies swap by what Google allows (ADR-008) |
| Review state | Append-only log, latest-wins fold | Event log | Mutating `album_mapping.json` | History, reversibility, resumability (ADR-009) |
| Cloud access | `CloudPolicy` passed explicitly (Capability object) | Least privilege | Global flag read ad hoc | A plugin cannot reach the network without receiving the policy |
| Heavy ML | Separate PEP 723 script sharing the SQLite schema | Process boundary | `uv run --with` per call | Pinned Python 3.12, `cli.py` stays light (ADR-004) |

---

## Tech Debt Disposition

| Area | Existing Issue | Disposition | Justification |
|------|----------------|--------------|----------------|
| `G/metadata.py` (209 lines) | One 110-line function fuses date synthesis, tags, GPS, exiftool I/O, `-overwrite_original` (`metadata.py:105,159-160`); failed chunk counted as success (`:196-200`); writes whatever date it is handed unconditionally (`:171`; the placeholder values originate in `ai_enrich.py:31,85` and `scanner.py:68`); tag-by-substring (`"chris"` matches "christmas", `:80`) | **Refactor-first** (Story 8.1 before 8.3/8.4; interim safety fixes in 1.3, 1.5; destructive `--apply` locked off by 1.11 until 8.4 lands) | A journal cannot be bolted onto a function that decides and writes in one pass; split into `plan_writes` (pure) and `apply` (journaled) |
| `G/ai_enrich.py` (117 lines) | Hardcoded family-event dates (`:36-45`), `YYYY:01:01` placeholders (`:31,85`), in-place mutation of `AlbumMapping` | **Isolate via seam** (Story 3.3 `plugins/event.py` adapter) with a **removal criterion**: delete `ai_enrich.enrich_mapping_data` and `infer_cmd` (Task 10.5c) once `fuse` decides album dates (2.8) and album review items flow through `review` (7.2); a test fails if either is still imported after that point | The adapter must not become permanent; heuristics are data; wrap as plugins, keep `infer` callable only until then |
| `G/uploader.py` (136 lines) | Date-blind, album-granular upload; manifest success = rclone exit 0 (`:113-129`); non-atomic manifest write `save_manifest` (`:78-80`) | **Isolate via seam** (Story 1.6 / 9.2 `pipeline/upload_gate.py`; atomic write in 1.2) | rclone copy and `QuotaExceeded` are sound; do not edit `_run_rclone`. The quota wait-and-retry loop and `ok` live in `cli.py` `upload_cmd` (about lines 415-431), not here: Story 1.8 extracts it to `pipeline/quota_retry.py` |
| `G/cli.py` (496 lines) | Inline stages; non-atomic `album_mapping.json` writes (`:85,274,357,435`); statuses set by hand (`:354,432`); measured command bodies over 40 lines today: `upload_cmd` 73, `review_cmd` 63, `fix_metadata_cmd` 59, `scan_cmd` 55, `update_album_cmd` 54, `infer_cmd` 43 | **Shell it** (Story 1.11): `cli.py` becomes a registration shell that auto-discovers `G/cli_*.py` Typer sub-apps; the four commands touched by later stories (`upload_cmd`, `fix_metadata_cmd`, `update_album_cmd`, `scan_cmd`) have their bodies extracted to `pipeline/*_service.py`; `review_cmd` and `infer_cmd` are grandfathered | About 25 new commands must not land in the hotspot. Each new story adds its own `G/cli_<area>.py` (no shared-file collisions). The 40-line body guard applies to NEW commands only, with a ratchet baseline that lets existing bodies shrink but never grow (Story 1.11, enforced in 10.5) |
| `G/scanner.py` (261 lines) | Year range collapses to Jan 1 (`:33-93`, placeholder produced at `:62-70`/`:68`); `parse_date_and_location` returns point dates; extension sets disagree with `metadata.py:18-19` | **Extend as-is** after Story 1.4 swaps its date parsing for `dateparse.py`; extension sets unified in `media_types.py` (1.5) | Album enumeration is correct; only the date value changes |
| `G/models.py` (64 lines) | Free-form `metadata_status`/`upload_status` strings (`:37-38`) | **Extend as-is** (field-compatible additions, Story 1.7) | Existing JSON must still load |
| `G/report.py` (68 lines) | Album-level only | **Extend as-is** (Story 10.1) | Additive sections |
| Repo-level `Makefile` | `ready` runs llm-sync and pyinfra tests only | **Extend as-is** (Story 1.1 adds `gphotos-test` to `ready`) | Same pattern as `llm-sync-test` |

---

**Defect trace (`research/pitfalls.md` section 1, B1 to B11 by ID).** B1 and B4: Stories 8.1/8.4 (B4's argfile semantics are pinned by Story 1.3 first; the `-overwrite_original` flag is deleted by 8.4 with a grep test). B2: Stories 1.3 and 1.11. B3 (writes `DateTimeOriginal` unconditionally; real camera dates may be overwritten): Stories 3.4 and 8.4 (a backed real EXIF date is never overwritten; existing `Genuine` EXIF is the strongest anchor). B5: Story 1.5. B6, B7 and B10: Stories 1.7 and 8.6 (statuses), with B7 also in 9.2 (manifest records more than rclone exit 0). B8: Stories 1.6 and 9.2. B9: Story 1.8. B11: Story 1.2.

## Migration Plan

- **Persistence boundaries (the rule everything below follows)**:

  | Store | Tables / files | Class | Rollback may delete? |
  |---|---|---|---|
  | `DATA/pipeline.db` (`DerivedStore`, WAL) | `files, evidence, decisions, faces, clusters, embeddings, anchors, calibration, dup_groups, uploads_observed, audit_runs, run_metrics, schema_version` | DERIVED: recomputable from the drive, plugins and `state.db` | Yes |
  | `DATA/state.db` (`StateStore`, WAL) | `write_journal, labels, constraints, anchor_pins, schema_version` | SOURCE OF TRUTH: undo records and owner input | NEVER |
  | `DATA/placeholders.jsonl` | append-only, latest-wins placeholder classifications and owner `confirm-genuine` records (Story 1.9) | SOURCE OF TRUTH (owner input; written before `state.db` exists) | NEVER |
  | `DATA/journals/<run_id>.jsonl` | append-only, fsynced mirror of every `write_journal` row (and of label/constraint/anchor-pin changes as `state-events.jsonl`) | SOURCE OF TRUTH (survives a corrupted `state.db`) | NEVER |
  | `DATA/review/decisions.jsonl` | append-only review decisions | SOURCE OF TRUTH | NEVER |
  | `DATA/review/ids.jsonl` | append-only typed item aliases (`F42` to stable key) | SOURCE OF TRUTH (rebuildable from the log) | NEVER |
  | `DATA/backups/state-<ts>.db` | consistent copy of `state.db` taken before every `--apply` with the SQLite backup API (`sqlite3.Connection.backup`) or `VACUUM INTO`, never `cp` of a live WAL database (a plain copy can be inconsistent) | backup | NEVER |
  | `DATA/backup-attestation.json`, `DATA/placeholders-labels.jsonl` | drive-backup attestation (Story 8.8) and owner precision-sample labels (Story 1.9) | SOURCE OF TRUTH (owner evidence) | NEVER |
  | `DATA/prewrite/<run_id>/` | local pre-write byte snapshots (`PrewriteSnapshot`, Story 8.8) | working data, large | only by `prewrite purge` after the run is `Verified` |
  | `album_mapping.json`, `upload_manifest.json` | legacy state; paths resolved by `LegacyPaths` (the manifest lives at the REPO ROOT `/home/tstapler/dotfiles/upload_manifest.json`, not in `G/`; both are gitignored, `.gitignore` lines 382-385); only the writers change to temp-file + `os.replace` | legacy source of truth | NEVER (restore via `.premigrate`) |

  Single-writer rule: only `cli.py` writes `state.db`. `analyze_ml.py` writes only its own `evidence, faces, clusters, embeddings, calibration` rows and `run_metrics` rows (`holdout_mae`, Story 6.3) in `pipeline.db` and opens `state.db` read-only (labels and constraints are read, never written, by the cluster pass). Both processes set `PRAGMA busy_timeout` and retry on `SQLITE_BUSY`; one `analyze` at a time via `DATA/analyze.lock` (`flock`).
- **Migrations are per epic, forward-only, additive, independent**, named by owning story (`G/pipeline/migrations/pipeline/sNNNN_<name>.sql`, `G/pipeline/migrations/state/sNNNN_<name>.sql`, `NNNN` = zero-padded story number), applied in name order and recorded by name in `schema_version` (a set of applied names, so stories landing in different waves never fight over a shared counter). Story 2.2 ships `pipeline/s0202_initial` (`files, evidence, decisions, schema_version`) and `state/s0202_initial` (`schema_version` only); later stories ship their own: 8.3 `state/s0803_write_journal`, 4.4 `state/s0404_labels_constraints`, 5.2 `state/s0502_anchor_pins` and `pipeline/s0502_anchors`, 5.3 `pipeline/s0503_calibration`, 4.3 `pipeline/s0403_faces`, 4.4 `pipeline/s0404_clusters`, 6.1 `pipeline/s0601_dup_groups`, 6.2 `pipeline/s0602_embeddings`, 9.3 `pipeline/s0903_uploads_observed`, 9.9 `pipeline/s0909_audit_runs`, 10.2 `pipeline/s1002_run_metrics`. The ML script refuses to start when either store's applied-migration set differs from the set the code expects.
- **Status vocabulary migration** (Story 1.7, reconciled with Story 8.6): the stored legacy `metadata_status` keeps only `pending | legacy_unverified | skipped`; the loader maps every old value (`models.py:37` documents `verified, pending_fix, fixed, skipped`, and the file today holds only `pending`): `pending` -> `pending`, `pending_fix` -> `pending`, `fixed` -> `legacy_unverified`, `verified` -> `legacy_unverified` (the legacy writer never read anything back, so the word `verified` is reserved for journal read-back), `skipped` -> `skipped`, any unknown value -> `pending` with a logged warning. Story 8.6 then derives the shown status from the journal: `not_written | pending | verified | mismatch | reverted` (an album with no journal rows falls back to its stored value: `pending` shows as `not_written`). There is no stored `written` state. Manifest-completed albums -> `uploaded_unverified`. Old files load unchanged; first save writes the new vocabulary. A pre-migration copy `album_mapping.json.premigrate` is written once (targeting the resolved `LegacyPaths`, so running from another directory cannot copy or load the wrong file).
- **Reversibility**: DB migrations are additive (new tables). Rollback may delete `DATA/pipeline.db` ONLY; it never touches `state.db`, `journals/`, `review/`, `backups/` or the legacy JSON. JSON vocabulary migration is reversible via `.premigrate`.
- **Zero-downtime**: single-operator CLI; the background upload loop only writes `upload_manifest.json`, so Story 1.2 keeps its schema and adds only atomicity. Do not edit `uploader.py`'s manifest schema while that loop runs.
- **Rollback procedure**: `git revert` the PR. To reset derived data: `undo` any wanted runs first, confirm `DATA/backups/state-<ts>.db` exists, then delete `DATA/pipeline.db` only (and rerun `index`). Restore `.premigrate` copies if the JSON vocabulary change must be undone. EXIF writes roll back with `undo --run <id>` (Story 8.5), not git. Acceptance tests in Stories 4.5 and 8.3 prove that deleting `pipeline.db` leaves undo and labels intact.

## Observability Plan

- **Logs**: loguru (existing) with a `run_id` bound per invocation and a JSONL sink at `DATA/logs/run-<run_id>.jsonl`; entry/exit lines at each stage boundary (`index`, `analyze`, `fuse`, `plan`, `apply`, `audit`, `upload`); every error path logs error + `ContentKey`/album id; paths are logged, person names are not (Story 10.2, 10.4).
- **Metrics** (rows in `run_metrics(run_id, name, labels_json, value)`; rendered by `report`): `plugin_files_total{plugin,cached|computed|abstain|error}`, `plugin_seconds{plugin}` (one per operation over 100 ms: face detect, embed, OCR, regression, cloud call), `confidence_histogram{plugin}`, `anchor_error_years{plugin,decade,color}` (median/p90 on `HoldOut`), `decisions_total{status}`, `guards_fired{guard}`, `exif_written_total{verified|mismatch}`, `quota_events_total`, `metric1_violations{bounded}` / `metric1_unbounded` (from the audit, Story 9.9), review burden and remediation counts computed at report time (Story 10.1c: open per source, decided per action, auto-dated vs reviewed, fixed/waived/open), `cloud_calls_total{plugin}` and `cloud_bytes_sent`, `audit_flagged_total`.
- **Alerts**: no pager. End-of-run warnings printed in the summary panel and nonzero exit when: any `mismatch` journal rows, any leftover `_exiftool_tmp`/`_original`, `cloud_calls_total > 0` (always listed), or calibration reliability below threshold for a plugin that voted.
- **Per-run report** (requirements Observability): Story 10.1 renders it as markdown to `DATA/reports/`, names redacted by default.
- **Deviation from requirements**: requirements ask for results cached "beside the manifest"; this plan keeps everything under `DATA/` (outside git, mode 600/700) because face embeddings are biometric-adjacent and the manifest lives in the dotfiles tree (data residency NFR). Recorded here as a deliberate deviation.

## Risk Control

- **Dry-run default**: every mutating command (`fix-metadata`, `upload`, `review import`, remediation `apply`) requires `--apply`; the plan is a file and `--apply` consumes it (stale plan refused).
- **Legacy destructive path locked (Story 1.11)**: until Story 8.4 lands, `fix-metadata --apply` exits 1 with the next command (the legacy writer uses `-overwrite_original` with no journal; the 9,460 Jan-1 files and thousands of 12:00:SS-signature files show it has probably already done damage). Dry-run still works. 8.4 replaces the lock with the journaled plan/apply path.
- **Journaled reversible writes**: journal row committed (to `state.db` and the JSONL mirror) before each exiftool write; read-back after; `undo --run <id>` (ADR-007). No `-overwrite_original`. Journal rows survive `pipeline.db` deletion. Before each `--apply`, `state.db` is backed up to `DATA/backups/` with the SQLite backup API (not `cp`). On exFAT (fstype `exfat|vfat|fuseblk`, detected from `/proc/self/mountinfo`) `--workdir` is mandatory: in-place writes are refused.
- **Per-plugin enable flags**: `DATA/config.toml` `[plugins.<name>] enabled=false` by default for ML/cloud plugins; `--plugins a,b` per run; a failed model download disables only that plugin.
- **`--allow-cloud`**: off by default; a plugin with `requires_cloud=True` is not even imported without it; `CloudPolicy` carries sample cap and spend cap; every send is logged to `DATA/logs/cloud-send.jsonl` (ADR-005).
- **Confidence threshold** (`--min-confidence`, default 0.8): gates all writes; conflicts never written.
- **Irreversible-write protection (pre-mortem failure mode 1)**: the journal restores tags, not damaged files, and the drive (`/dev/sda1`, 58G, 54G used, 4.0G free per `df -h` on 2026-10-16) may be the only copy and has no room for a same-drive backup. Therefore no real `--apply` (Story 8.4) or `placeholders revert --apply` (Story 8.7) runs until all of these hold, enforced in code by Story 8.8 and the 8.4 preflight: (1) a verified full-drive backup on a DIFFERENT physical medium (`BackupAttestation`, Owner Checklist item 4); (2) a 20-file canary apply on a copy of real files passed; (3) `fsck.exfat -n` on the unmounted drive clean before the first apply and after every N albums; (4) one album per mount-sync-verify cycle; (5) local `PrewriteSnapshot` bytes per file, with a free-space check on the local filesystem that refuses a run whose byte total does not fit; (6) the journal-backup step uses the SQLite backup API.
- **Upload gate**: deny list in code (keyed on album id `9102dede1a50` AND folder name, checked inside `upload_album_to_gphotos` so no caller bypasses it) + a global fail-closed rule (Story 1.6: no album with any `LegacyPlaceholder`, `Suspect` or unscanned dateable file uploads until 9.2; before the 1.9 scan has run, all uploads are refused with `Blocked: placeholder scan not run`) + decisions-based predicate (an `Anchor` passes only with a backed on-disk date, otherwise only after a `Verified` write) + `AuditClear(album)` requiring positive observability; "upload only after audit passes" is implemented in Story 9.2, not just stated here.
- **Decision: the legacy upload loop is stopped, not planned around.** `ps` on 2026-10-16 showed an outside loop invoking old `cli.py upload ... --album-id <id>` processes; old code in memory ignores any new gate, each new process loads whatever is on disk at that moment (a half-merged wave could crash it or write the old vocabulary into the manifest), and 23 small albums (about 227 files; 17,145 - 7,757 - 9,161 = 227) are not worth the wrong-dated pollution. The owner stops the loop before Story 1.1 starts (Owner Checklist item 1) and leaves it stopped until Story 9.2 lands. Belt and braces: Story 1.2 merges first, and `upload_manifest.json` stays schema-compatible with old readers until the loop is confirmed dead. Recorded decision on the pre-seed alternative (a fake completed entry for id `9102dede1a50`, which the old `upload_cmd` skips via `manifest.completed_albums`): still declined, because it writes a false record that Story 1.7 would map to `uploaded_unverified` and that the audit (9.9) would treat as uploaded; revisit only if the owner cannot confirm the loop is stopped.
- **Client retirement and quota error handling (Story 1.8)**: rclone's shared client_id is "being retired in 2026" (research/stack.md s6) and today is 2026-10-16, so error text is classified, not scanned loosely: only HTTP 429 or known quota strings cause a sleep; text that mentions "quota" without them is a hard failure; `invalid_client` / client-retired / 403 maps to a specific message and never sleeps.
- **Public-repo privacy**: PR evidence, logs and report files follow the privacy rule in the plan header (counts and album ids only, names redacted); `--data-dir` or `GPHOTOS_*` resolving inside a git work tree or a synced folder is a hard error (Story 10.4).
- **Unofficial Google tooling**: opt-in flag AND env confirmation, banner label, never automatic (ADR-008).
- **Feature flag / staging**: not a deployed service; staged rollout = run the whole pipeline in dry-run on the 200-image spike sample (4.1) and the e2e fixture corpus (10.5) before any `--apply` on the real drive.
- **Rollback**: `undo --run`, then delete `pipeline.db` only (never `state.db`, `journals/`, `review/`, `backups/`), `git revert`.

## Test Strategy

- **Style**: plain `test_*.py` functions run by `uv run test_x.py`, sharing `G/tests/_test_runner.py` (a copy of `stapler-scripts/llm-sync/_test_runner.py`: `run_tests(globals())` in `__main__`); no pytest. Makefile target `gphotos-test` mirrors `llm-sync-test` (`Makefile:40-41`) and joins `ready`.
- **Golden-file tests**: `G/tests/golden/dateparse.json` (folder/filename strings -> `PartialDate`), `G/tests/golden/fusion/*.json` (evidence + guards + people -> `DateDecision`), `G/tests/golden/enrich_parity.json` (legacy `enrich_mapping_data` outputs ONLY; it pins legacy behavior, not plugin behavior), `G/tests/golden/event_plugin.json` (the `event` plugin's intentionally different outputs, so plugin drift is reviewable), `G/tests/golden/placeholder_detector.json` (classification cases). Regenerate only with an explicit `--update-golden` flag; a diff in review is the signal.
- **Determinism**: synthetic embeddings (seeded numpy-free lists or small fixtures) for clustering/age/era tests, never real model weights; model-dependent checks live only in spikes and the e2e smoke (10.5).
- **Fakes**: fake `exiftool` and fake `rclone` executables (`G/tests/fakes/`) selected via `GPHOTOS_EXIFTOOL` / `GPHOTOS_RCLONE` env vars; real exiftool (13.55 present) used for round-trip tests on generated fixture files.
- **Property checks**: fusion is pure -> assert idempotence, monotonicity (adding an abstain changes nothing), and that no Layer B result lies outside Layer A's surviving years.
- **Run proof**: each story's done-criterion includes the test command output pasted in the PR (repo rule: no completion claim without proof).

## Pre-implementation Owner Checklist
*(Manual gates; each must be done by Tyler and its evidence pasted into the PR of the named story before that story starts.)*
- [ ] **1. STOP the legacy upload loop (before Story 1.1) and keep it stopped until Story 9.2 lands.** Run `ps -ef | grep '[c]li.py upload'`. If a loop is running, stop it (kill the driving shell and its `cli.py upload` child); do not merely check its album list. Re-run the same `ps` command and paste the output showing no process into the Story 1.1 and 1.6 PR descriptions (processes only, no album names). The code gate (Story 1.6) cannot stop an already-running old process, and a loop left running while waves merge can crash or write the old vocabulary into the manifest.
- [ ] **2. No legacy `fix-metadata --apply` (before Story 1.11 merges).** Do not run it; the code lock lands in W2.
- [ ] **3. Drive mounted for Stories 1.9, 1.10, 2.4, 4.1 (real runs).**
- [ ] **4. Verified full-drive backup on a DIFFERENT physical medium (before the first real `fix-metadata --apply` of Story 8.4 or `placeholders revert --apply` of Story 8.7).** The drive is 58G with 54G used and 4.0G free, so a same-drive backup is impossible. Make a checksummed copy (rsync with `--checksum` or `sha256` manifest of all 17,255 files stored in `DATA`) on another disk; run `backup verify` (Story 8.8) so `DATA/backup-attestation.json` exists; paste the counts (files, bytes, mismatches = 0) into the PR. Also supply a throwaway USB stick for the exFAT yank spike (Task 1.10c).
- [ ] **5. Decide where the planning artifacts live before the first `git add` of `project_plans/gphotos-organizer-pipeline/`** (still untracked). The repo `github.com/tstapler/dotfiles` is public and these documents contain real album and person names. Choose one: keep them untracked or in the private experimental repo (`experimental_dir`), or commit a redacted copy. Record the choice in the Story 10.4 PR.
- [ ] **6. Before Story 5.6 (anchor census):** provide the list of albums you trust as date anchors (Unresolved Question 3) and the labeled precision sample for Story 1.9 (50 files per class and signal combination); accept or change the go/no-go minimums stated in Story 5.6.
- [ ] **7. Before Story 9.6 pilot:** create the throwaway album and the own Google OAuth client; the real 9.6 run waits for the pilot result.
- [ ] **8. Cost decision gates (after W5 and after W9):** read the published actual-vs-estimate report and reply `continue` or name what to change; the next wave does not start without the reply (see Effort estimate, Overrun checkpoint).
- [ ] **9. Confirm the accuracy and review-burden targets after their baselines** (Success Metrics 2 and 6): after the first held-out run (Story 5.5, W12) set `[targets]` in `DATA/config.toml` (median years for children and adults); after the first `fuse` following the census (Story 5.6) set the maximum open review items and the minimum auto-dated share. Until then both are report-only.
- [ ] **10. Run the Story 7.5 usability pass** (W5; about one sitting) and accept or change its thresholds (25 s per cluster label, 15 s per file item, 2 mode switches per 10 labels) before Stories 7.2 and 7.3 start.
- [ ] **11. Before the first real `fix-metadata --apply` of Story 8.4, and again at each fsck boundary: unmount the family drive and have root available.** `fsck.exfat -n` reads the block device and needs it unmounted; `backup fsck` runs it through `sudo` on a TTY (you type the password; the tool never sees it) or reads output you captured with `--from-output`. The check on the 54G drive takes a drive-dependent time (UNVERIFIED; record it in the Story 8.8 PR) and each periodic boundary of an apply run pauses the run (exit 0 with a resume line) until you have run it and remounted. Paste the exit status and counts only into the Story 8.8 PR.

**Owner inputs in the order the plan needs them** (a wave is a dependency level, not a calendar; "start by" means before that wave's first story begins its owner step; the table sequences Tyler's sittings so none of them is discovered late):

| Order | Owner input | Can start after | Needed by (blocks) | Why this order |
|---|---|---|---|---|
| 1 | Stop the legacy upload loop (item 1) | now | before W1 (Story 1.1) | an old process ignores every gate |
| 2 | Decide where planning artifacts live (item 5) | now | before the first `git add` | public repo |
| 3 | Second-medium backup and checksummed copy (item 4); a throwaway USB stick (Task 1.10c) | now (long copy time) | before 8.4 `--apply` and 8.7 `--apply`; USB before 1.10c (W3) | copy time is the longest wall-clock item; start it first |
| 4 | Drive mounted for real scans (item 3) | now | W3 (1.9, 1.10) | real-drive counts |
| 5 | Labeled precision sample, 50 files per class and signal combination (Story 1.9e) | 1.9 done (W3) | 5.6 GO needs the precision gate passed (W6); 8.7 `--apply` (W11) | the census verdict cannot be GO without it, so label during W4-W5, not when 5.6 starts |
| 6 | Trusted-album list and the 200-file slice dated by eye; accept or change the GO minimums (item 6) | 3.2, 3.4 done (W5) | Story 5.6 (W6) | feeds the ML go/no-go |
| 7 | Run the usability pass (item 10) | 7.5 built (W5) | Stories 7.2, 7.3 (W8, W10) | cheap to change criteria before they are built |
| 8 | Birth and death dates for `people.toml` | any time | Story 4.5 owner step (W9); 4.6, 5.4 later | dates cost minutes; do them early so labeling on real data is not blocked |
| 9 | Cluster labeling on real clusters | 7.3 sheets exist (W10) | Story 4.6 real data, 5.4 real run | needs the index and sheets |
| 10 | Cost gate replies (item 8) | end of W5, end of W9 | W6 start, W10 start | owner decision point |
| 11 | Own Google OAuth client; throwaway album (items 7) | any time | 9.1 parts 3-5 (W2 spike), 9.6 pilot (W12) | 9.1 results shape the audit strategy early |
| 12 | Confirm accuracy and review-burden targets (item 9) | 5.5 baseline (W12) | none (report-only until set) | baseline first |
| 13 | Unmount the drive and run fsck with root (item 11) | 8.8 built (W4) and the second-medium backup verified | 8.4 `--apply` (W9), then every fsck boundary | do it in the same sitting as the backup verification, while the drive is already out of normal use |


## Unresolved Questions
*(All OWNER-dependent; none blocks the start of implementation. Each must be resolved before the named story starts its owner-input step.)*
- [ ] Birth (and death) dates of family members for `people.toml` — blocks Story 4.5 owner step, 4.6, 5.4 — owner: Tyler
- [ ] Labeling of face clusters (names for clusters, merges) — blocks Story 4.6 acceptance on real data, 5.2 anchor identity — owner: Tyler
- [ ] Which albums are trustworthy anchors (pin/exclude list) — blocks Story 5.2 real calibration, 5.3 — owner: Tyler
- [ ] Whether to enable the Claude-vision cloud plugin on an uncertain subset (cost estimate $4-$40 is UNVERIFIED pricing; recheck at `platform.claude.com`) — blocks Story 6.4 real run only (code ships disabled) — owner: Tyler
- [ ] Create an own Google Cloud OAuth client for rclone/Library API (shared rclone client_id is "being retired in 2026", research/stack.md s6) — blocks Story 9.1 parts (3)-(5) — owner: Tyler
- [ ] Whether to run the optional unofficial Google-Photos-Toolkit strategy at all (ToS/breakage risk) — blocks Story 9.7 real use only — owner: Tyler
- [ ] Whether the flagged albums (137 today; 138 is the stored counter, 132 in earlier docs) merge into the single review list: plan assumes **yes** (`source=album`); owner may veto — blocks Story 7.2 — owner: Tyler
- [ ] `YearPrecisionPolicy` rule 3 (write a marked mid-period noon date for owner-released albums so Google Photos places them on the timeline): plan assumes **allowed only per album with `--allow-year-precision`**; owner may veto, in which case year-precision files stay un-uploaded — blocks Story 8.4 rule-3 task only — owner: Tyler
- [ ] Legacy placeholder handling: plan assumes **quarantine first** (Story 1.9, classification only) and a separate owner-run journaled revert (Story 8.7) that removes fabricated tags, only after the measured precision gate (>= 0.98 on a labeled sample) and the drive backup; owner may choose quarantine-only — blocks Story 8.7 `--apply` only — owner: Tyler
- [ ] Labeling of the 50-file precision sample per class and signal combination (Story 1.9) — blocks Story 8.7 `--apply` and the real anchor build in 5.2/5.6 — owner: Tyler
- [ ] Videos: plan decides they are OUT of scope for placeholder detection and revert (Story 1.9, N3); extending to QuickTime tags is a separate story if the owner reverses this — owner: Tyler

Spike-resolved unknowns (not owner questions): CPU time for 17k images (4.1); whether `edit.appcreateddata` allows date edits and whether `rclone lsjson` dates match EXIF at scale (9.1); whether rclone's shared client_id still works (9.1); `ImageDataMD5` stability across writes per format (2.2); whether `gpmc` can edit dates (9.8).

## Dependency Visualization

Waves below are derived by topological sort over the dependency lists in this section (script committed at `implementation/waves.py`, run `python3 implementation/waves.py --check`; its `DEPS` table is the authoritative edge list and `--check` fails if a story's `**Depends on**` line names an edge the table lacks; rule: a story's wave = 1 + the maximum wave of its dependencies), then checked so that **no two stories in the same wave edit the same file**. Shared hotspots are therefore serialized by dependency: `cli.py` is edited only by 1.1 (PEP 723 block), 1.11 and 10.5 (W13, `drop infer_cmd only`, serialized after both; every other story adds its own `G/cli_<area>.py`, auto-discovered); `models.py` by 1.4 -> 1.5 -> 1.7 -> 8.6; `metadata.py` by 1.3 -> 1.5 -> 8.1 -> 8.4; `uploader.py`/`upload_service.py` by 1.2 -> 1.6 -> 1.8 -> 9.2 -> 9.6; `fix_metadata_service.py` by 1.2 -> 1.3 -> 1.5 -> 8.4 -> 8.6; `fusion.py` by 2.6 -> 2.7; `cloud_policy.py` by 2.3 -> 6.4; `report.py` by 10.1 -> 5.5; `report_html.py` by 7.3 -> 7.4 (Story 7.6 renders placeholder sheets from its own `report_html_groups.py`); `journal.py` by 8.3 -> 8.5; `ai_enrich.py` by 1.2 -> 1.5 -> 3.3 -> 10.5; `cli_write.py` by 1.10 -> 8.3 -> 8.4 -> 8.5; `cli_audit.py` by 9.3 -> 9.4 -> 9.9 -> 9.5; `cli_stages.py` by 2.4 -> 2.5 -> 2.8; `ADR-008` by 9.1 -> 9.8; `cli_placeholders.py` by 1.9 -> 8.7; `ml_dispatch.py` by 4.2 -> 2.5; `cli_legacy.py` by 1.11 -> 10.5 (later stories only shadow it, never edit it); `cli_report.py` by 10.1 -> 5.5; `cli_review_cluster.py` by 4.5 -> 7.3 -> 7.6; `pipeline/cli_loader.py` by 1.11 -> 1.12; `Makefile` by 1.1 -> 1.14; `ADR-009` by 7.5 only; `pipeline/confirm.py`, `labels.py` and `explain_topics.py` by 1.13 only (other stories call them, never edit them); `pipeline/review.py` by 7.2 -> 7.4; `placeholder-scan-summary.json` is written by 1.9 and only read by 1.6; `cli_backup.py` and the `drive_backup`/`prewrite_store` modules by 8.8 only (8.4 and 8.7 call them); `ADR-007` by 1.10 only; `fuse_service.py` by 2.8 only; `pipeline/status.py` is owned solely by 10.3 (8.6 owns `pipeline/write_state.py`).

```
E1 Foundation
 1.1 harness+tools+fakes+LegacyPaths ─┬─> 1.13 confirmation tiers + labels + reverse map ─> 1.6, 7.4, 8.4, 8.5, 8.8, 10.3 (and 7.6)
                                      ├─> 1.14 wave gate (also needs 1.11)
                                      ├─> 1.11 CLI shell + legacy-apply lock ─┬─> 1.12 help panels, completion, alias notices
                                      │                                       ├─> 1.2 atomic IO ─┬─> 1.3 exiftool failure acct ─> 1.5 no placeholders ─> 1.7 truthful status
                                      │                                       │                  └─> 1.6 global fail-closed gate v0 (needs 1.9's scan summary) ─> 1.8 quota retry seam
                                      │                                       ├─> 1.9 placeholder detector (needs 1.4)
                                      │                                       └─> 7.1 decisions log (needs 1.2)
                                      ├─> 1.4 dateparse ─> 1.5, 1.9, 2.1, 3.1, 3.2
                                      └─> 1.10 leftover finder + minimal recover (also needs 1.11: `cli_write.py` registers through the loader) ─> 2.4 ; 1.2 + 1.10 ─> 8.8 backup attestation/canary/fsck/prewrite ─> 8.4
E2 Core
 2.1 contract(needs 1.4) ─┬─> 2.2 two stores+ContentKey ─┬─> 2.4 index(needs 1.10) ─> 2.5 analyze runner(needs 2.3, 4.2 for ML_CMD) ─┐
                          ├─> 2.3 registry ──────────────┘                                                          │
                          └─> 2.6 guards ─> 2.7 scoring ─────────────────────────────────────────────────────────────┴─> 2.8 fuse cmd (also needs 7.1 for the decisions.jsonl fold)
E3 plugins:  3.1 folder_year, 3.2 filename_date (need 1.4,2.1,2.3) ; 3.4 exif_anchor (needs 1.9,2.3) ; 3.3 ai_enrich seam (needs 1.5,2.3) ; 3.5 OCR (needs 4.2,2.3)
SPIKES (early, parallel): 4.1 CPU timing ; 9.1 Google Photos capabilities ; 9.8 gpmc (after 9.1: same ADR)
E4 faces:  4.1 + 4.2 ML scaffold(needs 2.2; defines ML_CMD) + 5.6 anchor census GO verdict ─> 4.3 faces ─> 4.4 cluster(+labels/constraints state) ─> 4.5 people+labels(needs 7.1, 7.2) ─> 4.6 identity ; 4.3 ─> 4.7 fallback
E5 age:    4.3 ─> 5.1 age ; 3.4+3.2+1.9+7.1 ─> 5.6 anchor census (go/no-go before 4.3, 6.2) ; 3.4+3.2 ─> 5.2 anchors ─> 5.3 calibration(needs 5.1) ─> 5.4 age evidence(needs 4.6) ─> 5.5 holdout report(needs 2.8)
E6 era:    6.1 print_cues + dup_group (core; no dependency on fuse) ; 4.2 + 5.6 ─> 6.2 embeddings ─> 6.3 regressor (needs 5.3) ; 6.4 cloud (needs 2.5,4.2)
E7 review: 7.1 decisions ─> 7.5 usability spike (needs 1.11) ─> 7.2 terminal review (needs 2.8, 1.9 for Suspect items) ─> 7.3 HTML (needs 4.4,4.5,7.5) ─> 7.4 export/import (needs 1.13) ─> 7.6 group decisions + placeholder sheets (needs 7.2, 7.3, 7.4, 1.9, 1.13)
E8 write:  1.5 ─> 8.1 split metadata ─> 8.2 reader (needs 1.9) ─> 8.3 journal+state.db (needs 2.2) ─> 8.4 plan/apply (needs 2.8,7.2,8.8) ─> 8.5 undo, 8.6 derived status ; 8.4 + 8.5 + 1.9 ─> 8.7 placeholder revert (W11)
E9 upload: 9.1 spike ─> 9.3 rclone audit enumerate (needs 1.8,1.9,2.2) ─> 9.4 Takeout ─> 9.9 audit join+AuditClear (needs 2.8,7.2) ─> 9.2 gate v1 (needs 8.4,8.6,1.6,1.7) ; 9.9 ─> 9.5 strategy iface ─> 9.7 toolkit ; 9.5+9.2+9.1 ─> 9.6 trash+reupload (pilot first)
E10: 2.5 ─> 10.2 logs+metrics ─> 10.1 report (needs 2.8) ; 10.3 status (needs 8.6,2.8,7.2,10.2) ; 10.4 privacy ; 10.5 e2e smoke (last, needs all)
```

**Agent waves** (stories in a wave have no dependency among themselves and edit no common file; recomputed by `implementation/waves.py` after the 2026-10-16 triad repair pass 2, 72 stories, 13 waves, 0 same-wave file collisions; Story 1.10's edge on 1.11 was already in the table and is now also stated in its `Depends on` line, so it stays in W3):
- W1: 1.1
- W2: 1.4, 1.11, 1.13, 4.1 (spike), 9.1 (spike), 10.4
- W3: 1.2, 1.9, 1.10, 1.12, 1.14, 2.1, 9.8 (spike)
- W4: 1.3, 1.6, 2.2, 2.3, 2.6, 7.1, 8.8
- W5: 1.5, 1.8, 2.4, 2.7, 3.1, 3.2, 3.4, 4.2, 6.1, 7.5 (usability spike)
- W6: 1.7, 2.5, 3.3, 3.5, 5.2, 5.6 (anchor census, go/no-go), 8.1, 9.3
- W7: 2.8, 4.3, 6.2, 6.4, 8.2, 9.4, 10.2
- W8: 4.4, 4.7, 5.1, 7.2, 8.3, 10.1
- W9: 4.5 (owner input), 5.3, 8.4, 9.9
- W10: 4.6, 6.3, 7.3 (owner labels real clusters), 8.5, 8.6, 9.5
- W11: 5.4, 7.4, 8.7, 9.2, 9.7, 10.3
- W12: 5.5, 7.6, 9.6
- W13: 10.5 (e2e smoke), final verification.

**Wave integration (pre-mortem failure mode 13).** The integrator is the coordinator thread, a named role that is never given a feature in the same slot. At the end of each wave it merges that wave's stories in the order below, runs `make wave-gate` (Story 1.14: `make ready`, app load with no skipped `cli_*` module, no duplicate command or migration name) after each merge, reverts (does not patch forward) the first story that turns the gate red, and pastes the gate output into the wave's cost report. Until Story 1.14 lands (W3), the gate is `make ready` plus `cli.py --help`. Merge order rule: stories with more transitive later-wave dependents merge first (critical path first), ties by story number; computed by script from the dependency lists above:

| Wave | Merge order (first to last) |
|---|---|
| W1 | 1.1 |
| W2 | 1.4, 1.11, 1.13, 4.1, 9.1, 10.4 |
| W3 | 2.1, 1.2, 1.9, 1.10, 1.12, 1.14, 9.8 |
| W4 | 2.3, 2.2, 7.1, 2.6, 1.3, 1.6, 8.8 |
| W5 (10 parallel stories: gate after every merge) | 4.2, 2.4, 2.7, 7.5, 3.2, 3.4, 1.5, 1.8, 3.1, 6.1 |
| W6 | 2.5, 5.6, 8.1, 9.3, 5.2, 1.7, 3.3, 3.5 |
| W7 | 2.8, 4.3, 8.2, 9.4, 10.2, 6.2, 6.4 |
| W8 | 7.2, 4.4, 8.3, 5.1, 10.1, 4.7 |
| W9 | 4.5, 8.4, 9.9, 5.3 |
| W10 | 8.6, 4.6, 7.3, 9.5, 8.5, 6.3 |
| W11 | 5.4, 7.4, 9.2, 8.7, 9.7, 10.3 |
| W12 | 5.5, 7.6, 9.6 |
| W13 | 10.5 |

**Critical path** (serial dependency depth, 13 waves, unchanged by the repair pass; chain (b) alone spans 13, chain (a) has 12 nodes): (a) 1.1 -> 1.4 -> 2.1 -> 2.2 -> 2.4 -> 2.5 -> 2.8 -> 7.2 -> 9.9 -> 9.2 -> 9.6 -> 10.5; (b) 1.1 -> 1.11 -> 1.2 -> 1.3 -> 1.5 -> 8.1 -> 8.2 -> 8.3 -> 8.4 -> 8.6 -> 9.2 -> 9.6 -> 10.5. The ML branch (4.2 -> 5.6 census gate -> 4.3 -> 4.4 -> 4.5 -> 4.6 -> 5.4 -> 5.5) spans W5-W12 (the census inserts one wave in front of the real-corpus ML batches, which is why 4.3 and 6.2 moved from W6 to W7) and is gated by owner input at 4.5 and the labeling pass of 7.3. Real writes (8.4, 8.7) additionally wait on the owner's second-medium backup (Owner Checklist item 4). `recover`/leftover handling (1.10, W3) lands before `index` (2.4, W5), which refuses on leftovers; the destructive legacy apply is locked at W2 (1.11), long before the journaled writer (8.4, W9, which also needs 8.8 from W4). Owner story 4.5 is the only one whose wall-clock is a human, not an agent.

---

## Phase 1: Foundation fixes and truthful state

### Epic 1: Foundation fixes and truthful state
**Goal**: Stop the data-loss and false-claim defects in the existing tool before building on it, and establish the test harness, tool/path resolution and persistence primitives everything else uses. All defects are VERIFIED in `research/pitfalls.md` section 1 and `research/features.md` section 1; the placeholder population is VERIFIED by measurement (header).

#### Story 1.1: Test harness, DataDir, tool/path resolution, and `fail()` helper
**As a** developer, **I want** a plain-function test runner, a resolved data dir with safe permissions, absolute legacy-file paths, env-overridable tool resolution with fakes, and a uniform error helper, **so that** every later story has tests, a place for private state, cwd-independent state files, and errors that name the next command.
**Depends on**: none (wave 1 root).
**Acceptance Criteria**:
- `make gphotos-test` runs every `G/tests/test_*.py` and `make ready` includes it.
  - *Given* `G/tests/test_smoke.py` containing one passing and one deliberately failing test function in a temp copy, *When* `make gphotos-test` runs, *Then* it prints `ok  test_pass`, exits nonzero on the failing one, and exits 0 on the committed (passing-only) file.
- `DataDir.resolve()` creates `~/.local/share/gphotos-organizer/` with mode 700 and files created through it get 600; `GPHOTOS_DATA_DIR` overrides; subdirs include `journals/ backups/ quarantine/`.
  - *Given* `GPHOTOS_DATA_DIR=/tmp/gpo-test` and no such directory, *When* `DataDir.resolve().db_path()` is called, *Then* `/tmp/gpo-test` exists with mode `0o700` and `db_path()` is `/tmp/gpo-test/pipeline.db` (and `state_db_path()` is `/tmp/gpo-test/state.db`).
- `LegacyPaths` resolves state files independent of cwd.
  - *Given* cwd `/tmp` and no overrides, *When* `LegacyPaths.resolve()` runs, *Then* `manifest` is `<repo root>/upload_manifest.json` (the real file is `/home/tstapler/dotfiles/upload_manifest.json`, not under `G/`) and `mapping` is the repo-root `album_mapping.json` location, both absolute; `GPHOTOS_MANIFEST` / `GPHOTOS_MAPPING` or `DATA/config.toml [paths]` override them.
  - *Given* a manifest path that does not exist while the mapping shows uploaded albums, *When* `LegacyPaths.require_consistent()` runs, *Then* it exits 1 with `Manifest not found at <path> but album_mapping.json shows N uploaded albums. Set GPHOTOS_MANIFEST or run from the repo root. Nothing was changed.` (an empty manifest from the wrong cwd would otherwise make the loop treat every album as not uploaded).
- `fail(msg, hint)` prints a panel and exits nonzero; the source-drive check fails fast.
  - *Given* `/run/media/tstapler/EE5B-3D9B` does not exist, *When* `require_source_root(path)` runs, *Then* it exits 1 with text `Source drive not mounted: /run/media/tstapler/EE5B-3D9B. Mount it and rerun`.
- Core dependencies are declared and checked.
  - *Given* `cli.py`'s PEP 723 block, *When* `test_cli_deps.py` runs, *Then* it contains the allow-list `typer, loguru, rich, pydantic, Pillow, pillow-heif, tomli-w` (Pillow for `print_cues`, dHash and thumbnails, pillow-heif for HEIC, `tomli-w` for `people add` and `deny release`, because `tomllib` is read-only) and none of the ML packages; `analyze_ml.py`'s block carries the same shared runtime deps (`pydantic`, Pillow); a dependency-parity test imports every `pipeline/` module in both environments' dependency sets.
- Tools resolve through one seam, with fakes.
  - *Given* `GPHOTOS_EXIFTOOL=/tmp/fake_exiftool.py` and `GPHOTOS_RCLONE=/tmp/fake_rclone.py`, *When* `tools.exiftool_path()` / `tools.rclone_path()` are called, *Then* they return those paths; with no env they return the system binaries.
- PR evidence is redacted (public repo).
  - *Given* `pipeline/evidence.py` `redact(text, mapping)`, *When* it is applied to text containing an album title from `album_mapping.json`, a name from `people.toml` or an absolute file path, *Then* the title and name become `album:<id>` / `person:<n>` and the path becomes `<album id>/<sha8 of relative path>`; every story's "paste the output" step uses it (see the plan-header privacy rule).
- Cost checkpoint inputs exist from the first implementer run.
  - *Given* this story's PR, *When* it is opened, *Then* it records actual spend for Story 1.1 against its table row and the recalibrated multipliers (the 1.48 impl and 1.63 total factors, derived from the task-sum basis in the Effort estimate), which Task 1.1g writes into the Effort estimate.
**Files**: `G/tests/_test_runner.py`, `G/tests/test_smoke.py`, `G/pipeline/__init__.py`, `G/pipeline/datadir.py`, `G/pipeline/paths.py`, `G/pipeline/tools.py`, `G/pipeline/errors.py`, `G/pipeline/evidence.py`, `G/tests/test_evidence_redact.py`, `G/tests/test_cli_deps.py`, `G/tests/fakes/fake_exiftool.py`, `G/tests/fakes/fake_rclone.py`, `G/cli.py` (PEP 723 deps block only), `Makefile`, `.gitignore`

##### Task 1.1a: Runner, smoke test, Makefile target (XS)
- Copy `stapler-scripts/llm-sync/_test_runner.py` to `G/tests/_test_runner.py`; add `gphotos-test` target mirroring `Makefile:40-41`; append to `.PHONY` and `ready` prerequisites.
- Files: `G/tests/_test_runner.py`, `G/tests/test_smoke.py`, `Makefile`
##### Task 1.1b: `DataDir` (S)
- `pipeline/datadir.py`: resolve, mkdir 700, `open_private()` 600, subdirs `review/ thumbs/ logs/ reports/ models/ journals/ backups/ quarantine/`; add `DATA/`-style entries (`*.db`, `*.sqlite`, `*.npy`, `thumbs/`, `review/`, `journals/`, `backups/`) to the gphotos block of `.gitignore` as defense in depth.
- Files: `G/pipeline/datadir.py`, `.gitignore`, `G/tests/test_datadir.py`
##### Task 1.1c: `fail()` + drive check (XS)
- `pipeline/errors.py`: `fail(msg, hint)`; `require_source_root`; test with a temp path.
- Files: `G/pipeline/errors.py`, `G/tests/test_errors.py`
##### Task 1.1d: Core deps, allow-list and parity test (XS)
- Add Pillow, pillow-heif, tomli-w to `cli.py`'s inline deps; `test_cli_deps.py` holds the allow-list now (Story 4.2 extends it with the ML denylist); parity test as in the AC.
- Files: `G/cli.py`, `G/tests/test_cli_deps.py`
##### Task 1.1e: `LegacyPaths` (S)
- `pipeline/paths.py` per the AC; repo root derived from `Path(__file__).resolve()`; correct the Migration Plan statement that both files "stay in `G/`".
- Files: `G/pipeline/paths.py`, `G/tests/test_paths.py`
##### Task 1.1f: `tools.py` seam and fake executables (S)
- `pipeline/tools.py` (`exiftool_path()`, `rclone_path()`, env override); `fake_exiftool.py` and `fake_rclone.py` scripted-output fakes (later stories add scenarios, never new env names).
- Files: `G/pipeline/tools.py`, `G/tests/fakes/fake_exiftool.py`, `G/tests/fakes/fake_rclone.py`, `G/tests/test_tools.py`
##### Task 1.1g: `redact()` evidence helper and cost recalibration note (S)
- `pipeline/evidence.py` per the AC; record the first-run actual vs estimate in the PR and update the Effort estimate multipliers.
- Files: `G/pipeline/evidence.py`, `G/tests/test_evidence_redact.py`

#### Story 1.2: Atomic JSON persistence (all six write sites)
**As an** operator, **I want** state files written atomically, **so that** a crash cannot corrupt the only source of truth (`cli.py:85,274,357,435`; `ai_enrich.py:115` mapping write reached from `infer`; uploader manifest `uploader.py:78-80`, success written `:113-129`).
**Depends on**: 1.11 (CLI shell, service extraction, and legacy-app).
**Acceptance Criteria**:
- `write_json_atomic(path, obj)` writes a temp file in the same directory, fsyncs, then `os.replace`.
  - *Given* `album_mapping.json` holding `{"a": 1}` and a writer that raises after 10 bytes are written to the temp file, *When* the write is attempted, *Then* `album_mapping.json` still parses as `{"a": 1}` and no `.tmp` file remains.
- All six JSON state writers use it.
  - *Given* `grep` for `write_text(json` in `G/*.py` and `G/pipeline/*.py`, *When* run after the change, *Then* it returns zero matches (sites: scan `cli.py:85`, update-album `:274`, fix-metadata `:357`, upload `:435`, `ai_enrich.py:115` `mapping_file.write_text(json.dumps(...))`, `uploader.py:80` `save_manifest`; after Story 1.11 the first four live in the `pipeline/*_service.py` modules; `ai_enrich.py` is fixed in place and deleted later by Task 10.5c).
**Files**: `G/pipeline/atomic_io.py`, `G/pipeline/scan_service.py`, `G/pipeline/album_service.py`, `G/pipeline/fix_metadata_service.py`, `G/pipeline/upload_service.py`, `G/uploader.py`, `G/ai_enrich.py`, `G/tests/test_atomic_io.py`

##### Task 1.2a: `atomic_io.py` + failure-injection test (S)
- Files: `G/pipeline/atomic_io.py`, `G/tests/test_atomic_io.py`
##### Task 1.2b: Swap the three service call sites (S)
- Replace the writers in the scan, update-album and fix-metadata services (sites `cli.py:85,274,357`). Do NOT change the manifest schema (background upload loop is running). Run `make gphotos-test`.
- Files: `G/pipeline/scan_service.py`, `G/pipeline/album_service.py`, `G/pipeline/fix_metadata_service.py`
##### Task 1.2c: Swap the upload, manifest and `ai_enrich` call sites (S)
- Replace the remaining three writers (upload `cli.py:435`, `uploader.py:80` `save_manifest`, `ai_enrich.py:115`), so all six are covered (not three, not five); do NOT change the manifest schema. `uploader.py` is edited by this story only in this wave; Story 1.8 no longer touches it. Run `make gphotos-test`.
- Files: `G/pipeline/upload_service.py`, `G/uploader.py`, `G/ai_enrich.py`

#### Story 1.3: exiftool failure accounting (interim fix of defect B2)
**As an** operator, **I want** a failed exiftool chunk reported as failed, **so that** `metadata_status` never claims success it did not achieve (`metadata.py:196-200`, `cli.py:350-354`).
Root cause hypothesis (to confirm in 1.3a): both branches of the `returncode == 0 or "image files updated" in stdout` conditional do `total_updated += len(chunk)`, and `success` is never set False. (VERIFIED by the architecture review: `metadata.py:197,200,209`.)
**Depends on**: 1.2 (Atomic JSON persistence all six write sites).
**Acceptance Criteria**:
- A chunk whose exiftool output reports errors is counted as failed per file.
  - *Given* a fake exiftool printing `Error: File format error - /x/a.jpg` and `    1 files weren't updated due to errors` with exit 1 for a 3-file chunk, *When* `update_album_metadata` runs, *Then* it returns `success=False`, `updated=2`, `failed=["/x/a.jpg"]`.
- `fix-metadata` does not mark an album complete (`legacy_unverified` or later `verified`) when any file failed.
  - *Given* the fake above, *When* the fix-metadata service runs on that album (apply path exercised through the test seam; the CLI `--apply` is locked by Story 1.11), *Then* the album's `metadata_status` remains `pending` and the summary lists `/x/a.jpg`.
- Defect B4 (`metadata.py:160` + `-@` argfile, `-overwrite_original` emitted per file; INFERRED fine, untested in `research/pitfalls.md`) is pinned by a test until Story 8.4 deletes the flag.
  - *Given* a fake exiftool recording its argv and argfile, *When* a 3-file chunk runs through `update_album_metadata`, *Then* the recorded argfile contains `-overwrite_original` exactly once per `-execute` block, so the semantics 8.4 removes are documented by a passing test, not assumed.
**Files**: `G/metadata.py`, `G/scanner.py`, `G/pipeline/fix_metadata_service.py`, `G/tests/test_metadata_accounting.py`

##### Task 1.3a: Reproduce B2 as a failing test (S)
- Use `tools.exiftool_path()` from Story 1.1 in `scanner.py` and `metadata.py` (replacing the hardwired `EXIFTOOL_PATH`); add the scripted error scenario to `fake_exiftool.py`.
- Files: `G/tests/test_metadata_accounting.py`, `G/scanner.py`
##### Task 1.3b: Parse results, return per-file failures (S)
- Parse the `N files weren't updated due to errors` line and `Error:` lines; return `(updated, failed_paths)`; keep `-overwrite_original` untouched here (replaced in 8.4; the CLI path is locked by 1.11 meanwhile). Caller marks status per result.
- Files: `G/metadata.py`, `G/pipeline/fix_metadata_service.py`

#### Story 1.4: `dateparse.py` with golden tests (filename and folder dates as `PartialDate`)
**As an** operator, **I want** folder and filename dates parsed into intervals with precision, **so that** `IMG_20150102`, 2024+ dates, and year ranges are handled correctly (`metadata.py:38-62`; `scanner.py:33-93`).
**Depends on**: 1.1 (Test harness, DataDir, tool/path resolution).
**Acceptance Criteria**:
- Camera-style filenames match.
  - *Given* the filename `IMG_20150102_134501.jpg`, *When* `parse_filename_date` runs, *Then* it returns `PartialDate.day(2015-01-02)`.
  - *Given* `PXL_20251130_101500123.jpg`, *When* parsed, *Then* year 2025 is accepted (no `<2024` cap) and the result is `2025-11-30` precision Day.
- Invalid calendar dates are rejected, not crashed.
  - *Given* `IMG_20230231.jpg`, *When* parsed, *Then* it returns `None`.
- Non-capture prefixes are blacklisted.
  - *Given* `Screenshot_20240105-101010.png` and `WhatsApp Image 2023-05-01 at 10.11.12.jpeg`, *When* parsed, *Then* each returns `None` with reason `non_capture_prefix`.
- Folder year ranges stay intervals.
  - *Given* the folder `Summer Camp 1985-1990`, *When* `parse_folder_date` runs, *Then* it returns `PartialDate.range(1985-01-01, 1990-12-31)`, not `1985-01-01`.
  - *Given* `Christmas '94` and `1980s`, *When* parsed, *Then* results are `1994-12-01..1994-12-31 (Month)` and `1980..1989 (Decade)`.
- Illegal states are unconstructible.
  - *Given* an attempt to build `PartialDate` with `precision=Day` and a multi-year interval via the raw dataclass constructor, *When* run, *Then* `ValueError` (the public API is the classmethods `day/month/year/range/decade`, which derive bounds from precision; there is no `is_placeholder` field).
**Files**: `G/dateparse.py`, `G/models.py`, `G/scanner.py`, `G/tests/golden/dateparse.json`, `G/tests/test_dateparse.py`

##### Task 1.4a: `PartialDate`/`DatePrecision` types (S)
- Frozen dataclass with `earliest`, `latest`, `precision`; `__post_init__` invariants (`precision==Day` implies `earliest==latest`, `earliest<=latest`, bounds consistent with precision); constructors `day()/month()/year()/range()/decade()`; `to_interval()`.
- Files: `G/dateparse.py`, `G/tests/test_dateparse.py`
##### Task 1.4b: Filename parser (S)
- `(?<!\d)(19\d\d|20\d\d)[-._]?(\d{2})[-._]?(\d{2})(?!\d)` allowing `_` neighbors; calendar validation via `datetime.date`; future-date reject; blacklist table.
- Files: `G/dateparse.py`
##### Task 1.4c: Folder parser + scanner wiring + golden file (M)
- Cover 4-digit, 2-digit apostrophe years, decades, ranges, season/month words, holiday keywords (carry over scanner's christmas/father/mother/halloween/grad behaviors as Month precision); `scanner.parse_date_and_location` delegates; golden JSON captures every case including the legacy ones.
- Files: `G/dateparse.py`, `G/scanner.py`, `G/tests/golden/dateparse.json`

#### Story 1.5: Stop producing placeholder dates; unify media-type sets
**As an** operator, **I want** unresolved dates left unwritten, **so that** no fabricated `YYYY:01:01 12:00:00` is stored as a real capture date (B5). The placeholder values originate in `ai_enrich.py:31,85` and `scanner.py:68`; `metadata.py:171` only writes whatever date it is handed.
Year-precision rule (single definition, see glossary `YearPrecisionPolicy`): precision coarser than Day is never turned into a fabricated month/day by default. In this story the gate is album-level (`AlbumMapping.date_precision`) as an interim proxy; Story 8.4 replaces it with the per-file, per-decision rule and the owner opt-in `--allow-year-precision`.
**Depends on**: 1.3 (exiftool failure accounting interim fix of de), 1.4 (dateparse.py with golden tests filename and f).
**Acceptance Criteria**:
- The fix-metadata planning path skips albums whose date precision is coarser than Day (Year, Range, Decade, Month, Unknown; same set as `YearPrecisionPolicy`).
  - *Given* an `AlbumMapping` for folder `2021 random photos` with `date_precision=Year`, *When* `fix-metadata` (dry-run) runs, *Then* zero exiftool invocations occur for it and the summary reports `skipped_placeholder: 9161`.
- An explicit override exists, is loud, and cannot write before 8.4.
  - *Given* the same album and `--allow-placeholder`, *When* run in dry-run, *Then* the plan lists the files with the warning `PLACEHOLDER date 2021:01:01 12:00:00 would be written` and nothing is written (the `--apply` path is locked by Story 1.11 until 8.4 supersedes this flag with `--allow-year-precision`).
- `ai_enrich.py` and `scanner.py` no longer emit a fabricated day for any precision coarser than Day (Year, Range, Decade, Month).
  - *Given* the folder `1987`, *When* `scanner`/`ai_enrich` populate `inferred_date`, *Then* the album carries `date_precision=Year` and an interval, and no `YYYY-01-01` point value.
  - *Given* the Month folders `Christmas '94` and `1980 May`, *When* populated, *Then* the album carries `date_precision=Month` with the month interval, and no day-15 or holiday-day point value (the old `scanner.py:46-52` behavior), and `fix-metadata` dry-run skips them like Year folders.
- One `media_types.py` defines Dateable image, Dateable video, Uploadable.
  - *Given* a `.webp` and a `.3gp` file, *When* `classify(path)` runs, *Then* `.webp` is `DateableImage` and `.3gp` is `UploadableOnly`, and the scan report lists `.3gp` under "not dateable".
**Files**: `G/media_types.py`, `G/metadata.py`, `G/scanner.py`, `G/models.py`, `G/ai_enrich.py`, `G/pipeline/fix_metadata_service.py`, `G/tests/test_placeholder_gate.py`

##### Task 1.5a: `media_types.py` and extension reconciliation (S)
- Files: `G/media_types.py`, `G/scanner.py`, `G/metadata.py`, `G/tests/test_media_types.py`
##### Task 1.5b: `date_precision` on `AlbumMapping` (default derived from `dateparse` over `folder_name`, so old JSON loads) (S)
- Files: `G/models.py`, `G/tests/test_models_compat.py`
##### Task 1.5c: Gate in the fix-metadata service + `--allow-placeholder` dry-run listing (S)
- Files: `G/metadata.py`, `G/ai_enrich.py`, `G/pipeline/fix_metadata_service.py`, `G/tests/test_placeholder_gate.py`

#### Story 1.6: Deny-list upload gate v0
**As an** operator, **I want** `2021 random photos` refused by code at the point where files go to rclone, **so that** the constraint is enforced rather than documented, and a renamed folder, a different caller or a differing `album_name` cannot bypass it (B8).
**Acceptance Criteria**:
- A denied album is never passed to rclone, whichever caller invokes the uploader.
  - *Given* an `AlbumMapping(id="9102dede1a50", folder_name="2021 random photos")` and a fake rclone recording invocations, *When* `upload --apply` runs, *Then* the fake records zero calls for it and the output says `Blocked: '2021 random photos' is on the deny list. Resolve dates, then run: gphotos-organizer deny release "2021 random photos"`.
  - *Given* the same album id with `folder_name="renamed"` or `album_name != folder_name`, *When* `upload_album_to_gphotos` is called directly (not through `upload_cmd`), *Then* it raises `DenyListBlocked` and the fake records zero calls (the check lives inside `upload_album_to_gphotos`, keyed on id AND normalised folder name AND normalised path).
- Release is explicit, logged and has a precondition.
  - *Given* `deny release "2021 random photos"` has not been run, *When* `upload --apply --all` is invoked, *Then* the album is still blocked.
  - *Given* the album still has `Review` or `Conflict` decisions (or `fuse` has never run), *When* `deny release` runs, *Then* it refuses with the counts and `Run: gphotos-organizer review next`; with zero such decisions it asks for the album's file count (printed in the summary above the prompt; the album id is already on the command line and is not the token) before writing the release (tier T3 of the confirmation table, `pipeline/confirm.py`, Story 1.13; the release is logged to `DATA/logs` and `state-events.jsonl`).
- Global fail-closed rule (pre-mortem failure mode 4): the deny list is not the only protection. Until Story 9.2 replaces it, `upload_album_to_gphotos` refuses any album that is not proven placeholder-free. The proof is `DATA/placeholder-scan-summary.json`, an atomic file written by Story 1.9's `placeholders scan` with per-album counts `{files, genuine, suspect, legacy, undated, videos, unscanned}` keyed by album id (this story reads the file; it does not import 1.9 code).
  - *Given* no `placeholder-scan-summary.json` (Story 1.9 not yet run), *When* `upload --apply` runs for ANY album, *Then* the fake rclone records zero calls and the output says `Blocked: placeholder scan not run. Run: gphotos-organizer placeholders scan --root <drive>. Nothing was changed.`
  - *Given* a summary in which album A has `legacy=3`, `suspect=1`, `unscanned=2`, `undated=0` or `videos>0` (videos are never classified, Story 1.9), *When* `upload --apply` runs for A, *Then* it is blocked with `Blocked: N files in album <id> carry legacy-placeholder or unverified dates. Not uploadable until the Story 9.2 gate passes.` and zero rclone calls; an album whose summary shows every file `genuine` and no videos passes this v0 rule.
  - *Given* the summary is older than the newest `mtime` of any file in the album's folder, *When* `upload --apply` runs, *Then* it is blocked as unscanned (stale summary).
- Manifest stays compatible with old readers.
  - *Given* a manifest written by this code, *When* the old `load_manifest` reads it, *Then* it parses (no new required keys; the schema change waits for Story 9.2 and the confirmed-dead loop).
- The legacy uploader is stopped, not merely documented.
  - *Given* this story's PR description, *When* reviewed, *Then* it contains the post-stop `ps -ef | grep '[c]li.py upload'` output showing no process (Owner Checklist item 1; processes only, no album names) and a link to the Risk Control decision.
**Depends on**: 1.2, 1.9 (scan summary file), 1.13 (confirmation helper for `deny release`).
**Files**: `G/pipeline/upload_gate.py`, `G/uploader.py`, `G/pipeline/upload_service.py`, `G/cli_deny.py`, `G/tests/test_upload_gate.py`, `G/tests/fakes/fake_rclone.py`

##### Task 1.6a: `DenyList` (code constant keyed on id + folder name, `DATA/deny.toml`) and `deny list|release` in `cli_deny.py` (S)
- Files: `G/pipeline/upload_gate.py`, `G/cli_deny.py`, `G/tests/test_upload_gate.py`
##### Task 1.6b: Gate call inside `upload_album_to_gphotos` plus the service call site; fake rclone scenario (S)
- Files: `G/pipeline/upload_gate.py`, `G/uploader.py`, `G/pipeline/upload_service.py`, `G/tests/fakes/fake_rclone.py`
##### Task 1.6c: Global fail-closed rule reading `placeholder-scan-summary.json`, stale-summary check, manifest back-compat test (S)
- Do not edit `_run_rclone`.
- Files: `G/pipeline/upload_gate.py`, `G/uploader.py`, `G/pipeline/upload_service.py`, `G/tests/fakes/fake_rclone.py`

#### Story 1.7: Truthful status enums and status migration
**As an** operator, **I want** `metadata_status` and `upload_status` to be typed and honest, **so that** "all uploaded" claims stop being unverifiable (B6, B7, B10).
Root-cause step: Task 1.7a reproduces why all 628 albums show `pending` (UNVERIFIED in pitfalls B6: candidate causes are `--apply` never completing a save, or rescan overwriting `album_mapping.json`; the measured Jan-1 population shows writes did occur, so the likeliest candidate is the status never being persisted).
**Depends on**: 1.5 (Stop producing placeholder dates; unify media).
**Acceptance Criteria**:
- Statuses are `Literal` enums with a legacy load mapping for every old value (see Migration Plan, status vocabulary): stored `metadata_status` is `pending | legacy_unverified | skipped`; the derived `not_written | pending | verified | mismatch | reverted` view is Story 8.6.
  - *Given* a legacy JSON album with `"metadata_status": "fixed"` and a manifest entry for it, *When* loaded, *Then* `metadata_status == "legacy_unverified"` and `upload_status == "uploaded_unverified"`.
  - *Given* legacy values `pending_fix`, `verified`, `skipped` and an unknown `"zzz"`, *When* loaded, *Then* they map to `pending`, `legacy_unverified`, `skipped` and `pending` (plus a logged warning) respectively.
- Rescanning does not erase statuses.
  - *Given* an album id with `metadata_status="legacy_unverified"` in `album_mapping.json`, *When* `scan` re-runs over the same drive, *Then* that album keeps `legacy_unverified`.
**Files**: `G/models.py`, `G/scanner.py`, `G/pipeline/scan_service.py`, `G/tests/test_status_migration.py`

##### Task 1.7a: Reproduce the all-pending cause with a failing test (S)
##### Task 1.7b: Enums + loader mapping + `.premigrate` copy (S)
##### Task 1.7c: Scan merge-not-overwrite (S)

#### Story 1.8: Quota retry seam and fake-429 test
**As an** operator, **I want** the 2026-10-16 quota wait-and-retry loop extracted from `cli.py` and tested against a fake 429, **so that** `QuotaExceeded` / `seconds_until_quota_reset` are known to work before real use (B9).
Corrected seam: `uploader.upload_album_to_gphotos` only raises `QuotaExceeded`; the wait-and-retry `while True` loop and the `ok` variable live in `cli.py` `upload_cmd` (about lines 415-431). `ok` cannot be unbound there (the loop exits only by `break` after assignment), so there is no `UnboundLocalError` AC.
**Depends on**: 1.6 (Deny-list upload gate v0).
**Acceptance Criteria**:
- A fake rclone emitting quota text triggers wait-and-resume.
  - *Given* a fake rclone that prints `rateLimitExceeded ... 429` on call 1 and exits 0 on call 2, and an injected `sleep`/`now`, *When* `upload_with_quota_retry(album, sleep=..., now=...)` runs, *Then* it catches `QuotaExceeded`, sleeps `seconds_until_quota_reset()` (injected), the second call completes, and the manifest entry is written once.
- Bounded retries return a failure result.
  - *Given* a fake that returns quota errors on every call and `max_waits=3`, *When* the call exhausts retries, *Then* it returns a failure result (not an exception, not an infinite loop) and the album is not marked uploaded.
- Quota detection is strict (pre-mortem failure mode 4): `classify_rclone_error(stderr, rc)` returns `Quota | ClientRetired | AuthExpired | Hard`.
  - *Given* stderr containing `429`, `rateLimitExceeded` or `RESOURCE_EXHAUSTED`, *Then* `Quota` (sleep until reset, bounded by `max_waits`); *Given* stderr that mentions the word "quota" (for example `quota project not set` or a disk-quota message) without any of those strings, *Then* `Hard`: no sleep, album not marked uploaded, error text shown.
  - *Given* stderr containing `invalid_client`, `deleted_client`, "client has been retired" or `403` with `access_denied`, *Then* `ClientRetired`: no sleep, exit 1 with `rclone's shared Google client was rejected (invalid_client). Create your own OAuth client, then run: gphotos-organizer setup-rclone. Nothing was changed.`
  - *Given* a computed wait longer than 26 hours, *Then* the loop refuses to sleep and returns `Hard` (a mis-parsed reset must not put the loop to sleep forever).
**Files**: `G/pipeline/quota_retry.py`, `G/pipeline/upload_service.py`, `G/tests/test_quota.py`, `G/tests/fakes/fake_rclone.py`

##### Task 1.8a: Extract the loop from the upload service into `pipeline/quota_retry.py` with injectable clock/sleep (S)
##### Task 1.8b: Quota tests (S)

#### Story 1.9: Legacy placeholder detector and quarantine (read-only)
**As an** operator, **I want** every existing EXIF date classified as genuine, suspect or legacy placeholder from independent signals, **so that** anchors, calibration, the hold-out report and the audit are never built on dates the old tool fabricated.
Requirement trace: not in the original written requirements; added to requirements.md by the 2026-10-16 repair pass (Baseline, In Scope 7 "detect and quarantine legacy placeholder dates"). It serves Success Metric 1 (no mis-dated photos on the timeline), Success Metric 2 (anchors and the hold-out must be genuine), Risk Control and In Scope 6 (truthful state).
Evidence (VERIFIED by the coordinator, `exiftool -r -T -fast2 -DateTimeOriginal` over the drive's jpg/jpeg/png, 2026-10-16; 15,943 dated files in this run, 16,044 in an earlier one): 9,460 files are dated Jan 1 (any time); 5,926 are NOT Jan 1 but carry a `12:MM:SS` time-of-day, and 3,162 of those are exactly `12:00:SS` with SS a multiple of 5 (the legacy 5-second-offset signature, `scanner.py:46-52,77-91`, `metadata.py:41-60,121-141`). Jan 1 alone therefore under-detects, and "not Jan 1" proves nothing. What is and is not established: the 9,460 Jan-1 files are placeholder *candidates* (a 59% Jan-1 rate, 9,460 of 15,943, cannot be genuine, but the times of day of the Jan-1 files that are not `12:xx` have no established origin and no count is derived for them here); the signature-bearing non-Jan-1 files (3,162 strict, up to 5,926 at any `12:MM:SS`) are most likely legacy placeholders but unproven; no file is proven genuine except by the rules below or by the owner.

Signals (each computed independently and recorded as a reason):
- (a) `time_signature`: time-of-day is `12:00:00 + 5k s` for an integer k with 0 <= k < 720 (12:00:00..12:59:55); the strict subset `12:00:SS`, SS % 5 == 0, is the measured 3,162.
- (b) `jan1`: month and day are 01-01, any time.
- (c) `no_make_model`: both `Make` and `Model` absent.
- (d) `folder_date_equal`: the date's year (Year/Range/Decade/Month folders) or full date (Day) equals what `dateparse` (Story 1.4) extracts from the folder name or filename.
- (e) `ladder`: the file is in a run of 3 or more files of one folder, ordered by `name.lower()`, whose `DateTimeOriginal`s share a calendar date and differ from the run's first by non-decreasing multiples of 5 s, tolerating at most one missing step in total (`max_gaps=1`: offsets `0,5,10,20,25` qualify, `0,5,15,25` do not). Computed per folder, so the detector takes a `FolderContext`; files in the folder that do not belong to the candidate run (later additions, other dates) are skipped, not treated as breaks.
  - Sort key is `name.lower()` because that is exactly the order the legacy writer assigned offsets in: `sorted(..., key=lambda p: p.name.lower())` at `G/metadata.py:119-122` (VERIFIED by reading the file; the validation plan cites `:123-125`, which is the `if not media_files` check four lines below). **Natural sort is rejected**: it would order `a10` after `a2`, whereas the legacy writer put `a10` before `a2`, so a natural-sort ladder would mis-reconstruct the very sequence the tool wrote and miss real placeholders. The sort sensitivity is real (a case-sensitive sort moves 14,975 versus 15,004 files into `LegacyPlaceholder` in the reviewer's estimate), so a golden fixture pins it.
Strong signals are (a), (b), (e); weak signals are (c), (d). (`Create`/`Modify`/`Original` being identical is recorded as a reason `tags_identical` but is not a signal.)
Each classification record also carries two flags used by Story 8.7: `weak` (true when rule 2 was reached only with `Make`/`Model` present and no signal (d), or when (e) fired for a series of 20 or more uniform 5 s steps that does not start at `12:00:00`, which is the shape of a real time-lapse) and `date_kept` (true when the file is `LegacyPlaceholder` but its DATE equals a Day-precision folder or filename date, for example `2000-9-5 Dad Birthday`: the date is right and only the time is fabricated, so it is evidence (`folder_day`), not a revert target).

Classification truth table (pure function, evaluated in this order):
| Rule | Signal combination | Class |
|---|---|---|
| 1 | owner record in `placeholders.jsonl` (latest wins) | the owner's class (`Genuine`) |
| 2 | any two of the strong signals (a, b, e); `Make`/`Model` present does NOT block this (the legacy writer never cleared them) | `LegacyPlaceholder` |
| 3 | one strong signal AND (c) AND (d) | `LegacyPlaceholder` |
| 4 | none of (a, b, e) AND NOT ((c) AND (d)) | `Genuine` |
| 5 | everything else: a lone strong signal, one strong plus one weak, or (c) AND (d) with no strong signal | `Suspect` |
A lone time signature or a lone Jan 1 is `Suspect`, never `Genuine`. `Genuine` is the only class that is anchor-eligible.

**Depends on**: 1.11 (CLI shell, service extraction, and legacy-app), 1.4 (dateparse.py with golden tests filename and f).
**Acceptance Criteria**:
- Truth-table cases (each a row in `G/tests/golden/placeholder_detector.json`).
  - *Given* `DateTimeOriginal=CreateDate=ModifyDate=2021:01:01 12:00:10`, no `Make`/`Model`, folder parsed as 2021, *When* classified, *Then* `LegacyPlaceholder` with reasons `time_signature, jan1, no_make_model, folder_date_equal, tags_identical`.
  - *Given* `2021:06:04 12:00:15` with `Make=Canon` in a folder whose files form a 5-second ladder, *When* classified, *Then* `LegacyPlaceholder` (rule 2: a + e).
  - *Given* `1980:05:15 12:00:00`, no `Make`/`Model`, folder `1980 May` (day 15 emitted by the old scanner), *When* classified, *Then* `LegacyPlaceholder` (rule 3: a + c + d).
  - *Given* `2021:01:01 12:00:10` with `Make=Apple` and no ladder, *When* classified, *Then* `LegacyPlaceholder` (rule 2: a + b), and `placeholders confirm-genuine` can protect it (below).
  - *Given* lone `time_signature` (`2015:08:09 12:00:20`, `Make=Canon`, no ladder, folder year differs), *When* classified, *Then* `Suspect`.
  - *Given* lone `jan1` at `2019:01:01 00:00:18` with `Make=LG`, *When* classified, *Then* `Suspect`.
  - *Given* a date that is not Jan 1, has no time signature, no ladder, and either a `Make` or a folder mismatch (`2003:07:04 10:00:00`, `Make=Canon`), *When* classified, *Then* `Genuine`.
  - *Given* a non-Jan-1 date at a non-signature time with no `Make`/`Model` whose date equals the filename date (rule 5: c + d, no strong signal), *When* classified, *Then* `Suspect`, never `Genuine`.
- Offset signature boundaries.
  - *Given* a time `12:03:40` (12:00:00 + 5 s x 44) and a time `12:03:41`, *When* signal (a) is tested, *Then* the first matches and the second does not; `13:00:00` does not match.
- Only `Genuine` is an anchor.
  - *Given* any `LegacyPlaceholder` or `Suspect` date, *When* `anchor_eligible(cls)` is called, *Then* it returns False; it returns True only for `Genuine` (detector rule 4 or an owner record). Stories 3.4, 5.2 and 9.9 call this.
- Owner confirmation works on `Suspect` and on `LegacyPlaceholder`.
  - *Given* `placeholders confirm-genuine --file <path>` on a `Suspect` file, *When* run, *Then* a `Genuine` record with `source=owner` is appended to `DATA/placeholders.jsonl` (append-only, latest wins) and `anchor_eligible` becomes True.
  - *Given* the same command on a `LegacyPlaceholder` file (a real New Year's noon scan), *When* run, *Then* it refuses until the owner types back the exact current `DateTimeOriginal` (`Type the date to confirm: 2021:01:01 12:00:10`); on a match the record is appended and Story 8.7 skips the file; a mismatch or `--yes` without the typed value exits 1 with nothing changed.
- Measurement is reproducible and recorded.
  - *Given* `placeholders scan --root <drive>`, *When* run, *Then* it writes `DATA/reports/placeholders-<ts>.md` with total dated images, counts per signal (a, b, c, d, e), the cross-tab Jan-1 x time-signature (Jan 1 only / Jan 1 plus signature / signature without Jan 1), counts per class, and per-album counts keyed by album id (titles only with `--show-names`, never pasted into a PR); it also writes the atomic `DATA/placeholder-scan-summary.json` that Story 1.6's global fail-closed rule reads; the PR records these next to the 2026-10-16 baseline (9,460 Jan 1; 5,926 non-Jan-1 with `12:MM:SS`, of which 3,162 strict `12:00:SS`; 15,943 dated) and explains any drift.
- Recovery sources are counted, nothing is changed.
  - *Given* a `LegacyPlaceholder` file, *When* the scan runs, *Then* the report counts how many have a camera-style filename date, XMP/IPTC date, or Takeout sidecar that could re-date them, and no media file is modified (hash of fixtures equal before and after).
- Ladder order and tolerance (N4).
  - *Given* files `IMG_2.JPG`, `img_1.jpg`, `IMG_3.jpg` at offsets 0, 5, 10 s, *When* signal (e) runs, *Then* they form a ladder only under `name.lower()` order; *Given* names `a2`, `a10` where the legacy order put `a10` first, *Then* the ladder follows `a10, a2` (not natural order); *Given* offsets 0,5,10,20,25 (one missing step) *Then* (e) holds; *Given* 0,5,15,25 (two missing steps) *Then* (e) does not hold; *Given* a lone (e) on a series starting at a non-noon time with a `Make`, *Then* the file stays `Suspect` (rule 5).
- Videos are out of scope (N3): detection reads still-image `DateTimeOriginal` only.
  - *Given* an `.mp4` carrying QuickTime `CreateDate` `12:00:05`, *When* `placeholders scan` runs, *Then* the report counts it under `not classified (video, out of scope)`, it is never an anchor (Story 3.4), never reverted (Story 8.7), and the album summary row reports `videos=N` so Story 1.6's fail-closed rule and Story 9.2 do not exempt it. Extending detection to QuickTime tags is a separate story if the owner reverses this decision (Unresolved Questions).
- Measured precision gate (pre-mortem failure mode 2): the classifier's accuracy is measured against the owner's judgement before anything destructive runs, because the true originals were overwritten by `-overwrite_original` and cannot be compared with the file itself.
  - *Given* `placeholders sample --per-class 50 --seed 7`, *When* run, *Then* it writes `DATA/placeholders-sample.jsonl` holding at least 50 randomly chosen files for each class (`Genuine`, `Suspect`, `LegacyPlaceholder`) AND for each signal combination that occurs 50 or more times (all files of rarer combinations), deterministic for the seed, with the album id (not the title) and a relative path hash per row.
  - *Given* `placeholders label <sample-id> --as placeholder|genuine|unsure`, *When* run, *Then* a line is appended to `DATA/placeholders-labels.jsonl` (latest wins); the owner may use an old backup copy, a source scan or personal knowledge as ground truth, and `unsure` rows are excluded from the denominator and reported.
  - *Given* labeled rows, *When* `placeholders precision` runs, *Then* it writes `DATA/placeholder-precision.json` with, per class and per signal combination, `n`, `precision` and the Wilson 95% interval, and `passed=true` only if every gated cell has `n >= 50` and `precision >= 0.98` (gated cells: `LegacyPlaceholder` overall and per combination, and `Genuine` overall; `Suspect` is reported, not gated). Any other result prints `Precision gate FAILED: <cell> n=<n> precision=<p>. Revert and the real anchor build stay locked. Label more with: gphotos-organizer placeholders label ...` and exits 1.
  - *Given* a synthetic classifier with a planted 6% error in one combination, *When* `placeholders precision` runs on a 60-row labeled sample of it, *Then* the gate fails and names that combination.
- Day-precision folder dates are evidence, not revert targets.
  - *Given* `2000:09:05 12:00:10` in folder `2000-9-5 Dad Birthday` (Day precision, date equal), *When* classified, *Then* the class is `LegacyPlaceholder` (a + d + c) with `date_kept=True`, the scan report counts it under `date kept, time fabricated`, and Story 3.4 emits `folder_day` evidence (Day precision, confidence at most 0.6, never an anchor).
**Files**: `G/pipeline/exif_reader.py`, `G/pipeline/placeholder_detector.py`, `G/pipeline/placeholders.py`, `G/pipeline/precision_gate.py`, `G/pipeline/scan_summary.py`, `G/cli_placeholders.py`, `G/tests/golden/placeholder_detector.json`, `G/tests/test_placeholder_detector.py`, `G/tests/test_precision_gate.py`

##### Task 1.9a: Minimal batch tag reader (`read_tags`, argfile chunking, `tools.exiftool_path()`) (S)
- Files: `G/pipeline/exif_reader.py`, `G/tests/test_placeholder_detector.py`
##### Task 1.9b: Five signals, `FolderContext` ladder detection, truth-table classifier and golden cases for every row (M)
- Files: `G/pipeline/placeholder_detector.py`, `G/tests/golden/placeholder_detector.json`, `G/tests/test_placeholder_detector.py`
##### Task 1.9c: `DATA/placeholders.jsonl` store (atomic append, latest wins) and `anchor_eligible` (S)
- Files: `G/pipeline/placeholders.py`, `G/tests/test_placeholder_detector.py`
##### Task 1.9d: `placeholders scan|list|confirm-genuine` commands, the measurement report and `placeholder-scan-summary.json` (S; wall-clock: drive mounted)
- Files: `G/pipeline/scan_summary.py`, `G/pipeline/placeholders.py`, `G/cli_placeholders.py`
##### Task 1.9e: `placeholders sample|label|precision` and the 0.98 gate; `weak` and `date_kept` flags; video count (M; wall-clock: Tyler labels the sample)
- Files: `G/pipeline/precision_gate.py`, `G/cli_placeholders.py`, `G/tests/test_precision_gate.py`

#### Story 1.10: Leftover finder and minimal `recover`
**As an** operator, **I want** partial-write litter detected and handled before `index` runs, **so that** `index`'s "Run: gphotos-organizer recover" hint points at a command that exists.
Requirement trace: serves Constraint "idempotent and resumable; never modify source files without a backup/dry-run default" and Risk Control (reversible writes): a partial write left by the legacy tool must be found before any new stage reads or rewrites the drive. Not a separate written requirement; added to requirements.md by the repair pass.
Corrected claim (VERIFIED by the coordinator with `ls` on 2026-10-16; an earlier "none found" was a bad shell glob): two leftover files DO exist on the drive, `<drive>/<1961 wedding album>/img033.jpg_exiftool_tmp` (album title withheld here per the privacy rule; the coordinator's `ls` output has the real path) and `/run/media/tstapler/EE5B-3D9B/2021 random photos/20210701_172927.mp4_exiftool_tmp`. The second shows the legacy writer already touched `2021 random photos`, the deny-listed album. The recursive finder remains the authority, and its first real run must report at least these two.
**Depends on**: 1.11 (the loader: `cli_write.py` registers its `recover` command through it).
**Acceptance Criteria**:
- Finder.
  - *Given* `x.jpg_exiftool_tmp` and `y.jpg_original` under a nested fixture tree, *When* `find_leftovers(root)` runs (recursive, any depth), *Then* both are returned with kind `tmp` / `original`.
- Minimal recover.
  - *Given* leftovers, *When* `recover --list` runs, *Then* it prints each path, kind and whether the base file exists, plus `Next: gphotos-organizer recover --quarantine --apply`.
  - *Given* `recover --quarantine --apply`, *When* run, *Then* each `_exiftool_tmp` whose base file exists is MOVED (never deleted) to `DATA/quarantine/<ts>/`, `_original` files are only listed, and the dry-run default prints the intended moves without `--apply`.
- Day-one check.
  - *Given* the mounted drive, *When* `recover --list` runs, *Then* its count is recorded in the PR and it lists at least the two known leftovers above (a lower count means the finder or the drive state is wrong and blocks the story).
**Files**: `G/pipeline/leftovers.py`, `G/cli_write.py`, `G/tests/test_leftovers.py`

##### Task 1.10a: `find_leftovers` (recursive) and tests (S)
##### Task 1.10b: `recover --list` / `--quarantine` (dry-run default) in `cli_write.py` (S)
- Journal reconciliation of `Pending` rows is added by Task 8.3b to the same command.
##### Task 1.10c: exFAT yank/remount spike on a throwaway USB stick (S; wall-clock: Tyler supplies a small stick, never the family drive)
- Format the stick exFAT, run a tmp-write-then-rename loop on it, pull it mid-write and remount; record what `dmesg` shows, whether `fsck.exfat -n` flags it, and what `*_exiftool_tmp` or truncated files remain, in ADR-007 "Spike outcome". This turns the INFERRED exFAT corruption claim (research/pitfalls.md s5) into a measured one before Story 8.4 relies on it.
- Files: `project_plans/gphotos-organizer-pipeline/decisions/ADR-007-exif-plan-apply-journal.md`

#### Story 1.11: CLI shell, service extraction, and legacy-apply lock
**As an** operator, **I want** `cli.py` reduced to a registration shell, the destructive legacy writer disabled, and the hot command bodies moved into services, **so that** 25 new commands do not land in the hotspot, and no run can overwrite EXIF in place without a journal (B2).
Requirement trace: serves Success Metric 4 (new analysis step without editing `cli.py` core flow) and Risk Control (dry-run default, reversible writes: the legacy `-overwrite_original` path is locked); the command-name rule below makes the UX document's command set (UX-29, UX-05) exactly achievable. Added to requirements.md by the repair pass.

**Command-name rule (consistency review B2).** Auto-discovery registers what a `G/cli_<x>.py` module exports, by explicit declaration, not by file name:
- `COMMANDS: dict[str, Callable]` registers **flat top-level commands** by the dict key (for example `cli_stages.py` exports `{"index": ..., "analyze": ..., "fuse": ...}`; the UX names are flat).
- `GROUPS: dict[str, typer.Typer]` contributes subcommands to a **group** named by the key. Several modules may contribute to the same group; the loader merges them into one Typer group (it never calls `add_typer` twice with one name).
- Any duplicate top-level name, or any duplicate subcommand inside a merged group, is a startup error naming both modules (`Command 'accept' registered by cli_a and cli_b`), so Click can never silently shadow one registration. Exception: a module with `LEGACY = True` yields to any non-legacy registration of the same name, with one log line.
- The inventory (each owner module is a story's own file): flat `scan, infer (removed in 10.5), fix-metadata, upload, update-album, setup-rclone` (stay in `cli.py` as thin delegations), `index, analyze, fuse` (`cli_stages`), `plan, undo, recover` (`cli_write`), `audit` (`cli_audit`), `status` (`cli_status`), `census` (`cli_census`); groups `review` (`cli_review_cluster`: merge, split, sheet; `cli_review_items`: list, next, accept, reject, set, skip, undo-last; `cli_review_io`: import), `people` (`cli_people`), `placeholders` (`cli_placeholders`), `deny` (`cli_deny`), `models` (`cli_models`), `anchors` (`cli_anchors`), `remediation` (`cli_remediation`), `backup` and `prewrite` (`cli_backup`), `report` (`cli_report`: bare `report` = run report, `report accuracy`, `report albums`). `accept`, `reject` and `skip` live only in `cli_review_items` and dispatch on the item kind through the Story 7.2 handler registry (cluster ids such as `C12` reach the handler Story 4.5 registers), so the two stories cannot collide.

**Disposition of the three legacy commands that collide with new names** (`cli.py` today: `review_cmd` line 155, `report_cmd` line 278, `status_cmd` line 452): all three are moved out of `cli.py` into `G/cli_legacy.py` by this story with `LEGACY = True` and byte-identical behavior (characterization fixtures), then **migrated with an alias** by the story that owns the new name, which absorbs the legacy behavior so `cli_legacy.py` can be deleted in Task 10.5c:
- `review` (legacy: flagged-album list with `--mapping`, `--severity`, `--json`) becomes the `review` group (Story 7.2); the legacy listing is `review list --source album [--severity] [--json]`, and bare `review` with a legacy flag runs that listing and prints one notice line on stderr (`'review --severity' is now: review list --source album --severity ...`) for one release; stdout and the exit code equal the new form's.
- `report` (legacy: album Markdown report with `--mapping`, `--out`) becomes the `report` group (Stories 10.1, 5.5): bare `report` is the run report, the legacy output is `report albums` (golden-identical), and bare `report` with `--mapping` or `--out` runs `report albums` with a stderr notice for one release.
- `status` (legacy: table of scanned source, album and file totals, flagged count, uploaded albums) is **replaced in place** by the new `status` screen (Story 10.3), whose header keeps those five legacy rows and the `--mapping` / `--manifest` options.
**Depends on**: 1.1 (Test harness, DataDir, tool/path resolution).
**Acceptance Criteria**:
- Legacy destructive apply is unusable.
  - *Given* any album and `fix-metadata --apply`, *When* run, *Then* it exits 1 with `Legacy writer disabled: it overwrites files in place and leaves no undo record. Run the dry run: gphotos-organizer fix-metadata. The journaled writer arrives with plan/apply. Nothing was changed.` and the fake exiftool records zero invocations; the dry run still works. Story 8.4 removes the lock and replaces it with the journaled path.
- Sub-apps are auto-discovered.
  - *Given* a test file `G/cli_toy.py` exporting `GROUPS = {"toy": app}` (a Typer app), *When* `cli.py --help` runs, *Then* `toy` is listed and `cli.py` is byte-identical to before (asserted by hash in the test); each later story adds its own `G/cli_<area>.py` and never edits `cli.py`.
- Command names follow the rule above.
  - *Given* fixture modules exporting `COMMANDS={"index": f}`, `GROUPS={"review": app_a}` and a second module `GROUPS={"review": app_b}`, *When* `cli.py --help` runs, *Then* `index` is a top-level command and `review` is ONE group listing the union of both modules' subcommands.
  - *Given* two fixture modules that both register subcommand `accept` in `review`, *When* `cli.py --help` runs, *Then* exit 1 with `Command 'review accept' registered by cli_a and cli_b. Nothing was changed.` and neither is silently shadowed.
  - *Given* the real command inventory above, *When* the Story 10.5 test builds the full app, *Then* the top-level names are exactly the inventory (including `analyze, index, fuse, plan, undo, recover, audit, status, report`) and no name is registered twice.
- Legacy collisions are dispositioned.
  - *Given* `cli_legacy.py` registering `review`, `report`, `status` with `LEGACY = True` and, later, the new `review` group, *When* both are loaded, *Then* the new group wins with one log line, and until then `review --severity high --json`, `report --out x.md` and `status` produce byte-identical output to the pre-change commands (characterization fixtures).
- Auto-discovery keeps imports lazy.
  - *Given* `cli.py --help` run with `python -X importtime` (or an import-recording hook) in a test, *When* it finishes, *Then* no module outside the stdlib plus `typer`, `rich`, `pydantic`, `loguru` and the `G/cli_*.py` shells themselves was imported: Pillow, `pillow-heif`, `pipeline/store.py` and every other heavy or store-opening import lives inside command bodies or is deferred via a function-level import (ADR-001 rejected directory auto-discovery for plugins because of import-time side effects; this keeps CLI discovery from reintroducing them).
- A broken sub-app cannot break other commands.
  - *Given* `G/cli_broken.py` containing `raise ImportError("boom")` next to a healthy `cli_toy.py`, *When* `cli.py --help` and `cli.py toy ...` run, *Then* `toy` still works, the help ends with a warning naming the failing module (`Skipped G/cli_broken.py: ImportError: boom`), the exit code of `--help` is 0, and invoking the broken sub-app's name exits 1 with the same message and `Nothing was changed.`
- Extraction preserves behavior.
  - *Given* characterization fixtures (fake exiftool and fake rclone) run through `upload_cmd`, `fix_metadata_cmd`, `update_album_cmd` and `scan_cmd` before the change, *When* run after, *Then* outputs and written JSON match (except the legacy lock), and the four command bodies are thin delegations to `pipeline/upload_service.py`, `fix_metadata_service.py`, `album_service.py`, `scan_service.py`. `review_cmd` (63 lines, now in `cli_legacy.py`) and `infer_cmd` (43) are grandfathered.
- Ratchet guard on body length.
  - *Given* `tests/cli_size_baseline.json` listing today's measured bodies (`upload_cmd` 73, `review_cmd` 63, `fix_metadata_cmd` 59, `scan_cmd` 55, `update_album_cmd` 54, `infer_cmd` 43), *When* `test_cli_size.py` runs, *Then* a NEW command whose body exceeds 40 lines (excluding `typer.Option` declarations) fails, an existing command may shrink but not grow, and lowering the baseline is the only allowed edit to that file.
- Paths come from `LegacyPaths`.
  - *Given* cwd `/tmp`, *When* `scan`, `upload` and `update-album` run against the fixture mapping, *Then* they read and write the absolute paths from `LegacyPaths` (Story 1.1), not cwd-relative files.
**Files**: `G/cli.py`, `G/cli_legacy.py`, `G/pipeline/cli_loader.py`, `G/pipeline/upload_service.py`, `G/pipeline/fix_metadata_service.py`, `G/pipeline/album_service.py`, `G/pipeline/scan_service.py`, `G/tests/test_cli_size.py`, `G/tests/cli_size_baseline.json`, `G/tests/test_cli_shell.py`

##### Task 1.11a: Characterization fixtures for the four commands (S)
- Files: `G/tests/test_cli_shell.py`
##### Task 1.11b: `cli.py` auto-discovers `cli_*.py` through `pipeline/cli_loader.py` (the `COMMANDS` / `GROUPS` / `LEGACY` rule, group merging, duplicate detection) with function-level lazy imports and per-module failure isolation; move `review_cmd`, `report_cmd`, `status_cmd` to `cli_legacy.py` (M)
- Files: `G/cli.py`, `G/cli_legacy.py`, `G/pipeline/cli_loader.py`, `G/tests/test_cli_shell.py`
##### Task 1.11f: Extract the four command bodies (`upload_cmd`, `fix_metadata_cmd`, `update_album_cmd`, `scan_cmd`) into the four services, characterization fixtures from 1.11a unchanged (S)
- Files: `G/pipeline/upload_service.py`, `G/pipeline/fix_metadata_service.py`, `G/pipeline/album_service.py`, `G/pipeline/scan_service.py`
##### Task 1.11c: Legacy `--apply` lock and its test (XS)
- Files: `G/pipeline/fix_metadata_service.py`, `G/tests/test_cli_shell.py`
##### Task 1.11d: Wire path defaults to `LegacyPaths` (XS)
- Files: `G/pipeline/scan_service.py`, `G/pipeline/album_service.py`, `G/pipeline/upload_service.py`
##### Task 1.11e: Ratchet guard and baseline (S)
- Files: `G/tests/test_cli_size.py`, `G/tests/cli_size_baseline.json`

#### Story 1.12: Help panels, shell completion, and alias notices
**As an** operator, **I want** `--help` grouped by workflow stage, tab completion for ids, names and albums, and a stderr notice whenever an old command name is used, **so that** about 25 commands and 9 groups are discoverable and the three renamed legacy commands cannot silently change behavior.
Requirement trace: serves Success Metric 4 (commands added without editing `cli.py`) and the UX document S12 (help panels, completion, alias notices; UX-93 to UX-95). The panel map lives in one file so later stories never set `rich_help_panel` themselves.
**Depends on**: 1.11 (the loader).
**Acceptance Criteria**:
- Help is grouped in workflow order.
  - *Given* the full app, *When* `cli.py --help` runs, *Then* the panels appear in the order Setup, Analyze, Review, Safety, Write, Upload, Audit, Legacy, each command in exactly one panel (the map in `pipeline/cli_help.py` equals the UX S12 table), a command missing from the map fails `test_cli_help.py`, and the epilog begins `Where am I? gphotos-organizer status` and `Reverse something? gphotos-organizer status --explain reverse`.
- Aliases warn on stderr only.
  - *Given* bare `review --severity high --json`, *When* run, *Then* stdout is byte-identical to `review list --source album --severity high --json`, the exit code is equal, and stderr carries one line `Deprecated: 'review --severity' is now 'review list --source album --severity ...'`; the same for bare `report --out`.
- Completion offers ids, names and albums without opening a database.
  - *Given* `GPHOTOS_DATA_DIR` holding `people.toml`, `decisions.jsonl` and `album_mapping.json`, *When* the completer runs for `review accept <TAB>`, `review accept C12 --name <TAB>`, `review sheet --album <TAB>` and `undo --run <TAB>`, *Then* it returns item and cluster ids (`C12`, `C12/F3`), people names and aliases, album ids with the title as hint, and run ids, and an import hook asserts neither `pipeline/store.py` nor `sqlite3` was imported.
- List-type commands share option semantics.
  - *Given* `review list`, `review next`, `people list`, `placeholders list` and `placeholders summary`, *When* each is run with `--json`, *Then* each emits a JSON document with a top-level `items` array; `--source` and `--album` mean the same wherever they exist (checked by Story 10.5 over the full app).
**Files**: `G/pipeline/cli_help.py`, `G/pipeline/completion.py`, `G/pipeline/cli_loader.py`, `G/tests/test_cli_help.py`, `G/tests/test_completion.py`

##### Task 1.12a: Panel map, loader hook, epilog, and the exactly-one-panel test (S)
- Files: `G/pipeline/cli_help.py`, `G/pipeline/cli_loader.py`, `G/tests/test_cli_help.py`
##### Task 1.12b: Completion providers (items, clusters, names, albums, runs, plans) with the no-database import guard (S)
- Files: `G/pipeline/completion.py`, `G/tests/test_completion.py`
##### Task 1.12c: Stderr deprecation helper used by the `review` and `report` aliases, and the `--json` shape test (XS)
- Files: `G/pipeline/cli_help.py`, `G/tests/test_cli_help.py`

#### Story 1.13: Confirmation tiers, display vocabulary, and the reversal map
**As an** operator, **I want** one confirmation helper for every destructive or hard-to-reverse command, one vocabulary, and one printable map of how to reverse each action, **so that** `upload --apply`, `placeholders revert --apply`, `prewrite purge`, `--force-guard` and `--prefer-import` do not each invent their own prompt, and I always know which undo applies.
Requirement trace: serves Risk Control (dry-run default, reversible writes) and the UX document S12 (UX-90 to UX-92); consumed by Stories 1.6, 7.4, 7.6, 8.4, 8.5, 8.7, 8.8, 9.2 and 10.3.
**Depends on**: 1.1 (`errors.py`).
**Acceptance Criteria**:
- Tiered confirmation with a token the prompt does not print.
  - *Given* `confirm(tier="T2", token="1214", scope_words="1,214 files across 88 albums", prompt="Type the number of files to write to continue:", reversal="undo --run R7")`, *When* run on a pty and an empty line, a wrong number, then `1214` are typed in three separate runs, *Then* the first two print `Confirmation did not match; nothing was changed.` and exit 1, the third proceeds, and the prompt text never contains `1214` (every T2/T3 command prints this one message; no command says `nothing written`).
  - *Given* a non-TTY, *When* `--yes` is passed, *Then* the token is supplied and the preconditions still run; *Given* a TTY and `--yes`, *Then* `--yes` is ignored with a notice.
- T3 checks its precondition before it asks.
  - *Given* `confirm(tier="T3", precondition=lambda: "Run R7 has Pending/Mismatch rows")`, *When* the precondition fails, *Then* it exits 1 with that text and never prompts.
- T3 tokens are counts that are not on the command line.
  - *Given* `deny release 9102dede1a50` (the album id is in argv) on a pty, *When* the prompt `Type the number of files in this album to continue:` is answered with the album id, with a wrong number, then with `9161` in three runs, *Then* the first two exit 1 with `Confirmation did not match; nothing was changed.` and the third proceeds; the same holds for `upload --i-verified-trash ALBUM` (the album's local file count), `prewrite purge --run R7` (snapshot files) and `undo --force` (files to overwrite).
  - *Given* a `confirm()` call with ordered `tokens=["212", "7757"]` (albums, then files) and `212` present in `sys.argv`, *When* it runs, *Then* it asks for the first candidate that is not an argv element (here the file count) and the prompt names what to count; *Given* every candidate present in argv, *Then* it refuses cleanly (no exception, exit 1): `Cannot confirm: the counts in the summary (212 albums, 7,757 files) both appear on the command line. Rerun without the numeric arguments. Nothing was changed.`; an empty candidate list is the only developer error (`ValueError`, caught in tests), so no T2/T3 command can use a plan, run or album id as its token and no data-dependent collision crashes a command mid-flow. `upload --apply --album X` (exactly one album) uses the file count as its first candidate.
  - *Given* the summary prints `1,214 files`, *When* `1,214` and `1214` are typed in two runs, *Then* both confirm.
- The tier table has T1 (immediate) and T1a (preview then `--apply`), and every command appears in exactly one tier.
  - *Given* `explain_topics.tiers()`, *When* rendered, *Then* T1 lists single-item `review accept|reject|skip|set <id>` and cluster/face labeling by id, `people add`, `people edit`, `remediation done|waive` and `models fetch`; T1a lists `review import`, `review confirm-genuine|confirm-placeholder`, `review set <album> --offset|--date`, `review reject <Accepted cluster>`, `recover --quarantine` and `anchors pin-album`; and a test walks every documented usage in UX S2 to S12 (`people edit "X" --born ...`, `remediation done --album "1985 Beach"`, `models fetch faces`) and fails if a T1 command requires `--apply` or a T1a command applies without it.
- T1+ override flags are journaled loudly.
  - *Given* `--force-guard`, `--prefer-import`, `--include-weak` or `--unviewed`, *When* used, *Then* one line `Override: <flag> (<rule>). Journaled.` prints and the decision or journal row carries the rule name; the refusal (or dry-run) that precedes the override names the exact flag, so a single `review set` that a guard refuses is previewed by its refusal and `--force-guard` then applies immediately.
- Display vocabulary is one function.
  - *Given* `labels.display(DecisionStatus.Review)`, `labels.display(WriteState.Verified)` and the plan bucket, *When* called, *Then* they return `Needs review`, `Read-back OK` and `Held`.
  - *Given* the golden output of every terminal screen (status, plan, review list/next/clusters, import dry-run, upload, undo, audit, backup, help) and every sheet template, *When* the vocabulary scan runs, *Then* it enforces the five rules of UX S12 and fails on any breach: V1 `Skipped`/`skipped` only on review screens; V2 the bare word `verified` nowhere (`uploaded_unverified`, `backup verify`, `--i-verified-trash` are not matches); V3 bare `Review` as a fusion outcome nowhere, nor the lowercase outcome forms `needs review` and `conflict` (the allow-list holds the `Review` help panel and the `Review file 11 of 172` header); V4 `Held` never in upload output, `Blocked` never in plan output, and neither on any review screen (review leftovers read `parked` and `cleared`); V5 `Ignored`, `Not imported`, `restored`, `left unchanged` and `Pending` never in a review-state cell or the cluster intents column (`review undo-last` prints `back to accept`, the column is `Queued`). Exceptions live only in `G/tests/vocab_allowlist.toml` (screen plus exact string), and an allow-list entry that matches no golden line fails the test.
- The reversal map is printable and complete.
  - *Given* `explain_topics.reverse()`, *When* rendered, *Then* it has one row for each of: review decision, import, group decision, `fix-metadata --apply`, `placeholders revert --apply`, damaged file, leftovers, `prewrite purge`, `upload --apply`, `people edit`; each row names the command that reverses it and what that command does not reverse; Story 10.3 serves it as `status --explain reverse`. It also has an `anchors pin-album --apply` row (`anchors exclude FILE`), and the `review undo-last` and `undo --run` rows point at each other: `undo --run R9` for an unknown run prints `No run 'R9'. To undo a review decision: review undo-last`, and `review undo-last` with nothing to undo prints `Nothing to undo. To reverse EXIF writes: undo --list`.
**Files**: `G/pipeline/confirm.py`, `G/pipeline/labels.py`, `G/pipeline/explain_topics.py`, `G/tests/test_confirm.py`, `G/tests/test_labels.py`, `G/tests/vocab_allowlist.toml`

##### Task 1.13a: `confirm()` with tiers T0 to T3, token rule, `--yes` rule, override notices (S)
- Files: `G/pipeline/confirm.py`, `G/tests/test_confirm.py`
##### Task 1.13b: `labels.display()`, `explain_topics` (reverse, vocabulary, tiers) and the vocabulary scan test (S)
- Files: `G/pipeline/labels.py`, `G/pipeline/explain_topics.py`, `G/tests/test_labels.py`
##### Task 1.13c: argv-collision handling (candidate-count fallback and clean refusal, replacing the raise), the T3 count-token tests and `vocab_allowlist.toml` with its stale-entry check (XS)
- Files: `G/pipeline/confirm.py`, `G/tests/test_confirm.py`, `G/tests/vocab_allowlist.toml`
##### Task 1.13d: T1/T1a split in `explain_topics.tiers()`, thousands-separator token matching, the usage-versus-tier walk test, the undo cross-pointers and the V3 to V5 scan extensions (S)
- Files: `G/pipeline/confirm.py`, `G/pipeline/explain_topics.py`, `G/pipeline/labels.py`, `G/tests/test_confirm.py`, `G/tests/test_labels.py`

#### Story 1.14: Wave integrator and merge-order gate
**As the** coordinator, **I want** an explicit integration step and merge order at the end of every wave, **so that** nine parallel stories (W5) do not merge into a broken tree and the cost of a bad merge is found at the wave boundary, not at Story 10.5 (pre-mortem failure mode 13).
Requirement trace: serves the Risk Control "staged rollout" and the plan's wave model. The integrator is a named role: the coordinator thread, never a feature worker; it runs this story's gate after merging a wave's stories in the order given under "Agent waves" and fixes only merge conflicts and import breaks (no feature work).
**Depends on**: 1.1 (Makefile), 1.11 (loader and duplicate-command detection).
**Acceptance Criteria**:
- One command is the wave gate.
  - *Given* a tree on which a wave's stories were merged, *When* `make wave-gate` runs, *Then* it runs `make ready`, loads the app (`cli.py --help` exits 0 with no `Skipped G/cli_*.py` warning), fails on a duplicate command or group-subcommand registration, fails on two stories shipping the same `sNNNN_` migration name, and prints `wave gate: ok` or the first failing check.
  - *Given* a deliberately broken fixture module `cli_broken.py` on the tree, *When* the gate runs, *Then* it exits 1 naming the module (the loader tolerates the break, the gate does not).
- Merge order is deterministic and recorded.
  - *Given* the merge-order table in the plan (rule: stories with more later-wave dependents merge first, ties by story number), *When* the coordinator integrates a wave, *Then* the gate output is pasted in the wave's cost report and the first failing story is reverted, not patched forward.
**Files**: `G/tests/wave_gate.py`, `G/tests/test_wave_gate.py`, `Makefile`

##### Task 1.14a: `wave_gate.py` checks (ready, help load, duplicates, migration names) and `make wave-gate` target (S)
- Files: `G/tests/wave_gate.py`, `Makefile`
##### Task 1.14b: Broken-module fixture test and merge-order record template (XS)
- Files: `G/tests/test_wave_gate.py`

---

## Phase 2: Pipeline core and date plugins

### Epic 2: Pipeline core (contract, registry, store, fusion, journal foundation)
**Goal**: The Protocol, SQLite store, lazy registry, index and analyze stages, and pure fusion that every plugin plugs into (ADR-001, 002, 003).

#### Story 2.1: Contract types
**As a** plugin author, **I want** one typed contract, **so that** a plugin is a file plus one registry entry file.
**Depends on**: 1.4 (dateparse.py with golden tests filename and f).
**Acceptance Criteria**:
- `Evidence` is a sum type `Observation | Abstention`, immutable.
  - *Given* `Observation(kind=Date, interval=1985-01-01..1990-12-31, confidence=0.6, provenance=folder_year@1)`, *When* a field is assigned, *Then* a `FrozenInstanceError` (or pydantic `ValidationError`) is raised.
- Confidence outside the range 0 to 1 is rejected.
  - *Given* `Confidence(1.2)`, *When* constructed, *Then* `ValueError`.
- Abstain evidence carries no value, and the illegal combinations cannot be built.
  - *Given* `Abstention(plugin="faces", reason="no_face")`, *When* serialized, *Then* the row has `kind="abstain"`, `value` null, and no `Confidence`; *Given* an attempt to construct an `Observation` with `abstain=True` or an `Abstention` with a value, *Then* the call is a `TypeError` (the fields do not exist). A `match` over `Evidence` without both arms fails the exhaustiveness test.
- `DecisionStatus` holds fusion outcomes only.
  - *Given* the enum, *When* its members are listed, *Then* they are exactly `Anchor, Eligible, Review, Conflict, UserOverride` (no `Written`/`Reverted`; write state is the journal join `WriteState`, Story 8.6).
- Boundary parsing.
  - *Given* a JSON row read from `evidence`, `decisions.jsonl` or `plan.jsonl`, *When* loaded, *Then* it is parsed into typed objects at the read boundary (a malformed row raises a parse error naming the file and line), never passed onward as a dict.
**Files**: `G/pipeline/contract.py`, `G/tests/test_contract.py`

##### Task 2.1a: Newtypes and enums (`ContentKey`, `Confidence`, `EvidenceKind`, `PluginScope`, `PluginRuntime`, `DecisionStatus`, `WriteState`) (S)
##### Task 2.1b: `Observation`, `Abstention`, `Provenance`, `FileContext`, `AnalysisPlugin` Protocol + JSON round-trip + boundary parser (S)

#### Story 2.2: Two stores (derived + source of truth), migration runner, and `ContentKey`
**As an** operator, **I want** evidence cached by a metadata-insensitive content hash in a derived store, and undo records and owner input kept in a separate store that rollback never deletes, **so that** EXIF writes do not invalidate the cache and "delete the derived DB" is always safe (C5, architecture.md s8, ADR-002).
**Depends on**: 2.1 (Contract types).
**Acceptance Criteria**:
- Each store has its own versioned, per-epic migrations (not all tables up front).
  - *Given* empty `DATA/`, *When* `Store.open()` runs, *Then* `pipeline.db` has exactly `files, evidence, decisions, schema_version` (applied: `s0202_initial`) and `state.db` has exactly `schema_version` (applied: `s0202_initial`); later epics add their tables with their own story-named migrations (state: 8.3 `write_journal`, 4.4 `labels, constraints`, 5.2 `anchor_pins`; pipeline: 4.3 `faces`, 4.4 `clusters`, 5.2 `anchors`, 5.3 `calibration`, 6.1 `dup_groups`, 6.2 `embeddings`, 9.3 `uploads_observed`, 9.9 `audit_runs`, 10.2 `run_metrics`).
- Deleting the derived store loses nothing irreplaceable.
  - *Given* rows in `state.db` and `DATA/journals/`, *When* `pipeline.db` is deleted and `index` re-run, *Then* `state.db` and the journals are byte-identical and `Store.open()` succeeds.
- Concurrent access is safe.
  - *Given* two processes opening `pipeline.db`, *When* one holds a write transaction, *Then* the other waits up to `PRAGMA busy_timeout` and retries on `SQLITE_BUSY` rather than failing; a test with a held lock proves the retry; only `cli.py` opens `state.db` writable (the ML script opens it `mode=ro`, asserted in 4.2).
- Version check.
  - *Given* a store whose applied-migration set differs from what the code expects, *When* opened by the ML runtime, *Then* it refuses to start with `Schema mismatch: pipeline.db is missing s0403_faces. Run: gphotos-organizer index (migrates). Nothing was changed.`
- `ContentKey` is stable across an EXIF write.
  - *Given* a generated 64x64 JPEG, *When* `ContentKey` is computed, then `exiftool -DateTimeOriginal="1975:06:01 12:00:00"` is applied, and `ContentKey` is recomputed, *Then* both keys are equal while `sha256(bytes)` differs.
- Evidence keyed by (key, plugin, version, params_hash, kind, seq) is idempotent.
  - *Given* the same `Evidence` inserted twice with identical key, *When* `evidence_for(key)` runs, *Then* one row is returned; bumping `plugin_version` returns the new row and keeps the old (stale, retained for audit).
**Files**: `G/pipeline/store.py`, `G/pipeline/state_store.py`, `G/pipeline/content_key.py`, `G/pipeline/migrations/pipeline/s0202_initial.sql`, `G/pipeline/migrations/state/s0202_initial.sql`, `G/tests/test_store.py`, `G/tests/test_content_key.py`

##### Task 2.2a: Hash-stability spike across formats (S)
- Over generated JPEG/PNG/TIFF/HEIC (if exiftool can write)/MP4 fixtures: compare `ImageDataMD5` before/after a journaled write. Record per-format result in ADR-002 "Spike outcome"; formats where it is unstable use sha256 pinned at first index.
- Files: `G/pipeline/content_key.py`, `G/tests/test_content_key.py`
##### Task 2.2b: Two-store schema + per-store migration runner + WAL + busy-timeout/retry + `mode=ro` opener (M)
- Files: `G/pipeline/store.py`, `G/pipeline/state_store.py`, `G/pipeline/migrations/pipeline/s0202_initial.sql`, `G/pipeline/migrations/state/s0202_initial.sql`, `G/tests/test_store.py`
##### Task 2.2c: `ContentKey` computation (batch exiftool call, `(size, mtime_ns)` skip map, sha256 fallback) (S)
- Files: `G/pipeline/content_key.py`, `G/tests/test_content_key.py`
##### Task 2.2d: Evidence repository + tests (S)
- Files: `G/pipeline/store.py`, `G/tests/test_store.py`

#### Story 2.3: Lazy plugin registry
**As a** plugin author, **I want** to add a plugin without editing `cli.py`, **so that** the success metric "new analysis step without editing core flow" holds. The registry is the union of one-line entry files `G/plugins/registry.d/<name>.toml` (`name`, `class = "module:Class"`, `runtime`, `enabled_by_default`); reading them imports nothing, so loading stays lazy and explicit (ADR-001 amended), and plugin stories in the same wave never edit a shared file.
**Depends on**: 2.1 (Contract types).
**Acceptance Criteria**:
- Only enabled plugins are imported.
  - *Given* a registry containing `faces -> "ml_plugins.faces:FacesPlugin"` and `faces` disabled, *When* `registry.load(enabled=["folder_year"])` runs, *Then* `"ml_plugins.faces"` is not in `sys.modules`.
- Order follows the `after=` DAG; cycles are rejected.
  - *Given* plugins `age(after=["faces"])` and `faces(after=["age"])`, *When* `registry.order()` runs, *Then* `PluginCycleError` names both.
- Cloud plugins are not importable without policy.
  - *Given* `cloud_vision.requires_cloud=True` and `CloudPolicy(allow_cloud=False)`, *When* `registry.load(["cloud_vision"], policy)` runs, *Then* it is skipped with the message `Plugin 'cloud_vision' sends images to a cloud provider. Skipped; pass --allow-cloud to enable.`
- Adding a toy plugin touches only a plugin file and the registry.
  - *Given* a test plugin file `tests/fixtures/toy_plugin.py` and one `registry.d/toy.toml` entry, *When* `analyze --plugins toy` runs over 3 fixture files, *Then* 3 evidence rows are stored and `cli.py` is unmodified (asserted by git diff in the test of 10.5).
**Files**: `G/pipeline/registry.py`, `G/pipeline/cloud_policy.py`, `G/plugins/registry.d/.gitkeep`, `G/tests/test_registry.py`

##### Task 2.3a: Registry, DAG order, enable flags from `DATA/config.toml` (S)
##### Task 2.3b: `CloudPolicy` and gating (S)

#### Story 2.4: `index` stage
**As an** operator, **I want** a per-file index with content keys, **so that** every later stage is incremental and per-file (the current code has no per-file entity: `models.py:15-21`).
**Depends on**: 2.2 (Two stores derived + source of truth , migrat), 1.10 (Leftover finder and minimal recover).
**Acceptance Criteria**:
- Indexes files from `album_mapping.json` albums.
  - *Given* an album with 3 jpg and 1 `.json` sidecar on a fixture drive, *When* `index` runs, *Then* `files` has 3 rows with `media_class=DateableImage` and the sidecar is skipped.
- Rerun is a no-op.
  - *Given* unchanged `(size, mtime_ns)`, *When* `index` re-runs, *Then* the summary prints `0 hashed, 3 cached` and no file is read.
- Refuses on unmounted drive or leftover exiftool temp files, and the named command exists (Story 1.10 ships `recover --list` before this story).
  - *Given* a file `a.jpg_exiftool_tmp` beside `a.jpg`, *When* `index` runs, *Then* it exits 1 with `Partial write detected: a.jpg_exiftool_tmp. Inspect, then run: gphotos-organizer recover --list`, using `pipeline/leftovers.find_leftovers`.
**Files**: `G/pipeline/indexer.py`, `G/cli_stages.py`, `G/tests/test_indexer.py`

##### Task 2.4a: Indexer with batched hashing and Ctrl-C-safe commits (M)
##### Task 2.4b: `index` command + leftover-file detection + progress (S)

#### Story 2.5: `analyze` runner
**As an** operator, **I want** a resumable plugin runner with per-file cache, **so that** the overnight batch is incremental and interrupt-safe.
**Depends on**: 2.3 (Lazy plugin registry), 4.2 (ML runtime scaffold analyze_ml.py), 2.4 (index stage).
**Acceptance Criteria**:
- Cached results are not recomputed.
  - *Given* 100 indexed files and `folder_year@1` already stored for 60, *When* `analyze --plugins folder_year` runs, *Then* the summary prints `60 cached / 40 computed` and the plugin is called 40 times.
- A raising plugin does not abort the run, and failures are retryable.
  - *Given* a plugin that raises on file 7 of 10, *When* run, *Then* 9 evidence rows are stored, 1 error row goes to `errors.jsonl`, exit code is 0 with `1 failed; rerun with --retry-failed`.
  - *Given* `analyze --plugins X --retry-failed`, *When* run after the failure is fixed, *Then* only the files listed in `errors.jsonl` for X are recomputed (`1 retried / 0 failed`) and cached files are untouched.
  - *Given* each `errors.jsonl` row carries `attempts` and an `error_class`, *When* a retry fails again with the same `error_class`, *Then* the row's `attempts` becomes 2 and the file is *permanently failed*: it is still listed and counted (`37 failed -> errors.jsonl`) but `status` no longer counts it as incomplete analyze work (Story 10.3).
- An ML subprocess crash is mapped, not propagated.
  - *Given* the ML subprocess exits non-zero or is killed (OOM) mid-batch, *When* `analyze --plugins faces` observes it, *Then* the run prints `1 failed; rerun with --retry-failed`, rows committed before the crash stay (each file's results commit in one transaction, so no partial `faces` batch), and exit code is 0.
- Single analyzer at a time.
  - *Given* an `analyze` already holding `DATA/analyze.lock`, *When* a second starts, *Then* it exits 1 with `Another analyze is running (pid N). Wait, or remove DATA/analyze.lock if it crashed. Nothing was changed.`
- Interrupt safety.
  - *Given* a `KeyboardInterrupt` at file 51 of 100 with batch size 25, *When* caught, *Then* the first 50 rows are committed and the message `Saved 50. Resume: rerun the same command` prints.
- Ml-runtime plugins dispatch to the ML script (this story needs Story 4.2 for `ML_CMD`).
  - *Given* `--plugins faces` (runtime Ml), *When* run, *Then* `cli.py` invokes the canonical command constant `ML_CMD` (defined once in `pipeline/ml_dispatch.py` by Story 4.2, which runs earlier; this story imports it and adds the subprocess dispatch around it, never a second copy of the command line) with `--plugins faces --data-dir <DATA>` as a subprocess and streams its progress.
**Files**: `G/pipeline/runner.py`, `G/pipeline/ml_dispatch.py`, `G/cli_stages.py`, `G/tests/test_runner.py`

##### Task 2.5a: Runner core (cache check, batch commit, error rows, corpus-scope passes, `analyze.lock`) (M)
##### Task 2.5b: `analyze` command, `--retry-failed`, ML subprocess dispatch and exit mapping, progress with cached/computed counts (S)

#### Story 2.6: Fusion Layer A (hard guards)
**As an** operator, **I want** guards that no score can override, **so that** impossible dates are never written (ADR-003; ship before Layer B).
**Depends on**: 2.1 (Contract types).
**Acceptance Criteria**:
- Birth/death bounds.
  - *Given* a `Person(birth=1972-03-04)` identified in a file and a folder interval 1965..1975, *When* guards apply, *Then* the surviving interval is `1972-03-04..1975-12-31` and `BirthDeathBounds` is recorded in provenance.
- Folder-year bounds with configurable k.
  - *Given* folder year 1990 and `k=2`, *When* an era vote says 1999, *Then* 1999 is pruned and `FolderYearBounds` fired.
- Anchors are fixed points.
  - *Given* a file with camera EXIF `2003-07-04`, *When* guards apply, *Then* status is `Anchor` and no plugin vote changes the interval.
- Upload-window ceiling.
  - *Given* an interval whose latest bound is 2026-10-01 and `UploadWindow` start 2025-09-01 with no anchor in the window for that album, *When* guards apply, *Then* the ceiling prunes dates at or after 2025-09-01 and a pre-1995 scan cannot resolve to the upload window.
- Contradiction -> conflict.
  - *Given* birth 1972 and a folder interval 1950..1960, *When* guards apply, *Then* the interval is empty and status is `Conflict`.
**Files**: `G/pipeline/fusion.py`, `G/tests/golden/fusion/guards_*.json`, `G/tests/test_fusion_guards.py`

##### Task 2.6a: `Guard` protocol + five guards as pure functions (M)
##### Task 2.6b: Golden-file cases (one JSON per guard plus combined) and property tests (S)

#### Story 2.7: Fusion Layer B (weighted per-year log-score)
**As an** operator, **I want** soft evidence combined with a correlated-vote discount, **so that** several weak plugins cannot jointly exceed what their shared signal justifies.
**Depends on**: 2.6 (Fusion Layer A hard guards).
**Acceptance Criteria**:
- Highest-mass contiguous window and confidence.
  - *Given* surviving years 1976..1984 and an age vote centered 1980 (sigma 2, weight 1.0), *When* scored, *Then* the point estimate is 1980 and confidence equals the mass in the chosen window (golden value in `fusion/layerb_age_only.json`).
- Correlated votes are discounted.
  - *Given* two evidence rows in the same `correlation_group` ("faces") each voting 1980 at weight 1.0 and `group_cap=1.5`, *When* scored, *Then* the combined weight is at most 1.5, not 2.0.
- Abstain contributes nothing.
  - *Given* a base case plus an `Abstention` row, *When* scored, *Then* the output equals the base case byte for byte.
- Too few independent voters -> review.
  - *Given* `min_independent_voters=2` and one surviving voter group, *When* fused, *Then* status is `Review`.
- Threshold is a pure rerun.
  - *Given* stored evidence and `--min-confidence` changed from 0.8 to 0.6, *When* `fuse` re-runs, *Then* no plugin is invoked and statuses change only where confidence lies in [0.6, 0.8).
**Files**: `G/pipeline/fusion.py`, `G/tests/golden/fusion/layerb_*.json`, `G/tests/test_fusion_scoring.py`

##### Task 2.7a: Year-axis scorer, dependence discount, window selection (M)
##### Task 2.7b: Golden cases + monotonicity/idempotence property tests (S)

#### Story 2.8: `fuse` command and `decisions` table
**As an** operator, **I want** a per-file `DateDecision` stored with voters and guards, **so that** the review list and writes derive from it.
**Depends on**: 2.5 (analyze runner), 2.7 (Fusion Layer B weighted per-year log-score), 7.1 (decisions.py append-only log).
**Acceptance Criteria**:
- Writes `decisions` rows and prints a status histogram.
  - *Given* 10 indexed files with stored evidence, *When* `fuse` runs, *Then* `decisions` has 10 rows and the output prints counts per `DecisionStatus`.
- Conflicts are never `Eligible`.
  - *Given* a `Conflict` decision, *When* `fuse --min-confidence 0.0` runs, *Then* it remains `Conflict`.
- `fuse` never touches write state.
  - *Given* a file with a `Verified` journal row, *When* `fuse` re-runs, *Then* its `decisions` row is recomputed from evidence and the file's `WriteState` is unchanged (it is a join over `state.db`, not a `decisions` column).
- Owner overrides survive deleting the derived store.
  - *Given* `DATA/review/decisions.jsonl` holding a `set` `ReviewDecision` for file F (date 1976-06) and `pipeline.db` deleted, *When* `index` and `fuse` run again, *Then* `fuse` re-folds the log (Story 7.1 fold) into a `UserOverride` `Observation` (confidence 1.0, `hard=True`) and F is `UserOverride` again; overrides gate uploads, so they must not live only in `pipeline.db`. (Story 7.2 repeats this end to end.)
- `fuse` has no dependency on near-duplicate grouping. (Near-duplicate propagation is ordinary evidence emitted by the Story 6.1 `dup_group` plugin and consumed by the generic scorer; this story's hard dependency on 6.1 is removed.)
**Files**: `G/pipeline/fuse_service.py`, `G/cli_stages.py`, `G/tests/test_fuse_service.py`

##### Task 2.8a: Service wiring evidence -> guards -> scoring -> persisted decision, including the `decisions.jsonl` re-fold into `UserOverride` evidence (S)
##### Task 2.8b: CLI + status histogram (S)

### Epic 3: Date-parsing, folder and filename plugins, and the `ai_enrich` seam
**Goal**: The legacy heuristics become the first plugins so the old path and the new path are the same path.

#### Story 3.1: `folder_year` plugin
**As an** operator, **I want** folder names emitted as interval evidence, **so that** fusion can intersect them.
**Depends on**: 1.4 (dateparse.py with golden tests filename and f), 2.1 (Contract types), 2.3 (Lazy plugin registry).
**Acceptance Criteria**:
- Emits interval with precision-based confidence and `placeholder` flag.
  - *Given* a file in the folder `1985-1990`, *When* `folder_year.analyze` runs, *Then* it returns `Observation(Date, PartialDate.range(1985-01-01, 1990-12-31))` with `Confidence <= 0.5` and no point estimate (a Year/Range/Decade folder has an interval, never a fabricated point).
- Abstains with no year.
  - *Given* the folder `Misc scans`, *When* analyzed, *Then* it returns `Abstention(reason="no_year_in_folder")`.
**Files**: `G/plugins/folder_year.py`, `G/plugins/registry.d/folder_year.toml`, `G/tests/test_plugin_folder_year.py`

##### Task 3.1a: Plugin + `registry.d` entry file (S)
##### Task 3.1b: Tests incl. golden parity with `dateparse.json` (XS)

#### Story 3.2: `filename_date` plugin
**As an** operator, **I want** filename dates emitted as evidence, **so that** `IMG_YYYYMMDD` camera names act as anchors.
**Depends on**: 1.4 (dateparse.py with golden tests filename and f), 2.1 (Contract types), 2.3 (Lazy plugin registry).
**Acceptance Criteria**:
- Camera-style filename -> anchor-grade evidence.
  - *Given* `IMG_20150102_134501.jpg`, *When* analyzed, *Then* Evidence is `2015-01-02` Day with `Confidence >= 0.9` and `anchor_candidate=True`.
- Non-capture names abstain.
  - *Given* `Scan_0001.jpg`, *When* analyzed, *Then* abstain with `non_capture_prefix`.
- Filename date conflicting with folder year raises a flag, not an override.
  - *Given* `IMG_20190101.jpg` in folder `1995`, *When* fused, *Then* the decision is `Conflict` (FolderYearBounds vs filename anchor) and routed to review.
**Files**: `G/plugins/filename_date.py`, `G/plugins/registry.d/filename_date.toml`, `G/tests/test_plugin_filename_date.py`

##### Task 3.2a: Plugin using `dateparse` (S)
##### Task 3.2b: Tests + conflict case through `fuse_service` (S)

#### Story 3.3: `ai_enrich` seam (Isolate via seam)
**As an** operator, **I want** the hardcoded family-event heuristics wrapped as an `event` plugin, **so that** they become data behind the contract while `infer` keeps working until parity is shown.
**Depends on**: 1.5 (Stop producing placeholder dates; unify media), 2.3 (Lazy plugin registry).
**Acceptance Criteria**:
- `infer` output unchanged.
  - *Given* the fixture `G/tests/golden/enrich_parity.json` (inputs captured from `enrich_mapping_data` on 30 representative albums before the change), *When* `enrich_mapping_data` runs after the change, *Then* its outputs are identical.
- The `event` plugin reproduces the same dates as intervals.
  - *Given* the album `Christmas 1994` with the legacy rule producing `1994-12-25`, *When* `event.analyze` runs, *Then* it returns `1994-12-01..1994-12-31` Month with the rule id in provenance.
- Placeholder `YYYY:01:01` is no longer produced by the plugin.
  - *Given* the album `1987` , *When* analyzed, *Then* `event` abstains (folder_year owns it).
- Plugin drift is reviewable, and the Adapter has an exit.
  - *Given* `G/tests/golden/event_plugin.json` (the plugin's outputs, which intentionally differ from legacy: Month intervals, abstain on year-only), *When* the plugin changes, *Then* the golden diff shows it; `enrich_parity.json` pins legacy behavior only. *Given* Story 2.8 and Story 7.2 are complete, *When* Task 10.5c runs (the final wave; it is the only task that may edit `cli.py` to drop `infer_cmd`), *Then* `ai_enrich.enrich_mapping_data` and `infer_cmd` are deleted and a test fails if anything still imports them.
**Files**: `G/plugins/event.py`, `G/plugins/event_data.py`, `G/plugins/registry.d/event.toml`, `G/ai_enrich.py`, `G/tests/golden/enrich_parity.json`, `G/tests/golden/event_plugin.json`, `G/tests/test_enrich_parity.py`

##### Task 3.3a: Capture parity golden from current code (S)
- Files: `G/tests/golden/enrich_parity.json`, `G/tests/test_enrich_parity.py`
##### Task 3.3b: `event` plugin reading the hardcoded table moved to `G/plugins/event_data.py` (S)
- Files: `G/plugins/event.py`, `G/plugins/event_data.py`, `G/plugins/registry.d/event.toml`
##### Task 3.3c: Parity test (legacy only) + `event_plugin.json` golden; mark `ai_enrich.enrich_mapping_data` legacy with a deprecation log line (XS)
- Files: `G/ai_enrich.py`, `G/tests/golden/event_plugin.json`, `G/tests/test_enrich_parity.py`

#### Story 3.4: `exif_anchor` plugin
**As an** operator, **I want** real camera EXIF dates treated as the strongest anchors and scanner dates as upper bounds, **so that** true dates are never overwritten and scan dates are never mistaken for capture dates.
**Depends on**: 1.9 (Legacy placeholder detector and quarantine re), 2.3 (Lazy plugin registry).
**Acceptance Criteria**:
- Real EXIF -> Anchor.
  - *Given* an `ExifSnapshot(DateTimeOriginal=2003:07:04 10:00:00, Software=None, Make="Canon")` classified `Genuine` by Story 1.9, *When* analyzed, *Then* Evidence is `2003-07-04` Day, `Confidence 0.98`, `anchor_candidate=True`.
- Scanner software -> upper bound only.
  - *Given* `ExifSnapshot(CreateDate=2012:03:10, Software="Epson Scan")`, *When* analyzed, *Then* Evidence is `latest=2012-03-10` with `earliest` unbounded and `scan_date=True`, not an anchor.
- Legacy placeholders and suspect dates are never anchors, whatever else the file carries.
  - *Given* `ExifSnapshot(DateTimeOriginal=2021:01:01 12:00:10, Make="Canon")` classified `LegacyPlaceholder` or `Suspect` by Story 1.9 (`anchor_eligible` False; anchors admit only `Genuine`, never `Suspect`), *When* analyzed, *Then* no `anchor_candidate` evidence is produced: it emits a low-confidence `Observation` with reason `legacy_placeholder` (weight cap 0.1) or an `Abstention`, and `Make`/`Software` do not rescue it. Only a `Genuine`-classified (or owner `confirm-genuine`) date becomes an `Anchor`; a `Suspect` or `LegacyPlaceholder` date does not, even for a file with a camera `Make`.
  - *Given* a `LegacyPlaceholder` with `date_kept=True` (Day-precision folder date, Story 1.9) *When* analyzed, *Then* it emits `folder_day` evidence (that Day-precision date, `Confidence <= 0.6`, `anchor_candidate=False`) instead of the 0.1-weight observation.
  - *Given* a video (QuickTime `CreateDate`), *When* analyzed, *Then* no anchor evidence is produced (videos are out of scope for classification, Story 1.9).
- Existing real EXIF is never overwritten by plan building, but an anchor is only upload-ready when its date is on disk (enforced in 8.4 and 9.2; consistency review B1).
  - *Given* an anchor with `source=exif` whose on-disk `DateTimeOriginal` is `Genuine` and equals the decision, *When* `plan` runs, *Then* it emits no write for it (its `OnDiskDate` is backed).
  - *Given* an anchor with `source=filename` (`IMG_20150102.jpg`, no EXIF date) or `source=owner_album`, or a `UserOverride`, *When* `plan` runs, *Then* it DOES emit a journaled write of the decision date (Story 8.4), and the file is upload-ready only after that write is `Verified`.
**Files**: `G/plugins/exif_anchor.py`, `G/plugins/registry.d/exif_anchor.toml`, `G/tests/test_plugin_exif_anchor.py`

##### Task 3.4a: Plugin + reader dependency (`exif_reader.read_tags` from 1.9; full `ExifSnapshot` batch read lands in 8.2) + `placeholders.anchor_eligible` gate (S)
##### Task 3.4b: Tests incl. Software-name table (XS)

#### Story 3.5: Printed date-stamp OCR plugin (spike-first; Ml runtime)
**As an** operator, **I want** film-camera corner date stamps read, **so that** the highest-accuracy signal (features.md section 6) is used where present.
Requirement trace: beyond the written In Scope list as a separate item, it serves In Scope 3 (date inference plugins) and Success Metric 2 (error on held-out anchors) as the highest-accuracy date signal; adds a system OCR dependency (`tesseract` or `rapidocr`), engine UNVERIFIED until the spike.
**Depends on**: 4.2 (ML runtime scaffold analyze_ml.py), 2.3 (Lazy plugin registry).
**Acceptance Criteria**:
- Stamp read with ambiguity handled.
  - *Given* a fixture crop containing orange digits `'96 3 14`, *When* analyzed, *Then* Evidence is `1996-03-14` Day with `Confidence 0.7` pending calibration, validated against the folder interval.
- Reset-clock stamps abstain.
  - *Given* a stamp reading `1 1 00`, *When* analyzed, *Then* abstain with reason `suspect_reset_clock`.
- OCR engine chosen by spike.
  - *Given* 30 owner-supplied or synthetic stamp crops, *When* the spike compares candidate engines (tesseract via `pytesseract`, `rapidocr-onnxruntime`), *Then* the chosen engine and its accuracy are recorded in the story's PR and ADR-004 addendum (engine choice is UNVERIFIED today).
**Files**: `G/ml_plugins/date_stamp.py`, `G/plugins/registry.d/date_stamp.toml`, `G/tests/test_plugin_date_stamp.py`

##### Task 3.5a: Engine spike on synthetic stamp images (S)
##### Task 3.5b: Corner-crop + parse (day/month order, 2-digit year pivot) + plugin (M)
##### Task 3.5c: Tests with synthetic image fixtures (S)

---

## Phase 3: Analysis plugins (faces, age, era)

### Epic 4: Face clustering and identity labeling
**Goal**: Local face detection, embedding, clustering, and owner-labeled identity, with human labels stored separately and never overwritten (pitfalls rule 6).

#### Story 4.1: [SPIKE] CPU timing on 200 images
**Timing**: run first (W2); no production code.
**As an** operator, **I want** measured CPU timing before committing plugin order, **so that** the overnight-batch SLO is checked (research/stack.md s1: speed UNVERIFIED).
**Depends on**: 1.1 (Test harness, DataDir, tool/path resolution).
**Acceptance Criteria**:
- Timing report exists for detect and embed.
  - *Given* a random sample of 200 images from the mounted drive (`/run/media/tstapler/EE5B-3D9B`), *When* `G/spikes/time_faces.py` runs InsightFace buffalo_l (CPU, det_size 640 and 480) in 1, 4 and 8 worker settings, *Then* it prints images/sec, faces/image, decode-vs-inference split, CPU model, onnxruntime version, and the extrapolated seconds for 17,145 images.
- Decision recorded.
  - *Given* the report, *When* extrapolated total exceeds 12 hours on the best setting, *Then* ADR-006 is amended to default to `det_size=(480,480)` / `buffalo_s` and plugin ordering puts faces last; otherwise it records the chosen settings.
**Files**: `G/spikes/time_faces.py`, `project_plans/gphotos-organizer-pipeline/decisions/ADR-006-face-models-and-licensing.md`

##### Task 4.1a: Timing script (S)
##### Task 4.1b: Run on sample, record numbers and amend ADR-006 (XS; wall-clock: drive mounted)

#### Story 4.2: ML runtime scaffold (`analyze_ml.py`)
**As a** developer, **I want** a separate PEP 723 script pinned to Python 3.12, **so that** `cli.py` never resolves onnxruntime/torch (ADR-004).
**Depends on**: 2.2 (Two stores derived + source of truth , migrat).
**Acceptance Criteria**:
- Shares the derived-store schema, checks versions, and never writes the source-of-truth store.
  - *Given* the canonical constant `ML_CMD = ["uv", "run", "--python", "3.12", "G/analyze_ml.py"]`, defined here once in `pipeline/ml_dispatch.py` (Story 2.5 imports it), invoked with `--plugins noop --data-dir /tmp/gpo-test` against a `pipeline.db` seeded through `pipeline/store.py` (Story 2.2) with three `FileRecord` rows (not `cli.py index`, which is a same-wave story), *When* run, *Then* it writes one `noop` evidence row per file using `pipeline/store.py` and exits 0.
  - *Given* a `pipeline.db` or `state.db` whose `schema_version` differs from the code's expected version, *When* the script starts, *Then* it refuses with the schema-mismatch message (Story 2.2).
  - *Given* the script runs, *When* it opens `state.db`, *Then* the connection is `mode=ro` (a write attempt raises); labels and constraints are read, never written, so `cli.py` stays the only `state.db` writer.
- `cli.py` stays light.
  - *Given* `cli.py`'s PEP 723 block, *When* checked by `test_cli_deps.py`, *Then* it contains none of `onnxruntime`, `torch`, `insightface`, `scikit-learn`, `open_clip_torch`, and `requires-python = ">=3.11"`.
- Models are fetched explicitly with checksum, offline failure is clean.
  - *Given* no network, *When* `models fetch faces` runs, *Then* it prints `Could not download model buffalo_l (<reason>). Plugin 'faces' disabled for this run; others continue. Retry: gphotos-organizer models fetch faces` and exits 1; `models check` lists cached/missing with sizes.
**Files**: `G/analyze_ml.py`, `G/ml_plugins/__init__.py`, `G/ml_plugins/noop.py`, `G/plugins/registry.d/noop.toml`, `G/pipeline/models_cache.py`, `G/pipeline/ml_dispatch.py`, `G/cli_models.py`, `G/tests/test_cli_deps.py`, `G/tests/test_ml_boundary.py`

##### Task 4.2a: Script with `requires-python = ">=3.11,<3.13"`, the single `ML_CMD` definition in `pipeline/ml_dispatch.py` (Story 2.5 imports it), `noop` plugin, read-only `state.db` opener, schema-version check (S)
- Files: `G/analyze_ml.py`, `G/ml_plugins/__init__.py`, `G/ml_plugins/noop.py`, `G/plugins/registry.d/noop.toml`, `G/pipeline/ml_dispatch.py`
##### Task 4.2b: `models fetch|check` in `cli_models.py` with checksum and model dir in `DATA/models` (S; this is the UX-25 `models fetch <plugin>` command)
- Files: `G/pipeline/models_cache.py`, `G/cli_models.py`, `G/tests/test_ml_boundary.py`
##### Task 4.2c: Extend `test_cli_deps.py` with the ML denylist (the Pillow/tomli-w allow-list is Story 1.1d); import-isolation test (XS)
- Files: `G/tests/test_cli_deps.py`, `G/tests/test_ml_boundary.py`

#### Story 4.3: `faces` plugin (detect + embed)
**As an** operator, **I want** face boxes, quality, and 512-d embeddings stored per `FaceId`, **so that** clustering and age run without re-reading images.
**Depends on**: 4.1 (the CPU timing spike), 4.2 and the Story 5.6 anchor-census verdict. The real overnight batch runs only if 5.6 recorded GO; on NO-GO the code may still land but no real-corpus ML batch is started (pre-mortem failure mode 3).
**Acceptance Criteria**:
- Stores faces with quality.
  - *Given* a fixture image with two faces (det_score 0.99 and 0.4, sizes 180px and 40px), *When* analyzed, *Then* two `faces` rows exist with `quality` computed and the 40px face flagged `low_quality` and excluded from centroids.
- Downscale before detect.
  - *Given* a 6000x4000 scan, *When* analyzed, *Then* detection ran on a 1600px-longest-side copy and bbox is stored in original coordinates.
- Unreadable file is an error row, not a crash.
  - *Given* a truncated JPEG, *When* analyzed, *Then* one error row and abstain evidence `decode_failed`.
- Embeddings in 0600 DB only.
  - *Given* a completed run, *When* file modes under `DATA` are listed, *Then* all are 600/700.
**Files**: `G/ml_plugins/faces.py`, `G/plugins/registry.d/faces.toml`, `G/pipeline/face_store.py`, `G/pipeline/migrations/pipeline/s0403_faces.sql`, `G/tests/test_face_store.py`

##### Task 4.3a: Embedding/box storage schema + repository (S)
##### Task 4.3b: Plugin using InsightFace per ADR-006 with worker pool (sessions created after fork) (M)
##### Task 4.3c: Tests with a stub detector returning canned boxes (S)

#### Story 4.4: Cluster pass
**As an** operator, **I want** deterministic, versioned face clusters with noise left unknown, **so that** labeling is tractable and reruns do not shuffle ids.
**Depends on**: 4.3 (faces plugin detect + embed).
**Acceptance Criteria**:
- Deterministic.
  - *Given* 60 synthetic L2-normalised embeddings forming 3 tight groups plus 5 outliers and a fixed seed, *When* clustered twice with input order shuffled, *Then* both runs give the same partition (after sorting inputs by `FaceId`) with outliers labeled -1.
- Constraints override the algorithm.
  - *Given* a `cannot-link` between faces f1 and f2 that HDBSCAN placed together, *When* clustering reruns, *Then* f1 and f2 are in different clusters.
- Labels keyed by `FaceId`.
  - *Given* a label on `FaceId(K1,bbox)`, *When* a new `cluster_run_id` is produced, *Then* the label is still attached to that face.
- Labels and constraints live in the source-of-truth store, which the cluster pass only reads.
  - *Given* `labels` and `constraints` rows in `state.db` (migration `s0404_labels_constraints`) and a deleted `pipeline.db`, *When* clustering reruns after `analyze --plugins faces`, *Then* the constraints are still applied and the labels still attach; the ML script opens `state.db` read-only.
**Files**: `G/ml_plugins/cluster.py`, `G/pipeline/constraints.py`, `G/pipeline/migrations/state/s0404_labels_constraints.sql`, `G/pipeline/migrations/pipeline/s0404_clusters.sql`, `G/tests/test_cluster.py`

##### Task 4.4a: HDBSCAN pass (scikit-learn, L2-normalise, `min_cluster_size=3..5`, `min_samples` note: sklearn includes the point itself) (M)
##### Task 4.4b: Constraint application (must-link merge, cannot-link split) (S)
##### Task 4.4c: Tests with synthetic embeddings (XS)

#### Story 4.5: People file and cluster labeling commands
**As an** operator, **I want** to enter birth dates and label clusters in the terminal first, **so that** identity is owner-confirmed (ADR-009).
**Depends on**: 4.4 (Cluster pass), 7.1 (decisions.py append-only log), 7.2 (Terminal review).
**Acceptance Criteria**:
- People are added with validation.
  - *Given* `people add "Grandma Ruth" --born 1931-05-02 --died 2009-11-30`, *When* run, *Then* `DATA/people.toml` contains the entry and `--born 2031-01-01` is rejected with `Birth date is in the future. Example: --born 1931-05-02`.
- Ordering (consistency review C6): the HTML contact sheet is Story 7.3, which runs after this story because it needs the people file. This story therefore ships and tests the labeling commands against fixtures and a terminal table (`review list --clusters` prints cluster id, face count, estimated year range, top-3 album ids by count, ordered by expected gain, the files resolved per label, exactly as in UX S2, so the first 20 labels cover the most files; the header prints `Cluster run CR7` and a `Queued` column); the owner's labeling pass on REAL clusters is an owner step of Story 7.3, after `review sheet --cluster` exists. Story 4.6's real-data acceptance and Story 5.4's real run wait for that pass.
- Cluster labels and face membership are append-only decisions, reached through the Story 7.2 handler registry (this story registers the `cluster_label` and `face_member` kind handlers in `pipeline/cluster_review.py`, so `review accept|reject|skip C12` and `C12/F3` need no second command registration). Semantics are fixed by ADR-009 and UX S2: only a cluster-level `accept` labels; a face-level action never labels by itself.
  - *Given* cluster C12 (a fixture cluster; on real data the owner views its sheet from Story 7.3 first), *When* `review accept C12 --name "Grandma Ruth"` runs, *Then* a `ReviewDecision(kind=cluster_label, item=C12, action=accept, name="Grandma Ruth")` line is appended to `decisions.jsonl` and `labels` rows are created per member `FaceId` that is not face-rejected.
  - *Given* C12 with 60 members, *When* `review reject C12/F3` and then `review accept C12 --name "Grandma Ruth"` run, *Then* a `face_member` reject line for F3 (carrying the canonical `FaceId`) is appended, a cannot-link from F3 to the rest of C12 is recorded, 59 `labels` rows are created, the output says `Labeling 59 faces (1 rejected).`, and `review split C12 --faces F3,F9` is equivalent to two face rejects in one action.
  - *Given* `review accept C12/F5`, *When* run, *Then* the face is recorded as a confirmed member and is preferred as an exemplar by Story 4.6; no label is created by that command alone.
  - *Given* a face id not in the cluster, *When* `review reject C12/F99` runs, *Then* `Faces F99 are not in C12 (members: F1-F60). Nothing was changed.`; *Given* every face rejected then `review accept C12 --name X`, *Then* `All 60 faces of C12 are rejected; nothing to label. Use: review reject C12`.
- Names resolve against `people.toml` (UX-77).
  - *Given* `people.toml` holding `Grandma Ruth` (alias `Ruthie`), *When* `review accept C12 --name "grandma ruth"` and `--name Ruthie` run, *Then* both resolve to `Grandma Ruth` and print `Using 'Grandma Ruth' (matched 'grandma ruth').`
  - *Given* `--name "Grandma Rut"`, *When* run, *Then* it exits 1 with `No person 'Grandma Rut'. Did you mean 'Grandma Ruth'? Rerun with that name, or add her: people add "Grandma Rut" --born YYYY-MM-DD. Nothing was changed.`; with `--new-person` it creates a stub entry and prints the no-birth-date warning, and no other path creates a person.
- Queued merge and split intents are visible and costed (UX-78).
  - *Given* `review merge C12 C40`, *When* run, *Then* it prints `Recorded must-link C12+C40 (1 queued intents). Effective at the next cluster pass: gphotos-organizer analyze --plugins faces (re-clusters cached faces only; last cluster pass took N s; detection is not rerun).` with `no estimate yet` when no `plugin_seconds{cluster}` row exists, and `review list --clusters` shows a `Queued` column (`merge->C40`, `split 2 faces`) until a cluster pass consumes the constraint.
- Merge and split are explicit actions.
  - *Given* clusters C12 and C40, *When* `review merge C12 C40` runs, *Then* must-link constraints are recorded and the next cluster pass shows one cluster.
- Merge and split have one definition.
  - *Given* `review merge C12 C40`, *Then* exactly one `cluster_link` line with `action=merge` is appended; *Given* `review split C12 --faces F3,F9`, *Then* exactly two `face_member` reject lines sharing one `batch_id` are appended (no `split` line exists) and one `review undo-last` retracts both.
- Cluster ids are guarded by the cluster run (UX S2 rule g).
  - *Given* `review accept C12 --name N --run CR7` while the current run is CR9, *When* run, *Then* it exits 1 with `C12 was numbered by cluster run CR7 but the current run is CR9; ids were renumbered. List: review list --clusters. Nothing was changed.` and nothing is appended; the same holds for `reject`, `skip`, `merge`, `split` and the no-JS card commands the sheet prints (each carries `--run`); without `--run` the confirmation echoes `C12: 60 faces, est. 1962-2004, top album A7, run CR9`.
  - *Given* a cluster-level `reject` made in run CR7 and a new cluster pass CR9, *When* `review list --clusters` runs, *Then* that cluster shows Undecided with `reset by cluster pass CR9`, while labels, face rejects and merge/split intents (stored by `face_id`) are unchanged.
  - *Given* C12 (59 labeled `Grandma Ruth`) and C40 (12 labeled `Grandma Ruth`) merged into a new cluster C5 by a recluster, *When* `review list --clusters` runs, *Then* C5 reads `Accepted: Grandma Ruth` once every non-rejected member is labeled and `Partly labeled: Grandma Ruth (59 of 71)` before that; *Given* a cluster whose members carry two names, *Then* it reads `Mixed names: Grandma Ruth / Aunt May` and `review accept` on it is refused with the merge-refused message; status is derived from the `labels` rows, never from the old cluster-level line.
- Fold order is deterministic (UX S2 rules e and f).
  - *Given* `review accept C12 --name N` then `review reject C12/F3`, *When* run, *Then* F3's `labels` row is removed in the same command (`Removed 1 label (C12/F3). Cluster C12 now labels 59 faces.`), and `review accept C12/F3` or a re-run of the cluster accept restores it; *Given* the reject first and the accept second, *Then* 59 labels are created.
  - *Given* C12 Accepted as N with 59 labels, *When* `review reject C12` runs without `--apply`, *Then* it prints `C12 is Accepted as 'N' (59 labels). Rejecting removes those 59 labels. Apply: review reject C12 --apply` and changes nothing; with `--apply` the labels are removed and `review undo-last` restores them; on an Undecided cluster `review reject C12` is immediate.
- People can be corrected (`people edit`).
  - *Given* `people edit "Grandma Ruth" --born 1931-05-03`, *When* run, *Then* `DATA/people.toml` is rewritten atomically (previous copy kept as `people.toml.bak`), the output echoes the old and new values, and `--died` earlier than `--born` is rejected with `Death date 1930-01-01 is before birth date 1931-05-02. Check both with: people list`; an unknown name prints `No person 'X'. List: people list`; `--name "New Name"` renames and keeps `labels` rows (they reference the name through `person_id`, not the string).
- Names stay out of logs.
  - *Given* the above, *When* `DATA/logs/*.jsonl` is searched for "Grandma Ruth", *Then* zero matches.
- Labels survive deletion of the derived store.
  - *Given* labels created by `review accept C12 --name ...`, *When* `pipeline.db` is deleted and rebuilt, *Then* the `labels` rows in `state.db` (and the `state-events.jsonl` mirror) are intact and re-attach to `FaceId`s.
**Files**: `G/pipeline/people.py`, `G/pipeline/name_resolve.py`, `G/pipeline/cluster_review.py`, `G/cli_people.py`, `G/cli_review_cluster.py`, `G/tests/test_people.py`

##### Task 4.5a: `people add|list|edit` subcommands + toml (S)
- Files: `G/pipeline/people.py`, `G/cli_people.py`, `G/tests/test_people.py`
##### Task 4.5b: `cluster_label` and `face_member` kind handlers (accept, reject, skip; `C12/F3` ids) plus `review merge|split|list --clusters` (with the `Queued` column) for clusters over the Story 7.1 `decisions.py` API (generic `kind` field; no edit to `decisions.py` or `pipeline/review.py`) (S)
- Files: `G/pipeline/cluster_review.py`, `G/cli_review_cluster.py`, `G/tests/test_people.py`
##### Task 4.5c: Tests + log-redaction check (S)
- Files: `G/tests/test_people.py`
##### Task 4.5d: Name resolution (`name_resolve.py`: case-insensitive, aliases, did-you-mean, `--new-person`) and the cluster-pass cost message (S)
- Files: `G/pipeline/name_resolve.py`, `G/pipeline/people.py`, `G/cli_review_cluster.py`, `G/tests/test_people.py`
##### Task 4.5e: Cluster run guard (`--run`, signature echo, per-run reset of cluster-level reject/skip), fold order (label removal on a later face reject), `review reject C12` preview on an Accepted cluster, and `merge`/`split` log shapes (S)
- Files: `G/pipeline/cluster_review.py`, `G/cli_review_cluster.py`, `G/tests/test_people.py`
Owner input (wall-clock): birth dates (Tyler) here; cluster labels on real data after Story 7.3 provides the sheets.

#### Story 4.6: Identity assignment evidence
**As an** operator, **I want** each face assigned to the nearest labeled exemplar under a strict threshold with top-2 ambiguity flagged, **so that** siblings and look-alikes are not auto-assigned.
**Depends on**: 4.5 (People file and cluster labeling commands).
**Acceptance Criteria**:
- Strict threshold.
  - *Given* a face at cosine similarity 0.52 to "Grandma Ruth" exemplars and `threshold=0.6`, *When* assigned, *Then* no `Person` evidence is emitted (abstain `below_threshold`).
- Ambiguity flagged.
  - *Given* top-1 similarity 0.71 (Ruth) and top-2 0.69 (Aunt Ann), *When* assigned, *Then* Evidence is emitted with `ambiguous=True` and `Confidence` capped at 0.4, and guards using this person are skipped.
- Person evidence activates birth/death guards.
  - *Given* a confident Ruth assignment (born 1931), *When* fused with a folder interval 1925..1935, *Then* `BirthDeathBounds` fires and prunes pre-1931.
**Files**: `G/ml_plugins/identity.py`, `G/tests/test_identity.py`

##### Task 4.6a: Assignment with exemplar sets per person per decade (M)
##### Task 4.6b: Tests with synthetic embeddings (S)

#### Story 4.7: License-clean fallback (YuNet + SFace)
**As an** operator, **I want** a swappable face model pack, **so that** weights can be replaced if the non-commercial license ever matters (ADR-006).
Requirement trace: not in the written In Scope list; it is a licensing hedge for In Scope 3 (face cluster plugin) and serves the Constraint "local by default" by keeping a fully permissive model available.
**Depends on**: 4.3 (faces plugin detect + embed).
**Acceptance Criteria**:
- Config switch.
  - *Given* `[plugins.faces] model="yunet_sface"`, *When* `analyze --plugins faces` runs on the fixture, *Then* embeddings are 128-d, stored with `model_id="sface"`, and cached rows for `buffalo_l` are untouched.
- Dimension mismatch is handled in clustering.
  - *Given* mixed models in the store, *When* clustering runs, *Then* it clusters per `model_id` and warns `Mixed embedding models: clustering per model`.
**Files**: `G/ml_plugins/faces_yunet.py`, `G/ml_plugins/faces.py`, `G/tests/test_faces_model_switch.py`

##### Task 4.7a: OpenCV Zoo adapter (checksum verified; Apache-2.0 claim is UNVERIFIED primary, confirm in `opencv_zoo` LICENSE) (M)
##### Task 4.7b: Model-id-aware clustering and tests (S)

### Epic 5: Age estimation and anchor calibration
**Goal**: Age is strong evidence only where calibration shows it (children), degrading gracefully elsewhere.

#### Story 5.1: `age` plugin
**As an** operator, **I want** an apparent-age estimate with a stated sigma per face, **so that** fusion can weight it by measured reliability.
**Depends on**: 4.3 (faces plugin detect + embed).
**Acceptance Criteria**:
- Preprocess for scans.
  - *Given* a color face crop and a B&W crop of the same person, *When* preprocessed, *Then* both are converted to grayscale and equalized before inference (`input_hash` identical for identical grayscale arrays), and faces under 60px abstain with `face_too_small`.
- Output is a distribution.
  - *Given* an estimated age 8, *When* emitted, *Then* Evidence carries `age_est=8` and `sigma` taken from the `CalibrationCurve` if present else a conservative default (children 3, adults 10) and the weight cap is `0.3` until calibrated.
- Baseline model via InsightFace `genderage`; MiVOLO evaluated, not required.
  - *Given* MiVOLO's weight license is UNVERIFIED, *When* the optional evaluation task runs, *Then* it records license text and the anchor MAE vs the baseline in ADR-006 and adopts only if the license permits personal use.
**Files**: `G/ml_plugins/age.py`, `G/tests/test_age.py`

##### Task 5.1a: Baseline plugin and preprocessing (M)
##### Task 5.1b: Optional MiVOLO evaluation (S; skipped if license blocks)

#### Story 5.2: Anchor registry
**As an** operator, **I want** trusted known-date photos pinned or excluded, **so that** calibration has ground truth and hold-out.
**Depends on**: 3.4 (exif_anchor plugin), 3.2 (filename_date plugin).
**Acceptance Criteria**:
- Anchors are collected from camera EXIF, dated filenames, owner-pinned albums, and `UserOverride`.
  - *Given* 100 files of which 30 have Day-precision `exif_anchor` evidence, *When* `anchors build` runs, *Then* `anchors` has 30 rows with `source=exif` and prints anchor counts per person-decade (a table).
- Owner can pin/exclude albums, and the pins are source-of-truth.
  - *Given* `anchors pin-album "Trip 1996" --trusted` without `--apply`, *When* run, *Then* it prints `Dry run: 212 files in 'Trip 1996' would become anchors (source=owner_album)` and the exact `--apply` command, and writes nothing (tier T1a).
  - *Given* `anchors pin-album "Trip 1996" --trusted --apply`, *When* run, *Then* the album's files become anchors with `source=owner_album` and a row is written to `state.db` `anchor_pins` (migration `s0502_anchor_pins`) so deleting `pipeline.db` does not lose them; `anchors exclude <file>` removes one.
- Legacy placeholders are never anchors.
  - *Given* 100 files of which 30 carry a `DateTimeOriginal` classified `LegacyPlaceholder` or `Suspect` (Story 1.9) and 20 carry genuine camera dates, *When* `anchors build` runs, *Then* only the 20 `Genuine` ones become `source=exif` anchors (`Suspect` is never admitted), the 30 are counted and printed per class as `excluded: legacy_placeholder N, suspect M` (N + M = 30), and calibration (5.3) and the hold-out report (5.5) are computed from the 20.
- A real anchor build needs a passed classifier precision gate.
  - *Given* no `DATA/placeholder-precision.json` with `passed=true` (Story 1.9), *When* `anchors build` runs on the real corpus, *Then* it exits 1 with `Anchors need a measured classifier precision of at least 0.98. Run: gphotos-organizer placeholders precision. Nothing was changed.` (fixture runs pass `--fixture`).
- Deterministic hold-out.
  - *Given* the same 30 anchors, *When* `HoldOut` is computed with seed s, *Then* the same 6 (20%) are held out on every run, independent of insertion order.
**Files**: `G/pipeline/anchors.py`, `G/pipeline/migrations/state/s0502_anchor_pins.sql`, `G/pipeline/migrations/pipeline/s0502_anchors.sql`, `G/cli_anchors.py`, `G/tests/test_anchors.py`

##### Task 5.2a: Anchor repository and builder (S)
##### Task 5.2b: Pin/exclude commands and hold-out split (S)
Owner input (wall-clock): trusted albums (Tyler).

#### Story 5.3: Calibration pass (corpus scope)
**As an** operator, **I want** per-plugin error measured against anchors by decade and by color/B&W, **so that** weights and sigmas are earned, not assumed (pitfalls rule 8).
**Depends on**: 5.1 (age plugin), 5.2 (Anchor registry).
**Acceptance Criteria**:
- Curve per plugin x decade x color x age band.
  - *Given* 40 training anchors with synthetic age estimates having known error N(0,4) years, *When* calibration runs, *Then* the stored sigma for that bucket is within 15% of 4.0 (golden) and `n=40` is recorded.
  - *Given* anchors whose estimated age is 6 and 44, *When* calibrated, *Then* they land in different `age_band` buckets (`child` = estimated age under 18 at the estimated date, `adult` = 18 or over), so Success Metric 2's separate child and adult targets can be evaluated.
- Sparse buckets are capped.
  - *Given* a bucket with fewer than `min_anchors=10`, *When* queried, *Then* `weight_cap=0.2` and the report prints `UNCALIBRATED (n=3)`.
- Held-out metrics are separate.
  - *Given* hold-out anchors, *When* calibration runs, *Then* held-out median and p90 absolute error are reported and never used to fit.
**Files**: `G/ml_plugins/calibrate.py`, `G/pipeline/calibration.py`, `G/pipeline/migrations/pipeline/s0503_calibration.sql`, `G/tests/test_calibration.py`

##### Task 5.3a: Curve fitting and persistence (M)
##### Task 5.3b: Weight-cap policy + report rows (S)
##### Task 5.3c: Synthetic-data tests (S)

#### Story 5.4: Age evidence -> date interval
**As an** operator, **I want** age converted to a date interval via the identified person's birth date, **so that** children's photos date to within a few years while adults degrade to wide intervals.
**Depends on**: 4.6 (Identity assignment evidence), 5.3 (Calibration pass corpus scope).
**Acceptance Criteria**:
- Date = birth + age with sigma.
  - *Given* `Person(birth=1980-06-01)`, age estimate 5, sigma 2, *When* converted, *Then* Evidence is centered 1985 with interval 1983-01-01..1987-12-31.
- Group photo uses the smallest-sigma face.
  - *Given* faces: child age 4 sigma 2 and adult age 40 sigma 10, *When* combined, *Then* the child's vote is used and the adult's is down-weighted; if the two implied years differ by more than the sum of sigmas, status flows to `Review` with reason `group_age_disagreement`.
- Implausible implied ages rejected.
  - *Given* implied age > 100 or < 0 for a cluster, *When* converted, *Then* the vote is dropped with reason `implausible_age`.
- Adults are capped.
  - *Given* an adult age 45, sigma 10 (uncalibrated), *When* fused alone, *Then* confidence stays below the default write threshold (0.8) so the file goes to review.
**Files**: `G/ml_plugins/age_to_date.py`, `G/tests/test_age_to_date.py`

##### Task 5.4a: Conversion + group-photo rule (M)
##### Task 5.4b: Tests (S)

#### Story 5.5: Held-out error report
**As an** operator, **I want** error by decade and color reported every run, **so that** the Success Metric (median error, ±2 children / ±8 adults targets) is measured.
**Depends on**: 5.4 (Age evidence -> date interval), 10.1 (Run report), 2.8 (fuse command and decisions table), 5.3 (Calibration pass corpus scope).
**Acceptance Criteria**:
- Report prints median/p90 per decade and per age band.
  - *Given* 10 held-out anchors with known errors, *When* `report accuracy` runs, *Then* it prints a table by decade, color/B&W and `age_band` (child under 18, adult) with n, median and p90. Targets are baseline-first (Success Metric 2): until the owner confirms targets in `DATA/config.toml [targets]` after the first held-out run, the pass/fail column reads `provisional (children ±2, adults ±8; baseline run, no target set)` and the first run is recorded as the baseline; once confirmed, it prints pass/fail against the confirmed values. Any `holdout_mae{plugin}` rows in `run_metrics` (for example the era regressor and its label-mean baseline from Story 6.3) are rendered generically next to it.
- Baseline then target (Owner Checklist item 9).
  - *Given* no `[targets]` table, *When* `report accuracy` runs, *Then* it exits 0 and ends with `Baseline recorded. Confirm targets in DATA/config.toml [targets] (median_years_child, median_years_adult), then rerun.`; *Given* targets set, *Then* the pass/fail column uses them.
- Success metric 1 audit line (decisions side).
  - *Given* decisions where a pre-1995 scan resolved inside the upload window, *When* the report runs, *Then* it prints `0` or lists offenders by name. The remote side (already-uploaded items, including those dated by legacy placeholders) is reported by Story 9.9, which this line points to: `Remote check: gphotos-organizer audit`.
**Files**: `G/report.py`, `G/cli_report.py`, `G/pipeline/accuracy.py`, `G/tests/test_accuracy_report.py`

##### Task 5.5a: Aggregation and rendering; `accuracy` subcommand in the `report` group (S)

#### Story 5.6: Anchor census and ML go/no-go checkpoint
**As an** operator, **I want** a read-only count of how many trustworthy anchors exist, and a pre-agreed verdict on whether face/age/era work can succeed, **so that** about 4.3M implementation CU (Epics 4, 5, 6 are 4,322k of the 18,286k, roughly 7.0M with verification) is not spent producing a review list because the corpus has too few anchors (pre-mortem failure mode 3).
Requirement trace: serves Success Metric 2 (calibration needs enough held-out anchors) and the Feasibility Risk "ground-truth anchors may be too sparse per person/decade". Starts before any real ML batch: Stories 4.3 and 6.2 depend on it.
Context (INFERRED from the measured figures in the plan header, to be replaced by this story's count): with the legacy placeholder population quarantined, roughly 170 files are `Genuine` EXIF dates (re-review 2 estimate), so the anchors are `Genuine` EXIF plus dated filenames plus owner-pinned albums plus `UserOverride`; `2021 random photos` (9,161 files, 53% of the corpus) has the weakest anchors.
**Depends on**: 1.9 (classes), 3.2 and 3.4 (filename and EXIF anchor evidence), 7.1 (`UserOverride` fold). To stay a wave ahead of the ML epics it does NOT depend on 5.2: owner-pinned albums are read from `DATA/trusted-albums.toml` (the owner's list, album ids only), which Story 5.2's `anchors pin-album` ingests later.
**Acceptance Criteria**:
- Census is read-only and reproducible.
  - *Given* `census` run on the fixture corpus (30 files: 10 camera EXIF, 10 dated filenames, 10 undated), *When* it runs, *Then* it prints anchors by source (`exif`, `filename`, `owner_album`, `user_override`), by decade, and by colour/B&W (from `print_cues`, Story 6.1, when available, else `unknown`), writes `DATA/reports/anchor-census-<ts>.md` plus `DATA/anchor-census.json`, and no media or database row other than that report is written (hashes equal).
  - Per person x decade counts appear only once labels exist (`labels` rows); before that the table says `persons: not yet labeled`.
- Pre-agreed minimums (stated here so the verdict is not argued after the fact; the owner may change them in Owner Checklist item 6 before the census runs). GO requires ALL of: total anchors >= 400; anchors in each of at least 3 decades >= 40; `Genuine` classifier precision gate (Story 1.9) passed; the owner's trusted-album list supplied (Unresolved Question 3). Otherwise the verdict is NO-GO.
  - *Given* a census of 170 anchors, *When* the verdict is computed, *Then* it prints `NO-GO: 170 anchors (< 400); decades with >= 40: 1 (< 3).` and exits 0 with the fallback below.
  - *Given* 450 anchors with 4 decades >= 40 and the gate passed, *When* computed, *Then* `GO` and it prints the per-decade table.
- Defined fallback on NO-GO (cheap path before buying face and age work): Epics 4, 5, 6 real-corpus batches are not started; the pipeline continues with the Core evidence only: `folder_year`, `filename_date`, `exif_anchor`, `print_cues`, `dup_group` and the `seq_neighbor` filename-sequence neighbor plugin (Task 6.1d), burst and duplicate-group propagation, and folder context, and everything unresolved goes to the review list by album. Code for Stories 4.x-6.x may still be merged and tested on fixtures, so the later GO is cheap. The 5.6 PR records the verdict and the fallback chosen.
- Success for `2021 random photos` is defined separately, on a held-out slice.
  - *Given* the owner dates 200 randomly chosen files of that album by eye (`review set`, owner effort, deterministic sample via `census --slice 200 --seed 7`), *When* `fuse` runs with the evidence available at the time of the check, *Then* `census` prints the fraction of the slice that reaches `Eligible` at the 0.8 threshold with the correct year; the pre-agreed target is at least 30% (changeable in Owner Checklist item 6), and below it the album is handled by album-level review rather than per-file inference.
**Files**: `G/pipeline/anchor_census.py`, `G/cli_census.py`, `G/tests/test_anchor_census.py`

##### Task 5.6a: Census aggregation over anchors, decades, colour, and the verdict function with the stated minimums (S)
##### Task 5.6b: `census` command, report, held-out slice measurement and tests (S; wall-clock: Tyler supplies the trusted-album list and dates the 200-file slice)

### Epic 6: Era-by-appearance
**Goal**: A low-weight tiebreaker built from cheap cues and a regressor on the owner's own dated photos (ADR-010), with an optional cloud variant.

#### Story 6.1: `print_cues` plugin and near-duplicate groups
**As an** operator, **I want** free non-ML cues and duplicate grouping, **so that** scan characteristics inform era and duplicates share one date.
Requirement trace: `print_cues` serves In Scope 3 (era-by-appearance, ADR-010); near-duplicate grouping is beyond the written In Scope list and serves Success Metric 2 (a duplicate of an anchored print inherits its date). It is optional for `fuse`: this story has no downstream hard dependency (Story 2.8's former dependency on it is removed).
**Depends on**: 2.3 (Lazy plugin registry).
**Acceptance Criteria**:
- Cues extracted.
  - *Given* a fixture scan with a white deckle border and sepia cast, *When* analyzed, *Then* Evidence kind `Era` is emitted with cue features (`border=deckle`, `cast=sepia`, `aspect=1.33`) and a wide interval (e.g. 1930..1975) at `Confidence <= 0.25`.
- Scanner EXIF treated as scan date only.
  - *Given* `Software="VueScan"`, *When* analyzed, *Then* no capture-date claim is made.
- Near-duplicates grouped.
  - *Given* two scans of the same print (one rotated 90 degrees, one cropped 5%) and one different photo, *When* dHash grouping runs with Hamming threshold 10, *Then* `dup_groups` has one group of 2.
- Duplicate propagation is ordinary evidence.
  - *Given* two files in one group where one is an `Anchor`, *When* the Corpus-scope `dup_group` plugin runs, *Then* the other gets an `Observation(Date, <anchor interval>)` at weight 0.5 with the anchor's `ContentKey` in provenance, and fusion needs no special-case code.
- Cheap-path fallback for an anchor-starved corpus (Story 5.6 NO-GO route): a filename-sequence neighbor propagates dates without any ML.
  - *Given* `IMG_0101.jpg` (anchor, 1994-07-04) and `IMG_0102.jpg`, `IMG_0103.jpg` (no date) in one folder, *When* the Core `seq_neighbor` plugin runs, *Then* the two files get `Observation(Date, <anchor interval widened by 3 days>)` at weight 0.4 with the anchor's `ContentKey` in provenance (correlation group `sequence`), and a file whose number is more than 3 away from any anchor, or a different folder, gets an `Abstention(reason="no_adjacent_anchor")`.
**Files**: `G/plugins/print_cues.py`, `G/plugins/dup_group.py`, `G/plugins/seq_neighbor.py`, `G/plugins/registry.d/print_cues.toml`, `G/plugins/registry.d/dup_group.toml`, `G/plugins/registry.d/seq_neighbor.toml`, `G/pipeline/dup_groups.py`, `G/pipeline/migrations/pipeline/s0601_dup_groups.sql`, `G/tests/test_print_cues.py`, `G/tests/test_seq_neighbor.py`

##### Task 6.1a: Cue extraction with Pillow (core runtime) (S)
- Files: `G/plugins/print_cues.py`, `G/plugins/registry.d/print_cues.toml`, `G/tests/test_print_cues.py`
##### Task 6.1b: dHash duplicate grouping incl. rotations (S)
- Files: `G/pipeline/dup_groups.py`, `G/pipeline/migrations/pipeline/s0601_dup_groups.sql`, `G/tests/test_print_cues.py`
##### Task 6.1c: `dup_group` Corpus-scope plugin emitting propagated evidence (S)
- Files: `G/plugins/dup_group.py`, `G/plugins/registry.d/dup_group.toml`, `G/pipeline/dup_groups.py`
##### Task 6.1d: `seq_neighbor` Core plugin (the cheap-path fallback) and tests (S)
- Files: `G/plugins/seq_neighbor.py`, `G/plugins/registry.d/seq_neighbor.toml`, `G/tests/test_seq_neighbor.py`

#### Story 6.2: Frozen embeddings cache
**As an** operator, **I want** CLIP/SigLIP image embeddings stored per `ContentKey`, **so that** the regressor trains and predicts without re-reading images.
**Depends on**: 4.2 and the Story 5.6 anchor-census verdict (same rule as Story 4.3: no real-corpus batch on NO-GO).
**Acceptance Criteria**:
- Embedding stored once per (key, model, preprocessing).
  - *Given* 5 fixture images, *When* `analyze --plugins era_embed` runs twice, *Then* 5 rows exist after the second run and the second run reports `5 cached`.
- Model choice recorded.
  - *Given* ONNX/torch availability, *When* the plugin loads, *Then* it records `model_id` (open_clip ViT-B/32 default; SigLIP optional via `transformers`) in provenance; if torch is unavailable it prints the install hint for the ML env.
**Files**: `G/ml_plugins/era_embed.py`, `G/pipeline/migrations/pipeline/s0602_embeddings.sql`, `G/tests/test_era_embed.py`

##### Task 6.2a: Embedding extraction plugin (M)
##### Task 6.2b: Tests with a stub encoder (XS)

#### Story 6.3: Era regressor trained on the owner's dated photos
**As an** operator, **I want** a calibrated regressor from embeddings to year distribution, **so that** era evidence beats zero-shot CLIP (MAE 15.8 per research) on this collection.
**Depends on**: 5.3 (Calibration pass corpus scope), 6.2 (Frozen embeddings cache).
**Acceptance Criteria**:
- Trains on folder-dated and anchor labels only, excluding hold-out.
  - *Given* 200 synthetic embeddings with years drawn from two Gaussians (1975 and 1998) and 40 hold-out, *When* trained, *Then* held-out MAE is below the label-mean baseline and the model file records the training-set `ContentKey` list hash.
- Output is low-weight.
  - *Given* a prediction 1982 +/- 9, *When* emitted, *Then* `weight_cap <= 0.25` and `correlation_group="appearance"`.
- Zero-shot baseline comparison logged.
  - *Given* the same held-out set, *When* training finishes, *Then* it writes `holdout_mae{plugin=era_regress|label_mean|zero_shot_clip}` rows to `run_metrics`, which Story 5.5's `report accuracy` renders next to its tables (this story does not edit the report).
- Model is retrained, versioned, invalidates only its own evidence rows.
  - *Given* a new anchor added, *When* retrain runs, *Then* `plugin_version` increments and other plugins' rows are untouched.
**Files**: `G/ml_plugins/era_regress.py`, `G/tests/test_era_regress.py`

##### Task 6.3a: Ridge/logistic over year bins with calibration (M)
##### Task 6.3b: Versioning, hold-out evaluation, tests (S)

#### Story 6.4: Optional `cloud_vision` plugin (`--allow-cloud`)
**As an** operator, **I want** an opt-in cloud vision estimate on an uncertain subset, **so that** hard cases get a second, independent opinion without leaking by default.
**Depends on**: 2.5 (analyze runner), 4.2 (ML runtime scaffold analyze_ml.py).
**Acceptance Criteria**:
- Not importable, not runnable without policy.
  - *Given* no `--allow-cloud`, *When* `analyze --plugins cloud_vision` runs, *Then* it exits 0 with the skip message and zero network calls (fake HTTP client asserts zero requests).
- Caps and logging.
  - *Given* `--allow-cloud --cloud-sample 50 --cloud-spend-cap 1.00` against 200 uncertain files, *When* run with a fake client priced $0.003/call, *Then* exactly 50 calls are made, each appended to `DATA/logs/cloud-send.jsonl` with `ContentKey`, bytes sent, model, prompt version, and the run summary prints `cloud_calls=50 est_cost=$0.15`.
- Image-only prompt; cached first answer.
  - *Given* a prompt template, *When* rendered, *Then* it contains no folder name or neighboring dates (asserted by test); a second run returns the cached answer without a call.
- Output is a low-weight range.
  - *Given* a response "1970s, year 1976", *When* parsed, *Then* Evidence interval is 1972..1980 with `weight_cap 0.25` and `cost=cloud` provenance.
**Files**: `G/ml_plugins/cloud_vision.py`, `G/pipeline/cloud_policy.py`, `G/tests/test_cloud_vision.py`

##### Task 6.4a: Policy plumbing, send log, caps (S)
##### Task 6.4b: Plugin with injected HTTP client, prompt template, parser (M)
##### Task 6.4c: Tests with fake client (S)
Owner decision (wall-clock): whether to run it on real data (Tyler); pricing must be rechecked (UNVERIFIED $4-$40).

---

## Phase 4: Human loop and EXIF writes

### Epic 7: Review flow
**Goal**: One review list for per-file decisions and the flagged albums (137 today), terminal-first, then static offline HTML (ADR-009).

#### Story 7.1: `decisions.py` (append-only log)
**As an** operator, **I want** every human decision journaled, **so that** history is inspectable and review resumes after interruption.
**Depends on**: 1.2 (Atomic JSON persistence all six write sites).
**Acceptance Criteria**:
- Latest wins on fold.
  - *Given* lines `accept C12` then `reject C12`, *When* folded, *Then* C12 resolves to `reject`.
- Append is atomic per line and survives a torn tail.
  - *Given* a file whose last line is truncated JSON, *When* loaded, *Then* the valid prefix loads, the torn line is reported and skipped.
- `update-album` is routed through it.
  - *Given* `update-album --id A7 --date 1994-12-25`, *When* run, *Then* a `ReviewDecision(kind=album_date, item=A7, value=1994-12-25)` is appended in addition to the mapping update.
- Retraction primitive (used by `review undo-last`, Story 7.2).
  - *Given* decisions `accept F42` then `reject F42`, *When* `retract_last(n=1)` (the most recent non-retracted line or batch, whichever shell or day wrote it; there is no session) appends a `retract` line, *Then* the fold of item F42 returns to `accept` (the previous state), and the `retract` line itself is journaled, never a file rewrite.
- Item ids are typed and stable (ADR-009; UX S3 "Item ids").
  - *Given* a file with `ContentKey` K, an album with id `9102dede1a50`, an audit finding (K plus remote id R), a year-precision item (K) and a Suspect placeholder (K), *When* ids are allocated, *Then* they are `F<n>`, `A<n>`, `U<n>`, `Y<n>` and `P<n>` with the integer allocated once per `(prefix, stable key)` and appended to `DATA/review/ids.jsonl`, never reused or renumbered, and the file's `F` and `P` items are distinct ids; `ids.jsonl` is rebuilt from `decisions.jsonl` (every line carries `item` and `item_key`) when it is lost, and allocation resumes above the highest alias.
  - *Given* `accept F42` logged with `item_key` K, then `fuse` re-run so F42 no longer needs review and later needs review again, *When* the log is folded, *Then* the decision is still attached to K under `F42`; *Given* a line whose `item` is `F42` but whose `item_key` is not the key `review_ids` holds for F42, *Then* it is ignored with `Ignored 1 line: id F42 now names a different file` and attached to nothing; *Given* a bare `42`, *Then* resolution fails listing the prefixes that exist for it.
- A terminal decision has one definition.
  - *Given* the per-kind attribute `SOURCE_VERBS[kind].reject_terminal` (true for `placeholder`, `audit`, `cluster`, `face`; false for `file`, `album`, `year_precision`), *When* `fold()` returns an item, *Then* it carries `state` (Accepted/Rejected/Skipped/Undecided), `terminal` (an `accept`, a `set`, or a `reject` on a terminal kind) and `parked` (a `skip`, or a `reject` on a hold kind); `status`, `review list|next --state`, the upload gate and the import conflict rule are tested to read these fields and nothing else.
  - *Given* five decision lines appended with the same `import_id` (or the same `batch_id`, or one `group` line with `group_id`), *When* `retract_group(import_id|group_id)` appends one `retract` line naming it, *Then* the fold of all five items returns to their previous states in one step (used by `review undo-last --import` and group decisions).
- Cluster kinds fold as specified.
  - *Given* one `cluster_link` merge line and two `face_member` reject lines sharing a `batch_id`, *When* folded, *Then* the merge is a must-link intent, the two rejects are cannot-links, and `retract_group(batch_id)` retracts both rejects in one step; an imported line keeps its sheet `decided_at` next to the log `ts`.
- The log is generic over `kind`, so later stories (4.5 cluster labels, 7.2 file decisions, 9.5 remediation) add kinds without editing `decisions.py`.
**Files**: `G/pipeline/decisions.py`, `G/pipeline/review_ids.py`, `G/pipeline/album_service.py`, `G/tests/test_decisions.py`

##### Task 7.1a: Append/fold/load with torn-tail tolerance and `retract_last` (S)
##### Task 7.1b: Route `update-album` through it (via `album_service.py`, not `cli.py`) (XS)
##### Task 7.1c: Stable typed item ids (append-only `DATA/review/ids.jsonl`, rebuild from the log, `item_key` in every line, fold keyed by `(kind, item_key)`) and the `SOURCE_VERBS` terminal-or-hold fold fields (S)
- Files: `G/pipeline/review_ids.py`, `G/pipeline/decisions.py`, `G/tests/test_decisions.py`

#### Story 7.2: Terminal review
**As an** operator, **I want** `review list|next|accept|reject|set|skip`, **so that** low-confidence dates and flagged albums are resolved without a GUI.
**Acceptance Criteria**:
- One list with a `source` column.
  - *Given* (illustrative counts) 137 flagged albums and 40 `Review` file decisions, *When* `review list` runs, *Then* 177 rows print with `source` in {album, file, audit, year_precision, placeholder} (exactly these five, the same set in ADR-009 and the UX document) sorted by severity then confidence; `review list --state undecided|skipped|rejected|parked` (alias `--skipped`) lists by state (`parked` is skipped plus hold-kind rejected; `rejected` marks terminal rejects `cleared`) and `review list --clusters` lists cluster-label items through the registered handler (Story 4.5); the `Source` column never shows `cluster` or `face`.
- Filters and grouping keep one source from burying another (UX-70).
  - *Given* 40 `file` items and 300 `placeholder` items, *When* `review next --source file` and `review next --source placeholder --album A7` run, *Then* each returns only items of that source (and album), `--severity` filters likewise, `--order gain` sorts by files resolved per decision (default for `--source placeholder`; `severity` is the default otherwise), `review list --source placeholder --by album` prints one row per album with count, class and signal words ordered by gain, and `--json` on `list` and `next` emits `{"items": [...]}` with the same keys.
- `--open` removes the find-the-sheet step (UX-71).
  - *Given* `GPHOTOS_OPEN` pointing at a recording fake, *When* `review next --open` runs for item F42 whose sheet exists, *Then* the fake is called once with `<sheet path>#item-F42`, the `Sheet:` line prints as a `file://` URL, and with no sheet generated it prints `No sheet for this item yet. Generate: review sheet --album A7 --open`.
- Legacy `review` is migrated with an alias (Story 1.11 disposition).
  - *Given* the pre-change fixture and `review --severity high --json`, *When* run, *Then* the output equals `review list --source album --severity high --json` plus one notice line on stderr, and `review list --source album` without flags reproduces the legacy table.
- One verb set, dispatched by item kind, with the meaning per source defined (UX-97).
  - *Given* a kind-handler registry in `pipeline/review.py` (`register_kind(kind, accept, reject, skip)`; `KIND_MODULES = ("pipeline.cluster_review", "pipeline.review_groups")` is imported lazily if present), *When* `review accept F42` (file item) and `review accept C12 --name X` (cluster) run, *Then* each reaches its handler, `accept`/`reject`/`skip` are registered exactly once in `cli_review_items.py`, and `cli_review_cluster.py` only adds `merge`, `split`, `sheet`.
  - *Given* one item of each source (`file`, `album`, `year_precision`, `audit`, `placeholder`) plus a cluster and a face, *When* `review next` shows each, *Then* its `Next:` line lists only that kind's verbs (the UX S3 table), and an undefined verb such as `review set C12` exits 1 with `review set is not defined for cluster C12. Use: review accept C12 --name NAME`.
  - *Given* a bare `review accept 42` where F42 and P42 both exist, *When* run, *Then* it exits 1 with `'42' needs a prefix: F42 (file), P42 (placeholder). Nothing was changed.` and `review confirm-placeholder P42` / `review accept F42` each reach exactly their own handler.
  - *Given* a `year_precision` item, *When* `review accept Y77` runs, *Then* a `year_precision` decision releases the file for `YearPrecisionPolicy` rule 3 (Story 8.4 plans the marked mid-period date); `reject` keeps it keyword-only and un-uploaded. *Given* an `audit` item, *Then* `accept` puts it on the remediation worklist input and `reject` clears it as a false positive with the reason recorded.
  - *Given* a `placeholder` item (a `Suspect` file), *When* `review reject P4021` (alias `review confirm-genuine P4021`) runs, *Then* a decision is appended AND a `Genuine` record with `source=owner` is appended to `DATA/placeholders.jsonl`, and the item then lists as `Rejected (genuine)`; `review accept P4021` (alias `review confirm-placeholder P4021`) appends a `LegacyPlaceholder` owner record, and the item screen's `Next:` line prints the explicit alias names.
- Accept records an override that becomes an anchor.
  - *Given* a review row for file F with candidate 1974..1978, *When* `review set F42 --date 1976-06` runs, *Then* a `UserOverride` Evidence (confidence 1.0, `hard=True`) is stored, a `ReviewDecision` appended, and the next `fuse` shows F as `UserOverride`.
- Overrides are rebuilt from the log.
  - *Given* a `review set F42 --date 1976-06` made earlier and `pipeline.db` then deleted, *When* `index` and `fuse` re-run, *Then* F is again `UserOverride` (the fold in `fuse`, Story 2.8) and the upload gate still treats it as decided.
- `review next` shows the first undecided item and the next command.
  - *Given* 3 undecided items, *When* `review next` runs, *Then* it prints the item with voters/provenance and `Next: gphotos-organizer review accept F<n> | review set F<n> --date YYYY[-MM[-DD]] | review skip F<n> | review reject F<n>` (the id of the item shown) followed by `Immediate (tier T1, one item; undo: review undo-last): accept, reject, skip, set. Preview first (T1a, --apply): set <album> --offset, confirm-genuine, confirm-placeholder, import, reject of an Accepted cluster.`
- Resume after interruption.
  - *Given* 10 decisions made before Ctrl-C, *When* `review next` re-runs, *Then* it starts at the 11th.
- Progress is per source and leftovers resurface (UX-104).
  - *Given* 35 `file`, 137 `album` and 300 `placeholder` items, *When* `review next` runs unfiltered, *Then* the header reads `Review file 1 of 35` and never serves a placeholder item, `review next --source album` reads `Review album 1 of 137`, and with only placeholder items left it prints `Only placeholder items remain: 300 files in 2 albums. Next: gphotos-organizer review list --source placeholder --by album` followed by `The 172 non-placeholder items are decided (...)`, never the `All N items decided` line (precedence (a) undecided non-placeholder, (b) only placeholders remain, (c) all decided).
  - *Given* 6 rejected-terminal items (genuine placeholders and cleared audit findings), 3 hold-kind rejected, 3 skipped and 160 accepted/set, and nothing undecided, *When* `review next` runs, *Then* it prints `All 172 items decided (160 accepted/set, 6 rejected and cleared, 3 rejected and parked, 3 skipped). 6 items stay parked (not written, not uploaded). Next: gphotos-organizer plan   (or revisit them: gphotos-organizer review next --state parked)`; `review next --state parked|rejected|skipped` serves those items with the same verbs and filters (the 6 cleared items appear only under `--state rejected`, marked `cleared`), and with nothing parked the line ends `Next: gphotos-organizer plan`.
  - *Given* a genuine placeholder (reject on a terminal kind) and a rejected file (reject on a hold kind), *When* `fold()`, `review list --state parked`, the all-decided line, `status` and the upload gate are queried, *Then* the first is never parked, never counted as held or left over and never nags, and the second is parked everywhere; `Held` and `Blocked` never print on a review screen.
- `review undo-last` returns the item to its previous state.
  - *Given* decisions `accept F42` then `reject F42` (possibly written by another shell or on another day), *When* `review undo-last` runs, *Then* it first prints `Undoing: reject F42 (line 118, 2026-10-16 14:02); back to accept.`, item F42 is `accept` again, and it ends `Undid: reject F42 (back to: accept). Next: review next`; `--n 2` walks back two steps, `--list` shows the last 10, `--import` retracts the last import, one group decision or one split batch is one step, and with nothing to undo it prints `Nothing to undo. To reverse EXIF writes: undo --list. Next: review next`.
- `--force-guard` overrides a guard, journaled with its name.
  - *Given* `review set F42 --date 1976-06` for a file whose identified person is born 1980, *When* run, *Then* it refuses with `1976-06 is before <name>'s birth (1980). Choose a later date, or override: --force-guard`; with `--force-guard` it records a `UserOverride` whose provenance lists `forced_guard=BirthDeathBounds`, and the item appears in `review list --source file --forced`; the command is T1+: it first refuses (exit 1) without the flag and the refusal names `--force-guard`, so no separate dry-run exists and the override applies immediately.
- Album bulk `--offset` with dry-run preview.
  - *Given* album `A7` with 40 files, *When* `review set A7 --offset +10y` runs without `--apply`, *Then* it prints the file count, the first 5 before/after rows and `Apply: gphotos-organizer review set A7 --offset +10y --apply`; with `--apply` it appends one album-level decision and per-file `UserOverride` evidence; `--date` on an album uses the same preview/apply pair, and a result in the future or today is refused (UX-13).
**Depends on**: 2.8, 1.9 and 7.5 (the usability pass may amend the criteria above before this story starts).
**Files**: `G/pipeline/review.py`, `G/pipeline/opener.py`, `G/cli_review_items.py`, `G/tests/test_review.py`

##### Task 7.2a: Review item projection (decisions + album flags `models.py:34-36` + `Suspect` files from `placeholders.jsonl` as `source=placeholder`, Story 1.9) (M)
- Files: `G/pipeline/review.py`, `G/tests/test_review.py`
##### Task 7.2b: Commands, fold, `UserOverride` evidence, `--force-guard` (S)
- Files: `G/pipeline/review.py`, `G/cli_review_items.py`, `G/tests/test_review.py`
##### Task 7.2c: `review undo-last` and album `--offset`/`--date` preview-apply (S)
- Files: `G/pipeline/review.py`, `G/cli_review_items.py`, `G/tests/test_review.py`
##### Task 7.2d: Tests (S)
- Files: `G/tests/test_review.py`
##### Task 7.2e: Filters (`--source/--album/--severity/--order/--by album`), `--open` through `pipeline/opener.py`, per-source verb tables and handlers for `year_precision`, `audit` and `placeholder` (S)
- Files: `G/pipeline/review.py`, `G/pipeline/opener.py`, `G/cli_review_items.py`, `G/tests/test_review.py`

##### Task 7.2f: `--state undecided|skipped|rejected|parked`, per-source progress headers, the unfiltered-`next` placeholder rule, the all-decided leftover line, immediate-vs-preview labels and the defined `undo-last` (`--n`, `--list`, `--import`) (S)
- Files: `G/pipeline/review.py`, `G/cli_review_items.py`, `G/tests/test_review.py`

##### Task 7.2g: Typed-id dispatch (prefix to handler, bare-number refusal), the `SOURCE_VERBS` table (terminal-or-hold reject, parenthetical state words), the placeholder-versus-all-decided precedence and the `undo` cross-pointers (S)
- Files: `G/pipeline/review.py`, `G/cli_review_items.py`, `G/tests/test_review.py`

#### Story 7.3: Static HTML contact sheets
**As an** operator, **I want** offline contact sheets per cluster and per date group, **so that** visual judgments (same person? 1974 or 1984?) are fast.
Requirement trace: beyond the written In Scope list (which names a review flow, not a sheet format) it serves In Scope 4 and Success Metric 3 (low-confidence dates reviewed, not guessed). It stays on the right side of the Out of Scope line "hosting a photo web UI" (ADR-009): static files under `DATA/`, no server, no network, nothing hosted.
**Acceptance Criteria**:
- Cluster sheet content and "show more" (UX-76).
  - *Given* a cluster with 60 faces, *When* `review sheet --cluster C12` runs, *Then* the HTML contains at most 24 face crops sampled across estimated age (outliers first), cluster id, member count, estimated year range, and album names as captions; each card shows `C12/F3` and per-card `Same person`/`Not this person`/`Unsure` buttons with the face-level meaning of ADR-009; the cluster controls (`Accept as person...`, `Reject cluster`, `Skip`) are separate, and the Name field is a closed `<select>` of `people.toml` names (no free typing).
  - *Given* the same cluster, *When* `review sheet --cluster C12 --page 2` runs (or the sheet's `Show next 24 (of 60)` link is followed), *Then* `cluster-C12-p2.html` holds the next 24 faces not yet shown, none repeated; `--all` writes every face, paged at 100.
- Index, navigation and opening (UX-71, UX-72).
  - *Given* 212 clusters and 40 already labeled, *When* `review sheet --clusters` runs, *Then* `DATA/review/sheets/index.html` lists every cluster with id, face count, estimated years, status word (`Accepted: <name>`, `Partly labeled: <name> (k of n)`, `Mixed names`, `Rejected`, `Skipped`, `Undecided`, `Merge queued`) and expected gain, sorted by gain, with a link to the first unlabeled one; every cluster sheet header has `Prev | Index | Next | Next unlabeled` links that resolve to existing files; `--all` generates all sheets with a progress line (`Sheets 40/212`); the generated HTML carries the cluster-run id and a `generation` hash used by Story 7.4.
  - *Given* `GPHOTOS_OPEN` set to a recording fake, *When* any `review sheet` form runs with `--open`, *Then* the fake is called once with the path and the `file://` URL is printed.
- Text, alt and card labels by sheet kind (UX-52, UX-79, UX-109).
  - *Given* a cluster, a date-group and a placeholder sheet, *When* generated, *Then* each `<img>` alt follows its kind (`Face crop from <album>, estimated <year>` / `Photo <file> from <album>, current date <date or none>` / `Photo from <album>, EXIF date <YYYY-MM-DD HH:MM:SS>`), the card buttons read `Same person`/`Not this person`/`Unsure` on cluster sheets, `Accept date`/`Reject date`/`Skip` on date-group sheets and `Genuine`/`Placeholder`/`Unsure` on placeholder sheets, the visible counter counts shown cards only (`12 of 24 shown faces judged`), and a `<dialog>` asks to type the name (`Label 120 faces (24 shown) as N? Type the name to confirm.`) only when the faces shown are fewer than 25% of the members to be labeled (`TYPED_NAME_SHOWN_FRACTION`); *Given* clusters of 60 (40% shown) and 120 (20% shown) faces, *Then* the first presses through on one `Accept as person...` and the second asks for the name.
- Open failures and resume (UX-105).
  - *Given* no opener (`GPHOTOS_OPEN` unset and no `xdg-open`), *When* `review sheet --cluster C12 --open` runs, *Then* it prints `Could not open a browser (xdg-open not found). Open this file: file://...` and exits 0; *Given* `review sheet --clusters --all` interrupted after 40 of 212 sheets, *When* rerun, *Then* sheets whose generation is unchanged are kept and it prints `Sheets 40/212 kept, 172 to write`.
- Scale: pages and progress (UX-75; date-group sheets only, because a placeholder sample sheet is one unpaginated page, Story 7.6).
  - *Given* album `2021 random photos` with 9,161 files, *When* `review sheet --album 9102dede1a50` runs, *Then* page 1 holds at most 100 cards (`--per-page` up to 200), the page shows `Page 1 of 92` with first/prev/next/last links, only page 1's thumbnails are generated, stderr shows `Thumbnails 100/100`-style progress (a plain line per 500 when not a TTY), and the HTML file stays under 2 MB.
- Enlarge image (UX-87).
  - *Given* a card, *When* its sheet is generated, *Then* a 1024 px image is cached at `DATA/thumbs/<ContentKey>-1024.jpg` for each card on the page and referenced by the `Enlarge` dialog; a missing source shows the alt tile.
- Date-group sheet has its own command (consistency review C6).
  - *Given* an album holding `file`, `year_precision` and `audit` items, *When* its date-group sheet is generated, *Then* the cards and the album block carry exactly the controls of the UX S4 control table: file cards `Accept date`/`Reject date`/`Skip` and `Set date`, year-precision cards `Release date`/`Keep keyword-only`/`Skip`, audit cards `Date is right`/`Remote is right`/`Skip`, and a top album block `Accept album date`/`Reject album date`/`Skip album` plus an `Offset` field validated like `--offset`; each control's `data-kind`/`data-action` matches one row of that table (a test walks the table and the template).
  - *Given* album `1985 Beach` with 40 files of mixed decision status, *When* `review sheet --album <album-id>` runs (or `review sheet --group <group-id>` for a group of items sharing a folder date), *Then* `DATA/review/sheets/dategroup-<id>.html` is written with one photo card per file showing folder date, inferred date, confidence and voters (provenance), the same shell, controls and accessibility rules as the cluster sheet, and the path plus `Next: gphotos-organizer review next` is printed; an unknown id prints `No album 'X'. List: review list --source album`.
- Owner labeling pass on real clusters (owner step of this story, wall-clock: Tyler).
  - *Given* real clusters from Story 4.4 and the people file from Story 4.5, *When* Tyler runs `review sheet --cluster <id>` and labels with `review accept <id> --name ...`, *Then* the number of labels made and the files they resolve (expected-gain column of `review list --clusters`) are recorded in the PR, together with seconds per label, seconds per file item and switches per 10 labels for the first 20 real clusters (more than 1.5 x a Story 7.5 threshold is an owner decision point, appended to the ADR-009 outcome section); Story 4.6's real-data acceptance and Story 5.4's real run start after this pass.
- Accessibility baseline.
  - *Given* the generated file, *When* checked by `test_report_html.py`, *Then* it has one `<h1>`, `lang="en"`, every `<img>` has non-empty `alt` like `Face crop from <album>, estimated 1978`, accept/reject controls are native `<button>`s, state also shown by text, `prefers-color-scheme` styles and a visible `:focus-visible` outline, no `http://` or `https://` references, and `<meta name="robots" content="noindex">`.
- Contrast.
  - *Given* the stylesheet's declared text/background pairs, *When* contrast is computed, *Then* all are at least 4.5:1 (UI components 3:1).
- Thumbnails local and lazy.
  - *Given* a first render, *When* thumbnails are missing, *Then* they are generated into `DATA/thumbs/<ContentKey>.jpg` at 256px and reused on rerun.
- Written outside git.
  - *Given* the output path, *When* resolved, *Then* it is under `DATA/` not the repo.
**Depends on**: 4.4, 4.5, 7.2 and 7.5 (the usability pass may change the criteria below before this story starts).
**Files**: `G/report_html.py`, `G/pipeline/thumbs.py`, `G/pipeline/sheet_index.py`, `G/cli_review_cluster.py`, `G/tests/test_report_html.py`, `G/tests/test_sheet_pages.py`

##### Task 7.3a: Thumbnail generator (cached by `ContentKey`, drive-unmounted message) (S)
- Files: `G/pipeline/thumbs.py`, `G/tests/test_report_html.py`
##### Task 7.3b: Cluster and date-group templates and the `review sheet --cluster|--album|--group` commands (plain f-string templating, no new service) (M)
- Files: `G/report_html.py`, `G/cli_review_cluster.py`, `G/tests/test_report_html.py`
##### Task 7.3c: Accessibility/contrast assertions, including focus ring, state icons and badges in both themes (S)
- Files: `G/tests/test_report_html.py`
##### Task 7.3d: Pagination, cluster index, Prev/Index/Next links, `Show next 24`, and `--open` (M)
- Files: `G/pipeline/sheet_index.py`, `G/report_html.py`, `G/cli_review_cluster.py`, `G/tests/test_sheet_pages.py`
##### Task 7.3e: Thumbnail progress line and 1024 px enlarge images (S)
- Files: `G/pipeline/thumbs.py`, `G/tests/test_sheet_pages.py`

##### Task 7.3f: The sheet control table (file, year-precision, audit cards and the album block with `Offset`), alt text and button labels per sheet kind, shown-cards counter, closed Name `<select>` with the typed-name `<dialog>`, `--open` failure message, resumable `--all`, and the index's top-3 album ids (S)
- Files: `G/report_html.py`, `G/pipeline/sheet_index.py`, `G/cli_review_cluster.py`, `G/tests/test_sheet_pages.py`

#### Story 7.4: Keyboard UI and decision export/import
**As an** operator, **I want** `a`/`r`/`s` keys on the sheet and an exported `decisions.json`, **so that** batch review is fast and results merge back.
Requirement trace: beyond the written In Scope list; it serves Success Metric 3 by making the review list tractable at 170+ items, and keeps the static-files-only boundary (no server).
**Acceptance Criteria**:
- Export format `gpo-decisions/2` merges (ADR-009; UX S5 gives the schema).
  - *Given* a `decisions-cluster-C12-CR7-9f2c41aa-20261016T1402.json` downloaded from the sheet with 12 entries, *When* `review import --latest` (newest `decisions-*.json` in `$XDG_DOWNLOAD_DIR`, else `~/Downloads`; `--glob` takes several) runs, *Then* it is a dry-run that prints the 12 entries and an `Apply:` command with the resolved file path(s) pinned, and 12 `ReviewDecision` lines are appended only by that printed command (`review import FILE --apply`); `review import --latest --apply` is refused with `--latest resolves a different file each time. Run the dry-run and use the Apply command it prints. Nothing was changed.`, and a newer export landing between dry-run and apply is not imported; each line is carrying an `import_id`, and duplicates of already-folded decisions (key `(kind, item_key | group_id, face, action, value | offset | name | outcome + hash(exceptions))`) are ignored; every non-cluster item carries `item` (typed id) and `item_key`, import resolves by `item_key`, and an entry whose alias and key disagree is rejected (`Entry F42 names a different file than the log's F42. Regenerate the sheet.`); every item carries `decided_at` and kinds are snake_case (`album_date`, `year_precision`); `review undo-last --import` retracts that import's lines in one step (Story 7.1 `retract_group`).
  - *Given* a cluster-sheet export holding `cluster_label accept C12 name`, `face_member reject C12/F3` and `face_member accept C12/F5`, *When* imported with `--apply`, *Then* the three Story 4.5 handlers run exactly as the equivalent terminal commands (labels for non-rejected members, a cannot-link for F3, F5 a confirmed exemplar), and, for a sheet whose `cluster_run_id` differs from the current run, `cluster_label` entries are ignored while `face_member` entries are applied by canonical `face_id` (cannot-links and confirmations survive renumbering; an entry whose face no longer exists is ignored) with `Entries for C12 were made against cluster run CR7 but the current run is CR9. Applied 3 face_member entries by face_id (they survive renumbering); Ignored 1 cluster_label (cluster-level entries are valid only for the run that recorded them). Regenerate: review sheet --cluster C12`.
  - *Given* a `cluster_label accept` with no `name`, or a name not in `people.toml`, *When* imported, *Then* the Story 4.5 message is printed (`Entry C12 has action accept but no name ...` / for a name missing from `people.toml`: `... not in people.toml (people.toml changed after the sheet was generated, since the sheet's list is closed). Regenerate the sheet: review sheet --cluster C12   (or run the import with --new-person)`) and the other entries still apply; `--new-person` is the only way to create a name at import.
  - *Given* an album-level export entry `album_date` `set` with `offset: "+10y"`, *When* imported, *Then* the dry-run prints the file count and first 5 before/after rows exactly as `review set A7 --offset +10y`, `--apply` is required, and a result in the future or today is refused.
- Keyboard map and WCAG 2.2 behavior (UX-84 to UX-89).
  - *Given* the sheet source, *When* parsed, *Then* it declares handlers for `a`, `r`, `s`, `u`, `e`, `?` that act only while a card has focus (never on `body` or in an input), a `Keyboard shortcuts` checkbox that disables them (persisted), visible buttons for every shortcut that are `aria-pressed` toggles, a plain `<ul>` whose `<li>` (no role on the `<li>`) each contain one `<div role="group">` with an accessible name and a description stating that the decisions are mutually exclusive (no `grid`/`listbox`/`radiogroup` role is claimed), every card control in the natural Tab order (no roving tabindex and no `tabindex="-1"` on any card control), a native `Next undecided card` button as the last stop of every card (visually hidden until focused) and one in the header, arrow/Home/End/PageUp/PageDown movement to the neighbouring card's same control without wrapping, only while focus is inside a card and not in a text field, as an enhancement only, an Export button that uses `aria-disabled="true"` with `aria-describedby` text while empty (it stays focusable), focus kept on the decided control (state updated in place), a visible counter updated on every change plus a separate visually hidden `role="status"` region that updates at most every 1.5 s and speaks every fifth change and at zero left, a native `<dialog>` enlarge view with Esc and focus return, and no keyboard trap (JS-optional: page usable without it).
  - *Given* Playwright with shortcuts switched off and a 24-card cluster sheet, *When* a keyboard-only run decides ten consecutive cards using only Tab, Shift+Tab and Enter/Space (no arrow keys), *Then* every decision succeeds, every card control is reachable, and the number of Tab presses from one card's first decision button to the next card's is exactly 5 on cluster and placeholder sheets (6 on date-group sheets, which add the `Set date` field); *Given* focus on card 3's first button, *When* Tab moves to its `Next undecided card` button and Enter is pressed with cards 4 and 5 already decided, *Then* focus lands on card 6's first decision button; *Given* shortcuts off and arrows never pressed, *Then* all 24 cards are decidable.
  - *Given* Playwright at 200% zoom (640 CSS px viewport) and with the WCAG 1.4.12 text-spacing overrides applied, *When* the sheet is scanned, *Then* no text is clipped or overlapped and every button box is at least 24 px.
  - *Given* the `Set date` field, *When* `1976-13`, today, a future date, `1976-06` for a card whose identified person is born in 1980, and `1976-06` are entered in turn, *Then* the first four show an inline error linked by `aria-describedby` (with `aria-invalid`) and create no export entry, and the last shows `month precision: 1976-06` and exports a `set`; every field has a visible `<label>`.
  - *Given* Playwright at a 320 px viewport and at a 1280x500 viewport, *When* every card is focused in turn, *Then* there is no horizontal scroll and the focused card's bounding box is never covered by the header (`scroll-padding-top`, sticky only at 600 px height or more).
- Sheet state is safe across regeneration, undo and reload (UX-80 to UX-83).
  - *Given* decisions saved for sheet `cluster-C12` generation `9f2c41aa` and the sheet regenerated with generation `77ab01c3`, *When* it opens, *Then* the new page starts empty and shows `Decisions from an older version of this sheet (12, saved <date>) exist. [Export them] [Discard]`; the same generation reopens with its decisions.
  - *Given* a decided card, *When* its key is pressed again, *Then* it returns to Undecided; `u` undoes the last decision up to 50 deep; `Clear all...` asks through a native `<dialog>`.
  - *Given* items already decided in `decisions.jsonl` when the sheet was generated, *When* it opens, *Then* their cards carry `In log: <state> (<date>)`; after Export the header shows `Exported N at <time>`, and `Mark as imported` clears this page's local decisions.
  - *Given* `localStorage` throwing on write (storage denied or a quota error), *When* a decision is made, *Then* a banner says decisions are lost on close and offers Export now, and the decision stays in memory and is exported.
- Schema fields and group collisions (UX-99).
  - *Given* an export holding two `group` entries with the same action for different albums (different `group_id`), *When* imported, *Then* both are appended, neither is reported as a duplicate; *Given* an item without `decided_at`, *Then* it is rejected with `Entry C12 has no decided_at; export again from the sheet. Nothing was changed.`
  - *Given* `review import FILE --apply` finishes, *Then* `index.html` is regenerated (no thumbnails) and the output ends `Individual sheets keep old badges until regenerated: review sheet --cluster C12`, preceded by `Export files contain names and stay in ~/Downloads. Delete them, or move them under DATA/review/imported/ with: review import ... --apply --archive`; with `--archive` the applied files are moved there (never deleted).
- Imported `set` values are validated like `review set` (UX-106).
  - *Given* an export with `set F42 1976-13`, `set F43 <today>` and `set F44 1976-06` for a person born in 1980, *When* imported, *Then* each refused value is rejected individually with the terminal message (`--force-guard`, T1+, overrides only the birth guard) and the other entries still apply.
- Import rejects unknown ids.
  - *Given* an entry with item id `C999` not in the DB, *When* imported, *Then* it is rejected with the id named and nothing else is lost.
- Conflicts with newer terminal decisions are not imported unless the owner overrides (`decided_at` makes this evaluable).
  - *Given* a sheet entry `accept C12` and a terminal `reject C12` decided later, *When* `review import FILE --apply` runs, *Then* it lists `C12: sheet says accept, terminal decided reject on <ts>. Not imported. Use --prefer-import to override.` and does not import it (the sheet entry's `decided_at` is older than the terminal line's `ts`; a sheet entry whose `decided_at` is newer is appended and wins; only a terminal decision as defined in Story 7.1 counts, so a later `skip` or a hold-kind `reject` such as `reject F42` never blocks a sheet entry); *Given* `--prefer-import`, *Then* the sheet entry is appended and supersedes the terminal one (latest wins), and the output says so (tier T1+: `Override: --prefer-import (newer terminal decision). Journaled.`).
**Depends on**: 7.3 and 1.13 (`--prefer-import` is a T1+ override with the shared notice).
**Files**: `G/report_html.py`, `G/pipeline/review.py`, `G/cli_review_io.py`, `G/tests/test_review_import.py`, `G/tests/test_ux_sheet.py`

##### Task 7.4a: Sheet JS (keys, counter, export) (S)
- Files: `G/report_html.py`
##### Task 7.4c: Sheet state: generation-hash key, undo/clear, `In log:` badges, exported/imported markers, storage-failure banner (S)
- Files: `G/report_html.py`, `G/tests/test_ux_sheet.py`
##### Task 7.4d: WCAG behaviors (focus-gated shortcuts and off switch, natural Tab order with the 5/6-stop budget and `Next undecided card`, `aria-pressed` buttons in a `role="group"` inside a plain `<li>`, `aria-disabled` Export, focus-after-decision, visible counter plus separate throttled live region, labels and `aria-describedby`, enlarge dialog, reflow, 200% zoom, text spacing and sticky-header tests in Playwright) (S)
- Files: `G/report_html.py`, `G/tests/test_ux_sheet.py`
##### Task 7.4b: `review import` with dry-run default and `--prefer-import` conflict policy (S)
- Files: `G/pipeline/review.py`, `G/cli_review_io.py`, `G/tests/test_review_import.py`

##### Task 7.4e: Export fields (`decided_at`, `item_key`, `offset`, `group_id`, `outcome`), filename scheme, `review import --latest|--glob`, index regeneration after `--apply`, stale-run handling (cluster-level entries ignored, `face_member` applied by `face_id`), the pinned `Apply:` command (`--latest --apply` refused), `--archive`, `item_key` resolution and the terminal-decision conflict rule, and `Set date` validation in the sheet JS and at import with `--force-guard` (S)
- Files: `G/report_html.py`, `G/pipeline/review.py`, `G/cli_review_io.py`, `G/tests/test_review_import.py`, `G/tests/test_ux_sheet.py`
##### Task 7.4f: Export producers for every row of the control table (album block with `Offset`, year-precision and audit cards, `item_key` and typed ids in each entry) and the keyboard-only Playwright test with the 5/6-stop budget and `Next undecided card` (S)
- Files: `G/report_html.py`, `G/tests/test_ux_sheet.py`

#### Story 7.5: [SPIKE] Review-loop usability pass on a fixture corpus
**Timing**: run early (W5), before Stories 7.2 and 7.3 start.
**As an** operator, **I want** the labeling and date-review loop tried and timed on a small fixture before the full review flow is built, **so that** the sheet/terminal seam (the dominant friction of the loop, UX triad review) is measured while it is cheap to change.
Requirement trace: serves Success Metric 6 (review burden) and the UX document S12 "Usability pass". Runs in W5 against the Story 7.1 log, so its findings can change the Story 7.2 and 7.3 criteria before those start.
**Depends on**: 1.11 (loader), 7.1 (`decisions.py`).
**Acceptance Criteria**:
- A throwaway prototype exists on a fixture.
  - *Given* `make_fixture.py`, *When* it runs, *Then* it writes a synthetic corpus of 20 clusters (60 faces for the largest), 50 date items across 5 albums and 3 placeholder albums (2,000 files in total, no real photos), and `review_proto.py` renders a static cluster index, a cluster sheet with face-level and cluster-level controls, a placeholder sample sheet and a terminal `accept|reject|next --open` over the real `decisions.py` log.
- The pass is timed and recorded.
  - *Given* Tyler runs the pass (labeling 20 clusters with the index and `--open`, deciding 50 date items, one group decision over a placeholder album), *When* it ends, *Then* the PR records seconds per cluster label, seconds per file item, terminal/browser switches per 10 labels, and where he hesitated, against the pre-agreed thresholds (25 s, 15 s, 2 switches, plus 120 s per placeholder album and at most 3 `review import` runs per 10 cluster labels when exports are batched with `--glob`; the owner may change them before the run); the outcome is written to the "Usability pass outcome" section of ADR-009.
  - *Given* a threshold is missed, *When* the story closes, *Then* the Story 7.2 and 7.3 acceptance criteria are amended in the same PR (what changed and why is listed), or the owner records `accepted as is`.
- The limitation is stated and totals are projected.
  - *Given* the ADR-009 outcome section, *When* the pass ends, *Then* it states that the clusters were synthetic (the pass measures mechanics, not the time to judge aging faces), projects totals (212 clusters x seconds per label, 172 items x seconds per item, 31 placeholder albums x seconds per album including the sample sheet, dry-run and apply steps, switches and import runs for 212 labels), and the owner accepts or changes the thresholds against those totals; the same quantities, plus how often the typed-name dialog fires on the real cluster sizes, are re-measured on the first 20 real clusters in the Story 7.3 owner pass.
- Nothing from the prototype ships.
  - *Given* Story 10.5, *When* it runs, *Then* `review_proto.py` is not imported by any `pipeline/` module (the prototype is deleted in Task 10.5c).
**Files**: `G/review_proto.py`, `G/tests/fixtures/review_pass/make_fixture.py`, `G/tests/test_review_proto.py`, `project_plans/gphotos-organizer-pipeline/decisions/ADR-009-review-surface.md`

##### Task 7.5a: Fixture generator and the throwaway prototype (index, cluster sheet, placeholder sheet, terminal loop) (S)
- Files: `G/review_proto.py`, `G/tests/fixtures/review_pass/make_fixture.py`, `G/tests/test_review_proto.py`
##### Task 7.5b: Timed pass protocol, measurements, ADR-009 outcome and criteria amendments (S; wall-clock: Tyler runs the pass)
- Files: `project_plans/gphotos-organizer-pipeline/decisions/ADR-009-review-surface.md`

#### Story 7.6: Group decisions and the placeholder visual path
**As an** operator, **I want** to confirm or reject whole album and signal groups of `Suspect` files after looking at a sample, **so that** the ~15k Suspect/placeholder items are reviewed in tens of decisions, not one per file.
Requirement trace: serves Success Metric 6 (review burden), Success Metric 1 and Story 1.9's Suspect class (a `Suspect` file cannot be an anchor until classified). Reuses the Story 7.4 sheet JavaScript, so it runs after it.
**Depends on**: 7.2, 7.3, 7.4, 1.9 and 1.13.
**Acceptance Criteria**:
- Group decisions have a preview, a viewed-sample precondition, and one-step retraction (UX-73).
  - *Given* 412 `Suspect` files in album A7 with signals `jan1` and `no_make_model`, *When* `review confirm-genuine --album A7 --signals jan1,no_make_model` runs without `--apply`, *Then* it prints the file count, five sample rows and `Apply: ...` and writes nothing.
  - *Given* `--apply` on that selection when its sample sheet was never generated, *When* run, *Then* it exits 1 with `412 files selected and no sample sheet was generated for this selection (the tool cannot tell whether you looked at it). Run: review sheet --placeholders --album A7 --signals jan1,no_make_model --open` (bypass: `--unviewed`, a T1+ override; a `group` entry that arrives from that sheet's Export also satisfies the check); selections of 50 files or fewer need no sample.
  - *Given* the sheet was generated and `--apply` runs, *When* it finishes, *Then* one `group` decision line is appended (`scope`, selector, `group_id`, `count`, `sample_hash`, `outcome`, merged `exceptions`) and, in the same command, a `Genuine` owner record carrying the `group_id` is appended to `DATA/placeholders.jsonl` for every selected file except the exceptions (the group has this one materialized representation; the fold never expands a `group` line at read time), `review undo-last` retracts the whole group in one step (Story 7.1 `retract_group`) and exactly those records are superseded, restoring each file's previous record, and `review confirm-placeholder` does the same for `LegacyPlaceholder`.
  - *Given* an album that gains 12 files after a group decision, *When* `review list --source placeholder` runs, *Then* the 12 appear as new Undecided `P` items, the group's `count` is unchanged and none of the 12 inherits the outcome.
  - *Given* two groups that overlap (album scope A7 `genuine`, then signals scope `jan1` `legacy_placeholder`), *When* a file in both is folded, *Then* the latest non-retracted record wins and neither scope outranks the other; a per-file `review confirm-genuine P4021` made after both beats both.
- The placeholder sheet is the visual source (UX-74).
  - *Given* 412 `Suspect` files, *When* `review sheet --placeholders --album A7 --signals jan1 --sample 48 --seed 7` runs, *Then* the HTML holds a deterministic sample of 48 cards (same seed, same cards), each with the current EXIF date and time, the class and the signals in words, totals (`412 files; 48 shown`), group controls (`Genuine: all 412`, `Placeholder: all 412`, `Skip group`) and per-card `Genuine` / `Placeholder` / `Unsure` buttons (a card that differs from the group control, or is `Unsure`, is an exception; a differing choice is exported as its own per-file entry); Export writes a `group` entry (with `group_id` and `outcome`) whose `exceptions` are those cards; `review import` applies it like the terminal form; the sheet is always a single page of at most 200 cards (never paginated, `--sample` above 200 is refused with `Sample is capped at 200 cards; use --seed to see other cards`) so the group controls and exceptions never span pages, and it obeys the same accessibility, contrast and no-network rules as the other sheets.
  - *Given* two exports of the same group made from `--seed 7` (exceptions P4022, P4031) and `--seed 8` (exceptions P4040), *When* both are imported with `--apply`, *Then* the second line's exceptions are united with the first's (P4022, P4031, P4040 all stay Suspect), no file the first export excepted receives an owner record, and an exception id no longer in the selection is dropped with `Ignored 1 stale exception (P4099 is not in this selection)`.
- The sample scales with the group and shows the timestamp histogram (UX-103).
  - *Given* a 412-file and a 9,161-file selection, *When* `review sheet --placeholders` runs without `--sample`, *Then* the sample sizes are 82 and 200 (`max(48, ceil(4 x sqrt(N)))`, cap 200), every distinct exact EXIF timestamp (up to 24 strata) appears at least once, the page opens with a histogram of the ten most common exact timestamps with counts and a by-year list for the whole selection, another `--seed` yields other cards, and the terminal dry-run prints the five most common timestamps.
- Exceptions and their end-state (UX-103).
  - *Given* `review confirm-genuine --album A7 --signals jan1 --except P4022,P4031,P4040 --apply`, *When* run, *Then* 409 `Genuine` owner records are appended, the three excepted files get no record (they stay `Suspect`, Undecided and Held), the output ends `Confirmed 409 genuine; 3 exceptions stay Suspect: review next --source placeholder`, and an id outside the selection exits 1 with `File P9999 is not in this selection (412 files). Nothing was changed.`; `confirm-placeholder` takes the same flag.
  - *Given* a sheet export holding a `group` entry (`outcome=genuine`, 3 exceptions) and a per-file entry for a card marked `Placeholder`, *When* `review import` runs without `--apply`, *Then* the dry-run prints `group genuine A7 [jan1] 412 files, 3 exceptions (P4022, P4031, P4040; stay Suspect)` and the per-file line.
- Albums are offered in order of expected gain.
  - *Given* 30 albums holding Suspect files, *When* `review list --source placeholder --by album` runs, *Then* albums are ordered by files resolved per decision and each row prints the exact `review sheet --placeholders --album ID` command.
**Files**: `G/pipeline/review_groups.py`, `G/cli_review_groups.py`, `G/report_html_groups.py`, `G/cli_review_cluster.py`, `G/tests/test_review_groups.py`

##### Task 7.6a: Group decision engine (`group` kind handler registered through `KIND_MODULES`, selection hash, exceptions, materialized owner records, `retract_group`) (M)
- Files: `G/pipeline/review_groups.py`, `G/tests/test_review_groups.py`
##### Task 7.6b: Placeholder sample sheet template and `review sheet --placeholders` (S)
- Files: `G/report_html_groups.py`, `G/cli_review_cluster.py`, `G/tests/test_review_groups.py`
##### Task 7.6c: `review confirm-genuine|confirm-placeholder` commands, sample-sheet-generated guard, T1+ `--unviewed` override (S)
- Files: `G/cli_review_groups.py`, `G/pipeline/review_groups.py`
##### Task 7.6d: Tests incl. a 15,000-record pool and import of a sheet `group` entry (S)
- Files: `G/tests/test_review_groups.py`

##### Task 7.6e: Sample sizing and stratification, timestamp histogram (sheet and dry-run), `--except` on both terminal group commands with the exception end-state, `outcome`/`group_id` in the export, and group lines in the import dry-run (S)
- Files: `G/pipeline/review_groups.py`, `G/cli_review_groups.py`, `G/report_html_groups.py`, `G/tests/test_review_groups.py`

##### Task 7.6f: Group semantics beyond the first apply: exception union across same-`group_id` lines, stale-exception dropping, no drift onto files added later, per-file latest-record precedence for overlapping groups, and the single-page placeholder sheet cap (S)
- Files: `G/pipeline/review_groups.py`, `G/report_html_groups.py`, `G/tests/test_review_groups.py`

### Epic 8: EXIF plan/apply with journal
**Goal**: Reversible, verified writes; status derived from read-back (ADR-007).

#### Story 8.1: Split `metadata.py` (Refactor-first)
**As a** developer, **I want** pure planning separated from I/O, **so that** the journal can wrap the I/O.
**Depends on**: 1.5 (Stop producing placeholder dates; unify media).
**Acceptance Criteria**:
- Characterization first: current outputs for fixed inputs are captured, then preserved.
  - *Given* 20 fixture (filename, album date, index) tuples run through current `infer_file_specific_date` and `generate_descriptive_tags` before refactor, *When* run after the split, *Then* outputs match the saved golden except documented intentional fixes (placeholder skip 1.5, filename regex 1.4), listed in the PR.
- No function over 40 lines; `update_album_metadata` is gone or a thin wrapper.
  - *Given* `metadata.py` after the split, *When* `sg` counts function lengths, *Then* no function exceeds 40 lines and `plan_writes` has no subprocess import use.
- Tag generation fixed (`"chris"` vs "christmas").
  - *Given* a filename `christmas_1994.jpg`, *When* `generate_descriptive_tags` runs, *Then* no `Chris` person tag is produced (word-boundary match).
**Files**: `G/metadata.py`, `G/pipeline/write_planner.py`, `G/tests/golden/metadata_characterization.json`, `G/tests/test_write_planner.py`

##### Task 8.1a: Characterization golden from the current code (S)
##### Task 8.1b: Extract `plan_writes` (pure) and `tags.py` (M)
##### Task 8.1c: Equivalence + intentional-diff tests (S)

#### Story 8.2: exiftool snapshot reader
**As an** operator, **I want** batch reads of the date-related tags (full `ExifSnapshot`), **so that** old values are journaled before any write. (The leftover finder moved to Story 1.10 so `recover` exists before `index`; this story extends the minimal `read_tags` reader created in Story 1.9.)
**Depends on**: 8.1 (Split metadata.py Refactor-first), 1.9 (Legacy placeholder detector and quarantine re).
**Acceptance Criteria**:
- Batch read.
  - *Given* 50 fixture files, *When* `read_snapshots(paths)` runs, *Then* it issues at most `ceil(50/chunk)` exiftool processes and returns an `ExifSnapshot` per file including absent tags as `None`.
- Real exiftool round trip.
  - *Given* exiftool 13.55 on this machine and a generated JPEG, *When* a snapshot is read, *Then* the values equal what `exiftool -json` prints directly.
- Snapshot carries what the journal needs.
  - *Given* a file, *When* a snapshot is taken, *Then* it also returns `size`, `mtime_ns`, the exiftool version string and a streaming `sha256` of the bytes (computed only when requested, for the journal).
**Files**: `G/pipeline/exif_reader.py`, `G/tests/test_exif_reader.py`

##### Task 8.2a: `read_snapshots` on top of `read_tags` (argfile chunking reused) (S)
##### Task 8.2b: Byte fingerprint (`sha256`, size, mtime_ns) helper and tests (S)

#### Story 8.3: Journal (journal-first, verify-after) in the source-of-truth store
**As an** operator, **I want** each write preceded by a committed journal row and followed by read-back, **so that** every change is reversible and status is true, and the undo records survive deletion or corruption of the derived database.
**Depends on**: 8.2 (exiftool snapshot reader), 2.2 (Two stores derived + source of truth , migrat).
**Acceptance Criteria**:
- Journal committed before write, in the source-of-truth store.
  - *Given* a fake exiftool that kills the process on invocation, *When* `apply` runs for file F, *Then* `state.db` `write_journal` already holds a `Pending` row for F with old values and the pre-write `sha256`, size, `mtime_ns`, `ContentKey`, exiftool version, plan hash and the exact tag-argument list, the same row is present in `DATA/journals/<run_id>.jsonl` (fsynced, append-only), and `recover` reconciles it by re-reading the file.
- Read-back sets status.
  - *Given* a successful write, *When* the read-back equals the intended values, *Then* the row is `Verified`; *Given* the fake silently ignoring the write (as `-ignoreMinorErrors` can), *Then* the row is `Mismatch` and the album halts.
- Scan-date preserved.
  - *Given* a scan with `ModifyDate=2012:03:10`, *When* the plan rewrites ModifyDate, *Then* the old value is in the journal.
- Rollback of the derived store never removes undo records.
  - *Given* journaled runs R1 and R2, *When* `pipeline.db` is deleted and recreated, *Then* `undo --run R1` (dry-run) still lists every reversion from `state.db`, and when `state.db` is replaced by an empty file the JSONL mirror alone reproduces the same list.
- Backup before apply uses the SQLite backup API, not `cp`.
  - *Given* `journal.backup_state()` (called by the Story 8.4 apply orchestrator before its first write) and a second connection writing to the WAL-mode `state.db` while it runs, *When* run, *Then* `DATA/backups/state-<ts>.db` is produced by `sqlite3.Connection.backup()` (or `VACUUM INTO`), passes `PRAGMA integrity_check`, opens, and lists the same journal rows as the source at the backup's snapshot point; a source-grep test fails if `shutil.copy` or `cp` touches `state.db`.
- Mirror and database cannot silently diverge (pre-mortem failure mode 12).
  - *Given* a crash injected between the JSONL fsync and the `state.db` insert (the write order is JSONL fsync first, then `state.db`), *When* the next `apply` starts, *Then* it compares the last run's rows in `state.db` against `DATA/journals/<run_id>.jsonl`, refuses `--apply` on a mismatch with `Journal mirror and state.db disagree for run R7 (1 row). Run: gphotos-organizer recover --run R7`, and `recover --run` reconciles by re-reading the file.
**Files**: `G/pipeline/journal.py`, `G/pipeline/migrations/state/s0803_write_journal.sql`, `G/cli_write.py`, `G/tests/test_journal.py`

##### Task 8.3a: Journal schema ops (`state.db` + JSONL mirror) + Pending/Verified/Mismatch state machine + pre-write fingerprint (M)
##### Task 8.3b: `recover --run` journal reconciliation (extends the Story 1.10 `recover`) and crash-injection tests (S)

#### Story 8.4: Plan/apply
**As an** operator, **I want** `plan` to write `plan.jsonl` and `fix-metadata --apply` to consume it, **so that** what I reviewed is what is written, replacing the Story 1.11 legacy lock.
**Acceptance Criteria**:
- Only decisions that need a date on disk; backed real EXIF is never overwritten.
  - *Given* decisions {F1 Eligible (Day precision), F2 Review, F3 Anchor `source=exif` with a `Genuine` on-disk date equal to the decision, F4 Conflict, F5 Anchor whose EXIF was classified `LegacyPlaceholder`}, *When* `plan` runs, *Then* `plan.jsonl` contains F1 only; F3 needs no write (its `OnDiskDate` is backed); F5 is not an anchor (Story 1.9) so it appears as `Review`, not as a write.
- Anchors and overrides whose date is not yet on disk ARE written (consistency review B1; the gate in Story 9.2 depends on this).
  - *Given* F7 an Anchor with `source=filename` (`IMG_20150102.jpg`, no EXIF date), F8 an Anchor with `source=owner_album`, F9 a `UserOverride` for 1976-06 (precision Month, governed by `YearPrecisionPolicy`), and F10 a `UserOverride` whose file already has a `Genuine` camera date that differs, *When* `plan` runs, *Then* `plan.jsonl` contains writes for F7 (2015-01-02 Day) and F8 (the album's Day-precision decision date) and the policy-governed write for F9; F10 is NOT written and appears as `Conflict -> Review` (`source=file`, reason `override_differs_from_genuine_exif`) unless the override was recorded with `review set --replace-exif`, in which case the write is planned and flagged in the summary; and `plan` prints `Anchors/overrides needing a date written: N`.
  - *Given* each of those writes has been applied and read back, *When* the journal row is `Verified`, *Then* `write_state.on_disk_backed(file)` is true and Story 9.2's gate passes the file; before that it does not.
- `--allow-placeholder` is gone (supersedes Story 1.5's dry-run flag).
  - *Given* `fix-metadata --allow-placeholder`, *When* run after this story, *Then* it exits 1 with `--allow-placeholder was replaced. Use: gphotos-organizer plan --allow-year-precision --album <id>. Nothing was changed.`
- Stale plan refused.
  - *Given* a plan generated before the latest `fuse`, *When* `fix-metadata --apply` runs, *Then* it exits 1 with `Plan is older than the latest analysis. Regenerate: gphotos-organizer plan`.
- Year-precision policy (the single rule from the glossary `YearPrecisionPolicy`; the owner can veto rule 3).
  - *Given* F6 with a Year-precision decision 1976 (or any precision coarser than Day), *When* planned without `--allow-year-precision`, *Then* NO `DateTimeOriginal`/`CreateDate` is written; the plan writes only the keyword `gpo-year:1976` (XMP `dc:Subject` / IPTC Keywords) and F6 is listed under `source=year_precision` in the review list.
  - *Given* the album was released with `plan --allow-year-precision --album <id>` (owner opt-in; only meaningful if Story 9.1 shows an undated upload lands on the upload date), *When* planned, *Then* (mid-period noon: July 1 for Year; the 15th for Month; July 1 of the midpoint year floor((earliest+latest)/2) for Range and Decade) writes are `DateTimeOriginal=1976:07:01 12:00:00`, `CreateDate` same, XMP `xmp:CreateDate` same, the keywords `gpo-year:1976` and `gpo-date-inferred:year`, `OffsetTimeOriginal` per ADR-007, `-P` is used, `-overwrite_original` is absent, and every such write is journaled and flagged in the plan summary; a Month decision `1976-06` instead writes `1976:06:15 12:00:00` with marker `gpo-date-inferred:month`.
- Tag policy applied consistently for Day precision.
  - *Given* F1, *When* planned, *Then* `DateTimeOriginal`, `CreateDate`, XMP `xmp:CreateDate` carry the same value, `-P` is used, `-overwrite_original` is absent.
- Exotic formats follow policy.
  - *Given* a `.png`, `.heic` and a RAW, *When* planned, *Then* `.png` gets XMP only, `.heic` is written only after the round-trip fixture passes (else listed unwritable), RAW is never written (XMP sidecar journaled only).
- exFAT safety path is mandatory and atomic.
  - *Given* the source root's filesystem type is `exfat`, `vfat` or `fuseblk` (read from `/proc/self/mountinfo`), *When* `fix-metadata --apply` runs without `--workdir`, *Then* it exits 1 with `Source is on exFAT: in-place writes are refused. Rerun with --workdir /tmp/gpo-work. Nothing was changed.` (there is no bypass flag).
  - *Given* `--workdir /tmp/gpo-work`, *When* applied, *Then* each file is copied locally, its pre-write `sha256` is journaled, it is written and read back locally, then copied back to `<name>.tmp` beside the original on the drive, its hash is verified, and only then renamed over the original (write-temp-then-rename, never an in-place overwrite); the run refuses to start with leftovers present (`recover --list`, Story 1.10).
- Failed items are retryable.
  - *Given* a run with 9 mismatches and 4 failures, *When* `fix-metadata --apply --retry-failed` runs, *Then* only those 13 files are re-attempted, each with a new journal row, and `Verified` files are untouched.
- Apply confirmation and preflight order (consistency review C1; UX-11, UX-12, S6).
  - *Given* a plan with id `7f3a21`, *When* `fix-metadata --apply --plan 7f3a21` runs on a TTY, *Then* preflight runs in this fixed order and stops at the first failure with the matching message and `Nothing was changed.`: (1) plan fresh versus the latest `fuse`, (2) drive mounted, (3) `exiftool` present, (4) workdir clean (no leftovers, `recover --list`), (5) a valid `BackupAttestation` (below), (6) a recorded clean `fsck.exfat -n` result in the attestation that is fresh (exit 0, recorded after the newest write run and at most 24 hours old, `--fsck-max-age`, INFERRED) - preflight reads the record and never runs fsck or asks for sudo, failing with `No fresh fsck result (last: <ts>). Unmount the drive, then run: gphotos-organizer backup fsck. Nothing was changed.`, (7) canary passed for this plan's format mix; only then it prints `About to write to N files across M albums (X dates, Y keyword-only; journaled; reverse with: undo --run R7). Type the number of files to write to continue:` (tier T2 through `pipeline/confirm.py`; the token is N, which the prompt does not repeat, and the plan id is not the token because `--plan` already puts it on the command line).
  - *Given* an empty line or a wrong number typed, *Then* `Confirmation did not match; nothing was changed.` and exit 1 (`1,214` and `1214` both confirm); *Given* the right number, *Then* the run proceeds. *Given* a non-TTY, *Then* `--yes` is required and skips only the typed confirmation, never the preflight; `--yes` on a TTY is ignored with a notice. `--plan ID` selects the plan; without it the latest plan is used and its id is echoed; an id that does not match the latest plan exits 1 with `Plan 'X' is not the latest (7f3a21). Regenerate or pass --plan 7f3a21.`
  - *Given* a running apply, *When* Ctrl-C arrives, *Then* the current chunk finishes, the journal flushes, and it prints `Saved K of N. Resume: gphotos-organizer fix-metadata --apply --plan 7f3a21`; the end summary prints `Written, read-back OK A; mismatch B; failed C (see errors.jsonl). Run id R7. Undo: gphotos-organizer undo --run R7. Next: gphotos-organizer audit` plus a progress bar with ETA on a TTY and plain lines otherwise.
- No real write without a backup, a canary and a clean filesystem (pre-mortem failure mode 1; Story 8.8 provides the helpers).
  - *Given* no `DATA/backup-attestation.json` (or one older than the newest drive file `mtime`, or one whose manifest does not cover every file in the plan), *When* a real `--apply` runs, *Then* it exits 1 with `No verified full-drive backup on another medium. Run: gphotos-organizer backup verify --copy <path>. Nothing was changed.` (fixture and `GPHOTOS_ALLOW_FIXTURE_APPLY=1` test runs on a temp drive are exempt; there is no bypass for the real drive root).
  - *Given* a first apply for a plan, *When* preflight step 7 runs, *Then* a 20-file canary (a deterministic sample covering each format in the plan) is copied to the local workdir, written, read back, copied back to a scratch directory on the SAME exFAT drive (`<drive>/.gpo-canary/`), hash-verified and deleted; any failure aborts before the first real write.
  - *Given* a plan touching 88 albums, *When* applied, *Then* it runs one album per mount-sync-verify cycle (`sync`, then confirm the mount is still `rw` and the file hashes match), a clean `fsck.exfat -n` record (Story 8.8) is required before the first apply, and every 10 albums (`--fsck-every N`) the run pauses at the album boundary and exits 0 with `Paused after 10 of 88 albums: the periodic fsck is due. Unmount the drive, run: gphotos-organizer backup fsck, remount, then rerun: gphotos-organizer fix-metadata --apply --plan 7f3a21 (resumes).` (no sudo prompt mid-run; the rerun's preflight accepts the new record), and a `remount-ro` or missing mount stops the run with the resume line.
  - *Given* each file in a run, *When* it is about to be written, *Then* its bytes are first copied to `DATA/prewrite/<run_id>/<ContentKey>.bin` (this is the `PrewriteSnapshot`); *Given* the local filesystem has less free space than the run's total byte size plus 10%, *Then* the run refuses to start with `Not enough local space for pre-write snapshots (need X, have Y). Free space or apply fewer albums with --album.`; snapshots are removed only by `prewrite purge --run R7`, which requires the run to be `Verified` and the typed snapshot file count (tier T3, Story 8.8).
- The legacy lock is replaced, not bypassed.
  - *Given* Story 8.4 is complete, *When* `fix-metadata --apply` is run without a plan, *Then* it exits 1 with `No plan found. Create one: gphotos-organizer plan`; the Story 1.11 "Legacy writer disabled" path is gone and `grep -- '-overwrite_original' G/` returns no matches.
**Depends on**: 2.8, 7.2, 8.3, 8.8 (backup attestation, fsck, canary and pre-write snapshot helpers) and 1.13 (the shared confirmation helper).
Defect trace: B1 and B4 (the `-overwrite_original` flag is removed and a grep test enforces it; Story 1.3 pinned its argfile semantics first), B3 (read-before-write: the first criterion, a backed real EXIF date is never overwritten, makes existing `Genuine` EXIF the strongest anchor, as `research/pitfalls.md` B3 prescribes).
**Files**: `G/pipeline/plan_service.py`, `G/metadata.py`, `G/pipeline/fix_metadata_service.py`, `G/cli_write.py`, `G/tests/test_plan_apply.py`

##### Task 8.4a: `plan` command and `WritePlan` (S)
##### Task 8.4b: Apply orchestrator (journal -> write -> read-back) replacing `-overwrite_original`, with `--retry-failed` (M)
##### Task 8.4c: exFAT detection, mandatory workdir, copy-back via temp + rename + hash verify, and format policy (S)
##### Task 8.4d: `YearPrecisionPolicy` in `plan_write`: keyword-only default, `--allow-year-precision` per-album opt-in, `source=year_precision` review items (S)
##### Task 8.4e: Tests incl. real exiftool on generated fixtures (S)
##### Task 8.4f: `plan` writes for Anchor/UserOverride dates not on disk; preflight order, typed-count confirmation through `pipeline/confirm.py`, `--plan`/`--yes`, Ctrl-C summary (S)
##### Task 8.4g: Wire Story 8.8 gates (attestation, canary, per-album mount-sync-verify cycle, fsck cadence, pre-write snapshots) into the apply orchestrator (S)

#### Story 8.5: `undo`
**As an** operator, **I want** `undo --run <id>`, **so that** any run can be reverted.
**Acceptance Criteria**:
- Replays old values, deletes tags that were absent.
  - *Given* a run that changed `DateTimeOriginal` from `2012:03:10` and added `XMP:CreateDate`, *When* `undo --run R1 --apply` runs, *Then* `DateTimeOriginal` is `2012:03:10`, `XMP:CreateDate` is absent, and rows are `Reverted`.
- Dry-run default.
  - *Given* the same, *When* run without `--apply`, *Then* a table of intended reversions prints and the files are unchanged.
- Undo needs only the source-of-truth store.
  - *Given* `pipeline.db` deleted, *When* `undo --run R1 --apply` runs, *Then* it succeeds from `state.db` (or the JSONL mirror).
- Confirmation tier (Story 1.13).
  - *Given* `undo --run R1 --apply` on a TTY, *When* it runs, *Then* it prints the file count and asks for that number (T2, not printed in the prompt); `undo --force` for files modified after the run is T3 and prints the number of forced files first; both summaries end with the reversal line from the map.
- Unknown run and modified files.
  - *Given* `undo --run R9`, *Then* `No run 'R9'. Runs: gphotos-organizer undo --list`; *Given* a file modified after the run (current hash differs from the journaled post-write value), *Then* it is listed `skipped: modified after run` unless `--force`.
**Depends on**: 8.4 and 1.13.
**Files**: `G/pipeline/journal.py`, `G/cli_write.py`, `G/tests/test_undo.py`

##### Task 8.5a: Undo with read-back, `--list`, `--force` (S)

#### Story 8.6: Derived `WriteState` and `metadata_status`
**As an** operator, **I want** write state and album status computed from journal rows, **so that** they cannot lie and no second copy of write state exists.
**Depends on**: 8.4 (Plan/apply).
**Acceptance Criteria**:
- Album status derives.
  - *Given* an album with 9 `Verified` and 1 `Mismatch` rows, *When* status is derived, *Then* it is `mismatch`; with 10 `Verified` it is `verified`; with a `Pending` row it is `pending`; with every row `Reverted` it is `reverted`; with no journal rows it falls back to the stored legacy value (`pending` shows as `not_written`, `legacy_unverified` and `skipped` as themselves, consistent with the Story 1.7 mapping). The complete derived set is `not_written | pending | verified | mismatch | reverted` plus the two fallback values.
- Per-file `WriteState` is a join, not a column.
  - *Given* a file with rows Pending then Verified then Reverted, *When* `write_state(content_key)` runs, *Then* it returns `Reverted`; the `decisions` table has no write-state column; and the gate test is a function in this module used by Story 9.2: `upload_ready(file) = write_state(file) == Verified or on_disk_backed(file)`, where `on_disk_backed` is true only for an `Anchor` with `source=exif` whose `Genuine` on-disk date equals the decision. `UserOverride` and filename/owner-album anchors satisfy it only via a `Verified` write.
  - *Given* a `UserOverride` file with no journal rows and a `source=exif` anchor with a backed date, *When* `upload_ready` runs, *Then* the first is False and the second True; after a `Verified` row for the first, both are True.
- `cli.py` and the services no longer assign it.
  - *Given* `grep -rn 'metadata_status = ' G/`, *When* run, *Then* no assignment remains outside the derived view.
**Files**: `G/pipeline/write_state.py`, `G/pipeline/fix_metadata_service.py`, `G/pipeline/upload_service.py`, `G/models.py`, `G/tests/test_derived_status.py`

##### Task 8.6a: `WriteState` join + derived album status + remove hand-set flags (S)

#### Story 8.7: Journaled revert / quarantine of legacy placeholder dates
**Depends on**: 1.9, 8.3, 8.4 (writer) and 8.5 (`undo`), so it runs in W11, strictly after both. Real `--apply` additionally requires the Story 1.9 precision gate (`placeholder-precision.json` with `passed=true`) and the Story 8.8 `BackupAttestation` (Owner Checklist item 4).
**As an** operator, **I want** the already-written fabricated dates classified `LegacyPlaceholder` (9,460 Jan-1 candidates and the 12:00:SS-signature files are measured; only those meeting the Story 1.9 truth table are reverted) neutralized once, reversibly, **so that** they cannot be re-read as truth by Google Photos, the next scan, or a future tool.
Requirement trace: serves Success Metric 1 (no mis-dated photos on the timeline) and Risk Control (every write reversible). The original pre-placeholder values were overwritten by the legacy writer (`-overwrite_original`) and are unrecoverable from the file; re-dating then happens through the normal plan/apply path from filename, XMP/IPTC, source scans or review.
**Acceptance Criteria**:
- Quarantine is the default; revert is a separate owner-applied step.
  - *Given* files classified `LegacyPlaceholder` (Story 1.9), *When* `placeholders revert` runs without `--apply`, *Then* it prints a table (file, current date, action `remove DateTimeOriginal/CreateDate/ModifyDate if identical to the placeholder`) and the apply command; nothing is written. Revert and quarantine apply ONLY to `LegacyPlaceholder`, and only when the current on-disk value still equals the stored classification's value (safe-original check). Files classified `Suspect` or `Genuine`, and any file with an owner `Genuine` record, are never touched; `Suspect` files go to the review list (`source=placeholder`, Story 7.2) for a decision.
  - *Given* a mixed fixture of 2 `LegacyPlaceholder`, 2 `Suspect` (lone Jan 1; lone time signature), 1 `Genuine` and 1 `LegacyPlaceholder` with an owner `confirm-genuine` record, *When* `placeholders revert --apply` runs, *Then* exactly the 2 unconfirmed `LegacyPlaceholder` files are written and journaled, the other 4 are byte-identical, and the 2 `Suspect` files appear in `review list --source placeholder`.
- Confirmation tier and reversal line (Story 1.13).
  - *Given* `placeholders revert --album A7 --apply` on a TTY, *When* run, *Then* it prints `About to remove fabricated dates from N files in album A7 (journaled; reverse with: undo --run R<n>; the original pre-placeholder dates are not recoverable by any command)` and asks for N as a typed token (T2); `--yes` works only without a TTY.
- Journaled and reversible.
  - *Given* `placeholders revert --apply --workdir /tmp/gpo-work` on the fixture drive, *When* it finishes, *Then* each write has a `Verified` journal row (via Story 8.3/8.4 machinery, including the exFAT rules) and `undo --run <id> --apply` restores the placeholder values.
- One write per file, never remove-then-rewrite (pre-mortem failure mode 2a).
  - *Given* a `LegacyPlaceholder` file that already has a resolvable decision (`Eligible`, `Anchor` or `UserOverride` at Day precision), *When* `placeholders revert --apply` runs, *Then* the revert SKIPS it (reason `has_decision`) and the later Story 8.4 `plan` overwrites the placeholder with the decided date in a single journaled write; only files with NO resolvable decision have their fabricated tags removed. A test counts exiftool invocations per file across `revert` then `plan --apply` and asserts at most one write per file.
  - *Given* a file with `date_kept=True` (Day-precision folder date, Story 1.9), *When* revert runs, *Then* it is skipped (reason `date_kept`) and handled as `folder_day` evidence.
- Revert is gated on a measured precision and a backup (pre-mortem failure mode 2).
  - *Given* no `placeholder-precision.json` with `passed=true`, *When* `placeholders revert --apply` runs, *Then* it exits 1 with `Precision gate not passed (needs >= 0.98 on a labeled sample). Run: gphotos-organizer placeholders precision. Nothing was changed.`; *Given* no valid `BackupAttestation`, *Then* the Story 8.4 backup message. Dry-run (`placeholders revert` and `placeholders summary`) works without either.
- Selection is re-validated at apply (N1).
  - *Given* a dry-run listing file X as `LegacyPlaceholder` and then (a) a file added to X's folder that breaks the ladder so the run drops below 3, (b) a file removed so the ladder drops below 3, (c) X's on-disk value changed, or (d) `placeholders confirm-genuine` recorded for X, *When* `placeholders revert --apply` runs, *Then* it re-runs the Story 1.9 classifier against the CURRENT `FolderContext` and current on-disk value (a stored classification is a hint, not authority), skips each such file and reports it as `reclassified: Suspect` / `value changed` / `owner-confirmed`, leaves it byte-identical, and writes no journal row for it.
  - *Given* a saved selection older than the classification version, *When* `--apply` runs, *Then* exit 1 with `Selection is stale. Regenerate: gphotos-organizer placeholders revert`.
- Reviewable in pieces, and weak classes are opt-in (N2).
  - *Given* a 15,000-record pool across albums, *When* `placeholders summary` runs, *Then* it prints one group per album id (count, signals present, class, 5 sample files) so output length is bounded by albums x 6 lines, with `Next: gphotos-organizer placeholders revert --album <id>`.
  - *Given* `placeholders revert --album <id>` (dry-run) it ends with the exact `--album <id> --apply` command; with `--apply` it writes only that album's files under one `run_id` (so `undo --run` affects only that album); an unknown album id prints `No album 'X'. List: placeholders summary`.
  - *Given* files with the `weak` flag (Story 1.9: rule 2 with `Make` and no folder-date match, or a uniform 5 s series of 20+ files not at noon), *When* revert runs without `--include-weak`, *Then* they are listed but not selected; with `--include-weak` they are selected.
- Videos are out of scope (N3).
  - *Given* an `.mp4` carrying QuickTime `CreateDate` `12:00:05`, *When* revert runs, *Then* it is byte-identical afterwards; the dry-run counts it under `not classified (video)`; videos are never anchors and are not exempt from the upload gate (they follow decisions and `WriteState` like any file). If the owner extends scope to QuickTime tags, the four `test_n3_*` rows flip to coverage tests (validation plan).
- Owner can choose quarantine-only.
  - *Given* the owner never runs `placeholders revert --apply`, *When* the pipeline continues, *Then* quarantined (`LegacyPlaceholder` and `Suspect`) dates remain excluded from anchors, calibration and hold-out, and the upload gate treats the files as needing a decision.
**Files**: `G/pipeline/placeholder_revert.py`, `G/cli_placeholders.py`, `G/tests/test_placeholder_revert.py`

##### Task 8.7a: Revert planner (selection, exact-match safety check against the stored classification) (S)
##### Task 8.7b: Apply through the journaled writer and tests (S)
##### Task 8.7c: Re-validation at apply (N1), `placeholders summary`, `--album`, `--include-weak`, single-write rule, precision and backup gates, video scope tests (M)
- Files: `G/pipeline/placeholder_revert.py`, `G/cli_placeholders.py`, `G/tests/test_placeholder_revert.py`

#### Story 8.8: Drive backup attestation, canary, fsck and pre-write snapshots
**As an** operator, **I want** every real write to the exFAT drive to be preceded by a verified second copy on another medium, a canary, a filesystem check and local pre-write bytes, **so that** a yank, USB reset or `remount-ro` mid-batch cannot destroy the only copy of a family photo; the journal restores tag values but never a truncated or lost file (pre-mortem failure mode 1).
Requirement trace: serves Constraint "never modify source files without a backup/dry-run default" and Risk Control "every write reversible" at the file level, which the tag journal alone does not reach. Facts: `df -h` on 2026-10-16 shows `/dev/sda1` 58G with 54G used and 4.0G free, so the backup MUST be on a different physical medium.
**Depends on**: 1.2 (atomic JSON), 1.10 (leftover finder and exFAT detection), 1.13 (confirmation helper for `prewrite purge`). Consumed by Stories 8.4 and 8.7, which refuse real runs without it.
**Acceptance Criteria**:
- A verified full-drive backup on another medium is a hard gate.
  - *Given* `backup verify --copy /mnt/other/gpo-backup --root <drive>`, *When* run, *Then* it walks every file under the source root, compares size and `sha256` against the copy, writes `DATA/backup-attestation.json` (verification time, source and copy device ids, file count, byte total, mismatch count, `manifest_sha256` of the full checksum manifest stored at `DATA/backup-manifest.tsv`) and exits 0 only with zero mismatches and a copy on a different device id than the source (`st_dev` and block-device name differ); a copy on the same device exits 1 with `Backup is on the same drive as the source (/dev/sda1). A same-drive copy does not protect against drive loss. Use another disk.`
  - *Given* a source file added or changed after the attestation, *When* `backup check` runs, *Then* the attestation is reported `stale: N files not covered` and Story 8.4's preflight refuses.
  - *Given* 17,255 files, *When* the manifest is produced, *Then* it holds exactly one row per file (recount by command in the PR: files and bytes) and the verify pass streams (bounded memory).
- `fsck.exfat -n` check.
  - *Given* the source device, *When* `backup fsck` runs while the drive is unmounted (it prints the `umount` command and waits; it never unmounts for the operator), *Then* it runs `fsck.exfat -n <device>`, records exit status and output hash in the attestation, and a nonzero status blocks 8.4 (the binary is resolved inside `fsck_check.py` from `GPHOTOS_FSCK`, else `fsck.exfat`, so tests use a fake and `tools.py` stays owned by Story 1.1); a mounted device prints `Unmount the drive first: udisksctl unmount -b /dev/sda1. Nothing was changed.`
- `fsck.exfat -n` needs the drive unmounted and usually root, and the plan says how (Owner Checklist item 11).
  - *Given* the device is readable by the operator, *When* `backup fsck` runs, *Then* it runs `fsck.exfat -n` directly; *Given* it is not readable (`os.access(device, R_OK)` is false) and stdin is a TTY, *Then* it runs `sudo fsck.exfat -n <device>` attached to the TTY (sudo prompts; the tool never reads, stores or logs a password) and prints `Using sudo for fsck.exfat (device not readable by this user).`; *Given* no TTY, *Then* it exits 1 with `fsck.exfat needs read access to /dev/sda1 (usually root). Run: sudo fsck.exfat -n /dev/sda1 > fsck.out; echo $? >> fsck.out   then: gphotos-organizer backup fsck --from-output fsck.out. Nothing was changed.`; *Given* `--from-output FILE`, *Then* the exit status and output hash are read from the file and recorded in the attestation with `source=operator-supplied`. The periodic fsck during Story 8.4 apply uses the same three routes through `backup fsck` run by the operator between two invocations of the apply (the apply pauses and exits at the boundary rather than waiting inside a long progress run).
- Canary on a copy, then on the drive's scratch directory.
  - *Given* a plan, *When* `backup canary --plan <id>` runs, *Then* it selects 20 files deterministically covering each format in the plan, copies them into `<drive>/.gpo-canary/`, passes each through an injected writer callback (copy, write, read-back, hash-verified rename), deletes the copies, and reports `canary 20/20 ok`; a failure prints the failing file's id and blocks 8.4. This story tests it with a fake writer; Task 8.4g injects the real Story 8.4 writer (so 8.8 does not depend on 8.4).
- Local pre-write snapshots are kept, bounded and purged only by the owner.
  - *Given* `prewrite snapshot --run R7 --plan <id>`, *When* run before an apply, *Then* each target file's bytes are copied to `DATA/prewrite/R7/<ContentKey>.bin` (mode 600), a `prewrite/R7/manifest.jsonl` row records size and `sha256`, and the command refuses when local free space (`shutil.disk_usage`) is below the run's total bytes plus 10% (message in Story 8.4).
  - *Given* a run not `Verified`, *When* `prewrite purge --run R7` runs, *Then* it refuses (`Run R7 has Pending/Mismatch rows`); for a `Verified` run it prints the snapshot file count and bytes to be destroyed, requires that count typed (tier T3; the run id is already on the command line and is not the token) and removes the directory; `prewrite restore --run R7 --file <path>` copies a snapshot back through the Story 8.4 temp-then-rename path.
- Evidence contains counts only.
  - *Given* the PR evidence for this story, *When* reviewed, *Then* it shows file and byte counts and `mismatches=0`, never album titles or file names (privacy rule).
**Files**: `G/pipeline/drive_backup.py`, `G/pipeline/fsck_check.py`, `G/pipeline/prewrite_store.py`, `G/cli_backup.py`, `G/tests/test_drive_backup.py`

##### Task 8.8a: Backup manifest, verification, attestation and same-device refusal (M; wall-clock: Tyler's second disk, copy time)
##### Task 8.8b: `backup fsck` and `backup canary` (S)
##### Task 8.8c: `prewrite snapshot|restore|purge` with the free-space check and tests (S)
##### Task 8.8d: `backup fsck` privilege routes (direct, `sudo` on a TTY, `--from-output`), the unmount wait and the no-password rule (XS; wall-clock: Tyler unmounts the drive and has root; fsck duration on the 54G drive is UNVERIFIED, record it in the PR)

---

## Phase 5: Upload gate, audit, remediation, reporting

### Epic 9: Upload gate, audit, remediation
**Goal**: Upload only dated files; know what Google actually holds (scoped); fix already-uploaded misdated items through whichever route Google allows (ADR-008).

#### Story 9.1: [SPIKE] Google Photos capability check
**Timing**: run early (W2); only Story 9.3 and later depend on its result.
**As an** operator, **I want** the unknowns settled by experiment, **so that** remediation strategies are chosen on evidence.
**Depends on**: 1.1 (Test harness, DataDir, tool/path resolution).
**Acceptance Criteria** (each outcome recorded in ADR-008 "Spike outcome"):
- rclone listing yields dates.
  - *Given* the album already listed successfully on 2026-10-16, *When* `rclone lsjson gphotos:album/<name> --fast-list` and `rclone lsl` run on 5 files with known EXIF dates, *Then* the doc records whether `ModTime` equals EXIF capture time for all 5 and how `gphotos:media/by-year` buckets behave.
- Own OAuth client visibility.
  - *Given* Tyler's new own client_id and scopes `appendonly`, `readonly.appcreateddata`, `edit.appcreateddata`, *When* `mediaItems.list` runs, *Then* the doc records the visible count vs the 7,757 manifest files (expected: near 0 for items uploaded by rclone's shared client, INFERRED).
- Date edit attempt.
  - *Given* one test file uploaded via the own client, *When* `mediaItems.patch` is called with `updateMask=mediaMetadata.creationTime`, *Then* the doc records the response (research expects HTTP 400 because only `description` is patchable, VERIFIED in the API reference).
- Shared client_id status.
  - *Given* `rclone config show gphotos` with secrets redacted, *When* inspected, *Then* the doc records whether the remote uses rclone's shared client_id and the retirement risk.
- Undated-upload placement (decides whether `YearPrecisionPolicy` rule 3 is needed).
  - *Given* one throwaway test file with no EXIF date uploaded to a throwaway album, *When* the item's timeline date is read back (rclone `lsjson` ModTime or the web UI), *Then* the doc records whether Google Photos places it at upload time or at file mtime.
- Album re-use and same-bytes behavior after trash (backs Story 9.6, currently INFERRED).
  - *Given* a throwaway album with 2 files, trashed in the web UI by Tyler, *When* the same album name is uploaded again via rclone `copy`, *Then* the doc records whether the album is reused or duplicated, and whether unchanged bytes re-appear as a new item or stay deduped.
- Join-key stability and observability baseline (backs Story 9.9 and the `AuditClear` coverage rule).
  - *Given* the 5 test files edited by exiftool after upload, *When* listed again, *Then* the doc records whether remote filename, size and `ModTime` change with the edit (filename + size alone is not a safe join key: camera names such as `IMG_0001.jpg` repeat across albums and size changes after an EXIF write) and whether the own OAuth client can see items the shared client uploaded (`observable` versus `unobservable`).
  - The throwaway album and files used here are removed from the library afterwards and the spike notes are kept out of the public repo (counts only in ADR-008).
- Fallback if rclone dates are not EXIF dates.
  - *Given* the rclone `ModTime` check above fails for any of the 5 files, *When* recorded, *Then* the doc states that Success Metric 1 must be measured via Takeout (Story 9.4) and names that as the audit path (Story 9.3 prints the matching message).
**Files**: `G/spikes/gphotos_capabilities.py`, `project_plans/gphotos-organizer-pipeline/decisions/ADR-008-remediation-strategy-interface.md`

##### Task 9.1a: Spike script + redacted evidence capture (S)
##### Task 9.1b: Record outcomes in ADR-008 (XS; wall-clock: Tyler creates OAuth client)

#### Story 9.2: Upload gate v1 and advisory manifest
**As an** operator, **I want** upload to require resolved dates and a passing audit, **so that** nothing undated reaches the timeline, "uploaded" claims are scoped, and the requirements' "upload only after audit passes" is implemented rather than only stated.
**Depends on**: 9.9 (Audit join, flagging, and the audit-clear pre), 8.4 (Plan/apply), 8.6 (Derived WriteState and metadata_status), 1.6 (Deny-list upload gate v0), 1.7 (Truthful status enums and status migration).
**Acceptance Criteria**:
- Gate refuses unresolved albums.
  - *Given* an album with 40 files of which 1 has status `Review`, *When* `upload --apply` runs, *Then* it refuses with `Blocked: 1 of 40 files in '<album>' have no resolved date. Run: gphotos-organizer review next`.
- Allowed files are those with a Verified write or a backed on-disk date (narrowed per consistency review B1; Story 8.6 `upload_ready`); the Story 1.6 global fail-closed v0 rule is superseded by this decision-based predicate.
  - *Given* all files with `write_state == Verified` or an `Anchor` whose `OnDiskDate` is backed (`source=exif`, `Genuine`, equal to the decision), and the album not denied, *When* run, *Then* upload proceeds.
  - *Given* a `UserOverride` file or an `Anchor` from a dated filename or an owner-pinned album whose date has NOT yet been written (no `Verified` row), *When* `upload --apply` runs, *Then* the album is blocked with `Blocked: N files have a decided date that is not written yet. Run: gphotos-organizer plan, then fix-metadata --apply`.
  - *Given* a video with an unresolved decision, *When* run, *Then* it blocks the album like any file (videos are not exempt).
- Year-precision files are held.
  - *Given* files whose decisions are coarser than Day and not released with `--allow-year-precision` (Story 8.4), *When* `upload --apply` runs, *Then* the album is blocked with `Blocked: N files have year-only dates. Review: gphotos-organizer review list --source year_precision`.
- Upload only after audit passes (`AuditClear`).
  - *Given* no completed `audit` newer than the album's last write, *When* `upload --apply` runs, *Then* the album is blocked with `Blocked: no audit covers '<album>' since its last write. Run: gphotos-organizer audit`; *Given* an audit that lists suspicious items for the album, *Then* it is blocked naming the count; *Given* `--allow-unaudited`, *Then* upload proceeds with a loud warning logged to `DATA/logs`. For `generation>=2` albums it additionally requires zero surviving remote copies (Story 9.6).
- `AuditClear` requires positive observability (pre-mortem failure mode 5).
  - *Given* an audit whose `Coverage` for the album is `unobservable` (the own OAuth client cannot see rclone-uploaded items, so zero copies would be reported vacuously), *When* `upload --apply` runs for a `generation>=2` album, *Then* it is blocked with `Blocked: the audit cannot see this album's old items (coverage: unobservable), so "zero surviving copies" proves nothing. Use a Takeout audit: gphotos-organizer audit --source takeout --takeout PATH`.
  - *Given* coverage `observable` but `baseline_count == 0` (no items seen before trashing), *Then* the same block with `baseline_count=0`.
  - *Given* `--i-verified-trash <album>` (T3: the prompt asks for that album's local file count, because the album id is already on the command line), *Then* the gate passes for that album only, the override is logged to `DATA/logs` with the timestamp, and a post-upload duplicate check (`audit` item count versus local file count) runs and is stored.
- Confirmation tier (Story 1.13).
  - *Given* `upload --apply` on a TTY with 21 uploadable albums, *When* the per-album gate lines have printed as `Gate: <album>: ready (would upload)` or `Gate: <album>: Blocked: ...` (never `ok (uploaded_unverified)` before consent), *Then* it prints `About to upload 21 albums (7,757 files; not reversible by this tool; fix later with: audit --plan). Type the number of albums to upload to continue:` (T2, token not repeated in the prompt; blocked albums are excluded from the count; with exactly one uploadable album the token is its file count, not `1`); `Album <title>: ok (uploaded_unverified)` lines print only after the confirmation, as each album finishes; `--allow-unaudited` is also T2 and `--i-verified-trash <album>` is T3 (token: the album's local file count); `--yes` works only without a TTY.
- Manifest stays advisory and records more.
  - *Given* a successful upload, *When* the manifest entry is written, *Then* it holds upload timestamp, rclone summary counts (`--use-json-log`/stats), and `upload_status=uploaded_unverified` until `audit` confirms.
- Legacy 604 grandfathered.
  - *Given* the 604 existing entries, *When* loaded, *Then* each is `uploaded_unverified` and none is re-uploaded.
**Files**: `G/pipeline/upload_gate.py`, `G/pipeline/audit_clear.py`, `G/uploader.py`, `G/pipeline/upload_service.py`, `G/tests/test_upload_gate_v1.py`

##### Task 9.2a: Predicate over decisions + `WriteState` + deny list + year-precision hold (S)
##### Task 9.2b: `AuditClear` predicate (coverage, `baseline_count`, `--i-verified-trash`) and `--allow-unaudited` (S)
##### Task 9.2c: Manifest additive fields via the seam (S)

#### Story 9.3: rclone audit: enumerate and store remote items
**As an** operator, **I want** remote items enumerated by date and stored, **so that** the "all uploaded" claim is replaced by an inspected one with stated coverage, including the items uploaded from files that carried legacy placeholder dates.
**Depends on**: 9.1 (Google Photos capability check), 1.8 (Quota retry seam and fake-429 test), 1.9 (Legacy placeholder detector and quarantine re), 2.2 (Two stores derived + source of truth , migrat).
**Acceptance Criteria**:
- Enumerate and store.
  - *Given* a fake rclone `lsjson` listing of 100 items (3 dated within the `UploadWindow`), *When* `audit --source rclone` runs, *Then* 100 `uploads_observed` rows are stored with `source=rclone`.
- Coverage is stated and stored per album.
  - *Given* the run, *When* it finishes, *Then* it prints `Coverage: rclone-created items only (cannot see items uploaded by other apps)`.
  - *Given* a manifest-completed album with 40 files for which the listing returns 0 items (the own OAuth client cannot see the shared client's uploads), *When* the audit stores results, *Then* the album's `Coverage` is `unobservable` with `baseline_count=0` and the run prints `Observed 0 of 40 manifest-claimed files in '<album id>': coverage unobservable`; with 38 of 40 seen it is `observable`, `baseline_count=38`, and the run prints the coverage ratio 0.95. The baseline is stored at audit time, before any trash.
- Remote dates that match the legacy placeholder signature are counted, so Success Metric 1 can see already-uploaded placeholder-dated items.
  - *Given* remote items dated `1962-01-01T12:03:40`, `2021-01-01T12:00:05` and `1990-06-14T09:12:00`, *When* stored, *Then* the first two are tagged `remote_date_matches_legacy_placeholder` (Jan 1 and `12:00:00 + 5 s x k`), the third is not, and the run prints `Remote items dated like legacy placeholders: N` (a class independent of the decisions, which may themselves be derived from placeholders). Because all 604 albums were uploaded from placeholder-carrying files, these sit in the past, not in the upload window, so counting only "dated in upload window" would report 0 incorrectly.
- Fallback when rclone dates are not EXIF dates.
  - *Given* the Story 9.1 spike showed `ModTime` is not the EXIF capture time (or the own OAuth client sees ~0 rclone-uploaded items), *When* the audit runs, *Then* it prints `Remote dates are not EXIF capture dates for this remote; Metric 1 is UNMEASURED via rclone. Use: gphotos-organizer audit --source takeout --takeout PATH` and exits 0 without claiming a clean audit.
- Auth expiry is explained.
  - *Given* rclone fails with an expired/revoked token (7-day testing-mode tokens, pitfalls section 6), *When* the audit runs, *Then* it prints `rclone is not configured or its token expired. Run: gphotos-organizer setup-rclone. Nothing was changed.`
**Files**: `G/pipeline/audit.py`, `G/pipeline/uploads_observed.py`, `G/pipeline/migrations/pipeline/s0903_uploads_observed.sql`, `G/cli_audit.py`, `G/tests/test_audit.py`, `G/tests/fakes/fake_rclone.py`

##### Task 9.3a: Enumerator (rclone) + `uploads_observed` repository (S)
- Files: `G/pipeline/audit.py`, `G/pipeline/uploads_observed.py`, `G/pipeline/migrations/pipeline/s0903_uploads_observed.sql`, `G/tests/test_audit.py`
##### Task 9.3b: Placeholder-signature tagging, coverage line, spike-failure fallback, auth-expiry message (S)
- Files: `G/pipeline/audit.py`, `G/cli_audit.py`, `G/tests/fakes/fake_rclone.py`

#### Story 9.4: Takeout parser (audit source)
**As an** operator, **I want** Google Takeout JSON sidecars parsed, **so that** items not visible to rclone can still be audited.
Requirement trace: beyond the written In Scope list; it serves Success Metric 5 (audit enumerates uploaded items by remote date) in the case where rclone cannot see items or its dates are not EXIF dates (the Story 9.1 fallback).
**Depends on**: 9.3 (rclone audit: enumerate and store remote item).
**Acceptance Criteria**:
- Parses `photoTakenTime`.
  - *Given* a sidecar `IMG_1.jpg.json` with `photoTakenTime.timestamp = "1480000000"`, *When* parsed, *Then* the observed date is `2016-11-24T15:06:40Z` (UTC) and the item is stored `source=takeout`.
- Duplicate-name handling.
  - *Given* `IMG_1(1).jpg` with sidecar `IMG_1.jpg(1).json`, *When* parsed, *Then* they pair correctly.
- Large export streaming.
  - *Given* a directory of 10,000 sidecars, *When* parsed, *Then* memory is bounded (streamed) and unmatched sidecars are counted.
**Files**: `G/pipeline/takeout.py`, `G/tests/test_takeout.py`

##### Task 9.4a: Parser with Takeout naming quirks (S; format specifics beyond this are UNVERIFIED, inspect `gpth`-style tools first)
##### Task 9.4b: Tests with synthetic sidecars (S)
Wall-clock: Takeout export generation by Google (Tyler requests it).

#### Story 9.9: Audit join, flagging, and the audit-clear predicate
**As an** operator, **I want** observed remote items joined to local decisions and flagged into the review list, **so that** suspicious uploads are fixed and `upload` can require a clean audit.
**Depends on**: 9.4 (Takeout parser audit source), 2.8 (fuse command and decisions table), 7.2 (Terminal review).
**Acceptance Criteria**:
- Join and flag.
  - *Given* local files with decisions and `uploads_observed` rows, *When* joined, *Then* the join key is `ContentKey` captured pre-write plus pre-write filename and size (stored in the journal, Story 8.3) plus remote `ModTime` and name per the Story 9.1 finding; filename + size alone is a weak fallback that never clears an item (it collides on camera names such as `IMG_0001.jpg` across albums and changes after the EXIF write). Items whose remote date lies in the `UploadWindow`, outside the decision interval, or matches the legacy placeholder signature (time signature, Jan 1, or a `Suspect`/`LegacyPlaceholder` local classification) are added to the review list with `source=audit`.
- Success Metric 1 (numeric bound, requirements.md).
  - *Given* flagged items, *When* the audit ends, *Then* it prints `Suspicious (dated in upload window): N   Dated like legacy placeholders: M   Outside decision interval: K`, with `Unmatched: R remote-only, L local-only`.
  - *Given* items whose bound B is the `latest` of the decision interval (else of the folder-year or filename interval), *When* the audit ends, *Then* it also prints `Metric 1: violations V (bounded), unbounded U, unobservable albums A`, where a violation is a matched item on an `observable` album whose remote date is later than B + 1 year or is dated in the upload window or like a legacy placeholder while B is earlier than the window start; items with no B count in U and are never reported clean; the first run's V is stored as the baseline in `audit_runs`.
- Join does not trust placeholder-built decisions.
  - *Given* a decision derived from a `LegacyPlaceholder` or `Suspect` date (neither is an anchor, Story 3.4, so it can only be `Review`/`Conflict`), *When* joined, *Then* the item is flagged, not cleared by "matches decision".
- A clean-looking audit must be backed by coverage and a manual spot-check (pre-mortem failure modes 5 and 11).
  - *Given* an album whose `Coverage` is `unobservable`, *When* the audit ends, *Then* the run says `Cannot call this album clean: coverage unobservable` and never prints a zero-suspicious "clean" verdict for it; the printed coverage ratio (observed / manifest-claimed files) below the agreed threshold (default 0.9) also withholds the word "clean".
  - *Given* the first audit that would otherwise report clean, *When* it ends, *Then* it prints `Spot-check: open Google Photos and compare 30 random uploaded items (list: DATA/reports/spotcheck-<ts>.md, ids only) with their observed dates`, and `AuditClear` requires the owner's recorded `audit spotcheck --ok` for that audit run.
- Audit completion is recorded for the gate.
  - *Given* a finished audit, *When* it ends, *Then* an `audit_runs` record (timestamp, source, per-album suspicious counts, per-album `Coverage` and `baseline_count`) is stored, and `AuditClear(album)` reads it (Story 9.2); a `remediation done` item is only cleared by a later audit.
**Files**: `G/pipeline/audit_join.py`, `G/pipeline/migrations/pipeline/s0909_audit_runs.sql`, `G/cli_audit.py`, `G/tests/test_audit_join.py`

##### Task 9.9a: Join and flagging into review items (M)
##### Task 9.9b: `audit_runs` record and `AuditClear` query (S)

#### Story 9.5: `RemediationStrategy` interface and web-UI worklist
**As an** operator, **I want** a worklist grouped by album for "Edit date & time", **so that** small batches can be fixed by hand with a shrinking checklist.
**Depends on**: 9.9 (Audit join, flagging, and the audit-clear pre).
**Acceptance Criteria**:
- Strategy interface.
  - *Given* `RemediationStrategy` Protocol with `name`, `capability`, `plan(flagged) -> RemediationWorklist`, *When* `audit --plan --strategy webui` runs, *Then* the registered `WebUiWorklist` is invoked and no network call is made.
- Worklist content.
  - *Given* 12 flagged items in album `1985 Beach` with target interval 1985-06..1985-08, *When* planned, *Then* `DATA/remediation/webui-1985-Beach.md` lists each filename, remote date, target date, and a search hint (album title, upload date), grouped so one multi-select edit covers a group.
- Done-state tracked.
  - *Given* `remediation done <item>` , *When* run, *Then* a `ReviewDecision(kind=remediation, action=done)` is appended and the next `audit` verifies it against remote dates before removing it.
- Items can be waived as accepted-as-manual residual (Success Metric 5).
  - *Given* `remediation waive --album A7 --reason "no web-UI route"`, *When* run, *Then* a `ReviewDecision(kind=remediation, action=waive, reason=...)` is appended, the items leave the open worklist, `audit --plan --list` shows state `waived`, and `report` and `status` count fixed (audit-clear after `done`), waived and open separately; a later audit that finds a waived item still wrong keeps it `waived`, never `fixed`.
- The worklist can be listed.
  - *Given* worklists for 7 albums, *When* `audit --plan --list` runs, *Then* it prints one row per worklist item (album, filename, remote date, target, state `open|done|still-wrong`) with `Next: gphotos-organizer remediation done --album "<album>"`; with none it prints `No worklist. Next: gphotos-organizer audit --plan --strategy webui`; and `remediation done X` for an unknown item prints `No worklist item 'X'. List: audit --plan --list`.
**Files**: `G/pipeline/remediation/__init__.py`, `G/pipeline/remediation/webui.py`, `G/cli_audit.py`, `G/cli_remediation.py`, `G/tests/test_remediation_webui.py`

##### Task 9.5a: Protocol + registry + CLI `audit --plan` and `audit --plan --list` (S)
##### Task 9.5b: Web-UI worklist renderer and done tracking (S)
##### Task 9.5c: `remediation waive` with reason and the fixed/waived/open counters (XS)
- Files: `G/pipeline/remediation/__init__.py`, `G/cli_remediation.py`, `G/tests/test_remediation_webui.py`

#### Story 9.6: Trash and re-upload strategy
**As an** operator, **I want** corrected-EXIF re-upload for large batches, **so that** hundreds of items need one trash action rather than hundreds of edits.
**Depends on**: 9.5, 9.2 and the Story 9.1 album-reuse result (which gates the real run). Scope: only albums for which an audit proved the wrong-dated copies are visible (`Coverage == observable`, `baseline_count > 0`).
**Acceptance Criteria**:
- Pilot first on a throwaway album (pre-mortem failure mode 5).
  - *Given* a throwaway album of 5 files created for this purpose (Owner Checklist item 7), *When* `audit --plan --strategy trash-reupload --pilot <album>` runs, *Then* it executes the whole loop on that album only (corrected EXIF, trash list, owner trash, audit shows zero copies with observable coverage, re-upload, audit again) and records the outcomes (album reused or duplicated, items per file, dates) in ADR-008; until that record exists, `--pilot` is the only accepted target and any real album exits 1 with `Run the pilot first: gphotos-organizer audit --plan --strategy trash-reupload --pilot <throwaway album>. Nothing was changed.`
  - *Given* the Story 9.1 album-reuse result says Google duplicates the album or re-dedups unchanged bytes, *Then* the real run is blocked with the specific finding and the plan falls back to the web-UI worklist (Story 9.5).
- Orders the steps and never auto-deletes.
  - *Given* 300 flagged items in 5 albums, *When* `audit --plan --strategy trash-reupload` runs, *Then* it (1) plans journaled EXIF corrections locally (via 8.4), (2) emits `DATA/remediation/trash-<album>.csv` of remote items to trash in the web UI, (3) marks albums `awaiting_trash`, and (4) performs no remote mutation.
- Re-upload is gated on an audit, not on a self-reported flag, and recorded as a new generation.
  - *Given* Tyler marks an album `trashed` but the last audit still lists remote copies of its old items, *When* `upload --apply` runs, *Then* it is blocked with `Blocked: audit still shows N remote copies of '<album>'. Trash them, run: gphotos-organizer audit`.
  - *Given* an audit showing zero surviving remote copies WITH `Coverage == observable` and `baseline_count > 0` (Story 9.2), all files `Verified`, *When* `upload --apply` runs, *Then* the gate passes, the manifest entry gets `generation=2`, and rclone uploads (changed bytes -> new Google item; behavior per the Story 9.1 spike, INFERRED until then).
- Dedup caveat printed.
  - *Given* a file whose bytes did not change, *When* planned, *Then* it is refused with `Bytes unchanged: Google dedups identical uploads, so this would not fix the date`.
- Verification.
  - *Given* the re-upload finished, *When* `audit` re-runs, *Then* the items' remote dates are compared with decisions and results shown as verified/unverified.
**Files**: `G/pipeline/remediation/trash_reupload.py`, `G/uploader.py`, `G/pipeline/upload_gate.py`, `G/pipeline/upload_service.py`, `G/tests/test_remediation_trash.py`

##### Task 9.6a: Worklist/CSV and album state machine (S)
##### Task 9.6b: Generation-aware manifest + gate integration (M)
##### Task 9.6c: Tests with fake rclone (S)
##### Task 9.6d: `--pilot` mode, pilot record gate and observable-coverage scope (S)
Wall-clock: Tyler's web-UI trash step; daily upload quota resets.

#### Story 9.7: Optional unofficial helper strategy (opt-in, labeled)
Requirement trace: beyond the written In Scope list; it serves In Scope 5 (remediation) for large batches only if the owner opts in (ADR-008); disabled unless `--i-accept-unofficial-risk`.
**As an** operator, **I want** an optional strategy that prepares input for https://github.com/xob0t/Google-Photos-Toolkit (undocumented web API; list/trash/add-to-album; README does not mention date edits), **so that** bulk trash can be semi-automated if I accept the risk.
**Depends on**: 9.5 (RemediationStrategy interface and web-UI work).
**Acceptance Criteria**:
- Opt-in and labeled.
  - *Given* no flag, *When* `audit --plan --strategy unofficial-gptk` runs, *Then* it exits with `Unofficial tool: undocumented Google web API, may break or violate Terms of Service. Re-run with --i-accept-unofficial-risk to continue.`
- Never executes the tool.
  - *Given* the flag, *When* run, *Then* it only writes an item-id/filter file and step instructions and does not invoke the toolkit; no claim is made that it edits dates.
- README format check first.
  - *Given* the toolkit README at implementation time, *When* Task 9.7a reads it, *Then* the output format is derived from it (UNVERIFIED today) and the doc notes the README commit.
**Files**: `G/pipeline/remediation/unofficial_gptk.py`, `G/tests/test_remediation_gptk.py`

##### Task 9.7a: Read README, define output (XS)
##### Task 9.7b: Strategy + opt-in guard + tests (S)

#### Story 9.8: [SPIKE] `gpmc` date-edit capability
**Timing**: after Story 9.1 (W3); evidence only.
Requirement trace: beyond the written In Scope list; an evidence-gathering spike for In Scope 5 (remediation). No production code.
**As an** operator, **I want** to know whether https://pypi.org/project/gpmc/ (reverse-engineered mobile API uploader) can set dates, **so that** a future strategy is evidence-based; no production code.
**Depends on**: 9.1 (Google Photos capability check).
**Acceptance Criteria**:
- Finding recorded, nothing integrated.
  - *Given* gpmc's README/source at https://pypi.org/project/gpmc/, *When* read and (only with a throwaway test account and Tyler's explicit OK) exercised, *Then* ADR-008 records whether date edit is supported and the ToS/account risk; `ADR-008` stays UNVERIFIED if not tested.
**Files**: `project_plans/gphotos-organizer-pipeline/decisions/ADR-008-remediation-strategy-interface.md`

##### Task 9.8a: Read-only evaluation and ADR note (XS)

### Epic 10: Reporting and observability
**Goal**: The per-run report, structured logs, and a single "where am I" screen, plus privacy hygiene and an end-to-end proof.

#### Story 10.1: Run report
**As an** operator, **I want** counts per plugin, a confidence histogram, anchor error by decade, flags, writes and quota events, **so that** each run is auditable.
**Depends on**: 10.2 (Structured logs and metrics), 2.8 (fuse command and decisions table).
**Acceptance Criteria**:
- Report sections.
  - *Given* a run on the fixture corpus, *When* `report run` executes, *Then* `DATA/reports/run-<id>.md` has sections: plugins (cached/computed/abstain/error), confidence histogram (10 bins), error by decade/color, flagged (albums+files), written (verified/mismatch), quota events, cloud calls.
- Review burden and remediation sections (Success Metrics 5 and 6; computed at report time from the stores, no new emit sites).
  - *Given* a fixture with 30 `Needs review` items across sources, 12 files dated without a human decision and 8 with one, and audit items in states fixed, waived and open, *When* `report` runs, *Then* it has a `Review burden` section (open items per source, decided per action, auto-dated count, reviewed count, auto-dated share, group decisions counted per file) and a `Remediation` section (fixed, waived, open, waived share) with the numbers equal to the fixture's, and neither section sets a pass/fail until the owner has confirmed targets after the baseline.
- Names redacted by default.
  - *Given* a person label "Grandma Ruth", *When* the report is rendered, *Then* it appears as `Person 3` unless `--show-names` is passed; reports are never written under the repo.
- Existing album report unchanged, and the legacy `report` command is migrated with an alias (Story 1.11 disposition).
  - *Given* `report.generate_markdown_report` on the legacy fixture, *When* run, *Then* output matches the pre-change golden.
  - *Given* the `report` group in `cli_report.py` (`invoke_without_command`), *When* `report albums --mapping M --out O` runs, *Then* the output file equals the legacy `report --mapping M --out O` output byte for byte; *When* bare `report --out O` is run with a legacy flag, *Then* it runs `report albums` and prints the one-line notice; *When* bare `report` runs with no legacy flag, *Then* it writes the run report above.
  - Report files carry album ids and counts, and person names only under `--show-names`; the report is never written under the repo and never pasted into a PR (privacy rule).
**Files**: `G/report.py`, `G/cli_report.py`, `G/pipeline/run_report.py`, `G/tests/test_run_report.py`

##### Task 10.1a: Aggregations from `run_metrics`/`decisions` (S)
##### Task 10.1b: Rendering + redaction (S)
##### Task 10.1c: Review-burden and remediation sections (S)
- Files: `G/pipeline/run_report.py`, `G/tests/test_run_report.py`

#### Story 10.2: Structured logs and metrics
**As an** operator, **I want** a bound `run_id` and JSONL log, **so that** failures are traceable.
**Depends on**: 2.5 (analyze runner).
**Acceptance Criteria**:
- Run-bound logs.
  - *Given* any command, *When* it runs, *Then* `DATA/logs/run-<id>.jsonl` exists, every line has `run_id`, `stage`, and error lines include `content_key`.
- Metrics written.
  - *Given* `analyze` over 10 files, *When* done, *Then* `run_metrics` has `plugin_files_total` rows summing to 10 per plugin.
- Other stages emit through the same API, in their own stories.
  - *Given* `pipeline/metrics.emit(name, labels, value)`, *When* Stories 2.8, 8.4, 9.9 and 9.2 are implemented after this one, *Then* each calls it for its own metric names (listed in the Observability Plan); this story wires only `runner.py` and the logging sink, so it edits no file owned by a later story.
**Files**: `G/pipeline/logging_setup.py`, `G/pipeline/metrics.py`, `G/pipeline/runner.py`, `G/pipeline/migrations/pipeline/s1002_run_metrics.sql`, `G/tests/test_metrics.py`

##### Task 10.2a: Loguru sink + run id (XS)
##### Task 10.2b: Metrics writer, `run_metrics` migration, and the `runner.py` call sites (S)

#### Story 10.3: `status` as the single "where am I" screen
**As an** operator, **I want** per-stage counts and the next command, **so that** I always know what to run.
**Acceptance Criteria**:
- Stage table, per-source rows and next step (UX-104, UX-111).
  - *Given* 17,145 indexed, 12,000 analyzed, 35 undecided file items, 137 undecided album items, 31 albums holding Suspect files (14,812 files) and 0 planned, *When* `status` runs, *Then* it prints counts per stage, `review file 0 35`, `review album 0 137`, `review placeholder 0 31 ... 14,812 files remaining` (never 15,000 rows) and `Next: gphotos-organizer analyze` with the review command named in the same line, because analyze has pending files.
  - *Given* 37 files that failed on `analyze` and failed again on `--retry-failed` with the same `error_class` (permanently failed, Story 2.5) and nothing else pending, *When* `status` runs, *Then* the Note column reads `37 failed -> errors.jsonl` and rule (2) does not fire; *Given* 5 files whose failure has `attempts=1`, *Then* `Next: gphotos-organizer analyze --retry-failed`.
- Next: follows the rule order of UX S9.
  - *Given* analyze complete and fuse current with 35 undecided file items, *Then* `Next: gphotos-organizer review next`; *Given* only placeholder items undecided, *Then* `Next: gphotos-organizer review list --source placeholder --by album` (this rule precedes the plan rules, and `review next` prints the same line before any `All N decided` line); *Given* 3 skipped leftovers and nothing undecided, *Then* `Next: gphotos-organizer plan   (3 items parked; to revisit: review next --state parked)`, so following only Next: lines reaches `Nothing to do` and cannot loop (a test follows Next: lines from a fixture with permanently failed files and parked leftovers until `Nothing to do`, bounded at 10 steps); *Given* a genuine placeholder or a cleared audit item, *Then* it is neither parked nor counted as a leftover; *Given* a drive or database problem, *Then* its fix command comes first. The order is the eight rules of UX S9.
- Truthful upload line.
  - *Given* 604 grandfathered albums, *When* run, *Then* it prints `604 albums uploaded_unverified (not audited)`.
- The legacy `status` is replaced in place (Story 1.11 disposition).
  - *Given* the pre-change fixture, *When* `status --mapping M --manifest F` runs, *Then* the header still shows the five legacy rows (scanned source, total albums, total media files, flagged for review recounted from `needs_review` rather than the stored `flagged_albums_count` counter, uploaded albums `N / total`) before the stage table.
- Explain topics (Story 1.13 content).
  - *Given* `status --explain reverse`, `--explain vocabulary` and `--explain tiers`, *When* run, *Then* each prints the matching table from `pipeline/explain_topics.py` and ends with `Next:`; the status screen uses `labels.display()` for every state word and prints `Read-back OK`, never a bare `verified`.
- Reads both databases and says so.
  - *Given* `status` needs `pipeline.db` (stage counts) and `state.db` (`WriteState`), *When* either is missing, *Then* it prints which one (`No state database at DATA/state.db. Next: gphotos-organizer index`) and still exits 0.
**Depends on**: 8.6, 2.8, 7.2, 10.2 and 1.13.
**Files**: `G/cli_status.py`, `G/pipeline/status.py`, `G/tests/test_status_screen.py`

`pipeline/status.py` is owned by this story alone (Story 8.6 owns `pipeline/write_state.py`); the write line reads `WriteState` from it.

##### Task 10.3a: Implement `status` over stage counts, `WriteState` and audit state (S)
##### Task 10.3b: `status --explain reverse|vocabulary|tiers` wired to `explain_topics` (XS)
- Files: `G/cli_status.py`, `G/tests/test_status_screen.py`
##### Task 10.3c: Per-source review rows, the placeholder row and the `Next:` order (XS)
- Files: `G/pipeline/status.py`, `G/tests/test_status_screen.py`
##### Task 10.3d: Eight-rule `Next:` precedence: permanently failed files excluded from rule (2), `analyze --retry-failed` for retryable ones, parked leftovers as an alternative on the `plan` line, and the follow-the-Next:-lines no-loop test (XS)
- Files: `G/pipeline/status.py`, `G/tests/test_status_screen.py`

#### Story 10.4: Privacy hardening
**As an** operator, **I want** biometric-adjacent data kept out of git and logs, **so that** the confidential classification is met.
**Depends on**: 1.1 (Test harness, DataDir, tool/path resolution).
**Acceptance Criteria**:
- Gitignore and perms.
  - *Given* `DATA` resolved to the default, *When* `git check-ignore` runs on repo paths for `*.db`, `thumbs/`, `review/`, *Then* all are ignored and the data dir is outside the repo.
- No names in committed paths.
  - *Given* the repo and a `people.toml` (created by Story 4.5), *When* `test_no_names_in_repo` greps `project_plans/` and `G/` for names present in it, *Then* zero matches; *Given* no `people.toml` yet, *Then* the test reports `skipped: no people.toml` and passes.
- Cloud send log lists exactly what left the machine.
  - *Given* a cloud run, *When* `cloud-send.jsonl` is read, *Then* each line has `ContentKey`, bytes, model and timestamp and no image content.
- The repo is public, so album titles and dates are protected too (pre-mortem failure mode 8).
  - *Given* a local `album_mapping.json`, *When* `test_no_names_in_repo` scans `project_plans/`, `G/` and `docs/` for album titles from it (and birth/death dates and per-person cluster counts from `people.toml`), *Then* any hit fails the test unless the file is on an explicit allowlist the owner chose in Owner Checklist item 5; with no mapping file present the test reports `skipped: no album_mapping.json` and passes.
  - *Given* `--data-dir` or `GPHOTOS_DATA_DIR` resolving inside any git work tree or under a known synced folder (Syncthing marker `.stfolder`, Dropbox `.dropbox`), *When* `DataDir.resolve()` runs, *Then* it exits 1 with `Data directory <path> is inside a git work tree / synced folder. Choose a path outside it. Nothing was changed.`
  - *Given* the `.gitignore` gphotos block, *When* `git check-ignore` runs on `*.db`, `*.npy`, `thumbs/`, `review/`, `remediation/`, `prewrite/`, `journals/`, `backups/` and exported `*.html` sheets, *Then* all are ignored, and a pre-commit check (`git diff --cached` scan) fails on a staged `.db`, `.npy`, `people.toml` or album title from the mapping.
**Files**: `.gitignore`, `G/pipeline/datadir.py`, `G/tests/test_privacy.py`

##### Task 10.4a: Tests and any missing ignore entries (S)

#### Story 10.5: End-to-end smoke on a fixture corpus
**As an** operator, **I want** the whole pipeline proven on generated fixtures, **so that** nothing is first run on the real drive.
**Depends on**: every other story (the smoke test runs last, in the final wave).
**Acceptance Criteria**:
- Full dry-run chain.
  - *Given* a generated corpus of 30 images (10 with camera EXIF, 10 in dated folders, 10 undated in `2021 random photos`-style folders) and fake rclone, *When* `scan -> index -> analyze (core plugins) -> fuse -> plan -> fix-metadata (dry-run) -> upload (dry-run)` runs, *Then* the undated folder is blocked by the gate, the dated ones are planned, and nothing on disk changed (hash of fixtures equal).
- Apply then undo restores.
  - *Given* the same corpus, *When* `fix-metadata --apply` then `undo --run <id> --apply` run, *Then* all tag values equal the pre-run snapshot.
- Plugin-add claim.
  - *Given* the toy plugin from Story 2.3, *When* `git diff --stat G/cli.py` is taken after adding it, *Then* `cli.py` is untouched.
- CLI growth guard (ratchet, Story 1.11).
  - *Given* every `G/cli*.py`, *When* `test_cli_size.py` runs, *Then* no NEW command body exceeds 40 lines (excluding option declarations) and no baseline command grew; it fails if the baseline file was raised.
- Every command ends with a `Next:` or `Nothing to do` line (UX-29).
  - *Given* each command in the inventory run on the fixture corpus, *When* the output is checked, *Then* the last line starts with `Next:` or `Nothing to do`.
- Legacy placeholders are handled end to end.
  - *Given* fixture files carrying `2021:01:01 12:00:10` with no Make, plus `2021:06:04 12:00:15` files forming a 5-second ladder (non-Jan-1) and one lone-Jan-1 file at `00:00:18`, *When* `index -> analyze -> fuse -> plan` runs, *Then* the first two groups are classified `LegacyPlaceholder`, the lone-Jan-1 file `Suspect`; none is ever an `Anchor`, none is planned for overwrite, and `upload` blocks their album.
- Help, vocabulary and option parity hold over the full app (Stories 1.12, 1.13).
  - *Given* the full app, *When* `--help` is parsed, *Then* the panels are Setup, Analyze, Review, Safety, Write, Upload, Audit, Legacy (the last empty once Task 10.5c ran) with every command in exactly one; *When* `--json` is run on every list-type command, *Then* each has a top-level `items` array; *When* the vocabulary scan runs over every screen's output on the fixture corpus, *Then* it finds no cross-use.
- Command names are exactly the inventory (Story 1.11 rule) and no legacy shim remains.
  - *Given* the full app built from every `G/cli*.py`, *When* the top-level names are listed, *Then* they equal the Story 1.11 inventory with no duplicates, and no module has `LEGACY = True` (Task 10.5c deletes `cli_legacy.py` once Stories 7.2, 10.1 and 10.3 have absorbed `review`, `report` and `status`).
- The Adapter is removed (Task 10.5c).
**Files**: `G/tests/test_e2e_smoke.py`, `G/tests/fixtures/make_corpus.py`, `G/tests/test_cli_size.py`, `G/cli.py` (drop `infer_cmd` only), `G/cli_legacy.py` (delete), `G/ai_enrich.py`, `G/review_proto.py` (delete)

##### Task 10.5a: Corpus generator with exiftool (S)
- Files: `G/tests/fixtures/make_corpus.py`
##### Task 10.5b: E2E chain, undo, plugin-add, legacy-placeholder and size guards (M)
- Files: `G/tests/test_e2e_smoke.py`, `G/tests/test_cli_size.py`
##### Task 10.5c: Remove the `ai_enrich` Adapter: delete `enrich_mapping_data` and `infer_cmd`, with a failing-import guard; delete `cli_legacy.py` and the Story 7.5 throwaway `review_proto.py` (XS)
- Files: `G/cli.py`, `G/cli_legacy.py`, `G/ai_enrich.py`, `G/review_proto.py`

---

## Effort estimate

Basis (one authoritative basis, stated once): **bottom-up from the task cost classes in this plan, at the ESTIMATION.md band midpoints XS = 20k, S = 55k, M = 130k raw tokens per task (no L tasks exist)**. Each story's raw figure below is the sum of its own `##### Task` classes; the flat per-story round numbers used before the 2026-10-16 triad repair pass (8,425k raw over 67 stories, "no task-level basis") are retired. Bands and weights are INFERRED (ESTIMATION.md); recalibrate after the first implementer run (Task 1.1g). Implementation runs assumed 12% output share; cost unit CU = fresh-input-equivalent tokens = tokens x (1 + 4 x output share) with cache discounts ignored (conservative). Verification multiplier x1.75 on raw tokens, with the added review share costed at 6% output.

| Story | Name | Tasks (classes) | Raw tokens (task sum) | Output share | Impl CU | Wall-clock blocker |
|---|---|---|---|---|---|---|
| 1.1 | Test harness, DataDir, LegacyPaths, tools seam, fail() | 7 (3XS, 4S) | 280k | 12% | 414k | none |
| 1.2 | Atomic JSON persistence | 3 (3S) | 165k | 12% | 244k | none |
| 1.3 | exiftool failure accounting | 2 (2S) | 110k | 12% | 163k | none |
| 1.4 | dateparse (golden) | 3 (2S, 1M) | 240k | 12% | 355k | none |
| 1.5 | Stop placeholder dates | 3 (3S) | 165k | 12% | 244k | none |
| 1.6 | Deny-list gate v0 (id+name, inside uploader) | 3 (3S) | 165k | 12% | 244k | none |
| 1.7 | Truthful status enums | 3 (3S) | 165k | 12% | 244k | none |
| 1.8 | Quota retry seam + fake-429 test | 2 (2S) | 110k | 12% | 163k | none |
| 1.9 | Legacy placeholder detector (five signals, truth table) + quarantine | 5 (3S, 2M) | 425k | 12% | 629k | drive mounted (Tyler) for the real scan |
| 1.10 | Leftover finder + minimal recover | 3 (3S) | 165k | 12% | 244k | drive mounted (Tyler) |
| 1.11 | CLI shell, service extraction, legacy-apply lock | 6 (2XS, 3S, 1M) | 335k | 12% | 496k | none |
| 1.12 | Help panels, completion, alias notices | 3 (1XS, 2S) | 130k | 12% | 192k | none |
| 1.13 | Confirmation tiers, labels, reversal map | 4 (1XS, 3S) | 185k | 12% | 274k | none |
| 1.14 | Wave integrator and merge-order gate | 2 (1XS, 1S) | 75k | 12% | 111k | none |
| 2.1 | Contract types | 2 (2S) | 110k | 12% | 163k | none |
| 2.2 | Two stores + ContentKey | 4 (3S, 1M) | 295k | 12% | 437k | none |
| 2.3 | Registry | 2 (2S) | 110k | 12% | 163k | none |
| 2.4 | index stage | 2 (1S, 1M) | 185k | 12% | 274k | drive mounted (Tyler) |
| 2.5 | analyze runner | 2 (1S, 1M) | 185k | 12% | 274k | none |
| 2.6 | Fusion Layer A | 2 (1S, 1M) | 185k | 12% | 274k | none |
| 2.7 | Fusion Layer B | 2 (1S, 1M) | 185k | 12% | 274k | none |
| 2.8 | fuse command | 2 (2S) | 110k | 12% | 163k | none |
| 3.1 | folder_year | 2 (1XS, 1S) | 75k | 12% | 111k | none |
| 3.2 | filename_date | 2 (2S) | 110k | 12% | 163k | none |
| 3.3 | ai_enrich seam | 3 (1XS, 2S) | 130k | 12% | 192k | none |
| 3.4 | exif_anchor | 2 (1XS, 1S) | 75k | 12% | 111k | none |
| 3.5 | date-stamp OCR | 3 (2S, 1M) | 240k | 12% | 355k | none |
| 4.1 | CPU timing spike | 2 (1XS, 1S) | 75k | 12% | 111k | drive + 200-image run |
| 4.2 | ML scaffold | 3 (1XS, 2S) | 130k | 12% | 192k | none |
| 4.3 | faces plugin | 3 (2S, 1M) | 240k | 12% | 355k | overnight batch on real corpus |
| 4.4 | cluster pass | 3 (1XS, 1S, 1M) | 205k | 12% | 303k | none |
| 4.5 | people (add/list/edit) + labels | 5 (5S) | 275k | 12% | 407k | Tyler: birth dates, cluster labels |
| 4.6 | identity assignment | 2 (1S, 1M) | 185k | 12% | 274k | none |
| 4.7 | YuNet+SFace fallback | 2 (1S, 1M) | 185k | 12% | 274k | none |
| 5.1 | age plugin | 2 (1S, 1M) | 185k | 12% | 274k | none |
| 5.2 | anchor registry | 2 (2S) | 110k | 12% | 163k | Tyler: trusted albums |
| 5.3 | calibration | 3 (2S, 1M) | 240k | 12% | 355k | none |
| 5.4 | age -> date | 2 (1S, 1M) | 185k | 12% | 274k | none |
| 5.5 | held-out report | 1 (1S) | 55k | 12% | 81k | none |
| 5.6 | Anchor census + ML go/no-go checkpoint | 2 (2S) | 110k | 12% | 163k | Tyler: trusted-album list; dates a 200-file slice |
| 6.1 | print_cues + dup groups + dup_group plugin | 4 (4S) | 220k | 12% | 326k | none |
| 6.2 | embeddings | 2 (1XS, 1M) | 150k | 12% | 222k | overnight batch on real corpus |
| 6.3 | era regressor | 2 (1S, 1M) | 185k | 12% | 274k | none |
| 6.4 | cloud_vision | 3 (2S, 1M) | 240k | 12% | 355k | Tyler: --allow-cloud decision |
| 7.1 | decisions.py (+ typed stable ids) | 3 (1XS, 2S) | 130k | 12% | 192k | none |
| 7.2 | terminal review (+undo-last, --force-guard, --offset) | 7 (6S, 1M) | 460k | 12% | 681k | Tyler review time |
| 7.3 | HTML contact sheets | 6 (4S, 2M) | 480k | 12% | 710k | none |
| 7.4 | HTML export/import | 6 (6S) | 330k | 12% | 488k | none |
| 7.5 | Review-loop usability pass (spike) | 2 (2S) | 110k | 12% | 163k | Tyler: runs the timed pass |
| 7.6 | Group decisions and placeholder visual path | 6 (5S, 1M) | 405k | 12% | 599k | Tyler: group decisions on real albums |
| 8.1 | metadata.py split | 3 (2S, 1M) | 240k | 12% | 355k | none |
| 8.2 | exif snapshot reader | 2 (2S) | 110k | 12% | 163k | none |
| 8.3 | journal (state.db + JSONL) | 2 (1S, 1M) | 185k | 12% | 274k | none |
| 8.4 | plan/apply (+YearPrecisionPolicy, exFAT) | 7 (6S, 1M) | 460k | 12% | 681k | none |
| 8.5 | undo | 1 (1S) | 55k | 12% | 81k | none |
| 8.6 | WriteState + derived status | 1 (1S) | 55k | 12% | 81k | none |
| 8.7 | Placeholder revert / quarantine writer | 3 (2S, 1M) | 240k | 12% | 355k | Tyler: apply decision; drive mounted |
| 8.8 | Drive backup attestation, canary, fsck, pre-write snapshots | 4 (1XS, 2S, 1M) | 260k | 12% | 385k | Tyler: second disk and copy time; unmount the drive and root for `fsck.exfat -n` |
| 9.1 | Google Photos spike | 2 (1XS, 1S) | 75k | 12% | 111k | Tyler: OAuth client creation |
| 9.2 | gate v1 + AuditClear | 3 (3S) | 165k | 12% | 244k | none |
| 9.3 | rclone audit enumerate | 2 (2S) | 110k | 12% | 163k | rclone auth; drive |
| 9.4 | Takeout parser | 2 (2S) | 110k | 12% | 163k | Google Takeout export latency |
| 9.5 | strategy iface + web-UI worklist | 3 (1XS, 2S) | 130k | 12% | 192k | Tyler: manual web-UI edits |
| 9.6 | trash + re-upload | 4 (3S, 1M) | 295k | 12% | 437k | Tyler: web-UI trash; quota resets |
| 9.7 | unofficial toolkit (opt-in) | 2 (1XS, 1S) | 75k | 12% | 111k | none |
| 9.8 | gpmc spike | 1 (1XS) | 20k | 12% | 30k | none |
| 9.9 | audit join + AuditClear | 2 (1S, 1M) | 185k | 12% | 274k | none |
| 10.1 | run report | 3 (3S) | 165k | 12% | 244k | none |
| 10.2 | logs + metrics | 2 (1XS, 1S) | 75k | 12% | 111k | none |
| 10.3 | status screen | 4 (3XS, 1S) | 115k | 12% | 170k | none |
| 10.4 | privacy hardening | 1 (1S) | 55k | 12% | 81k | none |
| 10.5 | e2e smoke | 3 (1XS, 1S, 1M) | 205k | 12% | 303k | none |

- **Sum**: 72 stories, 209 tasks (26 XS, 151 S, 32 M), 12.99M raw implementation tokens (12,985k), 19.22M impl CU (19,218k; raw x 1.48 = 19,218k) (the Tasks column of the table is the class count per story). Verification x1.75 adds ~12.08M CU (12,076k; 0.75 x raw at 6% output, i.e. raw x 0.93). **Total ~31.3M CU** (31,294k; about 22.7M raw tokens). **That is above the requirements' "Large (3-15M CU)" band by ~16.3M CU (about 109%); it is XL, roughly twice the top of Large. The figure is INFERRED and uncalibrated: the per-class midpoints (XS 20k, S 55k, M 130k raw) come from ESTIMATION.md, not from a measured run of this pipeline, so treat it as an order-of-magnitude bound that the W5 and W9 checkpoints below recalibrate.** Full scope is kept by owner decision; nothing was cut. Per-epic impl CU (recounted by `waves.py --effort` from this table): E1 4,017k, E2 2,022k, E3 932k, E4 1,916k, E5 1,310k, E6 1,177k, E7 2,833k, E8 2,375k, E9 1,725k, E10 909k (sum 19,216k of rounded story rows).
- **Did the total move? Yes. Triad repair pass 3: 30,583k to 31,294k CU, +711k, entirely from 6 added tasks (5 S + 1 XS = 295k raw x 2.41 CU per raw token: 1.13d, 7.1c, 7.2g, 7.4f, 7.6f, 10.3d); no story was added or re-sized and nothing was cut. Triad repair pass 2: 29,776k to 30,583k CU, +807k, entirely from 8 added tasks (5 S + 3 XS = 335k raw x 2.41 CU per raw token); no story was re-sized and nothing was cut.** The earlier pass 1 move was: **from ~20.3M CU (20,304k) to ~29.8M CU (29,776k), +9,472k.** Two causes, both counted, neither a re-scope: (1) rebasing on the task sum: the same original 67 stories' 171 tasks sum to 11,025k raw against the old table's 8,425k (+2,600k raw, +6,266k CU at raw x 2.41), because 14 stories ran at least 1.8x above their old figure (1.1, 1.5, 1.7, 1.9, 1.10, 4.7, 8.1, 8.4, 8.8 and 9.6 on their original tasks; 1.2, 1.11, 7.3 and 7.4 also include tasks the repair pass added) while a handful ran below it (9.8: 50k old, 20k by tasks; 3.4, 5.5, 10.4 and 9.1 about 0.6x to 0.7x); (2) the triad repair pass added Stories 1.12, 1.13, 1.14, 7.5, 7.6 and 11 new tasks in existing stories (24 tasks, 1,330k raw, +3,205k CU). The first cause is a correction of an undercount, not new work.
- **Overrun checkpoint is a decision gate, not a note** (pre-mortem failure mode 10): the trigger is actual spend above 1.25 x 1.63 x the running sum of Impl CU for the stories done so far (so the threshold is now anchored on the task-sum column above); the factor is derived, not assumed: total / impl = 31,294k / 19,218k = 1.628 (verification adds 0.93 x raw on top of impl CU 1.48 x raw, so 1 + 0.93/1.48). In addition, at the end of W5 and again at the end of W9 the coordinator publishes actual versus estimate per epic and a re-estimate of the remainder (recalibrated multipliers from Task 1.1g), and **the next wave does not start until the owner replies `continue` or names what to change** (Owner Checklist item 8). The gate is an owner decision point, not an invitation to cut; the safety spine (E1, E2, E8 including 8.8, and Story 9.2) is ordered before the ML epics' real-corpus batches so an overrun cannot leave the pipeline unsafe. At the end, report cost per file moved from Review to Eligible so the ML spend (E4+E5+E6 = 4,403k impl CU, about 7.2M with verification) can be judged against the cheap path (Story 5.6 fallback).
- **Critical path**: 13 agent waves (see Dependency Visualization). Parallel fan-out is widest in W5 (10 stories; W6 has 8); shared-file serialization points are named in the Dependency Visualization intro, and no two stories in a wave edit the same file.
- **Wall-clock blockers (the real calendar)**:
  1. Tyler: birth dates and death dates for family members (blocks 4.5 owner step, 5.4 real run).
  2. Tyler: cluster labeling and merges in the terminal/contact sheets (4.5, 4.6).
  3. Tyler: trusted-album/anchor list (5.2).
  4. Tyler: create own Google Cloud OAuth client (9.1); decide on unofficial strategy (9.7) and cloud plugin (6.4).
  5. Drive `/run/media/tstapler/EE5B-3D9B` mounted for index, spikes, thumbnails, writes.
  6. ML batch compute on the real corpus: faces and embeddings overnight (duration depends on the 4.1 spike; research estimates 1.5-5 h, INFERRED).
  7. Google daily request quota resets between re-upload batches (9.6).
  8. Google Takeout export generation (9.4).
  9. Tyler's manual web-UI "Edit date & time" / trash steps (9.5, 9.6).
  10. Human review latency for the review list (7.2).
  11. Local compute runs on the real drive (not agent time): the 200-image CPU spike (4.1), the placeholder scan over ~17k files (1.9), the hash-stability spike (2.2a), the first `index` over 17,145 files (2.4), the faces/embeddings overnight batches (4.3, 6.2), OCR engine comparison (3.5), the Google Photos capability spike (9.1), and the exFAT-safe workdir apply (8.4).
  12. Tyler: Pre-implementation Owner Checklist item 1 (stop the running legacy uploader, `ps` evidence; precedes Story 1.1).
  13. Tyler: second disk and the time to copy and checksum the 54G drive (Story 8.8, gates 8.4 and 8.7); a throwaway USB stick for the exFAT yank spike (Task 1.10c).
  14. Tyler: label the 50-file-per-class placeholder precision sample (Story 1.9), supply the trusted-album list and date a 200-file slice of the undated album (Story 5.6), and decide where planning artifacts live (Owner Checklist items 5 and 6).
  15. Tyler: cost decision gates after W5 and W9 (Owner Checklist item 8), and the labeling pass on real clusters after the sheets exist (Story 7.3).
  16. Tyler: unmount the family drive and supply root (sudo) for `fsck.exfat -n` before the first real apply of Story 8.4 and at each fsck boundary (Story 8.8, Owner Checklist item 11).

## Resumability and ordering notes

- Safety first: the destructive legacy writer is locked in W2 (Story 1.11) and the placeholder detector (1.9) and `recover` (1.10) land in W3, before any story consumes EXIF dates or `index` runs. Spikes early: 4.1 CPU timing and 9.1 Google Photos capabilities in W2 (owner OAuth step may delay 9.1; only 9.3 and later depend on its result), 9.8 gpmc read-only evaluation in W3 (serialized after 9.1 because both edit ADR-008). Riskiest stories early: 2.2 (ContentKey stability), 8.3/8.4 (write safety).
- Ship Layer A guards and the review flow before Layer B scoring is trusted (architecture.md risk 3): until calibration exists, plugin weights are capped, so ambiguous files go to review rather than being guessed.
- Every story ends with its test command output in the PR description; `make ready` must pass before merge.
