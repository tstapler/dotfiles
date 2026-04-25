#!/usr/bin/env python3
"""
Resolve display names to GitHub handles within a GitHub org.

Strategy:
1. Search GitHub users by name (search/users?q={name}+in:name)
2. Cross-check each candidate against org membership
3. Try common company naming heuristics if search fails
4. Cache org member list to /tmp to avoid repeated API calls

Usage:
  python3 resolve_members.py --org my-org --names "Tyler Stapler"
  python3 resolve_members.py --org my-org --names "Display Name" --refresh-cache
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import date
from typing import Optional


def gh_api(endpoint: str, extra_args: list[str] | None = None) -> dict | list | None:
    cmd = ["gh", "api", endpoint]
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def gh_api_paginated(endpoint: str) -> list:
    result = subprocess.run(
        ["gh", "api", endpoint, "--paginate", "--jq", ".[].login"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def get_org_members(org: str, refresh: bool = False) -> set[str]:
    cache_path = f"/tmp/{org}-members-{date.today()}.json"
    if not refresh and os.path.exists(cache_path):
        with open(cache_path) as f:
            return set(json.load(f))
    print(f"Fetching org members for {org} (caching to {cache_path})...", file=sys.stderr)
    members = gh_api_paginated(f"/orgs/{org}/members")
    with open(cache_path, "w") as f:
        json.dump(members, f)
    return set(members)


def is_org_member(org: str, login: str, members: set[str]) -> bool:
    return login.lower() in {m.lower() for m in members}


def search_by_name(name: str) -> list[dict]:
    parts = name.strip().split()
    query = "+".join(parts) + "+in:name"
    data = gh_api(f"search/users?q={query}&per_page=10")
    if not data or "items" not in data:
        return []
    return [{"login": item["login"], "name": item.get("name", "")} for item in data["items"]]


def company_naming_heuristics(name: str) -> list[str]:
    """
    Generate candidate logins from common company GitHub naming conventions.
    Customize these patterns to match your org's conventions.
    """
    parts = name.lower().split()
    if len(parts) < 2:
        return []
    first, last = parts[0], parts[-1]
    return [
        f"{last}-org",
        f"{first}-{last}",
        f"{first}{last}",
        f"{first[0]}{last}",
        f"{first}.{last}",
        f"{first}_{last}",
    ]


def resolve_name(name: str, org: str, members: set[str]) -> dict:
    # 1. Search GitHub by name
    candidates = search_by_name(name)
    org_matches = [c for c in candidates if is_org_member(org, c["login"], members)]

    if len(org_matches) == 1:
        return {"input": name, "login": org_matches[0]["login"], "display_name": org_matches[0]["name"], "method": "search"}

    if len(org_matches) > 1:
        # Return all candidates for human disambiguation
        return {"input": name, "login": None, "candidates": org_matches, "method": "ambiguous"}

    # 2. Try company naming heuristics
    for candidate_login in company_naming_heuristics(name):
        if is_org_member(org, candidate_login, members):
            profile = gh_api(f"/users/{candidate_login}")
            display = profile.get("name", "") if profile else ""
            return {"input": name, "login": candidate_login, "display_name": display, "method": "heuristic"}

    # 3. Return unresolved with best guesses
    return {"input": name, "login": None, "candidates": candidates[:3], "method": "unresolved"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve display names to GitHub handles in an org")
    parser.add_argument("--org", required=True, help="GitHub org name")
    parser.add_argument("--names", nargs="+", required=True)
    parser.add_argument("--refresh-cache", action="store_true")
    parser.add_argument("--output", help="Write JSON results to file instead of stdout")
    args = parser.parse_args()

    members = get_org_members(args.org, refresh=args.refresh_cache)
    print(f"Loaded {len(members)} org members", file=sys.stderr)

    results = []
    for name in args.names:
        result = resolve_name(name, args.org, members)
        results.append(result)
        status = f"✓ {result['login']}" if result.get("login") else f"? unresolved ({len(result.get('candidates', []))} candidates)"
        print(f"  {name}: {status}", file=sys.stderr)

    output = json.dumps(results, indent=2)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
