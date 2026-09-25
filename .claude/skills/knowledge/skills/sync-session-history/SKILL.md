---
description: Find durable technical concepts from this session that aren't in the Logseq wiki yet, and synthesize the gaps. Defaults to the current session; --history sweeps past sessions instead.
---

# Sync Session History to Wiki

Close the gap between what got figured out in conversation and what's actually written down.

Two modes:
- **Default (no args): the current session.** Review this conversation, extract durable concepts not yet in the wiki, synthesize the gaps. This is the common case — run it near the end of a session that turned up something worth keeping.
- **`--history`**: sweep *past* sessions instead (see "Historical Mode" below). Supports `--since <date>`, `--all`, `--limit <n>` (default 20). Expensive — this machine has 1000+ stored session transcripts, so unscoped `--all` needs explicit user confirmation before running.

## Default Mode: Current Session

No transcript parsing needed — the point of running this *in* the session is that you already have the full conversation in context. Don't read `~/.claude/projects/.../*.jsonl` for this mode; that's only for Historical Mode below.

### Step 1: Resolve the Wiki Root

Same resolution as `knowledge-synthesis`'s Wiki Root Resolution — never hardcode:
1. `$WIKI_PATH` env var if set.
2. Else the `wiki_path` shell function if available.
3. Else `~/Documents/notes` (current default), then `~/Documents/personal-wiki/logseq` as a legacy fallback.
4. `Glob` to check whether `pages/`+`journals/` sit directly under the root or nested under `logseq/` — don't assume.

### Step 2: Extract Candidate Concepts

Review the conversation so far (if this skill is invoked from a fresh agent/fork rather than inline, that agent already inherits full context — no extra fetch needed). Identify durable, non-obvious technical concepts — the kind that would still matter in an unrelated future conversation. Exclude:
- Anything fully derivable by reading the current state of the repo/code.
- Routine debugging with no generalizable lesson.
- Pure task narration ("then I edited file X, then ran the tests").
- Ephemeral state (a specific PR number, ticket ID, temp file path) unless it's the kind of durable reference (like a platform URL pattern or a diagnostic technique) worth keeping.

For each candidate: a short title, a 1-3 sentence summary, and the concrete evidence (a quote, command, or fact) backing it.

### Step 3: Cross-Check Against the Existing Wiki

For every candidate:
1. `Glob` `<GRAPH>/pages/*.md` for an exact or near-match filename.
2. If a match exists, `Read` it and decide: genuinely new information, or already covered? Drop duplicates; keep only material additions (flag as "update to `[[Existing Page]]`").
3. No match → candidate for a new page.

### Step 4: Synthesize the Survivors

Delegate to the `knowledge-synthesis` agent (or apply its skill directly) for the actual writing:
- New concepts → one atomic page each, per its Atomicity rule, tagged and cross-linked.
- Updates → append to the existing page; split out a new page instead if the addition is really a distinct concept.
- Log the run in today's journal with the standard nested-bullet shape:
  ```markdown
  - Synced this session's findings to the wiki
  	- ## Created Pages
  		- [[New Page]] — one-line description
  	- ## Updated Pages
  		- [[Existing Page]] — what changed on it
  ```

If there's nothing worth keeping, say so plainly and skip writing anything — don't force a page out of a routine session.

### Output Report

```
=== Session Sync Complete ===
Concepts considered: N → K new after dedup
Pages created: [[Page]], [[Page]]
Pages updated: [[Page]]
```

---

## Historical Mode (`--history`)

Sweeps *past* sessions instead of the current one. Use when you want to backfill older work, not for routine end-of-session synthesis.

Args: `--since <date>` (process sessions started on/after), `--all` (ignore the cursor, full backfill — confirm with the user first, this machine has 1000+ session transcripts), `--limit <n>` (cap per run, default 20).

### Step H1: Resolve the Wiki Root

Same as Step 1 above.

### Step H2: Find the Cursor

State lives in a hidden file at the wiki root, same pattern as `slack-daily-synthesis`'s thread cache:
```
<wiki root>/.session-history-sync-cursor
```
Contents: a single ISO-8601 timestamp — the newest session already processed. Missing file = first run; default the cursor to 30 days ago rather than "all time" unless `--all` was passed.

### Step H3: Enumerate Candidate Sessions

Session transcripts are raw JSONL at `~/.claude/projects/<project-slug>/<session-id>.jsonl` — one file per session, across every project ever worked in on this machine. The current session's own id is `$CLAUDE_CODE_SESSION_ID`; exclude that file from a historical sweep, since Default Mode already covers it directly from context.

1. **Try `mcp__consolette__list_sessions_summary` first** — returns `{id, started_at, source, call_count, cost_per_call_usd, peak_context_tokens, chain_coverage_ratio}` per session, no arguments needed. If connected and returning more than one distinct real entry, filter to `started_at` newer than the cursor, sort ascending, take the first `--limit`.
   - **Known gotcha**: some environments return exactly one row, `{"id":"fixture-session","started_at":"2024-01-01T00:00:00Z"}` — placeholder data. Treat a single fixture-only result as "not wired to real session storage here," not as "no sessions exist," and fall through to H3b.
2. **Fallback: enumerate raw transcripts directly.**
   ```sh
   find ~/.claude/projects -maxdepth 2 -iname "*.jsonl" -newer "$GRAPH/.session-history-sync-cursor" 2>/dev/null \
     | grep -v "$CLAUDE_CODE_SESSION_ID" \
     | xargs -I{} stat -f "%Sm %N" -t "%Y-%m-%dT%H:%M:%S" {} \
     | sort \
     | head -n "${LIMIT:-20}"
   ```
   (No cursor file yet → use `-mtime -30` instead of `-newer`.) Skip files under 2KB (empty/aborted sessions).

### Step H4: Extract Candidates Per Session (delegate — never read raw transcripts in the main context)

A transcript can be tens of MB; reading one directly would blow out context for no benefit. For each session in the batch, launch a **fresh `general-purpose` Agent** (not a fork — these need no shared context, and should run in parallel) with a self-contained prompt:

> "Read the Claude Code session transcript at `<path>`. It's JSONL — each line is one event; look at `type:"user"`/`type:"assistant"` message rows for the actual conversation, skip hook/tool-noise rows unless they reveal a concrete finding. Extract only durable, non-obvious technical concepts — useful in an unrelated future conversation. Exclude routine debugging with no generalizable lesson, anything derivable from current repo state, pure task narration. Report 0-8 concepts (most sessions: 0-2): title, 1-3 sentence summary, one-line evidence quote. Keep the whole report under 400 words."

Batch these launches in **one message with multiple Agent tool calls** so they run concurrently. Group several small transcripts into one Agent call to cut overhead; one call per session for large transcripts.

### Step H5: Cross-Check and Synthesize

Same as Steps 3-4 above, applied to the pooled candidates from all sessions in this batch.

### Step H6: Advance the Cursor

Only after synthesis succeeds: overwrite `<GRAPH>/.session-history-sync-cursor` with the newest `started_at`/mtime actually processed this run — not "now," so a capped batch resumes correctly next time instead of skipping unprocessed sessions.

### Output Report

```
=== Historical Session Sync Complete ===
Sessions scanned: N (range: <oldest> .. <newest>)
Concepts found: M candidates → K new after dedup
Pages created / updated: ...
Cursor advanced to: <timestamp>
Remaining backlog: ~<count> sessions not yet covered (if capped by --limit)
```

## Related Skills

- `knowledge-synthesis` — atomicity rule, wiki root resolution, linking/tagging, journal integration pattern; this skill delegates all actual writing to it.
- `slack-daily-synthesis` — the sibling skill Historical Mode's cursor/walk-back/cache pattern is copied from, for a different source (Slack instead of session transcripts).
- `knowledge:expand-missing-topics` — closes gaps *within* the wiki (referenced-but-undocumented `[[links]]`); this skill closes gaps *between* conversations and the wiki instead.
