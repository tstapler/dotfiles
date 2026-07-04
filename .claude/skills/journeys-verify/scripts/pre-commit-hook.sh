#!/usr/bin/env bash
# journeys-verify pre-commit gate.
#
# No-ops if the target repo has no docs/journeys/ — safe to install everywhere.
# Runs the deterministic Tier 1 check (source_refs exist, test_ids findable),
# which rewrites each journey's status/last_verified/verify_notes in place.
#
# Blocks the commit if:
#   - verify updated any journey file (status changed — needs a conscious re-stage), or
#   - any journey is still stale after the update.
#
# ponytail: shells out to `uv run`, so `uv` must be on PATH; no other deps.
set -euo pipefail

JOURNEYS_DIR="${JOURNEYS_DIR:-docs/journeys}"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

[ -d "$JOURNEYS_DIR" ] || exit 0

check_status=0
uv run "$SKILL_DIR/verify_journeys.py" check --journeys-dir "$JOURNEYS_DIR" --strict || check_status=$?

if ! git diff --quiet -- "$JOURNEYS_DIR"; then
  echo "journeys-verify: journey status changed — review and 'git add $JOURNEYS_DIR', then commit again." >&2
  exit 1
fi

if [ "$check_status" -ne 0 ]; then
  echo "journeys-verify: one or more journeys are stale. Run journeys-enrich to relink, or commit with --no-verify to bypass." >&2
fi

exit "$check_status"
