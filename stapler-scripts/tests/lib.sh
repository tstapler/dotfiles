#!/usr/bin/env bash
# Shared fixtures for wrapper_*.sh. Sourced; sets SCRATCH, SHIM_LOG, and a fake `dunnage` on PATH that records
# its argv and DUNNAGE_VIA and exits SHIM_EXIT (default 0). Nothing here touches real caches.
set -euo pipefail

SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export SCRIPTS
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/wrapper-test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT
export HOME="$SCRATCH/home" XDG_STATE_HOME="$SCRATCH/state"
mkdir -p "$HOME" "$SCRATCH/bin"
SHIM_LOG="$SCRATCH/shim.log"
export SHIM_LOG
unset DUNNAGE_BIN DUNNAGE_LEGACY DUNNAGE_STEAM_LEGACY_BIN DISK_CLEANUP_VIA DUNNAGE_VIA

install_shim() {
  cat >"$SCRATCH/bin/dunnage" <<'SHIM'
#!/usr/bin/env bash
{ echo "ARGS: $*"; echo "VIA: ${DUNNAGE_VIA:-}"; } >>"$SHIM_LOG"
exit "${SHIM_EXIT:-0}"
SHIM
  chmod +x "$SCRATCH/bin/dunnage"
}

# PATH without dunnage, but with the tools the wrappers need.
BASE_PATH="/usr/bin:/bin"
use_shim() { install_shim; PATH="$SCRATCH/bin:$BASE_PATH"; export PATH; }
no_dunnage() { rm -f "$SCRATCH/bin/dunnage"; PATH="$SCRATCH/bin:$BASE_PATH"; export PATH; }

FAILS=0
check() { # check <name> <expected> <actual>
  if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1: expected [$2] got [$3]"; FAILS=$((FAILS + 1)); fi
}
check_contains() { # check_contains <name> <needle> <haystack>
  case "$3" in *"$2"*) echo "ok   $1" ;; *) echo "FAIL $1: [$2] not in [$3]"; FAILS=$((FAILS + 1)) ;; esac
}
last_args() { grep '^ARGS: ' "$SHIM_LOG" | tail -1 | sed 's/^ARGS: //'; }
reset_log() { : >"$SHIM_LOG"; }
finish() { if [ "$FAILS" -eq 0 ]; then echo "all passed"; else echo "$FAILS failed"; exit 1; fi; }
