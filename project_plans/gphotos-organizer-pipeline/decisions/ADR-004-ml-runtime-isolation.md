# ADR-004: Heavy ML plugins run in a separate uv script pinned to Python 3.12

**Status**: Accepted · **Plan**: Story 4.2 (also 3.5 OCR engine choice)

## Context
PEP 723 dependencies are fixed per script. `cli.py` must stay light (typer, loguru, rich, pydantic; `requires-python >= 3.11`). onnxruntime/insightface/scikit-learn/open_clip are heavy, and insightface wheels for Python 3.14 (system Python here is 3.14.7) are UNVERIFIED (`research/stack.md` s0).

## Decision
`G/analyze_ml.py` is a second PEP 723 script (`requires-python = ">=3.11,<3.13"`, run with `uv run --python 3.12`). `cli.py analyze` dispatches `runtime=Ml` plugins to it as a subprocess. The integration point is the shared SQLite schema (ADR-002), importing `pipeline/store.py`. A test asserts `cli.py`'s dependency block contains no ML packages.

## Consequences
`scan`, `upload`, `fuse`, `plan` never pay ML install cost; ML env can fail without breaking core commands. Two environments to maintain; the shared schema version is checked on ML script start.

## Addenda
OCR engine (tesseract vs rapidocr-onnxruntime) is chosen by the Story 3.5 spike and recorded here.

## Alternatives rejected
Heavy deps in `cli.py` (every `uv run` resolves them); per-call `uv run --with` (slow, unpinned Python).
