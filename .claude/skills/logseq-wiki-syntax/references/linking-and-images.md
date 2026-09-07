# Linking Strategy, Image Embedding, and Tables

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

## Tables

Tables are standard markdown, written inside a bullet item (or standalone in Zettelkasten style):

```markdown
- | Column A | Column B | Column C |
- |---|---|---|
- | Value 1 | Value 2 | Value 3 |
```

In bullet-only pages, each table row is its own bullet. In Zettelkasten pages with standalone headers, tables can be written without the leading `- `.
