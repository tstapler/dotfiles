# cfgcaddy Feature Expansion: Failure Modes, Edge Cases, and Risks

**Research date:** 2026-06-02  
**Scope:** Feature 1 (templating), Feature 2 (## scoring), Feature 3 (profiles), Feature 4 (diff), Feature 5 (doctor)

---

## Risk 1: Jinja2 Template Rendering Pitfalls

### The Problem

Jinja2 uses `{{ }}` as its default variable delimiter. Shell scripts only conflict with Jinja2 when they contain `{{ }}` — not `${}`, `${var}`, `{single}`, or even `${arr[@]}`. Single curly braces are completely safe. The real conflicts are:

**Hard failure (TemplateSyntaxError):** Files containing `{{ }}` with non-identifier content inside:
- `grep '{{[^}]*}}' file` — the `[^}]` is invalid Jinja2 syntax
- `{{.Values.cluster}}` — Go/Helm template syntax: dot notation is a Jinja2 syntax error
- Any `{{ }}` containing characters that aren't valid Python identifiers

These raise `TemplateSyntaxError` at parse time (before rendering), with confusing Jinja2 error messages like `unexpected char '^' at position 12` instead of `this file contains Go template syntax`.

**Silent corruption (only without StrictUndefined):** Files containing `{{ identifier }}` where the identifier is not a variable name:
```bash
# Config for {{hostname}} machine   <- treated as Jinja2 var, becomes empty string
```
With the default Jinja2 `Environment()`, undefined vars silently become empty strings. **Always use `StrictUndefined`.**

**Confirmed safe patterns:**
- `${variable}` bash expansion — single braces, ignored by Jinja2
- `${arr[@]}` bash arrays — safe
- `awk '{print $1}' file` — single braces, safe
- `awk '{count++} END {print count}' file` — confirmed safe (tested)
- `awk '/[0-9]{2,4}/{print}' file` — awk regex intervals with single `{n,m}` syntax, safe
- JSON `{"key": "value"}` — single braces, safe

### Failure Modes by Severity

| Scenario | Behavior | Severity |
|---|---|---|
| `{{ undeclared_var }}` with StrictUndefined | `UndefinedError` with variable name | Acceptable — clear error |
| `{{ undeclared_var }}` without StrictUndefined | Silent empty string substitution | **Critical** — data corruption |
| `{{.Values.cluster}}` Go template syntax | `TemplateSyntaxError: unexpected '.'` | High — confusing error message |
| `grep '{{[^}]...}}'` pattern | `TemplateSyntaxError: unexpected '^'` | High — confusing error message |
| Shell `${var}`, `{single}`, awk `'{...}'` | Passes through unchanged | OK |

### Mitigation

1. **Always use `StrictUndefined`:**
   ```python
   from jinja2 import Environment, StrictUndefined
   env = Environment(undefined=StrictUndefined)
   ```

2. **Wrap `TemplateSyntaxError` with filename context:**
   ```python
   except TemplateSyntaxError as e:
       raise CfgcaddyError(
           f"Template syntax error in {tmpl_path} at line {e.lineno}: {e.message}\n"
           f"Hint: if this file contains Go/Helm template syntax or regex with {{{{...}}}},\n"
           f"escape it with {{% raw %}}...{{% endraw %}} or {{ '{{' }}"
       )
   ```

3. **Document the escape mechanisms for users:**
   - `{% raw %}...{% endraw %}` for blocks containing `{{ }}` (e.g., heredocs generating k8s manifests)
   - `{{ '{{' }}` for individual literal `{{`
   - Custom delimiters possible if needed (allows `[[ var ]]` syntax like chezmoi's option)

4. **Missing variable error must name the variable AND the file:**
   ```
   ERROR: Template variable 'github_token' is undefined
     File: ~/dotfiles/.shell/secrets.sh.tmpl
     Hint: add 'github_token = "value"' to ~/.config/cfgcaddy/local.toml
   ```

### How chezmoi handles this
chezmoi uses Go `text/template` (same `{{ }}` delimiters) and requires `{{ "{{" }}` to escape literal braces. They document that files containing `{{ }}` not intended as templates should use `{% raw %}` blocks. cfgcaddy should take the same approach.

---

## Risk 2: Symlink + Rendered File Coherence

### Cache Location Risk

The requirements specify `~/.cache/cfgcaddy/rendered/` as the cache location. **`~/.cache/` is semantically volatile** — some tools, CI systems, and users treat it as clearable. If the cache is deleted:
- Symlinks from `~/.shell/env.sh` → `~/.cache/cfgcaddy/rendered/.shell/env.sh` become broken
- Shell startup files that `source ~/.shell/env.sh` fail with "No such file or directory"
- This is a visible failure, not silent — but disruptive

**Recommendation:** Consider `~/.local/share/cfgcaddy/rendered/` (XDG_DATA_HOME) instead — the XDG spec defines this as persistent user data, not clearable cache. Alternatively, keep `~/.cache/` but make `cfgcaddy link` always re-render and repair broken symlinks automatically.

### Stale Cache

If `cfgcaddy link` only renders when the cached file doesn't exist, the following changes produce stale content:
- `local.toml` values change (e.g., new email address)
- Source `.tmpl` file changes
- Profile changes

**Mitigation — always re-render:** Re-render ALL templates on every `cfgcaddy link` run. With Jinja2, even 50 template files renders in well under 1 second. This eliminates stale cache entirely at trivial performance cost.

If mtime-based invalidation is preferred, use a **hash of both template content and local.toml content** stored as a sidecar file — not mtime alone (git pull doesn't reliably update mtimes).

### Atomic Write Requirement

Without atomic writes, a shell that starts while cfgcaddy is mid-render reads a partial file:

```python
# WRONG: direct write risks partial reads
with open(rendered_path, 'w') as f:
    f.write(rendered_content)

# CORRECT: atomic rename (os.rename is atomic on POSIX)
with tempfile.NamedTemporaryFile(mode='w', dir=cache_dir, delete=False, suffix='.cfgcaddy') as tmp:
    tmp.write(rendered_content)
    tmp_path = tmp.name
os.rename(tmp_path, rendered_path)
```

### Permission Copying

Source `.tmpl` files may be executable (shell scripts intended to be executed, not just sourced). The rendered output must preserve the source's permissions, not be hardcoded to `0600`.

```python
import shutil
shutil.copymode(template_path, rendered_path)  # copies permission bits
```

Note: rendered files containing secrets should additionally have `0600` permissions set explicitly for security. But executable scripts need `0755` — these goals conflict. Recommendation: copy source permissions, document that sensitive `.tmpl` files should be chmod'd appropriately in the source repo.

### Fixed Output Path is Simpler

Use a fixed rendered path mirroring the source structure, not a content-addressed hash filename:
- Source: `~/dotfiles/.shell/env.sh.tmpl`
- Rendered: `~/.cache/cfgcaddy/rendered/.shell/env.sh`
- Symlink: `~/.shell/env.sh` → `~/.cache/cfgcaddy/rendered/.shell/env.sh`

The symlink never needs updating after initial creation (atomic overwrite of the rendered file handles re-renders). Content-addressed filenames require symlink updates on every hash change and add complexity with no benefit for this use case.

---

## Risk 3: Alternate File Scoring Edge Cases

### Edge Case A: All Candidates Non-Matching (No Default)

If all candidates for a target have `##` suffixes and none match the current machine with no `##default` or bare filename:
- **Current spec behavior:** nothing gets linked — silently
- **Risk:** user deploys to a new machine type, their dotfile silently disappears with no warning

**Mitigation:** `cfgcaddy link` should emit a WARNING (not error) when candidates exist for a target but none match. `cfgcaddy doctor` should flag this as WARN.

### Edge Case B: `gitconfig` and `gitconfig##default` Coexist — Score Tie

The spec says "files with no ## suffix are treated as ##default (score 0)." If both `gitconfig` (score 0, implicit default) and `gitconfig##default` (score 0, explicit default) exist, they tie. The spec says `doctor` reports ties, but `link` has undefined behavior.

**Mitigation:** Define a deterministic tiebreak rule in the spec: explicit `##default` beats a bare filename (or vice versa — either is fine, but it must be documented and consistent). Log a warning even when the tiebreak resolves it.

### Edge Case C: Equal-Score Non-Default Ties

`gitconfig##os.darwin` and `gitconfig##hostname.work-laptop` both score 1 on a macOS work laptop. Undefined which wins.

**Mitigation:** `cfgcaddy doctor` reports this as WARN (already in spec). For `cfgcaddy link`, define a tiebreak rule (e.g., lexicographic order of filename) so behavior is deterministic and testable.

### Edge Case D: ## in the Middle of a Filename

A filename like `my##weird##file.txt` splits to `["my", "weird", "file.txt"]` — the last element `file.txt` is not a valid scoring key. This happens if:
- A user has a legitimate `##` in a filename (rare but possible)
- A tag like `##hostname.machine-name` where the value has dots

**Mitigation:** Validate all parsed tags against the known tag key set (`os`, `hostname`, `default`, `profile`). Emit a WARNING for unrecognized tags and treat the file as non-candidate (don't silently skip or silently link). Document that `##` in filename values is not supported.

### Edge Case E: `.tmpl` + `##` Combination

A file could have both: `gitconfig##os.darwin.tmpl`. The parsing order matters:
1. Strip `.tmpl` suffix first → `gitconfig##os.darwin`
2. Then parse `##` scoring → base `gitconfig`, tag `os.darwin`

Or:
1. Parse `##` first → `gitconfig`, tag `os.darwin.tmpl` (wrong — includes extension)

**Mitigation:** Define and test the canonical parsing order: strip `.tmpl` last (after scoring). This means the file participates in scoring AS IF it were `gitconfig##os.darwin`, and if selected, gets rendered as `gitconfig`.

---

## Risk 4: Profile Security

### Path Traversal via Profile Name

Profile names passed via `--profile <name>` or `CFGCADDY_PROFILE` are used to construct a file path:

```python
profile_path = Path("~/.config/cfgcaddy/profiles") / f"{profile_name}.toml"
```

With `name = "../../../etc/passwd"`:
```
~/.config/cfgcaddy/profiles/../../../etc/passwd.toml
= ~/etc/passwd.toml  (reads from user's home)
```

With `name = "../../.ssh/id_rsa"`:
```
= ~/.ssh/id_rsa.toml  (would fail to parse as TOML but file is read)
```

The actual risk is **information disclosure** (reading arbitrary TOML-parseable files as profile variables) and potentially confusing error messages from attempting to parse non-TOML files.

This is not a remote attack vector (local attacker with shell access can already read these files). But the `CFGCADDY_PROFILE` environment variable path is worth defending — a malicious `.env` or shell script could set it.

### Mitigation

Validate profile names with a strict allowlist regex before constructing the path:

```python
import re

PROFILE_NAME_RE = re.compile(r'^[a-zA-Z0-9_-]+$')

def validate_profile_name(name: str) -> None:
    if not PROFILE_NAME_RE.match(name):
        raise CfgcaddyError(
            f"Invalid profile name '{name}': only letters, digits, hyphens, "
            f"and underscores are allowed"
        )
    # Belt-and-suspenders: verify resolved path stays in profiles dir
    profiles_dir = Path("~/.config/cfgcaddy/profiles").expanduser().resolve()
    target = (profiles_dir / f"{name}.toml").resolve()
    if not str(target).startswith(str(profiles_dir) + "/"):
        raise CfgcaddyError(f"Profile name '{name}' resolves outside profiles directory")
```

Note: dots are intentionally excluded (no `work.v2` style names). This also prevents `.hidden` profile files from being targeted. The same validation must apply to `CFGCADDY_PROFILE` env var values.

---

## Risk 5: Migration / Coexistence with Ignore Patterns

### How ## Interacts with pathspec Matching

The existing `find_absences()` function uses `pathspec.PathSpec.from_lines("gitwildmatch", ...)` to filter files. Test results show:

| Pattern | Filename | Matches? |
|---|---|---|
| `gitconfig` | `gitconfig##os.darwin` | **No** — `##` changes the name |
| `*.yml` | `config.yml##os.darwin` | **No** — extension is not `.yml` |
| `secrets*` | `secrets.sh##os.linux` | **Yes** — wildcard matches the full name |
| `secrets.sh` | `secrets.sh##os.darwin` | **No** — exact name doesn't match |

The spec says: "`.cfgcaddy.yml` ignore patterns apply to the base name (before `##`)."

This means the implementation **must** strip `##` suffixes before checking ignore patterns. Without this:
- `ignore: ["secrets.sh"]` will NOT ignore `secrets.sh##os.linux` (security risk: secret files may be linked)
- `ignore: ["*.yml"]` will NOT ignore `config.yml##os.darwin`
- Users must update every ignore pattern to `secrets.sh*` or `secrets*` to get previous behavior

### Explicit Implementation Requirement

In `find_absences()`, before the pathspec check, extract the base name:

```python
# When checking files against ignored patterns, use base name (before ##)
base_name = f.split("##")[0] if "##" in f else f
base_rel = path.join(rel_path, base_name)
if ignored.match_file(base_rel):
    continue  # skip the ## variant
```

Without this, any user with exact filename ignore patterns (common for secrets files like `*.op.sh`, `secrets.sh`) would have their secret files silently linked after upgrading. This is a **regression in security behavior**.

---

## Risk 6: op:// References

### cfgcaddy's Role

The requirements are internally consistent but the design intent needs explicit documentation: **cfgcaddy does NOT resolve `op://` URIs**. It treats them as ordinary strings. The flow is:

```
local.toml:   github_token_path = "op://FBG/GitHub PAT/credential"
template:     export GITHUB_TOKEN_PATH={{ github_token_path }}
rendered:     export GITHUB_TOKEN_PATH=op://FBG/GitHub PAT/credential
shell script: export TOKEN=$(op read "$GITHUB_TOKEN_PATH")
```

cfgcaddy renders the string `op://FBG/GitHub PAT/credential` into the file. The shell (or user) then calls `op read` to resolve it. cfgcaddy is not in the `op` call chain at all.

### Failure Mode: op Not Installed or Not Signed In

With the above design, if `op` CLI is not installed or not signed in:
- `cfgcaddy link` succeeds (just string substitution — no op call)
- `cfgcaddy diff` succeeds (diffs rendered strings)
- Shell startup FAILS when trying to `op read` the URI
- The failure happens at shell use time, not at link time

`cfgcaddy doctor`'s "op CLI not installed" check is an advisory warning, not a blocker. This is the **right** behavior — it's the shell's problem to resolve the URI, not cfgcaddy's.

### Failure Mode: op Value Used Directly (Not as URI)

If a user puts the actual secret value in `local.toml` instead of an `op://` URI:
```toml
github_token = "ghp_abc123realtoken..."
```

This is valid — cfgcaddy renders it as-is. The rendered file in `~/.cache/cfgcaddy/rendered/` contains the actual secret. This is acceptable (local machine only, not committed), but the cache directory should have `0700` permissions and ideally individual rendered files should be `0600`.

### Missing Dependency

The requirements list `tomllib` (stdlib 3.11+, `tomli` backport for 3.10) but `tomllib`/`tomli` are **read-only**. The `secrets init` wizard creates/updates `local.toml`, which requires writing TOML. Add `tomli-w` to `pyproject.toml` dependencies, or write TOML manually for the simple flat-key case (nested tables require a proper writer).

---

## Risk 7: Test Isolation

### Current Test Pattern

The existing tests use `tempfile.mkdtemp()` for source and dest directories, which is solid. The new features introduce paths that are currently hardcoded to `~/.cache/` and `~/.config/`, which will pollute the real user home directory during tests if not addressed.

### Specific Isolation Risks

1. **Template rendering** writes to `~/.cache/cfgcaddy/rendered/` — tests will create real files there
2. **`local.toml` loading** reads from `~/.config/cfgcaddy/local.toml` — tests pick up the real user's config
3. **Profile loading** reads from `~/.config/cfgcaddy/profiles/` — same issue
4. **`secrets init`** writes to `~/.config/cfgcaddy/local.toml` — destructive to real user state

### Recommended Isolation Strategy

**Dependency injection (preferred):** Pass `config_dir` and `cache_dir` as parameters throughout the new code. Defaults to XDG locations, but tests override:

```python
def render_template(
    tmpl_path: Path,
    variables: dict,
    output_dir: Path,  # injected in tests
) -> Path: ...

def load_local_toml(
    config_dir: Path = None  # defaults to ~/.config/cfgcaddy/
) -> dict: ...
```

**XDG environment variable override (fallback):** Respect `XDG_CACHE_HOME` and `XDG_CONFIG_HOME` throughout the implementation. Tests set these to temp dirs:

```python
import pytest, tempfile, os

@pytest.fixture
def isolated_xdg(tmp_path):
    with patch.dict(os.environ, {
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
    }):
        yield tmp_path
```

The dependency injection approach is cleaner and doesn't require modifying environment variables. The XDG approach is more realistic (tests the same code path as production) but requires the implementation to honor XDG variables, which is good practice anyway.

### Testing Template Rendering

Template rendering tests should cover:
1. Happy path: variable substitution works
2. `StrictUndefined`: missing variable raises `UndefinedError` with correct variable name
3. `TemplateSyntaxError`: malformed template (Go syntax `{{.var}}`) raises with filename info
4. Atomic write: partial file is never observable (hard to test directly; verify rename pattern is used)
5. Permission copying: rendered output has same mode as source
6. No `.tmpl` suffix: rendered file doesn't have `.tmpl` in its name

### Testing ## Scoring

Scoring tests are pure functions (no filesystem I/O for the scoring logic itself) and are straightforward. Key cases:
1. Highest-score candidate wins
2. Non-matching candidates are excluded
3. Tie → ambiguous (doctor detects, link uses deterministic tiebreak)
4. No candidates match → no file linked + warning emitted
5. Both `gitconfig` and `gitconfig##default` present → tiebreak applied
6. Ignore patterns apply to base name, not full `##`-suffixed name

---

## Summary: Highest-Priority Risks

1. **Silent data corruption from default Jinja2 `Environment()`** — Using `Environment()` without `StrictUndefined` silently replaces any `{{ identifier }}` with an empty string if the variable is missing. A shell script that happens to contain `{{hostname}}` as a comment would be silently corrupted with no error. **Fix is one line** (`undefined=StrictUndefined`) but must be enforced by code review and tests.

2. **Ignore pattern regression breaks secret file protection** — Existing users who have `ignore: ["secrets.sh"]` in `.cfgcaddy.yml` will find that `secrets.sh##os.darwin` is NOT ignored by that pattern after the `##` feature lands. Their secrets file gets symlinked to HOME. The implementation must extract the base name (before `##`) before running pathspec matching. This must be explicitly tested with cases like "ignore pattern for exact filename ignores all `##` variants."

3. **Rendered cache at `~/.cache/` can be cleared, breaking shell startup** — If `~/.cache/cfgcaddy/rendered/` is deleted (disk cleanup, CI, fresh machine restore), all symlinks from shell startup files to rendered templates become broken. Shell startup fails with cryptic "No such file or directory." Consider `~/.local/share/cfgcaddy/rendered/` (XDG_DATA_HOME) instead of `~/.cache/`, or ensure `cfgcaddy link` detects and repairs broken rendered-target symlinks. Additionally, rendered files may contain actual secrets (if user puts token values directly in `local.toml`) — the cache dir must be created with `0700` permissions.
