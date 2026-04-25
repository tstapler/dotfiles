---
name: github-org-team-activity
description: Look up GitHub activity for people in a GitHub org by display name or handle. Summarizes PRs opened/merged/reviewed, repos touched, and provides a narrative of what each person worked on over a specified timeframe. Use when asked what teammates have been working on, for sprint reviews, team status reports, or manager 1:1 prep.
---

# GitHub Org Team Activity

Summarize what one or more people have been working on in a GitHub org. Supports lookup by display name (e.g. "Jane Smith") or GitHub handle (e.g. "jsmith-org").

## Step 0: Determine the Org and Current User

Always start by discovering context from the local `gh` config:

```bash
# Who is authenticated
gh api /user --jq '{login, name}'

# What orgs they belong to
gh api /user/orgs --jq '.[].login'
```

**Org selection:**
- **1 org** → use it
- **Multiple orgs** → ask the user which one
- **0 orgs** → ask for the org name explicitly

Never assume or hardcode an org.

## Step 1: Resolve Names → GitHub Handles

Run the member resolution script:

```bash
python3 ~/.claude/skills/github-org-team-activity/scripts/resolve_members.py \
  --org {org} \
  --names "Jane Smith" "Alex Johnson"
```

If names are already handles, skip to Step 2.

**Manual fallback** when script resolution fails:
```bash
# 1. Search GitHub by name
gh api "search/users?q={FirstName}+{LastName}+in:name" --jq '.items[] | {login, name}'

# 2. Check each candidate is in the org (204 = yes, 404 = no)
gh api /orgs/{org}/members/{login} -i 2>&1 | grep "HTTP/"

# 3. Try common company naming patterns if search fails
#    {last}-{suffix}, {first}{last}At{Company}, {first}-{last}-{suffix}
```

## Step 2: Fetch Activity for Each Handle

Buffer all output to `/tmp` to avoid context bloat:

```bash
# PRs authored
gh search prs \
  --owner {org} \
  --author {login} \
  --created ">=2026-03-01" \
  --limit 100 \
  --json title,repository,state,createdAt,closedAt,url \
  > /tmp/prs-{login}.json

# PRs where they were requested as reviewer
gh search prs \
  --owner {org} \
  --review-requested {login} \
  --created ">=2026-03-01" \
  --limit 50 \
  --json title,repository,state,createdAt,url \
  > /tmp/reviews-{login}.json
```

Or use the activity script for multiple people:

```bash
python3 ~/.claude/skills/github-org-team-activity/scripts/activity_report.py \
  --org {org} \
  --logins jsmith-org alexjohnson \
  --since 2026-03-01 \
  --output /tmp/activity-report.json
```

## Step 3: Format the Report

Always generate output from the saved JSON using the formatter script — never inline the formatting:

```bash
python3 ~/.claude/skills/github-org-team-activity/scripts/format_report.py /tmp/activity-report.json

# Limit repos shown per person
python3 ~/.claude/skills/github-org-team-activity/scripts/format_report.py /tmp/activity-report.json --top-repos 5
```

**Output format — always opens with a timeframe header, then one block per person:**
```
## Activity Report: {org} · {since} → {until}

---

### {Display Name} (@{login})

**Commits:** {N} · **PRs:** {N opened} ({N merged}, {N open}) · **Reviews given:** {N}
**PR impact:** +{additions} / -{deletions} lines, {files} files

**What they worked on:**
- [repo-a] Description of theme — N PRs, +X/-Y lines
- [repo-b] Description of theme — N PRs, +X/-Y lines

**Commits by repo:** repo-a (N), repo-b (N)
```

## Key Notes

- **Date filter**: `--created ">=YYYY-MM-DD"` on `gh search prs`
- **State filter**: `--state merged|open|closed`
- **Reviewed PRs**: `--review-requested` finds PRs where the person was requested as reviewer. For actually completed reviews, use GraphQL (see reference.md)
- **Commits**: Not searchable via `gh search`; use `gh api /repos/{owner}/{repo}/commits?author={login}` per-repo if needed
- **Large orgs**: Always use cached member list at `/tmp/{org}-members-{date}.json` — avoids 900+ API calls per run

## Timeframe Reference

| When asked...          | `--created` value                         |
|------------------------|-------------------------------------------|
| "this week"            | `>=YYYY-MM-DD` (Monday's date)            |
| "last 30 days"         | `>=$(date -v-30d +%Y-%m-%d)`             |
| "this quarter"         | `>=YYYY-01-01` / `>=YYYY-04-01` etc.      |
| "last sprint" (2 wk)  | `>=$(date -v-14d +%Y-%m-%d)`             |
| no timeframe specified | Ask the user                              |

## Token Budget
- SKILL.md: ~700 tokens
- scripts/: loaded on demand only
