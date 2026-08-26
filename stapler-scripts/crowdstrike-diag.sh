#!/usr/bin/env bash
# Gather CrowdStrike Falcon performance diagnostics on macOS.
#
# Usage: sudo ./crowdstrike-diag.sh [duration_seconds]
#   duration_seconds defaults to 60. Run this WHILE the performance issue is occurring.

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "This script must be run with sudo." >&2
  exit 1
fi

DURATION="${1:-60}"
OUTDIR="/tmp/crowdstrike-diag-$(stat -f %m "$0" 2>/dev/null || echo run)"
mkdir -p "$OUTDIR"

echo "Collecting diagnostics for ${DURATION}s into ${OUTDIR}..."

echo "==> spindump"
spindump -notarget "$DURATION" -o "$OUTDIR/spindump.txt"

echo "==> fs_usage (${DURATION}s)"
fs_usage -t "$DURATION" -w >> "$OUTDIR/fs_usage.txt" &
FS_PID=$!
sleep "$DURATION"
kill "$FS_PID" 2>/dev/null || true

echo "==> falconctl diagnose"
/Applications/Falcon.app/Contents/Resources/falconctl diagnose

echo "==> falconctl stats"
/Applications/Falcon.app/Contents/Resources/falconctl stats >> "$OUTDIR/falcon_stats.txt"

echo "==> falconctl stats agent_info"
/Applications/Falcon.app/Contents/Resources/falconctl stats agent_info >> "$OUTDIR/agent_info.txt"

echo "==> gzip results"
tar -czf "$OUTDIR.tar.gz" -C "$(dirname "$OUTDIR")" "$(basename "$OUTDIR")"

echo "Done. Upload $OUTDIR.tar.gz to Google Drive and attach it to the CrowdStrike support case."
