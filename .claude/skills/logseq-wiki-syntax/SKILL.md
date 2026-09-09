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
| `?` (question mark) | drop it | `Tidy First.md` not `Tidy First?.md` |
| `/` (slash) | `___` (triple underscore) | Logseq namespace separator |

When a page title needs a colon or question mark (e.g. a book title like "Tidy First?"), drop/substitute the character in the actual filename, and use `title::` in the page property to preserve the real display title (`title:: Tidy First?`).

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

For the full journal-entry and outfit/event lookbook templates, see [references/page-templates.md](references/page-templates.md).

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

## Linking, Images, and Tables

Link concepts, people, tools, and events on first mention per section — don't spam links on generic words. Use `[[Page Name]]` for pages, `#[[Tag Name]]` for inline tags. Personal photos go in `logseq/assets/` with descriptive kebab-case names and relative paths; CDN/product images are embedded as verified full URLs (never guess a CDN path — confirm it resolves before embedding).

Full link-format table, linking rules, image embedding patterns, and table syntax: [references/linking-and-images.md](references/linking-and-images.md).

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
