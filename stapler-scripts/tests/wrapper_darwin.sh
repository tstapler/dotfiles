#!/usr/bin/env bash
# Darwin gate (Story 5.2.1, Task 5.2.1e): all three wrappers stay on the legacy tool unless the machine-local
# darwin-verified marker holds the sha256 of the dunnage binary. A `uname` shim fakes Darwin; nothing real is touched.
# shellcheck source=lib.sh
. "$(dirname "$0")/lib.sh"
use_shim
printf '#!/bin/sh\necho Darwin\n' >"$SCRATCH/bin/uname"; chmod +x "$SCRATCH/bin/uname"

# Scratch copies so disk-cleanup finds a stub legacy script next to it.
mkdir "$SCRATCH/copy"
cp "$SCRIPTS/disk-cleanup" "$SCRIPTS/steam-clean" "$SCRIPTS/buildclean.py" "$SCRATCH/copy/"
printf '#!/usr/bin/env bash\necho "legacy $*"\n' >"$SCRATCH/copy/disk-cleanup-legacy"; chmod +x "$SCRATCH/copy/disk-cleanup-legacy"
printf '#!/usr/bin/env bash\necho "legacy $*"\n' >"$SCRATCH/legacy"; chmod +x "$SCRATCH/legacy"
export DUNNAGE_STEAM_LEGACY_BIN="$SCRATCH/legacy"
marker="$XDG_STATE_HOME/dunnage/darwin-verified"
mkdir -p "$(dirname "$marker")"
good="$(sha256sum "$SCRATCH/bin/dunnage" | cut -d' ' -f1)"

# buildclean has no shell uname: run it with sys.platform patched.
bc() {
  BC_PATH="$SCRATCH/copy/buildclean.py" python3 -I -c 'import os, runpy, sys; sys.platform = "darwin"; sys.argv = ["buildclean.py"] + sys.argv[1:]; runpy.run_path(os.environ["BC_PATH"], run_name="__main__")' "$@" 2>/dev/null
}

run_all() { # prints which tool each wrapper used: dunnage or legacy
  reset_log
  dc="$("$SCRATCH/copy/disk-cleanup" --top 1 2>/dev/null)"
  sc="$("$SCRATCH/copy/steam-clean" list 2>/dev/null)"
  reset_log; bc "$HOME" --min-age-min 1 >/dev/null || true
  bcr="dunnage"; [ -s "$SHIM_LOG" ] || bcr="legacy"
  [ "$dc" = "legacy --top 1" ] && dcr=legacy || dcr=dunnage
  [ "$sc" = "legacy list" ] && scr=legacy || scr=dunnage
  echo "$dcr $scr $bcr"
}

rm -f "$marker"
check "no marker gives legacy" "legacy legacy legacy" "$(run_all)"
echo "0000" >"$marker"
check "marker with another hash gives legacy" "legacy legacy legacy" "$(run_all)"
echo "$good  dunnage" >"$marker"
check "marker with the right hash gives dunnage" "dunnage dunnage dunnage" "$(run_all)"
echo "$good" >"$marker"
check "bare-hash marker gives dunnage" "dunnage dunnage dunnage" "$(run_all)"
echo "$good" >"$marker"; echo changed >>"$SCRATCH/bin/dunnage"
check "rebuilt binary falls back to legacy" "legacy legacy legacy" "$(run_all)"

# The old in-repo marker path is gitignored so a commit cannot flip a Mac.
if command -v git >/dev/null 2>&1; then
  git init -q "$SCRATCH/repo" && printf 'stapler-scripts/.disk-cleanup-darwin-ok\n' >"$SCRATCH/repo/.gitignore"
  git -C "$SCRATCH/repo" check-ignore -q stapler-scripts/.disk-cleanup-darwin-ok && r=0 || r=$?
  check "old in-repo marker path is ignorable" 0 "$r"
fi
finish
