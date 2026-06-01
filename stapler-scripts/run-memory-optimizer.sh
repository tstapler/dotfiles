#!/usr/bin/env bash
# Ensures Ansible is installed, then runs the memory-optimizer playbook.
# Usage: ./run-memory-optimizer.sh [--dry-run] [extra ansible-playbook args]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAYBOOK="$SCRIPT_DIR/memory-optimizer.yaml"

# ── Install Ansible if missing ────────────────────────────────────────────────
if ! command -v ansible-playbook &>/dev/null; then
  echo "Ansible not found. Installing..."
  if command -v pacman &>/dev/null; then
    sudo pacman -Sy --noconfirm ansible
  elif command -v apt-get &>/dev/null; then
    sudo apt-get update -qq && sudo apt-get install -y ansible
  elif command -v dnf &>/dev/null; then
    sudo dnf install -y ansible
  elif command -v zypper &>/dev/null; then
    sudo zypper install -y ansible
  else
    echo "ERROR: No supported package manager found (pacman/apt/dnf/zypper)." >&2
    exit 1
  fi
fi

# ── Parse args ────────────────────────────────────────────────────────────────
DRY_RUN=false
EXTRA_ARGS=()

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    *)         EXTRA_ARGS+=("$arg") ;;
  esac
done

# ── Prompt once for the become password and validate it immediately ───────────
read -rsp "BECOME password: " ANSIBLE_BECOME_PASS
echo
if ! echo "$ANSIBLE_BECOME_PASS" | sudo -S true 2>/dev/null; then
  echo "Incorrect sudo password." >&2
  exit 1
fi
export ANSIBLE_BECOME_PASS

# ── Run playbook ──────────────────────────────────────────────────────────────
cd "$SCRIPT_DIR"

if $DRY_RUN; then
  echo "Running in dry-run mode (--check --diff) ..."
  ansible-playbook "$PLAYBOOK" --check --diff "${EXTRA_ARGS[@]}"
else
  ansible-playbook "$PLAYBOOK" "${EXTRA_ARGS[@]}"
fi

unset ANSIBLE_BECOME_PASS
