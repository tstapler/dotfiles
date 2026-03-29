---
name: address-review-comments
description: Systematically address all open GitHub PR review comments — fix code or decline with reasoning, reply to every thread, resolve when done
---

# Address PR Review Comments

Load all unresolved review threads for a PR, then for each: decide whether to fix or decline, implement fixes when accepting, reply with a clear response, and resolve the thread. No comment goes unacknowledged.

## Step 1: Identify the PR

```bash
# From current branch
PR_NUMBER=$(gh pr view --json number -q '.number')

# Or user provides PR number directly
PR_NUMBER=123
```

## Step 2: Fetch All Unresolved Review Threads

Write this GraphQL query to `/tmp/review-threads.graphql`, then execute it.

```graphql
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
```

```bash
OWNER=$(gh repo view --json owner -q '.owner.login')
REPO=$(gh repo view --json name -q '.name')
gh api graphql -f query="$(cat /tmp/review-threads.graphql)" \
  -f owner="$OWNER" -f repo="$REPO" -F pr="$PR_NUMBER" \
  > /tmp/review-threads.json
```

Parse the JSON. Filter to threads where `isResolved: false`. Write a summary to `/tmp/review-summary.md` with columns: thread ID, file path, line, first comment body (truncated), author.

## Step 3: Group and Prioritize

1. **Group by file path** — process all comments for one file before moving to the next (minimizes re-reads).
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

Use `gh` REST API to reply:

```bash
gh api repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments/$COMMENT_ID/replies \
  -f body="$RESPONSE_BODY"
```

Where `$COMMENT_ID` is the **first comment ID** in the thread (the one that started the review thread).

**Response patterns:**

| Decision | Response template |
|----------|-------------------|
| Fixed | "Fixed. [1-sentence description of what changed]" |
| Deferred | "Good catch. This needs a broader fix — deferring to a follow-up to keep this PR focused." |
| Declined (design choice) | "This is intentional — [specific reasoning]. [Optional: link to ADR or related code]" |
| Declined (disagree) | "I see the concern. I prefer the current approach because [specific reasoning]. Happy to discuss further." |
| Declined (scope) | "Agreed this could be improved. Out of scope for this PR — I will address it separately." |

### Resolve the Thread

After replying, resolve the thread via GraphQL mutation:

```bash
gh api graphql -f query='mutation($id: ID!) { resolveReviewThread(input: {threadId: $id}) { thread { isResolved } } }' \
  -f id="$THREAD_ID"
```

**Important**: Only resolve threads where YOU made the comment being addressed (i.e., you are the PR author). If the reviewer opened the thread, resolve only after replying with a fix or clear response. Do NOT resolve threads where the reviewer asked a question you have not fully answered.

## Step 5: Commit and Push

After all threads are addressed:

```bash
# Stage and commit all fixes in one commit
git add -A
git commit -m "address review comments

- [bullet summary of each fix made]
- [note any deferred items]"
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

- Fetch all threads in one GraphQL call, not per-thread REST calls.
- Read files only when processing their threads. Do not pre-read all files.
- Write the full thread JSON to `/tmp/review-threads.json` so it can be re-read if needed without re-fetching.
- Process files in order to avoid reading the same file twice for threads on different lines.
- For files with many threads, read the file once and address all threads before moving on.
