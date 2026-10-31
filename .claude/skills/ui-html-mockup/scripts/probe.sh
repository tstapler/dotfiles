#!/usr/bin/env bash
# Run probe.js against a mockup at a given width and theme; prints JSON. Usage: probe.sh file.html[#page] [width] [light|dark]
# Run both themes: contrast failures often appear only in dark.
set -euo pipefail
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
here="$(cd "$(dirname "$0")" && pwd)"; f="${1%%#*}"; hash="${1#"$f"}"; w="${2:-1440}"; theme="${3:-light}"
tmp="$(mktemp -d)"; THEME="$theme" python3 - "$f" "$here/probe.js" "$tmp/p.html" <<'PY'
import sys,os
s=open(sys.argv[1]).read(); p=open(sys.argv[2]).read()
pre="<script>document.documentElement.dataset.theme='dark';</script>" if os.environ.get('THEME')=='dark' else ''
open(sys.argv[3],'w').write(s.replace('</body>',pre+'<script>'+p+'</script></body>'))
PY
"$CHROME" --headless=new --disable-gpu --window-size="$w,900" --virtual-time-budget=4000 --dump-dom "file://$tmp/p.html$hash" 2>/dev/null | grep -o '<title>.*</title>' | sed 's/<[^>]*>//g;s/&quot;/"/g;s/&amp;/\&/g'
