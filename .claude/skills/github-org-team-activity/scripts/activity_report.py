#!/usr/bin/env python3
"""
Fetch comprehensive GitHub activity for a list of handles in an org.

Data sources:
  - GraphQL contributionsCollection: actual commits, actual reviews given, PR review list
  - gh search prs: authored PRs (org-scoped)
  - Individual PR API: additions, deletions, changed_files per PR

Usage:
  python3 activity_report.py --org my-org --logins user1 user2 --since 2026-03-25
  python3 activity_report.py --org my-org --logins user1 --since 2026-01-01 --output /tmp/report.json
"""

import argparse
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any


def run_graphql(query: str) -> dict | None:
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def gh_search_prs(org: str, login: str, since: str, limit: int = 100) -> list[dict]:
    result = subprocess.run(
        [
            "gh", "search", "prs",
            "--owner", org,
            "--author", login,
            "--created", f">={since}",
            "--limit", str(limit),
            "--json", "title,repository,state,createdAt,closedAt,url,number",
        ],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  Warning: pr search failed for {login}: {result.stderr.strip()}", file=sys.stderr)
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def fetch_pr_size(owner: str, repo: str, number: int) -> dict:
    result = subprocess.run(
        ["gh", "api", f"/repos/{owner}/{repo}/pulls/{number}",
         "--jq", "{additions, deletions, changed_files}"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return {"additions": None, "deletions": None, "changed_files": None}
    try:
        data = json.loads(result.stdout)
        # Individual PR endpoint returns additions/deletions; list endpoint returns null
        return data
    except json.JSONDecodeError:
        return {"additions": None, "deletions": None, "changed_files": None}


def enrich_prs_with_size(prs: list[dict], org: str) -> list[dict]:
    """Add additions/deletions/changed_files to each PR."""
    enriched = []
    for pr in prs:
        repo = pr.get("repository", {}).get("name", "")
        number = pr.get("number")
        if repo and number:
            size = fetch_pr_size(org, repo, number)
            pr = {**pr, **size}
        enriched.append(pr)
    return enriched


def fetch_contributions(login: str, since: str, org: str) -> dict:
    """
    Fetch contributions via GraphQL contributionsCollection.
    Returns commits by repo (filtered to org), actual reviews, totals.
    """
    since_iso = f"{since}T00:00:00Z"
    today = datetime.now(timezone.utc)
    today_iso = today.strftime("%Y-%m-%dT%H:%M:%SZ")
    today_date = today.strftime("%Y-%m-%d")

    query = f"""
    {{
      user(login: "{login}") {{
        name
        contributionsCollection(from: "{since_iso}", to: "{today_iso}") {{
          totalCommitContributions
          totalPullRequestReviewContributions
          totalPullRequestContributions
          commitContributionsByRepository(maxRepositories: 25) {{
            repository {{
              nameWithOwner
              name
            }}
            contributions {{
              totalCount
            }}
          }}
          pullRequestReviewContributions(first: 50) {{
            nodes {{
              pullRequest {{
                title
                number
                url
                repository {{
                  nameWithOwner
                  name
                  owner {{ login }}
                }}
              }}
              occurredAt
            }}
          }}
        }}
      }}
    }}
    """

    data = run_graphql(query)
    if not data or not data.get("data", {}).get("user"):
        return {}

    user = data["data"]["user"]
    cc = user["contributionsCollection"]

    # Filter commit repos to this org only
    org_commits = [
        {
            "repo": r["repository"]["name"],
            "commits": r["contributions"]["totalCount"],
        }
        for r in cc["commitContributionsByRepository"]
        if r["repository"]["nameWithOwner"].startswith(f"{org}/")
    ]

    # Filter reviews to this org only
    org_reviews = [
        {
            "title": n["pullRequest"]["title"],
            "repo": n["pullRequest"]["repository"]["name"],
            "url": n["pullRequest"]["url"],
            "reviewed_at": n["occurredAt"],
        }
        for n in cc["pullRequestReviewContributions"]["nodes"]
        if n["pullRequest"]["repository"]["owner"]["login"] == org
    ]

    # Commit total for this org only
    org_commit_total = sum(r["commits"] for r in org_commits)

    return {
        "display_name": user.get("name") or login,
        "total_commits_in_org": org_commit_total,
        "total_commits_all_orgs": cc["totalCommitContributions"],
        "total_reviews_given": len(org_reviews),
        "total_prs": cc["totalPullRequestContributions"],
        "commits_by_repo": org_commits,
        "reviews_given": org_reviews,
        "until": today_date,
    }


def count_by_state(prs: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for pr in prs:
        counts[pr.get("state", "unknown")] += 1
    return dict(counts)


def group_by_repo(prs: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for pr in prs:
        repo = pr.get("repository", {}).get("name", "unknown")
        grouped[repo].append(pr)
    return dict(grouped)


def summarize_person(login: str, org: str, since: str, include_pr_sizes: bool = True) -> dict[str, Any]:
    print(f"  [{login}] fetching contributions via GraphQL...", file=sys.stderr)
    contributions = fetch_contributions(login, since, org)

    print(f"  [{login}] fetching authored PRs...", file=sys.stderr)
    authored = gh_search_prs(org, login, since)

    if include_pr_sizes and authored:
        print(f"  [{login}] enriching {len(authored)} PRs with size data...", file=sys.stderr)
        authored = enrich_prs_with_size(authored, org)

    total_additions = sum(pr.get("additions") or 0 for pr in authored)
    total_deletions = sum(pr.get("deletions") or 0 for pr in authored)
    total_files = sum(pr.get("changed_files") or 0 for pr in authored)

    return {
        "login": login,
        "display_name": contributions.get("display_name", login),
        "org": org,
        "since": since,
        "until": contributions.get("until", "today"),
        "commits": {
            "total_in_org": contributions.get("total_commits_in_org", 0),
            "by_repo": contributions.get("commits_by_repo", []),
        },
        "authored_prs": {
            "total": len(authored),
            "by_state": count_by_state(authored),
            "total_additions": total_additions,
            "total_deletions": total_deletions,
            "total_files_changed": total_files,
            "by_repo": {
                repo: [
                    {
                        "title": pr["title"],
                        "state": pr["state"],
                        "url": pr["url"],
                        "created": pr["createdAt"],
                        "additions": pr.get("additions"),
                        "deletions": pr.get("deletions"),
                        "changed_files": pr.get("changed_files"),
                    }
                    for pr in prs
                ]
                for repo, prs in sorted(group_by_repo(authored).items(), key=lambda x: -len(x[1]))
            },
        },
        "reviews_given": {
            "total": contributions.get("total_reviews_given", 0),
            "prs": contributions.get("reviews_given", []),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize GitHub activity for org members")
    parser.add_argument("--org", required=True, help="GitHub org name")
    parser.add_argument("--logins", nargs="+", required=True, help="GitHub handles to report on")
    parser.add_argument("--since", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--no-pr-sizes", action="store_true", help="Skip PR size enrichment (faster)")
    parser.add_argument("--output", help="Write JSON to file (default: stdout)")
    args = parser.parse_args()

    members_hash = hashlib.sha256(",".join(sorted(args.logins)).encode()).hexdigest()[:8]
    default_output = f"/tmp/{args.org}-{args.since}-{members_hash}-activity.json"
    output_path = args.output or default_output

    print(f"Fetching activity in {args.org} since {args.since}...", file=sys.stderr)
    results = [
        summarize_person(login, args.org, args.since, include_pr_sizes=not args.no_pr_sizes)
        for login in args.logins
    ]

    output = json.dumps(results, indent=2)
    with open(output_path, "w") as f:
        f.write(output)
    print(f"Report written to {output_path}", file=sys.stderr)
    print(output_path)


if __name__ == "__main__":
    main()
