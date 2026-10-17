# Research: Stack (libraries, models, Google Photos API limits)

Date: 2026-10-16. Labels: VERIFIED = page/command output opened this session (URL given); UNVERIFIED = from memory or a search-result summary only; INFERRED = my reasoning from verified facts.

## 0. Constraints from the existing code (VERIFIED, local)

- `cli.py` header: `#!/usr/bin/env -S uv run`, PEP 723 block with `requires-python = ">=3.11"` and deps `typer>=0.12, loguru>=0.7, rich>=13, pydantic>=2.0` (`stapler-scripts/gphotos-organizer/cli.py:1-9`). Sibling modules (`scanner.py`, `metadata.py`, `uploader.py`, `models.py`) are imported flat (`from models import ...`), so they run only when the script dir is on `sys.path`. They are not a package.
- exiftool is already shelled out via `subprocess` with `-@ argfile` chunking (`metadata.py`, `EXIFTOOL_PATH` from `scanner.py`). Local exiftool is 13.55; rclone is v1.73.4 at `/home/linuxbrew/.linuxbrew/bin/rclone`. Machine: 24 logical CPUs, system Python 3.14.7, uv 0.9.28.
- Heavy ML deps in PEP 723 inline metadata are possible but each `uv run` resolves them (cached after the first run). Recommendation: keep `cli.py` light (typer/loguru/rich/pydantic) and put ML plugins behind a PEP 723 sub-script or `uv run --with` / an optional-extras `pyproject.toml` in the project dir, so `scan`/`upload` don't pay ML install cost. Pin `requires-python = ">=3.11,<3.14"` for the ML script: onnxruntime 1.31.0 needs >=3.11 (PyPI JSON), but wheel availability for 3.14 for insightface's compiled extension is UNVERIFIED. uv can fetch a managed 3.12 with `--python 3.12`, which is the safe choice.

## 1. Face detection + embedding + clustering

| Option | Version / date | License | Notes |
|---|---|---|---|
| InsightFace (`insightface`) | 2.1, uploaded 2026-10-03 (PyPI JSON https://pypi.org/pypi/insightface/json); previous 0.7.3 (2023-04-02) | Code MIT; **pretrained models (incl. buffalo_l) non-commercial research only** (VERIFIED via search summary of https://pypi.org/project/insightface/ and https://github.com/NicoJuicy/insightface/blob/master/python-package) | Requires numpy, onnx>=1.13, onnxruntime, opencv-python, scipy, scikit-image (PyPI JSON, VERIFIED). buffalo_l = SCRFD-10GF detector + ResNet50@WebFace600K ArcFace (512-d), 326 MB. Personal, non-commercial use is fine. Whether the 2.x line changed model packs/licensing is UNVERIFIED. |
| face_recognition (dlib) | 1.3.0, last release 2020-02-20 | MIT | Unmaintained for 6+ years (VERIFIED, PyPI JSON). Needs dlib compile (cmake, C++). 128-d embedding; weaker than ArcFace on profile/aged faces (INFERRED from model generation). Not recommended. |
| DeepFace | 0.0.102 | MIT | Wrapper over many backends (ArcFace, Facenet, RetinaFace). Pulls TensorFlow/Keras: heavy. Use only if you want one API; otherwise redundant with InsightFace. |
| ArcFace/FaceNet via plain ONNX | n/a | model-dependent (OpenCV Zoo SFace/YuNet is Apache-2.0, per search summary of LocalAI docs; UNVERIFIED primary) | Lightest, licence-clean fallback: `onnxruntime` + `opencv`. Lower accuracy than buffalo_l. |

Clustering:
- `hdbscan` 0.8.44 (BSD, uploaded 2026-06-01, Python >=3.10) and `scikit-learn` 1.9.1 (BSD-3, Python >=3.11), which also ships `sklearn.cluster.HDBSCAN` (PyPI JSON, VERIFIED versions/licences). Prefer scikit-learn's HDBSCAN to avoid a second dependency (that it is available in 1.9.1 is INFERRED from it being added in sklearn 1.3).
- Pattern: L2-normalise 512-d embeddings, use cosine (HDBSCAN on normalised vectors with euclidean is equivalent), `min_cluster_size` ~3-5, `min_samples` 1-2. Use per-era sub-clusters then agglomerative merge by centroid cosine, with human merge (requirements Rabbit Hole: 50 years of aging). Keep noise points (label -1) as "unknown" instead of forcing them into clusters.
- Identity labels: store cluster centroid + a few labelled exemplars per person per decade; classify new faces by nearest labelled exemplar with a distance threshold.

CPU speed for ~17k images (UNVERIFIED, no authoritative benchmark found; my web search for buffalo_l CPU ms/image returned none). Planning estimate only: SCRFD-10G at 640x640 plus ArcFace R50 on a modern CPU is on the order of 0.1-0.4 s per image with onnxruntime using several threads. With 24 logical cores and process-level parallelism (4-6 workers x 4 threads) 17k images should be well inside an overnight window (INFERRED). Action for the plan: add a 200-image timing spike as the first task and record CPU model, threads and onnxruntime version. Use `buffalo_s`/`det_size=(480,480)` as the speed fallback. Decode HEIC with `pillow-heif` 1.8.1 (BSD-3) if needed.

## 2. Age estimation

- MiVOLO (face+body transformer): AgeDB MAE 5.55 (MiVOLO-D1, vs DEX 13.1 on the same table) and UTKFace 4.23 (face-only per its GitHub), 3.7 on one leaderboard (VERIFIED as reported by search summaries of https://arxiv.org/pdf/2307.04616 and https://github.com/qeumo/mivolo; the discrepancy between 4.23 and 3.7 is unresolved). A 2026 benchmark of 34 models across 8 datasets found MiVOLO the only specialised model competitive with VLMs, average MAE 5.10 vs 4.32 for the best VLM (https://arxiv.org/pdf/2403.02302 is the benchmark paper title match; the 2026 figures come from a Fraunhofer-hosted related-work page found in the same search, so treat as UNVERIFIED primary). MiVOLO weight licence: UNVERIFIED (search returned nothing; check the repo LICENSE before use; it is not ONNX-first, so expect a PyTorch dependency or an ONNX export).
- InsightFace's bundled `genderage` model in buffalo_l gives a coarse age with no published MAE I could verify. Treat as UNVERIFIED and the cheapest baseline (it comes free with the detector pack).
- DEX (IMDB-WIKI): MAE 13.1 on AgeDB per MiVOLO's table above, so the 2015 baseline is weak for adults. IMDB-WIKI licence UNVERIFIED (likely research-only).
- Old / scanned / grayscale photos: **no benchmark found** quantifying the drop (two searches; best result only notes B&W "can have a significant effect", https://um.edu.mt/library/oar/handle/123456789/71654). Consequences: published MAE values (4-6 years on clean data) are a floor, not an expectation. Anchor calibration (known birth date + known photo date) is the only way to measure error on this collection, as the requirements already propose. Mitigations: convert all inputs to grayscale before age inference so colour and B&W photos share a distribution; histogram-equalise faded prints; discard faces under ~60 px; report error by decade and by colour/B&W.
- Practical stance: use estimated age mainly for children (rapid change gives high information; requirements target ±2 yrs) and widen the confidence interval for adults (±8 yrs target) so fusion discounts adult votes automatically.

## 3. Era-by-appearance and photo-dating models

- Dataset "Date Estimation in the Wild" (DEW, Müller, Springstein, Ewerth, ECIR 2017): >1M Flickr images, years 1930-1999, balanced test set of 1,120 images (16 per year), CC BY 4.0 on RADAR (DOI 10.22000/43 metadata, 10.22000/44 images) (VERIFIED: https://oa.tib.eu/renate/items/1617ef10-5757-4e6b-97d0-a33d6b8745cc; test-set size and baselines in https://arxiv.org/abs/2106.05618 / https://arxiv.org/html/2106.05618v1).
- Baselines on DEW test set, mean absolute error: GoogLeNet regression 7.5 yrs, classification 7.3 yrs (Table 1 of arXiv 2106.05618, VERIFIED). The retrieval method of that paper improves on this (exact value not extracted). Takeaway: the best supervised dating models are at ~7 years MAE across a 70-year range on Flickr photos, so an era classifier can narrow to a decade or two but not to a year.
- Pretrained weights for DEW models: I found none that are ready to use (UNVERIFIED; training would need the 1M-image dataset, out of scope). Do not plan on an off-the-shelf photo-dating model.
- CLIP zero-shot: OpenCLIP with prompt "a photograph from the year x" on 1950-2000 photos gives MAE 15.8, biased toward earlier dates; fine-tuning a logistic head removes the bias (https://arxiv.org/pdf/2310.06633, "Blind Dates", VERIFIED via search excerpt). L2RCLIP paper reports zero-shot CLIP is suboptimal on the 1930s-1970s decade dataset (https://arxiv.org/pdf/2306.13856). So zero-shot CLIP alone is a weak tiebreaker, which matches the requirements' Rabbit Hole. Better pattern: extract frozen CLIP/SigLIP image embeddings and fit a small ridge/logistic regressor on the user's own confidently dated photos (folder-dated albums supply thousands of labels). That is cheap, local and calibrated to this collection's scan characteristics (INFERRED design; the Blind Dates fine-tune result supports it).
- Libraries: `open_clip_torch` 3.3.0 (MIT, Python >=3.9), `transformers` 5.20.1 (Apache-2.0) for SigLIP; both need PyTorch (CPU wheel; large install). SigLIP-vs-CLIP accuracy on dating: UNVERIFIED. If torch is unwelcome, export the image tower to ONNX and run via onnxruntime 1.31.0 (MIT).
- Cheap non-ML era cues worth including as plugins: print/scan format (aspect ratio, border/deckle, sepia vs B&W vs colour cast), and embedded scanner EXIF (Software/Make) which is a scan date, not capture date, so must not be trusted as the capture date.
- Cloud variant (opt-in `--allow-cloud`): a vision LLM can be asked for era, clothing/vehicle cues and a year range with confidence. Accuracy on this collection UNVERIFIED; sample only low-confidence items and cache by file hash.

## 4. exiftool / PyExifTool

- Local exiftool 13.55 (VERIFIED, `exiftool -ver`). PyExifTool 0.5.6 (PyPI JSON; licence "GPLv3+/BSD" dual) requires exiftool >= 12.15 and runs one long-lived `-stay_open` process; use `exiftool.ExifToolHelper()` as a context manager (search summary of https://pypi.org/project/PyExifTool/ and https://github.com/sylikc/pyexiftool; docs https://sylikc.github.io/pyexiftool).
- Recommendation: keep the existing subprocess + argfile batching in `metadata.py`; add PyExifTool only for fast bulk reads (`get_tags` of DateTimeOriginal/CreateDate/ImageUniqueID for the audit and for hashing/skip logic), because it avoids a process spawn per file and adds a dependency. Not essential.
- Reversibility: `-overwrite_original` is not used if you want exiftool's default `_original` backup; better a journal table in sqlite (path, tag, old value, new value, run id) written before each write and a `revert` command that replays old values with `-TAG=old` (or deletes tags that were absent). Prefer `-DateTimeOriginal -CreateDate -ModifyDate` (+ `-OffsetTimeOriginal` unset) so Google reads a capture date (Google Photos uses EXIF capture time else upload time, VERIFIED in rclone doc, section 6).
- Checks: `-api QuickTimeUTC` for video; do not write placeholder `YYYY:01:01 12:00:00` for unresolved photos. Write nothing instead (keep them on the review list), since a missing EXIF date puts the item at upload date, which is exactly the failure mode in the problem statement.

## 5. Caching (sqlite)

- stdlib `sqlite3`, WAL mode; one DB beside the manifest, kept out of dotfiles git (add to `.gitignore`; requirement: data residency).
- Suggested tables: `files(sha256 PK, path, size, mtime)`, `plugin_results(sha256, plugin, plugin_version, params_hash, result_json, confidence, created_at, PK(sha256,plugin,plugin_version,params_hash))`, `faces(face_id PK, sha256, bbox, embedding BLOB float32[512], det_score)`, `clusters(face_id, cluster_id, run_id)`, `labels(cluster_id, person)`, `exif_journal(...)`, `uploads(...)`.
- Key by content hash (sha256 of bytes; for 17k files reading everything once is acceptable) with a cheap `(size, mtime_ns)` pre-check to skip rehash. Include `plugin_version` and a params hash in the key so changing a model invalidates only that plugin's rows. Store embeddings as raw float32 BLOBs (512 x 4 = 2 KiB per face; tens of thousands of faces is under 100 MB).
- Alternative considered: JSON-lines (matches the manifest style) but it has no indexed lookup or atomic partial updates; sqlite is better for resumability under crashes.

## 6. rclone `gphotos` backend (VERIFIED, https://rclone.org/googlephotos/)

- Tier 5 "Deprecated: No longer maintained or supported" on the rclone tiers page; installed rclone is v1.73.4 (local).
- **Since 2025-03-31 rclone can only download photos it uploaded** (Google policy). Albums: can only upload to albums it created; can remove files from albums it created only; cannot delete files anywhere except under `album`; API cannot delete media permanently, and does not support deleting albums.
- **Dates:** "The date shown of media in Google Photos is the creation date as determined by the EXIF information, or the upload date if that is not known. This is not changeable by rclone." So the only lever to control the timeline date on upload is correct EXIF before upload.
- **The shared rclone OAuth client_id is being retired and "will stop working during 2026"**; creating your own client_id with the Photos Library API enabled and scopes `photoslibrary.appendonly`, `photoslibrary.readonly.appcreateddata`, `photoslibrary.edit.appcreateddata` is now required. Today is 2026-10-16, so this is an operational risk for the upload step: confirm which client_id the existing `gphotos:` remote uses (`rclone config show gphotos`; I did not run it to avoid exposing secrets).
- Dedup: the same binary uploaded twice is deduplicated by Google, keeping the first filename. Consequence for remediation: re-uploading a fixed-EXIF file with different bytes creates a new item; the same bytes would dedupe to the old, misdated item (dedup by bytes is stated in the doc; whether metadata-only changes alter the hash is INFERRED: EXIF edits change bytes, so they should create a new item, UNVERIFIED).
- Downloads strip EXIF location and are not original resolution unless `--gphotos-proxy` (gphotosdl headless browser) is used. Not needed for this pipeline, since originals are on local disk.
- Batching: `--gphotos-batch-mode`, `--gphotos-batch-size` (<50), `--transfers`; the existing quota handling matches the daily request quota below.

## 7. Google Photos Library API (VERIFIED, official docs)

Sources: https://developers.google.com/photos/library/reference/rest (last updated 2025-04-01), https://developers.google.com/photos/support/updates, https://developers.google.com/photos/library/reference/rest/v1/mediaItems, https://developers.google.com/photos/library/reference/rest/v1/mediaItems/patch, https://developers.google.com/photos/overview/api-limits-quotas.

- Since 2025-03-31 the `readonly`, `sharing` and full `photoslibrary` scopes are removed; remaining scopes: `photoslibrary.appendonly`, `photoslibrary.readonly.appcreateddata`, `photoslibrary.edit.appcreateddata`. List/search/get operate **only on content created by your app** (your OAuth project), plus items chosen via the Picker API and added by the app.
- Methods on mediaItems: `batchCreate`, `batchGet`, `get`, `list`, `patch`, `search`. Albums: `addEnrichment`, `batchAddMediaItems`, `batchRemoveMediaItems`, `create`, `get`, `list`, `patch`. **No media-item delete and no album delete exist.**
- **Read item creation time: yes, for app-created items.** `mediaMetadata.creationTime` = "Time when the media item was first created (not when it was uploaded to Google Photos)" (RFC 3339). It carries the EXIF-derived/edited capture date as Google stores it.
- **Edit date: no.** `mediaItems.patch` "Only the `id` and `description` fields ... are read"; `updateMask` valid value is only `description`; item must be created by your app. Confirms the requirements' UNVERIFIED baseline claim: dates of existing items cannot be edited by API. (Editing date/time is possible in the Google Photos web/app UI; not an API feature.)
- **Delete: no** (confirmed by method list and by rclone's note about bug 109759781). Remediation for wrong items is trash in the web UI (owner action) then re-upload corrected files; Trash/UI behaviour itself is UNVERIFIED here.
- **Audit feasibility (important, INFERRED from "app-created only")**: `mediaItems.list/search` with a date filter would see only items uploaded by the same Cloud project/client_id. Photos already uploaded through rclone's shared client_id are probably not visible to a new own-client_id audit, so the audit may only cover future uploads. Test early: create own client, run `mediaItems.list` (page size up to 100, UNVERIFIED limit value) and count items; compare with `upload_manifest.json`. If visible count is 0, fall back to (a) rclone with the old shared client while it still works (`rclone lsl gphotos:media/by-year` style listing, which exposes year buckets per the layout section) or (b) Google Takeout (JSON sidecars with `photoTakenTime`; UNVERIFIED here) or (c) the Picker API (user manually selects items; not scriptable bulk).
- Picker API (`photospicker.googleapis.com`): sessions + list picked items; user-driven selection through the Photos app; read-only (VERIFIED, https://developers.google.com/photos/picker/reference/rest). Whether picked items expose creation time: UNVERIFIED.
- Quotas: Library API 10,000 requests/project/day; media-bytes access 75,000/day; exceeding returns HTTP 429 (VERIFIED, api-limits-quotas). Uploads are original quality and count against account storage. The existing 00:05 Pacific wait in `uploader.py` is consistent with daily quota, but the doc does not state the reset time (UNVERIFIED).
- Practical per-file cost: an upload is two calls (upload bytes + `batchCreate` of up to 50 items per call, per rclone's batch limit "less than 50"), so a daily cap of 10,000 requests allows roughly several thousand files/day depending on batching (INFERRED); the remaining ~9,400 unuploaded files (17,145 − 7,757 per the requirements) fit in a few days.

## 8. Adopt vs build (for the requirements' Alternatives)

- Immich / PhotoPrism / digiKam: not investigated in this pass (UNVERIFIED). Note both Immich and digiKam use ArcFace-class models plus DBSCAN-style clustering; importing their labels would require running a server or reading their DB. Given the sole-operator CLI setting, building a thin plugin on InsightFace + sklearn HDBSCAN is the lower-integration path. Recommend a follow-up research item on digiKam's face DB export if manual labelling UX is wanted.

## 9. Recommended minimal stack (summary)

| Concern | Choice | Why |
|---|---|---|
| Face detect+embed | `insightface` buffalo_l (ONNX, CPU) | Best accuracy among local options; non-commercial model licence is fine for personal use |
| Clustering | `scikit-learn` HDBSCAN, cosine on L2-normalised 512-d | One dependency, noise handling |
| Age | InsightFace genderage as baseline; evaluate MiVOLO via anchors | Published MAE 4-6 on clean data; none for scans, so measure on anchors |
| Era | Frozen CLIP/SigLIP embeddings + regressor trained on folder-dated photos | Zero-shot CLIP MAE 15.8; supervised DEW baselines ~7 |
| EXIF | existing exiftool argfile + sqlite journal; optional PyExifTool for reads | Reversible writes |
| Cache | stdlib sqlite3 keyed by sha256 + plugin_version | Incremental reruns |
| Upload/audit | rclone `gphotos` with own client_id; Library API `mediaItems.list` for audit of app-created items | Dates only controllable via EXIF; no date edit, no delete via API |
| Python | uv, `>=3.11`, ML script pinned to 3.12 | onnxruntime >=3.11; avoid unverified 3.14 wheels |
