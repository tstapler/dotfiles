#!/usr/bin/env python3
"""
Format a saved activity_report.py JSON file into a readable markdown summary.

Usage:
  python3 format_report.py /tmp/activity.json
  python3 format_report.py /tmp/activity.json --top-repos 5
  cat /tmp/activity.json | python3 format_report.py -
"""

import argparse
import json
import sys


def format_person(p: dict, top_repos: int) -> str:
    lines = []
    name = p["display_name"]
    login = p["login"]
    commits = p["commits"]["total_in_org"]
    prs = p["authored_prs"]
    reviews = p["reviews_given"]

    states = prs["by_state"]
    merged = states.get("merged", 0)
    open_ = states.get("open", 0)

    lines.append(f"### {name} (@{login})")
    lines.append(
        f"**Commits:** {commits}  ·  "
        f"**PRs:** {prs['total']} ({merged} merged, {open_} open)  ·  "
        f"**Reviews given:** {reviews['total']}"
    )

    if prs["total"] > 0:
        add = prs["total_additions"]
        dl = prs["total_deletions"]
        files = prs["total_files_changed"]
        lines.append(f"**PR impact:** +{add:,} / -{dl:,} lines, {files:,} files")
        lines.append("")
        lines.append("**What they worked on:**")
        for i, (repo, items) in enumerate(prs["by_repo"].items()):
            if i >= top_repos:
                remaining = len(prs["by_repo"]) - top_repos
                lines.append(f"- _...and {remaining} more repo(s)_")
                break
            repo_add = sum(item.get("additions") or 0 for item in items)
            repo_del = sum(item.get("deletions") or 0 for item in items)
            sample = items[0]["title"][:70] if items else ""
            lines.append(
                f'- [{repo}] {len(items)} PR(s)  +{repo_add:,}/-{repo_del:,} lines  — "{sample}"'
            )

    if commits > 0:
        by_repo = p["commits"]["by_repo"]
        top = ", ".join(f"{r['repo']} ({r['commits']}c)" for r in by_repo[:6])
        extra = f" + {len(by_repo) - 6} more" if len(by_repo) > 6 else ""
        lines.append(f"**Commits by repo:** {top}{extra}")

    if reviews["total"] > 0:
        review_repos = list({r["repo"] for r in reviews["prs"]})
        repos_str = ", ".join(review_repos[:4])
        extra = f" + {len(review_repos) - 4} more" if len(review_repos) > 4 else ""
        lines.append(
            f"**Reviews given:** {reviews['total']} across "
            f"{len(review_repos)} repo(s) ({repos_str}{extra})"
        )

    if prs["total"] == 0 and commits == 0 and reviews["total"] == 0:
        lines.append("_No contributions recorded in this org during the period._")

    return "\n".join(lines)


def format_report(data: list[dict], top_repos: int) -> str:
    if not data:
        return "_No data._"

    p0 = data[0]
    org = p0.get("org", "unknown-org")
    since = p0.get("since", "?")
    until = p0.get("until", "today")

    sections = [f"## Activity Report: {org} · {since} → {until}", ""]

    for p in data:
        sections.append("---")
        sections.append(format_person(p, top_repos))
        sections.append("")

    return "\n".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser(description="Format an activity_report.py JSON file")
    parser.add_argument("input", help="Path to JSON file, or - for stdin")
    parser.add_argument("--top-repos", type=int, default=10,
                        help="Max repos to show per person (default: 10)")
    args = parser.parse_args()

    if args.input == "-":
        data = json.load(sys.stdin)
    else:
        with open(args.input) as f:
            data = json.load(f)

    print(format_report(data, top_repos=args.top_repos))


if __name__ == "__main__":
    main()
