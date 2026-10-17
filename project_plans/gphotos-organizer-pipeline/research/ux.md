# UX research: human-in-the-loop review surface

Date: 2026-10-16. Sole user: Tyler (CLI). Scope: labeling face clusters, birth dates, low-confidence date review, EXIF write confirmation, manual Google Photos web-UI remediation.

Evidence labels: VERIFIED = opened/ran in this repo. UNVERIFIED = from background knowledge, URL cited but not fetched in this session (tool budget was 5 calls). Check before relying on them.

## Recommendation (minimal review surface)

Hybrid, with a file as the contract:

1. `review/decisions.jsonl` (append-only, one line per decision: `{item_id, kind, action: accept|reject|set|skip, value, ts}`) is the single source of truth. Everything else is a view over it.
2. Terminal-only for the small, high-value inputs: birth dates (a `people.toml` or `gphotos-organizer people add NAME --born YYYY-MM-DD`) and the confirm-before-write gate (`--apply` plus a rich summary table).
3. One generated static HTML contact sheet per face cluster and per low-confidence date group, for the visual judgment calls (is this the same person? is this 1974 or 1984?). Static, offline, no server. It cannot write files, so Tyler either (a) clicks accept/reject and the page exports a `decisions.json` download that `gphotos-organizer review import` merges, or (b) reads the sheet and answers in the terminal with `review accept C12 --name "Grandma Ruth"`. Build (b) first; it is a day-one fallback and (a) is a thin layer on top.
4. Do not build a server/web app (out of scope in requirements.md: "hosting a photo web UI").

Why not terminal-only: faces and scanned prints are a visual task. Rich cannot show images in most terminals reliably (kitty/sixel support varies; UNVERIFIED for Tyler's terminal), and labeling hundreds of clusters by typing paths into an image viewer is slow. Why not HTML-only: the date list and EXIF confirmation are tabular and fit the existing `review`/`status` commands.

## 1. Comparable flows

| Tool | Pattern worth copying | Pattern to avoid |
|---|---|---|
| Immich | People page: clusters shown as one face thumbnail; click to name; "merge people" is an explicit multi-select action; hide/unhide. Date edit: select assets, "Change date" dialog applies one date or a relative offset to the selection. https://immich.app/docs/features/facial-recognition (UNVERIFIED) | Requires running the server stack |
| PhotoPrism | "People" tab lists unnamed faces as suggestions; naming a face accepts it; separate "Review" queue for low-confidence items. https://docs.photoprism.app/user-guide/organize/people/ (UNVERIFIED) | Same server cost |
| digiKam | Face workflow has three buckets: Unknown, Unconfirmed (suggested), Confirmed; user confirms or rejects suggestions in bulk. Date correction via "Adjust Time & Date" with offset (add/subtract) and per-file preview table. https://docs.digikam.org/en/left_sidebar/people_view.html (UNVERIFIED) | Heavy desktop GUI |
| git (`add -p`, `rebase -i`, `status`) | Review a diff of proposed changes, accept/reject per hunk, nothing changes until an explicit apply; a plan file you can edit | n/a |
| Contact sheet (ImageMagick `montage`, Lightroom/Bridge) | Dense grid of thumbnails with a short caption; a human scans for the outlier far faster than reading a list. https://imagemagick.org/script/montage.php (UNVERIFIED) | n/a |

Distilled design: three states for every proposal (digiKam's Unknown / Unconfirmed / Confirmed maps to `pending / suggested / confirmed`), explicit merge action for split clusters (Immich), per-hunk accept (git), relative-offset date edits for a whole album (digiKam/Immich). The offset form matters here: a scanned album is usually wrong by a constant, and `fix-metadata` already has `--offset-seconds` (VERIFIED, `cli.py:320`).

Contact sheet content per cluster: up to ~24 face crops (sampled across estimated age, not just nearest to centroid, because embedding drift across decades is a stated rabbit hole), cluster id, member count, estimated year range, source album names as caption, and the outliers (farthest from centroid) first. Per date-review group: thumbnail, current folder date, inferred date, confidence, and which plugins voted (provenance is a stated success metric).

## 2. Mental models: dry-run/apply, progress, resumability

- Dry-run default, `--apply` to commit: already the repo convention (VERIFIED: `fix-metadata` and `upload` take `apply`, `cli.py:310`, `cli.py:383`). Keep it for every new write. Terraform plan/apply and `git add -p` are the closest analogues; the plan must be an inspectable artifact, not just logs.
- Make the plan a file: `plan.jsonl` of intended EXIF writes with `old_value`, `new_value`, `confidence`, `provenance`. `--apply` consumes the plan rather than recomputing, so what Tyler reviewed is what is written, and the old value doubles as the reversal journal required in requirements.md Risk Control.
- Progress: rich `Progress` bar per stage with ETA, plus a one-line "N cached / M computed" so Tyler sees the per-hash cache working during the overnight run. Stage-level resume is free if every plugin result is keyed by file hash (stated NFR). Print "resume: rerun the same command; N files already done" on start, not a bare spinner.
- Interrupt safety: write results in small committed batches (SQLite or JSONL append), catch KeyboardInterrupt, print a summary of what is saved. Ctrl-C must never lose the last hour.
- Review state also resumes: decisions are append-only, so `review next` always shows the first undecided item; later decisions on the same item win.
- `status` already exists (VERIFIED, `cli.py:452`); extend it as the single "where am I" screen: per stage counts, pending review count, next suggested command.

## 3. Accessibility of generated HTML

Single user, so target the sensible subset of WCAG 2.2 AA (https://www.w3.org/TR/WCAG22/ , UNVERIFIED) rather than a formal audit. It is cheap if baked into the template:

- Keyboard: every control a native `<button>`/`<input type=radio>`; no click-only divs. Grid of cards with roving focus: arrow keys move between cards, `a` accept, `r` reject, `s` skip, `?` shows the key map. Visible focus ring (WCAG 2.4.7; do not remove `outline`). No keyboard trap; an unfocused page must still scroll normally (2.1.1, 2.1.2).
- Alt text: each thumbnail gets `alt="Face crop from {album}, estimated {year}"` rather than empty; decorative elements `alt=""`. For family-photo review this also doubles as a text fallback if images fail to load from an unmounted drive (see section 4).
- Contrast: 4.5:1 for text, 3:1 for UI components and focus indicators (1.4.3, 1.4.11). State must not rely on color alone: accepted/rejected also shown with an icon and the word. Respect `prefers-color-scheme` and `prefers-reduced-motion`.
- Structure: one `<h1>`, a heading per cluster, `<main>`, `lang="en"`, sensible `<title>`. Use `aria-live="polite"` for the "12 decided, 40 left" counter. Buttons large enough to hit (2.5.8 target size 24 px minimum).
- Self-contained: embed thumbnails as relative paths to a local `thumbs/` dir (not base64 of full images; 17k originals would be huge) and keep the page JS-optional where possible (CSS-only layout; JS only for keys and export).
- Privacy (confidential data): write the sheet and thumbs under the local, git-ignored data dir beside the manifest; never into the dotfiles git tree. Add `<meta name="robots" content="noindex">` as a habit; no external CDN fonts/scripts (also keeps it working offline).

## 4. Error states and messages

Principle (Nielsen heuristic 9, https://www.nngroup.com/articles/ten-usability-heuristics/ , UNVERIFIED): say what happened, why, and the exact next command. Exit non-zero with a short rich panel; full traceback only under `--verbose`/in the loguru log.

| State | Detect | Message shape | Behavior |
|---|---|---|---|
| Drive unmounted | Check `source_root.exists()` and that it is non-empty before any stage; also before HTML open (thumbs on drive) | "Source drive not mounted: /run/media/tstapler/EE5B-3D9B. Mount it and rerun `gphotos-organizer <cmd>`. Nothing was changed." | Fail fast, before touching caches. Mid-run disappearance (OSError ENOENT/EIO): stop, flush cache, report last good file |
| Quota (HTTP 429) | Already implemented as `QuotaExceeded` in `uploader.py` (VERIFIED: raised at the rclone-output check, `uploader.py` ~line 115; not yet exercised against a real quota hit per requirements.md) | "Google Photos daily upload quota reached after N albums. Resuming at 00:05 Pacific (in 3h12m), or press Ctrl-C and rerun tomorrow; progress is saved." | Show countdown; manifest already makes rerun idempotent. Make the wait interruptible |
| Model download failure | Wrap first model fetch; catch network/HTTP/checksum errors | "Could not download model X from URL (reason). Plugin 'faces' disabled for this run; others continue. Retry: `gphotos-organizer models fetch faces`." | Per-plugin enable flags (requirements Risk Control) mean a failed plugin degrades, not aborts. Pre-flight `models check` lists cached/missing and sizes before an overnight run |
| Partial run | Any stage interrupted or per-file failure | End-of-run summary: "Processed 11,240 of 17,145; 37 failed (see errors.jsonl); rerun to continue." | Per-file failures are recorded and skipped, not fatal; failed list is retryable (`--retry-failed`) |
| Cloud plugin not allowed | Plugin needs network, no `--allow-cloud` | "Plugin 'era-llm' sends images to <provider>. Skipped; pass `--allow-cloud` to enable." | Off by default (owner decision) |
| `--apply` without a plan / stale plan | Plan hash mismatch with current cache | "Plan is older than the latest analysis. Regenerate: `... plan`." | Refuse rather than write unreviewed values |
| rclone missing/auth expired | Non-zero exit; existing `setup-rclone` command (VERIFIED, `cli.py:439`) | Point to `setup-rclone` | existing |

Existing code quality check (VERIFIED, read `uploader.py` tail): errors are logged via loguru `logger.error` with a message; no unified "what next" hint yet. Add a small `fail(msg, hint)` helper instead of ad hoc strings.

## 5. Jobs to be done

- Functional: "When I upload decades of scanned family prints, I want every photo to land at the right place on the timeline, so that nothing from 1974 shows as 2026." Success metric in requirements.md maps directly. Constraint: faces of 50 years of the same person cluster poorly; manual merge is a required feature, not an edge case.
- Emotional: "I want to be confident I have not damaged or mislabeled my family's history." Implications: never write an inferred date silently; show provenance ("voted by: folder 2021, age-estimate 1978 +/-6"); reversible writes with a journal; honest uncertainty. Prefer "unknown" over a confident wrong guess (graceful degradation is a stated rabbit-hole requirement). Reviewing should feel like looking through an album, not auditing a database: contact-sheet grids, album names as captions, faces large enough to recognize Grandma.
- Social: "I want to share albums with relatives that show the right people and eras." Implications: album names and people labels are outputs relatives will see; the people-labels file should be exportable (names only, not embeddings, given the biometric-adjacent classification) so that naming effort is reusable; ordering and album naming matter to others even though Google Photos' person tagging cannot be done via API (out of scope per requirements.md). Sharing is a reason to run the audit before upload ("upload only after audit passes").
- Manual Google Photos web-UI remediation (no API date-edit route is unverified per requirements.md): treat it as a checklist task. Generate `remediation.md` or an HTML page listing, per album, the items to fix with the target date and a deep link/search hint (album title, upload date), grouped so one "Edit date & time" action covers a selection. Track done-state in the same `decisions.jsonl` (`kind: remediation`, `action: done`) so the list shrinks on rerun and the audit command can verify it.

## Reuse check: existing report.py and review command

VERIFIED by reading `report.py` (68 lines) and `cli.py:155-218`.

- `report.py::generate_markdown_report(results, output_path)` renders the album-level mapping as markdown tables: summary stats by confidence, flagged albums (severity, folder, album name, reasons), locations, full index. Pure string building, no images, no per-photo data, no decisions.
- `cli.py review` already does a filtered rich Table of flagged albums (`--severity`, `--json` for LLM consumption). `update-album --id --date --album-name --location --clear-flags` (`cli.py:221`) is already a terminal "accept/set" action that clears flags. So an album-level terminal review loop exists.
- Reusable: the severity sort, the `needs_review`/`flag_reasons` model, the `--json` convention, and `update-album` as the write path for album-level decisions. The 132 flagged albums (open question) can flow into the same review list by emitting `kind: album-date` items with `flag_reasons` as provenance.
- Gaps: no per-photo or per-cluster granularity, no image output, no decision persistence other than mutating `album_mapping.json` directly (no history, not reversible), emoji in markdown headings (fine for md, avoid in generated HTML headings for screen readers or add `aria-hidden`).
- Suggested approach: keep `report.py` as is for the album report; add a sibling `report_html.py` (Jinja2 or plain f-string templating, no new service) that emits the contact sheets, plus `decisions.py` (append, load, latest-wins fold). Route `update-album` through `decisions.py` so album edits are journaled too.

## Open decisions for planning

1. HTML export-to-file vs terminal answers: ship terminal-answer (`review accept/reject/set`) first; HTML export import second.
2. Thumbnail generation cost on CPU: generate lazily per cluster at review time, cached by file hash.
3. Which terminal Tyler uses (inline image protocol support) is unknown; skip inline images unless confirmed.
