# GitHub API Patterns Reference

Advanced `gh api` patterns for operations not covered by `gh pr` commands.

## REST API Patterns

### PR Details

```bash
# Full PR object (use sparingly - large response)
gh api repos/{owner}/{repo}/pulls/{number}

# Specific fields with jq
gh api repos/{owner}/{repo}/pulls/{number} \
  --jq '{mergeable: .mergeable, state: .mergeable_state, behind: .behind_by}'
```

### PR Commits

```bash
# List commits in PR
gh api repos/{owner}/{repo}/pulls/{number}/commits \
  --jq '.[] | "\(.sha[0:7]) \(.commit.message | split("\n")[0])"'

# Commit count
gh api repos/{owner}/{repo}/pulls/{number}/commits --jq 'length'
```

### PR Review Comments (Line-Level)

```bash
# All review comments
gh api repos/{owner}/{repo}/pulls/{number}/comments \
  --jq '.[] | {
    file: .path,
    line: .line,
    author: .user.login,
    body: (.body | split("\n")[0])
  }'

# Unresolved comments only (need GraphQL for resolved status)
```

### PR Issue Comments (Conversation)

```bash
# Issue-level comments (not line-level)
gh api repos/{owner}/{repo}/issues/{number}/comments \
  --jq '.[] | "\(.user.login): \(.body | split("\n")[0])"'
```

### Check Runs

```bash
# All check runs for PR head
gh api repos/{owner}/{repo}/commits/{sha}/check-runs \
  --jq '.check_runs[] | "\(.name): \(.conclusion // .status)"'

# Failed checks with details
gh api repos/{owner}/{repo}/commits/{sha}/check-runs \
  --jq '.check_runs[] | select(.conclusion == "failure") | {
    name: .name,
    url: .details_url,
    output: .output.summary
  }'
```

### Branch Protection

```bash
# Check if branch is protected
gh api repos/{owner}/{repo}/branches/{branch}/protection \
  --jq '{
    required_reviews: .required_pull_request_reviews.required_approving_review_count,
    dismiss_stale: .required_pull_request_reviews.dismiss_stale_reviews,
    require_ci: .required_status_checks.strict
  }'
```

## GraphQL Patterns

GraphQL is more efficient for complex queries - single request, precise data.

### Basic GraphQL Structure

```bash
gh api graphql -f query='
  query {
    # Query here
  }
' --jq '.data'
```

### PR with Review Threads

```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        title
        state
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
              }
            }
          }
        }
      }
    }
  }
' -f owner=OWNER -f repo=REPO -F pr=123
```

### Unresolved Review Threads Only

```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 100) {
          nodes {
            isResolved
            path
            line
            comments(first: 1) {
              nodes {
                body
                author { login }
              }
            }
          }
        }
      }
    }
  }
' -f owner=OWNER -f repo=REPO -F pr=123 \
  --jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)'
```

### PR Review Decision Summary

```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewDecision
        reviews(last: 10) {
          nodes {
            author { login }
            state
            submittedAt
          }
        }
      }
    }
  }
' -f owner=OWNER -f repo=REPO -F pr=123 \
  --jq '{
    decision: .data.repository.pullRequest.reviewDecision,
    reviews: [.data.repository.pullRequest.reviews.nodes[] | {
      user: .author.login,
      state: .state
    }]
  }'
```

### Files Changed with Patch Status

```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        files(first: 100) {
          nodes {
            path
            additions
            deletions
            changeType
          }
        }
      }
    }
  }
' -f owner=OWNER -f repo=REPO -F pr=123 \
  --jq '.data.repository.pullRequest.files.nodes[]'
```

### CI Status via GraphQL

```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        commits(last: 1) {
          nodes {
            commit {
              statusCheckRollup {
                state
                contexts(first: 50) {
                  nodes {
                    ... on CheckRun {
                      name
                      conclusion
                      detailsUrl
                    }
                    ... on StatusContext {
                      context
                      state
                      targetUrl
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
' -f owner=OWNER -f repo=REPO -F pr=123
```

### Search PRs with GraphQL

```bash
gh api graphql -f query='
  query($search: String!) {
    search(query: $search, type: ISSUE, first: 20) {
      nodes {
        ... on PullRequest {
          number
          title
          author { login }
          updatedAt
          reviewDecision
        }
      }
    }
  }
' -f search="repo:owner/repo is:pr is:open review-requested:@me"
```

## Pagination Patterns

### REST Pagination

```bash
# First page
gh api repos/{owner}/{repo}/pulls?state=all&per_page=100

# With pagination (use --paginate for auto)
gh api repos/{owner}/{repo}/pulls?state=all --paginate \
  --jq '.[] | "\(.number) \(.title)"'
```

### GraphQL Pagination

```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!, $cursor: String) {
    repository(owner: $owner, name: $repo) {
      pullRequests(first: 100, after: $cursor, states: OPEN) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          number
          title
        }
      }
    }
  }
' -f owner=OWNER -f repo=REPO
# Use endCursor for next page
```

## Mutation Patterns

### Add Comment

```bash
gh api repos/{owner}/{repo}/issues/{number}/comments \
  -f body="Comment text here"
```

### Request Review

```bash
gh api repos/{owner}/{repo}/pulls/{number}/requested_reviewers \
  -f 'reviewers[]=username1' -f 'reviewers[]=username2'
```

### Add Labels

```bash
gh api repos/{owner}/{repo}/issues/{number}/labels \
  -f 'labels[]=bug' -f 'labels[]=priority:high'
```

### Merge PR

```bash
# Squash merge
gh api repos/{owner}/{repo}/pulls/{number}/merge \
  -f merge_method=squash \
  -f commit_title="feat: feature title (#123)"

# Check if mergeable first
gh api repos/{owner}/{repo}/pulls/{number} --jq '.mergeable'
```

### Resolve Review Thread (GraphQL)

```bash
gh api graphql -f query='
  mutation($threadId: ID!) {
    resolveReviewThread(input: {threadId: $threadId}) {
      thread {
        isResolved
      }
    }
  }
' -f threadId=THREAD_NODE_ID
```

## Rate Limiting

```bash
# Check rate limit status
gh api rate_limit --jq '{
  core: .resources.core,
  graphql: .resources.graphql
}'

# Remaining calls
gh api rate_limit --jq '.resources.core.remaining'
```

## Error Handling

```bash
# Check for errors in response
gh api repos/{owner}/{repo}/pulls/{number} 2>&1 | grep -q "Not Found" && echo "PR not found"

# Silent fail with default
gh api repos/{owner}/{repo}/pulls/{number} --jq '.mergeable // "unknown"'
```

## Useful jq Patterns

```bash
# Group by author
--jq 'group_by(.author.login) | map({author: .[0].author.login, count: length})'

# Filter and transform
--jq '[.[] | select(.state == "open") | {number, title}]'

# First/last N items
--jq '.[0:5]'  # first 5
--jq '.[-3:]'  # last 3

# Unique values
--jq '[.[] | .author.login] | unique'

# Sum/count
--jq '[.[] | .additions] | add'

# Conditional
--jq 'if .mergeable then "ready" else "blocked" end'
```
