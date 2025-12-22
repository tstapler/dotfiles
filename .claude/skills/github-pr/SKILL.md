---
name: github-pr
description: This skill should be used when working with GitHub pull requests, reviewing PRs, creating PRs, checking PR status, viewing PR comments, analyzing CI failures, or using gh CLI commands. Emphasizes token-efficient patterns using filters, file buffers, and targeted queries.
---

# GitHub Pull Request Operations

Use `gh` CLI for all GitHub PR operations. Minimize context usage through targeted queries, file buffers for large outputs, and grep-friendly formats.

## Core Principles

1. **Filter at source** - Use `--json` with specific fields, not full responses
2. **Buffer large outputs** - Write to `/tmp/` then grep, don't load into context
3. **Batch queries** - One `gh api` call vs multiple `gh pr` calls
4. **Structured output** - Use `--json` + `--jq` for precise extraction

## Essential Patterns

### Viewing PR Information

```bash
# Minimal PR overview (token-efficient)
gh pr view <number> --json title,state,author,additions,deletions,changedFiles

# PR with review status
gh pr view <number> --json title,state,reviewDecision,reviews --jq '{
  title: .title,
  state: .state,
  decision: .reviewDecision,
  reviewers: [.reviews[].author.login] | unique
}'

# Just the PR body (for context)
gh pr view <number> --json body --jq '.body'
```

### Listing PRs (Filtered)

```bash
# My open PRs only
gh pr list --author @me --state open --json number,title,updatedAt

# PRs needing my review
gh pr list --search "review-requested:@me" --json number,title,author

# Recently updated (last 7 days)
gh pr list --search "updated:>$(date -v-7d +%Y-%m-%d)" --limit 10
```

### PR Diff (Buffer Pattern)

```bash
# Write diff to file, grep as needed
gh pr diff <number> > /tmp/pr-diff.patch
grep -n "TODO\|FIXME\|XXX" /tmp/pr-diff.patch

# Diff for specific file only
gh pr diff <number> -- path/to/file.ts

# Stat summary (no content)
gh pr diff <number> --stat
```

### PR Files Changed

```bash
# List files only (not content)
gh pr view <number> --json files --jq '.files[].path'

# Files with change stats
gh pr view <number> --json files --jq '.files[] | "\(.path)\t+\(.additions)\t-\(.deletions)"'

# Filter to specific extension
gh pr view <number> --json files --jq '[.files[].path | select(endswith(".ts"))]'
```

### Comments and Reviews

```bash
# Write comments to buffer for searching
gh pr view <number> --comments > /tmp/pr-comments.txt
grep -i "bug\|issue\|concern" /tmp/pr-comments.txt

# Review comments only (via API for more control)
gh api repos/{owner}/{repo}/pulls/<number>/comments \
  --jq '.[] | "\(.path):\(.line) - \(.body | split("\n")[0])"'

# Latest review summary
gh pr view <number> --json reviews --jq '.reviews[-3:] | .[] | "\(.author.login): \(.state)"'
```

### CI/Check Status

```bash
# Check status summary
gh pr checks <number>

# Failed checks only
gh pr checks <number> --json name,state,conclusion \
  --jq '.[] | select(.conclusion == "failure")'

# Get specific check logs (buffer for grep)
gh run view <run-id> --log > /tmp/ci-log.txt
grep -A5 "error\|failed\|Error" /tmp/ci-log.txt
```

## Creating PRs

### Basic PR Creation

```bash
# Create with inline body
gh pr create --title "feat: add feature" --body "Description here"

# Create from template (preferred for longer descriptions)
cat > /tmp/pr-body.md << 'EOF'
## Summary
Brief description

## Changes
- Change 1
- Change 2

## Test Plan
- [ ] Tests pass
EOF
gh pr create --title "feat: add feature" --body-file /tmp/pr-body.md
```

### PR Targeting

```bash
# Target specific base branch
gh pr create --base develop --title "feat: feature"

# Draft PR
gh pr create --draft --title "WIP: feature"

# With reviewers
gh pr create --title "feat: feature" --reviewer user1,user2
```

## Updating PRs

```bash
# Update title/body
gh pr edit <number> --title "new title"
gh pr edit <number> --body-file /tmp/updated-body.md

# Add reviewers
gh pr edit <number> --add-reviewer user1,user2

# Add labels
gh pr edit <number> --add-label "needs-review"

# Convert draft to ready
gh pr ready <number>
```

## gh api for Advanced Queries

### When to Use gh api

- Complex queries needing GraphQL
- Batch operations
- Data not exposed by `gh pr`
- Custom filtering

### Common API Patterns

```bash
# PR timeline (all events)
gh api repos/{owner}/{repo}/issues/<number>/timeline \
  --jq '.[] | select(.event) | "\(.event): \(.actor.login // "system")"'

# Check if PR is mergeable
gh api repos/{owner}/{repo}/pulls/<number> --jq '.mergeable_state'

# Get PR review threads (for addressing comments)
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 50) {
          nodes {
            isResolved
            path
            line
            comments(first: 1) {
              nodes { body author { login } }
            }
          }
        }
      }
    }
  }
' -f owner=OWNER -f repo=REPO -F pr=NUMBER \
  --jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)'
```

## Token Optimization Patterns

### Pattern 1: File Buffer + Grep

```bash
# Instead of loading full diff into context
gh pr diff 123 > /tmp/diff.patch
# Then grep for what you need
grep -B2 -A2 "functionName" /tmp/diff.patch
```

### Pattern 2: Precise JSON Fields

```bash
# BAD: fetches everything
gh pr view 123

# GOOD: only what's needed
gh pr view 123 --json title,state,mergeable
```

### Pattern 3: jq Filtering

```bash
# Extract specific nested data
gh pr view 123 --json reviews --jq '
  .reviews
  | group_by(.author.login)
  | map({user: .[0].author.login, latest: .[-1].state})
'
```

### Pattern 4: Count Instead of List

```bash
# When you need counts, not items
gh pr list --state open --json number --jq 'length'
gh pr view 123 --json comments --jq '.comments | length'
```

## Common Workflows

### Review a PR

```bash
# 1. Get overview
gh pr view <number> --json title,body,author,changedFiles,additions,deletions

# 2. See files changed
gh pr view <number> --json files --jq '.files[].path'

# 3. Get diff to file, review specific areas
gh pr diff <number> > /tmp/review.patch
# Grep for patterns of interest

# 4. Check CI status
gh pr checks <number>

# 5. Submit review
gh pr review <number> --approve --body "LGTM"
# or
gh pr review <number> --request-changes --body "See comments"
```

### Debug CI Failure

```bash
# 1. Get failed check info
gh pr checks <number> --json name,conclusion,detailsUrl \
  --jq '.[] | select(.conclusion == "failure")'

# 2. Get run ID from checks
gh run list --branch <pr-branch> --limit 5

# 3. Download logs to buffer
gh run view <run-id> --log > /tmp/ci.log

# 4. Search for errors
grep -n "error\|Error\|FAILED" /tmp/ci.log | head -50
```

### Respond to Review Comments

```bash
# 1. Get unresolved threads
gh api graphql -f query='...' # (see API patterns above)

# 2. View specific file context
gh pr diff <number> -- path/to/file.ts | head -100

# 3. Reply to comment (via web or push fix)
```

## Quick Reference

| Task | Command |
|------|---------|
| View PR summary | `gh pr view N --json title,state,author` |
| List my PRs | `gh pr list --author @me` |
| PR diff to file | `gh pr diff N > /tmp/diff.patch` |
| Files changed | `gh pr view N --json files --jq '.files[].path'` |
| Check status | `gh pr checks N` |
| Create PR | `gh pr create --title "..." --body-file /tmp/body.md` |
| Approve | `gh pr review N --approve` |
| Merge | `gh pr merge N --squash` |

## Progressive Context

- For `gh api` GraphQL queries: see `references/api-patterns.md`
- For PR analysis scripts: see `scripts/` directory
