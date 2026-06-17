---
name: python-dependency-management
description: How to manage Python dependencies with UV — inline script metadata (PEP 723), project mode, tool running, and when to use each approach. Always use UV; never pip directly.
paths: "**/*.py,**/pyproject.toml,**/*.toml,**/*.sh"
---

# Python Dependency Management with UV

**Rule**: Always use `uv`. Never call `pip` directly. Never create virtualenvs manually.

---

## Mode 1 — Inline script metadata (PEP 723)

For standalone scripts that don't belong to a project. UV reads the `# /// script` block and creates a temporary isolated environment automatically.

```python
#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests>=2.31",
#   "rich>=13",
#   "cadquery",
# ]
# ///

import requests
from rich import print
```

Run:
```bash
uv run script.py          # UV reads the block, installs deps, runs
./script.py               # works if shebang is set (chmod +x first)
uv run --python 3.12 script.py   # override Python version
```

**When to use**: One-off scripts, exploratory scripts, scripts shipped as single files, CI helper scripts. No `pyproject.toml` needed.

**With extra deps at run time** (without editing the file):
```bash
uv run --with rich --with requests script.py
```

**With a specific package version pinned temporarily**:
```bash
uv run --with "cadquery==2.4.0" script.py
```

---

## Mode 2 — Project mode (pyproject.toml)

For packages, services, or anything with multiple files and a test suite.

```bash
uv init my-project        # scaffold pyproject.toml + src layout
cd my-project
uv add requests rich      # add to [project.dependencies]
uv add --dev pytest ruff  # add to [project.optional-dependencies] dev
uv sync                   # install everything into .venv
uv run pytest             # run inside the venv
uv run my-project         # run [project.scripts] entry point
```

Lock file is `uv.lock` — commit it. Reproducible installs on all machines.

```bash
uv sync --frozen          # CI: install exactly what's in the lock file, fail if out of date
uv lock --upgrade-package requests   # upgrade one dep without touching others
```

---

## Mode 3 — Tool running (uvx)

For CLI tools you want to run without polluting the project or global env.

```bash
uvx ruff check .          # run ruff without installing it
uvx black .               # run black
uvx cadquery-server       # spin up a tool temporarily
uvx --from cadquery cq-cli ...   # run a specific entry point from a package
```

`uvx` = `uv tool run` — installs into an isolated cache, reuses on subsequent calls.

**Install a tool globally** (available in PATH):
```bash
uv tool install ruff      # installs ruff globally via UV
uv tool upgrade ruff
uv tool list
```

---

## Mode 4 — pip compatibility shim

When you must interact with a requirements.txt or use pip-style commands (legacy projects, CI scripts):

```bash
uv pip install -r requirements.txt   # into current active venv
uv pip compile requirements.in -o requirements.txt   # pin versions
uv pip sync requirements.txt         # install exactly what's listed, remove extras
```

Avoid this mode for new projects — use Mode 2 instead.

---

## Choosing the right mode

| Situation | Mode |
|-----------|------|
| One-off script, no project structure | **Mode 1** — inline `# /// script` metadata |
| Exploring a library interactively | **Mode 1** — `uv run --with lib script.py` |
| Package / service / multi-file project | **Mode 2** — `pyproject.toml` + `uv add` |
| Running a CLI tool once | **Mode 3** — `uvx tool-name` |
| Integrating with legacy `requirements.txt` | **Mode 4** — `uv pip` |

---

## Environment and Python version management

```bash
uv python install 3.12    # install a specific Python version
uv python list            # show available versions
uv venv --python 3.12     # create a venv with a specific version (rare — prefer uv run)
```

UV manages its own Python downloads under `~/.local/share/uv/python/`.

---

## Common patterns

**Script that renders a mesh (inline deps):**
```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["trimesh[easy]>=4.0", "matplotlib>=3.8"]
# ///
import trimesh, matplotlib.pyplot as plt
```

**CI install (reproducible):**
```bash
uv sync --frozen --no-dev   # production deps only, exact lock
```

**Upgrade all deps:**
```bash
uv lock --upgrade            # re-resolve everything, update uv.lock
uv sync
```

**Check what's installed:**
```bash
uv pip list
uv tree                      # dependency tree for the current project
```
