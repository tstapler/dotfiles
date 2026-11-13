#!/usr/bin/env bash
# buildclean.py wrapper (Story 5.2.1, Task 5.2.1b): flag translation, refusals, legacy fallback.
# shellcheck source=lib.sh
. "$(dirname "$0")/lib.sh"
BC="$SCRIPTS/buildclean.py"
use_shim

run_bc() { SHIM_EXIT="${SHIM_EXIT:-0}" python3 -I "$BC" "$@" 2>"$SCRATCH/err" >"$SCRATCH/out"; echo $?; }

# S-04: buildclean_apply_kinds_node_modules_root_should_map_to_apply_kinds_build_dirs_root_and_not_forward_force_When_wrapped
reset_log
rc=$(run_bc ~/code --apply --kinds node_modules)
check "apply maps to build-dirs with --root" "--kinds build-dirs --jobs 24 --top 20 --min-age 60m --apply --root $HOME/code" "$(last_args)"
check "dunnage sees VIA" "VIA: buildclean.py" "$(grep '^VIA' "$SHIM_LOG" | tail -1)"
check "exit forwarded (0)" 0 "$rc"

# T-380: buildclean_apply_should_forward_exit_64_with_the_NOTE_and_never_invent_a_plan_id_When_build_dirs
reset_log
rc=$(SHIM_EXIT=64 run_bc ~/code --apply --kinds node_modules)
check "apply exit 64 forwarded" 64 "$rc"
check_contains "plan-id NOTE on stderr" "NOTE: build dirs now need --plan-id from a dry run" "$(cat "$SCRATCH/err")"
check "stdout empty on refusal" "" "$(cat "$SCRATCH/out")"
check_contains "note logged" "buildclean.py note" "$(cat "$XDG_STATE_HOME/dunnage/wrapper-use.log")"

reset_log
rc=$(SHIM_EXIT=64 run_bc ~/code)
check "dry-run 64 gets no plan-id NOTE" "" "$(cat "$SCRATCH/err")"

# S-05: buildclean_old_flags_min_age_min_jobs_scan_jobs_top_json_should_translate_or_exit_64_with_guidance_never_be_ignored_When_given
reset_log
rc=$(run_bc --min-age-min 90 -j 8 --top 5 --kinds node_modules target)
check "age/jobs/top translated, default roots omitted" "--kinds build-dirs --jobs 8 --top 5 --min-age 90m" "$(last_args)"

reset_log
rc=$(run_bc --min-age-min 0.2)
check "sub-minute age rounds up" "--kinds build-dirs --jobs 24 --top 20 --min-age 1m" "$(last_args)"

# S-06: buildclean_remove_should_exit_64_with_replacement_command_When_remove_dir_given
for flags in "--remove $HOME/a/b/c" "--json /tmp/x.json" "--scan-jobs 4"; do
  reset_log
  # shellcheck disable=SC2086
  rc=$(run_bc $flags)
  check "refused: $flags" 64 "$rc"
  check "not forwarded: $flags" "" "$(cat "$SHIM_LOG")"
  check_contains "guidance: $flags" "buildclean.py:" "$(cat "$SCRATCH/err")"
done

reset_log
rc=$(run_bc --force)
check "--force dropped" "--kinds build-dirs --jobs 24 --top 20 --min-age 60m" "$(last_args)"
check_contains "--force noted" "--force is not forwarded" "$(cat "$SCRATCH/err")"

# Legacy: no dunnage, or forced, scans a fixture with the old code and deletes nothing without --apply.
fixture="$HOME/code/proj"
mkdir -p "$fixture/node_modules/x"; : >"$fixture/package.json"; : >"$fixture/node_modules/x/f"
touch -d '3 days ago' "$fixture/node_modules/x/f" "$fixture/node_modules/x" "$fixture/node_modules"
no_dunnage
reset_log
rc=$(run_bc "$HOME/code" --min-age-min 1)
check "legacy dry run exits 0" 0 "$rc"
check_contains "legacy output" "dry run:" "$(cat "$SCRATCH/out")"
check "no dunnage call" "" "$(cat "$SHIM_LOG")"
check "legacy dry run deleted nothing" yes "$([ -d "$fixture/node_modules" ] && echo yes || echo no)"

use_shim
reset_log
rc=$(DUNNAGE_LEGACY=1 run_bc "$HOME/code" --min-age-min 1)
check_contains "DUNNAGE_LEGACY=1 forces legacy" "dry run:" "$(cat "$SCRATCH/out")"
check "forced legacy skips dunnage" "" "$(cat "$SHIM_LOG")"

finish
