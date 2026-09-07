# `pr-threads.py` Source

This is the **single shared implementation** for viewing and aggregating
live PR review threads — `/code:review` and `github:pr-ship` both call it
instead of each hand-rolling their own GraphQL/jq. If this file and
`~/.claude/scripts/pr-threads.py` diverge, treat this file as the source
of truth and re-sync the installed copy.

```python
#!/usr/bin/env python3
"""
pr-threads — single CLI for all GitHub PR review thread operations.

  pr-threads.py fetch   --owner ORG --repo REPO --pr N [--out FILE] [--hostname HOST]
  pr-threads.py reply   --owner ORG --repo REPO --pr N --comment-id DBID --body TEXT [--hostname HOST]
  pr-threads.py resolve --thread-id ID [ID ...] [--hostname HOST]
  pr-threads.py check   --owner ORG --repo REPO --pr N [--hostname HOST]
  pr-threads.py summary --owner ORG --repo REPO --pr N [--since ISO8601] [--hostname HOST]

`summary` is the shared staleness/aggregation check: it's the single source of
truth for "are there live review threads a prior check might have missed" —
used by the code-review skill (to fold live threads into a diff review) and by
the pr-ship gate loop (to tell whether Gate 3 is still actually green instead
of trusting a state file written before new comments landed). Pass --since the
timestamp of the last check (e.g. the last push or the state file's last Gate
3 verification) to get an explicit new_since_count instead of eyeballing
thread counts.

All gh calls use subprocess list args — body text with quotes, newlines,
or special characters is handled correctly without any shell escaping.
"""
import argparse, json, subprocess, sys


def gh(*args, hostname=None):
    cmd = ["gh"] + list(args)
    if hostname:
        cmd += ["--hostname", hostname]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"gh error: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return r.stdout.strip()


def fetch(owner, repo, pr, out, hostname):
    query = """
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          path
          line
          comments(first: 20) {
            nodes { id databaseId body author { login } createdAt }
          }
        }
      }
    }
  }
}
"""
    raw = gh("api", "graphql",
             "-f", f"query={query}",
             "-f", f"owner={owner}",
             "-f", f"repo={repo}",
             "-F", f"pr={pr}",
             hostname=hostname)
    data = json.loads(raw)
    threads = data["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    open_threads = [t for t in threads if not t["isResolved"]]

    output = json.dumps(open_threads, indent=2)
    if out:
        with open(out, "w") as f:
            f.write(output)
        print(f"Fetched {len(threads)} threads, {len(open_threads)} unresolved → {out}")
    else:
        print(output)

    for t in open_threads:
        first = t["comments"]["nodes"][0]
        print(f"  [{t['id'][:30]}] {t['path']}:{t.get('line','?')} "
              f"@{first['author']['login']} (dbId={first['databaseId']}): "
              f"{first['body'][:80]}", file=sys.stderr)


def reply(owner, repo, pr, comment_id, body, hostname):
    raw = gh("api",
             f"repos/{owner}/{repo}/pulls/{pr}/comments/{comment_id}/replies",
             "-f", f"body={body}",
             hostname=hostname)
    resp = json.loads(raw)
    print(f"Replied (id={resp['id']})")


def resolve(thread_ids, hostname):
    mutation = "mutation($id: ID!) { resolveReviewThread(input: {threadId: $id}) { thread { isResolved } } }"
    for tid in thread_ids:
        raw = gh("api", "graphql", "-f", f"query={mutation}", "-f", f"id={tid}", hostname=hostname)
        data = json.loads(raw)
        resolved = data["data"]["resolveReviewThread"]["thread"]["isResolved"]
        print(f"{'✓' if resolved else '✗'} {tid[:30]}  resolved={resolved}")


def summary(owner, repo, pr, since, hostname):
    query = """
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          path
          line
          comments(first: 20) {
            nodes { databaseId body author { login } createdAt }
          }
        }
      }
    }
  }
}
"""
    raw = gh("api", "graphql",
             "-f", f"query={query}",
             "-f", f"owner={owner}",
             "-f", f"repo={repo}",
             "-F", f"pr={pr}",
             hostname=hostname)
    data = json.loads(raw)
    threads = data["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    unresolved = [t for t in threads if not t["isResolved"]]

    def latest_comment_at(t):
        return max(c["createdAt"] for c in t["comments"]["nodes"])

    newest_at = max((latest_comment_at(t) for t in unresolved), default=None)
    new_since = None
    if since:
        new_since = [t for t in unresolved if latest_comment_at(t) > since]

    result = {
        "pr": pr,
        "total_threads": len(threads),
        "unresolved_count": len(unresolved),
        "resolved_count": len(threads) - len(unresolved),
        "newest_unresolved_comment_at": newest_at,
        "unresolved": [
            {
                "thread_id": t["id"],
                "path": t["path"],
                "line": t.get("line"),
                "author": t["comments"]["nodes"][0]["author"]["login"],
                "database_id": t["comments"]["nodes"][0]["databaseId"],
                "created_at": t["comments"]["nodes"][0]["createdAt"],
                "latest_comment_at": latest_comment_at(t),
                "body_preview": t["comments"]["nodes"][0]["body"][:120],
            }
            for t in unresolved
        ],
    }
    if since is not None:
        result["since"] = since
        result["new_since_count"] = len(new_since)

    print(json.dumps(result, indent=2))


def check(owner, repo, pr, hostname):
    repo_arg = f"{hostname}/{owner}/{repo}" if hostname else f"{owner}/{repo}"
    raw = gh("pr", "view", str(pr),
             "-R", repo_arg,
             "--json", "mergeable,mergeStateStatus,baseRefName")
    data = json.loads(raw)
    print(json.dumps(data, indent=2))


def main():
    p = argparse.ArgumentParser(description="GitHub PR review thread operations")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch")
    f.add_argument("--owner", required=True)
    f.add_argument("--repo", required=True)
    f.add_argument("--pr", required=True, type=int)
    f.add_argument("--out", help="output file path (default: stdout)")
    f.add_argument("--hostname", default=None)

    r = sub.add_parser("reply")
    r.add_argument("--owner", required=True)
    r.add_argument("--repo", required=True)
    r.add_argument("--pr", required=True)
    r.add_argument("--comment-id", required=True, dest="comment_id")
    r.add_argument("--body", required=True)
    r.add_argument("--hostname", default=None)

    res = sub.add_parser("resolve")
    res.add_argument("--thread-id", nargs="+", required=True, dest="thread_ids")
    res.add_argument("--hostname", default=None)

    c = sub.add_parser("check")
    c.add_argument("--owner", required=True)
    c.add_argument("--repo", required=True)
    c.add_argument("--pr", required=True, type=int)
    c.add_argument("--hostname", default=None)

    s = sub.add_parser("summary")
    s.add_argument("--owner", required=True)
    s.add_argument("--repo", required=True)
    s.add_argument("--pr", required=True, type=int)
    s.add_argument("--since", default=None, help="ISO8601 timestamp; reports new_since_count")
    s.add_argument("--hostname", default=None)

    args = p.parse_args()

    if args.cmd == "fetch":
        fetch(args.owner, args.repo, args.pr, args.out, args.hostname)
    elif args.cmd == "reply":
        reply(args.owner, args.repo, args.pr, args.comment_id, args.body, args.hostname)
    elif args.cmd == "resolve":
        resolve(args.thread_ids, args.hostname)
    elif args.cmd == "check":
        check(args.owner, args.repo, args.pr, args.hostname)
    elif args.cmd == "summary":
        summary(args.owner, args.repo, args.pr, args.since, args.hostname)


if __name__ == "__main__":
    main()
```

**Versioning**: bump a `# v2` style comment or just diff against the block above if you ever suspect the installed copy has drifted — check with `diff <(sed -n '/^```python/,/^```/p' references/pr-threads-script.md | sed '1d;$d') ~/.claude/scripts/pr-threads.py`.
