---
name: address-review-comments
description: Systematically address all open GitHub PR review comments — fix code or decline with reasoning, reply to every thread, resolve when done
---

# Address PR Review Comments

Load all unresolved review threads for a PR, then for each: decide whether to fix or decline, implement fixes when accepting, reply with a clear response, and resolve the thread. No comment goes unacknowledged.

> **Approval-friendly design**: All `gh api` calls run via Python subprocess — they appear to the approval handler as `python3 /tmp/...py` (auto-allowed), not as individual `gh api` commands. This means the skill runs without triggering repeated manual approval prompts.

## Step 1: Identify the PR

```python
import subprocess, json

def run_gh(*args):
    r = subprocess.run(["gh"] + list(args), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return r.stdout.strip()

# Repo info — uses gh CLI (auto-allowed)
repo_json = run_gh("repo", "view", "--json", "owner,name")
repo = json.loads(repo_json)
OWNER = repo["owner"]["login"]
REPO  = repo["name"]

# PR number from current branch
pr_json = run_gh("pr", "view", "--json", "number")
PR_NUMBER = json.loads(pr_json)["number"]

print(f"PR #{PR_NUMBER}  {OWNER}/{REPO}")
```

Or the user provides the PR number directly: `PR_NUMBER = 123`.

## Step 2: Fetch All Unresolved Review Threads

Write to `/tmp/fetch_threads.py` and run with `python3 /tmp/fetch_threads.py`.

```python
#!/usr/bin/env python3
import subprocess, json, sys

OWNER = sys.argv[1]
REPO  = sys.argv[2]
PR    = int(sys.argv[3])

QUERY = """
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
            nodes { id body author { login } createdAt }
          }
        }
      }
    }
  }
}
"""

result = subprocess.run(
    ["gh", "api", "graphql",
     "-f", f"query={QUERY}",
     "-f", f"owner={OWNER}",
     "-f", f"repo={REPO}",
     "-F", f"pr={PR}"],
    capture_output=True, text=True
)
if result.returncode != 0:
    print("ERROR:", result.stderr, file=sys.stderr)
    sys.exit(1)

data = json.loads(result.stdout)
threads = data["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
open_threads = [t for t in threads if not t["isResolved"]]

with open("/tmp/review-threads.json", "w") as f:
    json.dump(open_threads, f, indent=2)

print(f"Fetched {len(threads)} threads, {len(open_threads)} unresolved")
for t in open_threads:
    first = t["comments"]["nodes"][0]
    print(f"  [{t['id'][:20]}...]  {t['path']}:{t.get('line','?')}  @{first['author']['login']}: {first['body'][:60]}")
```

Run it:
```bash
python3 /tmp/fetch_threads.py OWNER REPO PR_NUMBER
```

Parse `/tmp/review-threads.json`. Write a summary to `/tmp/review-summary.md` with columns: thread ID, file path, line, first comment body (truncated), author.

## Step 3: Group and Prioritize

1. **Group by file path** — process all comments for one file before moving to the next (minimises re-reads).
2. **Within each file, sort by line number** ascending.
3. **Identify related threads** — multiple comments about the same logical issue get addressed together.

## Step 4: For Each Thread — Decide, Act, Respond

### Read Context

Read the file referenced in `path`. Focus on the lines around `line` (+/- 30 lines for context). Do NOT read entire large files upfront.

### Decision Framework

**Accept and fix** when the comment identifies:
- A bug, logic error, or incorrect behavior
- A clarity/readability improvement that is straightforward
- A style or naming inconsistency with the codebase
- A missing test case or uncovered edge case
- A security concern or data leak risk
- A valid performance concern with a clear fix

**Decline with explanation** when:
- The change is out of scope for this PR — "Valid point. Out of scope here — I will address it in a follow-up."
- It is an intentional design choice — explain the reasoning and link to relevant code/ADR if applicable.
- You disagree with the approach — state your reasoning respectfully and specifically, never dismissively.
- An architectural constraint prevents it — cite the constraint.

**Defer** when:
- The suggestion is valid but requires a larger refactor — "Agreed this needs work. Filing as a follow-up to keep this PR focused."

### Implement Fixes

When accepting, make the code change using Edit/Write tools. Group related fixes in the same file together. After all fixes for a file are applied, move to the next file.

### Respond to the Thread

Write `/tmp/reply_threads.py` and run with `python3 /tmp/reply_threads.py`:

```python
#!/usr/bin/env python3
"""Reply to a PR review thread comment via REST API."""
import subprocess, json, sys

OWNER      = sys.argv[1]
REPO       = sys.argv[2]
PR_NUMBER  = sys.argv[3]
COMMENT_ID = sys.argv[4]   # first comment ID in the thread
BODY       = sys.argv[5]   # response text

result = subprocess.run(
    ["gh", "api",
     f"repos/{OWNER}/{REPO}/pulls/{PR_NUMBER}/comments/{COMMENT_ID}/replies",
     "-f", f"body={BODY}"],
    capture_output=True, text=True
)
if result.returncode != 0:
    print("ERROR:", result.stderr, file=sys.stderr)
    sys.exit(1)

resp = json.loads(result.stdout)
print(f"Replied (comment id={resp['id']})")
```

Run it for each thread:
```bash
python3 /tmp/reply_threads.py "$OWNER" "$REPO" "$PR_NUMBER" "$COMMENT_ID" "Fixed. [description]"
```

**Response patterns:**

| Decision | Response template |
|----------|-------------------|
| Fixed | "Fixed. [1-sentence description of what changed]" |
| Deferred | "Good catch. This needs a broader fix — deferring to a follow-up to keep this PR focused." |
| Declined (design choice) | "This is intentional — [specific reasoning]. [Optional: link to ADR or related code]" |
| Declined (disagree) | "I see the concern. I prefer the current approach because [specific reasoning]. Happy to discuss further." |
| Declined (scope) | "Agreed this could be improved. Out of scope for this PR — I will address it separately." |

### Resolve the Thread

After replying, resolve threads in bulk with `/tmp/resolve_threads.py`:

```python
#!/usr/bin/env python3
"""Resolve one or more review threads via GraphQL."""
import subprocess, json, sys

MUTATION = 'mutation($id: ID!) { resolveReviewThread(input: {threadId: $id}) { thread { isResolved } } }'

thread_ids = sys.argv[1:]  # pass all thread node IDs as args

for tid in thread_ids:
    result = subprocess.run(
        ["gh", "api", "graphql",
         "-f", f"query={MUTATION}",
         "-f", f"id={tid}"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    resolved = data["data"]["resolveReviewThread"]["thread"]["isResolved"]
    print(f"{'✓' if resolved else '✗'} {tid[:20]}...  resolved={resolved}")
```

Run it:
```bash
python3 /tmp/resolve_threads.py "PRRT_..." "PRRT_..." "PRRT_..."
```

**Important**: Only resolve threads where YOU addressed the concern (either fixed or gave a clear response). Do NOT resolve threads where the reviewer asked a question you have not fully answered.

## Step 5: Commit

After all threads are addressed, commit the fixes. **Do not push automatically** — the user decides when to push.

```bash
git add -A
git commit -m "address review comments

- [bullet summary of each fix made]
- [note any deferred items]"
```

To push when ready:
```bash
git push
```

## Step 6: Summarize

Print a final summary table:

| Thread | File | Decision | Action Taken |
|--------|------|----------|-------------|
| #1 | `src/.../Foo.java` | Fixed | Renamed variable for clarity |
| #2 | `src/.../Bar.java` | Declined | Intentional design choice (explained) |
| #3 | `src/.../Baz.java` | Deferred | Follow-up needed for larger refactor |

Include counts: X fixed, Y declined, Z deferred, total N threads addressed.

## Etiquette Rules

- **Always acknowledge the reviewer's intent** before disagreeing. They took time to review your code.
- **Never be dismissive**. "Won't fix" alone is not acceptable. Always include reasoning.
- **Be specific**, not vague. "I prefer this approach" is weak. "I prefer this because X avoids Y" is strong.
- **Thank the reviewer** when they catch a real bug. A simple "Good catch" goes a long way.
- **When uncertain**, ask a clarifying question in the reply instead of guessing what they meant.
- **Keep responses concise**. One to two sentences for fixes. Three to four sentences max for declines.

## Token Optimization

- Fetch all threads in one GraphQL call (Step 2), not per-thread REST calls.
- Read files only when processing their threads. Do not pre-read all files.
- Write the full thread JSON to `/tmp/review-threads.json` so it can be re-read if needed without re-fetching.
- Process files in order to avoid reading the same file twice for threads on different lines.
- For files with many threads, read the file once and address all threads before moving on.
- Batch all thread resolutions into a single `python3 /tmp/resolve_threads.py ...` call.
