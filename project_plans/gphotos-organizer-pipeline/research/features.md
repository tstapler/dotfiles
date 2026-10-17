# Research: FEATURES (prior art, edge cases, unstated needs)

Date: 2026-10-16. Confidence labels: VERIFIED = source opened or code read; SEARCH = from a web-search snippet only (not opened); UNVERIFIED = inference.

## 1. Existing behavior in this codebase (VERIFIED, read in `stapler-scripts/gphotos-organizer`)

- `scanner.py:33-93` `parse_date_and_location`: precedence full date > year-month > year range > single year > none. Confidence labels are "high" (full date), "medium" (everything else), "low" (none). A year range (`1985-1990`) takes the START year, Jan 1. A single year becomes Jan 1 unless the name contains christmas/father/mother/halloween/grad keywords, which shift the month. These are guessed days that look like real dates once written.
- `metadata.py:38-62` `infer_file_specific_date`: filename regex `\b(19\d\d|20\d\d)[-._]?(\d{2})[-._]?(\d{2})\b`, hard-coded `y < 2024` guard, fixed 12:00:00 plus `index_offset` seconds to keep order.
  - Failure: `\b` does not split between `_` and a digit (underscore is a word character), so `IMG_20150102_...` and `PXL_2021...` do not match. Camera-style names are the main case where the filename date is correct.
  - Failure: the `<2024` cap rejects any real 2024+ filename date.
  - Failure: no month/day cross-validation (31 Feb passes the range check and then hits `except`).
  - Failure: there is no per-file confidence or provenance.
- Extension sets disagree. `scanner.py:17-18` counts `.webp .bmp .gif .3gp .webm .avi .mod .mkv`, but `metadata.py:18-19` only writes `.jpg .jpeg .png .heic .webp .tiff .tif` and `.mp4 .mov .m4v`. Files in the scanner-only set get counted and uploaded but can never get EXIF. The plan should define "dateable" explicitly.
- `generate_descriptive_tags` (`metadata.py:65-97`) tags people by filename substring (`"chris"` matches "christmas"). That is a near-miss precedent for the people-identification problem (see section 4).
- `cli.py` is 496 lines and the stages are inline; there is no plugin hook today.

## 2. Industry / prior-art survey

| Tool | Date from content (no EXIF)? | Face clustering | Notes for us |
|---|---|---|---|
| Immich | No | Yes, local ML; reported to need less manual correction than PhotoPrism ([user report via search](https://dataswamp.org/~solene/2026-04-09-photo-library-management.html)) | Can import face tags from EXIF/XMP sidecars in digiKam format since v1.114.0 ([release notes](https://newreleases.io/project/github/imagegenius/docker-immich/release/alpine-v1.114.0-ig100); users report the import is inconsistent, [discussion](https://github.com/immich-app/immich/discussions/4348)). Candidate for "adopt for clustering, import labels". Not for dating. |
| PhotoPrism | No | Yes; UX described as awkward ([same post](https://dataswamp.org/~solene/2026-04-09-photo-library-management.html)) | No dating features found. |
| digiKam | No, but filename-to-date is built in | Yes, local models downloaded on demand ([features](https://www.digikam.org/about/features/)); one user reports bad clustering on a large library ([thread](https://discuss.kde.org/t/issues-with-digikam-face-recognition-exiftool-config/35394)) | Known gap that matters here: scans often know only a year or month, but `DateTimeOriginal` needs a full timestamp, and digiKam ignores partial dates set through ExifTool ([bug 301357](https://bugs.kde.org/show_bug.cgi?id=301357)). So "imprecise date" needs its own representation, not a fake 01-01. |
| Google Photos | No automatic dating of undated scans found | Own grouping (out of scope) | The app can edit date/time (Android 5.57.0+, per search snippet, [rclone forum thread](https://forum.rclone.org/t/wrong-modtime-and-or-wrong-create-date-google-photos/32638)). A scan with no EXIF is dated from upload time/file mtime, which is the reported symptom. |
| MyHeritage PhotoDater | Yes. Estimates dates for people photos, 1860-1990, only when no date metadata exists. About 60% of estimates are within 5 years ([MyHeritage blog](https://blog.myheritage.com/2023/08/introducing-photodater-an-exclusive-free-new-feature-to-estimate-when-old-photos-were-taken/)). Vendor claim, not independently tested. | n/a | The closest product. Lessons: restricts scope (people photos only, not documents), writes the estimate as an approximate (GEDCOM-style) date, and lets the user save or dismiss. This matches our review-list-then-write flow. |
| Wrethink patent | Estimates scan date from face-age vs. reference images with known dates; notes scan date says nothing about capture date ([patent US12354406](https://patents.google.com/patent/US12354406)) | n/a | Same idea as the "anchor calibration" plugin. |
| Apple Photos, Mylio, Ancestry, FamilySearch | Not found. Searches returned nothing on dating features. | - | GAP: do not claim anything about them. |
| ExifTool scripts | Write only. They support date shifts and `-o`/`_original` backups, but infer nothing. | - | Use for the writes and the journal. |

### Academic work on dating images
- Palermo, Hays, Efros, "Dating Historical Color Images", ECCV 2012: 5-way decade classification from color-process cues with hand-crafted features and SVMs; beats untrained humans, but the paper's abstract gives no headline number ([mlanthology](https://mlanthology.org/eccv/2012/palermo2012eccv-dating)). A slide deck quotes 45.7% (unverified, secondary). Decade-level only, on old photos, so it says little about 1960-2005 family prints.
- Salem et al., "Face2Year" / yearbook work: year from faces and style, built on 20th-century US yearbook portraits ([arXiv 1511.02575](https://arxiv.org/pdf/1511.02575), [Face2Year PDF](https://www.cs.uky.edu/~salem/face2year/papers/salem2016face2year.pdf)). I could not extract numbers (the PDF came back as binary). The point still holds: hairstyle and fashion carry era signal that age estimators ignore.
- "Date Estimation in the Wild of Scanned Historical Photos: An Image Retrieval Approach" ([arXiv 2106.05618](https://arxiv.org/abs/2106.05618)): ranks archive images by estimated date, evaluated on the DEW dataset. I opened only the abstract page, which gives no MAE.
- Age estimation: MiVOLO face-only reaches MAE 4.23 y on UTKFace per its README ([GitHub](https://github.com/WildChlamydia/MiVOLO), [paper](https://arxiv.org/pdf/2307.04616)). A 2026 benchmark, seen only as a search snippet, lists MiVOLO at 5.10 and VLMs at about 4.3 ([search result](https://deepfake-demo.aisec.fraunhofer.de/related_work/2602.07815)). These are clean, digital, mostly young-adult faces. Expect worse on faded scans, and an age MAE of 4-5 y on adults is bigger than the requirements' target of ±2 y for children (plausible) and ±8 y for adults (roughly the right order). Implication: the age-based date is children-only evidence; for adults it should get a low weight.

### What tools do for scanned prints with no EXIF (summary)
1. Filename or folder to date (digiKam, this repo).
2. Face-age or appearance to estimated range (MyHeritage; research code).
3. Manual entry with a review UI (everything else).
No tool found reports accuracy on 1960-2000 family prints in color; the nearest number is MyHeritage's 60% within 5 y.

## 3. Google Photos remediation constraints (partly VERIFIED)
- Google's update notes say that after 2025-03-31 the Library API's `readonly`, `sharing` and full `photoslibrary` scopes were removed. List, search and get now work only on items the calling app created. `appendonly`, `readonly.appcreateddata` and `edit.appcreateddata` remain ([Google update page](https://developers.google.cn/photos/support/updates?hl=en), [release notes](https://developers.google.com/photos/library/support/release-notes)).
- Consequence: an audit that enumerates remote items by date cannot use the Library API on items uploaded by rclone's own client (a different app/client ID). Also uncertain is whether rclone's `googlephotos` backend still lists the library ([rclone forum](https://forum.rclone.org/t/add-the-new-google-photos-picker-api-to-rclone/47938) suggests uploads may still work and the Picker API does not fit). The Picker API is selection-based and interactive.
- No source found that says the API can edit `creationTime` of an existing item. rclone users are told it cannot override create date ([rclone forum](https://forum.rclone.org/t/wrong-modtime-and-or-wrong-create-date-google-photos/32638)). Requirements baseline claim stays UNVERIFIED but is consistent with every source seen.
- Design implication: the audit may have to be built from the local upload manifest (what was sent with which written date) instead of from remote reads. Remote verification may be limited to a Takeout export or manual spot-checks. Needs a decision after the API research dimension reports.

## 4. Edge cases and failure modes

| Case | Risk | Suggested handling |
|---|---|---|
| Aging drift over decades | One person's embedding at 8 and at 40 may not match; clusters split. Age-based dating depends on the right identity. | Allow multiple clusters per person (per-era sub-clusters) with manual merge; anchor-based calibration per cluster. |
| Siblings / twins / parent-child look-alikes | Cluster merges wrongly; wrong birth date gives a wrong date by a gap of years. | Never auto-assign identity above a strict threshold; require labeled cluster review; cap fusion if cluster purity is unknown; flag photos where top-2 identities are close. |
| Group photos | Several faces, several birth dates. Each yields a different implied date. | Take the consensus; treat spread beyond the age error as a conflict, send to review. Weight children more. |
| Photos of photos, framed prints, yearbook pages | Faces from a different era than the photo; reflections, glare. | Detect a nested frame or screen; lower confidence. |
| Faded, B&W, sepia scans | Age and era models trained on clean color; color-process cues (Palermo) are removed in B&W. | Per-plugin applicability gate; report confidence as "unknown" rather than a number. |
| Printed date stamp in the corner (1980s-90s film cameras, orange digits) | Highest-accuracy signal if present; OCR on it is cheap. Formats differ: `'96 3 14`, `14 3 96`, `MM DD YY`. Digits are ambiguous (day/month order). Also wrong if the camera clock was never set. | Candidate plugin: corner crop OCR, validate against folder-year bounds; give high weight but not absolute. Stamp reading `1/1/00` or similar is a reset clock. |
| Duplicate / near-duplicate scans (same print scanned twice, crops, rotations) | Double-counting in fusion; two different dates for the same print; uploads dedupe in Google or create duplicates. | Perceptual hash grouping; share one date across a group, use the highest-confidence member; cache by content hash (already in NFRs). |
| Videos (`.mp4 .mov .3gp .avi .mod`) | Faces can be sampled but scanned-era VHS rips have no EXIF; QuickTime tags and `.mod` (camcorder) have different write paths. | Keep out of face plugins at first; apply folder/filename dating only; document unwritable containers. |
| HEIC | Writes need exiftool; Pillow needs `pillow-heif` to decode. | Put HEIC in the writable-set test fixtures. |
| Filename dates | Regex fails on `IMG_2015...` (underscore); `<2024` cap; WhatsApp/Screenshot names carry download dates not capture dates; `Scan_0001`. | Replace with a provider-style parser that records `filename_date` as a vote with confidence; blacklist known non-capture prefixes. |
| Folder-name year formats | `1985-1990`, `'85`, `85`, `Summer 1990`, `Christmas '94`, `Fall 1998-Spring 1999`, decade names `1980s`, year-month in word form. Current code handles only 4-digit forms; range becomes start year. | Represent as an interval (start, end, precision) not a point; fuse as ranges. Fake `01:01` and `12:00:00` must be marked as placeholders in provenance. |
| Timezone / DST | Fixed 12:00:00 noon with no offset; Google Photos shows local time derived from EXIF plus `OffsetTime*` tags, absent here. Near midnight, UTC conversion can shift the day. | Always write a noon placeholder with an explicit `OffsetTimeOriginal`, or write dates only (noon local) and avoid DST edges; never write real-looking times for inferred dates. |
| Birth-date bounds | Age estimate implies a date before the person's birth or after death/the scan date. | Hard guards: date >= birth + estimated lower age; date <= earliest of folder-year upper bound and scan date. |
| Folder year vs. image evidence conflict | Folder `1995` holds a 2003 photo (misfiled). | Surface the conflict; folder-year is a prior, not a constraint, unless the owner marks the album trusted. |
| Cloud vision privacy | Face images leave the machine. | Already gated by `--allow-cloud`; log which files were sent. |

## 5. Unstated user needs (INFERRED from the requirements and the tools above)
1. Reversible writes: a journal of original tag values per file (JSONL: path, hash, tag, old, new, run id) plus a `revert` command; exiftool `_original` backups alone are fragile (they accumulate and skip on second run).
2. Review list UI: even without a web UI, a sortable CSV/HTML contact sheet (thumbnail, proposed date, interval, per-plugin votes, accept/override columns) and an `import-review` command that reads Tyler's decisions back. MyHeritage's save/dismiss model is the precedent.
3. Confidence provenance: store per-plugin votes (value, interval, weight, model version), so the fused result is reproducible and an unreliable plugin can be re-run or removed without redoing everything.
4. Per-person config: birth (and death) dates, aliases, and an optional "photo is trusted" flag, in a local file outside the dotfiles git (matches the data-residency NFR).
5. Anchor selection: which photos count as ground truth. Candidates: EXIF-dated photos, printed date stamps, folders with full dates. Let Tyler pin or exclude anchors, and hold some out for error reporting (already a success metric). Sparse anchors per person and decade are a stated risk, so show anchor counts per person-decade.
6. Already-uploaded items: a list of uploaded items (from the manifest) whose written date was a placeholder or is later changed by the pipeline, grouped by album, to drive manual web-UI fixes or trash and re-upload. Include a warning that re-upload may be deduplicated by content hash.
7. Imprecise dates as a first-class value (year only, decade, interval), with a display like "c. 1987" in the review list, and a clear rule for the date written to EXIF (midpoint? start?) that is applied consistently.
8. Status truthfulness: `metadata_status` and `upload_status` should derive from the journal and manifest, not a one-way flag (already in scope item 6).
9. Idempotent reruns keyed on content hash, with plugin version in the cache key so a model upgrade invalidates only that plugin.

## 6. Build-vs-adopt signals for the synthesis
- Adopt for faces: Immich or digiKam clustering is proven and has a review UI, but both want a running service or desktop app and an import path for labels; a library-only route (InsightFace) fits the uv-script CLI better. This tradeoff belongs to the faces/age research dimension.
- Nobody offers dating plus review for personal libraries offline. MyHeritage is cloud, and only for photos uploaded to it.
- Highest value-for-cost signals, in order: printed date stamp OCR (where present), folder/filename intervals, multi-face child age with birth-date bounds. Era-by-appearance stays a tiebreaker, as the requirements already say.

## 7. Gaps
- No accuracy numbers found for Apple Photos, Mylio, Ancestry or FamilySearch dating (searches returned nothing).
- Face2Year and DEW numbers not extracted; fetch the PDFs in a follow-up if a benchmark is needed.
- Whether rclone's `googlephotos` backend can still list or read dates after the March 2025 API change was not verified.
