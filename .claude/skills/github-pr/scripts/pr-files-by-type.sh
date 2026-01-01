#!/usr/bin/env bash
# pr-files-by-type.sh - List PR files grouped by extension
# Usage: pr-files-by-type.sh <pr-number> [repo]
# Output: Files grouped by type for targeted review

set -euo pipefail

PR_NUMBER="${1:?Usage: pr-files-by-type.sh <pr-number> [owner/repo]}"
REPO="${2:-}"

REPO_FLAG=""
if [[ -n "$REPO" ]]; then
  REPO_FLAG="--repo $REPO"
fi

gh pr view "$PR_NUMBER" $REPO_FLAG --json files \
  --jq '
    .files
    | group_by(.path | split(".")[-1])
    | map({
        ext: .[0].path | split(".")[-1],
        count: length,
        files: [.[] | {path: .path, changes: (.additions + .deletions)}]
      })
    | sort_by(.count) | reverse
  '
