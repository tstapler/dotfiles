#!/usr/bin/env bash
# pr-review-status.sh - Get review status with reviewer details
# Usage: pr-review-status.sh <pr-number> [repo]
# Output: Compact review summary

set -euo pipefail

PR_NUMBER="${1:?Usage: pr-review-status.sh <pr-number> [owner/repo]}"
REPO="${2:-}"

REPO_FLAG=""
if [[ -n "$REPO" ]]; then
  REPO_FLAG="--repo $REPO"
fi

gh pr view "$PR_NUMBER" $REPO_FLAG --json \
  reviewDecision,reviews,reviewRequests \
  --jq '{
    decision: .reviewDecision,
    reviews: [.reviews | group_by(.author.login)[] | {
      user: .[0].author.login,
      latest: .[-1].state,
      count: length
    }],
    pending: [.reviewRequests[].login]
  }'
