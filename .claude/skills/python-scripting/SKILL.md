---
name: python-scripting
description: Standards for writing standalone Python scripts — UV inline deps, loguru logging, typer CLI, exit codes, and the canonical script template. References python-dependency-management for dep management.
paths: "**/*.py"
---

# Python Scripting Standards

For **library/service code** see `code-python`. This skill is for **standalone scripts** — one-file tools, automation scripts, data processing jobs.

---

## Dependency management

Always use UV inline metadata (PEP 723). See [[python-dependency-management]] for full reference.

```python
#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "typer>=0.12",
#   "loguru>=0.7",
# ]
# ///
```

Run with `uv run script.py` — UV creates an isolated env automatically.

---

## Canonical script template

```python
#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "typer>=0.12",
#   "loguru>=0.7",
# ]
# ///
"""One-line description of what this script does."""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from loguru import logger

app = typer.Typer(add_completion=False)


@app.command()
def main(
    input_path: Path = typer.Argument(..., help="Input file", exists=True),
    output_dir: Path = typer.Option(Path("."), "--output-dir", "-o", help="Output directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """One-line description repeated for --help."""
    if not verbose:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    logger.info("Processing {}", input_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ... work ...

    logger.success("Done → {}", output_dir)


if __name__ == "__main__":
    app()
```

---

## Logging with loguru

Use `loguru` for scripts (not `structlog` — that's for services).

```python
from loguru import logger

# Default: goes to stderr, colored, with level filtering
logger.debug("detail: {}", value)
logger.info("step started")
logger.warning("unusual but OK: {}", msg)
logger.error("something failed: {}", err)
logger.success("all done")          # green INFO-level

# Add a log file alongside stderr:
logger.add("run.log", rotation="10 MB", retention=3)

# Structured context:
logger.bind(file=path, step="parse").info("processing")

# Exception with full traceback:
try:
    ...
except Exception:
    logger.exception("unexpected failure")
    sys.exit(1)
```

---

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (caught exception, bad input) |
| 2 | CLI misuse (typer handles this automatically) |
| 3+ | Domain-specific codes (document them in the script's docstring) |

```python
# Typer raises SystemExit automatically on bad args.
# For runtime errors, raise typer.Exit(code=1) or sys.exit(1).

try:
    process(path)
except FileNotFoundError as e:
    logger.error("Input not found: {}", e)
    raise typer.Exit(1)
```

---

## File I/O patterns

```python
from pathlib import Path

# Read
text = Path("file.txt").read_text()
data = Path("file.json").read_bytes()

# Write (atomic: write to tmp, rename)
import tempfile, os
tmp = Path(output) .with_suffix(".tmp")
tmp.write_bytes(result)
tmp.rename(output)

# Iterate directory
for ply in Path(input_dir).glob("*.ply"):
    process(ply)
```

---

## Progress bars

For long-running scripts with iterables:

```python
# /// script
# dependencies = ["typer>=0.12", "loguru>=0.7", "rich>=13"]
# ///
from rich.progress import track

for item in track(items, description="Processing..."):
    process(item)
```

---

## When NOT to use this pattern

| Situation | Use instead |
|-----------|-------------|
| > 3 files that share logic | `code-python` project layout |
| Needs a test suite | `pyproject.toml` + `uv add --dev pytest` |
| Long-running service / daemon | Service architecture (code-python + structlog) |
| Jupyter exploration | Jupyter notebook |
