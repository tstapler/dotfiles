#!/bin/bash
# Collect everything test-profile.py needs for ONE Go package, then print the report.
#
#   collect.sh <name> <package> [go test flags...]
#   collect.sh mcp ./server/mcp -tags=integration -race
#
# Writes <OUT>/<name>.{json,cpu,test,time,err} (OUT defaults to /tmp/test-profile) and
# prints the report. Run suites ONE AT A TIME: two suites sharing the machine inflate each
# other's per-test durations and make the histogram lie.
#
# `-o` keeps the test binary so pprof can symbolize; `/usr/bin/time -l` (macOS) records
# user+sys for the whole process tree, which includes child processes the CPU profile can't see.
set -u
name=${1:?usage: collect.sh <name> <package> [go test flags...]}
pkg=${2:?usage: collect.sh <name> <package> [go test flags...]}
shift 2
out=${OUT:-/tmp/test-profile}
mkdir -p "$out"
here=$(cd "$(dirname "$0")" && pwd)

/usr/bin/time -l -o "$out/$name.time" \
  go test -count=1 -json -timeout="${TIMEOUT:-1500s}" \
    -cpuprofile="$out/$name.cpu" -o "$out/$name.test" "$@" "$pkg" \
  >"$out/$name.json" 2>"$out/$name.err"
rc=$?
[ $rc -ne 0 ] && echo "note: go test exited $rc (failing tests still give a usable histogram; see $out/$name.err)" >&2

python3 "$here/test-profile.py" --title "$name ($pkg $*)" \
  --json "$out/$name.json" --cpu "$out/$name.cpu" --bin "$out/$name.test" --time "$out/$name.time"
