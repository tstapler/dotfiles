# Dotfiles Bootstrap Revamp — Requirements

## Goal
Consolidate two diverged bootstrap systems into a single Ansible-driven workflow reachable via a one-liner curl install command. Support macOS, Ubuntu/Debian, Arch/Manjaro, and WSL2 from one codebase.

## Current State (problems to fix)
- `bootstrap/roles/dotfiles/tasks/main.yml` tries `go build` on cfgcaddy, which is a Python package on PyPI
- `stapler-scripts/bootstrap-dotfiles.sh` uses pyenv just to install Ansible (slow, outdated)
- No `install.sh` entry point — user must manually clone first before running bootstrap
- `stapler-scripts/bootstrap.yaml` references a nonexistent `bootstrap` role (dead file)
- `bootstrap/roles/shell/tasks/main.yml` asdf step uses a broken `fileglob` lookup condition — `asdf install` never runs
- Two parallel bootstrap systems have diverged with no clear canonical one

## Entry Point
- Single `install.sh` at repo root
- Reachable via: `curl -fsSL https://raw.githubusercontent.com/tstapler/dotfiles/master/install.sh | bash`
- GitHub Pages redirect at `tstapler.github.io` → above URL (implemented separately, not in scope of this revamp)
- `install.sh` must:
  1. Detect OS (macOS, Ubuntu/Debian, Arch, WSL2)
  2. Install Homebrew (macOS + Linux via linuxbrew)
  3. Install Ansible via Homebrew
  4. Clone dotfiles repo to `$HOME/dotfiles` if not already present
  5. Initialize and update git submodules
  6. Delegate to `bootstrap/run.sh` (which runs `bootstrap/playbook.yml`)

## Platforms
All platforms must be supported by the Ansible playbook:
- **macOS** (Apple Silicon + Intel) — primary
- **Ubuntu/Debian** — full support
- **Arch/Manjaro** — full support
- **WSL2 (Windows)** — best-effort; Ansible tasks skip GUI/system-level items

Platform detection via Ansible `ansible_os_family` and `ansible_distribution` facts.

## Package Management Strategy
- **Homebrew (linuxbrew on Linux)** as the primary cross-platform package manager
- All packages declared in `Brewfile` (macOS) and `Brewfile.linux` (Linux subset, GUI apps excluded)
- Native package managers (apt, pacman) used only for Homebrew prerequisites

## Ansible Playbook (`bootstrap/playbook.yml`)
Roles run in order. Each role must be idempotent and tagged so individual roles can be re-run.

### Role: homebrew
- Install Homebrew if missing (macOS: standard, Linux: linuxbrew)
- `brew bundle install --file=Brewfile` on macOS
- `brew bundle install --file=Brewfile.linux` on Linux
- Create `Brewfile.linux` as a curated subset of `Brewfile` (CLI tools only, no casks)

### Role: dotfiles
- Install `uv` if not present (via Homebrew or official install script)
- Install cfgcaddy via `uv tool install cfgcaddy` (from PyPI)
- Run `cfgcaddy link --config $dotfiles_dir/.cfgcaddy.yml`
- Remove old `go build` tasks entirely

### Role: shell
- Set zsh as default shell
- Clone zplug if missing
- Fix asdf step: use `stat` on `.tool-versions` file instead of broken `fileglob` lookup
- Run `asdf install` when `.tool-versions` is present

### Role: asdf (new — split from shell)
- Install asdf plugins required by `.tool-versions`
- Run `asdf install` for all tool versions declared

### Role: nix
- Install Nix via Determinate Systems installer (keep as-is)
- Skip if already installed

### Role: secrets
- Require 1Password CLI (`op`) — hard fail with clear message if missing
- Check `op account list` for active session
- Print sign-in instructions if not authenticated
- Test secret injection via `op inject --dry-run` when authenticated

### Role: fonts (new)
- Install Nerd Fonts (powerline-compatible)
- macOS: via `brew install --cask font-meslo-lg-nerd-font` (or equivalent in Brewfile)
- Linux: download + install to `~/.local/share/fonts`, run `fc-cache -fv`
- Skip in WSL2 (no display server assumed)

### Role: claude (new)
- Install Claude Code CLI: `npm install -g @anthropic-ai/claude-code` (npm from Brewfile)
- Link `.claude/` config files via cfgcaddy (already in `.cfgcaddy.yml`)
- Verify: `claude --version`

## Retirement
- `stapler-scripts/bootstrap-dotfiles.sh` — kept for historical reference, add deprecation notice pointing to `install.sh`
- `stapler-scripts/bootstrap.yaml` — delete (references nonexistent role)
- `stapler-scripts/install-scripts/osx-ansible-install.sh` — delete (superseded)

## Non-Goals
- Windows native (non-WSL) support beyond existing PowerShell script
- Automated dotfile conflict resolution
- Remote machine provisioning (only localhost)
- Short URL setup (handled separately outside this repo)

## Success Criteria
1. `curl -fsSL https://raw.githubusercontent.com/tstapler/dotfiles/master/install.sh | bash` runs to completion on a fresh macOS machine
2. Running `install.sh` twice (idempotency) produces no errors and makes no unneeded changes
3. Each Ansible role can be run independently via `--tags <role>`
4. cfgcaddy symlinks are created correctly after dotfiles role runs
5. `asdf install` actually runs when `.tool-versions` exists
6. Claude Code CLI is installed and `claude --version` returns a version
7. Linux (Ubuntu) run completes without macOS-specific failures
