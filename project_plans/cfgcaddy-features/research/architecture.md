# Architecture Research: cfgcaddy Feature Expansion

## Codebase Summary

The existing system has a clean, minimal layered structure:

```
__main__.py          CLI entry point (click group + commands)
config.py            LinkerConfig — reads .cfgcaddy.yml, calls generate_links()
linker.py            Linker — orchestrates create_links() + create_custom_links()
link.py              Link(LinkSpec) — create() implements the actual symlink/copy logic
link_spec.py         LinkSpec protocol + LinkingResult flag
file_state.py        FileState enum — classifies dest/src path states
utils.py             Pure helpers: expand_path, user_confirm, copy_file_or_dir, etc.
__init__.py          Constants: DEFAULT_CONFIG_PATH, HOME_DIR, LinkMode
```

Data flow today:

```
.cfgcaddy.yml
  └─ LinkerConfig.__init__()
       ├─ read_config()          ← parse YAML
       └─ generate_links()       ← produce List[Link] stored as self.links
             Linker.create_links()       ← find_absences() → create_links()
             Linker.create_custom_links() ← Link.create() per explicit link
```

---

## Design Questions & Answers

### 1. Where does local data file loading fit into the config/linker flow?

**Decision:** Introduce a `LocalDataLoader` in a new `data.py` module. It is instantiated by `LinkerConfig.__init__()` alongside the YAML read, so all downstream consumers (linker, template renderer, doctor, diff) receive a fully-resolved data dict.

`LinkerConfig` grows two new optional attributes:
- `self.local_data: dict` — merged result of `~/.config/cfgcaddy/local.toml` + profile overlay
- `self.profile: Optional[str]` — resolved from CLI flag / env / yaml default

`LocalDataLoader` is responsible for:
1. Loading `~/.config/cfgcaddy/local.toml` (returns `{}` if absent — opt-in, no error)
2. Loading `~/.config/cfgcaddy/profiles/<name>.toml` if a profile is active
3. Merging: profile values override base values (shallow merge at top level, deep merge within tables)
4. Returning the merged dict

This keeps `config.py` as the single source of truth for all runtime state; nothing else reads TOML files directly.

```python
# config.py (additions only)
from cfgcaddy.data import LocalDataLoader

class LinkerConfig:
    def __init__(self, config_file_path=None, default_config=None, profile=None):
        ...
        self.profile = profile
        loader = LocalDataLoader(profile=self.profile)
        self.local_data = loader.load()
        self.generate_links(self.links_yaml)
```

### 2. Where does template rendering happen — before or after link resolution? What is the data flow?

**Decision:** Rendering is a **pre-link transformation** applied to the source path. The `TemplateRenderer` in a new `template.py` module converts `.tmpl` source files into rendered files written to `~/.cache/cfgcaddy/rendered/<relative-path-without-.tmpl>`, and returns the cache path as the effective source. Link resolution then proceeds normally against the cache path.

Rendering happens inside `generate_links()` in `config.py`, not in `Linker` or `Link`, because that is where `src_path` strings are converted to `Link` objects. The intercepting point is the inner loop in `generate_links()`:

```
for src_path in src_files:
    effective_src = renderer.render_if_template(src_path)  # NEW
    custom_links.append(Link(effective_src, dest_path, ...))
```

Full data flow:

```
.cfgcaddy.yml + local.toml + profile.toml
  └─ LinkerConfig.__init__()
       ├─ LocalDataLoader.load()        → local_data dict
       ├─ TemplateRenderer(local_data)  → renderer instance
       └─ generate_links()
            for each src_path:
              ├─ AlternateSelector.select(src_path)    → winning src
              └─ renderer.render_if_template(winning_src)
                   ├─ if .tmpl: render with Jinja2, write to ~/.cache/cfgcaddy/rendered/
                   │    raise TemplateMissingVariableError on undefined var
                   └─ else: return src unchanged
            → Link(effective_src, dest_path)
```

`TemplateRenderer.render_if_template()` must be idempotent (check mtime of source vs cache before re-rendering).

### 3. How does alternate file scoring integrate into generate_links() in config.py?

**Decision:** Introduce `AlternateSelector` in a new `alternate.py` module. It is used inside `generate_links()` **before** template rendering, operating on the raw filenames returned by `glob.glob()`.

Current `generate_links()` groups files matched by `glob.glob(path.join(self.linker_src, link_src))`. The new flow:

1. `find_absences()` in `link.py` — used for the auto-discovered (non-explicit) links — must also apply alternate scoring. This requires a new `AlternateSelector`-aware wrapper around the `os.walk` loop.
2. For explicit links in `generate_links()`, after globbing, call `AlternateSelector.select(candidates)` to pick the best match.

`AlternateSelector` is a pure-function utility:
- `parse_suffixes(filename) -> (base_name, list[tuple[key, value]])` — strips and parses `##` segments
- `score(filename, context) -> int` — context contains `os`, `hostname`, `profile`
- `select(candidates: list[Path]) -> Optional[Path]` — returns highest-scoring path, or `None` if no candidates match; raises `AmbiguousAlternateError` if two paths tie

Context object is built once from the environment in `LinkerConfig.__init__()`:

```python
self.alternate_context = AlternateContext(
    os=platform.system().lower(),
    hostname=socket.gethostname(),
    profile=self.profile,
)
```

**Ignore pattern integration:** The `ignore_patterns` check in `find_absences()` is applied to the **base name** (before `##`) using `AlternateSelector.parse_suffixes(f)[0]`.

### 4. How do new CLI commands (diff, doctor, secrets, profiles) attach to __main__.py?

**Decision:** Each command group is implemented in a dedicated module and registered on the existing `main` click group in `__main__.py`. No structural change to the existing `link` or `init` commands.

```python
# __main__.py additions
import cfgcaddy.commands.diff as diff_cmd
import cfgcaddy.commands.doctor as doctor_cmd
import cfgcaddy.commands.secrets as secrets_cmd
import cfgcaddy.commands.profiles as profiles_cmd

main.add_command(diff_cmd.diff)
main.add_command(doctor_cmd.doctor)
main.add_command(secrets_cmd.secrets)
main.add_command(profiles_cmd.profiles)
```

All new commands follow the same pattern as `link`: accept `-c/--config`, instantiate `LinkerConfig`, then do their work. The `--profile` option is hoisted to the `main` group using `@click.pass_context` + `@click.option("--profile")` so every subcommand inherits it.

`link` gains `--dry-run` as an alias for `diff`:

```python
@main.command()
@click.option("--dry-run", is_flag=True, help="Preview changes without applying (alias for diff)")
def link(config, no_interactive, dry_run):
    if dry_run:
        ctx.invoke(diff_cmd.diff, config=config)
        return
    ...
```

### 5. Which new modules should be created vs extending existing ones?

**New modules (new files):**

| Module | Path | Responsibility |
|--------|------|----------------|
| `data.py` | `cfgcaddy/data.py` | `LocalDataLoader` — load/merge TOML data files |
| `template.py` | `cfgcaddy/template.py` | `TemplateRenderer` — Jinja2 render + cache management |
| `alternate.py` | `cfgcaddy/alternate.py` | `AlternateSelector` — `##` suffix parsing and scoring |
| `commands/diff.py` | `cfgcaddy/commands/diff.py` | `diff` click command — dry-run link preview |
| `commands/doctor.py` | `cfgcaddy/commands/doctor.py` | `doctor` click command — audit checks |
| `commands/secrets.py` | `cfgcaddy/commands/secrets.py` | `secrets` click command group (init) |
| `commands/profiles.py` | `cfgcaddy/commands/profiles.py` | `profiles` click command group (list, init) |

**Existing modules — minimal, additive changes only:**

| Module | Changes |
|--------|---------|
| `config.py` | Add `profile`, `local_data`, `alternate_context` attributes; inject `AlternateSelector` and `TemplateRenderer` into `generate_links()`; inject `AlternateSelector` into `find_absences()` call path |
| `link.py` | `find_absences()` — apply base-name ignore matching; no logic changes to `Link.create()` |
| `linker.py` | No changes required for core features; `Linker` may gain a `dry_run` mode for `diff` |
| `__main__.py` | Add `--profile` to `main` group; register new command modules; add `--dry-run` to `link` |
| `__init__.py` | Add constants: `LOCAL_DATA_PATH`, `PROFILES_DIR`, `RENDERED_CACHE_DIR` |

### 6. How does the rendered template cache integrate with symlink creation in link.py?

**Decision:** `TemplateRenderer` writes rendered output to `~/.cache/cfgcaddy/rendered/<relative-source-path-without-.tmpl>`. The `Link` object is constructed with this **cache path as `src`** — `Link` itself is unaware of templating.

Cache path construction:

```python
# template.py
RENDERED_CACHE_DIR = Path.home() / ".cache" / "cfgcaddy" / "rendered"

def _cache_path(self, src: Path) -> Path:
    # Remove .tmpl suffix, preserve relative structure under linker_src
    rel = src.relative_to(self.linker_src).with_suffix("")
    return RENDERED_CACHE_DIR / rel
```

This means:
- `~/dotfiles/shell/secrets.op.sh.tmpl` → rendered to `~/.cache/cfgcaddy/rendered/shell/secrets.op.sh`
- Symlink target at `~/.shell/secrets.op.sh` → points to `~/.cache/cfgcaddy/rendered/shell/secrets.op.sh`
- The rendered cache file is outside the git repo by design (in `~/.cache/`)

**Staleness check:** Before re-rendering, compare `src.stat().st_mtime` and `local.toml.stat().st_mtime` against `cache_path.stat().st_mtime`. Re-render only when source or data is newer.

**`diff` integration:** For template files, `diff` reads the current symlink target (if exists) and compares it against a freshly rendered buffer (without writing to cache), then outputs a unified diff.

---

## Module Breakdown

```
cfgcaddy/
├── __init__.py           (extend: add cache/config path constants)
├── __main__.py           (extend: --profile on main, register new commands, --dry-run on link)
├── config.py             (extend: local_data, alternate_context, inject renderer+selector)
├── data.py               (NEW: LocalDataLoader — TOML load, profile merge)
├── template.py           (NEW: TemplateRenderer — Jinja2 render, cache read/write)
├── alternate.py          (NEW: AlternateSelector — ## parsing, scoring, selection)
├── link.py               (extend: base-name ignore matching in find_absences)
├── linker.py             (extend: dry_run flag for diff)
├── link_spec.py          (unchanged)
├── file_state.py         (unchanged)
├── utils.py              (unchanged)
└── commands/
    ├── __init__.py       (NEW: empty package init)
    ├── diff.py           (NEW: diff command)
    ├── doctor.py         (NEW: doctor command with checks + --fix)
    ├── secrets.py        (NEW: secrets init wizard)
    └── profiles.py       (NEW: profiles list + init)
```

### Dependency graph (new modules only)

```
__main__.py
  └─ commands/{diff,doctor,secrets,profiles}.py
       └─ config.py (LinkerConfig)
            ├─ data.py (LocalDataLoader)
            ├─ template.py (TemplateRenderer)
            │    └─ data.py (local_data dict)
            └─ alternate.py (AlternateSelector)
                 └─ utils.py (expand_path)
```

No circular dependencies. All new modules import from the existing core; nothing in the existing core imports from new modules except `config.py`, which is the intentional integration point.

---

## Key Constraints Respected

- `cfgcaddy link` with no `local.toml` and no `##` files: zero code-path difference from today
- `Link.create()` is untouched — it always receives a resolved, concrete `src` path
- All new features activate only when their inputs are present (local.toml, `.tmpl` files, `##` suffixes)
- New dependencies (`jinja2`, `tomllib`/`tomli`) are isolated to `template.py` and `data.py`
