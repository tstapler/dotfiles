# Implementation Plan: cfgcaddy Feature Expansion

This plan extends cfgcaddy with five capabilities — local data templating, alternate file scoring, profiles, a diff preview command, and a doctor audit command — while preserving all existing `cfgcaddy link` and `cfgcaddy init` behavior. Changes are organized by dependency order: each epic's output is required input for the next. All new features are strictly opt-in; a dotfiles repo with no `.tmpl` files, no `##`-suffixed files, and no `local.toml` follows exactly the same code path as today.

---

## Epic 1: Foundation

**Goal:** Add the four new runtime dependencies to `pyproject.toml`, add path constants to `__init__.py`, create the `data.py` TOML loader, introduce the `CfgcaddyContext` dataclass for Click state, hoist `--profile` onto the `main` group, and wire `LocalDataLoader` into `LinkerConfig`. No user-visible behavior changes; this is the shared substrate for Epics 2–6.

---

### Story 1.1: Dependency and metadata updates

**Tasks:**
- [ ] Task: In `pyproject.toml`, change `requires-python` from `">=3.7"` to `">=3.10"`. Update `[tool.ruff] target-version` to `"py310"` and `[tool.mypy] python_version` to `"3.10"`. Remove the three `UP006`, `UP007`, `UP045` ruff `ignore` entries.
  - Acceptance criteria: `uv sync` completes without error; ruff reports no violations on existing source files after the UP* ignore removals.

- [ ] Task: In `pyproject.toml` `[project.dependencies]`, add `"jinja2>=3.1.0"`, `"rich>=10.0.0"`, `"tomli>=1.1.0; python_version < '3.11'"`, and `"tomli-w>=1.0.0"`.
  - Acceptance criteria: `uv sync` installs all four packages; `python -c "import jinja2, rich, tomli_w"` succeeds on Python 3.10 and `python -c "import tomllib"` succeeds on Python 3.11+.

---

### Story 1.2: New path constants in `__init__.py`

**Tasks:**
- [ ] Task: In `cfgcaddy/__init__.py`, add three `Path` constants using `pathlib.Path`:
  - `LOCAL_DATA_PATH = Path.home() / ".config" / "cfgcaddy" / "local.toml"`
  - `PROFILES_DIR = Path.home() / ".config" / "cfgcaddy" / "profiles"`
  - `RENDERED_CACHE_DIR = Path.home() / ".local" / "share" / "cfgcaddy" / "rendered"`

  Note: use `~/.local/share/` (XDG_DATA_HOME) rather than `~/.cache/` to avoid the cache-clearing breakage risk identified in the pitfalls research.
  - Acceptance criteria: `from cfgcaddy import LOCAL_DATA_PATH, PROFILES_DIR, RENDERED_CACHE_DIR` succeeds; all three paths are `pathlib.Path` instances.

---

### Story 1.3: `data.py` — `LocalDataLoader`

**Tasks:**
- [ ] Task: Create `cfgcaddy/data.py` with a `LocalDataLoader` class. Constructor accepts `config_dir: Path = LOCAL_DATA_PATH.parent` and `profile: str | None = None`. Implement `load() -> dict` that: (a) reads `config_dir / "local.toml"` using `tomllib`/`tomli` and returns `{}` silently if the file is absent, (b) if `profile` is set, reads `config_dir / "profiles" / f"{profile}.toml"` and shallow-merges its top-level keys over the base dict (profile values win), (c) returns the merged dict.
  - Acceptance criteria: `LocalDataLoader().load()` returns `{}` when `~/.config/cfgcaddy/local.toml` does not exist; merging a profile file overrides a matching key from `local.toml`; loading a non-existent profile file with an active profile raises a clear `CfgcaddyError` (not a raw `FileNotFoundError`).

- [ ] Task: In `cfgcaddy/data.py`, add `validate_profile_name(name: str) -> None` that raises `CfgcaddyError` if the name does not match `^[a-zA-Z0-9_-]+$` or if the resolved path escapes `PROFILES_DIR`. Call this from `LocalDataLoader.__init__` when `profile` is not `None`.
  - Acceptance criteria: `validate_profile_name("../../../etc/passwd")` raises `CfgcaddyError`; `validate_profile_name("work")` passes; `validate_profile_name("work.v2")` raises (dots disallowed per pitfalls research).

- [ ] Task: Create `tests/test_data.py` using pytest `tmp_path`. Cover: absent `local.toml` returns `{}`; variables load correctly; profile merge overrides base; missing profile file raises `CfgcaddyError`; `validate_profile_name` rejects path-traversal names.
  - Acceptance criteria: All new tests pass; `pytest tests/test_data.py` exits 0.

---

### Story 1.4: `CfgcaddyContext` dataclass and `--profile` on `main` group

**Tasks:**
- [ ] Task: In `cfgcaddy/__main__.py`, add a `CfgcaddyContext` dataclass with fields: `config_path: str`, `profile: str | None`, `variables: dict` (default `{}`). Add `pass_cfg = click.make_pass_decorator(CfgcaddyContext, ensure=True)`.
  - Acceptance criteria: `CfgcaddyContext` is importable from `cfgcaddy.__main__`; `pass_cfg` decorator is defined.

- [ ] Task: In `cfgcaddy/__main__.py`, add `@click.option("--profile", envvar="CFGCADDY_PROFILE", default=None, help="Active profile name")` to the `main` group. Inside the `main` callback, use `@click.pass_context` to construct `CfgcaddyContext(config_path=DEFAULT_CONFIG_PATH, profile=profile)` and assign to `ctx.obj`. The existing `debug`/`quiet` logic is unchanged.
  - Acceptance criteria: `cfgcaddy --profile work link` does not error on the option; `cfgcaddy link` with no profile flag still works identically to the current release.

---

### Story 1.5: Wire `LocalDataLoader` into `LinkerConfig`

**Tasks:**
- [ ] Task: In `cfgcaddy/config.py`, update `LinkerConfig.__init__` signature to `(self, config_file_path=None, default_config=None, profile: str | None = None)`. After loading YAML, instantiate `LocalDataLoader(profile=profile)` and store `self.local_data = loader.load()` and `self.profile = profile`.
  - Acceptance criteria: Instantiating `LinkerConfig` with no `profile` argument produces `self.local_data == {}` when `local.toml` is absent; passing `profile="work"` loads and merges `profiles/work.toml`; the existing `test_linker.py` and `test_config.py` suites continue to pass unchanged.

- [ ] Task: In `cfgcaddy/__main__.py`, update the `link` command to pass `profile=ctx.obj.profile` (or the resolved profile from `CfgcaddyContext`) when constructing `LinkerConfig`.
  - Acceptance criteria: `cfgcaddy --profile work link` passes `profile="work"` to `LinkerConfig`; `cfgcaddy link` passes `profile=None`.

---

## Epic 2: Template Rendering

**Goal:** `.tmpl`-suffixed source files are rendered with Jinja2 using `local_data` variables before the symlink is created. Rendered output goes to `RENDERED_CACHE_DIR`. Non-`.tmpl` files are unaffected. The `secrets init` wizard creates/updates `local.toml` interactively.

---

### Story 2.1: `template.py` — `TemplateRenderer`

**Tasks:**
- [ ] Task: Create `cfgcaddy/template.py`. Define `TemplateRenderer` with constructor `(self, variables: dict, linker_src: Path, output_dir: Path = RENDERED_CACHE_DIR)`. Implement two public methods: (1) `render_if_template(src: Path) -> Path` — if `src.suffix != ".tmpl"` return `src` unchanged; otherwise render, write to cache (with idempotent write optimization), and return the cache path; (2) `render_to_string(src: Path) -> str | None` — if `src.suffix != ".tmpl"` return `None`; otherwise render and return the rendered string **without writing to the cache**. The diff command uses `render_to_string()` to generate the preview without side effects.
  - Acceptance criteria: Non-`.tmpl` paths pass through `render_if_template` unchanged; a `.tmpl` path triggers rendering and writes to cache; `render_to_string` on a `.tmpl` file returns the rendered content without touching the filesystem; `render_to_string` on a non-`.tmpl` file returns `None`.

- [ ] Task: In `cfgcaddy/template.py`, implement the rendering pipeline inside `render_if_template`: (a) compute cache path as `output_dir / src.relative_to(linker_src).with_suffix("")`; (b) create parent dirs for the cache path; (c) create a `jinja2.Environment(undefined=StrictUndefined, autoescape=False)`; (d) call `env.from_string(src.read_text())` and `template.render(**variables)` — this render call always executes, never cached; (e) encode the rendered string to bytes; (f) compare bytes against the existing cache file contents if it exists — **only skip the write if the bytes are identical**; (g) if writing, use an atomic rename pattern (`tempfile.NamedTemporaryFile` + `os.rename`) so no partial file is visible; (h) call `shutil.copymode(src, cache_path)` to preserve permission bits; (i) return `cache_path`. The "no write if content matches" optimization applies only to the filesystem write — the template is always re-rendered in memory so that stale cache files from changed templates are never silently served.
  - Acceptance criteria: The rendered file appears at the correct cache path; `src.stat().st_mode == cache_path.stat().st_mode`; atomic rename means no partial file is visible during write; changing a variable in `local.toml` and re-running `cfgcaddy link` updates the cached file.

- [ ] Task: In `cfgcaddy/template.py`, wrap `jinja2.UndefinedError` in a `CfgcaddyError` that includes the variable name and source file path. Wrap `jinja2.TemplateSyntaxError` with a message that includes filename, line number, and a hint about `{% raw %}` escaping.
  - Acceptance criteria: Rendering `{{ missing_var }}` with an empty variables dict raises `CfgcaddyError` containing both the variable name and the template file path; rendering `{{.invalid}}` raises `CfgcaddyError` mentioning `{% raw %}`.

- [ ] Task: Create `tests/test_template.py`. Cases: happy-path variable substitution; missing variable raises `CfgcaddyError` naming the variable; `TemplateSyntaxError` raises `CfgcaddyError` with file hint; non-`.tmpl` input returns input unchanged; rendered output has same permissions as source; rendered file has no `.tmpl` suffix in its name; `output_dir` is created if absent.
  - Acceptance criteria: All test cases pass; tests use `tmp_path` for both `linker_src` and `output_dir` — no writes to real `~/.local/share/cfgcaddy/`.

---

### Story 2.2: Integrate `TemplateRenderer` into `generate_links()`

**Tasks:**
- [ ] Task: In `cfgcaddy/config.py`, after `self.local_data = loader.load()`, instantiate `TemplateRenderer(variables=self.local_data, linker_src=self.linker_src)` and store as `self.renderer`. In the `for src_path in src_files` loop in `generate_links()`, replace the raw `src_path` with `effective_src = self.renderer.render_if_template(Path(src_path))` before constructing `Link(...)`.
  - Acceptance criteria: `cfgcaddy link` with a `.tmpl` source file creates a symlink pointing at the rendered cache path, not the `.tmpl` source. All existing `test_linker.py` tests continue passing (no `.tmpl` files in those fixtures, so the renderer is a no-op).

---

### Story 2.3: `commands/secrets.py` — `secrets init` wizard

**Tasks:**
- [ ] Task: Create `cfgcaddy/commands/__init__.py` (empty package marker).
  - Acceptance criteria: `from cfgcaddy.commands import diff` succeeds without import error.

- [ ] Task: Create `cfgcaddy/commands/secrets.py`. Implement a `@click.group() def secrets(...)` with a sub-command `@secrets.command() def init(config, ...)`. The `init` command: (a) scans all `*.tmpl` files under `linker_src`; (b) collects all `{{ variable_name }}` references using `jinja2.Environment().parse()`; (c) loads current `local.toml` if it exists; (d) uses `questionary` to prompt for any variable not already present in `local.toml`; (e) writes the updated values to `local.toml` using `tomli_w.dumps()`; (f) prints a summary of variables written.
  - Acceptance criteria: Running `cfgcaddy secrets init` with a `.tmpl` file containing `{{ github_token }}` prompts exactly once for `github_token`; an existing `local.toml` with `github_token` already set skips that prompt; the written file is valid TOML parseable by `tomllib`.

- [ ] Task: In `cfgcaddy/__main__.py`, import `secrets` from `cfgcaddy.commands.secrets` and call `main.add_command(secrets)`.
  - Acceptance criteria: `cfgcaddy secrets --help` shows the `init` sub-command.

- [ ] Task: Create `tests/test_secrets.py` using `tmp_path` and `CliRunner`. Cover: `secrets init` prompts for each variable in a `.tmpl` file; existing `local.toml` values are not re-prompted; written file is valid TOML; running `secrets init` twice with the same template is idempotent.
  - Acceptance criteria: All tests pass without writing to real `~/.config/cfgcaddy/`.

- [ ] Task: Add `{% raw %}` / `{% endraw %}` documentation as a note printed by `cfgcaddy secrets init` when variables are found, reminding users how to escape literal `{{ }}` sequences.
  - Acceptance criteria: The completion message from `secrets init` includes a line mentioning `{% raw %}`.

---

## Epic 3: Alternate File Scoring

**Goal:** Source files with `##key.value` suffixes are scored against the current machine context; the highest-scoring candidate wins. Ignore patterns match against the base name (before `##`). All existing behavior for files without `##` is preserved.

---

### Story 3.1: `alternate.py` — parsing and scoring

**Tasks:**
- [ ] Task: Create `cfgcaddy/alternate.py`. Define `AlternateContext` as a dataclass with fields `os: str`, `hostname: str`, `profile: str | None`. Add a module-level `CONDITION_WEIGHTS: dict[str, int]` mapping `{"os": 2, "hostname": 32, "profile": 16, "default": 0}`.
  - Acceptance criteria: `AlternateContext` is importable; `CONDITION_WEIGHTS` contains all four keys.

- [ ] Task: In `cfgcaddy/alternate.py`, implement `parse_alternate_name(filename: str) -> tuple[str, list[tuple[str, str]]]` that splits on `##`, returns `(base_name, [(key, value), ...])`. Strip a trailing `.tmpl` from `filename` before splitting (`.tmpl` is processed after scoring, not as a condition).
  - Acceptance criteria: `parse_alternate_name("gitconfig##os.darwin##hostname.work")` returns `("gitconfig", [("os", "darwin"), ("hostname", "work")])`; `parse_alternate_name("gitconfig.tmpl##os.linux")` returns `("gitconfig", [("os", "linux")])`; `parse_alternate_name("gitconfig")` returns `("gitconfig", [])`.

- [ ] Task: In `cfgcaddy/alternate.py`, implement `score_candidate(filename: str, context: AlternateContext) -> int | None`. Returns `None` if any condition doesn't match. Returns `sum(weight + 1000 for matching conditions)` to guarantee more-conditions-always-beats-fewer. Returns `0` for a bare filename (no `##` suffix) or `##default`. Emits a `logging.warning` for any unrecognized condition key.
  - Acceptance criteria: `score_candidate("gitconfig##os.darwin", ctx_darwin)` returns `1002`; `score_candidate("gitconfig##os.linux", ctx_darwin)` returns `None`; `score_candidate("gitconfig##os.darwin##hostname.work", ctx_darwin_work)` returns `2034`; `score_candidate("gitconfig", ctx)` returns `0`; `score_candidate("gitconfig##default", ctx)` returns `0`.

- [ ] Task: In `cfgcaddy/alternate.py`, implement `select_candidate(candidates: list[Path], context: AlternateContext) -> Path | None`. Filters out non-matching candidates, selects the highest scorer. If two candidates tie, picks the lexicographically last path as a deterministic tiebreak (and emits a `logging.warning`). Returns `None` if no candidates match.
  - Acceptance criteria: Given `[gitconfig##os.darwin##hostname.work, gitconfig##os.darwin, gitconfig##default]` on a darwin/work machine, returns the `##os.darwin##hostname.work` path; a tie between two different `##os.darwin` variants returns the lexicographically last one with a warning logged.

- [ ] Task: Create `tests/test_alternate.py` with parametrized test cases covering: highest-score wins; non-matching candidate excluded; tie triggers deterministic tiebreak; no match returns `None`; bare filename scores 0; `##default` scores 0; `.tmpl` suffix stripped before parsing; unrecognized key triggers warning and excludes candidate.
  - Acceptance criteria: All cases pass; scoring tests require no filesystem I/O (pure function tests).

---

### Story 3.2: Integrate `AlternateSelector` into `LinkerConfig` and `find_absences`

**Tasks:**
- [ ] Task: In `cfgcaddy/config.py`, build `self.alternate_context = AlternateContext(os=platform.system().lower(), hostname=socket.gethostname(), profile=self.profile)` in `LinkerConfig.__init__`. In `generate_links()`, after globbing `src_files`, group candidates by their base name (via `parse_alternate_name`), call `select_candidate(group, self.alternate_context)` per group, and skip groups where the result is `None`. When skipping, emit a user-visible warning via `click.echo(f"Warning: no candidate matches for '{base_name}' on this machine — skipping", err=True)` (NOT just `logging.warning`, which is invisible to end users running `cfgcaddy link`).
  - Acceptance criteria: `cfgcaddy link` on a repo containing `gitconfig##os.darwin` and `gitconfig##os.linux` links only the correct variant on each OS; a repo with no `##` files is unaffected; a repo with candidates for only the wrong OS prints a warning to stderr and creates no symlink for that base name.

- [ ] Task: In `cfgcaddy/link.py`, inside `find_absences()`, replace the raw `ignored.match_file(path.join(rel_path, f))` check for files with a two-step: first extract `base_f = f.split("##")[0]`, then check `ignored.match_file(path.join(rel_path, base_f))`. The function must track two distinct names per file: (1) the full `##`-suffixed filename `f` (used for `open()`/`Path(src_dir, f)` to read the actual source file on disk), and (2) the base name `base_f` (used as the destination symlink path in `Link.dest`). These MUST NOT be conflated — constructing the dest path from `f` would create a `##`-suffixed symlink in `$HOME`, and using `base_f` for the src open would fail to find the file.
  - Acceptance criteria: An `ignore` pattern of `secrets.sh` ignores `secrets.sh##os.darwin`; a file `gitconfig##os.darwin` on disk creates a symlink at `~/.gitconfig` (not `~/.gitconfig##os.darwin`); `Link.src` still points at the `##`-suffixed file on disk so the symlink resolves correctly.

- [ ] Task: Add tests to `tests/test_linker.py` (Style A, `FileLinkTestCase`) covering: ignore pattern on exact base name ignores all `##` variants; the destination symlink uses the base name not the `##`-suffixed name; no match for current OS produces a warning and no symlink; alternate file selection works through the full `Linker.create_links()` path.
  - Acceptance criteria: New tests pass; all existing `test_linker.py` tests continue to pass.

---

## Epic 4: Profiles

**Goal:** Named profiles load a per-profile TOML file that merges over `local.toml`. Profiles affect both template variables and `##profile.name` alternate file scoring. New CLI commands let users list and create profiles.

---

### Story 4.1: `##profile.name` scoring key

**Tasks:**
- [ ] Task: In `cfgcaddy/alternate.py`, confirm that `CONDITION_WEIGHTS` includes `"profile": 16` (already added in Story 3.1). Verify that `score_candidate` evaluates `profile` conditions against `context.profile` correctly — a `##profile.work` suffix scores `1016` when `context.profile == "work"` and returns `None` when `context.profile != "work"` or `context.profile is None`.
  - Acceptance criteria: `score_candidate("gitconfig##profile.work", AlternateContext(os="darwin", hostname="mac", profile="work"))` returns `1016`; same call with `profile=None` returns `None`.

- [ ] Task: Add parametrized tests in `tests/test_alternate.py` for `##profile.name` scoring including `profile=None` disqualification.
  - Acceptance criteria: New test cases pass; no regressions.

---

### Story 4.2: `commands/profiles.py` — `profiles list` and `profiles init`

**Tasks:**
- [ ] Task: Create `cfgcaddy/commands/profiles.py`. Implement `@click.group() def profiles(...)`. Add `@profiles.command() def list_profiles(...)` that enumerates `*.toml` files under `PROFILES_DIR`, prints each name (without `.toml` extension) one per line using `click.echo`. If the directory does not exist, prints a message and exits 0.
  - Acceptance criteria: `cfgcaddy profiles list` with an empty profiles directory prints a "no profiles found" message and exits 0; with `work.toml` and `home.toml` present, prints `home` and `work`.

- [ ] Task: In `cfgcaddy/commands/profiles.py`, add `@profiles.command() def init(name: str)` that takes `name` as a CLI argument, calls `validate_profile_name(name)`, creates `PROFILES_DIR` if absent, and uses `questionary` to prompt for key-value pairs, writing the result to `PROFILES_DIR / f"{name}.toml"` via `tomli_w`.
  - Acceptance criteria: `cfgcaddy profiles init work` creates `~/.config/cfgcaddy/profiles/work.toml`; a path-traversal name is rejected before any file I/O.

- [ ] Task: In `cfgcaddy/__main__.py`, import `profiles` from `cfgcaddy.commands.profiles` and call `main.add_command(profiles)`.
  - Acceptance criteria: `cfgcaddy profiles --help` shows `list` and `init` sub-commands.

- [ ] Task: Add `tests/test_profiles.py` using `tmp_path` and `unittest.mock.patch` to override `PROFILES_DIR`. Cover: `list_profiles` with no profiles dir; `list_profiles` with two profile files; `profiles init` with invalid name rejected; profile data loads correctly via `LocalDataLoader` with the new profile.
  - Acceptance criteria: All tests pass without touching real `~/.config/cfgcaddy/profiles/`.

---

### Story 4.3: `default_profile` in `.cfgcaddy.yml`

**Tasks:**
- [ ] Task: In `cfgcaddy/config.py`, extend `LinkerConfig.__init__` to read `self.config.get("preferences", {}).get("default_profile")` as a fallback when `profile` argument is `None`. Resolution order: constructor argument → YAML `default_profile` → `None`.
  - Acceptance criteria: A `.cfgcaddy.yml` with `preferences.default_profile: work` activates the `work` profile when no `--profile` flag is passed; an explicit `--profile home` overrides the YAML default.

- [ ] Task: Add tests to `tests/test_config.py` covering Story 4.3. Cases: `default_profile` in YAML activates profile when no CLI flag; CLI `--profile` overrides YAML default; `CFGCADDY_PROFILE` env var activates profile when no CLI flag (verify via `CliRunner(env={"CFGCADDY_PROFILE": "work"})` so the env-var resolution path from the `main` group is exercised end-to-end).
  - Acceptance criteria: All three resolution-order cases pass.

---

## Epic 5: diff Command

**Goal:** `cfgcaddy diff` shows what `cfgcaddy link` would change without making any changes. Uses rich-colored unified diff output. `cfgcaddy link --dry-run` is an alias.

---

### Story 5.1: Dry-run link resolution

**Tasks:**
- [ ] Task: In `cfgcaddy/linker.py`, add a `dry_run: bool = False` parameter to `Linker.__init__`. When `dry_run=True`, `create_links()` and `create_custom_links()` return a list of proposed `Link` objects rather than executing any filesystem operations. Implement a `resolve_planned_links(self) -> list[tuple[str, Link]]` method that returns `(action_label, link)` pairs where `action_label` is one of `"new"`, `"changed"`, `"broken"`, `"content_changed"` (template file whose rendered output differs from current deployed content), or `"conflict"` (dest exists as a regular file, not a symlink — cfgcaddy will not overwrite it without `--force`). The `os.readlink()` call MUST be guarded with `link.dest.is_symlink()` before attempting to read the target; calling `os.readlink()` on a regular file raises `OSError`.
  - Acceptance criteria: `Linker(cfg, dry_run=True).resolve_planned_links()` returns the correct action labels for each link state without modifying any files; a `link.dest` that is a plain file (not a symlink) produces a `"conflict"` entry, not an exception.

---

### Story 5.2: `commands/diff.py` — diff command with rich output

**Tasks:**
- [ ] Task: Create `cfgcaddy/commands/diff.py`. Implement `@click.command() def diff(config, profile)` that: (a) constructs `LinkerConfig(config_file_path=config, profile=profile)`; (b) constructs `Linker(cfg, dry_run=True)`; (c) calls `resolve_planned_links()`; (d) prints results using `rich.console.Console`.
  - Acceptance criteria: `cfgcaddy diff` with no pending changes exits 0 and prints "No changes"; with pending changes exits 1 and prints at least one entry.

- [ ] Task: In `cfgcaddy/commands/diff.py`, implement `show_link_diff(console: Console, action: str, link: Link, renderer: TemplateRenderer)` that: for non-template links prints the action and paths with color (`green` for new, `yellow` for changed, `red` for broken); for template links generates `difflib.unified_diff` between the current symlink target content and the freshly rendered content (without writing to cache), then renders via `rich.syntax.Syntax` with `lexer="diff"` and `theme="ansi_dark"`.
  - Acceptance criteria: Template files show a colored unified diff; non-template links show a one-line summary; output is suppressed if the content is identical (no diff output for already-correct links).

- [ ] Task: In `cfgcaddy/__main__.py`, import `diff` from `cfgcaddy.commands.diff` and call `main.add_command(diff)`. Add `@click.option("--dry-run", is_flag=True)` to the existing `link` command; when `True`, invoke `diff` via `ctx.invoke(diff, config=config)` and return early.
  - Acceptance criteria: `cfgcaddy link --dry-run` and `cfgcaddy diff` produce identical output; `cfgcaddy link` without `--dry-run` still performs symlink operations as before.

- [ ] Task: Create `tests/test_diff.py` using `tmp_path` and `click.testing.CliRunner`. Cover: exit code 0 with no changes; exit code 1 with a new link pending; template content diff shown for a `.tmpl` file whose rendered output differs from current deployed content; `--dry-run` alias produces same exit code as `diff`.
  - Acceptance criteria: All tests pass; no real symlinks created during test execution.

---

## Epic 6: doctor Command

**Goal:** `cfgcaddy doctor` audits current state against 7 checks and reports PASS/WARN/FAIL per check. Exit codes: 0=all pass, 1=warnings only, 2=any failure. `--fix` auto-repairs broken symlinks.

---

### Story 6.1: Check protocol and runner in `commands/doctor.py`

**Tasks:**
- [ ] Task: Create `cfgcaddy/commands/doctor.py`. Define `CheckLevel(IntEnum)` with values `PASS=0`, `WARN=1`, `FAIL=2`. Define `CheckResult` as a dataclass with `level: CheckLevel`, `name: str`, `message: str`. Define `Check` as a `typing.Protocol` with `def name(self) -> str` and `def run(self) -> CheckResult`.
  - Acceptance criteria: `CheckLevel`, `CheckResult`, and `Check` are importable from `cfgcaddy.commands.doctor`.

- [ ] Task: In `cfgcaddy/commands/doctor.py`, implement `run_all_checks(checks: list[Check], console: Console, fix: bool = False) -> int` that iterates checks, prints each result with a `rich`-formatted icon (`[green]✓[/]` for PASS, `[yellow]![/]` for WARN, `[red]✗[/]` for FAIL) and message, and returns the worst `CheckLevel` value as the integer exit code.
  - Acceptance criteria: A list containing one PASS and one WARN returns exit code 1; a list containing a FAIL returns exit code 2; a list of all PASS returns exit code 0.

---

### Story 6.2: Implement the 7 checks

**Tasks:**
- [ ] Task: In `cfgcaddy/commands/doctor.py`, implement `BrokenSymlinksCheck(linker_config: LinkerConfig)`. `run()` walks `linker_dest` looking for symlinks whose targets do not exist. Returns PASS if none found, FAIL if any found (listing the first three broken paths in the message). When `fix=True` passed to `run(fix=True)`, unlinks each broken symlink and returns WARN instead of FAIL.
  - Acceptance criteria: A broken symlink in `linker_dest` produces a FAIL result; `run(fix=True)` removes the broken symlink and returns WARN.

- [ ] Task: In `cfgcaddy/commands/doctor.py`, implement `SymlinkDriftCheck(linker_config: LinkerConfig)`. `run()` resolves each `Link` in `linker_config.links` and checks whether the current symlink target at `link.dest` matches `link.src`. Returns PASS if all match or dest doesn't exist yet, WARN if any dest is a symlink pointing to the wrong src.
  - Acceptance criteria: A symlink pointing to an outdated source path produces a WARN result.

- [ ] Task: In `cfgcaddy/commands/doctor.py`, implement `MissingVariablesCheck(linker_config: LinkerConfig)`. `run()` scans all `*.tmpl` files under `linker_src`, extracts referenced variable names using `jinja2.Environment().parse()`, and checks each against `linker_config.local_data`. Returns PASS if all variables are present, FAIL if any are missing (listing variable names and their template files).
  - Acceptance criteria: A `.tmpl` file referencing `{{ missing_var }}` with an empty `local_data` produces FAIL naming `missing_var` and the file path.

- [ ] Task: In `cfgcaddy/commands/doctor.py`, implement `MissingLocalTomlCheck(linker_config: LinkerConfig)`. `run()` checks if `LOCAL_DATA_PATH` exists. Returns PASS if no `.tmpl` files are present (templating not in use), WARN if `.tmpl` files exist but `local.toml` is absent (prompts user to run `cfgcaddy secrets init`).
  - Acceptance criteria: No `.tmpl` files + no `local.toml` = PASS; `.tmpl` files exist + no `local.toml` = WARN with a message pointing to `cfgcaddy secrets init`.

- [ ] Task: In `cfgcaddy/commands/doctor.py`, implement `AmbiguousAlternatesCheck(linker_config: LinkerConfig)`. `run()` groups all source files by base name and calls `score_candidate` for each group. Returns PASS if no ties, WARN if any base name has two or more candidates with equal non-None scores (listing the tied filenames).
  - Acceptance criteria: Two files `gitconfig##os.darwin` and `gitconfig##os.darwin` (identical scores) produce a WARN result naming both files.

- [ ] Task: In `cfgcaddy/commands/doctor.py`, implement `OpCliCheck(linker_config: LinkerConfig)`. `run()` checks if any value in `linker_config.local_data` (recursively, for nested tables) contains the string `op://`. If any `op://` references exist, checks whether `op` is on `$PATH` via `shutil.which("op")`. Returns PASS if no `op://` references or `op` is installed, WARN if `op://` references exist but `op` is not installed.
  - Acceptance criteria: `local.toml` containing `op://...` with `op` not on PATH returns WARN; no `op://` references returns PASS regardless of PATH.

- [ ] Task: In `cfgcaddy/commands/doctor.py`, implement `NoUnmatchedAlternatesCheck(linker_config: LinkerConfig)`. `run()` walks `linker_src` and for each base name that has only `##`-suffixed candidates (no bare filename and no `##default`), checks whether `select_candidate` returns `None` for the current `alternate_context`. Returns PASS if all base names have at least one matching candidate, WARN if any base name has candidates but none match the current machine.
  - Acceptance criteria: A directory containing only `gitconfig##os.linux` on a macOS machine produces WARN stating no candidate matches for `gitconfig`.

---

### Story 6.3: Wire the `doctor` command

**Tasks:**
- [ ] Task: In `cfgcaddy/commands/doctor.py`, implement `@click.command() def doctor(config, profile, fix)` with `@click.option("--fix", is_flag=True)`. Construct `LinkerConfig`, instantiate all 7 check classes, run `run_all_checks(checks, console, fix=fix)`, and call `sys.exit(result)`.
  - Acceptance criteria: `cfgcaddy doctor` exits 0 on a clean repo; exits 1 with only warnings; exits 2 with any failure. `cfgcaddy doctor --fix` repairs broken symlinks in place.

- [ ] Task: In `cfgcaddy/__main__.py`, import `doctor` from `cfgcaddy.commands.doctor` and call `main.add_command(doctor)`.
  - Acceptance criteria: `cfgcaddy doctor --help` shows the `--fix` flag.

- [ ] Task: Create `tests/test_doctor.py` using `tmp_path` and `CliRunner`. For each of the 7 checks, write one test covering PASS and one covering FAIL/WARN. Use `unittest.mock.patch` to override `LOCAL_DATA_PATH` and `PROFILES_DIR`. Cover: `--fix` repairs a broken symlink and exits 1 (WARN) not 2 (FAIL); `MissingVariablesCheck` names the correct variable.
  - Acceptance criteria: All 14+ test cases pass; no filesystem writes to real user home during test execution.

---

## Acceptance Criteria Summary (Cross-Epic)

- `cfgcaddy link` on a dotfiles repo with no `.tmpl` files and no `##` suffixes produces identical output to the current release.
- All 5 new commands (`diff`, `doctor`, `secrets init`, `profiles list`, `profiles init`) appear in `cfgcaddy --help`.
- `pytest` passes the full test suite with no failures and no new real filesystem writes under `~/`.
- `ruff check cfgcaddy/` passes with zero violations.
- `mypy cfgcaddy/` passes (existing `ignore_missing_imports = true` applies).
