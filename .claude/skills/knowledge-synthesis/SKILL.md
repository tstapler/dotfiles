---
name: knowledge-synthesis
description: Synthesize knowledge from multiple sources into Zettelkasten notes for Logseq. Use when creating wiki pages, integrating academic research, or building interconnected knowledge with [[links]] and #[[tags]].
---

# Knowledge Synthesis

Synthesize knowledge from multiple sources into interconnected Zettelkasten notes.

## When to Use This Skill

**Complex topics requiring**:
- Multi-source research (3+ authoritative sources)
- Academic literature integration
- Book zettels with author information
- Systematic concept mapping
- Both supporting and contradicting perspectives

**Simple topics** (single source, straightforward): Handle directly without full workflow

## Core Workflow

> For systematic web research before synthesizing, apply the `meta-research-workflow` skill.

### 1. Research Phase

- Search multiple source types (academic, books, authoritative sites)
- Find foundational works and key authors
- Identify supporting AND contradicting evidence
- Cross-reference across sources

### 2. Synthesis Phase

- Create main page with comprehensive coverage
- Create supporting pages for related concepts
- Create book zettels for referenced works
- Integrate with existing knowledge network

### 3. Integration Phase

- Update journal with synthesis summary
- Link to related existing pages
- Ensure bidirectional connections

## Zettelkasten Structure

Every note should include:

1. **Core Definition** - Brief, clear explanation
2. **Background/Context** - Origins, key figures
3. **Key Characteristics** - Essential features
4. **Applications/Usage** - Use cases
5. **Related Concepts** - `[[links]]` to other concepts
6. **Significance** - Why it matters
7. **Related Topics** - `#[[Tag1]] #[[Tag2]]`

## Linking Strategy

| Type | Format | Examples |
|------|--------|----------|
| People | `[[Name]]` | `[[Alan Turing]]` |
| Concepts | `[[Concept]]` | `[[Machine Learning]]` |
| Technologies | `[[Tech]]` | `[[Kubernetes]]` |
| Retailers | `[[Name]]` | `[[Lowe's]]`, `[[IKEA]]`, `[[Amazon]]` |
| Products/Parts | `[[Product Name]]` | `[[IKEA VIDGA Curtain Track]]` |
| Tags | `#[[Tag]]` | `#[[Computer Science]]` |

## Tagging Guidelines

Use 3-7 tags per note:
- **Disciplinary**: `#[[Computer Science]]`, `#[[Philosophy]]`
- **Methodological**: `#[[Design Patterns]]`, `#[[Best Practices]]`
- **Categorical**: `#[[Tools]]`, `#[[Concepts]]`, `#[[Theories]]`
- **Contextual**: `#[[Business]]`, `#[[Open Source]]`

## Quality Standards

- Accurate attribution with source URLs
- Meaningful bidirectional links (not link spam)
- Multi-source validation for complex topics
- Both supporting and critical perspectives
- Comprehensive coverage of major aspects

## File Locations

- **Pages**: `/logseq/pages/*.md`
- **Journals**: `/logseq/journals/YYYY_MM_DD.md`

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `knowledge-literature-review` | Survey a research area and build a citation graph before synthesizing |
| `meta-research-workflow` | Systematic multi-source web research before writing notes |
| `notebooklm` | Query source-grounded answers from uploaded documents |
| `knowledge-confluence-sync` | Publish synthesized notes to a Confluence wiki |
| `mermaid-diagrams` | Create concept maps or knowledge-graph diagrams |
| `home:2-research` / `home:full` | Research phase uses the Product & Retailer Zettel Template below when surfacing materials |
| `product-selection` | Uses the Product & Retailer Zettel Template for candidates and the Decision Write-Back Pattern to record the final pick |

## Book Zettel Template

For referenced books, create dedicated pages:
- Title as page name
- Author with credentials
- Key concepts covered
- Cross-references to related concepts
- Tags: `#[[Books]]`, `#[[Authors]]`

## Product & Retailer Zettel Template

For physical products, parts, and retailers encountered during research (e.g. home project planning, purchases):

**Check first, don't duplicate.** Before creating a page, `Grep`/`Glob` `logseq/pages/` for an existing page on that retailer/product/part. If one exists, read it and only append genuinely new information (a better price, a new source, a caveat) — never write a redundant duplicate page. Skip creating a page at all for one-off consumables (a single tube of caulk) that won't recur across future research.

Create a page when the retailer/product/part is distinctive and likely to come up again:
- **Retailer pages** (`logseq/pages/<Retailer Name>.md`): what they carry, price positioning, any recurring pros/cons noted across projects.
- **Product/part pages** (`logseq/pages/<Product Name>.md`): core definition, price/quality tier, why recommended (or not), at least one **source URL** — never state a price or quality claim without attribution.
- Link every product page to its retailer (`[[Retailer]]`) and to related products/concepts.
- Tags: `#[[Products]]`, plus a category tag (e.g. `#[[Home Improvement]]`, `#[[Tools]]`).
- Link back to the context that surfaced it (e.g. a house/location page, project page) so the page is discoverable from both directions.

## Decision Write-Back Pattern

When a synthesis or research process ends in the user picking one option (a product, a method, an approach), record that choice back to the relevant wiki page rather than letting the decision live only in a chat transcript or a one-off comparison table. Any skill that produces a decision should use this pattern instead of inventing its own logging format:

1. **Locate or create the relevant page** — the project/room/topic page the decision belongs to (e.g. a kitchen remodel page, a `home_plans/<project>/plan.md`).
2. **Update or add a `## Decisions Made / Locked` section**:
   ```markdown
   ## Decisions Made / Locked
   - **[Category]**: [[Chosen Option]] — [key differentiator, e.g. finish match, price, longevity] — [rationale in one sentence] — [ ] Approved / [ ] Ordered
   ```
3. **Move the item out of any "outstanding" or "options under consideration" list** it was previously tracked in, so the page doesn't show the same decision as both pending and resolved.
4. **Link the chosen option** to its Product & Retailer Zettel (above) if one exists, so the decision and the product knowledge stay connected.
5. **Record the rationale in one sentence** — why this option won, not a restatement of its specs (those live on the product page).

Used by: `product-selection` (recording a chosen product), `home:3-plan` (recording a chosen method/approach in a plan's Decisions & Open Questions section).
