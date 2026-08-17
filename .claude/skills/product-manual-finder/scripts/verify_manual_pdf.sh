#!/usr/bin/env bash
# Usage: verify_manual_pdf.sh <file.pdf> <model_number>
#
# The single most important correctness gate in this skill: confirms the
# claimed model number actually appears in the PDF's text before it gets
# linked from a wiki page as "the manual" for that product. Run this AFTER
# check_pdf_searchable.sh / make_searchable.sh — a false NO_MATCH on an
# image-only PDF just means it hasn't been OCR'd yet, not that it's wrong.
set -euo pipefail

pdf="${1:?usage: verify_manual_pdf.sh <file.pdf> <model_number>}"
model="${2:?usage: verify_manual_pdf.sh <file.pdf> <model_number>}"

# Extract to a variable first, not a pipe straight into grep -q: grep -q
# exits as soon as it finds a match, SIGPIPEs pdftotext, and under
# `pipefail` that turns a real match into a false "no match" exit status.
text="$(pdftotext "$pdf" - 2>/dev/null || true)"

if grep -qi -- "$model" <<<"$text"; then
	echo "MATCH: '$model' found in $pdf"
	exit 0
fi

echo "NO MATCH: '$model' not found in extracted text of $pdf — do not cite this as the manual until you confirm it another way (e.g. visually via the Read tool on the PDF's cover page)"
exit 1
