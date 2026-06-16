# Feature Research: Comparable Implementations

Research covering chezmoi, yadm, toml-bombadil, and Python dotfile tools.

---

## 1. Chezmoi's File Naming / Attribute System

**Key finding:** Chezmoi does NOT use a `##` suffix system. It uses a prefix-based naming convention where source filenames encode file attributes via well-defined prefixes.

### Prefix constants (from `internal/chezmoi/chezmoi.go`)

```
afterPrefix      = "after_"
beforePrefix     = "before_"
createPrefix     = "create_"
dotPrefix        = "dot_"
emptyPrefix      = "empty_"
encryptedPrefix  = "encrypted_"
exactPrefix      = "exact_"
executablePrefix = "executable_"
literalPrefix    = "literal_"
modifyPrefix     = "modify_"
oncePrefix       = "once_"
onChangePrefix   = "onchange_"
privatePrefix    = "private_"
readOnlyPrefix   = "readonly_"
removePrefix     = "remove_"
runPrefix        = "run_"
symlinkPrefix    = "symlink_"
literalSuffix    = ".literal"
TemplateSuffix   = ".tmpl"
```

### How it works (`internal/chezmoi/attr.go`)

`parseFileAttr(name, encryptedSuffix)` strips prefixes in strict order from the filename, building a `FileAttr` struct. Multiple attributes are composed by sequential prefix stripping (not scoring): `encrypted_private_readonly_empty_executable_dot_file.tmpl` is a valid source name that decodes to a hidden, template, encrypted, private, read-only, executable file.

**Relevance for cfgcaddy:** Chezmoi's attribute system is prefix-based and file-type-oriented; it has no concept of OS/hostname-based alternate file selection. The `##` scoring feature is **yadm's invention**, not chezmoi's. cfgcaddy's `##` system should be modeled on yadm.

---

## 2. YADM's `##` Alternate Files System

Source: [yadm alternates documentation](https://yadm.io/docs/alternates)

### Suffix structure

```
filename##<condition>[,<condition>,...]
```

Each condition is `attribute.value` (e.g., `os.darwin`, `hostname.work-laptop`). Multiple conditions separated by commas; all must match (logical AND). Abbreviations work (`o` = `os`, `h` = `hostname`).

### Supported attributes

| Attribute | Abbrev | Source |
|-----------|--------|--------|
| `arch` | `a` | `uname -m` |
| `class` | `c` | User-defined local config |
| `default` | — | Always matches, score 0 |
| `distro` | `d` | `lsb_release -si` or `/etc/os-release` |
| `distro_family` | `f` | `/etc/os-release` ID_LIKE |
| `extension` | `e` | No scoring, editor hint only |
| `hostname` | `h` | `uname -n` (short, no domain) |
| `os` | `o` | `uname -s` (e.g. `Darwin`, `Linux`) |
| `template` | `t` | Triggers template processing |
| `user` | `u` | `id -u -n` |

### Scoring algorithm

From yadm source code (`score_file()` function):

```
score = sum(condition_deltas) + 1000 * (number_of_matching_conditions)
```

**Delta values per attribute (positive = matches, negative = doesn't match):**
- `arch`: ±1
- `os`: ±2
- `distro`: ±4
- `distro_family`: ±8
- `class`: ±16
- `hostname`: ±32
- `user`: ±64
- `extension`: 0 (skipped entirely)
- `template`: 0 (triggers rendering, not scored)
- `default`: 0

**Key rules:**
- All conditions in a multi-condition filename must match; any non-matching condition eliminates the candidate
- More specific (more conditions) always beats less specific
- Negative conditions (`~hostname.work-laptop`) award their delta only relative to non-negated conditions
- The `1000 * count` multiplier ensures that a file with N matching conditions always beats one with N-1 conditions regardless of attribute types
- No match and no `##default` = no symlink created

### Implication for cfgcaddy's `##` system

The requirements spec (scores 0/1/2 for default/os/hostname+os) is a simplified version of yadm's algorithm. A clean Python implementation:

```python
CONDITION_WEIGHTS = {
    "os": 2,
    "hostname": 32,
    "profile": 16,
    "default": 0,
}

def score_candidate(filename: str, context: dict) -> int | None:
    """Returns score or None if any condition doesn't match."""
    base, _, suffix = filename.partition("##")
    if not suffix:
        return 0  # No ## = treat as default
    
    score = 0
    for condition in suffix.split("##"):
        key, _, value = condition.partition(".")
        if key == "default":
            continue
        weight = CONDITION_WEIGHTS.get(key, 0)
        if context.get(key) == value:
            score += weight + 1000  # match bonus keeps count-ordering
        else:
            return None  # disqualified
    return score
```

The requirements spec's simpler additive scoring (1 per matching condition) is also valid — the `1000 * count` trick is needed to guarantee count-ordering only when mixing high- and low-weight attributes. For cfgcaddy's limited attribute set (os=1pt, hostname=1pt), simple counting suffices.

---

## 3. Toml-Bombadil's Render-Then-Symlink Pattern

Source: [toml-bombadil docs](https://oknozor.github.io/toml-bombadil/quickstart.html), [lib.rs entry](https://lib.rs/crates/toml-bombadil)

**Tool:** Written in Rust (not Python), but the architectural pattern is directly applicable.

### How it works

1. **Source directory:** Contains template dotfiles (using Tera/Jinja-style `{{ variable }}` syntax) and a `vars.toml` defining variable values.
2. **`bombadil link` step:**
   - Reads all variables from `vars.toml` (and profile-specific var files)
   - Renders each template file by substituting variables → output written to `.dots/` directory inside the dotfiles repo
   - Creates symlinks from target paths (e.g., `~/.gitconfig`) to the rendered copies in `.dots/`
3. **Result:** The symlink target is never the raw template — it's always the rendered intermediate copy.

### Why this approach

- The committed file is a template (safe for public repos)
- The rendered file in `.dots/` is `.gitignore`d
- If variables change (new machine), re-run `bombadil link` to re-render
- Symlinks always point to rendered content, so apps read resolved values

### Mapping to cfgcaddy Feature 1

cfgcaddy's design mirrors this exactly:
- Template source file: `gitconfig.tmpl` in dotfiles repo
- Local variables: `~/.config/cfgcaddy/local.toml` (outside repo, gitignored by location)
- Rendered output: `~/.cache/cfgcaddy/rendered/gitconfig` (also outside repo)
- Symlink: `~/.gitconfig` → `~/.cache/cfgcaddy/rendered/gitconfig`

**Key difference from chezmoi:** chezmoi renders templates at apply time but does NOT use an intermediate rendered file cache — it writes the final content directly. Toml-bombadil's approach (and cfgcaddy's planned approach) keeps a rendered cache, which is useful for `diff` (compare rendered vs. deployed) and debugging.

---

## 4. Doctor Command Pattern (Chezmoi)

Source: `internal/cmd/doctorcmd.go` (23KB)

### Architecture

Chezmoi's doctor uses a **check interface** pattern:

```go
type check interface {
    Name() string
    Run(config *Config) (checkResult, string)
}
```

Each check type is a struct implementing this interface. Check result levels:

```go
checkResultOmitted  = -3  // hidden from output
checkResultFailed   = -2  // could not complete check
checkResultSkipped  = -1  // intentionally skipped
checkResultOK       = 0   // no issues
checkResultInfo     = 1   // interesting, not a problem
checkResultWarning  = 2   // might indicate a problem  
checkResultError    = 3   // definite problem
```

### Output format

Uses `tabwriter` for aligned columns:

```
RESULT    CHECK              MESSAGE
ok        version            2.47.0, commit abc123
warning   latest-version     2.48.0 available
ok        source-dir         ~/dotfiles is a git working tree (clean)
warning   suspicious-entries ~/dotfiles/.env
ok        symlink            created symlink from .new-name to .old-name
ok        git-command        found /usr/bin/git, version 2.43.0
info      age-command        age not found in $PATH
```

### Exit code strategy

```go
if worstResult > checkResultWarning {
    return chezmoi.ExitCodeError(1)
}
return nil
```

Only exits non-zero for errors (not warnings). Warnings are shown but don't fail the command.

### Check catalog in chezmoi's doctor

- `versionCheck`: current version + commit
- `latestVersionCheck`: GitHub API latest release comparison
- `configFileCheck`: config file exists, parseable, not a symlink
- `dirCheck`: source/dest dirs exist + git status (clean/dirty)
- `suspiciousEntriesCheck`: files in source dir that look like secrets
- `symlinkCheck`: verifies OS can create symlinks (temp dir test)
- `binaryCheck`: tool existence + minimum version (git, age, gpg, 1password, bitwarden, etc.)
- `fileCheck`: required files exist

### Python translation pattern for cfgcaddy

```python
from dataclasses import dataclass
from enum import IntEnum
from typing import Protocol

class CheckLevel(IntEnum):
    PASS = 0
    WARN = 1
    FAIL = 2

@dataclass
class CheckResult:
    level: CheckLevel
    name: str
    message: str

class Check(Protocol):
    def name(self) -> str: ...
    def run(self) -> CheckResult: ...

def run_doctor(checks: list[Check], fix: bool = False) -> int:
    worst = CheckLevel.PASS
    for check in checks:
        result = check.run()
        icon = {CheckLevel.PASS: "✓", CheckLevel.WARN: "!", CheckLevel.FAIL: "✗"}[result.level]
        click.echo(f"  {icon} {result.name}: {result.message}")
        worst = max(worst, result.level)
    return worst.value  # 0=pass, 1=warn, 2=fail
```

The requirements spec's `0=all pass, 1=warnings, 2=failures` exit code scheme aligns with chezmoi's pattern (chezmoi only exits 1 for errors, but cfgcaddy's 3-level scheme is cleaner).

---

## 5. Python CLI Per-Machine Config Patterns

### Dotdrop

Source: [dotdrop config docs](https://dotdrop.readthedocs.io/en/latest/config/config-config/), [dotdrop usage](https://dotdrop.readthedocs.io/en/latest/usage/)

**Profile system:**
- Default profile = hostname (auto-detected)
- Can override with `-p/--profile` flag
- Profiles are sections in `config.yaml` listing which dotfiles apply
- Profile-level variables override global variables

**`import_variables` pattern:**
```yaml
config:
  import_variables:
    - ~/.config/dotdrop/local-vars.yaml:optional
```

The `:optional` suffix prevents failures when the file doesn't exist (machine doesn't have local overrides). This is exactly the pattern cfgcaddy needs for `~/.config/cfgcaddy/local.toml` — if it doesn't exist and no `.tmpl` files are present, nothing should fail.

**Variable precedence:** `profile variables > imported variables > global variables`

### Mackup

Source: [mackup GitHub](https://github.com/lra/mackup)

**Not relevant for per-machine config** — mackup is a backup/restore tool that symlinks application configs to cloud storage. No templating or per-machine variables. Deprecated on macOS Sonoma (Aug 2024) due to symlink restrictions on `~/Library/Preferences`.

### Key patterns worth borrowing from dotdrop

1. **`:optional` imports** — load local config files that may not exist without erroring
2. **Profile = hostname by default** — reduces friction for new machines; cfgcaddy can auto-detect
3. **`import_configs`** — whole config file merging enables a "base + machine overlay" pattern that maps well to cfgcaddy's `local.toml` + `profiles/<name>.toml`
4. **Variable precedence hierarchy** — profile > imported > global is a proven ordering; cfgcaddy's `profiles/<name>.toml` overriding `local.toml` follows the same logic

---

## Summary: Key Implementation Decisions

### Alternate file scoring
Use yadm's scoring approach: `score = condition_weight_sum + 1000 * match_count`. For cfgcaddy's limited attribute set (os, hostname, profile, default), simple additive scoring (1 per match) with more-conditions-wins tiebreak is sufficient and matches the requirements spec exactly. Implement as a pure function `score_candidate(filename, context) -> int | None` where `None` disqualifies the candidate.

### Template rendering
Follow toml-bombadil's intermediate cache pattern: render to `~/.cache/cfgcaddy/rendered/<path>`, symlink the rendered file. This enables `cfgcaddy diff` to compare rendered content against current deployed content without re-rendering. Use `tomllib` (stdlib 3.11+, `tomli` backport for 3.10) for `local.toml` parsing; Jinja2 for rendering with `undefined=StrictUndefined` to surface missing variables clearly.

### Doctor command
Implement the check-interface pattern from chezmoi: a `Check` protocol/ABC with `name()` and `run() -> CheckResult`. Each check is a small class; the doctor command iterates and tabulates. Exit code `0/1/2` maps to `pass/warn/fail` as the requirements specify. The `:optional` import pattern from dotdrop means `local.toml` absence is a warning (not a failure) when no `.tmpl` files are present — only a failure when `.tmpl` files exist but `local.toml` is missing.
