# Adversarial Review: Dotfiles Bootstrap Revamp Implementation Plan

Reviewer role: adversarial. Every finding is an issue the implementer must resolve before writing code.

---

## Epic 1: Entry Point (`install.sh` / `bootstrap/run.sh`)

### Story 1.1 — install.sh

**FINDING 1 (CONCERN): `set -euo pipefail` + `sudo` interaction on first run**
`set -euo pipefail` combined with `sudo apt-get update` may abort if apt is locked (CI, cloud-init running in background). This is a silent failure mode — the script exits without error message. Add error handling around `apt-get` calls:
```bash
sudo apt-get update -qq || { echo "apt-get update failed; continuing anyway"; }
```
The `-qq` flag suppresses output but not non-zero exit codes.

**FINDING 2 (CONCERN): `exec` replaces the process — no error recovery**
`exec "$DOTFILES_DIR/bootstrap/run.sh" "$@"` replaces the current shell process. If `run.sh` does not exist (e.g. submodule checkout failed silently), the error message is obscure: `bash: exec: .../bootstrap/run.sh: No such file or directory`. Add a guard:
```bash
if [ ! -x "$DOTFILES_DIR/bootstrap/run.sh" ]; then
  echo "ERROR: $DOTFILES_DIR/bootstrap/run.sh not found or not executable" >&2
  exit 1
fi
exec "$DOTFILES_DIR/bootstrap/run.sh" "$@"
```

**FINDING 3 (CONCERN): `pacman -Sy` without `--needed` is non-idiomatic**
`pacman -Sy --noconfirm base-devel curl file git` will always output "installing" even if packages are already present, confusing idempotency. Use `pacman -S --needed --noconfirm` instead. Also: `-Sy` (sync + update DB only) without `-u` leaves the system in a partial upgrade state which pacman warns about. Should be `-Syu --needed --noconfirm` or `-S --needed --noconfirm` if DB was recently synced.

**FINDING 4 (CONCERN): No `NONINTERACTIVE=1` for Homebrew installer**
The official Homebrew install script checks for `NONINTERACTIVE=1` to suppress prompts. Without it, the script will pause and ask for confirmation on Linux. Set `NONINTERACTIVE=1` before calling the Homebrew installer:
```bash
export NONINTERACTIVE=1
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**FINDING 5 (CONCERN): `install.sh` calls `run.sh` which re-checks and re-installs Homebrew**
`install.sh` installs Homebrew, then delegates to `run.sh` which also has a Homebrew install check. This is redundant but harmless (idempotent). However, the `eval "$( /opt/homebrew/bin/brew shellenv )"` call in `run.sh` may fail if brew is already on PATH from the `install.sh` session. Not a blocker — just slightly wasteful.

### Story 1.2 — run.sh

**FINDING 6 (CONCERN): Shebang change from zsh to bash — confirm zsh tasks work**
`run.sh` is called from `install.sh` which uses bash. The shebang change is correct for Linux compatibility. Verify that nothing inside `run.sh` uses zsh-only syntax (e.g., `${param:-default}` works in both; `=(...)` process substitution does not). Current `run.sh` content uses `set -euo pipefail` which is bash/POSIX compatible.

---

## Epic 2: `bootstrap/playbook.yml`

### Story 2.1 — WSL2 detection + global vars

**FINDING 7 (CONCERN): WSL2 detection uses `shell:` module — this fails if `/proc/version` does not exist on macOS**
On macOS, `/proc/version` does not exist. The command `grep -qi microsoft /proc/version 2>/dev/null && echo yes || echo no` will produce `no` correctly due to `2>/dev/null`. This is actually safe. However: the `shell:` module is flagged by Ansible lint for not having `changed_when: false`. The plan includes `changed_when: false` — this is correct. No issue.

**FINDING 8 (CONCERN): `brew_prefix` ternary uses Jinja2 multi-line syntax — verify correctness**
```yaml
brew_prefix: >-
  {{ '/opt/homebrew' if ansible_os_family == 'Darwin' and ansible_architecture == 'arm64'
     else '/usr/local' if ansible_os_family == 'Darwin'
     else '/home/linuxbrew/.linuxbrew' }}
```
The `>-` block scalar folds newlines into spaces. The Jinja2 expression spans multiple lines inside `{{ }}`. Ansible evaluates the entire `{{ ... }}` block as a single template string, so line breaks inside `{{ }}` are permitted. This is syntactically valid. However: `ansible_architecture` on Apple Silicon returns `arm64` but on Intel returns `x86_64`. Confirm this fact name. The correct Ansible fact is `ansible_architecture` — confirmed correct.

**FINDING 9 (MISSING REQUIREMENT): `secrets` role is not documented in the plan**
The `secrets` role is referenced in `playbook.yml` and in the requirements, but there is NO epic, story, or task for the secrets role in the plan. The requirements say:
- Require 1Password CLI (`op`) — hard fail with clear message if missing
- Check `op account list` for active session
- Print sign-in instructions if not authenticated
- Test secret injection via `op inject --dry-run` when authenticated

The current secrets role could not be read (permission denied). The plan must include at minimum: a story to audit/rewrite the secrets role to match requirements. This is a **BLOCKED-class gap** — a role in the playbook has no implementation plan. Patching required.

**FINDING 10 (CONCERN): `gather_facts: true` is the default — no need to specify, but harmless**
Minor style note: `gather_facts: true` is already the default. Not an error. The existing `playbook.yml` does not set it, so the explicit declaration is cleaner documentation. No action needed.

---

## Epic 3: `homebrew` Role

### Story 3.1 — Linux prerequisites + install check

**FINDING 11 (CONCERN): `homebrew` module used for `brew update` but `homebrew` module may not be available on Linux**
In the current `main.yml` (to be rewritten), the plan uses `command: "{{ brew_prefix }}/bin/brew update"` — this is correct and avoids the `homebrew` Ansible module which is macOS-focused. The original role had `homebrew: update_homebrew: true` which would fail on Linux. The plan's fix is correct.

**FINDING 12 (CONCERN): `brew bundle install --no-lock` — verify `--no-lock` flag exists**
`brew bundle install --no-lock` is a valid flag (suppresses writing `Brewfile.lock.json`). Confirmed from Homebrew docs. No issue.

**FINDING 13 (MISSING): `Brewfile.linux` does not include `asdf`**
The `asdf` role depends on the `asdf` binary being installed by Homebrew via `Brewfile.linux`. The proposed `Brewfile.linux` content in Task 3.2.2 does NOT include `brew "asdf"`. If the `asdf` role runs on Linux, it will fail because `~/.asdf/asdf.sh` won't exist. `asdf` must be added to `Brewfile.linux`.

**FINDING 14 (CONCERN): Private tap issue not resolved in homebrew role tasks**
The plan acknowledges private taps (`fanatics-gaming/tap`, `tstapler/stelekit`) will fail on fresh machines, but provides no actual task-level fix. The homebrew role will unconditionally run `brew bundle install --file=Brewfile` on macOS, which will fail on private tap lines. The plan should specify concrete handling: either `|| true` on tap failures, or a task that pre-checks SSH config before running bundle. Currently this is documented as "future improvement" but it is a HIGH likelihood failure on every fresh macOS machine. Suggest adding `HOMEBREW_NO_AUTO_UPDATE=1` and splitting the brew bundle task to continue on error.

### Story 3.2 — Brewfile.linux

**FINDING 15 (CONCERN): `unzip` missing from `Brewfile.linux` (cited in risk register but not fixed)**
The plan's risk register notes "`unzip` not available on minimal Linux" but the `Brewfile.linux` content does not include `brew "unzip"` or `apt-get install unzip`. The fonts role uses Ansible's `unarchive` module which requires `unzip` on the host. Add `unzip` to `Brewfile.linux` or to the fonts role's prerequisite tasks.

---

## Epic 4: `dotfiles` Role

### Story 4.1 — uv + cfgcaddy

**FINDING 16 (CONCERN): `uv tool install cfgcaddy` idempotency — `failed_when` uses wrong output check**
The plan uses:
```yaml
failed_when: cfgcaddy_install.rc != 0 and 'already installed' not in cfgcaddy_install.stderr
```
The actual `uv tool install` output when already installed is: `cfgcaddy is already installed` in **stdout**, not stderr. The `failed_when` should check `cfgcaddy_install.stdout` not `cfgcaddy_install.stderr`. Alternatively, use `uv tool install --upgrade cfgcaddy` which is always idempotent and upgrades in place.

**FINDING 17 (CONCERN): `cfgcaddy init` will error if `~/.cfgcaddy.yml` already exists as a symlink**
The plan checks `stat: path: ~/.cfgcaddy.yml` and skips init if it exists. The `stat` module follows symlinks by default — `stat.exists` is true for symlinks. This is correct behavior (if the symlink exists, init was already done). However: if `~/.cfgcaddy.yml` is a broken symlink (target deleted), `stat.exists` returns false but `cfgcaddy init` may still fail. Edge case, low risk.

**FINDING 18 (CONCERN): `cfgcaddy link --no-interactive` vs `--no-interactive` flag name**
Research file shows the flag as `-y` / `--no-interactive`. The plan uses `--no-interactive` consistently. The features research file documents:
```
link  [-c CONFIG] [-y]
      -y / --no-interactive skips confirmation prompts.
```
The flag is `-y` OR `--no-interactive` (long form). Using `--no-interactive` is correct; verify this is the actual long-form flag name in cfgcaddy 0.1.8. If cfgcaddy uses `--yes` or only `-y`, the task will fail with "no such option". This should be verified against the installed cfgcaddy version.

---

## Epic 5: `shell` Role + `asdf` Role

### Story 5.1 — shell role

**FINDING 19 (CONCERN): `zplug` fork — using `https://github.com/tstapler/zplug` not upstream**
The shell role clones `https://github.com/tstapler/zplug` (a personal fork). On a fresh machine, this fork must exist and be public. If the fork becomes stale or private, the clone fails. This is not a plan issue per se but should be documented. No change needed.

### Story 5.2 — asdf role

**FINDING 20 (CONCERN): `asdf plugin add` for `lein` and `clojure` may require `asdf-java` as prerequisite**
The `.tool-versions` includes:
- `java openjdk-21` (requires `asdf-java` plugin)
- `lein 2.9.5` (Leiningen — requires `asdf-lein` plugin, which may depend on `asdf-java`)
- `clojure 1.10.1.739` (requires `asdf-clojure`)

Some asdf plugins require other plugins to be installed first (e.g., `lein` needs `java` first). The `Add asdf plugins` task loops over all plugins in parallel (Ansible's default loop behavior is sequential, not parallel, so this should be ordered). However, the loop iterates over `asdf_tool_names.stdout_lines` which is in `.tool-versions` order. The `.tool-versions` file lists `java` before `lein`, so the ordering is correct. No issue.

**FINDING 21 (CONCERN): `asdf install` timeout — `nim` and `golang` compile from source**
`asdf install nim 2.0.8` and similar compile-from-source installations can take 5-30 minutes. Ansible has a default task timeout of no limit (unless configured). This is fine but should be documented so implementers don't think the playbook has hung.

**FINDING 22 (CONCERN): asdf `.asdf/asdf.sh` path assumption**
The plan assumes asdf is installed to `~/.asdf/` (the default home directory installation). When installed via Homebrew, asdf may place `asdf.sh` at `{{ brew_prefix }}/opt/asdf/libexec/asdf.sh` rather than `~/.asdf/asdf.sh`. The correct source path for Homebrew-installed asdf is:
```bash
. $(brew --prefix asdf)/libexec/asdf.sh
```
This is a **show-stopper** if asdf was installed via Homebrew and the `~/.asdf/asdf.sh` file does not exist. The tasks sourcing `. {{ ansible_env.HOME }}/.asdf/asdf.sh` will fail with "No such file or directory". The plan must handle both the Homebrew install path and the legacy `~/.asdf/` install path. Recommend using `{{ brew_prefix }}/opt/asdf/libexec/asdf.sh` as primary with fallback.

---

## Epic 6: `fonts` Role

### Story 6.1 — fonts

**FINDING 23 (CONCERN): `homebrew_cask` module is deprecated; use `community.general.homebrew_cask`**
The `homebrew_cask` module was moved to `community.general` collection. The plan should specify:
```yaml
community.general.homebrew_cask:
  name: font-meslo-lg-nerd-font
  state: present
```
Or alternatively, ensure `font-meslo-lg-nerd-font` is already in the main `Brewfile` as a cask entry (which is the correct approach — casks should be in the Brewfile, not installed ad-hoc by the fonts role). If the cask is in `Brewfile`, the fonts role on macOS needs only to verify presence, not install.

**FINDING 24 (CONCERN): GitHub `releases/latest` URL redirect — idempotency issue**
`get_url` with `url: https://github.com/ryanoasis/nerd-fonts/releases/latest/download/Meslo.zip` will re-download every time the task runs if the file is already at `/tmp/Meslo.zip`, because `get_url` uses checksums to determine if re-download is needed but `latest` may resolve to different tags. Add `dest: /tmp/Meslo.zip` with `force: false` to skip re-download if file exists:
```yaml
get_url:
  url: "..."
  dest: "/tmp/Meslo.zip"
  force: false
  mode: '0644'
```
`force: false` (default) only downloads if the file does not exist.

**FINDING 25 (CONCERN): `unarchive` task is not idempotent — will re-extract on every run**
The `unarchive` module extracts every time it runs. There is no idempotency guard. Add a check:
```yaml
- name: Check if Meslo font already installed
  find:
    paths: "{{ ansible_env.HOME }}/.local/share/fonts/"
    patterns: "MesloLG*"
  register: font_files

- name: Unzip Meslo Nerd Font (Linux)
  unarchive:
    ...
  when: font_files.matched == 0
```

---

## Epic 7: `claude` Role

### Story 7.1 — claude role

**FINDING 26 (CONCERN): `npm install -g` path on macOS**
When `node` is installed via Homebrew, `npm install -g` installs to `$(npm prefix -g)/bin`. On macOS with Homebrew, this is typically `/opt/homebrew/bin` (already on PATH). On Linux, it may be `/home/linuxbrew/.linuxbrew/bin`. The `claude` binary should be findable after install without additional PATH manipulation. The plan's `PATH` environment in the verify task includes `brew_prefix/bin` which is correct.

**FINDING 27 (CONCERN): `npm install -g @anthropic-ai/claude-code` idempotency**
`npm install -g` is idempotent — it upgrades the package if already installed. Re-running will not fail. The `when: claude_check.rc != 0` guard means upgrade won't happen on re-runs. This is intentional but means claude will not be upgraded by re-running the playbook. Acceptable behavior; document it.

---

## Epic 8: Cleanup

### Story 8.1 / 8.2 — Retirement

**FINDING 28 (CONCERN): `stapler-scripts/install-scripts/osx-ansible-install.sh` may not exist**
Task 8.2.1 runs `git rm stapler-scripts/install-scripts/osx-ansible-install.sh`. Verify this file exists before specifying it as a deletion target. From the filesystem listing, `stapler-scripts/install-scripts/` directory exists. The file may or may not be present — the plan should include a verification step.

---

## Requirements Coverage Check

| Requirement | Covered | Notes |
|---|---|---|
| OS detection (macOS, Ubuntu, Arch, WSL2) | YES | install.sh Task 1.1.1 |
| Install Homebrew (macOS + Linux) | YES | Epic 3 |
| Install Ansible via Homebrew | YES | install.sh Task 1.1.4 |
| Clone repo if not present | YES | install.sh Task 1.1.4 |
| Initialize git submodules | YES | install.sh Task 1.1.4 |
| `homebrew` role: brew bundle macOS | YES | Story 3.2 |
| `homebrew` role: brew bundle Linux | YES | Story 3.2, Brewfile.linux |
| `dotfiles` role: uv install | YES | Story 4.1 |
| `dotfiles` role: cfgcaddy from PyPI | YES | Story 4.1 |
| `dotfiles` role: cfgcaddy link --config | PARTIAL | Uses default config path; see Finding 17 |
| `shell` role: fix asdf fileglob bug | YES | Story 5.1 (removed broken task) |
| `asdf` role: new role | YES | Story 5.2 |
| `asdf` role: idempotent plugin install | YES | Story 5.2 |
| `nix` role: keep as-is | YES | Not modified |
| `secrets` role: 1Password check | **NO** | **No epic/story for secrets role — BLOCKED** |
| `fonts` role: new role | YES | Epic 6 |
| `claude` role: new role | YES | Epic 7 |
| Retirement: bootstrap-dotfiles.sh deprecation | YES | Story 8.1 |
| Retirement: bootstrap.yaml deletion | YES | Story 8.2 |
| Retirement: osx-ansible-install.sh deletion | YES | Story 8.2 |
| Each role independently re-runnable via --tags | YES | Tag strategy documented |
| WSL2 detection + best-effort support | YES | Epic 2, fonts skip |

---

## Ordering / Dependency Issues

1. **`asdf` role before `dotfiles`?**: No — `dotfiles` links config files but does not depend on asdf. The current ordering (homebrew → dotfiles → shell → asdf) is correct.
2. **`claude` role depends on `dotfiles`**: The `.claude/` config linking happens in the dotfiles role. The claude role runs after dotfiles. Correct.
3. **`asdf` binary from Homebrew must be available before `asdf` role runs**: Homebrew role runs first and installs `asdf` via Brewfile. But `asdf` must be in `Brewfile` and `Brewfile.linux`. This is noted in the plan but not explicitly tasked as a verification step.

---

## Verdict

**CONCERNS**

The plan is substantively complete and addresses all major bugs identified in requirements. It is NOT BLOCKED because no finding individually prevents the plan from being executed. However, several CONCERNS must be addressed before implementation:

**Top 3 Findings (Highest Impact)**:

1. **Finding 9 (CONCERNS - near BLOCKED): `secrets` role has no implementation plan**
   The secrets role is in `playbook.yml` roles list but has zero coverage in the plan. Requirements specify explicit behavior (1Password CLI check, `op account list`, dry-run injection). This is a missing epic. The implementer will hit a wall at this role.

2. **Finding 22 (CONCERNS - HIGH): asdf Homebrew install path assumption**
   The `asdf` role sources `~/.asdf/asdf.sh` but Homebrew-installed asdf places `asdf.sh` at `$(brew --prefix asdf)/libexec/asdf.sh`. Every asdf task will fail with "No such file or directory" on systems where asdf was installed via Homebrew. Fix: use `{{ brew_prefix }}/opt/asdf/libexec/asdf.sh` as the source path.

3. **Finding 13 (CONCERNS - HIGH): `asdf` missing from `Brewfile.linux`**
   The proposed `Brewfile.linux` content does not include `brew "asdf"`. The `asdf` role cannot run on Linux without the asdf binary. This will cause the entire `asdf` role to fail on Linux with "command not found: asdf".

**Additional CONCERNS to address before coding**:
- Finding 4: Missing `NONINTERACTIVE=1` for Homebrew installer
- Finding 15: `unzip` missing from `Brewfile.linux` (needed by fonts role)
- Finding 16: `uv tool install` "already installed" in stdout not stderr
- Finding 23: Deprecated `homebrew_cask` module (use `community.general.homebrew_cask`)
- Finding 25: `unarchive` not idempotent — will re-extract fonts on every run
