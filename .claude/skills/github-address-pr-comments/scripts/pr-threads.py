#!/usr/bin/env python3
"""
pr-threads — single CLI for all GitHub PR review thread operations.

  pr-threads.py fetch     --owner ORG --repo REPO --pr N [--out FILE] [--auto-react] [--hostname HOST]
  pr-threads.py reply     --owner ORG --repo REPO --pr N --comment-id DBID --body TEXT [--hostname HOST]
  pr-threads.py react     --owner ORG --repo REPO --comment-id DBID [--content eyes] [--hostname HOST]
  pr-threads.py resolve   --thread-id ID [ID ...] [--hostname HOST]
  pr-threads.py check     --owner ORG --repo REPO --pr N [--hostname HOST]
  pr-threads.py summary   --owner ORG --repo REPO --pr N [--since ISO8601] [--hostname HOST]
  pr-threads.py checkruns --owner ORG --repo REPO --pr N [--hostname HOST]

`summary` is the shared staleness/aggregation check: it's the single source of
truth for "are there live review threads a prior check might have missed" —
used by the code-review skill (to fold live threads into a diff review) and by
the pr-ship gate loop (to tell whether Gate 3 is still actually green instead
of trusting a state file written before new comments landed). Pass --since the
timestamp of the last check (e.g. the last push or the state file's last Gate
3 verification) to get an explicit new_since_count instead of eyeballing
thread counts.

`checkruns` lists the check runs on the PR's head commit that did not succeed.
Bots such as bitbot report findings (mutation-testing gaps, risk assessments)
as a check run with conclusion "neutral": it never appears in reviewThreads and
does not fail the PR, so `gh pr checks` and a review-comments pass both miss it.

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


def login(comment):
    """Author login, or "ghost" when the account was deleted (GraphQL returns null)."""
    return (comment.get("author") or {}).get("login", "ghost")


def react(owner, repo, comment_id, content, hostname):
    raw = gh("api",
             f"repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions",
             "-f", f"content={content}",
             hostname=hostname)
    resp = json.loads(raw)
    print(f"Reacted with :{content}: to comment {comment_id} (id={resp['id']})")


def fetch(owner, repo, pr, out, auto_react, hostname):
    query = """
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviews(last: 10) {
        nodes {
          id
          author { login }
          state
          body
          createdAt
        }
      }
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          path
          line
          comments(first: 20) {
            nodes {
              id
              databaseId
              body
              author { login }
              createdAt
              reactions(first: 10) {
                nodes { content user { login } }
              }
            }
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
    pr_data = data["data"]["repository"]["pullRequest"]
    threads = pr_data["reviewThreads"]["nodes"]
    reviews = pr_data.get("reviews", {}).get("nodes", [])
    open_threads = [t for t in threads if not t["isResolved"]]

    copilot_reviews = [
        r for r in reviews
        if login(r) in ("copilot-pull-request-reviewer", "Copilot", "github-actions[bot]")
        and r.get("body") and ("Copilot review" in r["body"] or "ccr-overview" in r["body"])
    ]

    output = json.dumps(open_threads, indent=2)
    if out:
        with open(out, "w") as f:
            f.write(output)
        print(f"Fetched {len(threads)} threads, {len(open_threads)} unresolved "
              f"({len(copilot_reviews)} Copilot review reports) → {out}")
    else:
        print(output)

    if auto_react:
        for t in open_threads:
            first = t["comments"]["nodes"][0]
            db_id = first.get("databaseId")
            existing = [r.get("content") for r in first.get("reactions", {}).get("nodes", [])]
            if db_id and "EYES" not in existing and "eyes" not in existing:
                try:
                    react(owner, repo, db_id, "eyes", hostname)
                except Exception as e:
                    print(f"Failed to react to comment {db_id}: {e}", file=sys.stderr)

    for t in open_threads:
        first = t["comments"]["nodes"][0]
        print(f"  [{t['id'][:30]}] {t['path']}:{t.get('line','?')} "
              f"@{login(first)} (dbId={first['databaseId']}): "
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
                "author": login(t["comments"]["nodes"][0]),
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


# Conclusions that need no attention; every other completed conclusion (neutral, failure,
# cancelled, timed_out, action_required, stale, startup_failure) is reported.
OK_CONCLUSIONS = {"success", "skipped"}


def checkruns(owner, repo, pr, hostname):
    repo_arg = f"{hostname}/{owner}/{repo}" if hostname else f"{owner}/{repo}"
    head_sha = json.loads(gh("pr", "view", str(pr), "-R", repo_arg, "--json", "headRefOid"))["headRefOid"]
    # One JSON object per line: --paginate would otherwise concatenate whole pages.
    jq = ('.check_runs[] | {name, status, conclusion, details_url, app: .app.slug, '
          'title: .output.title, summary: (.output.summary // "")[0:300]}')
    raw = gh("api", "-X", "GET", f"repos/{owner}/{repo}/commits/{head_sha}/check-runs",
             "-F", "per_page=100", "--paginate", "--jq", jq,
             hostname=hostname)
    runs = [json.loads(line) for line in raw.splitlines() if line.strip()]
    pending = [r for r in runs if r["status"] != "completed"]
    non_success = [r for r in runs if r["status"] == "completed" and r["conclusion"] not in OK_CONCLUSIONS]
    print(json.dumps({
        "pr": pr,
        "head_sha": head_sha,
        "total": len(runs),
        "pending_count": len(pending),
        "non_success_count": len(non_success),
        "non_success": non_success,
    }, indent=2))


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

    def add_pr_args(sp):
        sp.add_argument("--owner", required=True)
        sp.add_argument("--repo", required=True)
        sp.add_argument("--pr", required=True, type=int)
        sp.add_argument("--hostname", default=None)

    f = sub.add_parser("fetch")
    add_pr_args(f)
    f.add_argument("--out", help="output file path (default: stdout)")
    f.add_argument("--auto-react", action="store_true", dest="auto_react",
                   help="react :eyes: to each unresolved thread's first comment")

    r = sub.add_parser("reply")
    add_pr_args(r)
    r.add_argument("--comment-id", required=True, dest="comment_id")
    r.add_argument("--body", required=True)

    re_ = sub.add_parser("react")
    re_.add_argument("--owner", required=True)
    re_.add_argument("--repo", required=True)
    re_.add_argument("--comment-id", required=True, dest="comment_id")
    re_.add_argument("--content", default="eyes")
    re_.add_argument("--hostname", default=None)

    res = sub.add_parser("resolve")
    res.add_argument("--thread-id", nargs="+", required=True, dest="thread_ids")
    res.add_argument("--hostname", default=None)

    add_pr_args(sub.add_parser("check"))

    s = sub.add_parser("summary")
    add_pr_args(s)
    s.add_argument("--since", default=None, help="ISO8601 timestamp; reports new_since_count")

    add_pr_args(sub.add_parser("checkruns"))

    args = p.parse_args()

    if args.cmd == "fetch":
        fetch(args.owner, args.repo, args.pr, args.out, args.auto_react, args.hostname)
    elif args.cmd == "reply":
        reply(args.owner, args.repo, args.pr, args.comment_id, args.body, args.hostname)
    elif args.cmd == "react":
        react(args.owner, args.repo, args.comment_id, args.content, args.hostname)
    elif args.cmd == "resolve":
        resolve(args.thread_ids, args.hostname)
    elif args.cmd == "check":
        check(args.owner, args.repo, args.pr, args.hostname)
    elif args.cmd == "summary":
        summary(args.owner, args.repo, args.pr, args.since, args.hostname)
    elif args.cmd == "checkruns":
        checkruns(args.owner, args.repo, args.pr, args.hostname)


if __name__ == "__main__":
    main()
