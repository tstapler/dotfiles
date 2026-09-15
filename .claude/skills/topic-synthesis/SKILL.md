---
name: topic-synthesis
description: Given a brief note describing a topic you want researched, research it (web search across authoritative sources) and write the findings into the personal Logseq wiki as atomic, cross-linked pages, then log it in today's journal. Use for prompts like "synthesize <topic> to my wiki", "research X and add it to my notes", or "look into Y and write it up" — for a *new* topic, not a video game (→ `game-guide-synthesis`) and not content you already have in hand from one specific source (→ `knowledge/synthesize-knowledge`).
---

# Topic Synthesis

Turn a one-line topic request into researched, atomic wiki pages — the generic counterpart to `game-guide-synthesis` for anything outside games.

## When to Use

- User gives a short prompt naming a topic or question and wants it researched and added to the wiki, with no source material already in hand
- Not a video game topic (use `game-guide-synthesis` — game wiki conventions, patch-note sourcing)
- Not synthesis of a specific source/URL you already have (use `knowledge/synthesize-knowledge` — daily consolidation Zettel)
- Follow-up on a topic already covered in the wiki: extend it, don't duplicate

## Workflow

1. **Recall** — resolve the wiki root and check for existing pages on the topic, per `knowledge-synthesis`'s Wiki Root Resolution. Read what's there before writing; extend rather than duplicate.
2. **Research** — apply `meta-research-workflow`: break the topic into subtopics if it's broad, search multiple authoritative sources, cross-check anything stated as fact, and say so instead of inventing a number/claim no source documents.
3. **Answer first** — give the user a direct summary in chat before or alongside writing to the wiki; don't make them open a file to get what they asked for.
4. **Synthesize into atomic pages** — apply `knowledge-synthesis`'s atomicity rule and Zettelkasten structure: one page per distinct concept, cross-linked, tagged. Add a hub/index page only if the topic naturally splits into multiple sub-concepts; a narrow topic just gets one page.
5. **Journal log** — per `knowledge-synthesis`'s Integration Phase, add the nested-bullet entry to today's journal listing what was asked and which pages were created or updated.

## Related Skills

- `knowledge-synthesis` — atomicity rule, wiki root resolution, linking/tagging, journal integration pattern; load before writing any page
- `meta-research-workflow` — systematic web research methodology
- `logseq-wiki-syntax` — formatting, filenames, linking mechanics
- `game-guide-synthesis` — use instead for video game topics
- `knowledge/synthesize-knowledge` — use instead when you already have specific source content in hand for the daily consolidation Zettel
