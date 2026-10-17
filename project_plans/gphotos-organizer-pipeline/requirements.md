# Requirements: gphotos-organizer-pipeline

**Date**: 2026-10-16
**Type**: feature addition
**Complexity**: 3 — system design (multiple epics; external integrations: Google Photos via rclone, optional cloud vision)

## Problem Statement
`stapler-scripts/gphotos-organizer` (scanner → ai_enrich → metadata → uploader, CLI in `cli.py`) dates photos only from folder names, filename patterns, and a placeholder `YYYY:01:01 12:00:00` fallback. Scanned prints from the 1960s–2000s have no EXIF, so photos with no usable folder date (e.g. `2021 random photos`, 9,161 files) or a wrong date land on the Google Photos timeline as "today" or in the wrong decade (old photos of grandparents among present-day photos). Analysis steps (face clustering, age estimation, era-by-appearance, date inference, upload audit) do not exist, and the pipeline is not pluggable: adding one means editing the monolithic CLI.

## Baseline
- Dates come from folder name / filename heuristics (`scanner.py`, `metadata.py`); everything else gets a placeholder date. `metadata_status` stays `pending` for all 628 albums in `album_mapping.json` even where EXIF was written.
- **Legacy-placeholder population (measured 2026-10-16, added by the repair pass)**: `exiftool` over the drive's jpg/jpeg/png found 15,943 dated images, of which 9,460 are dated January 1 and 5,926 are not Jan 1 but carry a `12:MM:SS` time (3,162 of those exactly `12:00:SS`, the legacy 5-second-offset signature). The legacy `fix-metadata --apply` evidently wrote fabricated dates at scale (with `-overwrite_original` and no journal), so existing EXIF dates cannot be trusted as anchors without classification (plan Stories 1.9, 8.7).
- Upload via `rclone copy` per album; `upload_manifest.json` records 604/628 albums (7,757 of 17,145 files) — measured 2026-10-16.
- Google Photos API cannot edit the date of an existing item (UNVERIFIED — research must confirm), so already-uploaded misdated photos have no automated fix.
- Quota (HTTP 429) handling was added 2026-10-16 (`uploader.py`: `QuotaExceeded`, wait until 00:05 Pacific); not yet exercised against a real quota hit.

## Users / Consumers
Tyler (sole operator, CLI). Output consumed by Google Photos timeline, and the review list Tyler reads to confirm low-confidence dates.

## Success Metrics
(Rewritten by the 2026-10-16 triad repair pass: Metric 1 now has a numeric bound, Metric 2 is baseline-first, the old Metric 5 duplicated Metric 1's measurement and is folded into it, and two new metrics cover review burden and remediation of already-uploaded items.)
1. **No mis-dated photos on the timeline.** For each processed file, its bound B is the `latest` date of its decision interval (Eligible, Anchor or UserOverride), else of its folder-year or filename interval, else undefined. A **bounded violation** is a matched remote item on an `observable` album whose remote date is later than B + 1 year, or that is dated in the upload window or like a legacy placeholder (Jan 1, or `12:00:00 + 5k s`) while B is earlier than the window start. Target: bounded violations = 0 on every observable album. Files with no B are reported as `unbounded`, and albums the audit cannot see as `unobservable`; neither is ever reported clean. Measurable from the first `audit` (plan Story 9.9 prints `Metric 1: violations V (bounded), unbounded U, unobservable albums A`); the first run's V over the 604 already-uploaded albums is the baseline. **Upload-window wording (repair pass)**: the 604 already-uploaded albums (7,757 files) came from placeholder-carrying files, so their remote dates sit in the past, not in the upload window; the audit therefore also counts remote items dated like legacy placeholders and reports coverage per album. The audit's enumeration of uploaded items by remote date, which was the old Metric 5, is the measurement mechanism of this metric.
2. **Held-out accuracy, baseline first.** On held-out anchor photos (known date/age), median and p90 date error by decade, color/B&W and age band are reported per run. Targets are set after the baseline run, not before: the starting expectation (±2 years for children, ±8 for adults) is provisional and labeled so in the report until the owner confirms or changes the targets after the first held-out run (plan Story 5.5, after calibration 5.3), and the confirmed values live in `DATA/config.toml [targets]`. Anchors contaminated by legacy placeholders are excluded by Story 1.9's `Genuine` gate, whose precision gate depends on the owner's labeled sample.
3. Every inferred date carries a confidence + provenance (which plugins voted); only photos above a configurable threshold are written to EXIF, the rest go to a review list.
4. A new analysis step can be added as a plugin without editing `cli.py` core flow.
5. **Remediation of already-uploaded items.** Every item the audit flags ends as `fixed` (audit-clear after a `remediation done`), `waived` (accepted as a manual residual with a recorded reason, `remediation waive`) or `open`. Target: `open` = 0. The report prints fixed, waived and open counts and the waived share, so a manual-only outcome is visible instead of silently accepted. (Whether the API can edit dates at all is UNVERIFIED until plan Story 9.1; the metric holds either way.)
6. **Review burden.** Per run the report gives items needing hand review by source, items decided by action, and the auto-dated versus reviewed ratio (files dated without a human decision versus files whose date came from a human decision, group decisions counted per file). The baseline is the first `fuse` after the anchor census (plan Story 5.6); the targets (maximum open review items, minimum auto-dated share) are set by the owner after that baseline and are report-only until then.

## Size
XL (> 15M CU) — revised from "Large" after planning: plan.md estimates ~29.8M CU on a bottom-up task basis (INFERRED, recalibrate after first implementer run; the earlier ~20.3M used flat per-story figures). Informational; full scope by default.

**Wall-clock blockers**: Tyler's birth-date list for family members and labeling of face clusters (owner decision/input); Google Photos daily upload quota resets; Google Photos web-UI steps for deleting/redating already-uploaded items (owner action, if no API route exists); drive `/run/media/tstapler/EE5B-3D9B` must be mounted for runs.

## Constraints
- Privacy: local by default; a plugin may call a cloud vision/LLM API only when explicitly enabled per run (owner decision 2026-10-16).
- Linux (Manjaro), Python via `uv` with PEP 723 inline deps; no GPU assumed. **Deviation (ADR-004)**: two scripts, `cli.py` (light core) and `analyze_ml.py` (pinned Python 3.12, heavy ML dependencies), sharing one SQLite schema.
- The repo is public (`github.com/tstapler/dotfiles`): PR evidence, logs and reports carry counts and album ids only, never album titles or person names; planning artifacts are not committed with real names until the owner decides where they live.
- Idempotent and resumable (existing manifest pattern); never modify source files without a backup/dry-run default (existing `--apply` convention).
- Do not upload `2021 random photos` until its dates are resolved.

## Non-functional Requirements
- **Performance SLO**: ~17k images processed in overnight batch on CPU; results cached per file hash so reruns are incremental.
- **Scalability**: tens of thousands of images, single machine.
- **Security classification**: confidential (private family photos, face embeddings are biometric-adjacent).
- **Data residency**: face embeddings and caches stay on local disk; not synced via dotfiles git.

## Scope
### In Scope
1. Survey of existing tools/libraries/services (face detection+embedding+clustering, age estimation, era/appearance classification, photo-dating, Google Photos API/rclone limits, existing plugin frameworks) — build vs adopt decisions.
2. Plugin architecture for analysis stages (common interface, registry/discovery, per-file result cache, confidence-weighted fusion).
3. Plugins: face cluster + identity labeling; age estimation; anchor calibration against known-date photos; era-by-appearance classifier (optional cloud variant); date inference/fusion with sanity guards (birth date bounds, folder-year bounds).
4. Review flow for low-confidence dates; EXIF write for high-confidence. Every real write is preceded by a verified full-drive backup on a different medium (the drive is 58G with 4.0G free), a canary and a filesystem check (plan Story 8.8).
5. Upload audit and remediation path for already-uploaded misdated items (detect; automate what the API allows, document/assist the rest).
6. Make `metadata_status`/`upload_status` truthful; tests following the repo's plain-function style where applicable.
7. Detect and quarantine legacy placeholder dates already written to EXIF (five-signal classifier with a measured precision gate, optional journaled revert), and refuse to upload any album that is not proven placeholder-free until the decision-based gate exists (plan Stories 1.6, 1.9, 8.7).
8. A command-line structure that lets stories add commands without editing `cli.py`, with unambiguous top-level command names and a disposition for the three legacy commands whose names collide (`review`, `report`, `status`; plan Story 1.11).

### Out of Scope
- Replacing Google Photos' own face grouping; hosting a photo web UI; tagging people inside Google Photos (not possible via API).
- Uploading `2021 random photos` before dates are resolved.
- Non-photo media workflows beyond existing video handling.

## Rabbit Holes
- Age estimators are biased on faded/scanned prints and on adults; accuracy may be too low to date adults — fusion must degrade gracefully, not guess.
- Face clustering across 50 years of aging for the same person (embedding drift); may need per-era sub-clusters and manual merge.
- Re-upload of fixed files may duplicate or be deduped by Google; deleting wrong copies is web-UI only (unverified).
- Era-by-appearance (CLIP zero-shot) overlaps 1990–2005; useful only as tiebreaker.
- Plugin framework over-engineering — keep to what 3–5 plugins need.

## Alternatives Considered
- Adopt an existing photo manager (Immich, PhotoPrism, digiKam) for face clustering and import its labels vs. build on InsightFace/dlib directly.
- Cloud vision LLM for era/age/who-is-this on a sampled/uncertain subset.
- Manual "Edit date & time" in Google Photos web UI for small batches.
- Trash + re-upload with corrected EXIF for large batches.

## Feasibility Risks
- Google Photos API read/delete/date-edit limits may make remediation partly manual.
- No GPU: CPU inference time for ~17k images (research must estimate).
- Ground-truth anchors may be too sparse per person/decade to calibrate.

## Observability Requirements
Per-run report: counts per plugin, confidence histogram, anchor error stats by decade, files flagged, files written, quota events; structured logs via loguru (existing); results/cache stored in a local sqlite (**deviation, ADR-002**: under `~/.local/share/gphotos-organizer/`, outside the dotfiles tree, mode 600/700, rather than beside the manifest, because face embeddings are biometric-adjacent and the manifest lives in the git work tree).

## Risk Control
Dry-run default; EXIF writes preceded by a recorded original-value journal (or exiftool `_original` backup) so every write is reversible; per-plugin enable flags; cloud plugins off unless `--allow-cloud`; confidence threshold gates all writes; upload only after audit passes. The legacy background upload loop is stopped (not merely gated) until the new gate exists, and the audit must have positive observability of an album's old items before it can clear a re-upload.

## Open Questions
- What tooling already exists for each stage, and how accurate is it on scanned prints? (research)
- Can the Google Photos Library API or rclone read per-item dates, move/remove items, or edit dates? (research)
- Best plugin mechanism for a uv-script CLI: entry points, directory discovery, or simple registry? (research)
- Which family members have known birth dates, and which albums give trustworthy anchors? (owner)
- Should the 137 flagged-for-review albums feed the same review list? (owner; recounted 2026-10-16: `album_mapping.json` stores `flagged_albums_count: 138` but 137 albums have `needs_review=True`; "132" in earlier drafts is historical)
