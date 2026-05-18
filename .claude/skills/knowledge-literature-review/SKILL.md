---
name: knowledge-literature-review
description: Conduct structured literature reviews by searching arXiv, building citation graphs via Semantic Scholar, and storing papers locally in the knowledge base. Use when asked to: review literature on a topic, map a research area, find key papers or state-of-the-art methods, explore citation networks, build a reading list, identify research gaps, expand from a seed paper to find related work, or understand what has been published in a field.
---

# Literature Review Skill

Systematically survey a research area via arXiv + Semantic Scholar, store every paper locally, build a citation graph, and surface the most important work.

## Storage Layout

All data lives in `LITERATURE_DIR` (default: `~/Documents/personal-wiki/literature/`):

```
literature/
├── papers/           # One JSON file per paper
│   └── 2105_12345.json
├── graph.json        # Citation edges (rebuilt by build_graph.py)
└── index.json        # Fast lookup: paper_id → file path + title
```

Set `LITERATURE_DIR` env var to override the default location.

## Scripts

All scripts use `uv run` for dependency management. Run from any directory.

| Script | Purpose |
|--------|---------|
| `fetch_papers.py` | Search arXiv, fetch metadata + references/citations from Semantic Scholar, save locally |
| `build_graph.py` | Rebuild graph.json, compute metrics, rank papers |
| `visualize_graph.py` | Output DOT (Graphviz) or interactive HTML |

Scripts location: `~/.claude/skills/knowledge-literature-review/scripts/`

## Core Workflow

### 1. Seed the corpus

Search by topic:
```bash
uv run ~/.claude/skills/knowledge-literature-review/scripts/fetch_papers.py search "3D semantic instance segmentation" --max 30
```

**Start from a known paper (snowball — recommended for focused reviews):**
```bash
# Full snowball: seed → its references + papers citing it → their citers (newest work)
uv run ~/.claude/skills/knowledge-literature-review/scripts/fetch_papers.py snowball arxiv:2105.12345

# With S2 semantic recommendations too
uv run ~/.claude/skills/knowledge-literature-review/scripts/fetch_papers.py snowball arxiv:2105.12345 --recommendations

# Just find what cited the seed (forward only, newest first)
uv run ~/.claude/skills/knowledge-literature-review/scripts/fetch_papers.py expand arxiv:2105.12345 --direction forward

# Just follow references (backward, what the seed builds on)
uv run ~/.claude/skills/knowledge-literature-review/scripts/fetch_papers.py expand arxiv:2105.12345 --direction backward --depth 2
```

### 2. Build and analyze the graph

```bash
uv run ~/.claude/skills/knowledge-literature-review/scripts/build_graph.py build
uv run ~/.claude/skills/knowledge-literature-review/scripts/build_graph.py top --n 20
uv run ~/.claude/skills/knowledge-literature-review/scripts/build_graph.py stats
```

### 3. Visualize

```bash
uv run ~/.claude/skills/knowledge-literature-review/scripts/visualize_graph.py html > /tmp/literature_graph.html
# Then open /tmp/literature_graph.html in browser

uv run ~/.claude/skills/knowledge-literature-review/scripts/visualize_graph.py dot > /tmp/graph.dot
dot -Tsvg /tmp/graph.dot > /tmp/graph.svg
```

> For synthesizing the key papers into Zettelkasten notes in Logseq, apply the `knowledge-synthesis` skill.

### 4. Create wiki pages for key papers

For each highly-cited paper surfaced by `build_graph.py top`, create a Logseq page:
- File: `~/Documents/personal-wiki/logseq/pages/Paper - {Title}.md`
- Link from the daily Knowledge Synthesis Zettel
- Follow the knowledge-synthesis pattern for bidirectional linking

## When Conducting a Literature Review

1. **Start broad**: search 2-3 keyword variants, collect 30-50 papers
2. **Identify anchors**: run `build_graph.py top` — papers with highest in-corpus citation count are likely landmark works
3. **Expand depth**: run `expand` on the top 5 anchor papers (depth 1 or 2)
4. **Rebuild and re-rank**: `build_graph.py build && build_graph.py top`
5. **Find clusters**: `build_graph.py clusters` to identify sub-topics
6. **Identify gaps**: papers in your query that are poorly connected to the main cluster may represent niche or emerging work
7. **Synthesize**: run `/knowledge:synthesize-knowledge` on key papers

## Snowball vs Expand vs Search

| Command | Best for |
|---------|---------|
| `snowball` | Starting from one known paper — discovers both older foundations AND newest follow-up work |
| `expand --direction forward` | Finding only papers that cited a given paper (what built on it) |
| `expand --direction backward` | Deep-diving the reference tree (what it was built on) |
| `search` | Broad topic discovery when you don't have a seed paper |

The `snowball` command is the primary entry point for seed-paper reviews. It:
1. Fetches the seed's references (backward)
2. Fetches papers that cite the seed (forward, newest first)
3. Fetches citers of round-1 papers (second-order = most recent related work)
4. Optionally adds S2 semantic recommendations (similar papers by embedding)

## Rate Limits

- Semantic Scholar: 100 req/5 min unauthenticated. Set `S2_API_KEY` env var for higher limits (free key at semanticscholar.org).
- arXiv: no auth needed, be polite (3 sec delay between requests).
- `fetch_papers.py` handles rate limiting automatically with exponential backoff.

## Paper JSON Format

See `reference.md` for full schema. Key fields:
- `id`: canonical form `arxiv:XXXX.XXXXX`
- `references`: list of paper IDs this paper cites (outgoing edges)
- `cited_by`: list of paper IDs that cite this paper (incoming, within corpus)
- `citation_count`: Semantic Scholar's total citation count (not just within corpus)
- `tags`, `notes`: user-editable fields for annotation

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `knowledge-synthesis` | Synthesize key papers into interconnected Zettelkasten notes |
| `notebooklm` | Load papers into NotebookLM for source-grounded Q&A |
| `meta-research-workflow` | Systematic web research when no seed paper is known |
| `mermaid-diagrams` | Visualize citation graphs or research concept maps |
| `knowledge-confluence-sync` | Publish the literature review to Confluence |

## Token Budget
- SKILL.md: ~800 tokens
- reference.md: ~400 tokens (loaded on demand)
- Scripts: read only when executing
