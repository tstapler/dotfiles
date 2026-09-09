---
name: game-guide-synthesis
description: Answer a question about a video game and synthesize the answer plus related mechanics into atomic Logseq wiki pages. Use when the user asks a game-mechanics/lore/item/how-to question about a game they're playing and wants both a direct answer and their personal wiki updated — e.g. "what does X do in No Man's Sky", "how do I get Y", or explicit phrasing like "synthesize this game info to my wiki."
---

# Game Guide Synthesis

Answer game questions AND grow the wiki's game-guide coverage in the same pass — one page per mechanic/item/location, cross-linked to a per-game hub page.

## When to Use

- User asks a specific question about a game they're playing (mechanic, item, location, how-to)
- User wants both an answer now and a durable note for next time
- Follow-up questions on a game already covered in the wiki (extend it, don't duplicate)

## Workflow

1. **Recall** — check the wiki for an existing hub page for the game (`<Game Name>.md`) and any existing pages on the topic asked about. Read them before answering; extend rather than duplicate. Apply `knowledge-synthesis`'s Wiki Root Resolution to find the wiki root, and `logseq-wiki-syntax` for all formatting.
2. **Research** — game mechanics, especially recent-update content, go stale in your training data fast. Use WebSearch and read a couple of sources before answering:
   - Official patch notes / developer site — authoritative on what changed and when
   - A dedicated wiki for the game (Fandom or similar) for mechanical detail
   - A recipe/calculator/guide site for exact numbers when the game has crafting/economy systems
   - Cross-check at least two sources for anything written as fact; if the publisher hasn't documented a number (yield tables, drop rates), say so instead of inventing one
3. **Answer first** — give the user a direct, complete answer in chat before or alongside writing to the wiki. Don't make them open a file to get the answer they asked for.
4. **Synthesize into atomic pages** — apply `knowledge-synthesis`'s atomicity rule: one page per concept (item, mechanic, building, vehicle), not one sprawling page per question. Create or update:
   - A hub page for the game if it doesn't exist yet (`<Game Name>.md`, Style 1 Zettelkasten, `## Related` listing sub-pages)
   - One page per distinct entity the question touches, cross-linked (each sub-page's `## Related` points to the others and back to the hub)
   - The game hub into the wiki's top-level `Games.md` related list, if not already there
5. **Journal log** — per `knowledge-synthesis`'s Integration Phase, add a short entry to today's journal (`journals/YYYY_MM_DD.md`) listing what was asked and which pages were created or updated.

## Page Conventions for Games

- Hub page: `<Game Name>.md` — one-paragraph definition, then whatever sections fit the game (`## Core Pillars`, `## Major Updates`, etc.), plus `## Related` linking every sub-page
- Sub-pages: name each after the in-game entity as the game/its wiki names it (`Gravitino Coil.md`). **If the term is generic enough that it could plausibly mean something else** — a real-world word, a common noun, a term another game or another page in the wiki could also use (`Corvette`, `Colossus`, `Settlement`, `Industrial Waste`) — prefix the filename and its `# Heading` with the game's short code (`NMS Corvette.md`, `# NMS Corvette`), so `[[Corvette]]` on its own stays free for something unrelated. Don't add a bare alias for the unprefixed term — that would silently reintroduce the same collision. Leave distinctive, game-coined terms unprefixed (`Gravitino Coil`, not `NMS Gravitino Coil`) — the prefix is for disambiguation, not branding every page. In the body text and bold definition, use the term's natural in-game name (`**Corvette** — ...`) even on a prefixed page; only the filename/heading/cross-links carry the prefix.
- Tags: `tags:: [[<Game Name>]], [[Games]]` on sub-pages — add a third tag only when a page clearly needs one (e.g. `[[Crafting]]`)
- Cite the specific update/version number and date when a mechanic is new or still actively changing — a future lookup needs to know whether this is still current

## Related Skills

- `logseq-wiki-syntax` — formatting, filenames, linking; load before writing any page
- `knowledge-synthesis` — Zettelkasten atomicity, wiki root resolution, journal integration pattern; load before synthesizing
