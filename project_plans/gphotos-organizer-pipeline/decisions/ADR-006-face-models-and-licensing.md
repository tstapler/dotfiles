# ADR-006: InsightFace buffalo_l for faces (non-commercial weights), YuNet+SFace fallback

**Status**: Accepted; speed settings pending spike (Story 4.1) · **Plan**: Stories 4.1, 4.3, 4.7, 5.1

## Context
InsightFace code is MIT but its pretrained models, including `buffalo_l`, are "non-commercial research purposes only" (VERIFIED: https://github.com/deepinsight/insightface/tree/master/model_zoo, per `research/pitfalls.md` s3). CPU speed for 17k images is UNVERIFIED (`research/stack.md` s1). Age estimators reach about 4-6 years MAE on clean faces; no benchmark was found for faded scans.

## Decision
- Use `insightface` `buffalo_l` (SCRFD detector + ArcFace 512-d + `genderage`) on CPU ONNX for personal, non-commercial use. This ADR records the license limit: do not publish or commercialize the tool with these weights.
- Keep the model pack name in config; provide OpenCV Zoo YuNet + SFace (Apache-2.0 claimed, UNVERIFIED primary) as a license-clean fallback (Story 4.7). Embeddings carry `model_id`; clustering runs per model.
- Clustering: scikit-learn HDBSCAN on L2-normalised embeddings, seeded, inputs sorted by `FaceId`; owner must-link / cannot-link constraints override it; noise stays unknown.
- Age is strong evidence only for children; adults are capped until calibrated against anchors by decade and color vs B&W. Grayscale/equalize before age inference.
- MiVOLO is evaluated optionally; adopted only if its weight license permits personal use (UNVERIFIED).

## Spike outcome
*(To fill in Story 4.1: images/sec, extrapolated total for 17,145 images, chosen `det_size`/pack, CPU model and onnxruntime version.)*

## Alternatives rejected
dlib `face_recognition` (unmaintained since 2020, compile needed); DeepFace (TensorFlow weight, inherits backend licenses); Immich/digiKam as backend (server stack; labels only importable as name-to-file mappings).
