# Requirements: cfgcaddy Feature Expansion

## Project Summary

Extend cfgcaddy (a Python symlink-based dotfile manager) to close the DX gap with chezmoi. All features are additive — zero breakage to existing setup. Changes land as a PR into the cfgcaddy submodule at `~/dotfiles/cfgcaddy/`.

## Background & Motivation

cfgcaddy currently manages dotfiles via symlinks from a source directory to HOME. It has no concept of secrets, templating, machine-specific config, or preview. The public dotfiles repo at github.com/tstapler/dotfiles exposes:
- 1Password vault item names and internal tooling stack (via `.shell/secrets.op.sh.tpl`)
- No mechanism to vary config between work laptop, home machine, or servers

Research into the ecosystem (chezmoi, yadm, dotter, toml-bombadil) identified best-in-class patterns for each missing feature. This project implements them in cfgcaddy's Python codebase.

## Existing System Constraints

- cfgcaddy is a Python project using `uv`, `click`, `ruamel.yaml`, `questionary`
- Config lives in `.cfgcaddy.yml` (committed to dotfiles repo)
- Current `cfgcaddy link` creates symlinks; this must continue to work unchanged
- cfgcaddy is a git submodule in `~/dotfiles/cfgcaddy/` — changes require a PR to the upstream repo
- The dotfiles repo is public on GitHub — secrets must never appear in committed files

## Scope: Features to Implement

### Feature 1: Local Data File + Jinja2 Template Rendering

**What:** A machine-local file (`~/.config/cfgcaddy/local.toml`, gitignored by definition since it's outside the repo) stores per-machine variables. Any source file with a `.tmpl` suffix is rendered via Jinja2 before the symlink is created — cfgcaddy writes the rendered output to a temp/cache location and symlinks that instead.

**Why:** Enables vault paths, email addresses, hostnames, and other machine-specific values to stay out of the public repo. The committed file contains `{{ github_token_path }}`, the local.toml contains `github_token_path = "op://FBG/FBG Github PAT/credential"`.

**Acceptance criteria:**
- `cfgcaddy link` renders `.tmpl` files using Jinja2 with variables from `~/.config/cfgcaddy/local.toml`
- Missing variable raises a clear error with the variable name and file
- Non-.tmpl files are unaffected (existing behavior preserved)
- `cfgcaddy secrets init` interactive wizard creates/updates `local.toml` by prompting for each variable referenced in `.tmpl` files in the source directory
- Rendered output written to `~/.cache/cfgcaddy/rendered/` (not committed anywhere)
- `local.toml` supports TOML format with nested tables for organization

### Feature 2: Alternate File Scoring (`##` suffix system)

**What:** Source files can have `##key.value` suffixes that cfgcaddy uses to select the best match for the current machine. Scoring: more specific = higher score. If multiple files match, highest score wins.

**Supported keys:**
- `##os.darwin`, `##os.linux`, `##os.windows` — matched against `platform.system().lower()`
- `##hostname.work-laptop` — matched against `socket.gethostname()`
- `##default` — always matches, lowest score (0)

**Example:** For target `.gitconfig`, candidates:
- `gitconfig##os.darwin##hostname.work-laptop` → score 2 (both match) → selected
- `gitconfig##os.darwin` → score 1
- `gitconfig##default` → score 0

**Acceptance criteria:**
- `cfgcaddy link` selects highest-scoring alternate file when multiple candidates exist
- Non-matching candidates are silently ignored
- Files with no `##` suffix are treated as `##default` (score 0) — preserves existing behavior
- `cfgcaddy doctor` reports ambiguous cases where two candidates have equal scores
- `.cfgcaddy.yml` `ignore` patterns apply to the base name (before `##`)

### Feature 3: Profiles

**What:** Named profiles (e.g., `work`, `home`, `server`) that select a different `local.toml` variable set and optionally a different set of active links. Activated via `cfgcaddy --profile work` or a `default_profile` setting in `.cfgcaddy.yml`.

**Profile resolution order:**
1. CLI flag `--profile <name>`
2. Environment variable `CFGCADDY_PROFILE`
3. `default_profile` in `.cfgcaddy.yml`
4. No profile (base local.toml only)

**Profile data files:** `~/.config/cfgcaddy/profiles/<name>.toml` — merged on top of `local.toml` (profile values override base values).

**Acceptance criteria:**
- `cfgcaddy --profile work link` loads `~/.config/cfgcaddy/profiles/work.toml` merged over `local.toml`
- `cfgcaddy profiles list` shows available profiles (files in `~/.config/cfgcaddy/profiles/`)
- Profile-specific alternate file selection: `##profile.work` suffix supported as a scoring key
- `cfgcaddy profiles init <name>` creates a new profile file interactively

### Feature 4: `diff` Command

**What:** `cfgcaddy diff` shows what `cfgcaddy link` would change without making any changes. Output mimics `diff` format showing: new symlinks that would be created, existing symlinks that point to a different target, broken symlinks that would be repaired, `.tmpl` files showing rendered diff vs current deployed content.

**Acceptance criteria:**
- `cfgcaddy diff` exits 0 if no changes, exits 1 if changes exist (scriptable)
- Output clearly distinguishes: new links, changed links, removed links, template content changes
- `cfgcaddy link --dry-run` is an alias
- Works correctly with alternate file scoring and profiles

### Feature 5: `doctor` Command

**What:** `cfgcaddy doctor` audits the current state and reports issues without making changes.

**Checks:**
- Broken symlinks (target doesn't exist)
- Symlinks pointing to wrong source (drift)
- `.tmpl` files with missing variables in `local.toml`
- Alternate file candidates with tied scores (ambiguous)
- `local.toml` missing entirely when `.tmpl` files exist
- `op` CLI not installed when `op://` references present in `local.toml`

**Acceptance criteria:**
- Output uses clear PASS/WARN/FAIL indicators per check
- Exit code: 0 = all pass, 1 = warnings, 2 = failures
- `cfgcaddy doctor --fix` auto-repairs broken symlinks where safe

## Non-Functional Requirements

- Zero regression: existing `cfgcaddy link` and `cfgcaddy init` behavior unchanged
- All new features are opt-in (no local.toml = no templating, no `##` files = no scoring)
- Python 3.10+ compatibility (matches existing codebase)
- Dependencies: Jinja2 and `tomllib` (stdlib in 3.11+, `tomli` backport for 3.10) added to pyproject.toml
- Test coverage for all new commands using pytest (existing test pattern)
- Click-based CLI (consistent with existing commands)

## Out of Scope

- Run-once scripts (future phase)
- File encryption (future phase)
- External file management / URL fetching (future phase)
- Windows support for new features (existing Windows support must not regress)
- Migrating existing `.shell/secrets.op.sh.tpl` — that's a separate dotfiles PR after these features land
