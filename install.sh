#!/usr/bin/env bash
# install.sh — One-liner entry point for dotfiles bootstrap.
# Usage: curl -fsSL https://raw.githubusercontent.com/tstapler/dotfiles/master/install.sh | bash
# Or from repo root: ./install.sh [--tags homebrew,dotfiles,shell,secrets]

set -euo pipefail

DOTFILES_REPO="https://github.com/tstapler/dotfiles"
DOTFILES_DIR="${HOME}/dotfiles"

# ── OS detection ───────────────────────────────────────────────────────────────
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

# ── Linux prerequisites ────────────────────────────────────────────────────────
install_linux_prereqs() {
  case "$OS" in
    ubuntu|wsl2)
      # apt-get update can fail if cloud-init holds the lock; continue with a warning
      sudo apt-get update -qq || { echo "WARNING: apt-get update failed; continuing anyway"; }
      sudo apt-get install -y build-essential curl file git unzip
      ;;
    arch)
      # --needed avoids re-installing already-present packages; avoids partial-upgrade state
      sudo pacman -S --needed --noconfirm base-devel curl file git unzip
      ;;
  esac
}

if [ "$OS" != "macos" ]; then
  install_linux_prereqs
fi

# ── Homebrew install + PATH setup ──────────────────────────────────────────────
install_homebrew() {
  if ! command -v brew &>/dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  fi

  # Add brew to PATH for this session — handle Apple Silicon, Intel macOS, and Linux
  if [ -f /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [ -f /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
  elif [ -f /home/linuxbrew/.linuxbrew/bin/brew ]; then
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
  fi
}

install_homebrew

# ── Ansible ────────────────────────────────────────────────────────────────────
if ! command -v ansible-playbook &>/dev/null; then
  echo "Installing Ansible via Homebrew..."
  brew install ansible
fi

# ── Clone dotfiles ─────────────────────────────────────────────────────────────
if [ ! -d "$DOTFILES_DIR" ]; then
  echo "Cloning dotfiles to $DOTFILES_DIR..."
  git clone "$DOTFILES_REPO" "$DOTFILES_DIR"
else
  echo "Dotfiles directory already exists at $DOTFILES_DIR, skipping clone."
fi

# ── Git submodules ─────────────────────────────────────────────────────────────
# Only update if there are uninitialized submodules (lines starting with '-')
if git -C "$DOTFILES_DIR" submodule status | grep -q "^-"; then
  echo "Initializing git submodules..."
  git -C "$DOTFILES_DIR" submodule update --init --recursive
fi

# ── Delegate to bootstrap/run.sh ──────────────────────────────────────────────
if [ ! -x "$DOTFILES_DIR/bootstrap/run.sh" ]; then
  echo "ERROR: $DOTFILES_DIR/bootstrap/run.sh not found or not executable" >&2
  exit 1
fi

exec "$DOTFILES_DIR/bootstrap/run.sh" "$@"
