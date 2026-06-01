#!/usr/bin/env bash
# Creates a 32G swapfile at /swapfile and registers it in /etc/fstab for persistence.
set -euo pipefail

SWAPFILE="/swapfile"
SIZE="32G"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Must be run as root (sudo $0)" >&2
  exit 1
fi

FSTYPE="$(stat -f -c '%T' /)"

if swapon --show | grep -q "^${SWAPFILE}"; then
  echo "Swap already active on ${SWAPFILE}"
else
  if [[ ! -f "$SWAPFILE" ]]; then
    echo "Creating ${SIZE} swapfile at ${SWAPFILE}..."
    if [[ "$FSTYPE" == "btrfs" ]]; then
      # btrfs: NoCOW must be set before any data is written to the file
      touch "$SWAPFILE"
      chattr +C "$SWAPFILE"
    fi
    fallocate -l "$SIZE" "$SWAPFILE"
    chmod 600 "$SWAPFILE"
    mkswap "$SWAPFILE"
  elif [[ "$FSTYPE" == "btrfs" ]]; then
    # Existing file — check NoCOW; if missing, the file must be recreated
    if ! lsattr "$SWAPFILE" | awk '{print $1}' | grep -q 'C'; then
      echo "ERROR: ${SWAPFILE} exists on btrfs but lacks NoCOW attribute." >&2
      echo "Remove it and re-run: sudo rm ${SWAPFILE} && sudo $0" >&2
      exit 1
    fi
  fi
  echo "Enabling swap..."
  swapon "$SWAPFILE"
fi

if ! grep -q "^${SWAPFILE}" /etc/fstab; then
  echo "Adding ${SWAPFILE} to /etc/fstab..."
  echo "${SWAPFILE} none swap defaults 0 0" >> /etc/fstab
else
  echo "${SWAPFILE} already in /etc/fstab"
fi

echo "Done. Current swap:"
swapon --show
