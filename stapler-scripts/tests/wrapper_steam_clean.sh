#!/usr/bin/env bash
# steam-clean launcher (Story 5.2.1, Task 5.2.1c): list passthrough, tidy retired, legacy fallback.
# shellcheck source=lib.sh
. "$(dirname "$0")/lib.sh"
SC="$SCRIPTS/steam-clean"
use_shim

# S-08: steam_clean_list_sort_size_should_map_to_steam_list_and_tidy_should_exit_64_When_wrapped
reset_log
"$SC" list --sort size 2>"$SCRATCH/err"; rc=$?
check "list --sort size" "steam list --sort size" "$(last_args)"
check "VIA exported" "VIA: steam-clean" "$(grep '^VIA' "$SHIM_LOG" | tail -1)"
check "list exit 0" 0 "$rc"

reset_log
"$SC" 2>/dev/null
check "bare call is steam list" "steam list" "$(last_args)"

reset_log
"$SC" --help 2>/dev/null
check "--help passes under steam" "steam --help" "$(last_args)"

reset_log
rc=0; "$SC" tidy --goal 50G 2>"$SCRATCH/err" || rc=$?
check "tidy exits 64" 64 "$rc"
check "tidy not forwarded" "" "$(cat "$SHIM_LOG")"
check_contains "tidy guidance" "tidy TUI is retired" "$(cat "$SCRATCH/err")"
check_contains "retired logged" "steam-clean retired" "$(cat "$XDG_STATE_HOME/dunnage/wrapper-use.log")"

# Legacy fallback: no dunnage -> the old binary.
printf '#!/usr/bin/env bash\necho "legacy $*"\n' >"$SCRATCH/legacy"; chmod +x "$SCRATCH/legacy"
no_dunnage
export DUNNAGE_STEAM_LEGACY_BIN="$SCRATCH/legacy"
check "legacy used without dunnage" "legacy list --sort size" "$("$SC" list --sort size)"
use_shim
check "DUNNAGE_LEGACY=1 forces legacy" "legacy list" "$(DUNNAGE_LEGACY=1 "$SC" list)"

# No self-exec loop: legacy path resolving to the launcher exits 2.
no_dunnage
ln -s "$SC" "$SCRATCH/selflink"
rc=0; DUNNAGE_STEAM_LEGACY_BIN="$SCRATCH/selflink" "$SC" list 2>"$SCRATCH/err" || rc=$?
check "refuses to exec itself" 2 "$rc"
check_contains "self-exec message" "refusing to exec itself" "$(cat "$SCRATCH/err")"

finish
