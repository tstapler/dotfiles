#!/usr/bin/env bash
# Usage: make_searchable.sh <input.pdf> [output.pdf]
#
# Adds an invisible OCR text layer via ocrmypdf, skipping any page that
# already has text (safe for manuals that mix a typeset cover with scanned
# diagram pages). Defaults to overwriting the input in place.
set -euo pipefail

in="${1:?usage: make_searchable.sh <input.pdf> [output.pdf]}"
out="${2:-$in}"

if ! command -v ocrmypdf >/dev/null 2>&1; then
	echo "ocrmypdf not found — install with: brew install ocrmypdf" >&2
	exit 1
fi

tmp="${out}.ocr-tmp.pdf"
ocrmypdf --skip-text --language eng --output-type pdf "$in" "$tmp"
mv "$tmp" "$out"
echo "Wrote searchable PDF to $out"
