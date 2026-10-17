#!/usr/bin/env bash
# Usage: fetch-docs.sh [outdir]   (default: new mktemp -d; path is printed)
set -euo pipefail
out="${1:-$(mktemp -d "${TMPDIR:-/tmp}/ccdocs.XXXXXX")}"
mkdir -p "$out"
base=https://code.claude.com/docs/en
for p in commands skills goal hooks sub-agents workflows scheduled-tasks; do
  curl -fsSL -m 30 -o "$out/$p.md" "$base/$p.md" || echo "WARN: $p.md failed" >&2
done
curl -fsSL -m 120 -o "$out/CHANGELOG.md" \
  https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md || echo "WARN: CHANGELOG.md failed" >&2
echo "docs dir: $out"
ls -l "$out"
# scan.py cannot run without these two.
for req in skills commands; do
  [ -s "$out/$req.md" ] || { echo "ERROR: $req.md missing or empty" >&2; exit 1; }
done
