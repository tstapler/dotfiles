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

# Add brew to PATH for this session — handle Apple Silicon, Intel macOS, and Linux
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

cd "$DOTFILES_DIR"
git submodule update --init cfgcaddy 2>/dev/null || true

# Install Nix if not present (requires root; handled here outside Ansible)
if [ ! -f /nix/var/nix/profiles/default/bin/nix ]; then
  echo "Installing Nix..."
  curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix \
    | sh -s -- install --no-confirm
fi

cd "$DOTFILES_DIR/bootstrap"
ansible-galaxy collection install -r requirements.yml --timeout 30
ansible-playbook playbook.yml \
  -e "dotfiles_dir=$DOTFILES_DIR" \
  "$@"
