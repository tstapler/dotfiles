---
name: github-address-pr-comments
description: Systematically address all open GitHub PR review comments — fix code or decline with reasoning, reply to every thread, resolve when done
---

# Address PR Review Comments

Load all unresolved review threads for a PR, then for each: decide whether to fix or decline, implement fixes when accepting, reply with a clear response, and resolve the thread. No comment goes unacknowledged.

## Step 0: Bootstrap — Install `pr-threads.py`

The skill uses a single permanent helper script at `~/.claude/scripts/pr-threads.py`.
Check if it exists; if not, write it from the embedded source below, then `chmod +x` it.
Once installed, all subsequent steps call `python3 ~/.claude/scripts/pr-threads.py <subcommand>` —
pre-approved by `Bash(python3:*)` in settings, no prompts needed.

```bash
[ -f ~/.claude/scripts/pr-threads.py ] && echo "installed" || echo "missing — write it"
```

If missing, write the file:

```python
#!/usr/bin/env python3
"""
pr-threads — single CLI for all GitHub PR review thread operations.

  pr-threads.py fetch   --owner ORG --repo REPO --pr N [--out FILE]
  pr-threads.py reply   --owner ORG --repo REPO --pr N --comment-id DBID --body TEXT
  pr-threads.py resolve --thread-id ID [ID ...]
  pr-threads.py check   --owner ORG --repo REPO --pr N

All gh calls use subprocess list args — body text with quotes, newlines,
or special characters is handled correctly without any shell escaping.
"""
import argparse, json, subprocess, sys


def gh(*args):
    r = subprocess.run(["gh"] + list(args), capture_output=True, text=True)
    if r.returncode != 0:
        print(f"gh error: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return r.stdout.strip()


def fetch(owner, repo, pr, out):
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
             "-F", f"pr={pr}")
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


def reply(owner, repo, pr, comment_id, body):
    raw = gh("api",
             f"repos/{owner}/{repo}/pulls/{pr}/comments/{comment_id}/replies",
             "-f", f"body={body}")
    resp = json.loads(raw)
    print(f"Replied (id={resp['id']})")


def resolve(thread_ids):
    mutation = "mutation($id: ID!) { resolveReviewThread(input: {threadId: $id}) { thread { isResolved } } }"
    for tid in thread_ids:
        raw = gh("api", "graphql", "-f", f"query={mutation}", "-f", f"id={tid}")
        data = json.loads(raw)
        resolved = data["data"]["resolveReviewThread"]["thread"]["isResolved"]
        print(f"{'✓' if resolved else '✗'} {tid[:30]}  resolved={resolved}")


def check(owner, repo, pr):
    raw = gh("pr", "view", str(pr),
             "-R", f"{owner}/{repo}",
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

    r = sub.add_parser("reply")
    r.add_argument("--owner", required=True)
    r.add_argument("--repo", required=True)
    r.add_argument("--pr", required=True)
    r.add_argument("--comment-id", required=True, dest="comment_id")
    r.add_argument("--body", required=True)

    res = sub.add_parser("resolve")
    res.add_argument("--thread-id", nargs="+", required=True, dest="thread_ids")

    c = sub.add_parser("check")
    c.add_argument("--owner", required=True)
    c.add_argument("--repo", required=True)
    c.add_argument("--pr", required=True, type=int)

    args = p.parse_args()

    if args.cmd == "fetch":
        fetch(args.owner, args.repo, args.pr, args.out)
    elif args.cmd == "reply":
        reply(args.owner, args.repo, args.pr, args.comment_id, args.body)
    elif args.cmd == "resolve":
        resolve(args.thread_ids)
    elif args.cmd == "check":
        check(args.owner, args.repo, args.pr)


if __name__ == "__main__":
    main()
```

After writing: `mkdir -p ~/.claude/scripts && chmod +x ~/.claude/scripts/pr-threads.py`

---

## Step 1: Identify the PR

```bash
OWNER=$(gh repo view --json owner --jq '.owner.login')
REPO=$(gh repo view --json name --jq '.name')
PR=$(gh pr view --json number --jq '.number')
```

Or the user provides the PR number directly.

## Step 2: Fetch All Unresolved Threads

```bash
OUT="/tmp/review-threads-${OWNER}-${REPO}-${PR}.json"
python3 ~/.claude/scripts/pr-threads.py fetch \
  --owner "$OWNER" --repo "$REPO" --pr "$PR" --out "$OUT"
```

Output file contains thread objects with: `id` (GraphQL node ID for resolving), `path`, `line`, and `comments.nodes[0].databaseId` (numeric ID for replying).

## Step 3: Group and Prioritize

1. **Group by file path** — process all comments for one file before the next (minimises re-reads).
2. **Within each file, sort by line number** ascending.
3. **Identify related threads** — multiple comments on the same logical issue get addressed together.

## Step 4: For Each Thread — Decide, Act, Respond

### Read Context

Read the file at `path`, focused on lines around `line` (±30 lines). Do NOT pre-read all files upfront.

### Decision Framework

**Default bias: fix it.** If a suggestion is reasonable and in scope, implement it — doing it right now beats a follow-up PR.

| Signal | Decision |
|--------|----------|
| Bug, logic error, null-safety issue | **Fix** |
| Clarity, naming, style improvement | **Fix** (even cosmetic if small and obviously correct) |
| Missing test, uncovered edge case | **Fix** |
| Valid perf concern with a clear fix | **Fix** |
| Valid but risky/large refactor | **Defer** — "Good catch. Deferring to follow-up to keep this PR focused." |
| Factually wrong or misunderstands intent | **Decline** — correct with specifics |
| Contradicts documented ADR / CLAUDE.md | **Decline** — cite source |
| Technical disagreement | **Decline** — state reasoning, never dismissively |

### Implement Fixes

Use Edit/Write tools. Group related fixes in the same file together before moving to the next file.

### Reply to the Thread

**`--comment-id` must be the numeric `databaseId` from `comments.nodes[0]`** — not the GraphQL node ID.

```bash
python3 ~/.claude/scripts/pr-threads.py reply \
  --owner "$OWNER" --repo "$REPO" --pr "$PR" \
  --comment-id 3183811072 \
  --body "Fixed. Added AtomicBoolean guard matching the tryStart pattern in IndexLifecycleCoordinator."
```

**Response patterns:**

| Decision | Template |
|----------|----------|
| Fixed | `"Fixed. [one sentence of what changed]"` |
| Deferred | `"Good catch. Needs a broader fix — deferring to follow-up to keep this PR focused."` |
| Declined (design) | `"This is intentional — [specific reasoning]. [Optional: ADR / code link]"` |
| Declined (disagree) | `"I see the concern. I prefer the current approach because [specific reason]. Happy to discuss."` |
| Declined (scope) | `"Agreed this could be improved. Out of scope for this PR — will address separately."` |

### Resolve All Addressed Threads in One Call

```bash
python3 ~/.claude/scripts/pr-threads.py resolve \
  --thread-id "PRRT_abc123" "PRRT_def456" "PRRT_ghi789"
```

**Only resolve threads where you gave a clear response.** Do not resolve threads where the reviewer asked a question you have not fully answered.

## Step 5: Commit

```bash
git add -A
git commit -m "address review comments

- [bullet per fix]
- [note any deferred items]"
git push
```

## Step 6: Check Merge Readiness

```bash
python3 ~/.claude/scripts/pr-threads.py check \
  --owner "$OWNER" --repo "$REPO" --pr "$PR"
```

| `mergeable` | `mergeStateStatus` | Action |
|-------------|-------------------|--------|
| `MERGEABLE` | `CLEAN` | Ready — inform user |
| `MERGEABLE` | `BLOCKED` | Awaiting approval — normal after addressing comments |
| `MERGEABLE` | `UNSTABLE` | CI failing — investigate before requesting review |
| `CONFLICTING` | `DIRTY` | Resolve conflicts: `git fetch origin main && git merge origin/main` |
| `UNKNOWN` | — | Wait 30 s and re-check |

## Step 7: Re-fetch and Verify Zero Unresolved

```bash
python3 ~/.claude/scripts/pr-threads.py fetch \
  --owner "$OWNER" --repo "$REPO" --pr "$PR"
```

Confirm output shows `0 unresolved`. If new threads appeared from the bot reviewing the push, loop back to Step 4.

## Step 8: Summarize

| Thread | File | Decision | Action |
|--------|------|----------|--------|
| #1 | `src/.../Foo.java` | Fixed | Renamed variable |
| #2 | `src/.../Bar.java` | Declined | Intentional design choice (explained) |
| #3 | `src/.../Baz.java` | Deferred | Larger refactor needed |

X fixed, Y declined, Z deferred — N total threads addressed.

## Etiquette

- Acknowledge the reviewer's intent before disagreeing.
- Never "Won't fix" alone — always include reasoning.
- "I prefer this because X avoids Y" beats "I prefer this approach."
- Thank reviewers when they catch a real bug.
- One to two sentences for fixes; three to four max for declines.

## Token Optimization

- One GraphQL fetch call for all threads (not per-thread REST).
- Read files only when processing their threads.
- Use PR-specific output file names to prevent stale data across parallel sessions.
- Batch all thread IDs into a single `resolve` call.
- Re-fetch after push to catch bot threads before declaring done.

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `github-pr` | View PR details, diff, and overall check status |
| `github-actions-debugging` | Investigate CI failures blocking merge |
| `code-review` | Apply structured review protocols before responding |
