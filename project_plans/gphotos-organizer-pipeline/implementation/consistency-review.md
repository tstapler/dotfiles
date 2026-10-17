# Cross-artifact consistency review: gphotos-organizer-pipeline

Date: 2026-10-16 · Phase 4 (validate) · Inputs read in full: `requirements.md`, `implementation/plan.md` (1,535 lines), `design/ux.md`, `decisions/ADR-001..011`.
Severity per the SDD prompt: BLOCKER = contradiction or coverage gap; CONCERN = scope drift or terminology; NITPICK = UX alignment. Two findings are rated above their default class and say why.

**Totals: 2 BLOCKER, 8 CONCERN, 9 NITPICK.**

## Numbers that were rechecked and hold (VERIFIED by command, 2026-10-16)

| Claim | Check | Result |
|---|---|---|
| plan header: 10 epics, 65 stories, 157 tasks | `grep -c '^### Epic'`, `'^#### Story'`, `'^##### Task'` | 10 / 65 / 157 |
| 13 waves; every story in exactly one wave | script over the `- W<n>:` lines | 65 ids, 65 unique, none missing or extra; W5 and W6 have 9 stories each, as claimed |
| Effort table: 7,665k raw, 11,346k impl CU, ~18.5M total | script over the 65 table rows | 65 rows, 7,665k, 11,346k; 0.93 x 7,665k + 11,346k = 18,474k; requirements "~18.5M CU / XL" agrees |
| Critical-path chains (a) 12 nodes, (b) 13 nodes | counted from plan text | holds |
| Story/wave dependency order | every listed dependency sits in an earlier wave | no violations found |
| 628 albums, 604 completed, 17,145 media files, 17,255 total | `album_mapping.json`, `upload_manifest.json` | 628 / 604 / 17,145 / 17,255 |
| 7,757 files in the 604 uploaded albums | sum of images+videos over completed album ids | 7,757 |
| `2021 random photos` = 9,161 files | `file_stats`: 9,163 total minus 2 non-media | 9,161 media |
| 604/628 metadata_status all `pending` | Counter over albums | 628 `pending` |
| Measured placeholder figures 9,460 / 5,926 / 3,162 / 15,943 | same values in requirements-derived ADR-007, plan header, glossary, Story 1.9 | identical everywhere (not re-measured: drive access out of scope; remains the coordinator's measurement) |
| ux sample arithmetic (172 = 160+9+3; 1,214 = 200+1,014 = 1,180+21+13 = 1,201+9+4; 124 = 83+41; 5,210 = 2,100+3,110; 7,757 = 7,690+67) | by hand | consistent |

## BLOCKER

### B1. Upload gate and plan writer disagree about what an `Anchor` or `UserOverride` file needs on disk (contradiction; plan.md vs plan.md/ADR-007)
- Glossary `Anchor`: "camera EXIF, dated filename, owner-pinned album, UserOverride" (plan.md:48). Story 3.4 AC: "a file with anchor status ... `plan` emits no write" (plan.md:704). Story 8.4 AC covers only `Eligible` writes and `Anchor (real EXIF)` skips; `UserOverride` is not mentioned (plan.md:1130-1131). Story 9.2 gate and glossary `UploadGate`: album uploads when every file has `status in {Anchor, UserOverride}` or `WriteState == Verified` (plan.md:62, 1236).
- Effect: a file anchored by its filename (`IMG_20150102`), by an owner-pinned album, or by `review set` has no capture date in EXIF, is never planned for a write, and passes the gate without a `Verified` write. It uploads undated and lands on the upload date, which is the defect the project exists to remove (Success Metric 1). ADR-007 says nothing that closes this.
- Resolution: state in 8.4 that `plan` writes for every `Anchor`/`UserOverride` decision whose on-disk Genuine EXIF date differs from the decision, and narrow the gate to "Anchor backed by a Genuine on-disk date, or `WriteState == Verified`" (update glossary, 3.4, 8.4, 9.2 together).

### B2. Command names: auto-discovery contract cannot produce the ux.md command set, and three names collide with existing commands (contradiction; ux.md vs plan Story 1.11 and Stories 5.5, 7.2, 10.1, 10.3; rated BLOCKER because UX-29/UX-05 depend on exact command names)
- ux.md uses flat top-level commands (`analyze`, `index`, `fuse`, `plan`, `undo`, `recover`, `audit`, `status`, `report`) and groups (`review ...`, `people ...`). Story 1.11 AC defines discovery as "a Typer `app` in `G/cli_<x>.py`; `toy` is listed ... `cli.py toy ...`" (plan.md:478), i.e. one group per module. The plan never says how single-command modules (`cli_stages`: index/analyze/fuse; `cli_write`: plan/fix-metadata/undo/recover; `cli_audit`; `cli_status`) become top-level names, and `review` is split across three modules (`cli_review_cluster`, `cli_review_items`, `cli_review_io`) that would each register a group of the same name.
- Existing commands in `cli.py` already own `review` (`review_cmd`, line 155, "grandfathered" in 1.11), `report` (`report_cmd`, line 278) and `status` (`status_cmd`, line 452). The plan adds a `review` group (7.2), `report run` / `report accuracy` (10.1, 5.5; ux.md says plain `report`) and a new `status` (10.3, `cli_status.py`). No story removes or migrates the old commands (10.5c removes only `infer_cmd`); Typer/Click would silently shadow one registration.
- Resolution: add to Story 1.11 a naming rule (module may export `app` for a group or a `commands` list registered top-level) and a disposition for `review`, `report`, `status` (replace in place, or fold the old behavior into the new one); align ux.md `report` with `report run|accuracy`.

## CONCERN

### C1. Safety-critical UX criteria have no plan story (UX-11, S6) — rated CONCERN rather than NITPICK because UX-11 is a write-safety control
`fix-metadata --apply --plan <id>`, the typed-plan-id confirmation (UX-11), `--yes` for non-TTY, the 4-step preflight and the progress/ETA/Ctrl-C summary (S6, UX-40) appear in no Story 8.4 acceptance criterion (`grep` for "Type the plan", `--yes`, `--plan ` finds only unrelated hits; plan.md:1127-1148). Resolution: add one AC to 8.4 covering plan-id confirmation, `--plan`, `--yes`, and preflight order (plan fresh, drive mounted, exiftool present, workdir clean).

### C2. requirements.md is stale relative to the plan (scope drift in the other direction)
- Not in requirements: the legacy-placeholder population (9,460 Jan-1; 5,926 `12:MM:SS`; 3,162 strict) that drives Stories 1.9, 1.10, 1.11, 3.4, 8.7, 9.9, and the "locked legacy writer". Stories 1.9, 1.10 and 1.11 have no "Requirement trace" line (8.7, 3.5, 4.7, 6.1, 7.3, 7.4, 9.4, 9.7, 9.8 do).
- Success Metric 1 is defined by "dated within the upload window"; plan 9.3/9.9 shows that misses the 604 already-uploaded albums (their remote dates are in the past). Metric text should add the legacy-placeholder remote check.
- Requirements Observability says cache "beside the manifest"; plan and ADR-002 deliberately deviate (recorded in plan Observability Plan and ADR-002 Consequences, but requirements.md is not amended). Constraint "PEP 723 inline deps in cli.py" is now two scripts (ADR-004).
- Resolution: amend requirements.md (Baseline, In Scope item 7 "detect and quarantine legacy placeholder dates", Metric 1, Observability, Constraints) or add a one-line trace for 1.9-1.11.

### C3. Flagged-album count differs in four places
requirements.md and ADR-009 say 132; plan.md says 138 (header, glossary, Epic 7) with "137 needs_review" noted; `album_mapping.json` records `flagged_albums_count: 138` but only 137 albums have `needs_review=true` and 137 have `flag_severity != none` (VERIFIED by script, 2026-10-16). ux.md uses 172 review rows as an illustrative total (not wrong, but not tied to 137 + file items). Resolution: pick 137 (recounted) in plan, mark 132/138 as historical, and update ADR-009 and requirements.

### C4. Review `source` vocabulary differs
ADR-009 and ux.md S3 list `file | album | audit`; plan Story 7.2 and glossary `ReviewItem` list five (`album, file, audit, year-precision, placeholder`); ux.md names `year-precision` only in its closing caveat and never `placeholder`. Resolution: update ADR-009 and ux.md S3 `--source` values to the five-value set.

### C5. Store inventory is inconsistent between ADR-002, glossary, Migration Plan and later stories
- ADR-002 puts `audit_runs` in `pipeline.db`; plan glossary `DerivedStore`, the Migration Plan table and Story 2.2's migration list omit it (the migration `s0909_audit_runs` exists in the Migration Plan text and Story 9.9).
- Tables implied by Stories 5.2 (`anchors`), 5.3 (calibration curves), 6.1 (`dup_groups`), 6.2 (embeddings) appear in no ADR-002 list and no migration name; 4.4/5.2 list only `labels, constraints, anchor_pins` and `clusters`.
- ADR-002 and plan single-writer rule say the ML script writes only evidence/faces/clusters rows, but Story 6.3 writes `holdout_mae` rows into `run_metrics` (from the Ml runtime) and calibration (5.3, `ml_plugins/calibrate.py`) persists curves.
- Resolution: add the missing tables and migrations to ADR-002 and the Migration Plan, and widen the ML-script write list.

### C6. Cluster labeling is scheduled before its sheet exists; date-group sheet has no command
Story 4.5 (W8, owner labeling step; AC says "cluster C12 shown in the contact sheet") precedes Story 7.3 (W9), which adds `review sheet --cluster`. ux.md S2 and UX-02 make the sheet the labeling aid, and S3 references a `dategroup-*.html` sheet, but Story 7.3's ACs and file list cover only `review sheet --cluster`; the date-group template exists only as Task 7.3b with no command or AC. Resolution: move the owner labeling step after 7.3 (or state terminal-only labeling in 4.5), and add a `review sheet --album|--group` AC to 7.3.

### C7. `metadata_status` vocabulary: `written` vs derived status
Story 1.7 maps legacy `fixed` to `written`; Story 8.6 derives album status as `verified | mismatch | pending` and removes hand-set values, so `written` can survive only as a migrated legacy value, and `reverted`/`not_written` albums have no status. `models.py:37` also documents legacy values `verified, pending_fix, fixed, skipped` that the 1.7 loader mapping does not address (the file currently holds only `pending`). Resolution: list the full derived status set in 8.6 and the legacy mapping for every old value in 1.7.

### C8. ux.md S8 audit summary omits the legacy-placeholder counter
Stories 9.3/9.9 print `Dated like legacy placeholders: M` and `Unmatched` lines because all 604 uploaded albums came from placeholder-carrying files (plan.md:1259, 1291). ux.md S8 shows only "Suspicious (dated in upload window): 83 / Outside decision interval: 41", and its `Added 124 items` arithmetic (83 + 41) ignores both overlap and the missing counter. Resolution: add the third counter to the S8 sample and note that items can fall in more than one category.

## NITPICK

- N1. Guard names: ux.md S3 shows `Guards: BirthBounds ok`; ADR-003, glossary and Story 2.6 use `BirthDeathBounds`. Use one name.
- N2. Strategy names: ux.md S8 says `webui, trash-reupload (and toolkit ...)`; plan Story 9.7 uses `unofficial-gptk`; ADR-008 names it `UnofficialToolkit`. ux.md S8 "Strategy lacks capability ... Falling back to: webui" has no AC in 9.6.
- N3. Deny-list text: ux.md S7 `Blocked (deny-listed until dates are resolved)` vs Story 1.6 `Blocked: '2021 random photos' is on the deny list. Resolve dates, then run: gphotos-organizer deny release ...`. `deny list|release`, `anchors build|pin-album|exclude`, `models check`, `report accuracy` have no ux.md surface.
- N4. ux.md S2 offers `review reject C12` and `review skip C12` for clusters; Task 4.5b implements only `accept|merge|split`. S2's empty-state text "analyze --plugins faces, then cluster" implies a `cluster` command; Story 4.4 makes clustering a Corpus-scope pass inside `analyze`. ux.md S3 `review list --skipped` has no AC in 7.2 (only `--forced`, `--source`, `--severity`).
- N5. UX criteria with no explicit task: UX-20 (test that lints every `fail()` call site for a hint), UX-24 (quota countdown and Ctrl-C exit 0 in Story 1.8, which tests retry only), UX-60 (`NO_COLOR`, non-TTY plain output), S10 preflight line, S9 "needs only the DB" (Story 10.3 also reads `state.db` for `WriteState`; one DB is named in ux.md).
- N6. Glossary `YearPrecisionPolicy` lists "Year / Range / Decade; Month included" while Story 1.5 also gates `Unknown`; glossary `ReviewDecision.action` omits `merge`, `split`, `retract` and `kind=cluster_label` used by 4.5/7.1; glossary `UploadGate` omits the year-precision hold (present in 9.2); Story 2.6 names five guards but ACs cover four (`PhysicalPlausibility` has none).
- N7. Story 1.5's `--allow-placeholder` dry-run flag is "superseded" by `--allow-year-precision` in 8.4, but 8.4 has no AC removing it.
- N8. Requirements In Scope 1 (tool survey) has no plan story; it is satisfied by `research/*.md` and ADR-006/-010/-011, so this is informational, not a gap.
- N9. Story 1.9 cites "the earlier run's 1,654 at `12:xx`" to derive "about 7.8k" Jan-1 files at other times; this figure appears nowhere else and mixes two measurement runs (15,943 vs 16,044 files). Source it or drop the derived 7.8k.

## Coverage summary

- Requirements to stories: every Success Metric (1-5) and In Scope item 2-6 maps to at least one story (metric 1: 5.5, 9.3, 9.9; 2: 5.3, 5.5; 3: 2.7, 2.8, 8.4; 4: 2.3, 10.5; 5: 9.3, 9.9). Constraints and Risk Control items map to 1.1, 1.6, 2.3, 8.3-8.5, 9.2. No requirement is without a story (N8 aside).
- Stories without a written requirement (accepted drift, traced in plan): 3.5, 4.7, 6.1 dup groups, 7.3, 7.4, 9.4, 9.7, 9.8, 8.7 (all carry a trace line); 1.9, 1.10, 1.11 lack one (see C2).
- ADR to plan: every ADR lists plan stories that exist and reference it back; no ADR contradicts another. Terminology `LegacyPlaceholder` / `Suspect` / `Genuine`, the truth table, the year-precision rule (July 1 for Year, 15th for Month, midpoint year for Range/Decade), `UserOverride`, `DecisionStatus` vs `WriteState`, and `pipeline.db` (derived) vs `state.db` (source of truth) are used identically across glossary, Stories 1.5/1.9/8.4/8.6/8.7, ADR-002 and ADR-007, and ux.md (UX-62 vocabulary matches). The only ADR/plan drift is C5 (`audit_runs`) and the stale 132 in ADR-009 (C3).
