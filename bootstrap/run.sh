#!/usr/bin/env zsh
# Bootstrap a fresh macOS machine from dotfiles.
# Usage: ./bootstrap/run.sh [--tags homebrew,dotfiles,shell,secrets]

set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Ensure Homebrew exists before ansible can use it
if ! command -v brew &>/dev/null; then
  echo "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/opt/homebrew/bin/brew shellenv)"
fi

# Ensure ansible exists
if ! command -v ansible-playbook &>/dev/null; then
  echo "Installing ansible..."
  brew install ansible
fi

cd "$DOTFILES_DIR/bootstrap"
ansible-playbook playbook.yml \
  -e "dotfiles_dir=$DOTFILES_DIR" \
  "$@"
