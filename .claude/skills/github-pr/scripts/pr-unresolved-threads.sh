#!/usr/bin/env bash
# pr-unresolved-threads.sh - Get unresolved review threads via GraphQL
# Usage: pr-unresolved-threads.sh <pr-number> <owner> <repo>
# Output: Unresolved review comments with file/line context

set -euo pipefail

PR_NUMBER="${1:?Usage: pr-unresolved-threads.sh <pr-number> <owner> <repo>}"
OWNER="${2:?Missing owner}"
REPO="${3:?Missing repo}"

gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 100) {
          nodes {
            isResolved
            isOutdated
            path
            line
            comments(first: 1) {
              nodes {
                body
                author { login }
                createdAt
              }
            }
          }
        }
      }
    }
  }
' -f owner="$OWNER" -f repo="$REPO" -F pr="$PR_NUMBER" \
  --jq '
    [.data.repository.pullRequest.reviewThreads.nodes[]
     | select(.isResolved == false)
     | {
         file: .path,
         line: .line,
         outdated: .isOutdated,
         author: .comments.nodes[0].author.login,
         comment: (.comments.nodes[0].body | split("\n")[0:3] | join(" ") | .[0:200])
       }
    ]
  '
