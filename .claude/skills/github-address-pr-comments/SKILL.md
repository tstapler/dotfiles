---
name: github-address-pr-comments
description: Systematically address all open GitHub PR review comments — fix code or decline with reasoning, reply to every thread, resolve when done
---

# Address PR Review Comments

Load all unresolved review threads for a PR, then for each: decide whether to fix or decline, implement fixes when accepting, reply with a clear response, and resolve the thread. No comment goes unacknowledged.

## Step 0: Bootstrap — Install `pr-threads.py`

The skill uses a single permanent helper script at `~/.claude/scripts/pr-threads.py`.
Check if it exists; if not, write it from [references/pr-threads-script.md](references/pr-threads-script.md), then `chmod +x` it.
Once installed, all subsequent steps call `python3 ~/.claude/scripts/pr-threads.py <subcommand>` —
pre-approved by `Bash(python3:*)` in settings, no prompts needed.

```bash
[ -f ~/.claude/scripts/pr-threads.py ] && echo "installed" || echo "missing — write it"
```

If missing, extract the Python source from `references/pr-threads-script.md` and write it to `~/.claude/scripts/pr-threads.py`.

That reference file is the **single shared implementation** for viewing and aggregating
live PR review threads — `/code:review` and `github:pr-ship` both call it
instead of each hand-rolling their own GraphQL/jq. If it and
`~/.claude/scripts/pr-threads.py` diverge, treat the reference file as the source
of truth and re-sync the installed copy.

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
| `code-review` (`/code:review`) | Apply structured review protocols before responding; also calls `pr-threads.py summary` in its own Step 0.5 to fold live threads into diff-based findings |
| `github:pr-ship` | Gate 3 delegates thread fetch/fix/resolve to this skill; Gate 4 calls `pr-threads.py summary --since` (this skill's own script) to detect new comments after CI goes green |

All three of the skills above share one aggregation implementation — `~/.claude/scripts/pr-threads.py` (`fetch`/`summary`/`reply`/`resolve`/`check`), canonically defined in [references/pr-threads-script.md](references/pr-threads-script.md). If you change its behavior, update that reference file first.
