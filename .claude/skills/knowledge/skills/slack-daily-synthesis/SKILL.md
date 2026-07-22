---
description: Synthesize Slack threads I participated in into the Logseq daily journal. Default mode walks backwards until finding a day already synthesized.
---

# Slack Daily Synthesis

Synthesize Slack conversations into the Logseq daily journal entries.

Supports three modes:
- **Default** (no args): walk backwards from today until finding a day already synthesized
- **`--yesterday`**: previous calendar day only (for 9am cron)
- **`--backfill`**: find the last synthesis date and fill in all missing days up to today (same as default but explicit)

## Step 0: Resolve the Logseq Graph Path

Never hardcode the graph location. Resolve it once, path-agnostically, so this works both in an
interactive session and under the launchd cron (where shell functions/exports are not sourced):

```bash
# Prefer $LOGSEQ_PATH (set by the cron agent + shell exports); then the logseq_path helper if
# available; then fall back to filesystem detection. First dir that contains journals/ wins.
GRAPH="${LOGSEQ_PATH:-}"
if [ -z "$GRAPH" ] && command -v logseq_path >/dev/null 2>&1; then GRAPH="$(logseq_path)"; fi
for c in "$GRAPH" "$HOME/Documents/notes" "$HOME/Documents/personal-wiki/logseq"; do
  if [ -n "$c" ] && [ -d "$c/journals" ]; then GRAPH="$c"; break; fi
done
JOURNALS="$GRAPH/journals"
PAGES="$GRAPH/pages"
CACHE="$GRAPH/.slack-thread-cache"   # hidden dir under the graph; ignored by Logseq
echo "Graph: $GRAPH"
```

Use `$JOURNALS`, `$PAGES`, and `$CACHE` throughout — never a literal `personal-wiki` or `notes` path.

## Step 1: Determine Date Range

Use the argument if provided: `{{args}}`

Run this to get today's date:
```bash
date +%Y-%m-%d
```

**If `--yesterday`**: Single date = yesterday. Done.

**Default or `--backfill`**: Walk backwards from today. For each candidate date (today, yesterday, day before, ...):
1. Check if the journal file exists: `$JOURNALS/YYYY_MM_DD.md`
2. If it exists, grep for `[[Slack]] conversations` — if found, **stop here** (this day and everything before is already done)
3. If not found (or file doesn't exist), add this date to the processing queue
4. Continue backwards up to a maximum of 30 days

Process the queue oldest-first so the journal entries read chronologically.

```bash
# Check if a journal day is already synthesized
grep -l "\[\[Slack\]\] conversations" "$JOURNALS/YYYY_MM_DD.md" 2>/dev/null
```

## Step 2: For Each Date in Range, Search Slack Threads

Slack access is the **slack-interactions** script — self-contained (needs only the machine-local
token file), so it works under the launchd cron with no MCP/plugin loading. Resolve it once:

```bash
SLACK_REQ="${SLACK_REQ:-$(ls "$HOME"/ws/*/plugins/slack-interactions-plugin/skills/slack-interactions/scripts/slack_request.py 2>/dev/null | head -1)}"
```

Search for threads *I* participated in. "I" spans my human identity **and** the bot that posts on my
behalf (both represent my conversations in this workspace). Override with env vars:

```bash
SYNTH_USERS="${SYNTH_USERS:-tstapler tylerbot}"   # from: takes a Slack username, not a user ID
SYNTH_MENTION="${SYNTH_MENTION:-U0BCQ0ME13K}"      # my human user ID, for the mention search
```

**Note**: Slack search `before:` is unreliable with `is:thread`. Use only `after:` with the day
*before* the target date, then post-filter to messages whose `ts` falls within the target day.

For each date (`DAY`, with `PREV` = the day before), run these searches, paginating each fully
(`--paginate-through-all`, `sort=timestamp`, `sort_dir=asc`) and collecting every result:

```bash
DAY=YYYY-MM-DD; PREV=YYYY-MM-DD-1
for U in $SYNTH_USERS; do
  # replies I wrote (is:thread), and threads I started (no is:thread)
  "$SLACK_REQ" --endpoint /api/search.messages --param query="from:@$U is:thread after:$PREV" --param sort=timestamp --param sort_dir=asc --paginate-through-all --json-pretty
  "$SLACK_REQ" --endpoint /api/search.messages --param query="from:@$U after:$PREV"            --param sort=timestamp --param sort_dir=asc --paginate-through-all --json-pretty
done
# threads where I was mentioned
"$SLACK_REQ" --endpoint /api/search.messages --param query="<@$SYNTH_MENTION> is:thread after:$PREV" --param sort=timestamp --param sort_dir=asc --paginate-through-all --json-pretty
```

Post-filter: keep only messages whose `ts` is within `DAY`. For the "threads I started" search, keep
only roots (`thread_ts == ts`) or messages with `reply_count > 0`.

**Deduplication**: dedupe all collected messages by `(channel, thread_ts)`. Each unique pair is one
thread to process.

**Search reach**: Slack search only goes back ~90 days; older dates may return empty — skip silently.

## Step 2b: Read Threads (Cache-First)

Before reading any thread via the Slack API, check the local cache:

**Cache path**: `$CACHE/YYYY-MM-DD/{channel_id}__{thread_ts}.md`

For each unique `thread_ts`:
1. Determine its date bucket (from the message timestamp)
2. Check if `$CACHE/YYYY-MM-DD/{channel_id}__{thread_ts}.md` exists
3. If cached: read from file — skip Slack API call
4. If not cached: fetch it with
   `"$SLACK_REQ" --endpoint /api/conversations.replies --param channel=$channel_id --param ts=$thread_ts --pretty`,
   then write the content to the cache file

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

Cache directory structure (`$CACHE`):
```
.slack-thread-cache/
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

Journal path: `$JOURNALS/YYYY_MM_DD.md`
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
- Check if `$PAGES/<Concept>.md` already exists
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

✓ Journal → $JOURNALS/YYYY_MM_DD.md (inline)
○ Wiki candidates: [list if any]
```

---

## Scheduling (launchd)

The durable, always-on scheduler lives in `stapler-scripts/slack-synthesis/`. It is a launchd
agent (`com.tstapler.slack-synthesis`) that runs `claude -p "/knowledge:slack-daily-synthesis
--yesterday"` at 09:10 local each day, with `LOGSEQ_PATH` exported so the graph resolves the same
way it does interactively.

Install / reinstall (idempotent):

```bash
~/dotfiles/stapler-scripts/slack-synthesis/install.sh
```

Manage:

```bash
launchctl kickstart -k gui/$(id -u)/com.tstapler.slack-synthesis   # run now
launchctl print gui/$(id -u)/com.tstapler.slack-synthesis          # status
tail -f ~/Library/Logs/slack-synthesis.log                          # logs
launchctl bootout gui/$(id -u)/com.tstapler.slack-synthesis        # disable
```

To change the schedule or graph path, edit `run.sh` / the plist in that directory and re-run
`install.sh`. Missed runs (laptop asleep) fire on the next wake because `--yesterday` + the
walk-back logic backfill any gap.
