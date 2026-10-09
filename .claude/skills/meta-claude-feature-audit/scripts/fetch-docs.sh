#!/usr/bin/env bash
# Usage: fetch-docs.sh [outdir]   (default /tmp/ccdocs)
set -euo pipefail
out="${1:-/tmp/ccdocs}"
mkdir -p "$out"
base=https://code.claude.com/docs/en
for p in commands skills goal hooks sub-agents workflows scheduled-tasks; do
  curl -fsSL -m 30 -o "$out/$p.md" "$base/$p.md" || echo "WARN: $p.md failed" >&2
done
curl -fsSL -m 120 -o "$out/CHANGELOG.md" \
  https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md
ls -l "$out"
