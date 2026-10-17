# UX design: gphotos-organizer-pipeline

Date: 2026-10-16 · Sole user: Tyler · Inputs: `requirements.md`, `research/ux.md`, `decisions/ADR-009-*.md`, `implementation/plan.md` (Stories 1.12, 1.13, 4.5, 7.1-7.6, 8.4, 8.5, 8.8, 9.2, 9.3, 9.5, 10.3).

Surfaces: terminal commands (typed into) and static offline HTML contact sheets under `DATA/` (no server, cannot write files; export `decisions.json`, merged by `review import`). Conventions that apply everywhere:

- **Error shape** (Story 1.1 `fail(msg, hint)`): what happened, why, exact next command, and whether anything changed. Non-zero exit, short panel, traceback only with `--verbose` or in the loguru log. Template: `<What failed>: <detail>. <Exact command to run>. Nothing was changed.`
- **Mutations are dry-run by default**; `--apply` commits (existing repo convention, `cli.py` `fix-metadata`/`upload`). Every dry-run ends with the exact `--apply` command.
- **Every interactive command prints a `Next:` line.** This is the exit path guarantee: no screen ends without a stated way forward or a stated "nothing to do".
- **Names stay out of logs**; terminal and HTML may show names.
- **No emoji in terminal or HTML headings**; state is conveyed by word + symbol, never color alone.
- **One confirmation-tier table, one reversal map, one vocabulary** apply to every command (S12 below); no command invents its own prompt or reuses a state word for another meaning.

## 1. Surface inventory

| # | Surface | Type | Treatment |
|---|---|---|---|
| S1 | `people add/list` | interactive terminal | full |
| S2 | Cluster labeling: `review sheet --cluster`, `review accept/merge/split` | terminal + HTML | full |
| S3 | Date review loop: `review list/next/accept/reject/set/skip` | interactive terminal | full |
| S4 | HTML contact sheet (cluster sheet, date-group sheet) | interactive HTML | full |
| S5 | `review import decisions.json` | interactive terminal | full |
| S6 | Plan/apply gate: `plan`, `fix-metadata --apply`, `undo` | interactive terminal | full |
| S7 | Upload gate and quota wait: `upload` | interactive terminal | full |
| S8 | Audit + remediation: `audit`, `audit --plan`, `remediation done` | terminal + generated md | full |
| S9 | `status` "where am I" screen | terminal output | full (single entry point) |
| S10 | Long-running stages: progress, Ctrl-C, preflight | terminal output | condensed |
| S11 | Run report (`report`), `DATA/remediation/*.md`, error/log output | non-interactive | condensed |
| S12 | Cross-cutting: confirmation tiers, reversal map, vocabulary, help panels, completion; plus review at scale (group decisions, placeholder sheets) inside S3/S4 | terminal + HTML | full |

Empty, loading, and error states are covered per flow below.

### 1a. Command names (single source: plan Story 1.11 naming rule)

Flat top-level commands: `scan`, `index`, `analyze`, `fuse`, `plan`, `fix-metadata`, `undo`, `recover`, `audit`, `status`, `census`, `upload`, `update-album`, `setup-rclone`. Groups (subcommands): `review` (`list`, `next`, `accept`, `reject`, `set`, `skip`, `undo-last`, `merge`, `split`, `sheet`, `import`, `confirm-genuine`, `confirm-placeholder`; `list` and `next` take `--state undecided|skipped|rejected|parked`), `people`, `placeholders` (`scan`, `list`, `confirm-genuine`, `sample`, `label`, `precision`, `summary`, `revert`), `deny`, `models`, `anchors`, `remediation` (`done`, `waive`), `backup` (`verify`, `check`, `fsck`, `canary`), `prewrite` (`snapshot`, `restore`, `purge`), `report` (bare = run report; `report accuracy`; `report albums`). Three older commands share names with the new ones: `review` (flagged-album list) becomes `review list --source album` with an alias for bare `review --severity ...`; `report` (album Markdown report) becomes `report albums` with an alias for bare `report --out ...` (both aliases print a deprecation notice on stderr, S12); `status` is replaced in place and keeps its five legacy rows in the header. `accept`, `reject` and `skip` are one verb set that dispatches on the typed item id (`F42` file, `A7` album, `Y77` year precision, `U310` audit, `P4021` placeholder, `C12` cluster, `C12/F3` face; the id scheme and its stability rules are in S3); what each verb means per source, and whether a reject is terminal or parks the item, is the table in S3. Command grouping in `--help`, aliases, completion and the `plan` / `fix-metadata` pairing are in S12.

## 2. Flows

### S1. People file (birth dates)

```
$ gphotos-organizer people add "Grandma Ruth" --born 1931-05-02 --died 2009-11-30
Added Grandma Ruth (born 1931-05-02, died 2009-11-30) -> DATA/people.toml
Next: gphotos-organizer people list | review sheet --cluster <id>
```

Flow: validate -> write `people.toml` (atomic) -> print row + Next. `people list` prints a table (name, born, died, labeled-cluster count); empty state: `No people yet. Add one: gphotos-organizer people add "NAME" --born YYYY-MM-DD`.
Exit: command returns; Ctrl-C before write leaves the file unchanged (atomic write).

| Error | Message | Exit path |
|---|---|---|
| Future birth date | `Birth date is in the future. Example: --born 1931-05-02` | rerun with a valid date |
| `--died` before `--born` | `Death date 1930-01-01 is before birth date 1931-05-02. Check both with: people list` | rerun / `people edit NAME` |
| Malformed date | `Could not read '31-05-1931'. Use YYYY-MM-DD. Example: --born 1931-05-02` | rerun |
| Duplicate name | `Grandma Ruth already exists (born 1931-05-02). To change: people edit "Grandma Ruth" --born ...` | edit or choose new name |
| Unwritable/corrupt `people.toml` | `Cannot parse DATA/people.toml line 4: <reason>. Fix the line, or restore DATA/people.toml.bak if you have used people edit. Nothing was changed.` | edit file |

### S2. Cluster labeling (terminal-first, sheet-assisted)

```
review sheet --clusters --open           -> writes DATA/review/sheets/index.html (all clusters, status, expected gain) and opens it
  Tyler clicks a cluster, scans faces (header: Prev | Index | Next | Next unlabeled)
review sheet --cluster C12 --open        -> same sheet, regenerated and opened directly
review accept C12 --name "Grandma Ruth" --run CR7   # label the whole cluster (every non-rejected member); --run is the cluster-run guard (rule g below)
review reject C12/F3                     # face F3 is NOT this person (cannot-link; leaves C12 at the next cluster pass)
review accept C12/F5                     # face F5 confirmed as this cluster's person (preferred exemplar)
review split C12 --faces F3,F9           # shorthand for reject C12/F3 + reject C12/F9 in one action
review merge C12 C40                     # same person, split by aging
review reject C12                        # not a person worth labeling (stranger, false detection)
review skip C12                          # decide later
```

Ids: a cluster is `C12`; a face inside it is `C12/F3` (`F3` is the face's position in C12 for the current `cluster_run_id`; the canonical `FaceId` is `ContentKey` + bbox and travels in the export). The sheet prints the full `C12/F3` on each card, and the no-JS fallback shows the exact terminal command.

Card buttons on a **cluster sheet** (cards are faces) are `Same person`, `Not this person` and `Unsure`; the word `Accept` is reserved for the cluster-level control so a face click never reads as labeling. Meaning of each control:

| Control | Level | Meaning | Recorded as (`decisions.jsonl` kind / action) | Carries |
|---|---|---|---|---|
| Face `Same person` (key `a`) | face | This face is the cluster's person (confirms membership; becomes a preferred exemplar for Story 4.6) | `face_member` / `accept` | `item=C12`, `face=F5`, `face_id` |
| Face `Not this person` (key `r`) | face | This face is NOT the cluster's person (a cannot-link from this face to the rest of the cluster; it leaves C12 at the next cluster pass, equivalent to `review split C12 --faces F3`) | `face_member` / `reject` | `item=C12`, `face=F3`, `face_id` |
| Face `Unsure` (key `s`) | face | Cannot tell; neither confirms nor rejects; the face still receives the cluster label if the cluster is accepted | `face_member` / `skip` | same |
| Cluster `Accept as person...` | cluster | Label every member that is not face-rejected with the name in the Name field. The name is required, is chosen from a closed `<select>` built from `people.toml` (its last option, `Not listed: add with people add`, disables the button and shows the terminal command), and IS exported (`name`), not just displayed. When the faces shown are fewer than 25% of the members to be labeled (`TYPED_NAME_SHOWN_FRACTION = 0.25`, INFERRED, measured in Story 7.3), a native `<dialog>` asks the operator to type the chosen name before the entry is created (`Label 120 faces (24 shown) as Grandma Ruth? Type the name to confirm.`); a 60-face cluster with 24 shown (40%) does not ask, so the normal path stays one press of `Accept as person...` | `cluster_label` / `accept` | `item=C12`, `name` |
| Cluster `Reject cluster` | cluster | Not a person worth labeling; faces stay unknown; no labels are made | `cluster_label` / `reject` | `item=C12` |
| Cluster `Skip` | cluster | Decide later | `cluster_label` / `skip` | `item=C12` |

Rules that follow: (a) a face decision never labels anything by itself; labeling is only a cluster-level `accept`. (b) A cluster `accept` after face rejections labels the remaining members, including faces that were never looked at (the sheet shows 24 of N faces; the confirmation line says so, see "Show more" below). (c) Face rejections without a cluster `accept` are recorded and shown as queued intents on `review list --clusters`; the cluster stays Undecided. (d) The split and merge ids are all cluster-scoped (`C12/F3`), so `review split` never needs a bare face id.

Further rules (fold order, rejecting an accepted cluster, run guard):
- (e) **Fold order.** Labels are a fold of the log, not a one-time write. A cluster's labels are its members minus every face whose latest `face_member` decision is `reject`. A `face_member reject` that is later than the cluster `accept` (typically from page 2 of the sheet, which is a separate export, or from the terminal) appends the decision and removes that face's `labels` row in the same command (`Removed 1 label (C12/F3).`); a later `face_member accept` or a re-run of the cluster `accept` restores it; a reject made before the accept just excludes the face. Accept-then-reject and reject-then-accept therefore end in different, deterministic states.
- (f) **Rejecting an accepted cluster.** `review reject C12` on a cluster that is `Accepted` is a preview first (`C12 is Accepted as 'Grandma Ruth' (59 labels). Rejecting removes those 59 labels. Apply: review reject C12 --apply`) and is undone by `review undo-last`; on an Undecided or Skipped cluster it is immediate because there is nothing to remove.
- (g) **Run guard.** Cluster ids are numbered per cluster pass. Every sheet, every no-JS card command and `review list --clusters` print `Cluster run CR7`, and every terminal command that takes a `C` id accepts `--run CR7`. If the given run is not the current one the command refuses: `C12 was numbered by cluster run CR7 but the current run is CR9; ids were renumbered. List: review list --clusters. Nothing was changed.` Without `--run` the confirmation line echoes a signature (`C12: 60 faces, est. 1962-2004, top album A7, run CR9`) so a stale id is visible. Labels, face rejects and merge/split intents are stored by canonical `face_id`, so they survive renumbering; cluster-level `reject` and `skip` are valid for the run that recorded them, and a new cluster pass shows those clusters as Undecided again (`reset by cluster pass CR9` in the Queued column). **Status after renumbering is derived from the labels, never from the old cluster-level line:** a cluster whose non-rejected members all carry one name reads `Accepted: <name>` (this includes two accepted clusters that a recluster merged under the same name); some labeled and some not reads `Partly labeled: <name> (59 of 71)` and one `review accept` labels the rest; members carrying two different names read `Mixed names: <a> / <b>`, and `review accept` on it is refused with the merge-refused message in the error table; no labeled member reads Undecided.
- (h) **Log kinds.** `cluster_label` (`accept|reject|skip`), `face_member` (`accept|reject|skip`), and, terminal only (the sheet has no merge control, so exports never carry them), `cluster_link` with `action=merge` (`item=C12`, `peer=C40`). There is no `split` action: `review split C12 --faces F3,F9` appends one `face_member reject` per face under one `batch_id`, so one `review undo-last` retracts both.

Interaction:
- **Names resolve against `people.toml`** (case-insensitive, whitespace-normalized, aliases included). `review accept C12 --name "Grandma ruth"` prints `Using 'Grandma Ruth' (matched 'Grandma ruth').` An unknown name is refused: `No person 'Grandma Rut'. Did you mean 'Grandma Ruth'? Rerun with that name, or add her: people add "Grandma Rut" --born YYYY-MM-DD. Nothing was changed.` `--new-person` accepts an unknown name and creates a stub entry, with the warning `'Grandma Ruth' has no birth date; age-based dating will skip her. Add: people add ... --born YYYY-MM-DD`. This prevents one person fragmenting into several labels. The sheet Name field is a closed `<select>` of the `people.toml` names written at generation time (no free typing, so a typo cannot travel through the browser and fail later at import); the import dry-run applies the same check (S5).
- **Show more**: the sheet shows up to 24 faces (outliers first, then sampled across estimated age). `review sheet --cluster C12 --page 2` (or the sheet's `Show next 24 (of 60)` link) writes the next 24 not yet shown (`cluster-C12-p2.html`); `--all` writes every face, paged at 100. `review accept C12 --name ...` prints `Labeling 60 faces (you viewed 24 in the sheet; 2 rejected).` The sheet counter counts only the faces shown (`12 of 24 shown faces judged`), never the cluster size, and the page says the normal path: mark the outliers `Not this person`, then press `Accept as person...` once.
- **Cluster index and navigation**: `review sheet --clusters` writes `index.html` with one row per cluster (id, face count, estimated years, status word, expected gain, link), sorted by expected gain (`review list --clusters` prints the same columns plus the top-3 album ids by count, the `Queued` column and the cluster run); every cluster sheet header carries `Prev | Index | Next | Next unlabeled`. `review sheet --clusters --all` generates all sheets (thumbnails only for each sheet's first page) with a progress line `Sheets 40/212`; an interrupted `--all` is resumable: rerunning it keeps sheets whose generation is unchanged and prints `Sheets 40/212 kept, 172 to write`. Every `review sheet` form takes `--open` (xdg-open on Linux, open on macOS) and always prints the `file://` URL (a terminal hyperlink on a TTY, the plain path otherwise); if no opener works (no `xdg-open`, headless) it prints `Could not open a browser (xdg-open not found). Open this file: file://...` and still exits 0.
- **Merge and split feedback**: `review merge C12 C40` (one `cluster_link` merge line) prints `Recorded must-link C12+C40 (3 queued intents). Effective at the next cluster pass: gphotos-organizer analyze --plugins faces (re-clusters cached faces only; last cluster pass took 94 s; detection is not rerun). Until then C12 and C40 stay separate.` `review list --clusters` has a `Queued` column (`merge->C40`, `split 2 faces`), so interim state is visible. Without a previous pass the estimate reads `no estimate yet`.
- Every action prints one confirmation line plus `Next:`. Unlabeled-cluster order: largest expected gain first, outliers shown first in the sheet (research/ux.md section 1).
- Exit: each command is atomic (one appended line); Ctrl-C between commands loses nothing. Undo a label: `review undo-last` (the last decision, see S3), re-run `review accept C12 --name ...` (latest wins) or `review reject C12` (preview first when the cluster is Accepted, rule f).

| Error / edge | Message | Exit path |
|---|---|---|
| Unknown cluster id | `No cluster 'C999'. Valid ids: C1-C212 (212 clusters). List: review list --clusters` | list |
| Unknown face id | `Faces F99 are not in C12 (members: F1-F60). Nothing was changed.` | fix ids |
| Unknown or misspelled name | see "Names resolve" above | rerun / `--new-person` |
| No clusters yet (empty) | `No face clusters yet. Run: gphotos-organizer analyze --plugins faces (clustering runs as the last pass of analyze)` | run stage |
| Faces plugin disabled/model missing | `Plugin 'faces' is disabled (model download failed). Retry: gphotos-organizer models fetch faces` | models fetch |
| Sheet thumbs need the drive, unmounted | `Source drive not mounted: /run/media/tstapler/EE5B-3D9B. Thumbnails already cached are used; 14 of 24 missing. Mount the drive and rerun the same command.` Sheet still generated for cached ones; missing show alt-text tiles | mount and rerun |
| Merge would join a labeled cluster to a differently labeled one | `C12 is 'Grandma Ruth', C40 is 'Aunt May'. Merge refused. Relabel one first: review accept C40 --name "Grandma Ruth"` | relabel |
| Cluster accept with every face rejected | `All 60 faces of C12 are rejected; nothing to label. Use: review reject C12` | reject |
| Stale cluster id (terminal) | `C12 was numbered by cluster run CR7 but the current run is CR9; ids were renumbered. List: review list --clusters. Nothing was changed.` | list |
| Face reject after the cluster was accepted | `Removed 1 label (C12/F3). Cluster C12 now labels 59 faces.` | n/a |

### S3. Date review loop (terminal)

Item screen from `review next` (the `Next:` line is chosen by the item's source, see the verb table below):

```
Review file 11 of 172  severity: high          (counts are within this source; others: review list)
  Item:      F42                          (typed id; stable across re-fuse)
  File:      1985 Beach/IMG_0042.jpg      Album: 1985 Beach (A7)
  Candidate: 1974-1978 (point 1976-06)    Confidence: 0.58 (threshold 0.80)
  Voters:    folder_year 1985 (conflict, dropped by FolderYearBounds)
             age_estimate Grandma Ruth ~45 +/-8 -> 1976
             era_clip tiebreak 1970s
  Guards:    BirthDeathBounds ok
  Sheet:     DATA/review/sheets/dategroup-1985-Beach.html   (open it: review next --open)
Next: gphotos-organizer review accept F42 | review set F42 --date YYYY[-MM[-DD]] | review skip F42 | review reject F42
Immediate (tier T1, one item; undo: review undo-last): accept, reject, skip, set. Preview first (T1a, --apply): set A7 --offset, confirm-genuine, confirm-placeholder, import, reject of an Accepted cluster.
```

**Item ids (one scheme, stable).** Every review item has a typed id: a one-letter prefix per source plus an integer alias. `F42` is a `file` item, `A7` an `album`, `Y77` a `year_precision` item, `U310` an `audit` item, `P4021` a `placeholder` item (a `Suspect` file), `C12` a cluster and `C12/F3` a face (run-scoped, S2). The prefix selects the source and its handler, so `review accept F42` (take the date) and `review confirm-placeholder P42` (agree it is a placeholder) never collide even when one file is both a `file` and a `placeholder` item. A bare number is refused and lists the prefixes that exist for it (`'42' needs a prefix: F42 (file), P42 (placeholder). Nothing was changed.`); `--source` is therefore never needed to dispatch. The integer is an alias allocated once per stable key and never reused or renumbered; the stable key is the album id (`A`), the file's `ContentKey` (`F`, `Y`, `P`), `ContentKey` plus remote item id (`U`), and for clusters and faces the run number plus the canonical `face_id` (S2). Aliases live in the append-only source-of-truth file `DATA/review/ids.jsonl` (one `{alias, item_key}` line per allocation, written with the same append primitive as `decisions.jsonl`, ADR-002) and can be rebuilt from `decisions.jsonl` alone because every decision line carries both `item` (the alias) and `item_key` (the stable key); allocation resumes above the highest alias seen. **The fold identifies a decision by `(kind, item_key)`; the alias is only for typing and display**, so a re-fuse never moves a decision to another item: an item that fuse resolves disappears from the list (`Item F42 no longer needs review (re-analysis resolved it)`), and if it needs review again it returns under the same id with its earlier decisions visible. A log line whose alias and key disagree with `review_ids` is ignored with `Ignored 1 line: id F42 now names a different file`. Exports carry both fields and `review import` resolves by `item_key`. `--album` accepts the album id or its `A` alias.

**What accept / reject / skip / set mean per kind, and whether reject is terminal or parks the item** (one verb set; the `Next:` line prints only the verbs of the item's kind, with the explicit alias where the plain word is ambiguous). The `review list` Source column holds exactly the five sources `album`, `file`, `audit`, `year_precision`, `placeholder`; `cluster` and `face` rows are kinds reached through the same verbs by the handler registry (`review list --clusters`), not further sources.

| Item kind (id) | `accept` | `reject` | reject is | `skip` | `set --date` |
|---|---|---|---|---|---|
| `file` (F42) | take the printed candidate (point or interval) | candidate is wrong; item stays unresolved, parked | hold | decide later | override; becomes a hard anchor (`UserOverride`) |
| `album` (A7) | accept the album's candidate date for all its files | wrong; album stays parked (not uploaded) | hold | decide later | album date or `--offset` (preview/apply) |
| `cluster` (C12) | label the cluster as `--name N` | not a person worth labeling; shown as `Rejected (not a person)` | terminal for this cluster run | decide later | n/a |
| `face` (C12/F3) | this face is that person (sheet button `Same person`) | this face is not that person (cannot-link; sheet button `Not this person`); shown as `Rejected (not this person)` | terminal | cannot tell (sheet button `Unsure`) | n/a |
| `year_precision` (Y77) | release this file for `YearPrecisionPolicy` rule 3 (a marked mid-period noon date is written) | keep keyword-only; the file stays parked, un-uploaded | hold | decide later | give a more precise date; Day precision becomes an anchor |
| `audit` (U310) | the target date is right; item goes to the remediation worklist | the remote date is actually right (false positive); shown as `Rejected (false positive)`, item cleared and recorded | terminal | decide later | give the true target date |
| `placeholder` (P4021, a Suspect file) | agree it is a placeholder: owner record `LegacyPlaceholder` (alias `review confirm-placeholder P4021`); shown as `Accepted (placeholder)`; Story 8.7 may revert it, `plan` re-dates it | it is genuine: owner record `Genuine`, anchor-eligible (alias `review confirm-genuine P4021`); shown as `Rejected (genuine)` | terminal | decide later | the true date; also records the old value as `LegacyPlaceholder` |

**One definition of terminal and parked.** A `skip`, and a `reject` on a kind whose reject is **hold**, leave the item *parked*: no longer Undecided, but it writes nothing, releases nothing and is served again by `review next --state parked`. A `reject` on a kind whose reject is **terminal** completes the item (a genuine photo, a cleared audit item, a cannot-link): nothing is parked, nothing is served again, and it never counts as a leftover. A **terminal decision** is the latest non-retracted log line for the item that is an `accept`, a `set`, or a `reject` on a terminal kind; `skip` and a hold-kind `reject` are not terminal. The fold, `review list|next --state`, the `All N items decided` line, `status` and its `Next:` order, the upload gate and the import conflict rule (S5) all read the same per-kind attribute (`SOURCE_VERBS[kind].reject_terminal`), so none of them can disagree. `--state rejected` lists every Rejected item (terminal ones are marked `cleared` and need no action); `--state parked` lists skipped plus hold-rejected items; `--state skipped` lists skipped only. Review-state words stay `Accepted/Rejected/Skipped/Undecided`; the parenthetical in the table is the word `review list`, `review next` and the sheet's state text print after it, so a photo Tyler certified shows `Rejected (genuine)`, not a bare `Rejected`. On `review list --source placeholder`, `review confirm-genuine` and `review confirm-placeholder` are printed in the `Next:` line, as on the item screen.

Actions:
- `accept <id>`: (a file or album id) take the candidate as written (must name the point or interval accepted; prints it). `reject`, `skip` per the table.
- `set F42 --date 1976-06`: override, becomes a hard anchor (UserOverride, confidence 1.0). Echoes `Recorded 1976-06 (month precision) for IMG_0042.jpg as a hard anchor.`
- `set A7 --offset +10y` / `--date` on an album: applies to the group; dry-run preview prints the file count and first 5 before/after rows, `--apply` required for the bulk form (research/ux.md digiKam offset pattern).
- `review list [--source album|file|audit|year_precision|placeholder] [--album ID] [--severity S] [--order severity|gain] [--by album] [--json] [--state undecided|skipped|rejected|parked] [--forced] [--clusters]` (`--skipped` is kept as an alias of `--state skipped`; `--forced` lists overrides made with `--force-guard`): table with a source column, sorted by severity then confidence (the `placeholder` source sorts by expected gain, files resolved per decision, by default). `--by album` collapses to one row per album with count and signals. `review next` takes the same `--source/--album/--severity/--order` filters so a run of placeholder items cannot bury date items (and the reverse); `--json` behaves identically on `review list|next`, `people list`, `placeholders list|summary`. Empty: `Nothing to review. Next: gphotos-organizer plan`.
- `review next --open`: opens the item's sheet at the item's card (`#item-F42`); the `Sheet:` line is also printed as a terminal hyperlink. This removes the find-the-file-then-return step.
- **Progress is per source.** `review next` takes the same filters and counts within the filtered source (`Review file 11 of 172`). Unfiltered `review next` never serves per-file `placeholder` items: it serves the highest-severity item of album, file, audit and year_precision, and when only placeholder items remain it prints `Only placeholder items remain: 14,812 files in 31 albums. Next: gphotos-organizer review list --source placeholder --by album` (the group path below) followed by one summary line for the rest (`The 172 non-placeholder items are decided (160 accepted/set, 6 rejected and cleared, 3 rejected and parked, 3 skipped).`). **Precedence for unfiltered `review next`:** (a) an undecided album, file, audit or year_precision item is served; (b) otherwise, if placeholder items are undecided, the `Only placeholder items remain` line is printed (with the summary line above), never the `All N decided` line; (c) otherwise the `All N items decided` line below. `--source placeholder` still reaches the per-file items.
- **Leftovers resurface.** Parked items (skipped, and rejected on a hold kind) can be served again: `review next --state parked` (or `--state skipped` / `--state rejected`, same filters). When nothing is undecided in any source, `review next` prints `All 172 items decided (160 accepted/set, 6 rejected and cleared, 3 rejected and parked, 3 skipped). 6 items stay parked (not written, not uploaded). Next: gphotos-organizer plan   (or revisit them: gphotos-organizer review next --state parked)`; with nothing parked the line ends `Next: gphotos-organizer plan`. `plan` is always the primary `Next:` once nothing is undecided, so following only `Next:` lines cannot loop through parked items; `status` follows the same rule (S9).
- Resume: `review next` always shows the first undecided; decisions persisted per line, so Ctrl-C loses at most the in-flight command.
- Every decision line is journaled. `review undo-last` retracts the most recent non-retracted decision line, or the whole batch it belongs to (one group decision, one import, one `review split`), regardless of which shell or day wrote it; the word "session" is not used. It prints what it will undo before doing it (`Undoing: reject F42 (line 118, 2026-10-16 14:02); back to accept.`), `--n N` walks back N steps, `--list` shows the last 10, and `--import` retracts the last import. `review undo-last` undoes review decisions only; to reverse EXIF writes use `undo --run RUN`, and each command's help and not-found error names the other (`Nothing to undo. To reverse EXIF writes: undo --list`; `No run 'R9'. To undo a review decision: review undo-last`). Re-deciding also reverses a decision, because latest wins.

**Which forms apply immediately and which preview first** (the item screen's Next: block repeats this; tiers are defined once in S12):

| Form | Behavior | Tier |
|---|---|---|
| `review accept|reject|skip <id>`, `review set <id> --date`, labeling a cluster or face by id | immediate for one item, undone by `review undo-last` | T1 |
| `review reject C12` | immediate when C12 is Undecided or Skipped; when C12 is Accepted it previews the label count and needs `--apply` (rule f) | T1, T1a for the Accepted case |
| `review set F42 --date D` that a guard refuses | exits 1 with the refusal, which names the override; `--force-guard` then applies immediately and prints `Override: --force-guard (BirthDeathBounds). Journaled.` (the refusal is the preview) | T1+ |
| `review set <album> --offset|--date`, `review confirm-genuine|confirm-placeholder --album ...`, `review import FILE` | dry-run; `--apply` required | T1a |

**Review at scale: the 15k Suspect/placeholder items (S12).** One file per decision is the wrong unit for `source=placeholder`. The visual path and the group path are:
1. `review list --source placeholder --by album` lists albums by expected gain (files resolved per decision), each row with class, signal set (words, not codes), and count.
2. `review sheet --placeholders --album ID [--signals jan1,no_make_model] [--sample N --seed 7] --open` writes `placeholders-<id>.html`: a deterministic, stratified sample of the selection (default size `max(48, ceil(4 x sqrt(files)))` capped at 200: 82 cards for 412 files, 200 for 9,161; strata are the distinct exact EXIF timestamps first, then the signals, so a rare timestamp is never missed), each card showing the current EXIF date and time, the class, and the signals, plus totals (`412 files; 82 shown`) and an **EXIF-date histogram** of the whole selection (the ten most common exact timestamps with counts and a by-year bar list; a single timestamp holding most of the group is the fastest mass-placeholder tell). Re-sampling with another `--seed` shows other cards. **A placeholder sample sheet is always one page** (at most 200 cards, never paginated; `--sample N` above 200 is refused with `Sample is capped at 200 cards; use --seed to see other cards`), so the group controls and the exceptions live on exactly one page and an export can never carry half of a group's exceptions. Group controls sit at the top: `Genuine: all 412`, `Placeholder: all 412`, `Skip group`. Card buttons are `Genuine`, `Placeholder` and `Unsure`; a card whose choice differs from the group control, or is `Unsure`, is an **exception** (kept out of the group action; a differing choice is exported as its own per-file entry).
3. The same decision from the terminal: `review confirm-genuine --album ID [--signals jan1] [--except IDS] [--apply]` and `review confirm-placeholder --album ID [--signals ...] [--except IDS] [--apply]` (the group form of `reject`/`accept` on `P` items; `--except` takes the `P` ids spotted on the sheet or in `review list`, for example `--except P4022,P4031`). Dry-run default prints the file count, the exceptions, the five most common exact EXIF timestamps in the selection, five sample rows and `Apply: ...`. `--apply` on more than 50 files is refused unless a sample sheet was generated for that selection (the sheet records a selection hash; a `group` entry that arrives from that sheet's Export also counts): `412 files selected and no sample sheet was generated for this selection (the tool cannot tell whether you looked at it). Run: review sheet --placeholders --album ID --signals jan1 --open` (override: `--unviewed`).
4. **A group decision has one representation: materialized per-file owner records, with one `group` log line as its handle.** Applying a group appends one `group` line (`scope=album|signals`, the selector, `group_id`, `count`, `sample_hash`, `outcome`, the merged exception list) and, in the same command, one owner record (`Genuine` or `LegacyPlaceholder`, `source=owner`, carrying the `group_id`) per selected file that is not excepted; the fold never expands a `group` line at read time. `review undo-last` retracts the line and supersedes exactly those records, restoring each file's previous record in one step. Consequences, all stated once here: (a) **Drift.** Files that join the album or signal set after the decision (a re-scan, new files) are not covered; they appear as new Undecided `P` items and the group line's `count` is never silently exceeded. (b) **Exceptions are a set, merged across exports.** When a `group` line arrives with the same `group_id` and `outcome` as earlier non-retracted lines (another sample sheet with a different seed, a second export), its exceptions are united with theirs before records are written, so a later export never labels a file an earlier one excepted; an exception is lifted only by deciding that file on its own (`review confirm-genuine P4022`) or by undoing the earlier line. (c) **Stale exceptions.** An exception id that is no longer in the selection (file removed or reclassified) is dropped with `Ignored 1 stale exception (P4099 is not in this selection)`. (d) **Overlap precedence.** Album-scope and signal-scope groups carry no rank: per file, the latest non-retracted owner record wins, whichever group or per-file decision wrote it; a per-file decision made after a group beats it. **Exception end-state:** an excepted file gets no owner record from the group line; it stays `Suspect` and Undecided, is not written and not uploaded, and is served again by `review next --source placeholder`, where it is decided one file at a time (`review confirm-genuine P4022`). The group result line says so (`Confirmed 409 genuine; 3 exceptions stay Suspect: review next --source placeholder`).

| Error / edge | Message | Exit path |
|---|---|---|
| Unknown item id | `No review item 'F999'. List: review list` | list |
| Bare number as an id | `'42' needs a prefix: F42 (file), P42 (placeholder). Nothing was changed.` | retype with the prefix |
| Id names a different item than the log line recorded | `Ignored 1 line: id F42 now names a different file` (the line is never attached to another item) | `review list` |
| `--date` unparseable or impossible (month 13) | `Could not read date '1976-13'. Use YYYY, YYYY-MM or YYYY-MM-DD. Example: --date 1976-06` | rerun |
| `--date` before an identified subject's birth | `1976-06 is before Alice's birth (1980). Choose a later date, or override: --force-guard` (override is journaled with the guard name) | change date or force |
| Date in the future / upload window (today) | `2026-10-16 is today. That is the value this tool exists to prevent. Choose the real date or: review skip F42` | rerun or skip |
| Verb not valid for the source | `review set is not defined for cluster C12. Use: review accept C12 --name NAME` | the printed verb |
| Already decided (re-decide) | accepted; prints `Replaced earlier decision (accept) from 2026-10-15` | n/a |
| `decisions.jsonl` torn tail | loads valid prefix and prints `Ignored 1 torn line at the end of decisions.jsonl (interrupted write). Earlier decisions are intact.` | continues |
| `decisions.jsonl` unreadable/permission | `Cannot append to DATA/review/decisions.jsonl: <reason>. Check permissions (expected 600). Decision NOT saved.` | fix perms, rerun the command |
| Stale items (fuse reran, item gone) | `Item F42 no longer needs review (re-analysis resolved it). Next: review next` | next |
| Group `--apply` with no sample sheet generated | see point 3 above | generate the sample sheet |
| `--except` id not in the selection | `File P9999 is not in this selection (412 files). Nothing was changed.` | fix ids |

### S4. HTML contact sheet (cluster, date-group, placeholder, index)

Commands: `review sheet --cluster C12 [--page N | --all]`, `review sheet --clusters [--all]` (index), `review sheet --album <album-id> [--page N]` or `--group <group-id>` (date-group sheet; writes `DATA/review/sheets/dategroup-<id>-p<N>.html`), `review sheet --placeholders --album ID [--signals ...]`. All take `--open`. Wireframe (cluster sheet; the date-group sheet has the same shell with photo cards, a provenance column, a `Set date` field per card and an album block at the top, see the control table below):

```
+---------------------------------------------------------------------+
| <nav> Prev | Index | Next | Next unlabeled        Page 1 of 3        |
| <h1> Cluster C12 - 60 faces, est. 1962-2004  [?] Keys [Next undecided card] [Export] |
| <p> 12 of 24 shown faces judged </p>  (visible text; spoken text is a separate live region)  |
|  [x] Keyboard shortcuts on    [Undo last (u)]  [Clear all...]        |
|---------------------------------------------------------------------|
| Cluster actions:  [Accept as person...] [Reject cluster] [Skip]     |
|  Name (required; closed list from people.toml): [ Grandma Ruth  v ]  |
|  Viewing 24 of 60 faces. [Show next 24]                              |
|---------------------------------------------------------------------|
| <h2> Outliers (farthest from centroid) </h2>                         |
| +--------+ +--------+ +--------+ +--------+ +--------+ +--------+   |
| | face   | | face   | | face   | | ...    | |        | |        |   |
| | C12/F3 | | C12/F5 | |        | |        | |        | |        |   |
| | 1962?  | | 1978   | |        | |        | |        | |        |   |
| |1985 Bch| |Xmas 78 | | In log:| |        | |        | |        |   |
| |[Enlarge| |[Enlarge| | Accepted|         |        | |        |   |
| |[Same]  | |[Same]  | |        | |        | |        | |        |   |
| |[Not]   | |[Not]   | |        | |        | |        | |        |   |
| |[Unsure]| |[Unsure]| |        | |        | |        | |        |   |
| +--------+ +--------+ +--------+ +--------+ +--------+ +--------+   |
| <h2> Sampled across estimated age (up to 24 total) </h2> ...         |
|---------------------------------------------------------------------|
| Decisions are held in this page. Press [Export] to download          |
| decisions.json, then run:  gphotos-organizer review import FILE      |
+---------------------------------------------------------------------+
```

Card text: thumbnail, cluster/face/item id (`C12/F3`), state word + icon (review-state words `Accepted`, `Rejected`, `Skipped`, `Undecided`; on face and placeholder cards the button label follows in parentheses, for example `Rejected (not this person)`), caption = album name + estimated year, an `Enlarge` button. The wireframe abbreviates the buttons: `Same person` / `Not this person` / `Unsure` on cluster sheets, `Genuine` / `Placeholder` / `Unsure` on placeholder sheets, `Accept date` / `Reject date` / `Skip` on date-group sheets. **Alt text by sheet kind:** cluster sheet `Face crop from <album>, estimated <year>`; date-group sheet `Photo <file name> from <album>, current date <YYYY-MM-DD or none>`; placeholder sheet `Photo from <album>, EXIF date <YYYY-MM-DD HH:MM:SS>`. A card for an item that is already decided in `decisions.jsonl` at generation time carries a read-only badge `In log: Accepted (2026-10-15)`. Date-group card also shows folder date, inferred date, confidence, voters (provenance), and a `Set date` field (YYYY[-MM[-DD]], validated, see below) that exports a `set`. Card verbs follow the per-source table in S3 (a face card on a cluster sheet follows the face rows in S2).

**Control table: which sheet control produces which export entry** (the single mapping between buttons and `gpo-decisions/2`, as S2 gives for cluster sheets):

| Sheet kind | Control (label) | Export `kind` / `action` | Carries |
|---|---|---|---|
| cluster | face `Same person` / `Not this person` / `Unsure` | `face_member` / `accept` / `reject` / `skip` | `item=C12`, `face`, `face_id` |
| cluster | `Accept as person...` / `Reject cluster` / `Skip` | `cluster_label` / `accept` / `reject` / `skip` | `item=C12`, `name` on accept |
| date-group | file card `Accept date` / `Reject date` / `Skip` | `file` / `accept` / `reject` / `skip` | `item=F42`, `item_key` |
| date-group | file card `Set date` field | `file` / `set` | `item`, `value` |
| date-group | year-precision card `Release date` / `Keep keyword-only` / `Skip` (cards of `Y` items; `Set date` gives a more precise date) | `year_precision` / `accept` / `reject` / `skip` / `set` | `item=Y77` |
| date-group | audit card `Date is right` / `Remote is right` / `Skip` (cards of `U` items; `Set date` gives the true target) | `audit` / `accept` / `reject` / `skip` / `set` | `item=U310` |
| date-group | album block (top of the sheet) `Accept album date` / `Reject album date` / `Skip album`, and an `Offset` field (`+10y`, validated like `--offset`) | `album_date` / `accept` / `reject` / `skip`; `Offset` exports `album_date` / `set` with `offset` | `item=A7`; on import an `offset` entry is a preview first, exactly like `review set A7 --offset`, and needs `--apply` |
| placeholder | file card `Genuine` / `Placeholder` / `Unsure` | `placeholder` / `reject` (genuine) / `accept` (placeholder) / `skip` | `item=P4021` (an exception when it differs from the group control) |
| placeholder | group controls `Genuine: all N` / `Placeholder: all N` / `Skip group` | `group` / `reject` (outcome `genuine`) / `accept` (outcome `legacy_placeholder`) / `skip` | `group_id`, merged `exceptions` |

**Index sheet** (`index.html`): one row per cluster or album with id, size, estimated years, status word (`Accepted: <name>`, `Partly labeled: <name> (k of n)`, `Mixed names`, `Rejected`, `Skipped`, `Undecided`, `Merge queued`), expected gain and a link; sorted by expected gain; links to the next unlabeled; regenerated on every `review sheet` run and by `review import --apply` (a navigation aid; the log is the truth; individual sheets keep their `In log:` badges until `review sheet --cluster C12` is rerun).

**Scale rules**: a date-group sheet shows at most 100 cards per page (`--per-page N`, max 200), with `Page k of N` and first/prev/next/last links; the 9,161-file album is 92 pages, and only the requested page's thumbnails are generated (`Thumbnails 120/9161 (9041 cached)` progress on stderr, a plain line per 500 when non-TTY). Each page has its own sheet id and its own localStorage entry (a few bytes per decision), and `review import` accepts several export files at once; per-file entries from different pages never conflict because each names its own item. A **placeholder sample sheet is never paginated** (one page, at most 200 cards, S3 point 2), because its group controls and exceptions must live on one page; exceptions from separate exports of the same group are united at import (S3 point 4). Group decisions (S3, S12) are the intended route for thousands of files; per-card review is for samples and exceptions.

Interaction:
- Keys (WCAG 2.1.4): the single-letter shortcuts `a` (same person / accept), `r` (not this person / reject), `s` (unsure / skip), `u` undo last, `e` enlarge, `?` key map act **only while a card has focus** (never on the page body or in a text field), and a visible `Keyboard shortcuts` checkbox turns them off entirely (persisted); every shortcut also exists as a visible button, so no function depends on a character key. The page itself needs no key to read.
- **Keyboard model (one definition: natural Tab order, arrows optional).** Cards are `<li>` elements of a plain `<ul>` (the list claims no composite role such as `grid` or `listbox`); each `<li>` contains one `<div role="group">` named `Face C12/F3, undecided`, which is where the per-card state text lives. **Every control of every card is in the natural Tab order, with no roving tabindex and no `tabindex="-1"` on any card control**, so with shortcuts off a keyboard user reaches and operates every card using only Tab, Shift+Tab and Enter/Space. The Tab-stop budget per card is the card's decision buttons, then `Enlarge`, then `Next undecided card`: **5 stops per card on cluster and placeholder sheets (3 buttons + Enlarge + skip) and 6 on date-group sheets (3 buttons + `Set date` + Enlarge + skip)**; deciding N consecutive cards costs at most 5N (or 6N) Tab presses plus Enter/Space. `Next undecided card` is a native button, visually hidden until it has focus, and is the last stop of every card; activating it moves focus to the first decision button of the next card that is still undecided (or to `Export` when none is left), so a user who has judged a card jumps over the already-judged ones without walking every stop. One more `Next undecided card` button sits in the header for a user who has not entered the list. Arrow Left/Right/Up/Down, Home/End and PageUp/PageDown are an enhancement for sighted keyboard users: they move focus to the same control of the neighbouring card, only while focus is inside a card and not in a text field, never wrap and never intercept page scrolling; no function depends on them, and screen-reader users get the same function from browse mode and the native buttons. After a decision focus stays on the same button (state text is updated in place, the element is never re-created); an optional `Advance after decision` checkbox (off by default) moves focus to the next undecided card.
- **Decision controls are `aria-pressed` toggle buttons inside a `role="group"` (one definition; a radiogroup is rejected).** The decisions are mutually exclusive, which the group's accessible description says (`Choose one: Same person, Not this person, Unsure. Press the selected one again to clear.`), and the card's state text names the current choice, so exclusivity is conveyed without a composite role. A `radiogroup` of native radios was rejected because radios are one tab stop with arrow-key movement (it would reintroduce the roving model) and cannot be un-selected, while the design lets a pressed decision be pressed again to return to Undecided.
- Pressing the same decision key again on a decided card returns it to Undecided (toggle); `u` undoes the last decision (50 deep); `Clear all...` opens a native `<dialog>` confirm.
- Visible counter and spoken text are separate. The visible counter (`12 of 24 shown faces judged`; `All 24 judged. Export now.` at zero left) is plain text updated on every change. A visually hidden `role="status"` (polite) region carries the spoken text, updated at most every 1.5 s, saying `12 of 24 judged` on every fifth change and `All 24 judged` at zero left; per-card state is spoken by the pressed button, not by the live region.
- Enlarge: the `Enlarge` button (or `e`) opens a native `<dialog>` with a 1024 px crop or photo, caption, Prev/Next, Esc to close and focus returned to the card; `a`/`r`/`s` still act on the shown card.
- Export is a native button that downloads `decisions-<sheet-id>-<run-or-fuse-id>-<generation>-<YYYYMMDDTHHMMSS>.json` (for example `decisions-cluster-C12-CR7-9f2c41aa-20261016T1402.json`), so 212 exports never collide as `decisions (1).json`. `review import --latest` resolves the newest such file from the download directory (`$XDG_DOWNLOAD_DIR`, else `~/Downloads`) and `--glob 'decisions-cluster-*.json'` resolves several, both at dry-run time only; the dry-run prints the `Apply:` command with the resolved file names pinned (rule in S5). The files contain person names and the tool does not delete them (S5). `Mark as imported` (after running the import) clears this page's local decisions and shows `Imported 12 at 14:10`. After Export the header shows `Exported 12 at 14:10`.
- Persistence: decisions are stored in `localStorage` under `gpo:v2:<sheet-id>:<generation>`; `generation` is the first 8 hex characters of a hash over the sheet kind, its item ids and candidate values, and the `cluster_run_id` or `fuse` run, so a regenerated sheet with different content never inherits old decisions. If an older generation's key exists for the same sheet id, a banner says `Decisions from an older version of this sheet (12, saved 2026-10-15) exist. [Export them] [Discard]`. Best effort: if storage is unavailable or full, a banner says decisions are lost on close and offers Export now (a quota error never drops the decision in memory). The banner names the limit: `file://` pages keep decisions per file in Firefox and share one store across files in Chrome, and neither survives clearing site data, so Export is the durable step.
- Layout and focus visibility (WCAG 2.4.11, 1.4.10): the grid reflows to one column at 320 CSS px with no horizontal scroll; the header is sticky only when the viewport is at least 600 px tall, with `scroll-padding-top` equal to its height so a focused card is never hidden under it.
- **Labels and errors.** Every field has a visible `<label>` (Name, Set date); the Set date error text sits in a `<p id>` that the input references with `aria-describedby` and `aria-invalid="true"`.
- **Set date validation (date-group sheets).** The field accepts `YYYY`, `YYYY-MM` or `YYYY-MM-DD` and shows the parsed precision beside it (`month precision: 1976-06`, `year precision: 1976`). It refuses a malformed value, today or the future (`2026-10-16 is today. That is the value this tool exists to prevent.`) and a date before the birth of a person identified on that card (`1976-06 is before Alice's birth (1980).`), with the same messages as `review set`; the sheet embeds birth years only for the people shown on its cards. `review import` runs the same checks on every `set` value (S5) and honors `--force-guard`; the sheet never exports a value it refused.
- **Zoom and spacing (WCAG 1.4.4, 1.4.12).** At 200% zoom (a 640 CSS px wide viewport) and with the text-spacing overrides (line height 1.5, paragraph spacing 2x, letter spacing 0.12em, word spacing 0.16em) no text is clipped or overlapped and every button keeps its 24 px target; checked in Playwright.
- The page is usable without JS: it lists the equivalent terminal commands per card (`review accept C12 --name ...`, `review reject C12/F3`), so the sheet is readable and actionable even with scripts blocked.
Exit: close the tab at any time (nothing was written to the pipeline); Export then `review import`; or use the terminal commands shown on the page.

| State | What the user sees | Exit path |
|---|---|---|
| Empty cluster/group | Page with `<h1>` and `No faces in this cluster (it was merged into C40). Run: gphotos-organizer review next` | terminal |
| All decided | Counter reads `All 60 decided. Export now.`; the Export button gets focus on `Tab` from the last card | export |
| Thumbnail missing/drive unmounted | Tile shows the alt text and `Thumbnail unavailable (drive not mounted)`; other cards unaffected | mount drive, regenerate: `review sheet --cluster C12` |
| Thumbnail load error | same tile fallback via `onerror`, no layout shift (fixed 256px box) | regenerate |
| JS disabled | Banner `Keyboard shortcuts and export need JavaScript. Use the terminal commands shown on each card.` | terminal commands |
| Export with zero decisions | Button carries `aria-disabled="true"` (it stays focusable and does nothing) and `aria-describedby` pointing at the visible text `Nothing to export yet` | decide something |
| Export download blocked | Fallback: a `<textarea>` with the JSON and `Copy it into decisions.json, then run: ...` | copy-paste |
| Sheet stale (cluster pass reran after generation) | Header shows generation timestamp and `Regenerated after analysis? Rerun: review sheet --cluster C12`; `review import` ignores `cluster_label` entries whose `cluster_run_id` differs from the current one and applies `face_member` entries by canonical `face_id` (S5) | regenerate |
| Older-generation decisions in storage | banner with Export / Discard (see Persistence) | export or discard |
| localStorage unavailable or full | banner: decisions are lost on close; Export now | export |
| Shortcut key pressed with no card focused or while typing | nothing happens (shortcuts need card focus) | n/a |
| Index and `In log:` badges stale after an import | `review import --apply` regenerates `index.html` itself and prints `Individual sheets keep old badges until regenerated: review sheet --cluster C12`; the sheet header shows its generation time | regenerate |
| `--open` cannot start a browser | `Could not open a browser (xdg-open not found). Open this file: file://...` (exit 0) | open by hand |
| `--all` interrupted at `Sheets 40/212` | rerun keeps sheets with an unchanged generation: `Sheets 40/212 kept, 172 to write` | rerun |
| Set date refused (format, today, future, before birth) | inline error under the field, linked by `aria-describedby`; no export entry is created | fix the value |

### S5. `review import decisions.json`

```
$ gphotos-organizer review import --latest
Dry run: 12 entries from ~/Downloads/decisions-cluster-C12-CR7-9f2c41aa-20261016T1402.json (sheet cluster-C12, generation 9f2c41aa, cluster run CR7)
  cluster_label accept C12 "Grandma Ruth"                       (new)
  face_member   reject C12/F3                                    (new; becomes cannot-link at the next cluster pass)
  face_member   accept C12/F5                                    (new)
  file          set    F42 1976-06                               (new; month precision)
  cluster_label reject C40                                       (new)
  group         genuine A7 [jan1] 412 files, 3 exceptions (P4022, P4031, P4040; stay Suspect)   (new)
  file          skip   F43                                       (duplicate of folded decision; ignored)
  ...
Would append 11, ignore 1 duplicate, reject 0.
Apply: gphotos-organizer review import ~/Downloads/decisions-cluster-C12-CR7-9f2c41aa-20261016T1402.json --apply
```

**`--latest` and `--glob` select files at dry-run time only.** The dry-run prints the `Apply:` command with the resolved file names, so what is applied is exactly what was previewed even if a newer export lands in the download folder in between; `review import --latest --apply` is refused with `--latest resolves a different file each time. Run the dry-run and use the Apply command it prints. Nothing was changed.` Exit: dry-run changes nothing; `--apply` appends and prints `Appended 11 decisions (import X-20261016-3b1f; reverse with: review undo-last --import). Next: review next`. Several files may be given (`review import a.json b.json`, or `--glob 'decisions-cluster-*.json'`); `--apply` also regenerates `index.html` and prints `Individual sheets keep old badges until regenerated: review sheet --cluster C12`. The export files contain person names and stay in the download folder: `--apply` prints `Export files contain names and stay in ~/Downloads. Delete them, or move them under DATA/review/imported/ with: review import ... --apply --archive` (`--archive` moves the applied files and never deletes them).

Export schema (`gpo-decisions/2`), the single contract between Story 7.4 (writer) and Story 7.4 `review import` (reader):

```json
{
  "schema": "gpo-decisions/2",
  "export_id": "X-20261016-3b1f",
  "sheet": {"id": "cluster-C12", "kind": "cluster", "generation": "9f2c41aa",
            "cluster_run_id": "CR7", "generated_at": "2026-10-16T14:02:11Z"},
  "items": [
    {"kind": "cluster_label", "item": "C12", "action": "accept", "name": "Grandma Ruth", "decided_at": "2026-10-16T14:05:40Z"},
    {"kind": "face_member",   "item": "C12", "face": "F3", "face_id": "<ContentKey>:<x,y,w,h>", "action": "reject", "decided_at": "2026-10-16T14:03:12Z"},
    {"kind": "file",          "item": "F42", "item_key": "<ContentKey>", "action": "set", "value": "1976-06", "decided_at": "2026-10-16T14:07:01Z"},
    {"kind": "album_date",    "item": "A7", "item_key": "<album id>", "action": "set", "offset": "+10y", "decided_at": "2026-10-16T14:08:10Z"},
    {"kind": "group", "group_id": "g-7c1e90ab44d1", "source": "placeholder", "scope": "signals", "album": "<id>",
     "signals": ["jan1"], "action": "reject", "outcome": "genuine", "count": 412, "sample_hash": "ab12...", "exceptions": ["P4022", "P4031", "P4040"], "decided_at": "2026-10-16T14:09:30Z"}
  ]
}
```

`kind` is one of `cluster_label`, `face_member`, `file`, `album_date`, `year_precision`, `audit`, `placeholder`, `group` (all snake_case; the log also has `cluster_link` and `remediation`, which sheets never export); the control that produces each is in the S4 control table; `action` is `accept|reject|skip|set`; `item` is the typed id of S3 and `item_key` its stable key (required on every non-cluster item; the importer resolves by `item_key` and rejects an entry whose alias and key disagree: `Entry F42 names a different file than the log's F42. Regenerate the sheet.`); `name` is required on a `cluster_label accept`; `value` is required on a `set` of a date and `offset` on an album `set` that is an offset (a `set` carries exactly one of the two); `face_id` is canonical (`F3` alone is meaningful only with the matching `cluster_run_id`).
- `decided_at` (UTC, required on every item) is when the card or control last changed in the browser. It makes the conflict rule evaluable: an entry is a conflict only when the log already holds a **terminal decision** (the S3 definition: an `accept`, a `set`, or a `reject` on a kind whose reject is terminal; never a `skip` or a hold-kind `reject`) for the same item whose `ts` is later than `decided_at`; otherwise the entry is appended (its log `ts` is the import time, but `decided_at` is kept), so an import never overwrites a terminal decision made after the click.
- `group` entries carry `group_id` (first 12 hex of sha256 over `source|scope|album|sorted signals`; it names the selection, never a page, because placeholder sample sheets are single-page) and `outcome` (`genuine|legacy_placeholder|skip`, the readable form of the `accept|reject` action on a placeholder group), so two placeholder groups with the same action never collide and an import dry-run can print `group genuine A7 [jan1] 412 files, 3 exceptions`. An imported `group` entry is applied as a whole by the S3 point 4 rule (materialized per-file records, exceptions united with those of earlier same-`group_id` same-`outcome` lines, stale exceptions dropped).
- Dedup key: `(kind, item | group_id, face, action, value | name | outcome + hash(exceptions))`, so importing the same file twice is a no-op, two different groups are both kept, and the same group re-exported with different exceptions is a new line whose exceptions are united with the earlier ones (S3 point 4), never a replacement.
- Imported `set` values are validated like `review set` (format, today/future, before an identified person's birth); a refused value is rejected individually with the terminal message, and `--force-guard` (T1+) overrides the birth guard only.

| Error | Message | Exit path |
|---|---|---|
| File not found | `No such file: ~/Downloads/decisions.json. The sheet's Export button saves decisions.json to your browser download folder.` | find file |
| Not valid JSON / wrong schema | `decisions.json is not a decisions export (missing 'items'). Export again from the sheet. Nothing was changed.` | re-export |
| Unknown ids (e.g. C999) | `Rejected 1 entry: unknown item id 'C999' (not in DB; sheet may be stale). 11 other entries are unaffected. Regenerate: review sheet --cluster C12` | regenerate sheet; apply the rest |
| Stale cluster run | `Entries for C12 were made against cluster run CR7 but the current run is CR9. Applied 3 face_member entries by face_id (they survive renumbering); Ignored 1 cluster_label (cluster-level entries are valid only for the run that recorded them). Regenerate: review sheet --cluster C12`. A `face_member` whose `face_id` no longer exists reads `Ignored 1 face_member (face no longer exists)` | regenerate |
| Conflicting with newer terminal decision | listed as `conflict`: `C12: sheet says accept, terminal decided reject on 2026-10-16 14:02 (after your click at 14:00). Not imported. Use --prefer-import to override.` A later `skip` or hold-kind `reject` in the log is not a terminal decision and never causes this | flag or leave |
| Cluster-label entry missing `name` | `Entry C12 has action accept but no name. Add the name in the sheet or run: review accept C12 --name "..."` | fix |
| Name not in `people.toml` | `Entry C12 names 'Grandma Rut', not in people.toml (people.toml changed after the sheet was generated, since the sheet's list is closed). Regenerate the sheet: review sheet --cluster C12   (or run the import with --new-person).` | regenerate or flag |
| Group entry with no sample sheet generated | same rule as the terminal group form (an entry that arrives from the sheet's Export satisfies it) | generate the sample sheet |
| `set` value refused | `Entry F42 set '1976-13': could not read date. Use YYYY, YYYY-MM or YYYY-MM-DD.` / `... 1976-06 is before Alice's birth (1980). Choose a later date, or override: --force-guard` / `... 2026-10-16 is today ...` (other entries still apply) | fix or force |
| Entry without `decided_at` | `Entry C12 has no decided_at; export again from the sheet. Nothing was changed.` | re-export |

### S6. Plan / apply / undo (EXIF write gate)

```
$ gphotos-organizer plan
Plan 7f3a21 written -> DATA/plan.jsonl  (decisions as of fuse run R42)
  Eligible to write: 1,214   Held: Needs review 172, Conflict 9;  no write needed (anchor, real date already on disk) 3,106
  Anchors/overrides needing a date written (filename, owner album, review set): 41
  Precision:         day 200 (date written); coarser than day 1,014 (keyword gpo-year only, no date written; release per album: plan --allow-year-precision --album ID)
  Formats:           jpg 1,180; png (XMP only) 21; heic unwritable (round-trip not confirmed) 13
  Sample (first 5): file | old | new | confidence | voters
  ...
Dry run only. Review DATA/plan.jsonl, then apply it (fix-metadata is the pair of plan):
  gphotos-organizer fix-metadata --apply --plan 7f3a21
```

`fix-metadata --apply`:
1. Preflight, in this order, failing fast before any write: (1) plan fresh, (2) drive mounted, (3) exiftool present, (4) workdir clean, (5) attested full-drive backup on another medium on record (`backup verify`), (6) a recorded clean `fsck.exfat -n` result that is still fresh (`backup fsck`), (7) 20-file canary passed (`backup canary`). Each failure names the exact command that fixes it. **Preflight never runs fsck and never asks for sudo; check (6) reads the result that `backup fsck` recorded in the attestation** and requires exit status 0, recorded after the most recent write run and not more than 24 hours earlier (`--fsck-max-age`, INFERRED), otherwise `No fresh fsck result (last: 2026-10-14 09:12, 3 runs ago). Unmount the drive, then run: gphotos-organizer backup fsck. Nothing was changed.` Running the check needs the drive unmounted and read access to the block device (normally root), which is why it is its own command: `backup fsck` runs `sudo fsck.exfat -n DEVICE` on a TTY (sudo prompts; the tool never sees a password), or reads the output of a run you did yourself (`--from-output FILE`), and prints which route it used.
2. Confirmation (tier T2, S12): `About to write to 1,214 files across 88 albums (200 dates, 1,014 keyword-only; journaled; reverse with: undo --run R7). Type the number of files to write to continue:` The prompt does not print the number (it is in the sentence above), so a muscle-memory Enter or a copy of the prompt cannot confirm; both `1,214` and `1214` are accepted, because the summary prints the thousands separator; the plan id is already on the command line via `--plan` and is not the token. `--yes` supplies the token only in non-TTY, and never skips the preflight.
3. Progress bar with ETA, per-chunk read-back verification. One album per mount-sync-verify cycle; every N albums (default 10, `--fsck-every N`) the run stops at the album boundary instead of prompting for root mid-run: `Paused after 10 of 88 albums: the periodic fsck is due. Unmount the drive, run: gphotos-organizer backup fsck, remount, then rerun: gphotos-organizer fix-metadata --apply --plan 7f3a21 (resumes).` (exit 0; the next preflight accepts the new fsck record); each file's bytes are first kept in `DATA/prewrite/<run>/` until you run `prewrite purge --run R7`. Ctrl-C finishes the current chunk, flushes the journal, prints the resume line.
4. Summary: `Written, read-back OK 1,201; mismatch 9; failed 4 (see errors.jsonl). Run id R7. Undo: gphotos-organizer undo --run R7. Next: gphotos-organizer audit` plus any failure retry command.

`undo --run R7`: dry-run table of intended reversions (file, current, restored value); `--apply` required; same typed-count confirmation (T2); summary with read-back. `undo --force` (modified files) and `prewrite purge --run R7` are T3: typed count plus their precondition (S12).
Exit: any prompt can be left with Ctrl-C or non-matching input (`Confirmation did not match; nothing was changed.`).

| Error | Message | Exit path |
|---|---|---|
| No plan | `No plan found. Create one: gphotos-organizer plan` | plan |
| Stale plan | `Plan is older than the latest analysis. Regenerate: gphotos-organizer plan` (exit 1) | plan |
| Nothing eligible | `Plan is empty: 0 eligible decisions (172 still need review). Next: gphotos-organizer review next` | review |
| Drive unmounted | `Source drive not mounted: /run/media/tstapler/EE5B-3D9B. Mount it and rerun the same command. Nothing was changed.` Mid-run disappearance: stop, flush journal, `Stopped after file N of M (last good: <path>). Rerun the same command to continue; journaled writes are safe.` | mount, rerun |
| exiftool missing | `exiftool not found. Install: brew install exiftool` | install |
| Write/read-back mismatch | counted separately, listed in `errors.jsonl`; album does not reach `Read-back OK`; `Retry only these: fix-metadata --apply --retry-failed` | retry or undo |
| No backup / stale backup | `No attested full-drive backup on another medium. Run: gphotos-organizer backup verify --copy <path>. Nothing was changed.` | backup verify |
| Not enough local space for pre-write snapshots | `Not enough local space for pre-write snapshots (need X, have Y). Free space or apply fewer albums with --album.` | free space / `--album` |
| Workdir leftovers (exFAT path) | `Leftover files in /tmp/gpo-work from run R6. Inspect, then remove it or run: gphotos-organizer recover --run R6` | recover |
| Source on exFAT without `--workdir` | `Source is on exFAT: in-place writes are refused. Rerun with --workdir /tmp/gpo-work. Nothing was changed.` | rerun with workdir |
| Year-only decisions in the plan | plan summary line `Year-precision held: N files (keyword only; no date written). Review: review list --source year_precision` | review or `plan --allow-year-precision --album ID` |
| Undo unknown run | `No run 'R9'. Runs: gphotos-organizer undo --list` | list |
| File changed since journal (undo) | listed `left unchanged: modified after run` with `--force` option (T3); the default leaves it unchanged, never overwriting unknown content | force or leave |

### S7. Upload gate and quota wait

```
$ gphotos-organizer upload --apply
Gate: 1985 Beach: ready (would upload)
Gate: 2021 random photos: Blocked (deny-listed until dates are resolved).
Gate: 1990 Xmas: Blocked: 1 of 40 files have no resolved date. Run: gphotos-organizer review next
...
About to upload 21 albums (7,757 files; not reversible by this tool; fix later with: audit --plan). Type the number of albums to upload to continue:
Album 1985 Beach: ok (uploaded_unverified)
...
Done: 21 albums uploaded_unverified, 2 Blocked. Next: gphotos-organizer audit
```

`upload --apply` is tier T2 (S12): the `Gate:` lines are the dry-run result (they say `ready (would upload)`, never `ok (uploaded_unverified)`, so nothing reads as uploaded before consent); then it prints the album and file counts and asks for the album count as a typed token (the file count when exactly one album would upload, so `--album X` is not answered by a muscle-memory `1`); `--allow-unaudited` is also T2. `--i-verified-trash ALBUM` is T3: the album id is already on the command line, so the prompt asks for a number that is not (`Overriding the audit gate for 1 album (412 local files). Type the number of local files to continue:`), after the precondition check (the album's only failing gate is the audit-coverage rule). The gate lines above print before the prompt, so blocked albums are never part of the count.

Quota: `Google Photos daily upload quota reached after 18 albums. Resuming at 00:05 Pacific (in 3h12m). Ctrl-C to stop and rerun tomorrow; progress is saved.` Live countdown, interruptible; Ctrl-C exits 0 with the rerun command.
Without `--apply`: the same `Gate:` lines and no prompt, ending with the exact `--apply` command.

| Error | Message | Exit path |
|---|---|---|
| Placeholder scan not run / album has legacy-placeholder or unscanned files | `Blocked: placeholder scan not run. Run: gphotos-organizer placeholders scan --root <drive>` / `Blocked: N files in album <id> carry legacy-placeholder or unverified dates.` | placeholders scan |
| Decided date not written yet (filename/owner-album anchor or UserOverride) | `Blocked: N files have a decided date that is not written yet. Run: gphotos-organizer plan, then fix-metadata --apply` | plan, apply |
| Gate blocks (unresolved dates, deny list) | per-album line with the reason and `review next`; run continues with other albums | review |
| rclone missing/auth expired | `rclone is not configured or its token expired. Run: gphotos-organizer setup-rclone` | setup-rclone |
| Drive unmounted | standard drive message | mount |
| Upload failure of one album | `Album X failed (rclone exit 1: <last line>). Not marked uploaded. Retry: gphotos-organizer upload --apply --album X` | retry |
| Everything already uploaded | `Nothing to upload: 0 albums pending (604 uploaded_unverified, not audited). Next: gphotos-organizer audit` | audit |

### S8. Audit and remediation

```
$ gphotos-organizer audit --source rclone
Enumerated 7,757 remote items. Matched 7,690 to local files; 67 remote-only, 24 local-only.
Coverage: rclone-created items only (cannot see items uploaded by other apps)
Coverage per album: observable 540 albums, unobservable 64 (their old items cannot be seen; never reported clean)
Suspicious (dated in upload window): 83   Dated like legacy placeholders: 3,310   Outside decision interval: 41
Added 124 items to the review list (source=audit; an item can fall in more than one category, so the counters do not sum to 124).
Next: gphotos-organizer audit --plan --strategy webui
```

All counts in this sample are illustrative (they are not measurements). `audit --plan --strategy webui` writes `DATA/remediation/webui-<album>.md` (S11 sample) and prints `Worklist: 7 albums, 124 items. Open DATA/remediation/webui-1985-Beach.md. No network calls were made.`
`remediation done <item|--album A>`: appends `done`; prints `Marked 12 done (not audit-clear until the next audit). Next: audit`. `remediation waive <item|--album A> --reason TEXT`: records an item as accepted-as-manual residual (not fixed, deliberately left); it is counted separately from fixed items in `report` and `status`. The next `audit` verifies against remote dates: items still wrong reappear with `Still wrong on remote: 1985 Beach/IMG_9 (remote 2026-10-16, target 1985-06). Not marked done.` Exit: worklist is a file, usable across sessions.

| Error | Message | Exit path |
|---|---|---|
| rclone `lsjson` fails | `Could not list remote 'gphotos:': <reason>. Run: gphotos-organizer setup-rclone. Nothing was changed.` | setup-rclone |
| No uploads yet (empty) | `Remote has 0 items under the configured path. Nothing to audit.` | upload |
| Takeout dir missing | `No Takeout directory at X. Request an export at takeout.google.com (Google Photos), then rerun with --takeout PATH.` | request export |
| Album coverage `unobservable` | `Cannot call this album clean: coverage unobservable. Use a Takeout audit: gphotos-organizer audit --source takeout --takeout PATH` | takeout |
| Remote-only items (no local match) | listed in report, not auto-flagged | n/a |
| Unknown strategy | `Unknown strategy 'foo'. Available: webui, trash-reupload (and unofficial-gptk if enabled)` | pick one |
| Strategy lacks capability | `Strategy 'trash-reupload' needs a pilot-tested plan (Story 9.6 gate) ... Falling back to: webui` printed, never silent | webui |
| `remediation done` for unknown item | `No worklist item 'X'. List: audit --plan --list` | list |

### S9. `status` (single "where am I")

```
gphotos-organizer status
Stage                Done     Total    Note
index                17,145   17,145
analyze              12,000   17,145   5,145 pending; 37 failed -> errors.jsonl
fuse                 12,000            current for the 12,000 analyzed
review file          0        35       35 undecided (parked: 0)
review album         0        137      137 undecided
review placeholder   0        31       albums with Suspect files; 14,812 files remaining (group decisions)
plan                 0
write                0        read-back OK 0
upload               604 albums uploaded_unverified (not audited)
Next: gphotos-organizer analyze      (5,145 files still lack evidence, so decisions made now may change; to review anyway: gphotos-organizer review next)
```

`status --explain [reverse|vocabulary|tiers]` prints the reversal map, vocabulary and confirmation tiers from S12. Empty state (fresh DB): `Nothing indexed yet. Next: gphotos-organizer index`. Errors: drive unmounted is a warning line, not a failure (status needs the databases, `pipeline.db` for stage counts and `state.db` for write state, not the drive); DB missing -> `No pipeline database at DATA/pipeline.db. Next: gphotos-organizer index`. Exit: always exits 0 with a `Next:` line.

`status` Next: is the first rule that applies: (1) a drive or database problem: its fix command; (2) `analyze` incomplete, meaning pending files or files whose failure is retryable: `analyze` (or `analyze --retry-failed` when only retryable failures remain), with the review command named in the same line; a file that failed again on its retry with the same error is *permanently failed*, is reported in the Note column (`37 failed -> errors.jsonl`) and never keeps this rule alive; (3) `fuse` older than the last analyze: `fuse`; (4) undecided album, file, audit or year_precision items: `review next`; (5) only placeholder items undecided: `review list --source placeholder --by album` (this rule comes before the plan rules, and `review next` prints the same `Only placeholder items remain` line before any `All N decided` line, S3); (6) no plan, or a stale plan: `plan`, with parked leftovers named as an alternative in the same line (`6 items parked; to revisit: review next --state parked`), never as the primary command, so Next: lines cannot loop through leftovers; (7) a plan not applied: `fix-metadata --apply --plan ID`; (8) uploads not audited: `audit`; otherwise `Nothing to do` (with the parked count if any). Terminal-reject items (a genuine placeholder, a cleared audit item, a cannot-link) are complete and never appear as leftovers. Denominators are per source (`review file 0 of 35`); placeholders count albums decided and files remaining, never 15,000 rows.

### S10. Long-running stages (condensed)

Sample (`analyze --plugins faces`):

```
Preflight: drive OK; models: faces cached (310 MB); cloud plugins: off
faces  [#####-----] 5,210/17,145  ETA 3h40m  cached 2,100 / computed 3,110
^C  Saved 5,210 results. Resume: rerun the same command (5,210 files already done).
```

Acceptance bullets in section 3 (UX-40s). Resumable by file hash; per-file failures recorded to `errors.jsonl`, skipped, retried with `--retry-failed`; end summary `Processed N of M; K failed; rerun to continue`. Model download failure: plugin disabled for the run, others continue, retry command printed. Cloud plugin without `--allow-cloud`: `Plugin 'era-llm' sends images to <provider>. Not run; pass --allow-cloud to enable.` Exit: every run ends with a summary and a `Next:` line. Ctrl-C exits 130 after printing the saved count and the resume line; waits that are designed to be interrupted (the S7 quota wait, `backup fsck` waiting for an unmount) exit 0.

### S11. Non-interactive outputs (condensed)

`DATA/remediation/webui-1985-Beach.md` sample:

```
# 1985 Beach - fix dates in Google Photos (12 items)
Target: 1985-06..1985-08. Search hint: album "1985 Beach", uploaded 2026-10-14.
Group A (select all, Edit date & time -> 1985-07-01): [ ] IMG_0042.jpg (remote 2026-10-16) [ ] IMG_0043.jpg ...
When done: gphotos-organizer remediation done --album "1985 Beach"; then audit.
```

Run report (`report`): names redacted by default, counts per plugin, confidence histogram, anchor error by decade, quota events; ends with `Next:`. Logs: JSONL, `run_id` bound, paths yes, person names no.

### S12. Cross-cutting rules: confirmation tiers, reversal map, vocabulary, help and completion

**Confirmation tiers** (one rule, one helper, Story 1.13 `pipeline/confirm.py`; every destructive or hard-to-reverse command uses it, so no command invents its own prompt):

| Tier | Meaning | Confirmation | Commands |
|---|---|---|---|
| T0 | Read-only or dry-run | none | every command without `--apply`; `status`, `audit`, `report`, `census`, `backup check` |
| T1 | Immediate: appends one record or does a small local write, undone by one named command | none; the result line names the undo | single-item `review accept|reject|skip|set <id>` and labeling a cluster or face by id (`review undo-last`), `people add`, `people edit` (`people.toml.bak`), `remediation done|waive` (re-run `audit`), `models fetch` (nothing to undo) |
| T1a | Preview first: bulk or file-touching, undone by one command | dry-run by default, `--apply` commits | `review import`, group decisions (`review confirm-genuine|confirm-placeholder`), `review set <album> --offset|--date`, `review reject <Accepted cluster>`, `recover --quarantine`, `anchors pin-album` (`anchors exclude FILE`) |
| T1+ | Overrides a safety rule; journaled with the rule's name | the explicit override flag and a one-line loud notice; **the refusal or dry-run that precedes it prints the exact flag, so that output is the preview** (a single `review set` has no separate dry-run) | `--force-guard`, `--prefer-import`, `--include-weak`, `--unviewed`, `plan --allow-year-precision --album ID` |
| T2 | Writes files or sends them to Google; reversible only in part or with effort | typed token (below) | `fix-metadata --apply`, `undo --run R --apply`, `placeholders revert --apply`, `upload --apply`, `upload --allow-unaudited` |
| T3 | Destroys a safety net or overrides a safety gate | typed token, plus a precondition the command checks first | `prewrite purge` (run must be `Read-back OK`), `undo --force` (modified files), `deny release ALBUM` (zero Needs review/Conflict decisions), `upload --i-verified-trash ALBUM` (the audit-coverage rule is the album's only failing gate) |

Two flows that had no drawn screen:

```
$ gphotos-organizer anchors pin-album "Trip 1996" --trusted
Dry run: 212 files in 'Trip 1996' would become anchors (source=owner_album); pinned anchors raise calibration weight.
Apply: gphotos-organizer anchors pin-album "Trip 1996" --trusted --apply     (undo per file: anchors exclude FILE)

$ gphotos-organizer placeholders revert --album A7
Dry run: 380 files selected for revert; 12 weak-evidence files listed but not selected (Make present, no folder-date match).
Apply: gphotos-organizer placeholders revert --album A7 --apply   (to include the 12: add --include-weak; prints "Override: --include-weak (weak evidence). Journaled.")
```

The typed token is a **count taken from the summary, never a value that is on the command line**, accepted with or without a thousands separator (`1,214` and `1214` both match, because the summary prints the separator), and the prompt does not print it: the preceding summary prints it once (`About to write to 1,214 files across 88 albums ...`) and the prompt names only what to count (`Type the number of files to write to continue:`). The counts are: files to write (T2 `fix-metadata`, `undo`), albums to upload (T2 `upload`), snapshot files to destroy (T3 `prewrite purge`), files to overwrite (T3 `undo --force`), and the album's file count (T3 `deny release ALBUM`, `upload --i-verified-trash ALBUM`). An id the operator typed as an argument (plan id, run id, album id) is never the token, because the prompt would then be answerable by copying the command line. Collisions are data-dependent (an album count can equal a number in argv), so a command supplies an ordered list of candidate counts from its summary (files, then albums, for `fix-metadata`; albums, then files, for `upload`) and the helper uses the first one that is not an argv element; if every candidate collides it refuses cleanly (`Cannot confirm: the counts in the summary (212 albums, 7,757 files) both appear on the command line. Rerun without the numeric arguments. Nothing was changed.`, exit 1) instead of raising. This forces reading the scope and defeats a muscle-memory Enter, and it also defeats a copy-paste of the prompt itself. It does not stop a determined copy from the summary line above; the design protects against reflex, not against the sole operator. `--yes` supplies the token only when stdin is not a TTY, never skips preflight or preconditions, and is ignored with a notice on a TTY. The legacy upload loop, if ever reinstated, must pass `--yes` explicitly.

**Reversal map** (printed by `status --explain reverse`, linked from every `--help` epilog, and named in each T2/T3 confirmation line):

| I did | Reverse it with | It does NOT reverse |
|---|---|---|
| a review decision | `review undo-last` (the last non-retracted decision or batch; `--n N` for more), or decide again (latest wins); EXIF writes use `undo --run`, not this command | anything already written to files |
| `review import --apply` | `review undo-last --import` (retracts that import's lines) | EXIF writes made after it |
| a group decision | `review undo-last` (one step for the whole group) | EXIF writes made after it |
| `fix-metadata --apply` (run R7) | `undo --run R7` (dry-run first; read-back checked; a review decision is reversed by `review undo-last`, not by this command) | a file damaged by an interrupted write; use `prewrite restore --run R7 --file PATH` |
| `placeholders revert --apply` | `undo --run R<n>` (the revert is a journaled run); original pre-placeholder dates were overwritten by the legacy tool and cannot be restored by anything | n/a |
| a damaged or truncated file | `prewrite restore --run R7 --file PATH` (before `prewrite purge`), else the second-medium backup | n/a |
| interrupted write leftovers | `recover --list`, `recover --run R7` (journal), `recover --quarantine` (moves, never deletes; move files back by hand) | n/a |
| `prewrite purge` | nothing; this is why it is T3 | the snapshots are gone |
| `upload --apply` | nothing automatic; `audit` then `audit --plan` (Story 9.5/9.6 remediation) | uploaded items stay on Google until fixed or trashed in the web UI |
| `people edit` | `DATA/people.toml.bak` | n/a |
| `anchors pin-album --apply` | `anchors exclude FILE` (per file) | calibration already run on the pins |

**Vocabulary** (each word has one meaning; a test scans terminal and HTML output for cross-use). `DecisionStatus.Review` keeps its enum name, but every user-facing screen displays it as `Needs review`, so the command group `review`, the fusion outcome and the review state never share one bare word.

| Concept | Words shown | Never used for |
|---|---|---|
| Review state (a human decision) | `Accepted`, `Rejected`, `Skipped`, `Undecided`, each optionally followed by the per-kind meaning in parentheses (`Rejected (genuine)`); cluster status adds `Partly labeled: <name> (k of n)` and `Mixed names` | plan buckets, upload outcomes, ignored-entry reports (use Held, Blocked, Ignored) |
| Review leftover | `parked` (skipped, or rejected on a hold kind: not written, not uploaded, served again by `--state parked`); `cleared` (terminal reject: nothing more to do) | `Held` (plan), `Blocked` (upload) |
| Fusion outcome | `Anchor`, `Eligible`, `Needs review`, `Conflict`, `UserOverride` | review state |
| Plan buckets | `Held` (needs review, conflict, no write needed) | `Skipped`, `Blocked` |
| Upload outcome | `ready (would upload)` (gate line before consent), `ok (uploaded_unverified)` (rclone accepted it, not audited), `Blocked`, `not attempted`; counts read `21 albums uploaded_unverified, 2 Blocked` | `Skipped`, `Held`, `verified` |
| Write state | `NotWritten`, `Pending`, `Read-back OK` (enum `Verified`), `Mismatch`, `Reverted` | audit and upload claims, and any review-screen column or status (the cluster intents column is `Queued`) |
| Import and load housekeeping | `Ignored` (read but not applied: duplicates, torn lines, stale-run entries), `Not imported` (lost a conflict) | review state, plan buckets |
| Undo outcome | `restored`, `left unchanged` (file modified after the run); a review decision that is undone reads `back to accept` | review state |
| Backup | `attested` (a `backup verify` pass wrote the attestation), `stale` | write state, `verified` |
| Audit result | `Suspicious`, `Audit-clear`, `unobservable` | write state |
| Command names | `backup verify` is the only place bare `verify` is an action | state words |

**Vocabulary scan (UX-92), explicit rules.** The test (Story 1.13, `G/tests/test_labels.py`) runs over the golden output of every terminal screen and sheet template and fails on any of these; the only exceptions are lines listed in `G/tests/vocab_allowlist.toml` (screen name plus exact string), and a stale allow-list entry that matches no golden line also fails the test.
- V1. `Skipped` or `skipped` appears only on review screens: `review list`, `review next`, `review list --clusters`, the `review import` dry-run action column, the `All N items decided` line, the `status` review rows and the state word on sheets. Every other screen (plan, upload, undo, audit, backup, help) containing it fails.
- V2. The bare word `verified` or `Verified` (word boundary) fails everywhere in output; `uploaded_unverified`, `backup verify` and `--i-verified-trash` are not matches. The enum name `Verified` is displayed as `Read-back OK`.
- V3. Bare `Review` as a fusion outcome fails, and so do the lowercase outcome forms `needs review` and `conflict` (outcomes print capitalized, `Needs review`, `Conflict`); the allow-list holds exactly the `Review` help panel name and the item header `Review file 11 of 172`.
- V4. `Held` in upload output or `Blocked` in plan output fails; `Held` and `Blocked` on any review screen (`review list|next`, the import dry-run, the `All N items decided` line, the verb table) fail too (use `parked` and `cleared`).
- V5. `Ignored`, `Not imported`, `restored`, `left unchanged` or `Pending` in a review-state cell or the cluster intents column fails (`review undo-last` prints `back to accept`, not `restored`).

**Help and discoverability.** `gphotos-organizer --help` groups commands into panels in workflow order (Story 1.12), each command in exactly one panel (Safety precedes Write because the `fix-metadata --apply` preflight requires `backup verify`), and the epilog begins `Where am I? gphotos-organizer status` and `Reverse something? gphotos-organizer status --explain reverse`:

| Panel | Commands |
|---|---|
| Setup | `people`, `models`, `anchors`, `setup-rclone` |
| Analyze | `scan`, `index`, `analyze`, `fuse`, `census`, `placeholders` |
| Review | `review`, `status` |
| Safety | `backup`, `prewrite`, `recover` |
| Write | `plan`, `fix-metadata`, `undo` |
| Upload | `upload`, `deny`, `update-album` |
| Audit | `audit`, `remediation`, `report` |
| Legacy | `infer` (until Task 10.5c) |

Naming decision: `plan` and `fix-metadata` stay a pair (`plan` writes the plan, `fix-metadata --apply --plan ID` writes the files); renaming the verb would touch every `Next:` line and the legacy muscle memory for no new capability, so the help panel text for `fix-metadata` reads `Apply a plan: write EXIF dates (the pair of plan)` and `plan` ends with `Apply with: gphotos-organizer fix-metadata --apply --plan ID`. Aliases that exist only for migration (bare `review --severity ...`, bare `report --out ...`) print a one-line deprecation notice on **stderr** naming the new command; stdout and the exit code are byte-identical to the new form, so a `--json` pipe keeps working. `--json`, `--source` and `--album` mean the same on `review list|next`, `people list`, `placeholders list|summary`. Shell completion (`gphotos-organizer --install-completion`) completes review item and cluster ids (`C12`, `C12/F3`), `--name` values from `people.toml`, album ids (with the title as the completion hint, local terminal only), plan and run ids; completers read small files only and never open the databases.

**Usability pass (Story 7.5, before the review flow is built).** A timed operator run on a fixture corpus (20 synthetic clusters, 50 date items, 3 placeholder albums) with a throwaway sheet and the real `decisions.py` log, recorded in ADR-009: seconds per cluster label, seconds per file item, terminal/browser switches per 10 labels, and where Tyler hesitated. **Limitation, stated up front:** the clusters do not exist yet when the pass runs (faces are built later), so the pass uses synthetic faces and measures the mechanics (clicks, switches, seconds per decision), not the time it takes to judge real aging faces. Pre-agreed pass thresholds (INFERRED, owner may change): at most 25 s per cluster label with the index and `--open`, at most 15 s per file item, at most 2 mode switches per 10 labels, at most 120 s per placeholder album (open the sample sheet, look, mark exceptions, Export, `review import` dry-run and `--apply`), and at most 3 `review import` runs per 10 cluster labels when exports are batched with `--glob`. They are judged against total effort, not per item: 212 clusters x 25 s = 5,300 s, 172 items x 15 s = 2,580 s, 31 placeholder albums x 120 s = 3,720 s, about 42 switches for 212 labels and about 64 import runs unbatched (about 22 batched); the ADR records those projections and the owner accepts or changes them. The Story 7.3 owner pass on real clusters also records how often the typed-name dialog fires on the real cluster-size distribution (`TYPED_NAME_SHOWN_FRACTION`); more than 20% of clusters is an owner decision point. A miss changes the Story 7.2/7.3 acceptance criteria before they start. The same three quantities are re-measured on the first 20 real clusters in the Story 7.3 owner labeling pass; more than 1.5 x a threshold there is an owner decision point.

## 3. UX acceptance criteria

Each is human-testable. IDs for traceability.

**Task completion**
- UX-01: Adding one person with a birth date takes 1 command and prints a confirmation row plus a `Next:` line.
- UX-02: Labeling a cluster takes at most 2 steps once the cluster pass exists: `review sheet --cluster CID --open` (or a click from the index), then one `review accept CID --name` command; no step requires locating a file by hand.
- UX-03: Resolving one low-confidence file takes 1 command (`accept`, `set`, `reject`, or `skip`) after `review next`; no other lookup is needed because the item screen shows file, album, candidate, confidence, voters, guards, and the next commands.
- UX-04: A constant-offset album correction takes 1 dry-run plus 1 `--apply` command and shows a before/after preview of at least 5 rows.
- UX-05: From a populated review list, Tyler can go review -> plan -> apply -> audit following only the printed `Next:` lines, never consulting docs.
- UX-06: In the HTML sheet, deciding a card takes 1 keystroke (`a`/`r`/`s`) and exporting takes 1 button press plus 1 `review import` command.

**Safety and trust**
- UX-10: Every mutating command (`fix-metadata`, `undo`, `review import`, `upload`, remediation apply, bulk `set`) writes nothing without `--apply`, and each dry-run ends with the exact `--apply` command.
- UX-11: `fix-metadata --apply` requires typing the number of files to be written, which the prompt does not print (or `--yes` when non-TTY); pressing Enter alone writes nothing.
- UX-12: Every EXIF write is undoable by `undo --run <id>`; the apply summary prints that command.
- UX-13: A date that equals today or lies in the future is refused by `review set` unless explicitly skipped; the message names the reason.
- UX-14: No inferred date is written silently: each review item and each plan row shows confidence and the voters that produced it.
- UX-15: `upload` refuses albums with unresolved dates and the message names the album, counts, and `review next`.
- UX-16: `status` shows uploaded albums as `uploaded_unverified (not audited)` until an audit confirms them; the word `Audit-clear` appears only after audit, and write state is shown as `Read-back OK`, never as a bare `verified` (S12 vocabulary).

**Errors: no dead ends**
- UX-20: Every error message states what happened, why, and an exact next command; it also says whether anything changed. Verified by a test that lints all `fail()` call sites for a non-empty hint.
- UX-21: Drive-unmounted error shows the mount path and the rerun command, appears before any cache or file is touched, and exits non-zero.
- UX-22: Stale plan shows exactly `Plan is older than the latest analysis. Regenerate: gphotos-organizer plan`.
- UX-23: Unknown ids in `review` commands and in `review import` name the id and the command to list valid ids; the other entries in an import still apply.
- UX-24: Quota (429) message shows albums done, resume time with countdown, and the Ctrl-C-and-rerun alternative; Ctrl-C during the wait exits cleanly with progress saved.
- UX-25: A failed model download disables only that plugin for the run and prints `gphotos-organizer models fetch <plugin>`.
- UX-26: Cloud plugin without `--allow-cloud` is skipped with a message naming the provider and the flag; no image leaves the machine.
- UX-27: A torn `decisions.jsonl` tail is reported, the valid prefix loads, and no earlier decision is lost.
- UX-28: Any state with no items (no clusters, nothing to review, nothing to plan, nothing to upload, empty remote) prints a specific message with the next command rather than an empty table.
- UX-29: "No dead ends": every command in the inventory ends with a `Next:` line or an explicit `Nothing to do` line; checked by running each command on a fixture corpus (Story 10.5).

**Interruption and resume**
- UX-40: Ctrl-C during `analyze`, `fix-metadata --apply`, `upload`, or `review` prints how many results were saved and the rerun command, and loses no more than the in-flight chunk or command.
- UX-41: Rerunning `analyze` reports `N cached / M computed` and skips cached files; progress bars show ETA.
- UX-42: `review next` after an interruption starts at the first undecided item.
- UX-43: Per-file failures do not abort a run; the summary gives the failed count, `errors.jsonl`, and `--retry-failed`.

**HTML sheets: accessibility and offline**
- UX-50: The sheet is fully keyboard-operable with shortcuts on or off: every control of every card is in the natural Tab order (S4 keyboard model, UX-85), `a`/`r`/`s` decide (only while focus is inside a card, UX-84), arrow keys move between cards as an enhancement only, `?` shows keys, Esc closes the key map, Tab never gets trapped, and the page scrolls normally when no card is focused.
- UX-51: Every control is a native `<button>`/`<input>`; focus ring is visible (3:1 contrast, not removed).
- UX-52: Every `<img>` has a non-empty alt by sheet kind: cluster `Face crop from <album>, estimated <year>`; date-group `Photo <file name> from <album>, current date <date or none>`; placeholder `Photo from <album>, EXIF date <YYYY-MM-DD HH:MM:SS>`; decorative elements have `alt=""`.
- UX-53: Text contrast >= 4.5:1, UI components and focus indicators >= 3:1, in both light and dark (`prefers-color-scheme`); computed by test from the stylesheet pairs.
- UX-54: Decision state is shown by word and icon, not color alone (`Accepted`/`Rejected`/`Skipped`/`Undecided`).
- UX-55: One `<h1>`, a heading per section, `<main>`, `lang="en"`, descriptive `<title>`, `aria-live="polite"` decision counter; interactive targets at least 24 px; animation disabled under `prefers-reduced-motion`.
- UX-56: The sheet loads with no network (no `http(s)` URLs other than in documentation text), works from `file://`, contains `<meta name="robots" content="noindex">`, and is written under `DATA/`, not the git tree.
- UX-57: With JS disabled, every card still shows the equivalent terminal command and a banner explains what is unavailable.
- UX-58: Missing thumbnails (drive unmounted) render the alt text in a fixed-size tile; the rest of the page works.
- UX-59: A reload does not lose in-page decisions (localStorage, keyed by sheet id plus generation hash, UX-80), and if storage is unavailable a visible note says decisions are lost on close and to export first.

**Review at scale, navigation and cluster-sheet semantics (added by the 2026-10-16 triad repair pass)**
- UX-70: `review next` and `review list` accept `--source`, `--album`, `--severity`, `--order`, `--json` with identical semantics; `--source placeholder` defaults to `--order gain`; `--by album` collapses to one row per album.
- UX-71: `review next --open` and every `review sheet` form accept `--open` and print the `file://` URL; no step requires finding a sheet file by hand.
- UX-72: `review sheet --clusters` writes an index of every cluster with status word and expected gain; each cluster sheet links Prev, Index, Next and Next unlabeled.
- UX-73: group decisions (album or signal scope) show a dry-run preview of count plus five rows, refuse `--apply` over 50 files for a selection with no generated sample sheet (unless `--unviewed`), and are undone by one `review undo-last`.
- UX-74: `review sheet --placeholders` shows a deterministic, stratified sample (default `max(48, ceil(4 x sqrt(files)))` capped at 200, seed 7, any `--seed` reshuffles) with the current EXIF date and time, class and signals, an EXIF-date histogram of the whole selection, group controls and per-card exceptions.
- UX-75: no cluster or date-group sheet page holds more than 100 cards by default (max 200); only the requested page's thumbnails are generated, with a progress line; a 9,161-file album yields 92 date-group pages; a placeholder sample sheet is never paginated.
- UX-76: a cluster sheet shows 24 faces and `Show next 24`; `--page N` and `--all` reach the rest; `review accept` prints how many faces it labels and how many were viewed.
- UX-77: `--name` resolves against `people.toml` (case-insensitive, aliases); a near miss is refused with `Did you mean ...`; `--new-person` is the only way to create a name through `review`; the sheet Name field is a closed `<select>` of known names (no free typing).
- UX-78: `review merge` and `review split` print the queued-intent count and the cluster-pass cost; `review list --clusters` shows a `Queued` column.
- UX-79: on a cluster sheet, the card buttons `Same person` / `Not this person` / `Unsure` act on the face (`face_member` accept/reject/skip) and only the cluster controls label; the cluster `accept` exports `name`; face ids are `C12/F3` with a canonical `face_id`; an import against a different `cluster_run_id` ignores `cluster_label` entries, applies `face_member` entries by canonical `face_id`, and says so.
- UX-97: for each kind in the S3 verb table, `accept`, `reject`, `skip` and `set` do exactly what the table says (including whether the reject is terminal or parks the item) and the `Next:` line shows only that kind's verbs; a verb not defined for a source is refused with the right verb named.

**Triad repair pass 2 additions (2026-10-16)**
- UX-98: every T3 command (`prewrite purge`, `undo --force`, `deny release ALBUM`, `upload --i-verified-trash ALBUM`) asks for a count that is not in argv; a test passes the album id as the answer and it is refused.
- UX-99: `gpo-decisions/2` carries `decided_at` on every item and `group_id`/`outcome` on group entries; two placeholder groups with the same action both import; a sheet decision older than a terminal decision is reported as `Not imported`, a newer one is appended.
- UX-100: terminal and no-JS card commands that take a `C` id accept `--run`, and refuse with the renumbering message when it differs from the current cluster run; an import from a stale run ignores `cluster_label` entries and applies `face_member` entries by canonical `face_id` (an entry whose face no longer exists is ignored); a merged or split cluster's status after renumbering is derived from its members' labels (`Accepted`, `Partly labeled`, `Mixed names`, Undecided).
- UX-101: a `face_member reject` after a cluster `accept` removes that face's label; `review reject C12` on an Accepted cluster previews the label count first; `review split` is two face rejects under one batch and `review merge` is one `cluster_link` line.
- UX-102: `review undo-last` retracts the last non-retracted decision or batch (no "session"), prints what it will undo, supports `--n N`, `--list` and `--import`.
- UX-103: the placeholder sample scales with group size, is a single unpaginated page of at most 200 cards, and is stratified by exact EXIF timestamp; the sheet and the terminal dry-run show the timestamp histogram, `--except IDS` (`P` ids) exists on both terminal group commands, excepted files stay Suspect and Undecided, and the import dry-run prints group lines.
- UX-104: review progress denominators are per source; unfiltered `review next` never serves per-file placeholder items; `review next --state parked|skipped|rejected` resurfaces parked items and the `All N decided` line names them and prints `plan` as the primary Next:; each command form is labeled immediate or preview; `status` has per-source rows and a placeholder row.
- UX-105: sheet exports are named by sheet id, run and timestamp and `review import --latest|--glob` resolves them at dry-run time and the printed `Apply:` command pins the file names (`--latest --apply` is refused); `review import --apply` regenerates the index; `--open` failure prints the URL and exits 0; an interrupted `--all` resumes.
- UX-106: the date-group `Set date` field validates format, today/future and birth in JS (with the parsed precision shown) and the same checks run at import.
- UX-107: with shortcuts off every card decision is reachable and operable with Tab, Shift+Tab and Enter/Space alone: at most 5 Tab stops per card on cluster and placeholder sheets and 6 on date-group sheets (3 decision buttons, `Set date` where present, `Enlarge`, `Next undecided card`), and `Next undecided card` moves focus to the next undecided card's first decision button.
- UX-108: decision buttons are `aria-pressed` toggles inside a `role="group"` that is the sole child of an `<li>` (no `role` on the `<li>`), the group's description states that the choices are mutually exclusive, no composite role is claimed, Export uses `aria-disabled` plus a described-by text while empty, and the visible counter and the live text are separate elements.
- UX-109: fields have visible labels and the Set date error is linked with `aria-describedby`; the Name field is a closed `<select>`.
- UX-110: at 200% zoom and with WCAG 1.4.12 text spacing nothing is clipped or overlapped and targets stay at least 24 px.
- UX-111: `status` Next: follows the eight-rule order in S9 (analyze before review while analyze has pending or retryable files; permanently failed files never keep it alive; only-placeholder before plan; parked leftovers are an alternative on the `plan` line, never the primary command), so a user who follows only Next: lines reaches `Nothing to do`.
- UX-112: a failing `backup fsck` privilege (no read access to the device) prints the sudo route and the `--from-output` route and never prompts for or stores a password.

**Triad repair pass 3 additions (2026-10-16)**
- UX-113: review item ids are typed and stable (`F`, `A`, `Y`, `U`, `P`, `C`, `C/F`); a bare number is refused with the prefixes that exist; aliases are allocated once per stable key and never reused; every log line and export entry carries `item` and `item_key`; after a re-fuse a decision still attaches to the same item and a line whose alias and key disagree is ignored.
- UX-114: each item kind declares whether its reject is terminal or holds; the fold, `review list|next --state`, the `All N decided` line, `status`, the upload gate and the import conflict rule read that one attribute; `skip` and hold-kind rejects are parked, terminal rejects are cleared; `Held` and `Blocked` never appear on review screens.
- UX-115: a group decision is materialized as per-file owner records with one `group` line; exceptions of same-`group_id` same-`outcome` lines are united; stale exceptions are dropped; files added after the decision stay Undecided; overlapping groups resolve per file by latest record; a placeholder sample sheet is one page.
- UX-116: the S4 control table maps every sheet control to exactly one export `kind`/`action`; every export kind in S5 has a producing control, including `album_date` (album block and `Offset`), `year_precision` and `audit` cards.
- UX-117: the preflight fsck check reads a recorded clean result no older than 24 hours and never runs fsck or asks for sudo; the periodic fsck pauses the run at an album boundary with a resume line.
- UX-118: `upload --apply` prints `Gate:` lines (`ready (would upload)`, `Blocked`) before the typed confirmation and `ok (uploaded_unverified)` only after it; `review import --latest` can only preview, and its printed Apply command names the files.

**Sheet state and WCAG 2.2 additions**
- UX-80: the localStorage key contains a content/generation hash; a regenerated sheet with different content does not inherit old decisions, and older ones are offered for export or discard.
- UX-81: pressing a decision key again on a decided card returns it to Undecided; `u` undoes the last decision; `Clear all` asks through a native `<dialog>`.
- UX-82: cards already decided in `decisions.jsonl` at generation time show `In log: <state> (<date>)`; Export records `Exported N at <time>`; `Mark as imported` clears local decisions.
- UX-83: if localStorage is unavailable or throws a quota error, a banner appears and Export stays available; an in-memory decision is never dropped.
- UX-84 (WCAG 2.1.4): single-letter shortcuts act only while a card has focus, a visible checkbox turns them off, and every shortcut has a visible button equivalent.
- UX-85: every card control is in the natural Tab order (no roving tabindex, no `tabindex="-1"` on card controls); arrows, Home, End, PageUp and PageDown move focus to the neighbouring card's same control without wrapping and are an enhancement, never the only route; they are intercepted only while focus is inside a card and not in a text field; focus stays on the decided control and is never lost to a re-render.
- UX-86: the visible decision counter updates on every change; a separate visually hidden `role="status"` region updates at most every 1.5 s and speaks every fifth change and at zero left.
- UX-87: `Enlarge` opens a native `<dialog>` with a 1024 px image, Esc closes it, and focus returns to the card.
- UX-88 (WCAG 1.4.10, 2.4.11): at 320 CSS px the sheet has one column and no horizontal scroll, and a focused card is never covered by the sticky header (sticky only at viewport height 600 px or more, `scroll-padding-top` set).
- UX-89: the contrast test (UX-53) also computes the focus ring, state icons, badges and the dialog backdrop in both themes.

**Safety, vocabulary and help**
- UX-90: every T2/T3 command confirms through the one tier helper (counts accepted with or without a thousands separator; a token that collides with argv falls back to the next candidate count and, if none is free, refuses cleanly instead of raising); the prompt never prints the expected token; the token is a count that is not present in argv (a plan, run or album id on the command line is rejected as the answer); `--yes` works only without a TTY and never skips a precondition.
- UX-91: `status --explain reverse` prints the reversal map, and each T2/T3 confirmation summary line names its reversal command.
- UX-92: the vocabulary scan enforces rules V1 to V5 of the S12 table (`Skipped` only on review screens, bare `verified` nowhere, `Needs review` for the fusion outcome, `Held`/`Blocked` kept to plan/upload) over the golden output of every screen and sheet template, with an explicit allow-list file whose stale entries also fail.
- UX-93: `--help` shows panels in the order Setup, Analyze, Review, Safety, Write, Upload, Audit, Legacy; each command appears in exactly one panel; the epilog starts with the `status` pointer.
- UX-94: alias deprecation notices go to stderr only; stdout and exit code equal the new command's.
- UX-95: shell completion offers review item and cluster ids, people names, album ids, plan and run ids without opening a database.
- UX-96: the Story 7.5 usability pass is recorded with the measured quantities (seconds per cluster label, per file item and per placeholder album, switches per 10 labels, import runs per 10 labels), states that it ran on synthetic faces (mechanics, not judgment time), projects totals for 212 clusters, 172 items and 31 placeholder albums, and is within the pre-agreed thresholds or the 7.2/7.3 criteria were changed because of it; the first 20 real clusters are re-measured in Story 7.3.

**Language and consistency**
- UX-60: Terminal output contains no emoji; success/failure is carried by words (`ok`, `Blocked`, `failed`), not color alone; honors `NO_COLOR` and non-TTY (plain lines, no live bars).
- UX-61: Person names do not appear in `DATA/logs/*.jsonl` or the default run report.
- UX-62: Terminology is consistent across terminal and HTML, per the S12 vocabulary table: `Accepted/Rejected/Skipped/Undecided` for review state only; `Anchor/Eligible/Needs review/Conflict/UserOverride` for fusion decisions (enum `Review` displayed as `Needs review`); `NotWritten/Pending/Read-back OK/Mismatch/Reverted` for write state (a journal join, never a decision status; enum `Verified`); `Held` and `Blocked` instead of `Skipped` in plan and upload output.

## 4. Exit-path and error-state coverage check

| Flow | Exit path | Error states | Gap |
|---|---|---|---|
| S1 people | yes (command returns, atomic write) | yes (5) | none |
| S2 cluster labeling | yes (atomic lines, relabel/reject/skip) | yes (8) | none |
| S3 date review | yes (Ctrl-C summary, skip, `Next:`) | yes (11) | none |
| S4 HTML sheet | yes (close tab; nothing written to pipeline) | yes (11) | none |
| S5 import | yes (dry-run default) | yes (8) | none |
| S6 plan/apply/undo | yes (typed-count confirm can be abandoned) | yes (9) | none |
| S7 upload/quota | yes (interruptible wait) | yes (5) | none |
| S8 audit/remediation | yes (worklist is a file) | yes (7) | none |
| S9 status | yes (always exit 0 + Next) | yes (2) | none |
| S10 long runs | yes (resume line) | yes (listed) | none |
| S11 non-interactive | n/a | n/a | none |
| S12 cross-cutting + review at scale | yes (dry-run default, reversal map) | yes (group, name, tier errors) | none |

Caveats carried from inputs (not design gaps): terminal inline-image support is unknown (design does not depend on it). Commands introduced by this design now have plan stories with acceptance criteria (2026-10-16 repair pass): `people edit` (Story 4.5), `review undo-last`, `--force-guard`, album `--offset` on `set` (Story 7.2), `--prefer-import` (Story 7.4), `recover` (Story 1.10 list/quarantine, Story 8.3 journal reconcile), `models fetch` (Story 4.2), `--retry-failed` (Story 2.5 for `analyze`, Story 8.4 for `fix-metadata --apply`), `audit --plan --list` (Story 9.5). Plan additions with user-visible surfaces not drawn above: `backup verify|check|fsck|canary` and `prewrite snapshot|restore|purge` (Story 8.8), `census` (Story 5.6), `placeholders sample|label|precision|summary` (Stories 1.9, 8.7), `audit spotcheck` and `--i-verified-trash` (Stories 9.9, 9.2), `review sheet --album|--group|--clusters|--placeholders`, pagination, index, `--open`, `Show next 24`, enlarge dialog (Story 7.3), sheet state and WCAG behaviors and the `gpo-decisions/2` export (Story 7.4), `review confirm-genuine|confirm-placeholder` and group decisions (Story 7.6), `review next|list` filters and `--open` (Story 7.2), name resolution, `C12/F3` face ids and queued-intent display (Story 4.5), help panels, completion and alias notices (Story 1.12), confirmation tiers, `status --explain` content and vocabulary labels (Stories 1.13, 10.3), `remediation waive` (Story 9.5), the usability pass (Story 7.5), the `report` group (Stories 10.1, 5.5), `placeholders scan|list|confirm-genuine|revert` (Stories 1.9, 8.7), `review list --source year_precision` (Stories 7.2, 8.4), `fix-metadata --apply` on exFAT requires `--workdir` (Story 8.4; error text: `Source is on exFAT: in-place writes are refused. Rerun with --workdir /tmp/gpo-work. Nothing was changed.`), and the interim `Legacy writer disabled` error on `fix-metadata --apply` before Story 8.4 lands (Story 1.11). Added by triad repair pass 2: `review next|list --state`, `review import --latest|--glob`, `review confirm-genuine|confirm-placeholder --except`, `--run` on cluster commands (Stories 7.2, 7.4, 7.6, 4.5), `cluster_link` and `decided_at`/`group_id` in the log and export (Stories 7.1, 7.4), `backup fsck --from-output` (Story 8.8), and the status Next: rule (Story 10.3). Added by triad repair pass 3: typed stable item ids and `item_key` (Stories 7.1, 7.2, 7.4, 7.6), the terminal-or-hold reject attribute and `parked` state (Stories 7.2, 10.3), materialized group decisions and single-page placeholder sheets (Story 7.6), the sheet control table, keyboard model and `Next undecided card` (Stories 7.3, 7.4), `review import` pinning and `--archive` (Story 7.4), tier T1/T1a split and count-token fallback (Story 1.13), the recorded-fsck preflight (Stories 8.4, 8.8).
