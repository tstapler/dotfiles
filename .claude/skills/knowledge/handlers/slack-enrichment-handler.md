# Slack Enrichment Handler

**Purpose**: Search Slack for knowledge relevant to a topic, parse large result files efficiently, extract insights, and enrich existing wiki pages.

**Status**: Production-ready handler

**Trigger**: When the user asks to find what they discussed on Slack about a topic, or to enrich the wiki from Slack conversations.

---

## The Core Problem This Solves

Slack search results from `mcp__claude_ai_Slack__slack_search_public_and_private` regularly return 60–110k character files that cannot be read directly into context. Naive approaches (reading the file, summarizing inline) crash or pollute the main context window. This handler encodes the correct pattern.

---

## Phase 1: Search

Run 2–4 parallel searches covering different angles of the topic. Use `from:me` to find Tyler's own contributions — these are the source of personal insights and heuristics.

```
Parallel searches for topic "X":
  1. "from:me X debugging troubleshooting"
  2. "from:me X root cause latency performance"
  3. "X incident postmortem fix resolved"       ← includes others for context
  4. "from:me X <specific-tech> problem"         ← technology-specific angle
```

**Key search modifiers**:
- `from:me` — Tyler's messages only (primary insight source)
- `from:<@U03U0MB392B>` — Tyler's user ID for exact matching
- `in:#channel-name` — narrow to a specific channel
- `after:YYYY-MM-DD` — limit to a time period
- Keyword search only (no boolean operators, no semantic search for this user)

---

## Phase 2: Handle Large Result Files

Slack results > ~30k chars are saved to disk, not returned inline. The file path is in the error message. **Never try to read these inline** — always delegate to a subagent.

### Detecting a saved file

The tool returns an error like:
```
Error: result (75,992 characters across 1 line) exceeds maximum allowed tokens.
Output has been saved to /path/to/file.txt
```

Or a JSON result with the path in the `persisted-output` block.

### Parsing pattern (always use in a subagent)

For `.txt` files (single long line):
```python
python3 -c "print(open('FILE').read()[0:40000])"
python3 -c "print(open('FILE').read()[40000:80000])"
python3 -c "print(open('FILE').read()[80000:])"
```

For `.json` files:
```python
python3 -c "import json; data=json.load(open('FILE')); print(data[0]['text'][0:40000])"
python3 -c "import json; data=json.load(open('FILE')); print(data[0]['text'][40000:80000])"
```

Read in ~40,000-char spans until you have read 100% of the file. Do not stop early.

---

## Phase 3: Subagent Extraction

Spawn one subagent per result file. **Do not parse inline** — this pollutes the main context window.

### Subagent prompt template

```
Read and analyze this Slack search results file to extract [Tyler Stapler's / all participants'] 
insights about [TOPIC].

The file is at: [FILE_PATH]
File size: ~[N] chars

Read it in ~40,000-char slices using:
  python3 -c "print(open('FILE').read()[A:B])"
Read ALL slices before responding.

Extract and return:
1. Each distinct [debugging episode / incident / insight] Tyler was involved in — 
   what the problem was, what caused it, how it was resolved
2. Specific tools, queries, or commands Tyler used
3. Mental models or heuristics Tyler articulated verbatim
4. Any specific fix, PR, or Jira ticket referenced

Return findings as structured bullet points with enough detail to write a wiki page.
Quote key messages verbatim where illuminating.
Include permalinks for any key messages.
```

---

## Phase 4: Identify Wiki Pages to Enrich

After subagents return findings, determine where to write:

1. **Check existing pages first**: `ls logseq/pages/ | grep -iE "topic|related-term"`
2. **Prefer enriching over creating**: Add a new section to an existing page rather than creating a new page for the same concept
3. **Create new pages only** when the finding is:
   - A distinct pattern with a clear name (e.g., "gRPC Shared Executor Singleton Trap")
   - Too large to fit naturally in an existing page's structure
   - A case study that belongs in `Knowledge Synthesis - YYYY-MM-DD.md`

### Section placement rules

| Finding type | Where to add |
|---|---|
| Debugging mental model / heuristic | `Debugging.md` → "Field-Tested Mental Models" |
| Database performance pattern | `Database Performance.md` → "Common Anti-Patterns" |
| Specific gRPC pattern | `gRPC Performance Bottlenecks.md` → relevant section |
| Incident process pattern | `Incident Management.md` → "Incident Process Philosophy" |
| Case study / specific incident | `Performance Investigation Methodology.md` → "Case Study Examples" |
| Daily synthesis | `Knowledge Synthesis - YYYY-MM-DD.md` (append) |

---

## Phase 5: Write Wiki Updates

Write in Logseq wiki format:
- Use `[[Wiki Links]]` for related concepts
- Use `#[[Tags]]` at the end of new sections
- Include a verbatim quote from Slack when it crystallizes the insight
- Add a reference to `[[Knowledge Synthesis - YYYY-MM-DD]]` in the References section

**Do not add duplicate content**. Read the target section before writing. If the pattern is already documented, add the specific case study example instead.

---

## Full Workflow Summary

```
User asks: "Find where I talked about X on Slack"

1. Run 2-4 parallel Slack searches (from:me + topic keywords)
2. For each result file > 30k chars:
   → Spawn subagent with file path and extraction prompt
   → Subagent reads file in 40k-char slices, returns structured findings
3. Synthesize findings across all subagents
4. Check which wiki pages already exist for the topic
5. Write enrichments to existing pages (or create new page if warranted)
6. Append summary to today's Knowledge Synthesis page
```

---

## Common Pitfalls

- **Do not read large files inline** — always subagent
- **Do not stop slicing early** — Slack result files have key content throughout, not just at the start
- **Search for the conclusion, not just the topic** — "gRPC blocking thread" finds the diagnosis; "gRPC latency" finds the symptom thread which may not have the answer
- **Check file format** — `.txt` uses `open().read()[A:B]`; `.json` uses `json.load()` then index into `data[0]['text']`
- **Run searches in parallel** — Slack search is slow; parallel queries save significant time

---

## Integration with Knowledge Skill

This handler is invoked when:
- User asks "find where I talked about X on Slack"
- User asks to enrich the wiki from Slack conversations
- A journal entry has `[[Needs Slack Synthesis]]` tag (future)

Delegates to:
- `mcp__claude_ai_Slack__slack_search_public_and_private` for search
- Agent subagents for large file parsing
- Standard wiki enrichment pattern for writing results
