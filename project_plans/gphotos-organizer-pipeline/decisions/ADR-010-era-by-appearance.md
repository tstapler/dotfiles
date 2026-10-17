# ADR-010: Era-by-appearance is a low-weight tiebreaker from frozen embeddings plus an owner-trained regressor

**Status**: Accepted · **Plan**: Stories 6.1-6.4

## Context
Zero-shot CLIP dating on 1950-2000 photos has MAE about 15.8 years and is biased early; fine-tuned heads remove the bias (https://arxiv.org/pdf/2310.06633, via `research/stack.md` s3). Supervised baselines on DEW reach about 7 years MAE across a 70-year range (https://arxiv.org/abs/2106.05618). No ready-to-use dating weights were found. The collection has thousands of folder-dated photos usable as labels.

## Decision
- Extract frozen CLIP/SigLIP image embeddings (open_clip ViT-B/32 default; SigLIP optional) into the store, then fit a small ridge/logistic regressor over year bins on anchor and folder-dated photos, excluding the hold-out. Evidence is a wide interval with `weight_cap <= 0.25`, `correlation_group="appearance"`.
- Add free non-ML cues (border, aspect, color cast, scanner EXIF as scan-date upper bound only) and dHash near-duplicate groups.
- Optional cloud variant (ADR-005) is also low weight and image-only prompted.
- Accuracy is reported against the label-mean baseline (and zero-shot if enabled) on hold-out every run.

## Consequences
Useful to break ties and narrow wide intervals, never decisive alone. Retraining bumps only this plugin's version.

## Alternatives rejected
Zero-shot CLIP as the main signal (weak); training on DEW (1M images, out of scope); relying on a cloud LLM for all files (privacy, cost UNVERIFIED).
