#!/usr/bin/env bash
# disk-cleanup wrapper as on master (commit 1d89af2): dunnage when installed, legacy otherwise. Not changed here.
# shellcheck source=lib.sh
. "$(dirname "$0")/lib.sh"
DC="$SCRIPTS/disk-cleanup"
use_shim

reset_log
"$DC" -v --top 3 2>/dev/null
check "-v dropped, rest forwarded" "--top 3" "$(last_args)"

reset_log
SHIM_EXIT=64 "$DC" -n --apply 2>/dev/null && rc=0 || rc=$?
check "-n --apply forwarded as typed" "-n --apply" "$(last_args)"
check "binary exit code forwarded" 64 "$rc"

# Legacy fallback: replace the legacy script with a stub in a scratch copy of the wrapper.
mkdir "$SCRATCH/copy"
cp "$DC" "$SCRATCH/copy/disk-cleanup"
printf '#!/usr/bin/env bash\necho "legacy $*"\n' >"$SCRATCH/copy/disk-cleanup-legacy"; chmod +x "$SCRATCH/copy/disk-cleanup-legacy"
no_dunnage
check "falls back to legacy" "legacy -n" "$("$SCRATCH/copy/disk-cleanup" -n 2>/dev/null)"

finish
