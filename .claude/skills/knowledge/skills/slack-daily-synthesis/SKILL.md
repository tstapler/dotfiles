---
description: Synthesize Slack threads I participated in into the Logseq daily journal. Default mode walks backwards until finding a day already synthesized.
---

# Slack Daily Synthesis

Synthesize Slack conversations into the Logseq daily journal entries.

Supports three modes:
- **Default** (no args): walk backwards from today until finding a day already synthesized
- **`--yesterday`**: previous calendar day only (for 9am cron)
- **`--backfill`**: find the last synthesis date and fill in all missing days up to today (same as default but explicit)

## Step 1: Determine Date Range

Use the argument if provided: `{{args}}`

Run this to get today's date:
```bash
date +%Y-%m-%d
```

**If `--yesterday`**: Single date = yesterday. Done.

**Default or `--backfill`**: Walk backwards from today. For each candidate date (today, yesterday, day before, ...):
1. Check if the journal file exists: `~/Documents/personal-wiki/logseq/journals/YYYY_MM_DD.md`
2. If it exists, grep for `[[Slack]] conversations` — if found, **stop here** (this day and everything before is already done)
3. If not found (or file doesn't exist), add this date to the processing queue
4. Continue backwards up to a maximum of 30 days

Process the queue oldest-first so the journal entries read chronologically.

```bash
# Check if a journal day is already synthesized
grep -l "\[\[Slack\]\] conversations" ~/Documents/personal-wiki/logseq/journals/YYYY_MM_DD.md 2>/dev/null
```

## Step 2: For Each Date in Range, Search Slack Threads

Search for threads I participated in during the time window. My Slack user ID is `U03U0MB392B`.

**Note**: Slack search `before:` date filtering does not reliably restrict results when combined with `is:thread`. Use only `after:` with the previous day's date, then filter results by timestamp manually.

Where `YYYY-MM-DD-1` is the day before the target date (e.g., to get Apr 14 threads, use `after:2026-04-13`). Filter returned messages to only include those with timestamps falling within the target date.

Run all three searches in parallel, paginating each until exhausted:

**Search 1 - Thread replies I wrote** (`is:thread` = reply messages only):
```
from:<@U03U0MB392B> is:thread after:YYYY-MM-DD-1
```

**Search 2 - Threads I started** (top-level messages that became threads — no `is:thread` filter):
```
from:<@U03U0MB392B> after:YYYY-MM-DD-1
```
Post-filter: keep only messages where `thread_ts == message_ts` (i.e. the message is a thread root with replies), OR where the message has `reply_count > 0`.

**Search 3 - Threads where I was mentioned:**
```
<@U03U0MB392B> is:thread after:YYYY-MM-DD-1
```

**Pagination**: For each search, use `slack_search_public_and_private` with `limit=20`. If `pagination_info` indicates more pages, repeat with the returned `cursor` until no more pages. Collect all results before deduplicating.

Use `sort=timestamp`, `sort_dir=asc`, `include_context=false` for all searches.

**Deduplication**: After collecting all results from all three searches and all pages, deduplicate by `thread_ts`. Each unique `thread_ts` = one thread to process.

**Note on Slack search limits**: Slack free-tier search only reaches ~90 days back. For very old dates, searches may return empty results — skip those dates silently and note them in the output.

## Step 2b: Read Threads (Cache-First)

Before reading any thread via the Slack API, check the local cache:

**Cache path**: `/Users/tylerstapler/Documents/personal-wiki/slack-thread-cache/YYYY-MM-DD/{channel_id}__{thread_ts}.md`

For each unique `thread_ts`:
1. Determine its date bucket (from the message timestamp)
2. Check if `slack-thread-cache/YYYY-MM-DD/{channel_id}__{thread_ts}.md` exists
3. If cached: read from file — skip Slack API call
4. If not cached: call `slack_read_thread` with `channel_id` and `message_ts=thread_ts`, then write content to the cache file

Cache file format:
```markdown
# Thread: {channel_name} / {thread_ts}
channel_id: {channel_id}
thread_ts: {thread_ts}
permalink: {permalink_url}
date: YYYY-MM-DD

---

{raw thread content — messages in order with author, timestamp, text}
```

Cache directory structure:
```
slack-thread-cache/
└── YYYY-MM-DD/
    └── {channel_id}__{thread_ts}.md
```

This ensures future backfills and re-runs never re-fetch threads already retrieved. The cache is permanent — don't expire or delete entries.

## Step 3: Cluster Threads by Topic

Group the unique threads into thematic clusters. Skip:
- Pure social/reaction threads (no substantive content)
- Incident channel noise with no decision
- Bot-only threads

For each substantive cluster, identify:
- **Topic**: What was being discussed
- **Channel**: Where it happened
- **Participants**: Who else was involved
- **Key points**: What was said / decided / learned
- **Decisions or action items**: Anything that requires follow-up
- **Insights worth keeping**: Technical learnings, strategic thinking, patterns noticed

## Step 4: Write Inline to Today's Logseq Journal

Synthesis goes **directly into the journal** — not a separate Knowledge Synthesis zettel. This keeps everything browsable inline in the daily entry.

Journal path: `/Users/tylerstapler/Documents/personal-wiki/logseq/journals/YYYY_MM_DD.md`
(Use underscores, not hyphens, for the filename)

If the journal file doesn't exist, create it. Always **append** — never overwrite existing content.

**In `--backfill` mode**: Many historical journal files may already exist with personal notes (reading, home, etc.). Append the Slack section at the end — it's additive context for what that day looked like.

Append using Logseq-native nested bullet structure. Each cluster gets a thread permalink so entries are clickable back to the original conversation:

```markdown
- [[Slack]] conversations
	- [Cluster Topic 1] ([#channel-name](permalink-url))
		- Key point 1
		- Key point 2
		- Decision: ...
		- Action item: ... (if any)
		- Related: [[Concept]], [[Tool]], [[Person]]
	- [Cluster Topic 2] ([#channel-name](permalink-url))
		- ...
```

The permalink for each cluster should link to the **root message** of the thread (`thread_ts` = `message_ts` of the first message), not a reply. Use the `Permalink` field from the search results for the earliest message in each thread.

## Step 6: Surface Any Wiki Candidates

For each major concept, tool, person, or decision that came up in the conversations:
- Check if `logseq/pages/<Concept>.md` already exists
- If not, note it as a candidate for a future zettel
- Only create stubs for things that are genuinely worth expanding later

Report candidates but don't auto-create unless explicitly asked.

## Output Report

After completing:

```
=== Slack Daily Synthesis Complete ===
Date: YYYY-MM-DD
Threads processed: N
Clusters synthesized: N

Topics:
  - [Cluster 1 topic] (#channel): [1-line summary]
  - [Cluster 2 topic] (#channel): [1-line summary]
  ...

✓ Journal → logseq/journals/YYYY_MM_DD.md (inline)
○ Wiki candidates: [list if any]
```

---

## Cron Setup

To run this automatically at 9am daily (synthesizing the previous day):

```bash
# Add to crontab with: crontab -e
# Runs at 9:00am Monday–Friday, synthesizes previous day's Slack activity
0 9 * * 1-5 /bin/zsh -l -c 'claude --print "/knowledge:slack-daily-synthesis --yesterday" >> ~/logs/slack-synthesis.log 2>&1'
```

Or for end-of-day at 6pm:
```bash
# Runs at 6:00pm Monday–Friday, synthesizes today's activity
0 18 * * 1-5 /bin/zsh -l -c 'claude --print "/knowledge:slack-daily-synthesis" >> ~/logs/slack-synthesis.log 2>&1'
```

Ensure the log directory exists: `mkdir -p ~/logs`

The `-l` flag on zsh loads your full shell environment (PATH, API keys, etc.) which is required for Slack MCP auth to work.
