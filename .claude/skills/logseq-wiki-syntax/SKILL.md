---
name: logseq-wiki-syntax
description: "Reference for writing and formatting Logseq wiki pages in Tyler's personal wiki. Covers bullet syntax, indentation, page properties, linking strategy, image embedding, filename rules, and the two main page styles. Apply whenever creating or editing pages in logseq/pages/ or logseq/journals/."
---

# logseq-wiki-syntax

Apply this skill whenever writing or editing pages in `/home/tstapler/Documents/personal-wiki/logseq/`.

---

## File Locations

| Content type | Path | Filename format |
|---|---|---|
| Concept/knowledge pages | `logseq/pages/*.md` | `Concept Name.md` (Title Case) |
| Daily journals | `logseq/journals/*.md` | `YYYY_MM_DD.md` |
| Personal photos / screenshots | `logseq/assets/` | `descriptive-kebab-name.jpg` |
| CDN product / reference images | Embed inline as full URL | — |

---

## CRITICAL: Android Filename Rules

**NEVER use these characters in filenames**: `: * ? " < > | \`

These fail on Android FAT32/exFAT where the wiki syncs.

| Character | Safe substitute | Example |
|---|---|---|
| `:` (colon) | `-` (hyphen) | `DDD- Aggregate.md` not `DDD: Aggregate.md` |
| `/` (slash) | `___` (triple underscore) | Logseq namespace separator |

When a page title needs a colon (e.g. a book title), use `title::` in the page property to set the display name, and use a hyphen in the actual filename.

```markdown
title:: World War Z: An Oral History of the Zombie War
```

---

## Two Main Page Styles

### Style 1 — Zettelkasten (preferred for knowledge pages)

Used for: concepts, technologies, people, tools, events.

```markdown
tags:: [[Tag1]], [[Tag2]], [[Tag3]]

# Page Title

- **Core Definition**: One-sentence explanation linking to [[Related Concept]]
  - Supporting detail
  - More context

## Section Header

- Key point about this section
  - Sub-point with [[Linked Page]]
  - Another sub-point

## Related Concepts

- [[Related Page 1]] — one-line description of the relationship
- [[Related Page 2]] — one-line description

#[[Tag]] #[[Another Tag]]
```

### Style 2 — Bullet-Only (preferred for notes, events, lookbooks)

Used for: meeting notes, outfit planning, project tracking, journals.

```markdown
tags:: [[Tag1]], [[Tag2]]

- **Event:** Name of the event
- **Date:** YYYY-MM-DD
- ## Section Name
	- Key point
		- Detail
	- Another point
- ## Another Section
	- Content here
```

Note: `- ## Header` (header as a bullet item) is the Logseq-native way to create a collapsible section within a bullet outline. Use it for event/lookbook pages. Use standalone `## Header` (not in a bullet) for Zettelkasten knowledge pages.

---

## Page Properties

Properties go on the **very first lines** of the file, before any other content.

```markdown
tags:: [[Tag1]], [[Tag2]], [[Tag3]]
title:: Display Title With Colon: Subtitle
category:: Technology
```

| Property | When to use | Format |
|---|---|---|
| `tags::` | Always — on most pages | Comma-separated `[[Wiki Links]]` |
| `title::` | When filename can't match title (colon in title) | Plain text with the real title |
| `category::` | For tech/science/project classification | Single word: `Technology`, `Science`, `Project` |

---

## Indentation Rules

**Use tabs, not spaces** for nested bullets. Each level of nesting = one tab.

```markdown
- Root level bullet
	- One tab indent (child)
		- Two tabs (grandchild)
			- Three tabs (great-grandchild)
```

In markdown source, this looks like `\t` characters. The Logseq editor handles this automatically; when writing raw markdown, use actual tab characters.

---

## Linking Strategy

### When to Link

- Link concepts that have (or should have) their own wiki page
- Link on first mention in each major section — not every occurrence
- Don't spam links: prefer meaningful connections over exhaustive tagging
- Link people, tools, concepts, events — not generic words

### Link Formats

| Type | Format | Example |
|---|---|---|
| Page link | `[[Page Name]]` | `[[Incident Management]]` |
| People | `[[First Last]]` | `[[Alan Turing]]` |
| Inline tag | `#[[Tag Name]]` | `#[[Computer Science]]` |
| Page-level tag | `tags:: [[Tag]]` | in properties block |

### Linking Rules

1. **People**: Always link full name. `[[Tyler Stapler]]`, `[[Bekah Reynolds]]`
2. **Technologies and tools**: Link on first mention. `[[Kubernetes]]`, `[[Grafana]]`
3. **Concepts**: Link when the concept has a page or deserves one. `[[Observability]]`
4. **Events**: Link to the event page. `[[Nora's Wedding Outfit]]`, `[[Lexi's Wedding Outfit]]`
5. **Cross-wiki references in journals**: Always link to the synthesis page. `See [[Knowledge Synthesis - 2026-05-25]]`
6. **Clothing/wardrobe brands**: Link brand pages. `[[Dandy Del Mar]]`, `[[Thursday Boot Co.]]`

### Related Concepts Section

At the bottom of knowledge pages, list related pages with a one-line relationship note:

```markdown
## Related Concepts

- [[Prometheus]] — metrics storage backend commonly used with Grafana
- [[Alertmanager]] — handles alert routing from Grafana alerting rules
- [[Loki]] — log aggregation that integrates natively with Grafana
```

---

## Image Embedding

### Personal Photos (assets)

Copy to `logseq/assets/` with a descriptive kebab-case name, then reference with a relative path:

```markdown
![Bekah's black floral maxi dress](../assets/bekah-black-floral-maxi.jpg)
```

- Path is always relative from `logseq/pages/` → `../assets/`
- Name files descriptively: `bekah-black-floral-maxi.jpg` not `IMG_3847.jpg`
- Formats: `.jpg`, `.png`, `.webp` all work

### CDN / Product Images

Embed the full URL directly — only use verified, accessible URLs (test with curl or WebFetch first):

```markdown
![Suitsupply Roma Blazer](https://cdn.suitsupply.com/image/upload/.../C261003_1.jpg)
```

**Never guess CDN paths.** Always verify the URL returns a real image before embedding.

### Image Placement

Images sit as bullet items, indented to their parent context:

```markdown
- ### Product Name · $Price
	- ![Product image](https://cdn-url/image.jpg)
	- [Product link](https://retailer.com/product) · Key details
	- **Why it works:** Pairing rationale
```

---

## Tables

Tables are standard markdown, written inside a bullet item (or standalone in Zettelkasten style):

```markdown
- | Column A | Column B | Column C |
- |---|---|---|
- | Value 1 | Value 2 | Value 3 |
```

In bullet-only pages, each table row is its own bullet. In Zettelkasten pages with standalone headers, tables can be written without the leading `- `.

---

## Tags: Two Patterns

### Page-level tags (preferred)

```markdown
tags:: [[Wedding]], [[Outfit]], [[Clothing]], [[Events]]
```

Goes on line 1. Shows the page in all those tag graphs in Logseq.

### Inline tags (supplemental)

```markdown
#[[Routing Protocols]] #[[Link-State Protocol]]
```

Used at the bottom of a page, or inline to tag a specific bullet. Use for concepts that are relevant but shouldn't appear in the top-level property list.

### Tag Count Guidelines

- Use **3–7 tags** per page
- Mix: domain tags (`[[Observability]]`), method tags (`[[Design Patterns]]`), category tags (`[[Tools]]`)
- Avoid over-tagging with generic terms that don't add graph value

---

## Journal Entry Format

Journals are bullet-only. No title — the date is the identity.

```markdown
- Worked on [[Project Name]] — key decision or outcome. See [[Knowledge Synthesis - YYYY-MM-DD]]
- - 📝 Voice note (HH:MM:SS)
	- Quick capture from voice: [[Concept]] needs research
- Met with [[Person Name]] about [[Topic]] — key takeaway
```

Rules:
- Each thought is a root bullet
- Link every meaningful concept, person, or project
- If a topic needs follow-up: tag with `[[Needs Research]]`
- If synthesized into a page: add `See [[Knowledge Synthesis - YYYY-MM-DD]]`

---

## Outfit / Event Lookbook Format

```markdown
tags:: [[Wedding]], [[Outfit]], [[Clothing]], [[Events]]

- **Event:** Event Name
- **Dress Code:** Dressy Casual / Garden Formal / etc.
- **Location:** City · Season · Climate note
- ## Our Looks
	- **Person A** — brief description (owned / purchase needed)
		- ![Photo](../assets/photo.jpg)
		- Color and style notes
	- **Person B** — summary of full look
	- *Coordination: 1–2 sentences on palette logic*
- ## Person B's Look
	- *Palette framing line*
	- ### ⭐ Option Name · $Price *(recommended)*
		- ![Image](https://cdn-url)
		- [Product link](url) · Size · Key details
		- **Why it works:** Specific pairing rationale
	- ### Notes
		- **Together:** Bridge note connecting the two looks
		- Sizing/tailoring notes
- ## Related
	- [[Related Page]]
```

---

## Anti-Patterns to Avoid

| Anti-pattern | Why | Correct approach |
|---|---|---|
| Mixing tabs and spaces for indentation | Breaks Logseq parsing | Use tabs only |
| Guessing CDN image URLs | Results in broken images | Always verify URL before embedding |
| Colons in filenames | Fails on Android | Use hyphen instead |
| Linking every word | Creates noise in the graph | Link on first meaningful mention per section |
| Properties after content | Logseq only reads properties at the top | `tags::` must be on line 1 |
| Skipping `tags::` | Page won't appear in tag graphs | Always add 3–7 relevant tags |
| Using spaces instead of `[[links]]` for cross-references | No graph edge created | Always use `[[Page Name]]` syntax |

---

## Related Skills

- [[knowledge-synthesis]] — Full workflow for creating Zettelkasten notes from research
- [[outfit-event-planner]] — Builds lookbook pages using this syntax
- [[clothing-product-sourcer]] — Sources product images and links for wiki pages
