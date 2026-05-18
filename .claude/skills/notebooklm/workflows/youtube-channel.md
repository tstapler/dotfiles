# YouTube Channel Loader Workflow

Bulk-load all videos from a YouTube channel into a new NotebookLM notebook.

## Inputs

- **channel_url**: e.g. `https://www.youtube.com/@LennysPodcast`
- **notebook_name**: Human-readable name for the notebook
- **count**: Number of most recent videos to load (default: 200, max: 300)

## Step 1: Verify auth

```bash
nlm login --check
~/.claude/skills/notebooklm/.venv/bin/notebooklm list
```

If auth error, see [workflows/auth.md](auth.md).

## Step 2: Scrape channel videos

```bash
python3 ~/.claude/skills/notebooklm/scripts/load_channel.py scrape \
  --channel "{channel_url}" \
  --output /tmp/channel-videos.json
```

Pure stdlib — no dependencies. Uses InnerTube API. Paginates through all videos, ordered most recent first.

Check output: `python3 -c "import json; d=json.load(open('/tmp/channel-videos.json')); print(f'{len(d)} videos found')"`

## Step 3: Create notebook

```bash
~/.claude/skills/notebooklm/.venv/bin/notebooklm create "{notebook_name}"
```

Note the notebook ID from the output (UUID format).

## Step 4: Load videos

```bash
python3 ~/.claude/skills/notebooklm/scripts/load_channel.py load \
  --videos /tmp/channel-videos.json \
  --notebook {notebook-id} \
  --count {count} \
  --concurrency 20
```

~200 videos in ~75 seconds. Failed uploads saved to `/tmp/channel-load-errors.json`.

## Step 5: Register with nlm CLI

```bash
nlm notebook list
```

Note: `nlm` tracks notebooks by ID — just use the ID directly in queries. No "use" command needed.

## Step 6: Wait for indexing

NotebookLM indexes content server-side after upload. Wait 2-5 minutes before querying, especially for large loads.

Verify readiness:
```bash
nlm source list {notebook-id} --json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'{len(d)} sources indexed')"
```

## Step 7: Create Logseq index page

Create `~/{Notebook Name}.md` (replacing spaces with spaces — keep it readable):

```markdown
# {Notebook Name}

## Overview

**Source**: [{channel_url}]({channel_url})
**Loaded**: {YYYY-MM-DD}
**Videos**: {count} most recent
**Notebook ID**: `{notebook-id}`

## Topics Covered

{Ask the notebook: nlm notebook query {id} "What are the main topics, themes, and subjects covered in this collection?" --json}

{Summarize the answer here in bullet points}

## Related Concepts

[[NotebookLM]] | [[Research]] | [[{Domain}]]

## Tags

#[[NotebookLM]] #[[{Domain}]] #[[YouTube]] #[[Research]]
```

## Step 8: Journal entry

Add to `~/YYYY_MM_DD.md`:
```
- Loaded [[{Notebook Name}]] into NotebookLM ({count} videos from {channel_url})
```

## Limits

- 300 sources per notebook max. For channels with 300+ videos, create `{Name} Part 1`, `{Name} Part 2`
- Some videos fail if private, deleted, or region-locked — check `/tmp/channel-load-errors.json`
- Rate limits may apply for very large loads
