# Technology Stack Research: cfgcaddy Feature Expansion

## Summary

Research into the specific technology choices for implementing the five new cfgcaddy features (templating, alternate file scoring, profiles, diff, doctor). Covers template engines, TOML parsing, diff output, Click patterns, existing test structure, and current dependencies.

---

## 1. Jinja2 vs Other Template Engines

### Decision: Jinja2 (requirements already specify this)

The requirements explicitly call for Jinja2, and it is the right choice for this use case.

**Current version:** Jinja2 3.1.6 (released March 5, 2025). Dependency pin: `jinja2>=3.1.0`.

### Key API choices

**Environment with StrictUndefined** — the most important configuration decision. The default `Undefined` type silently renders missing variables as empty strings. For dotfiles this is a silent corruption bug. Use `StrictUndefined` instead:

```python
from jinja2 import Environment, StrictUndefined

env = Environment(undefined=StrictUndefined)
template = env.from_string(source_text)
try:
    rendered = template.render(**variables)
except jinja2.UndefinedError as e:
    # e.message includes the variable name — surface this to the user
    raise CfgcaddyError(f"Template variable missing: {e}")
```

**Autoescape — must be disabled for dotfiles.** Jinja2's autoescape is designed for HTML/XML. For shell scripts, config files, and arbitrary text, `autoescape=False` (the default) is correct. Do not enable it.

### Shell script gotchas (important)

Bash uses `$VAR`, `${VAR}`, `${#ARRAY[@]}` syntax. Jinja2 uses `{{ var }}` and `{% block %}`. These do not conflict directly because Jinja2 only processes `{{`, `{%`, and `{#` delimiters — bare `$` and `${}` are left untouched.

However, there is one real conflict: bash arithmetic expansion uses `$(( ... ))`. If a shell script contains `$((expr))`, Jinja2 will not try to parse it (the opening is `$((` not `{{`), so this is safe.

The actual gotcha is `{% raw %}` blocks. If a dotfile template contains literal `{{ }}` or `{% %}` characters that should NOT be processed by Jinja2 (e.g., a `.zshrc` that references a tool using those strings), wrap those sections in `{% raw %}...{% endraw %}`. Document this in `cfgcaddy secrets init` output.

**Recommendation:** Use `Environment(undefined=StrictUndefined, autoescape=False)` with `from_string()` to render each `.tmpl` file's content directly.

---

## 2. tomllib (3.11+) vs tomli Backport for 3.10

### Decision: Conditional dependency with environment marker

The requirements specify Python 3.10+ compatibility. The current `pyproject.toml` declares `requires-python = ">=3.7"` (to be bumped to 3.10+ for this feature work).

**Correct `pyproject.toml` dependency declaration:**

```toml
dependencies = [
    # ... existing deps ...
    "jinja2>=3.1.0",
    "tomli>=1.1.0; python_version < '3.11'",
]
```

The environment marker `; python_version < '3.11'` ensures `tomli` is only installed on Python 3.10 and below. On Python 3.11+, the stdlib `tomllib` is used automatically.

**Correct import pattern in code:**

```python
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[no-redef]
```

This is the canonical pattern used by virtually every Python library that bridges this stdlib transition (e.g., `black`, `pip`, `poetry`).

**Note:** `tomllib` (stdlib) and `tomli` are read-only — they have no write/serialize API. For writing `local.toml` (during `cfgcaddy secrets init`), use `tomli-w` or simply write TOML manually since the structure is simple enough. Adding `tomli-w` as an optional dep is cleaner than hand-rolling a serializer.

---

## 3. Colored Diff Output: difflib vs rich vs others

### Decision: `rich` for display + `difflib.unified_diff` for generation

**Analysis:**

| Option | Pros | Cons |
|--------|------|------|
| `difflib` stdlib only | Zero deps | No color, output is plain text |
| `rich.Syntax` with "diff" lexer | Excellent color, already used in cfgcaddy ecosystem (questionary pulls it in transitively), one line of code | Requires `rich` as explicit dep |
| `ydiff` | Beautiful side-by-side | Heavy dep, overkill |
| Raw ANSI codes | No deps | Fragile, hard to maintain |

**Best approach:** Generate the diff text with stdlib `difflib.unified_diff`, then render it using `rich.Syntax` with the `"diff"` lexer:

```python
import difflib
from rich.console import Console
from rich.syntax import Syntax

def show_diff(old_text: str, new_text: str, filename: str) -> None:
    lines = list(difflib.unified_diff(
        old_text.splitlines(keepends=True),
        new_text.splitlines(keepends=True),
        fromfile=f"current:{filename}",
        tofile=f"new:{filename}",
    ))
    if not lines:
        return
    diff_text = "".join(lines)
    console = Console()
    console.print(Syntax(diff_text, "diff", theme="ansi_dark"))
```

This gives standard green/red diff coloring with zero custom ANSI code management. `difflib.unified_diff` exits code is handled by checking whether `lines` is empty.

**Dependency addition:** `rich>=10.0.0` should be added to `pyproject.toml`. Note: `questionary` (already a dep) requires `prompt_toolkit`, not `rich`, so there is no transitive free-ride — `rich` must be declared explicitly.

---

## 4. Click Patterns for Shared State Across Subcommands

### Decision: `ctx.obj` with a typed state dataclass + `@click.pass_obj`

The requirements need `--profile` to be available as a global flag resolved before any subcommand runs, and subcommands like `link`, `diff`, and `doctor` all need access to the resolved profile, config path, and local.toml variables.

Click's canonical pattern for this is `ctx.obj`:

```python
import click
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class CfgcaddyContext:
    config_path: str
    profile: Optional[str]
    # resolved after loading:
    variables: dict = field(default_factory=dict)

pass_cfg = click.make_pass_decorator(CfgcaddyContext, ensure=True)

@click.group()
@click.option("--profile", envvar="CFGCADDY_PROFILE", default=None)
@click.option("--config", default=".cfgcaddy.yml")
@click.pass_context
def cli(ctx: click.Context, profile: Optional[str], config: str) -> None:
    ctx.ensure_object(CfgcaddyContext)
    ctx.obj = CfgcaddyContext(config_path=config, profile=profile)

@cli.command()
@pass_cfg
def link(cfg: CfgcaddyContext) -> None:
    # cfg.profile, cfg.variables available here
    ...
```

**Profile resolution order** (from requirements) maps cleanly to this:
1. `--profile` CLI flag → set in `cli()` group callback
2. `CFGCADDY_PROFILE` env var → `envvar="CFGCADDY_PROFILE"` on the option
3. `default_profile` in `.cfgcaddy.yml` → fall back in `cli()` after loading config
4. No profile → `None`

`click.make_pass_decorator` is preferred over raw `@click.pass_obj` for type safety — it ensures the object type is correct and can auto-create it if missing.

**Subcommand groups** (`cfgcaddy profiles list`, `cfgcaddy secrets init`) should be added as `@cli.group()` nested groups, with commands registered under them. The `ctx.obj` propagates automatically through all nesting levels.

---

## 5. Existing Test Structure

### Pattern summary

The test suite uses **two testing styles** that should both be followed for new features:

**Style A: `unittest.TestCase` with file system fixtures** (`test_linker.py`, `test_utils.py`, `test_config.py`)
- Base class: `FileLinkTestCase` in `tests/__init__.py`
- Sets up `self.source_dir`, `self.dest_dir` as `tempfile.mkdtemp()` directories
- `setUp`/`tearDown` manage temp dir lifecycle
- Helpers: `create_files_from_tree(tree_dict, parent=dir)` creates a dict-described file tree
- Assertion helper: `assertDestMatchesExpected()` compares `dir_dict(dest)` to `self.expected_tree`
- Used for: testing `Linker` class behavior, config loading, symlink operations

**Style B: pytest-native with `tmp_path`** (`test_link.py`, `test_end_to_end.py`)
- Uses `@pytest.mark.parametrize` with dataclass test cases (`LinkTestCase`)
- Uses pytest's `tmp_path` fixture instead of `tempfile.mkdtemp()`
- Used for: testing `Link` objects, end-to-end integration

**Recommendation for new tests:** Use **Style B (pytest-native)** for all new tests. The `tmp_path` fixture and parametrize approach is cleaner and more readable. Use dataclass test cases for the alternate file scoring feature (many permutations). Use simple function-based pytest tests for `diff` and `doctor` commands.

**No test runner configuration** was found in `pyproject.toml` — tests are run with `pytest` directly. No `[tool.pytest.ini_options]` section exists, so add one when writing template rendering tests that need environment setup.

---

## 6. Current cfgcaddy Dependencies

From `/Users/tylerstapler/dotfiles/cfgcaddy/pyproject.toml`:

```toml
requires-python = ">=3.7"

dependencies = [
    "click>=8.0.0",
    "pathspec>=0.8.1",
    "ruamel.yaml>=0.16.12",
    "questionary>=1.9.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "ruff>=0.1.0",
    "mypy>=0.940",
    "python-semantic-release>=7.26.0",
]
```

**Proposed additions for this feature set:**

```toml
dependencies = [
    "click>=8.0.0",
    "pathspec>=0.8.1",
    "ruamel.yaml>=0.16.12",
    "questionary>=1.9.0",
    # New:
    "jinja2>=3.1.0",
    "rich>=10.0.0",
    "tomli>=1.1.0; python_version < '3.11'",
    "tomli-w>=1.0.0",   # for writing local.toml during secrets init
]
```

**Note on `requires-python`:** The current `>=3.7` is inconsistent with the ruff config (`UP006`/`UP007`/`UP045` suppression comments acknowledge 3.7-3.9 compat). The requirements doc specifies Python 3.10+. The `pyproject.toml` `requires-python` should be bumped to `>=3.10` as part of this PR, which also allows removing those three ruff suppression entries and cleaning up the `sys.version_info` guard for `tomllib`.

**Build system:** Uses `hatchling`. No changes required to `[build-system]`.

---

## Sources

- [Jinja2 PyPI (3.1.6)](https://pypi.org/project/Jinja2/)
- [Jinja2 Docs: StrictUndefined](https://jinja.palletsprojects.com/en/stable/api/)
- [tomllib Python 3.11 docs](https://docs.python.org/3/library/tomllib.html)
- [tomli GitHub (hukkinj1)](https://github.com/hukkinj1/tomli)
- [Click Docs: Nested Commands / ctx.obj](https://click.palletsprojects.com/en/stable/commands/)
- [Rich Docs: Syntax highlighting](https://rich.readthedocs.io/en/stable/reference/syntax.html)
- [Colored diff output with Python (chezsoi.org)](https://chezsoi.org/lucas/blog/colored-diff-output-with-python.html)
