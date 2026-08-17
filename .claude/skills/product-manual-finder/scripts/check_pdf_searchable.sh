#!/usr/bin/env bash
# Usage: check_pdf_searchable.sh <file.pdf>
#
# Prints SEARCHABLE or IMAGE_ONLY and exits 0/1 accordingly. A manual that's
# just scanned page images with no text layer can't be Ctrl-F'd in a PDF
# viewer or in Logseq's own PDF annotation view — that's what this checks
# before a PDF gets committed to the wiki.
set -euo pipefail

pdf="${1:?usage: check_pdf_searchable.sh <file.pdf>}"

chars=$(pdftotext -l 3 "$pdf" - 2>/dev/null | tr -d '[:space:]' | wc -c)

if [ "$chars" -lt 40 ]; then
	echo "IMAGE_ONLY (only $chars non-whitespace chars extracted from first 3 pages)"
	exit 1
fi

echo "SEARCHABLE ($chars non-whitespace chars extracted from first 3 pages)"
