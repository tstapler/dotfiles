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

### Lockfile hygiene — pin the index in the project, not the machine

`uv.lock` records the **index URL** each package came from. So a machine
configured against a private or corporate mirror rewrites *every* URL in the lock
on any resolve — and `uv run` resolves by default:

```bash
uv run pytest             # re-resolves; can rewrite the whole lock as a side effect
uv run --frozen pytest    # does not touch the lock
```

That produces a diff of thousands of near-identical lines that nobody reads, and
`git add -A` sweeps it straight in. On a public repo the consequences are worse
than noise: it publishes an internal hostname, and it breaks CI, which cannot
reach the mirror.

**Diagnose before blaming the tool.** It is almost never a patched or forked `uv`.
Check, in order:

```bash
which -a uv && uv --version         # is it actually the stock binary?
env | grep -i '^UV_\|^PIP_'         # env overrides
cat ~/.config/uv/uv.toml            # user-level config — the usual culprit
cat ~/.config/pip/pip.conf          # pip's, which some tooling also honours
```

A user-level `index-url` in `~/.config/uv/uv.toml` applies to **every project on
the machine**, public ones included. That is the bug: private configuration in a
global scope.

**Fix it in the project.** uv's precedence is CLI > environment > project config >
user config > system config, so the repo can override the machine — which means
the fix is committed and protects every contributor, every CI run, and every agent
session, instead of depending on someone remembering an env var:

```toml
# pyproject.toml — resolve against the public index whatever the machine says
[[tool.uv.index]]
url = "https://pypi.org/simple"
default = true
```

Verify it rather than assuming: with the user config still pointing at the mirror,
a bare `uv run pytest` should leave `uv.lock` untouched.

```bash
uv run pytest && git status --short   # uv.lock must not appear
```

Prefer this to the alternatives: `export UV_DEFAULT_INDEX=…` and habitual
`uv run --frozen` both depend on remembering them every session, and `--frozen`
additionally hides a genuinely stale lock. `.envrc`/direnv isn't committed, so it
only protects whoever has direnv set up.

The mirror-image fix is worth doing too: move the private index config out of the
user-level file and into the private repos that need it. Private configuration
belongs where the private code is.

**Guard it in CI**, since prevention and detection are different jobs:

```yaml
- run: uv lock --check          # lock is in sync with pyproject
- run: |                        # ...and references only the public index
    if grep -n 'registry = "' uv.lock | grep -v 'https://pypi.org/simple'; then
      echo "::error file=uv.lock::uv.lock references a non-public index"; exit 1
    fi
```

Note that `uv lock --check` **fails on the mirrored machine and passes in CI**,
because CI has no user config. If it fails locally, re-run it with the public
index forced before concluding the lock is genuinely stale:

```bash
UV_DEFAULT_INDEX=https://pypi.org/simple uv lock --check
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
