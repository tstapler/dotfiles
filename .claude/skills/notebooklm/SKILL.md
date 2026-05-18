---
name: notebooklm
description: "Use this skill to query Google NotebookLM notebooks and auto-synthesize answers into Logseq. Trigger when: user says 'notebooklm', 'ask my notebook', 'ask my research', 'query my notebook', 'load YouTube channel into NotebookLM', or wants source-grounded answers from a specific knowledge base. Do NOT trigger for general web research — this is only for querying content the user has already uploaded to NotebookLM."
---

# NotebookLM Research + Logseq Synthesis

Query Google NotebookLM for source-grounded, citation-backed answers from Gemini. Every answer is auto-synthesized into Logseq — no manual copy-paste.

**Key guarantee**: Gemini answers only from user-uploaded documents. No hallucination from training data.

## How to Query NotebookLM

**Prefer MCP tools** — the `notebooklm-mcp` MCP server is configured and gives Claude direct tool access. Use MCP tools for all querying and management. Fall back to `nlm` CLI only if MCP tools are unavailable.

### MCP Tools (primary — use these)

| Tool | Use for |
|---|---|
| `notebook_list` | List all notebooks |
| `notebook_query` | Ask a question, get cited answer |
| `notebook_create` | Create a new notebook |
| `source_add` | Add a URL, text, file, or Drive doc |
| `source_get_content` | Get raw text of a source |
| `studio_create` | Generate podcast, slides, mind map, report |
| `download_artifact` | Download generated audio/video/docs |

Full tool list: 35 tools covering notebooks, sources, studio, research, export. Run `notebooklm-mcp --help` to see all.

### CLI fallback

```bash
nlm login --check                                       # Check auth
nlm notebook list                                       # List notebooks
nlm notebook query {notebook-id} "{question}" -j        # Query
nlm source list {notebook-id} -j                        # List sources
```

## When to Use

Trigger when user:
- Says "notebooklm", "ask my notebook", "query my research", "search my docs"
- Wants to load a YouTube channel into NotebookLM
- Shares a NotebookLM URL
- Wants source-grounded answers (not Claude's general knowledge)

**Vault root**: `~/Documents/personal-wiki/logseq/` — pages in `pages/`, journals in `journals/`.

## Workflow Routing

| User says | Workflow |
|---|---|
| "load channel", "YouTube channel", "bulk load episodes" | [workflows/youtube-channel.md](workflows/youtube-channel.md) |
| "ask", "query", "what does X say about Y" | Use `notebook_query` MCP tool, then synthesize |
| "auth error", "login", "re-authenticate" | [workflows/auth.md](workflows/auth.md) |
| "list notebooks", "what notebooks" | Use `notebook_list` MCP tool |
| "create podcast", "generate slides", "mind map" | Use `studio_create` MCP tool |

## Setup (One-Time — User Must Run)

MCP server is already configured (`notebooklm-mcp` in `~/.claude.json`). Auth requires a one-time interactive browser login:

```bash
nlm login
```

This opens a browser for Google login. Auth persists for weeks. Run again when commands start failing.

For YouTube channel bulk loading (notebooklm-py, separate from nlm):
```bash
# Auth for notebooklm-py (creating notebooks, bulk loading)
~/.claude/skills/notebooklm/.venv/bin/notebooklm login
```

See [workflows/auth.md](workflows/auth.md) for troubleshooting.

> For synthesizing query results into Zettelkasten notes in Logseq, apply the `knowledge-synthesis` skill.

## CRITICAL: Auto-Synthesize After Every Query

**Every NLM query result MUST be synthesized into Logseq before the conversation ends.**

This is not optional. An answer that stays in the chat is wasted — the point is building the knowledge base.

After getting any answer from NotebookLM:

### 1. Determine the topic

Extract a short, title-case name for what was learned. Example: "Huberman Sleep Protocol", "Lenny Product Frameworks".

### 2. Create or update the Logseq page

Check if `~/Documents/personal-wiki/logseq/pages/{Topic Name}.md` exists. If not, create it. If yes, add a new dated section.

Structure for a new page:
```markdown
# {Topic Name}

## Core Definition

{2-3 sentence summary of the key answer from NLM}

## Details

{Full synthesized answer — NOT a raw paste of the NLM output. Synthesize it.}

## Sources (from NotebookLM)

{For each citation in the answer, format as:}
- [1] [[{Source Title}]] — "{short excerpt of cited text}"

## Related Concepts

[[{related concept 1}]] | [[{related concept 2}]] | [[{Notebook Name}]]

## Tags

#[[NotebookLM]] #[[{Domain}]] #[[Research]] {2-4 more relevant tags}
```

For updates to an existing page, append a dated H2 section (`## {YYYY-MM-DD} Update`) with new findings.

### 3. Append to daily synthesis

Append to `~/Documents/personal-wiki/logseq/pages/Knowledge Synthesis - YYYY-MM-DD.md` (create if it doesn't exist for today):

```markdown
## {Topic Name} (from NotebookLM)

**Context**: Queried [[{Notebook Name}]] — question: "{question asked}"

**Key Findings**:
- {bullet 1}
- {bullet 2}
- {bullet 3}

**Sources**: {N} citations

**Related Concepts**: [[{Topic Name}]] | [[{Notebook Name}]]
```

### 4. Add journal entry

Append one line to `~/Documents/personal-wiki/logseq/journals/YYYY_MM_DD.md` (create if needed):
```
- Queried [[{Notebook Name}]] → [[{Topic Name}]] — see [[Knowledge Synthesis - YYYY-MM-DD]]
```

## Limits

- **300 sources per notebook** — split large channels across multiple notebooks
- **Rate limits** on free Google accounts
- **Auth expires** after weeks — re-run `nlm login` when MCP tools start failing
- **Processing time** — after loading sources, NotebookLM indexes server-side; wait a few minutes before querying fresh content

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `knowledge-synthesis` | Synthesize query results into interconnected Zettelkasten notes |
| `knowledge-literature-review` | Find and import academic papers before loading into NotebookLM |
| `pdf-proof` | Visually verify specific values found in PDF sources |
| `meta-research-workflow` | Systematic web research to gather sources before loading |

## Quality Standards

- Synthesize into Logseq after EVERY query — never leave an answer only in chat
- Include citation sources in the Logseq page, not just the answer text
- Link new pages to existing `[[concepts]]` in the wiki
- Use the notebook name as a Logseq page (`[[Notebook Name]]`) so it becomes queryable
