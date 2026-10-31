#!/usr/bin/env bash
# Screenshot a mockup in headless Chrome. Usage: shoot.sh <file.html[#hash]> <out.png> [width] [height]
# The hash selects a page / mode, e.g. file.html#queues,annotations or file.html#tour.
set -euo pipefail
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
f="$1"; out="$2"; w="${3:-1440}"; h="${4:-900}"
case "$f" in http*|file:*) url="$f" ;; *) url="file://$(cd "$(dirname "${f%%#*}")" && pwd)/$(basename "${f%%#*}")$( [[ "$f" == *#* ]] && echo "#${f#*#}" )" ;; esac
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --window-size="$w,$h" --virtual-time-budget=4000 --screenshot="$out" "$url" 2>&1 | grep -E "written" || { echo "screenshot failed" >&2; exit 1; }
