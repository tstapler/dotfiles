#!/usr/bin/env bash
# pr-ci-failures.sh - Get failed CI checks with log excerpts
# Usage: pr-ci-failures.sh <pr-number> [repo]
# Output: Failed checks summary, writes full logs to /tmp/

set -euo pipefail

PR_NUMBER="${1:?Usage: pr-ci-failures.sh <pr-number> [owner/repo]}"
REPO="${2:-}"

REPO_FLAG=""
if [[ -n "$REPO" ]]; then
  REPO_FLAG="--repo $REPO"
fi

echo "=== Failed Checks ===" >&2

# Get failed checks
FAILED=$(gh pr checks "$PR_NUMBER" $REPO_FLAG --json name,state,conclusion,link 2>/dev/null \
  --jq '.[] | select(.conclusion == "failure" or .conclusion == "cancelled")' || echo "")

if [[ -z "$FAILED" ]]; then
  echo "No failed checks found" >&2
  exit 0
fi

echo "$FAILED" | jq -s '.'

# Get the branch name for run lookup
BRANCH=$(gh pr view "$PR_NUMBER" $REPO_FLAG --json headRefName --jq '.headRefName')

echo "" >&2
echo "=== Recent Failed Runs ===" >&2

# Get recent workflow runs
gh run list $REPO_FLAG --branch "$BRANCH" --status failure --limit 3 \
  --json databaseId,name,conclusion,createdAt \
  --jq '.[] | "\(.databaseId)\t\(.name)\t\(.conclusion)"'

echo "" >&2
echo "To get logs: gh run view <run-id> --log > /tmp/ci-log.txt" >&2
echo "Then: grep -n 'error\\|Error\\|FAILED' /tmp/ci-log.txt" >&2
