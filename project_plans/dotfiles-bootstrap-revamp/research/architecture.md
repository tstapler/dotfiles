# Architecture Research: curl | bash Bootstrap Patterns

## Safe curl | bash Practices

### Standard Pattern
```bash
curl -fsSL https://raw.githubusercontent.com/tstapler/dotfiles/master/install.sh | bash
```
**Flags**: `-f` (fail on HTTP error), `-s` (silent/no progress), `-S` (show errors even with -s), `-L` (follow redirects)

### Security Considerations
1. **Trust model**: curl|bash trusts the remote server completely. The practical mitigation is HTTPS (TLS in transit) + GitHub's content integrity guarantees.
2. **Checksum verification** (optional hardening): Download to tempfile, verify SHA256, then execute:
   ```bash
   tmp=$(mktemp); curl -fsSL $URL -o $tmp
   echo "EXPECTED_HASH  $tmp" | sha256sum -c && bash $tmp
   ```
   However, for a personal dotfiles repo this is overkill; the Determinate Systems Nix installer uses plain curl|sh and it runs millions of times daily.
3. **Tempfile pattern** (avoids piping directly): Download and inspect before running — better for users auditing the script.

### Idempotency Guards
Every step in install.sh must be safe to run twice. Key patterns:
```bash
# Guard: only run if not already installed
if ! command -v brew &>/dev/null; then
  # install brew
fi

# Guard: only clone if directory absent
if [ ! -d "$HOME/dotfiles" ]; then
  git clone ...
fi

# Guard: already initialized
if git -C "$HOME/dotfiles" submodule status | grep -q "^-"; then
  git -C "$HOME/dotfiles" submodule update --init --recursive
fi
```

### OS Detection Pattern
```bash
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
```

---

## GitHub Pages / Redirect Setup

### Simplest approach: raw.githubusercontent.com direct link
```
curl -fsSL https://raw.githubusercontent.com/tstapler/dotfiles/master/install.sh | bash
```
No redirect needed. Works immediately after pushing install.sh to the repo.

### Short URL via GitHub redirect
`git.io` is deprecated. The recommended modern alternative:
- Use `raw.githubusercontent.com` directly (no redirect service needed)
- Or set up GitHub Pages with a `docs/` folder and `index.html` redirect:
  ```html
  <meta http-equiv="refresh" content="0;url=https://raw.githubusercontent.com/tstapler/dotfiles/master/install.sh">
  ```

### curl-sh.github.io Pattern
The `curl-sh` service supports: `curl https://git.io/dotfiles.sh -L | sh`
- Can specify alternate repo: `... | sh -s tstapler/dotfiles`
- Not recommended — git.io is deprecated, and direct raw.githubusercontent.com is simpler.

---

## How chezmoi / yadm / dotbot Handle Multi-Platform

### chezmoi
- Single binary (Go), installed via `curl -fsLS get.chezmoi.io | sh`
- Templates with `{{ .chezmoi.os }}` and `{{ .chezmoi.arch }}` — platform-conditional file content
- Per-machine state in `~/.local/share/chezmoi/`
- `chezmoi apply` is idempotent by design — uses a local state DB to track what changed
- One-liner: `sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply tstapler`

### yadm
- Shell wrapper (bash), installed via package managers
- Bootstrap file: `$HOME/.config/yadm/bootstrap` — any executable, runs after clone
- Multi-platform via `##os.Linux`, `##os.Darwin` filename suffixes for conditional file selection
- No built-in Ansible integration — bootstrap script calls ansible-playbook

### dotbot
- Python-based, runs as a submodule inside the dotfiles repo
- `install` script calls `./dotbot/bin/dotbot -c install.conf.yaml`
- Config: YAML mapping of `link`, `shell`, `clean` directives
- Platform filtering via shell `if/else` around dotbot invocations in install script
- Simpler than Ansible but less powerful for system configuration

### Key Takeaway
All three frameworks converge on:
1. A single executable install command (curl|sh or package manager)
2. Idempotent apply step
3. Platform detection via OS facts or file suffixes
4. Bootstrap script delegates to a more powerful system (Ansible, shell, etc.)

**The requirements call for Ansible — this is more powerful than any of the above and is the right choice for the scope of tools being managed.**

---

## Determinate Systems Nix Installer as Reference Architecture

The Determinate Nix Installer is the best reference for a production-quality curl|bash installer:

```bash
curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix \
  | sh -s -- install --no-confirm
```

### Design Principles (applicable to install.sh)
1. **`--proto '=https'`** enforces HTTPS-only (no http fallback)
2. **`--tlsv1.2`** enforces minimum TLS version
3. **Installation receipt** (JSON at `/nix/...`) — tracks exactly what was done, enables clean uninstall
4. **Idempotent**: re-running detects existing install and skips
5. **`--no-confirm` flag** for unattended/CI use
6. **Written in Rust** (not bash) — avoids bash portability issues
7. Supports `--explain` flag for dry-run/audit

### Recommended install.sh Structure (adapted from DS pattern)
```bash
#!/usr/bin/env bash
set -euo pipefail

DOTFILES_REPO="https://github.com/tstapler/dotfiles"
DOTFILES_DIR="${HOME}/dotfiles"
INSTALL_RECEIPT="${HOME}/.dotfiles-installed"

# Step 1: OS detection
OS=$(detect_os)

# Step 2: Install Homebrew (if not present)
if ! command -v brew &>/dev/null; then
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  # Add brew to PATH for this session
  case "$OS" in
    macos)   eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)" ;;
    *)       eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)" ;;
  esac
fi

# Step 3: Install Ansible
if ! command -v ansible-playbook &>/dev/null; then
  brew install ansible
fi

# Step 4: Clone dotfiles
if [ ! -d "$DOTFILES_DIR" ]; then
  git clone "$DOTFILES_REPO" "$DOTFILES_DIR"
fi

# Step 5: Initialize submodules
git -C "$DOTFILES_DIR" submodule update --init --recursive

# Step 6: Delegate to bootstrap/run.sh
exec "$DOTFILES_DIR/bootstrap/run.sh" "$@"
```

---

## Recommended Entry Point Design

```
install.sh (repo root, curl-accessible)
  └── bootstrap/run.sh (Ansible driver)
       └── bootstrap/playbook.yml
            └── roles: homebrew, dotfiles, shell, asdf, nix, secrets, fonts, claude
```

- `install.sh`: shell-only, handles pre-Ansible prerequisites (brew, git, clone, submodules)
- `bootstrap/run.sh`: handles Ansible invocation, tag passing
- `bootstrap/playbook.yml`: Ansible orchestration with platform-conditional roles

## Sources
- [Determinate Systems nix-installer GitHub](https://github.com/DeterminateSystems/nix-installer)
- [chezmoi install docs](https://www.chezmoi.io/)
- [yadm bootstrap docs](https://yadm.io/docs/bootstrap)
- [dotfiles.github.io bootstrap patterns](https://dotfiles.github.io/bootstrap/)
- [curl-sh patterns](https://github.com/curl-sh/curl-sh.github.io)
