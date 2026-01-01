#!/usr/bin/env bash
# pr-summary.sh - Get token-efficient PR summary
# Usage: pr-summary.sh <pr-number> [repo]
# Output: Compact JSON summary suitable for context loading

set -euo pipefail

PR_NUMBER="${1:?Usage: pr-summary.sh <pr-number> [owner/repo]}"
REPO="${2:-}"

REPO_FLAG=""
if [[ -n "$REPO" ]]; then
  REPO_FLAG="--repo $REPO"
fi

# Get core PR info with minimal fields
gh pr view "$PR_NUMBER" $REPO_FLAG --json \
  number,title,state,author,baseRefName,headRefName,\
additions,deletions,changedFiles,mergeable,reviewDecision,\
isDraft,createdAt,updatedAt \
  --jq '{
    number: .number,
    title: .title,
    state: .state,
    author: .author.login,
    base: .baseRefName,
    head: .headRefName,
    stats: "\(.additions)+/\(.deletions)-/\(.changedFiles) files",
    mergeable: .mergeable,
    review: .reviewDecision,
    draft: .isDraft,
    age: (now - (.createdAt | fromdateiso8601) | . / 86400 | floor | tostring + "d")
  }'
