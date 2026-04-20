---
description: Synthesize Slack threads I participated in into the Logseq daily Knowledge Synthesis zettel. Supports backfill from last run.
---

# Slack Daily Synthesis

Synthesize Slack conversations into the Logseq daily Knowledge Synthesis zettel and journal entries.

Supports three modes:
- **Default** (no args): today only
- **`--yesterday`**: previous calendar day (for 9am cron)
- **`--backfill`**: find the last synthesis date and fill in all missing days up to today

## Step 1: Determine Date Range

Use the argument if provided: `{{args}}`

Run this to get dates:
```bash
# Today
date +%Y-%m-%d

# Yesterday
date -v-1d +%Y-%m-%d

# Last synthesis date (most recent Knowledge Synthesis file in wiki)
ls /Users/tylerstapler/Documents/personal-wiki/logseq/pages/ | grep "Knowledge Synthesis - 20" | sort | tail -1
```

**If `--backfill`**: Parse the last synthesis date from the filename (format `Knowledge Synthesis - YYYY-MM-DD.md`). Generate the list of all calendar dates from the day after that date through today. Process each date in sequence, oldest first. Skip weekends if desired (Slack is quieter on weekends — ask the user if they want to skip them).

**If `--yesterday`**: Single date = yesterday.

**Default**: Single date = today.

## Step 2: For Each Date in Range, Search Slack Threads

Search for threads I participated in during the time window. My Slack user ID is `U03U0MB392B`.

Run these two searches in parallel:

**Note**: Slack search `before:` date filtering does not reliably restrict results when combined with `is:thread`. Use only `after:` with the previous day's date, then filter results by timestamp manually.

**Search 1 - Threads I wrote in:**
```
from:<@U03U0MB392B> is:thread after:YYYY-MM-DD-1
```

**Search 2 - Threads directed at me:**
```
to:<@U03U0MB392B> is:thread after:YYYY-MM-DD-1
```

Where `YYYY-MM-DD-1` is the day before the target date (e.g., to get Apr 14 threads, use `after:2026-04-13`). Filter returned messages to only include those with timestamps falling within the target date.

Use `slack_search_public_and_private` with `sort=timestamp`, `sort_dir=asc` (chronological for context), `limit=20`, `include_context=false`.

Deduplicate results by `thread_ts` — the same thread may appear in both searches.

**Note on Slack search limits**: Slack free-tier search only reaches ~90 days back. For very old dates, the search may return empty results — skip those dates silently and note them in the output.

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
