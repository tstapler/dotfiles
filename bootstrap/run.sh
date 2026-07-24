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


cd "$DOTFILES_DIR/bootstrap"
ansible-galaxy collection install -r requirements.yml --timeout 30

# Mitogen keeps one Python interpreter alive across tasks instead of
# ansible-core forking a fresh one per task — a real speedup even for this
# connection: local playbook. ansible-core 2.20 (this repo's version) has
# been supported since mitogen 0.3.33 (2025-11-22); verify
# https://github.com/mitogen-hq/mitogen/releases before bumping ansible if
# this floor version ever needs to move. Installed with `pip --target` into a
# plain directory (not a venv, not ansible's own Homebrew Cellar site-packages)
# so it survives `brew upgrade ansible` untouched and isn't wiped by Homebrew.
# Wired in via env vars here rather than bootstrap/ansible.cfg so a bare
# `ansible-playbook playbook.yml` (no run.sh) still works unmodified — as of
# ansible-core 2.19, third-party strategy plugins are deprecated (a
# [DEPRECATION WARNING] prints, no removal date announced yet); if ansible-core
# ever removes them outright, deleting this block is the only revert needed.
MITOGEN_DIR="$HOME/.local/share/mitogen"
if [ ! -d "$MITOGEN_DIR/ansible_mitogen" ]; then
  echo "Installing Mitogen for Ansible..."
  python3 -m pip install --quiet --target "$MITOGEN_DIR" "mitogen>=0.3.33"
fi
export ANSIBLE_STRATEGY=mitogen_linear
export ANSIBLE_STRATEGY_PLUGINS="$MITOGEN_DIR/ansible_mitogen/plugins/strategy"
export PYTHONPATH="$MITOGEN_DIR${PYTHONPATH:+:$PYTHONPATH}"

# Auto-detect FBG work machine by hostname prefix; skip if tags already specified
FBG_ARGS=()
if [[ "$*" != *"--tags"* && "$*" != *"--skip-tags"* ]]; then
  if [[ "$(hostname)" == [Ff][Bb][Gg]-* ]]; then
    echo "FBG machine detected ($(hostname)) — enabling work tools."
  else
    echo "Non-FBG machine ($(hostname)) — skipping FBG-specific setup."
    FBG_ARGS=(--skip-tags fbg)
  fi
fi

# `gh auth refresh` for a missing OAuth scope is interactive (prints a
# device code / opens a browser, then blocks until authorized). Ansible's
# command module buffers output until the subprocess exits, so running this
# as a playbook task would look hung — the code would be invisible until
# it's too late. Do it here instead, where we have a real terminal, so the
# github role's SSH-key registration doesn't fail on a missing scope.
check_gh_scope() {
  local label="$1" user="${2:-}" original=""

  if [[ -n "$user" ]]; then
    original=$(gh api user --jq .login 2>/dev/null || echo "")
    gh auth switch --hostname github.com --user "$user" >/dev/null 2>&1 || return 0
  fi

  local status
  if ! status=$(gh auth status --hostname github.com 2>&1); then
    # Not authenticated at all — the github role's own fail-with-instructions
    # task handles first-time `gh auth login`, nothing to do here.
    [[ -n "$user" && -n "$original" ]] && gh auth switch --hostname github.com --user "$original" >/dev/null 2>&1
    return 0
  fi

  if ! grep -q "admin:public_key" <<<"$status"; then
    echo "gh CLI ($label) is missing the admin:public_key scope needed to register SSH keys."
    echo "Opening browser to authorize — approve the admin:public_key scope when prompted."
    gh auth refresh -h github.com -s admin:public_key || true
  fi

  [[ -n "$user" && -n "$original" ]] && gh auth switch --hostname github.com --user "$original" >/dev/null 2>&1
  return 0
}

if command -v gh &>/dev/null; then
  check_gh_scope "primary account"
  if [[ "$(hostname)" == [Ff][Bb][Gg]-* ]]; then
    check_gh_scope "personal account ($USER)" "$USER"
  fi
fi

# Ansible's become (sudo) runs from a forked, non-tty subprocess, so a sudo
# ticket cached in this script's own shell (e.g. from an earlier `sudo pacman`
# call) is invisible to it — sudo caches tickets per-tty by default. Always
# prompt for the become password; Ansible then re-supplies it on every
# privileged task itself, no ticket to babysit or expire mid-playbook.
ansible-playbook playbook.yml \
  -e "dotfiles_dir=$DOTFILES_DIR" \
  -K \
  "${FBG_ARGS[@]+"${FBG_ARGS[@]}"}" \
  "$@"
