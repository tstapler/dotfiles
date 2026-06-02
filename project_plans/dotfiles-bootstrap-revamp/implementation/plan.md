# Dotfiles Bootstrap Revamp — Implementation Plan

## Summary

This plan consolidates two diverged bootstrap systems into a single Ansible-driven workflow. The canonical entry point is a new `install.sh` at repo root, reachable via `curl -fsSL`. All existing bugs are fixed and four new roles are added (asdf, fonts, claude, secrets revamp). The total scope is 9 epics, 13 stories, 22 tasks.

**Post-adversarial-review patches applied**: secrets role added (Epic 9), asdf Homebrew path fixed, `asdf` and `unzip` added to `Brewfile.linux`, `NONINTERACTIVE=1` added to Homebrew install, `uv tool install` idempotency fix corrected (stdout not stderr), `community.general.homebrew_cask` used, fonts unarchive idempotency guard added.

---

## Epics / Stories / Tasks

---

### Epic 1: Entry Point (`install.sh`)

**Goal**: Create a single `install.sh` at repo root that handles pre-Ansible prerequisites and delegates to `bootstrap/run.sh`.

---

#### Story 1.1: Create `install.sh`

**File**: `install.sh` (new, repo root)

**Acceptance criteria**:
- Running on macOS ARM64 installs Homebrew at `/opt/homebrew`, installs Ansible, clones repo, runs playbook
- Running on macOS Intel installs Homebrew at `/usr/local`, all subsequent steps work
- Running on Ubuntu/Debian: installs prerequisites via apt, then linuxbrew path
- Running on Arch: installs prerequisites via pacman, then linuxbrew path
- Script is idempotent — running twice produces no errors
- Script is reachable at `https://raw.githubusercontent.com/tstapler/dotfiles/master/install.sh`

**Tasks**:

**Task 1.1.1**: Create `install.sh` with OS detection function
```bash
#!/usr/bin/env bash
set -euo pipefail

DOTFILES_REPO="https://github.com/tstapler/dotfiles"
DOTFILES_DIR="${HOME}/dotfiles"

detect_os() {
  case "$(uname -s)" in
    Darwin) echo "macos" ;;
    Linux)
      if grep -qi microsoft /proc/version 2>/dev/null; then
        echo "wsl2"
      elif [ -f /etc/arch-release ]; then
        echo "arch"
      elif [ -f /etc/debian_version ]; then
        echo "ubuntu"
      else
        echo "linux"
      fi
      ;;
    *) echo "unknown" ;;
  esac
}

OS=$(detect_os)
echo "Detected OS: $OS"
```

**Task 1.1.2**: Add Linux prerequisites installation block
```bash
install_linux_prereqs() {
  case "$OS" in
    ubuntu|wsl2)
      sudo apt-get update -qq || { echo "apt-get update failed; continuing anyway"; true; }
      sudo apt-get install -y build-essential curl file git unzip
      ;;
    arch)
      # -S --needed --noconfirm avoids partial-upgrade and re-installs of existing packages
      sudo pacman -S --needed --noconfirm base-devel curl file git unzip
      ;;
  esac
}

if [ "$OS" != "macos" ]; then
  install_linux_prereqs
fi
```

**Task 1.1.3**: Add Homebrew installation with correct platform path detection
```bash
install_homebrew() {
  if ! command -v brew &>/dev/null; then
    echo "Installing Homebrew..."
    # NONINTERACTIVE=1 suppresses prompts in the Homebrew installer
    export NONINTERACTIVE=1
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  fi

  # Add brew to PATH for this session (handle all three install locations)
  if [ -f /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [ -f /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
  elif [ -f /home/linuxbrew/.linuxbrew/bin/brew ]; then
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
  fi
}

install_homebrew
```

**Task 1.1.4**: Add Ansible install, git clone, submodule init, and delegation to `run.sh`
```bash
# Install Ansible via brew
if ! command -v ansible-playbook &>/dev/null; then
  echo "Installing Ansible..."
  brew install ansible
fi

# Clone dotfiles repo if not already present
if [ ! -d "$DOTFILES_DIR" ]; then
  echo "Cloning dotfiles..."
  git clone "$DOTFILES_REPO" "$DOTFILES_DIR"
else
  echo "Dotfiles directory already exists at $DOTFILES_DIR, skipping clone."
fi

# Initialize and update git submodules
# Only update if there are uninitialized submodules (-q suppresses noise)
if git -C "$DOTFILES_DIR" submodule status | grep -q "^-"; then
  echo "Initializing git submodules..."
  git -C "$DOTFILES_DIR" submodule update --init --recursive
fi

# Guard: verify run.sh exists before exec-ing into it
if [ ! -x "$DOTFILES_DIR/bootstrap/run.sh" ]; then
  echo "ERROR: $DOTFILES_DIR/bootstrap/run.sh not found or not executable" >&2
  exit 1
fi

# Delegate to bootstrap/run.sh
exec "$DOTFILES_DIR/bootstrap/run.sh" "$@"
```

**Task 1.1.5**: Make script executable and commit
```bash
chmod +x install.sh
git add install.sh
git commit -m "feat: add install.sh one-liner entry point"
```

---

#### Story 1.2: Update `bootstrap/run.sh`

**File**: `bootstrap/run.sh` (modify existing)

**Acceptance criteria**:
- `run.sh` still works standalone (for users who have already cloned)
- Brew PATH resolution handles Apple Silicon, Intel, and Linux paths
- No longer hardcodes `/opt/homebrew` eval path exclusively

**Tasks**:

**Task 1.2.1**: Fix Homebrew PATH eval in `run.sh` to handle all three install locations
```bash
#!/usr/bin/env bash
# Bootstrap the Ansible playbook. Called by install.sh or directly.
# Usage: ./bootstrap/run.sh [--tags homebrew,dotfiles,shell,secrets]

set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Ensure Homebrew exists and is on PATH
if ! command -v brew &>/dev/null; then
  echo "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Add brew to PATH for this session (all three install locations)
if [ -f /opt/homebrew/bin/brew ]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif [ -f /usr/local/bin/brew ]; then
  eval "$(/usr/local/bin/brew shellenv)"
elif [ -f /home/linuxbrew/.linuxbrew/bin/brew ]; then
  eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
fi

# Ensure Ansible exists
if ! command -v ansible-playbook &>/dev/null; then
  echo "Installing Ansible..."
  brew install ansible
fi

cd "$DOTFILES_DIR/bootstrap"
ansible-playbook playbook.yml \
  -e "dotfiles_dir=$DOTFILES_DIR" \
  "$@"
```

**Task 1.2.2**: Change shebang from `#!/usr/bin/env zsh` to `#!/usr/bin/env bash` for Linux compatibility

---

### Epic 2: `bootstrap/playbook.yml` Revamp

**Goal**: Update the Ansible playbook to add new roles, WSL2 detection, and proper platform variables.

---

#### Story 2.1: Add WSL2 detection and global vars

**File**: `bootstrap/playbook.yml` (modify existing)

**Acceptance criteria**:
- `is_wsl` fact is available to all roles
- WSL2 detection runs before any role
- `brew_prefix` variable set correctly for all platforms

**Tasks**:

**Task 2.1.1**: Rewrite `bootstrap/playbook.yml` to add pre_tasks, WSL2 detection, brew_prefix var, and updated roles list
```yaml
---
- name: Bootstrap development environment
  hosts: localhost
  connection: local
  gather_facts: true
  vars:
    dotfiles_dir: "{{ ansible_env.HOME }}/dotfiles"

  pre_tasks:
    - name: Detect WSL2
      shell: grep -qi microsoft /proc/version 2>/dev/null && echo yes || echo no
      register: wsl2_check
      changed_when: false

    - name: Set is_wsl fact
      set_fact:
        is_wsl: "{{ wsl2_check.stdout == 'yes' }}"

    - name: Set brew_prefix fact
      set_fact:
        brew_prefix: >-
          {{ '/opt/homebrew' if ansible_os_family == 'Darwin' and ansible_architecture == 'arm64'
             else '/usr/local' if ansible_os_family == 'Darwin'
             else '/home/linuxbrew/.linuxbrew' }}

  roles:
    - homebrew
    - dotfiles
    - shell
    - asdf
    - nix
    - secrets
    - fonts
    - claude
```

---

### Epic 3: `homebrew` Role Fix

**Goal**: Make the homebrew role cross-platform (macOS Apple Silicon, Intel, Linux) with correct Brewfile selection.

---

#### Story 3.1: Fix Homebrew install check and Linux support

**File**: `bootstrap/roles/homebrew/tasks/main.yml` (rewrite)

**Acceptance criteria**:
- Role detects correct brew binary path on all platforms
- Homebrew installs on Linux using linuxbrew path
- Linux prerequisites (build-essential / base-devel) are installed before Homebrew attempt
- No hardcoded `/opt/homebrew` in task conditions
- `brew update` runs after install

**Tasks**:

**Task 3.1.1**: Replace static stat check with dynamic `brew_prefix`-based check and add Linux prerequisites
```yaml
---
- name: Install Linux prerequisites (Debian/Ubuntu)
  apt:
    name:
      - build-essential
      - curl
      - file
      - git
    state: present
    update_cache: true
  become: true
  when: ansible_os_family == "Debian"
  tags: [homebrew]

- name: Install Linux prerequisites (Arch/Manjaro)
  pacman:
    name:
      - base-devel
      - curl
      - file
      - git
    state: present
  become: true
  when: ansible_os_family == "Archlinux"
  tags: [homebrew]

- name: Check Homebrew is installed
  stat:
    path: "{{ brew_prefix }}/bin/brew"
  register: brew_bin
  tags: [homebrew]

- name: Install Homebrew
  shell: |
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  when: not brew_bin.stat.exists
  tags: [homebrew]

- name: Update Homebrew
  command: "{{ brew_prefix }}/bin/brew update"
  changed_when: false
  environment:
    PATH: "{{ brew_prefix }}/bin:{{ ansible_env.PATH }}"
  tags: [homebrew]
```

---

#### Story 3.2: Brewfile selection and `Brewfile.linux` creation

**File**: `bootstrap/roles/homebrew/tasks/main.yml` (add tasks)
**File**: `Brewfile.linux` (new, repo root)

**Acceptance criteria**:
- macOS uses `Brewfile`
- Linux uses `Brewfile.linux` (CLI tools only, no casks)
- `Brewfile.linux` contains a curated, manually-maintained CLI subset
- `brew bundle install` runs with `--no-lock` to avoid lock file issues in CI

**Tasks**:

**Task 3.2.1**: Add Brewfile selection and `brew bundle` task
```yaml
- name: Set brewfile path
  set_fact:
    brewfile_path: "{{ dotfiles_dir }}/{{ 'Brewfile' if ansible_os_family == 'Darwin' else 'Brewfile.linux' }}"
  tags: [homebrew]

- name: Install packages from Brewfile
  command: >
    {{ brew_prefix }}/bin/brew bundle install
    --file={{ brewfile_path }}
    --no-lock
  register: brew_bundle
  changed_when: "'Installing' in brew_bundle.stdout or 'Upgrading' in brew_bundle.stdout"
  environment:
    PATH: "{{ brew_prefix }}/bin:{{ ansible_env.PATH }}"
  tags: [homebrew]
```

**Task 3.2.2**: Create `Brewfile.linux` — curated CLI subset (no casks, no macOS-only tools)

Create `/Users/tylerstapler/dotfiles/Brewfile.linux` with content:
```ruby
# Brewfile.linux — CLI tools subset of Brewfile.
# Casks and macOS-specific tools are excluded.
# Maintained manually; update when adding new CLI tools to Brewfile.

brew "ansible"
brew "asdf"          # required by asdf role
brew "bat"
brew "coreutils"
brew "curl"
brew "fd"
brew "fzf"
brew "git"
brew "git-lfs"
brew "gh"
brew "golang"
brew "htop"
brew "jq"
brew "neovim"
brew "node"
brew "python@3.12"
brew "ripgrep"
brew "shellcheck"
brew "starship"
brew "tmux"
brew "tree"
brew "unzip"         # required by fonts role (unarchive module)
brew "uv"
brew "wget"
brew "zsh"
```

Note: Private taps (`fanatics-gaming/tap`, `tstapler/stelekit`) are intentionally excluded from `Brewfile.linux` because they require SSH key setup which happens after bootstrap. The main `Brewfile` will fail on these taps on fresh machines — document this as a known limitation. Consider adding a `HOMEBREW_NO_AUTO_UPDATE=1` prefix and `|| true` wrapper for tap lines in the main Brewfile as a separate hardening task.

---

### Epic 4: `dotfiles` Role Rewrite

**Goal**: Replace the broken `go build` approach with `uv tool install cfgcaddy` from PyPI.

---

#### Story 4.1: Rewrite dotfiles role for uv + cfgcaddy

**File**: `bootstrap/roles/dotfiles/tasks/main.yml` (full rewrite)

**Acceptance criteria**:
- Old `go build` tasks are completely removed
- `uv` is installed via Homebrew (already in Brewfile)
- `cfgcaddy` is installed from PyPI via `uv tool install cfgcaddy`
- `cfgcaddy init` is run to symlink `.cfgcaddy.yml` (idempotent)
- `cfgcaddy link --no-interactive` creates symlinks
- `changed_when` captures when links are actually created
- All tasks include full PATH environment variable

**Tasks**:

**Task 4.1.1**: Rewrite `bootstrap/roles/dotfiles/tasks/main.yml`
```yaml
---
- name: Check if uv is available
  command: which uv
  register: uv_check
  failed_when: false
  changed_when: false
  environment:
    PATH: "{{ brew_prefix }}/bin:{{ ansible_env.HOME }}/.local/bin:{{ ansible_env.PATH }}"
  tags: [dotfiles]

- name: Install uv via Homebrew if not found
  command: "{{ brew_prefix }}/bin/brew install uv"
  when: uv_check.rc != 0
  environment:
    PATH: "{{ brew_prefix }}/bin:{{ ansible_env.PATH }}"
  tags: [dotfiles]

- name: Install cfgcaddy via uv tool install
  command: "{{ brew_prefix }}/bin/uv tool install cfgcaddy"
  register: cfgcaddy_install
  changed_when: "'Installed' in cfgcaddy_install.stdout"
  # uv outputs "cfgcaddy is already installed" to stdout (not stderr) when already present
  failed_when: cfgcaddy_install.rc != 0 and 'already installed' not in cfgcaddy_install.stdout
  environment:
    PATH: "{{ ansible_env.HOME }}/.local/bin:{{ brew_prefix }}/bin:{{ ansible_env.HOME }}/.asdf/bin:{{ ansible_env.HOME }}/.asdf/shims:/opt/homebrew/bin:/home/linuxbrew/.linuxbrew/bin:{{ ansible_env.PATH }}"
  tags: [dotfiles]

- name: Check if ~/.cfgcaddy.yml exists (init already done)
  stat:
    path: "{{ ansible_env.HOME }}/.cfgcaddy.yml"
  register: cfgcaddy_yml
  tags: [dotfiles]

- name: Init cfgcaddy (symlinks .cfgcaddy.yml to ~/.cfgcaddy.yml)
  command: "cfgcaddy init {{ dotfiles_dir }} {{ ansible_env.HOME }}"
  when: not cfgcaddy_yml.stat.exists
  environment:
    PATH: "{{ ansible_env.HOME }}/.local/bin:{{ brew_prefix }}/bin:{{ ansible_env.HOME }}/.asdf/bin:{{ ansible_env.HOME }}/.asdf/shims:/opt/homebrew/bin:/home/linuxbrew/.linuxbrew/bin:{{ ansible_env.PATH }}"
  tags: [dotfiles]

- name: Link dotfiles via cfgcaddy
  command: cfgcaddy link --no-interactive
  register: cfgcaddy_result
  changed_when: "'Linked' in cfgcaddy_result.stdout"
  environment:
    PATH: "{{ ansible_env.HOME }}/.local/bin:{{ brew_prefix }}/bin:{{ ansible_env.HOME }}/.asdf/bin:{{ ansible_env.HOME }}/.asdf/shims:/opt/homebrew/bin:/home/linuxbrew/.linuxbrew/bin:{{ ansible_env.PATH }}"
  tags: [dotfiles]
```

---

### Epic 5: `shell` Role Fix + New `asdf` Role

**Goal**: Fix broken asdf condition in the shell role and extract asdf management into a dedicated, idempotent role.

---

#### Story 5.1: Fix `shell` role — remove broken asdf task

**File**: `bootstrap/roles/shell/tasks/main.yml` (modify)

**Acceptance criteria**:
- Broken `fileglob` asdf task is removed
- `set zsh as default shell` task handles WSL2 (skip `become:true` service tasks on WSL2 where systemd may not be available — chsh still works)
- `zplug` clone is still idempotent
- `become: true` on the `user:` task is preserved (still required for chsh)

**Tasks**:

**Task 5.1.1**: Update `bootstrap/roles/shell/tasks/main.yml` — remove asdf task, keep zsh + zplug
```yaml
---
- name: Set zsh as default shell
  user:
    name: "{{ ansible_env.USER }}"
    shell: /bin/zsh
  become: true
  tags: [shell]

- name: Clone zplug if missing
  git:
    repo: https://github.com/tstapler/zplug
    dest: "{{ ansible_env.HOME }}/.zplug"
    update: false
  tags: [shell]
```

Note on become/sudo and WSL2: The `user:` module with `become: true` requires sudo. On WSL2 with sudo 1.9.16+, this may hang. Document the workaround: run `sudo -v` before executing the playbook in WSL2. The fonts and service-level tasks already have `when: not is_wsl` guards; the shell `user:` task cannot be skipped entirely on WSL2 (default shell change is still useful). Use `ignore_errors: true` on WSL2 or document manual step.

---

#### Story 5.2: Create new `asdf` role

**File**: `bootstrap/roles/asdf/tasks/main.yml` (new)

**Acceptance criteria**:
- Reads plugin names from `.tool-versions` dynamically
- Adds plugins idempotently (ignores "already added" error)
- Runs `asdf install` when `.tool-versions` exists
- All tasks source `~/.asdf/asdf.sh` via shell + explicit bash executable
- Role has `asdf` tag

**Tasks**:

**Task 5.2.1**: Create `bootstrap/roles/asdf/` directory structure
```
bootstrap/roles/asdf/
  tasks/
    main.yml
```

**Task 5.2.2**: Create `bootstrap/roles/asdf/tasks/main.yml`
```yaml
---
- name: Check .tool-versions exists
  stat:
    path: "{{ dotfiles_dir }}/.tool-versions"
  register: tool_versions_file
  tags: [asdf]

- name: Read tool names from .tool-versions
  shell: "awk '{print $1}' {{ dotfiles_dir }}/.tool-versions"
  register: asdf_tool_names
  changed_when: false
  when: tool_versions_file.stat.exists
  tags: [asdf]

- name: Add asdf plugins
  shell: |
    . {{ ansible_env.HOME }}/.asdf/asdf.sh
    asdf plugin add {{ item }}
  args:
    executable: /bin/bash
  register: plugin_result
  failed_when: plugin_result.rc != 0 and 'already added' not in plugin_result.stderr
  changed_when: plugin_result.rc == 0
  loop: "{{ asdf_tool_names.stdout_lines | default([]) }}"
  when: tool_versions_file.stat.exists
  environment:
    PATH: "{{ ansible_env.HOME }}/.asdf/bin:{{ ansible_env.HOME }}/.asdf/shims:{{ brew_prefix }}/bin:{{ ansible_env.PATH }}"
  tags: [asdf]

- name: Install asdf tool versions
  shell: |
    . {{ ansible_env.HOME }}/.asdf/asdf.sh
    asdf install
  args:
    chdir: "{{ dotfiles_dir }}"
    executable: /bin/bash
  when: tool_versions_file.stat.exists
  environment:
    PATH: "{{ ansible_env.HOME }}/.asdf/bin:{{ ansible_env.HOME }}/.asdf/shims:{{ brew_prefix }}/bin:{{ ansible_env.PATH }}"
  tags: [asdf]
```

Note: asdf itself must be installed (via Brewfile) before this role runs. The `homebrew` role runs first and `brew bundle` installs `asdf` from the Brewfile. Verify `asdf` is in both `Brewfile` and `Brewfile.linux`.

**CRITICAL PATH NOTE (asdf Homebrew install path)**: When asdf is installed via Homebrew, its init script is at `{{ brew_prefix }}/opt/asdf/libexec/asdf.sh`, NOT at `~/.asdf/asdf.sh`. The shell tasks in this role source `~/.asdf/asdf.sh` as a fallback (used when asdf was installed directly). Update all asdf shell tasks to try the Homebrew path first:

```yaml
- name: Add asdf plugins
  shell: |
    ASDF_SH="{{ brew_prefix }}/opt/asdf/libexec/asdf.sh"
    [ -f "$ASDF_SH" ] || ASDF_SH="{{ ansible_env.HOME }}/.asdf/asdf.sh"
    . "$ASDF_SH"
    asdf plugin add {{ item }}
  args:
    executable: /bin/bash
  ...
```

Apply this pattern to both the "Add asdf plugins" and "Install asdf tool versions" tasks.

---

### Epic 6: New `fonts` Role

**Goal**: Install Nerd Fonts per platform. Skip on WSL2.

---

#### Story 6.1: Create `fonts` role

**File**: `bootstrap/roles/fonts/tasks/main.yml` (new)

**Acceptance criteria**:
- On macOS: installs `font-meslo-lg-nerd-font` cask (or verifies it is in Brewfile casks)
- On Linux (non-WSL2): downloads Meslo Nerd Font zip from GitHub releases, installs to `~/.local/share/fonts/`, runs `fc-cache -fv`
- On WSL2: skips entirely with info message
- Role is tagged `fonts`

**Tasks**:

**Task 6.1.1**: Create `bootstrap/roles/fonts/` directory structure
```
bootstrap/roles/fonts/
  tasks/
    main.yml
```

**Task 6.1.2**: Create `bootstrap/roles/fonts/tasks/main.yml`
```yaml
---
- name: Skip fonts on WSL2
  debug:
    msg: "Skipping fonts role on WSL2 — install Nerd Fonts on Windows side manually."
  when: is_wsl | default(false)
  tags: [fonts]

- name: Install Meslo Nerd Font (macOS via Homebrew cask)
  # Note: font-meslo-lg-nerd-font should also be added to the main Brewfile cask section
  # to avoid managing it in two places. This task is a belt-and-suspenders install.
  community.general.homebrew_cask:
    name: font-meslo-lg-nerd-font
    state: present
  when: ansible_os_family == "Darwin"
  environment:
    PATH: "{{ brew_prefix }}/bin:{{ ansible_env.PATH }}"
  tags: [fonts]

- name: Ensure fonts directory exists (Linux)
  file:
    path: "{{ ansible_env.HOME }}/.local/share/fonts"
    state: directory
    mode: '0755'
  when: ansible_os_family != "Darwin" and not (is_wsl | default(false))
  tags: [fonts]

- name: Check if Meslo Nerd Font is already installed (Linux)
  find:
    paths: "{{ ansible_env.HOME }}/.local/share/fonts/"
    patterns: "MesloLG*"
  register: meslo_font_files
  when: ansible_os_family != "Darwin" and not (is_wsl | default(false))
  tags: [fonts]

- name: Download Meslo Nerd Font zip (Linux)
  get_url:
    url: "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/Meslo.zip"
    dest: "/tmp/Meslo.zip"
    force: false
    mode: '0644'
  when: ansible_os_family != "Darwin" and not (is_wsl | default(false)) and meslo_font_files.matched == 0
  tags: [fonts]

- name: Unzip Meslo Nerd Font (Linux)
  unarchive:
    src: "/tmp/Meslo.zip"
    dest: "{{ ansible_env.HOME }}/.local/share/fonts/"
    remote_src: true
  when: ansible_os_family != "Darwin" and not (is_wsl | default(false)) and meslo_font_files.matched == 0
  tags: [fonts]

- name: Refresh font cache (Linux)
  command: fc-cache -fv
  changed_when: false
  when: ansible_os_family != "Darwin" and not (is_wsl | default(false))
  tags: [fonts]
```

---

### Epic 7: New `claude` Role

**Goal**: Install Claude Code CLI via npm and verify it works.

---

#### Story 7.1: Create `claude` role

**File**: `bootstrap/roles/claude/tasks/main.yml` (new)

**Acceptance criteria**:
- `node` and `npm` are available (installed via Brewfile)
- `@anthropic-ai/claude-code` is installed globally via `npm install -g`
- Install is idempotent (re-running does not fail)
- `claude --version` returns a version string
- `.claude/` config files are already handled by cfgcaddy (already in `.cfgcaddy.yml`)
- Role is tagged `claude`

**Tasks**:

**Task 7.1.1**: Create `bootstrap/roles/claude/` directory structure
```
bootstrap/roles/claude/
  tasks/
    main.yml
```

**Task 7.1.2**: Create `bootstrap/roles/claude/tasks/main.yml`
```yaml
---
- name: Check if claude CLI is installed
  command: claude --version
  register: claude_check
  failed_when: false
  changed_when: false
  environment:
    PATH: "{{ brew_prefix }}/bin:{{ ansible_env.HOME }}/.local/bin:{{ ansible_env.PATH }}"
  tags: [claude]

- name: Install Claude Code CLI via npm
  command: npm install -g @anthropic-ai/claude-code
  when: claude_check.rc != 0
  environment:
    PATH: "{{ brew_prefix }}/bin:{{ ansible_env.HOME }}/.local/bin:{{ ansible_env.PATH }}"
  tags: [claude]

- name: Verify Claude Code CLI installed
  command: claude --version
  register: claude_version
  changed_when: false
  environment:
    PATH: "{{ brew_prefix }}/bin:{{ ansible_env.HOME }}/.local/bin:{{ ansible_env.PATH }}"
  tags: [claude]

- name: Show Claude Code version
  debug:
    msg: "Claude Code installed: {{ claude_version.stdout }}"
  tags: [claude]
```

---

### Epic 9: `secrets` Role Audit and Rewrite

**Goal**: Ensure the secrets role matches requirements — 1Password CLI check, session validation, dry-run injection test. The role could not be read due to permissions during research; this epic covers writing it from scratch per the requirements spec.

---

#### Story 9.1: Write secrets role per requirements

**File**: `bootstrap/roles/secrets/tasks/main.yml` (rewrite — current file may be permission-restricted)

**Acceptance criteria**:
- If `op` CLI is not installed: fail with clear human-readable message explaining how to install it
- If `op account list` returns no accounts: print sign-in instructions and exit gracefully (do not hard fail — secrets is best-effort on fresh machine)
- If session is active: run `op inject --dry-run` against a test template to verify injection works
- Role is tagged `secrets`

**Tasks**:

**Task 9.1.1**: Create `bootstrap/roles/secrets/tasks/main.yml`
```yaml
---
- name: Check 1Password CLI is installed
  command: which op
  register: op_check
  failed_when: false
  changed_when: false
  tags: [secrets]

- name: Fail with instructions if op CLI is not installed
  fail:
    msg: |
      1Password CLI (op) is required for secrets management but was not found on PATH.
      Install it: brew install --cask 1password-cli
      Then re-run: ansible-playbook bootstrap/playbook.yml --tags secrets
  when: op_check.rc != 0
  tags: [secrets]

- name: Check for active 1Password session
  command: op account list
  register: op_accounts
  failed_when: false
  changed_when: false
  environment:
    PATH: "{{ brew_prefix }}/bin:{{ ansible_env.PATH }}"
  tags: [secrets]

- name: Print sign-in instructions if no active session
  debug:
    msg: |
      No active 1Password session found. Sign in with:
        eval $(op signin)
      Then re-run: ansible-playbook bootstrap/playbook.yml --tags secrets
      Skipping dry-run secret injection test.
  when: op_accounts.rc != 0 or op_accounts.stdout | length == 0
  tags: [secrets]

- name: Test secret injection via op inject dry-run
  shell: |
    echo "{{ "{{" }} op://Personal/test-placeholder/password {{ "}}" }}" | op inject --dry-run
  register: op_inject_test
  failed_when: false
  changed_when: false
  when: op_accounts.rc == 0 and op_accounts.stdout | length > 0
  environment:
    PATH: "{{ brew_prefix }}/bin:{{ ansible_env.PATH }}"
  tags: [secrets]

- name: Report secret injection test result
  debug:
    msg: "op inject dry-run: {{ 'PASS' if op_inject_test.rc == 0 else 'FAIL — check op session' }}"
  when: op_inject_test is defined
  tags: [secrets]
```

Note: The `op inject --dry-run` test uses a placeholder vault path. In practice, this test verifies the `op` binary can connect to the vault and perform template injection. The test is non-destructive. If the placeholder path doesn't exist in 1Password, `op inject` will return non-zero — `failed_when: false` prevents this from aborting the playbook.

---

### Epic 8: Cleanup and Retirement

**Goal**: Remove dead files, add deprecation notice to the old bootstrap script, delete `bootstrap.yaml`.

---

#### Story 8.1: Deprecate `bootstrap-dotfiles.sh`

**File**: `stapler-scripts/bootstrap-dotfiles.sh` (modify)

**Acceptance criteria**:
- File is NOT deleted (kept for historical reference per requirements)
- A deprecation notice is added at the top of the file
- The notice clearly points to `install.sh`

**Tasks**:

**Task 8.1.1**: Add deprecation header to `stapler-scripts/bootstrap-dotfiles.sh`
```bash
# DEPRECATED: This script is no longer the canonical bootstrap entry point.
# Use instead: curl -fsSL https://raw.githubusercontent.com/tstapler/dotfiles/master/install.sh | bash
# Or from the repo root: ./install.sh
# This file is retained for historical reference only.
```

---

#### Story 8.2: Delete dead files

**Files to delete**:
- `stapler-scripts/bootstrap.yaml` — references a `bootstrap` role that does not exist; dead file
- `stapler-scripts/install-scripts/osx-ansible-install.sh` — superseded by Homebrew-based install

**Acceptance criteria**:
- Files are removed via `git rm`
- Deletion is committed with a clear message

**Tasks**:

**Task 8.2.1**: Delete dead bootstrap files
```bash
git rm stapler-scripts/bootstrap.yaml
git rm stapler-scripts/install-scripts/osx-ansible-install.sh
git commit -m "chore: remove dead bootstrap files (bootstrap.yaml, osx-ansible-install.sh)"
```

---

## Cross-Cutting Concerns

### PATH Environment Variable

Every Ansible task that invokes `uv`, `cfgcaddy`, `asdf`, or any Homebrew-installed binary in a `command:` or `shell:` module must include:

```yaml
environment:
  PATH: "{{ ansible_env.HOME }}/.local/bin:{{ ansible_env.HOME }}/.asdf/bin:{{ ansible_env.HOME }}/.asdf/shims:{{ brew_prefix }}/bin:/opt/homebrew/bin:/home/linuxbrew/.linuxbrew/bin:{{ ansible_env.PATH }}"
```

The `brew_prefix` variable is set in the `playbook.yml` pre_tasks and must be computed before any role runs. Both absolute paths and the variable are included as belt-and-suspenders for cases where the variable is not yet propagated.

### Role Ordering Dependencies

Roles must run in this order (as reflected in `playbook.yml`):
1. `homebrew` — installs all brew packages including `asdf`, `node`, `uv`
2. `dotfiles` — installs cfgcaddy, links config files (including `.claude/`)
3. `shell` — sets zsh, clones zplug
4. `asdf` — installs asdf plugins and tool versions (depends on `asdf` binary from homebrew)
5. `nix` — installs Nix (independent, but after dotfiles)
6. `secrets` — validates 1Password (independent)
7. `fonts` — installs Nerd Fonts (after dotfiles for platform facts)
8. `claude` — installs Claude CLI (depends on `node` from homebrew, `.claude/` from dotfiles role)

### Tag Strategy

Each role uses a single lowercase tag matching its role name. Individual roles can be re-run with:
```bash
ansible-playbook bootstrap/playbook.yml -e "dotfiles_dir=$HOME/dotfiles" --tags <role>
```

Valid tags: `homebrew`, `dotfiles`, `shell`, `asdf`, `nix`, `secrets`, `fonts`, `claude`

### WSL2 Caveats

- `is_wsl` fact is set in `pre_tasks` before any role runs
- All roles that must skip on WSL2 use `when: not (is_wsl | default(false))`
- The `fonts` role skips entirely on WSL2
- `become: true` tasks in the `shell` role may require `sudo -v` pre-run on WSL2 with sudo 1.9.16+
- Document: On WSL2, install fonts manually on the Windows side

### Submodule SSH vs HTTPS

If `git submodule update --init --recursive` fails on a fresh machine due to SSH URLs, add to `~/.gitconfig` (or include in install.sh):
```
[url "https://github.com/"]
  insteadOf = git@github.com:
```
This is a known issue with private submodules on fresh machines before SSH keys are configured.

### Private Tap Limitation

`Brewfile` contains private taps that require SSH key setup:
- `tap "fanatics-gaming/tap", "git@github-personal:..."`
- `tap "tstapler/stelekit", "git@github-personal:..."`

These will fail on a truly fresh machine before SSH is configured. `Brewfile.linux` intentionally excludes these. The main `Brewfile` run should be tolerant of tap failures. A future improvement: use `--no-upgrade` and wrap tap lines in `|| true` in the homebrew role, or split `Brewfile` into a `Brewfile.core` (public taps only) and `Brewfile.work` (private taps).

---

## File Change Summary

| File | Action | Epic |
|---|---|---|
| `install.sh` | Create | Epic 1 |
| `bootstrap/run.sh` | Modify | Epic 1 |
| `bootstrap/playbook.yml` | Rewrite | Epic 2 |
| `bootstrap/roles/homebrew/tasks/main.yml` | Rewrite | Epic 3 |
| `Brewfile.linux` | Create | Epic 3 |
| `bootstrap/roles/dotfiles/tasks/main.yml` | Rewrite | Epic 4 |
| `bootstrap/roles/shell/tasks/main.yml` | Modify | Epic 5 |
| `bootstrap/roles/asdf/tasks/main.yml` | Create | Epic 5 |
| `bootstrap/roles/fonts/tasks/main.yml` | Create | Epic 6 |
| `bootstrap/roles/claude/tasks/main.yml` | Create | Epic 7 |
| `stapler-scripts/bootstrap-dotfiles.sh` | Modify (deprecate) | Epic 8 |
| `stapler-scripts/bootstrap.yaml` | Delete | Epic 8 |
| `stapler-scripts/install-scripts/osx-ansible-install.sh` | Delete | Epic 8 |
| `bootstrap/roles/secrets/tasks/main.yml` | Rewrite | Epic 9 |

---

## Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Private Brewfile taps fail on fresh machine | High | `Brewfile.linux` excludes them; document limitation; add `--no-lock` flag |
| WSL2 `become: true` hangs with sudo 1.9.16+ | Medium | Document `sudo -v` pre-run; `ignore_errors: true` on shell user task |
| cfgcaddy PyPI version mismatch | Low | `uv tool install cfgcaddy` always installs latest; user owns the package |
| asdf plugin install fails for unknown plugins | Medium | `failed_when` ignores "already added"; plugins must exist in asdf registry |
| npm global install permissions | Low | npm installed via Homebrew has correct user-owned prefix |
| Submodule SSH URLs on fresh machine | Medium | Documented workaround with gitconfig url rewrite |
| `unzip` not available on minimal Linux | Low | `unarchive` Ansible module handles this; add `unzip` to `Brewfile.linux` prerequisites |

---

## Acceptance Criteria (System Level)

1. `curl -fsSL https://raw.githubusercontent.com/tstapler/dotfiles/master/install.sh | bash` runs to completion on a fresh macOS ARM64 machine
2. Running `install.sh` twice produces no errors and no unneeded changes (idempotent)
3. Each Ansible role can be run independently via `ansible-playbook bootstrap/playbook.yml --tags <role>`
4. cfgcaddy symlinks are created correctly after dotfiles role runs (`~/.cfgcaddy.yml` exists and symlinks are present)
5. `asdf install` actually executes when `.tool-versions` exists in `dotfiles_dir`
6. `claude --version` returns a version after the claude role runs
7. Linux (Ubuntu) playbook run completes without macOS-specific failures
8. WSL2 run completes with fonts role skipped and no systemd-related failures
