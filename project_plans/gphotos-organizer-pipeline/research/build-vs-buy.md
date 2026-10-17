# Build vs Buy: gphotos-organizer-pipeline

Date: 2026-10-16. Scope: ~17,145 images, CPU only, local by default, cloud opt-in (`--allow-cloud`).
Confidence labels: VERIFIED = seen in a fetched/search result (URL given); UNVERIFIED = not confirmed against a primary source. Most WebSearch results were secondary sources; primary-page checks are listed under "Gaps".

Code context (VERIFIED by `ls`/`head`): `stapler-scripts/gphotos-organizer/` is ~1,389 lines across `cli.py` (496), `metadata.py` (209), `scanner.py` (261), `uploader.py`, `ai_enrich.py`; PEP 723 deps are only typer/loguru/rich/pydantic. `metadata.py` already shells out to exiftool in chunked `-@ argfile` batches (path from `scanner.EXIFTOOL_PATH`).

## Summary table

| Capability | Recommended | Why in one line |
|---|---|---|
| Face detect/embed | InsightFace library + ONNX Runtime CPU (weights license gated, see below); fallback YuNet+SFace (Apache-2.0) | Mature, CPU-viable; weights are non-commercial, fine for personal use |
| Face cluster | scikit-learn `HDBSCAN` (or agglomerative) over embeddings; build thin glue | No new dep; ~50 lines |
| Age estimation | InsightFace genderage head (local) as weak signal; cloud age only as opt-in | Local estimators are biased on scans; treat as low weight |
| Era-by-appearance | open_clip zero-shot, tiebreaker only; optional Claude vision on uncertain subset | Rabbit hole per requirements |
| Date estimation / fusion | Build (small, deterministic, tested) | No library does anchor-calibrated fusion; it is the product logic |
| Plugin framework | Build a ~40-line registry; pluggy Viable | 3-5 plugins; entry points do not fit a uv script |
| EXIF writing | Keep exiftool subprocess (already used); PyExifTool Viable | Existing code works; wrapper adds little |
| Google Photos upload/audit/redate | rclone for upload (keep); audit via local manifest + Picker/manual; redating is manual | API cannot read or edit non-app items (VERIFIED below) |

## 1. Face detect / embed / cluster

### Option A: InsightFace (+ onnxruntime CPU)
- Pros: strong embeddings (ArcFace family), detection + landmarks + embedding + genderage in one `FaceAnalysis` call; ONNX runs on CPU; library code MIT.
- Cons: pretrained models (incl. auto-downloaded `buffalo_l`) are "non-commercial research purposes only" - fine for a personal tool, a blocker if ever distributed commercially; install pulls onnxruntime, numpy, opencv (and historically a C++ build for some wheels - UNVERIFIED for current wheels); newest PyPI version not confirmed (0.7.x seen).
- Sources: https://pypi.org/project/insightface/ ; license wording confirmed via search summary of https://pypi.org/project/insightface/0.7.2 and https://huggingface.co/mudler/face-detect-gguf (VERIFIED wording, version of latest UNVERIFIED).
- CPU cost for ~17k images: UNVERIFIED estimate, low single-digit images/sec per core with `buffalo_l` at det_size 640 -> roughly 1-3 hours on a multi-core CPU; must be benchmarked on a 200-image sample before planning. Cache embeddings per file hash.
- Verdict: **Recommended** (personal, local use). Keep the model pack name in config so the weights can be swapped.

### Option B: YuNet + SFace (OpenCV Zoo)
- Pros: Apache-2.0 weights per LocalAI docs (UNVERIFIED primary: check opencv_zoo LICENSE); tiny, fast on CPU; no non-commercial question.
- Cons: SFace embeddings less accurate than ArcFace on hard cases; no age head; fewer community recipes.
- Source: LocalAI docs mirror referenced in search (https://gitea.varghacsongor.hu/GithubMirror/LocalAI/src/branch/bump/turboquant-upstream-sync-april-2026/docs).
- Verdict: **Viable** (license-clean fallback).

### Option C: deepface
- Pros: one API for detect/embed/age/gender/emotion; MIT; active (0.0.100 released 2026-05-09 per https://pepy.tech/project/deepface , secondary).
- Cons: wrapper that pulls TensorFlow/Keras (heavy for a uv script); inherits each backend model's license (its own docs say so); age model accuracy figures not found; 0.0.x versioning signals API churn.
- Verdict: **Viable** for age experiments; **Not recommended** as the core dependency.

### Option D: face_recognition (dlib)
- Pros: simple API, well known.
- Cons: dlib needs a C++ compile; project reported as low-maintenance; older HOG/CNN models weaker on non-frontal and faded faces. Maintenance/release dates UNVERIFIED (search returned nothing).
- Verdict: **Not recommended**.

### Clustering: scikit-learn HDBSCAN vs hdbscan package vs agglomerative
- sklearn `cluster.HDBSCAN` exists since 1.3 (VERIFIED: https://scikit-learn.org/stable/modules/generated/sklearn.cluster.HDBSCAN.html); note `min_samples` includes the point itself (differs by 1 from `hdbscan` package). Avoids a Cython-build dependency.
- Pros: handles unknown cluster count and noise (unmatched faces stay unlabeled - desirable). Cons: needs cosine (normalize embeddings, use euclidean) and tuning; cross-decade drift means one person yields several clusters, so manual merge via the labeling step is required regardless of library.
- Verdict: sklearn HDBSCAN **Recommended**; standalone `hdbscan` **Viable**; hand-written clustering **Not recommended** (correctness risk, see section 7).

### Option E: Import labels from Immich / PhotoPrism / digiKam
- Immich: AGPL-3.0 since v1.95 (secondary: https://v1.100.0.archive.immich.app/milestones); face data lives in Postgres (`person`, `asset_faces`) per a third-party skill description, not official docs (UNVERIFIED). Needs Docker + ML container + DB just to cluster; Tyler's labels would be made in its UI.
- PhotoPrism: license and face export UNVERIFIED (no result). digiKam: face DB format UNVERIFIED (no result).
- Pros: polished face review UI, merge/split, handles drift better than a CLI; labels reusable. Cons: heavy infra; import path is schema-coupled (breaks on upgrades); embeddings not portable (different models), so you only get name-to-file mappings, which is exactly what anchors need; second system to maintain; privacy fine if local.
- Verdict: **Viable as an optional label source** (read name->file mappings via DB/sidecar, behind a plugin), **Not recommended** as the required backend. Revisit if manual cluster labeling in a CLI proves too painful.

## 2. Age estimation
- Local: InsightFace `genderage` head (part of buffalo packs, non-commercial weights) and deepface age model. Both trained on modern, sharp, color photos; expected bias on faded/scanned prints and adults (requirements Rabbit Holes). No accuracy numbers verified. Verdict: **Viable** as low-weight signal; calibrate against anchor photos (known birth date + known photo date) and fall back to "no vote" when disagreement or low face quality.
- AWS Rekognition `DetectFaces` returns `AgeRange` (low/high) - the range is typically ~10+ years wide (UNVERIFIED), which is too coarse for children's ±2y target but fine for child-vs-adult gating. Price: about $0.001/image first tier (secondary, conflicting free-tier info: https://aws.amazon.com/es/rekognition/pricing/ , https://wring.co/blog/aws-rekognition-pricing-guide) -> ~$17 for 17k. Data leaves machine (faces uploaded to AWS). Verdict: **Not recommended** by default; **Viable** opt-in.
- Google Cloud Vision: face detection does not return age (it returns emotions/landmarks) - UNVERIFIED from memory; price $1.50/1000 after 1,000 free (VERIFIED: https://cloud.google.com/vision/pricing). Verdict: **Not recommended** (no age).
- Claude vision (estimate "apparent age and decade"): Haiku 4.5 listed at $1/M input, $5/M output (secondary aggregators: https://anotherwrapper.com/llm-pricing/claude-haiku-4-5-20251001 ; confirm at platform.claude.com). Image tokens ~ w*h/750, long edge capped ~1568 px (older docs; secondary: https://docs.anthropic.com/claude/docs/vision). At ~1.5k image tokens + ~150 output tokens: ~$0.0023/image -> **~$40 for all 17k** (my arithmetic from unverified rates); ~$4 for a 10% uncertain subset. Cons: sends private family photos to a third party (violates default; allowed only with `--allow-cloud`); nondeterministic; refusals on identifying people (ask for apparent age/decade, never identity). Verdict: **Viable** opt-in on sampled/uncertain subset.

## 3. Era-by-appearance
- open_clip zero-shot ("photo from the 1970s/80s/90s" plus film-stock/print cues): maintained (mlfoundations/open_clip, MIT code; weights vary - check per checkpoint; UNVERIFIED), CPU ViT-B/32 is fast (UNVERIFIED rate). Cons: decade classes overlap 1990-2005 (requirements); CLIP is weak at fine-grained dating. Verdict: **Viable** as tiebreaker; low fusion weight.
- Cheap non-ML cues (print border, aspect ratio, scan DPI, EXIF Software tag, JPEG quantization) - build; **Recommended** as free features.
- Claude vision era classification: see section 2; **Viable** opt-in.
- Training a custom classifier on Tyler's anchors: **Not recommended** (sparse labels, per requirements risk).

## 4. Photo date estimation / fusion
- No library exists for anchor-calibrated, confidence-weighted date fusion with birth-date and folder-year bounds (none found in searches; UNVERIFIED negative). It is domain logic, small, and deterministic.
- Verdict: **Build** (pure functions + plain-function tests per repo convention). Correctness risk is low if kept to interval intersection + weighted vote + hard bounds; avoid LLM-written statistics (section 7).
- Alternative buys: Immich/PhotoPrism infer dates only from metadata/filename, not content - no help.

## 5. Plugin framework
- pluggy (pytest's hook system): mature, MIT; latest seen 1.5.0 (Apr 2024, secondary https://data.safetycli.com/packages/pypi/pluggy; newer may exist - UNVERIFIED). Pros: hook specs, ordering, validation. Cons: designed for entry-point discovery of installed packages; adds ceremony for 3-5 in-repo plugins; PEP 723 script deps must include every plugin's deps anyway.
- stevedore / entry points: **Not recommended** (needs installed distribution; this is a uv script).
- Build: a `Plugin` Protocol (`name`, `requires`, `analyze(file) -> Vote`), a dict registry populated by a directory scan of `plugins/*.py` or explicit imports, results cached in sqlite keyed by (file hash, plugin name, plugin version). ~40 lines.
- Verdict: simple registry **Recommended**; pluggy **Viable** (if hook-based cross-plugin events are wanted); stevedore **Not recommended**.

## 6. EXIF writing
- exiftool subprocess (current): VERIFIED in `metadata.py` (chunked argfile batches). Pros: de facto standard, handles formats/quirks, `_original` backup, `-overwrite_original`/journal friendly. Cons: external binary (already required).
- PyExifTool 0.5.6 (https://pypi.org/project/PyExifTool/ ; release date Oct 2023 per https://www.piwheels.org/project/pyexiftool): batch mode via persistent process, JSON parse. Pros: cleaner reads. Cons: stale-ish; needs exiftool >= 12.15; existing argfile approach already batches.
- Pure-Python (piexif, Pillow): **Not recommended** (no HEIC/video/XMP breadth, corruption risk).
- Verdict: keep exiftool subprocess **Recommended**; PyExifTool **Viable** for the read/audit side; add a before-value journal (requirements Risk Control) around existing writes.

## 7. Google Photos upload / audit / redating
Key constraint (VERIFIED, https://developers.google.com/photos/library/support/release-notes and https://developers.google.cn/photos/support/updates?hl=en): since 2025-04-01 the `photoslibrary.readonly`, `.sharing`, and full `photoslibrary` scopes were removed; remaining scopes are `appendonly`, `readonly.appcreateddata`, `edit.appcreateddata`. List/search/get return only items the app created. Whole-library selection goes through the Picker API.
Implication: an API client created by Tyler can only see items it uploaded itself. Items uploaded earlier by rclone's OAuth client are visible only if the same client ID is used (UNVERIFIED - rclone docs state it can only download photos it uploaded: https://tip.rclone.org/googlephotos/). Date edit of existing items: I found no API method for it (UNVERIFIED negative; the `edit.appcreateddata` scope is for editing app-created content, whose scope of "edit" - e.g. album membership vs. creation time - is UNVERIFIED and must be read from the REST reference).
Other rclone facts (VERIFIED, https://tip.rclone.org/googlephotos/ via search): uploads original quality; albums only for ones rclone created; API cannot permanently delete media; downloaded images lose EXIF location. Daily request quota ~10k/project cited from forum (UNVERIFIED: https://forum.rclone.org/t/working-with-google-photos-all-requests-quota-limit-10k/34349).

Options:
- rclone copy (current): **Recommended for upload** (works, resumable, quota handling already added); date comes from embedded EXIF written beforehand.
- Direct Library API (`appendonly` upload, `mediaItems.batchCreate`): **Viable** - gives per-item IDs and `creationTime` read-back for app-created items, enabling a real audit. Cost: own OAuth client + token refresh code; verify first that rclone and the API client share a client ID or the audit will not see rclone's 7,757 uploads.
- Audit via Picker API: **Viable** - user picks items in a UI, app receives `createTime`; manual, but covers non-app items. Detail UNVERIFIED (not read).
- Google Takeout export parse (JSON sidecars hold `photoTakenTime`): **Viable** for one-off audit of everything already uploaded; slow (hours/days) but needs no API. UNVERIFIED in this session; well known behavior.
- Redating existing items: no automated route found -> web UI "Edit date & time" for small batches, trash + re-upload with corrected EXIF for large ones (deleting is web-UI only per rclone docs). Verdict: automate detection and re-upload set generation; **document/assist** the deletion step.
- Google Photos Ultra-fragile unofficial clients (reverse-engineered mobile API, e.g. gpmc-type tools): **Not recommended** - ToS/account risk, UNVERIFIED, not researched.

## 8. LLM-written bespoke vs battle-tested library: correctness risk per algorithm

| Algorithm | Risk if LLM-written from scratch | Decision |
|---|---|---|
| Face detection / embedding | Very high (models + preprocessing alignment) | Library, never bespoke |
| Clustering (HDBSCAN) | High (density tree, tie handling) | sklearn |
| Age regression | Very high | Library or cloud |
| CLIP zero-shot | High | open_clip |
| Interval/weight date fusion | Low-medium; testable with property tests | Build, with tests on anchors |
| Birth-date/folder-year guards | Low | Build |
| Plugin registry + sqlite cache | Low | Build |
| EXIF tag writing | Medium-high (format quirks, corruption) | exiftool |
| Quota/backoff logic | Low-medium; already written, unexercised | Build; exercise with a fake 429 |

## 9. Fork / adapt candidates
- Immich ML service (AGPL-3.0) uses InsightFace + HDBSCAN-like clustering; forking it brings AGPL obligations and Docker coupling for no gain over calling the same libraries directly. **Not recommended.**
- Existing gphotos tools (e.g. takeout metadata fixers such as google-photos-takeout-helper, gpth): not researched in this session (UNVERIFIED); could inform audit/Takeout parsing. **Viable to inspect** before writing a Takeout parser.
- InsightFace example scripts for clustering/age: **Viable** as reference only.

## Cost summary (17k images, my arithmetic on unverified/secondary rates)
- Local pipeline: $0; est. 1-3 CPU-hours for InsightFace (UNVERIFIED, benchmark first).
- Rekognition DetectFaces: ~$17; Google Vision faces: ~$24 (no age).
- Claude Haiku 4.5 all images: ~$40; 10% subset: ~$4.
- Privacy: all cloud options upload face imagery; gate behind `--allow-cloud`, log counts per run.

## Gaps to close before locking decisions
1. Open InsightFace GitHub README for the exact current license text and latest PyPI version.
2. Open platform.claude.com pricing + vision docs for current Haiku/Sonnet rates and image-token formula; AWS Rekognition official pricing page and `AgeRange` width.
3. Read Library API REST reference for `edit.appcreateddata` methods (can any set creation time?) and Picker API fields.
4. Benchmark InsightFace on 200 sample scans (CPU speed, face-found rate, age error vs anchors).
5. Check PhotoPrism and digiKam licenses/face stores only if the label-import plugin is wanted.
