# Features Research: Current Dotfiles Repo Audit

## Bootstrap System Overview

There are **two parallel, diverged bootstrap systems**:

1. `bootstrap/` — Ansible-only, macOS-focused, newer structure
2. `stapler-scripts/bootstrap-dotfiles.sh` — Shell script entry point, uses pyenv, calls old `bootstrap.yaml`

Neither is the canonical entry point and they do not share state.

---

## bootstrap/ System

### Files
- `bootstrap/ansible.cfg` — Sets inventory=localhost, connection=local, roles_path=roles, smart gathering
- `bootstrap/playbook.yml` — Single play: localhost, roles: homebrew, dotfiles, shell, nix, secrets
- `bootstrap/run.sh` — Shell wrapper: installs Homebrew if absent, installs ansible via brew, runs playbook

### Roles

#### homebrew (WORKS, macOS only)
- Checks for brew at `/opt/homebrew/bin/brew` — **hardcoded Apple Silicon path, breaks on Intel/Linux**
- Installs Homebrew via curl|bash if absent
- Runs `brew update`
- Runs `brew bundle install --file={{ dotfiles_dir }}/Brewfile`
- No platform guards; will fail on Linux

#### dotfiles (BROKEN)
- Checks for `{{ dotfiles_dir }}/cfgcaddy/cfgcaddy` — a compiled Go binary
- Runs `go build -o cfgcaddy .` — **cfgcaddy is NOT a Go package; it is a Python package on PyPI**
- The binary would never be built; the `go build` step will fail (no `*.go` files in `cfgcaddy/`)
- Then calls `{{ dotfiles_dir }}/cfgcaddy/cfgcaddy link --config {{ dotfiles_dir }}/.cfgcaddy.yml` — path will never exist after the failed build
- **Root cause**: Ansible role was written assuming cfgcaddy was a Go binary; it was rewritten as Python

#### shell (BROKEN — asdf never runs)
- Sets zsh as default shell via `user:` module (requires become/sudo)
- Clones `https://github.com/tstapler/zplug` to `~/.zplug` (idempotent with `update: false`)
- Runs `asdf install` when `'.tool-versions' in lookup('fileglob', dotfiles_dir + '/.tool-versions')`
  - **BUG**: `lookup('fileglob', ...)` returns a list of paths. The `in` check tests if the string `'.tool-versions'` is literally in that list — it will never match. `asdf install` never executes.
  - `ignore_errors: true` silently masks this bug

#### nix (WORKS)
- Checks `/nix/var/nix/profiles/default/bin/nix`
- Installs via Determinate Systems: `curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install --no-confirm`
- Sources nix daemon and verifies version
- Well-structured, idempotent

#### secrets (unreadable — permission denied)
- Role exists but could not be read due to file permissions

---

## stapler-scripts/ System

### bootstrap-dotfiles.sh (OUTDATED)
- Uses `pyenv` to install Python 3.9.12 — slow, outdated Python version
- Uses `pyenv exec pipx install ansible` — installs Ansible into pyenv venv (not system PATH)
- Clones dotfiles repo to `$HOME/dotfiles` (with idempotency check)
- Runs `git submodule update --init --recursive`
- Runs `pyenv exec pipx install cfgcaddy` — **cfgcaddy is correctly installed from PyPI here**
- Runs `cfgcaddy init "$CLONE_DIR" "$HOME"` then `cfgcaddy link` — correct CLI usage
- Calls `ansible-playbook -vvv -K bootstrap.yaml`

### bootstrap.yaml (DEAD FILE)
```yaml
- hosts: localhost
  roles:
    - bootstrap
```
References a `bootstrap` role that **does not exist**. This file cannot run successfully.

### ansible.cfg (stapler-scripts/)
- Separate ansible.cfg from `bootstrap/ansible.cfg` — different config contexts

---

## cfgcaddy CLI Interface

cfgcaddy is a Python CLI tool (Click-based) available on PyPI as `cfgcaddy`. It is NOT a Go binary.

### Commands
```
cfgcaddy [OPTIONS] COMMAND

Options:
  -d, --debug    Enable debugging output
  -q, --quiet    Silence cfgcaddy

Commands:
  init  SRC_DIRECTORY DEST_DIRECTORY [-c CONFIG]
        Create or import a caddy config.
        - If ~/.cfgcaddy.yml already exists: error
        - If .cfgcaddy.yml found at src_directory: symlinks it to ~/.cfgcaddy.yml
        - Otherwise: runs interactive questionary prompt for linker_src and linker_dest,
          then creates ~/.cfgcaddy.yml

  link  [-c CONFIG] [-y]
        Link your config files using the config at ~/.cfgcaddy.yml (or -c path).
        -y / --no-interactive skips confirmation prompts.
        Reads .cfgcaddy.yml, creates symlinks from src to dest.
        Outputs "Linked" in stdout when links are created (used by Ansible changed_when).
```

### .cfgcaddy.yml Structure
```yaml
preferences:
  linker_src: $HOME/dotfiles
  linker_dest: $HOME
links:
  - src: .vimrc
    dest: .config/nvim/init.vim
    os: "Linux Darwin"
  - src: .shell
    os: "Linux Darwin"
  - src: stapler-scripts/*
    dest: bin/scripts
    os: "Linux Darwin"
ignore:
  - "*.yml"
  - "*.git"
```
- `os:` field filters links by platform ("Linux", "Darwin", "Windows")
- `src:` supports glob patterns (`bin/scripts/*`, `stapler-scripts/*`)
- `dest:` optional; defaults to same relative path
- The config file lives at `~/dotfiles/.cfgcaddy.yml` and gets symlinked to `~/.cfgcaddy.yml` by `cfgcaddy init`

### Correct Ansible task for cfgcaddy
```yaml
- name: Install cfgcaddy via uv
  command: uv tool install cfgcaddy
  environment:
    PATH: "{{ ansible_env.HOME }}/.local/bin:{{ ansible_env.PATH }}"

- name: Init cfgcaddy config
  command: cfgcaddy init {{ dotfiles_dir }} {{ ansible_env.HOME }}
  environment:
    PATH: "{{ ansible_env.HOME }}/.local/bin:{{ ansible_env.PATH }}"

- name: Link dotfiles via cfgcaddy
  command: cfgcaddy link --no-interactive
  environment:
    PATH: "{{ ansible_env.HOME }}/.local/bin:{{ ansible_env.PATH }}"
  register: cfgcaddy_result
  changed_when: "'Linked' in cfgcaddy_result.stdout"
```

---

## .tool-versions
```
nodejs 24.13.1
clojure 1.10.1.739
lein 2.9.5
java openjdk-21
golang 1.22.3
terraform 1.5.0
python 3.11.4
nim 2.0.8
```
8 asdf-managed tools. This file exists at `~/dotfiles/.tool-versions` — the condition bug in the shell role means none of these are ever installed via Ansible.

## Brewfile
- Starts with ~30 `tap` entries including private taps (`git@github-personal:...`) that will fail on fresh machines
- Includes `brew "ansible"` — so Ansible can be installed via Brewfile
- Large (13.6K) — likely contains many work-specific tools; a Brewfile.linux should contain CLI-only subset
- Includes casks (apps) which are macOS-only; Linux Brewfile must exclude all casks

## Summary of What Works / What Is Broken

| Component | Status | Issue |
|---|---|---|
| `bootstrap/roles/homebrew` | Partially works | Hardcoded `/opt/homebrew` — breaks Intel + Linux |
| `bootstrap/roles/dotfiles` | Broken | `go build` on Python package |
| `bootstrap/roles/shell` (zsh/zplug) | Works | — |
| `bootstrap/roles/shell` (asdf) | Broken | fileglob condition never true |
| `bootstrap/roles/nix` | Works | Well-structured |
| `bootstrap/run.sh` | Works (macOS only) | No Linux support |
| `stapler-scripts/bootstrap-dotfiles.sh` | Outdated | pyenv + Python 3.9.12 |
| `stapler-scripts/bootstrap.yaml` | Dead | References nonexistent role |
| cfgcaddy install (old scripts) | Uses pipx correctly | But via pyenv (slow) |
| cfgcaddy install (Ansible role) | Broken | Uses go build |
