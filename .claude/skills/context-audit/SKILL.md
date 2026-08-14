# context-audit — Context Window Token Breakdown & Recommendations

Analyzes a Claude Code session transcript (real on-disk JSONL, not `/context`
output) to show where context tokens actually went, then gives concrete
recommendations for cutting them.

## When to use

- The user asks "why is my context so full" / "what's eating my tokens" /
  "how do I stop context thrashing"
- Before or after a compaction, to understand what drove it
- Comparing two sessions to see if a workflow change reduced token spend

## How it works

Claude Code writes each session's transcript to:

```
~/.claude/projects/<cwd-with-slashes-as-dashes>/<session-uuid>.jsonl
```

Each line has a top-level `type`. The two that matter for token accounting
are `user` and `assistant` — their `message.content` is either a plain string
or a list of blocks (`text`, `thinking`, `tool_use`, `tool_result`, `image`).
`attachment` lines (hook output, deferred-tool-list deltas, task
notifications) also consume context but aren't part of the visible
conversation — they're broken out separately since they're a common silent
cost center.

Two totals are reported, on different bases:

- **Actual tokens** — real API-reported usage (`message.usage.{input_tokens,
  output_tokens, cache_creation_input_tokens, cache_read_input_tokens}`) from
  the *last* assistant turn in the transcript. This is the current context
  window size. `None` if the transcript has no assistant `usage` data.
- **Estimated tokens** — the `len(text) // 4` heuristic, summed across every
  block in the *entire* transcript. This is what the category breakdown
  (thinking/text/tool_use/tool_results/attachments) and recommendation
  percentages are based on, since `usage` isn't broken out per block. It's
  cumulative across the whole session, including content already
  pruned/compacted out of the live context — so it's normally larger than the
  actual total and the two aren't directly comparable.

## Running it

1. Find the transcript for the session to audit:
   ```
   ls -t ~/.claude/projects/<cwd-slug>/*.jsonl | head -1
   ```
   `<cwd-slug>` is the working directory path with `/` replaced by `-`. If
   auditing the *current* session, the path is available from context (it's
   printed at the bottom of a compaction summary, or ask the user to run
   `/status` if unsure).

2. Run the analyzer:
   ```
   python3 ~/.claude/skills/context-audit/scripts/context_audit.py <path.jsonl>
   ```
   Add `--json` for machine-readable output. Add
   `--sqlite ~/.claude/context-audit/trend.db --session-id <id> --trigger <manual|auto>`
   to also record the run in the shared trend db (this is what the
   PostCompact hook does automatically).

3. Read the output to the user. It reports:
   - Actual tokens (real usage, current context size) and estimated tokens
     (chars/4 heuristic, cumulative) — see **How it works** above for why
     these differ — plus a breakdown by category (thinking / text /
     tool_use inputs / tool_results / attachments)
   - Top tools by token cost and call count
   - The 10 largest individual items (which turn, which tool call)
   - Generated recommendations (thresholds: tool_results >35%, thinking >15%,
     attachments >10% of total trigger a specific callout)

## Interpreting results

- **tool_results dominant** → the agent is reading/dumping too much raw data.
  Push toward `Grep`/`Read` with `offset`/`limit`, redirecting large command
  output to a file instead of stdout, or using a subagent to isolate a
  research pass instead of pulling all its findings into the main context.
- **attachments dominant** → a hook is likely returning verbose stdout on
  every matching event. Check `settings.local.json` hooks for ones without
  output truncation.
- **tool_use inputs dominant** → look at `by_tool_calls` for a tool being
  called far more than expected (a retry loop, or a tool used where a more
  targeted one would do).
- **thinking dominant** → session used a high reasoning effort throughout;
  consider whether that effort level was needed for the whole session or just
  a few turns.

This skill only reports and recommends — it does not modify the transcript,
settings, or any hooks. Apply recommendations manually.

## Related

- The `PostCompact` hook (`~/dotfiles/.claude/hooks/context-audit-postcompact.sh`)
  runs this same script automatically after every compaction (in the
  background — it never blocks Claude Code) and records a row in a shared
  SQLite trend db at `~/.claude/context-audit/trend.db` (`compactions` table,
  WAL mode, matching the `cmdcrush`/`rtk` pattern), so token-spend patterns
  are queryable across sessions without needing to invoke this skill manually
  every time:
  ```
  sqlite3 ~/.claude/context-audit/trend.db \
    "SELECT timestamp, session_id, total_estimated_tokens, top_tools FROM compactions ORDER BY id DESC LIMIT 10;"
  ```
- `context-viz` — renders `/context all expand` output as a Sankey diagram.
  Complementary: `context-viz` visualizes the model's own live count,
  `context-audit` explains it from the transcript with recommendations.
