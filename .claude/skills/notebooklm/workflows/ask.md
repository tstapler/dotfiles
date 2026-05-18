# Ask Notebook Workflow

Query a NotebookLM notebook and auto-synthesize the answer into Logseq.

## Inputs

- **question**: The question to ask
- **notebook-id**: UUID from `nlm notebook list` (or omit if one is active)
- **topic-name**: Short title-case name for the Logseq page (e.g. "Huberman Sleep Protocol")

## Step 1: Verify auth

```bash
nlm login --check
```

If auth error: `nlm login` (user must run — opens browser).

## Step 2: List notebooks (if ID unknown)

```bash
nlm notebook list
```

## Step 3: Query

```bash
nlm notebook query {notebook-id} "{question}" -j > /tmp/nlm-answer.json
```

**Delegate to a sub-agent to keep raw JSON out of context:**

```
Agent(model="haiku", prompt="""
Run: nlm notebook query {notebook-id} "{question}" -j > /tmp/nlm-answer.json
Return: answer text (truncated to 2000 chars), citation count, source titles list
""")
```

Or read `/tmp/nlm-answer.json` directly. Key fields:
- `value.answer` — Gemini's full response text
- `value.references` — array of `{source_id, citation_number, cited_text}`
- Sources list from: `nlm source list {notebook-id} --json > /tmp/nlm-sources.json`

## Step 4: Resolve citations (optional)

Map `[N]` citation numbers to source titles:

```bash
nlm source list {notebook-id} --json > /tmp/nlm-sources.json

python3 ~/.claude/skills/notebooklm/scripts/resolve_citations.py \
  --qa /tmp/nlm-answer.json \
  --sources /tmp/nlm-sources.json \
  --output /tmp/nlm-resolved.md
```

This writes a Logseq-compatible markdown file with footnote citations.

## Step 5: Synthesize to Logseq

**This step is mandatory.** See the Auto-Synthesize section in SKILL.md.

Determine the topic name, then:

1. Create or update `~/{Topic Name}.md`
2. Append to `~/Knowledge Synthesis - YYYY-MM-DD.md`
3. Add one line to `~/YYYY_MM_DD.md`

## Output

- Logseq page: `~/{Topic Name}.md`
- Daily synthesis updated: `~/Knowledge Synthesis - YYYY-MM-DD.md`
- Journal entry added: `~/YYYY_MM_DD.md`

## Cross-Source Citation Note

NotebookLM sometimes returns the same `source_id` for all citations in cross-source synthesis. The resolve_citations.py script handles this by fuzzy-matching `*"episode title"*` section markers in the answer text to source titles. Works automatically.
