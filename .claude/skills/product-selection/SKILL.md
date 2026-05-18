---
name: product-selection
description: "Find, validate, and compare home renovation products (fixtures, hardware, appliances, finishes) with confirmed working image URLs and product links. Handles retailer bot-protection by routing image sourcing through accessible CDNs. Runs a structured discovery interview first to narrow requirements before searching. Output is a comparison table ready to paste into a wiki page or shareable email. ALWAYS trigger this skill when the user asks to find, research, compare, or select any physical product for the 711 N 60th remodel or any home improvement project — even if they don't say 'product selection' explicitly."
---

# product-selection — Home Renovation Product Research & Validation

## What This Skill Does

Given a product category and requirements, this skill:

1. **Interviews** the user to precisely define requirements before searching (avoids wasted research)
2. **Searches** for 2–4 options across price/quality tiers
3. **Sources** working image URLs from accessible CDNs (not guessed — validated)
4. **Validates** all product page links return HTTP 200 before including them
5. **Formats** a comparison table for wiki page or stakeholder email
6. **Records** the selection decision back to the relevant wiki page

---

## Phase 0 — Discovery Interview

**Run this phase before any searching.** Use `AskUserQuestion` for each question. Do not batch — ask one at a time, wait for the answer, then adapt follow-up questions based on responses. Do not propose solutions during the interview.

**HARD GATE: Do not run any WebSearch or WebFetch until Phase 0 is complete.**

### Question 1 — Product Category
```
header: "Product type"
question: "What type of product are you selecting?"
options:
  - "Plumbing fixture (faucet, sink, shower, toilet)"
  - "Door/cabinet hardware (knobs, levers, pulls, hinges)"
  - "Appliance (range, refrigerator, hood, dishwasher)"
  - "Finish material (tile, countertop, flooring, wallcovering)"
```
*(If "Other" selected, ask for a one-line description before proceeding)*

### Question 2 — Finish / Material Constraint
```
header: "Finish"
question: "What finish or material is required?"
options:
  - "Must match an existing item — I'll specify (click Other)"
  - "Polished chrome"
  - "Brushed/satin nickel"
  - "Matte black"
```
**Key follow-up**: If "must match an existing item" — ask which item and its exact model/SKU. Finish match is the #1 cause of selection mistakes.

### Question 3 — Functional Constraint
```
header: "Function"
question: "Are there any hard functional requirements?"
options:
  - "No hard constraints beyond category and finish"
  - "Physical constraint (hole spacing, size, rough-in) — I'll specify"
  - "Occupant constraint (e.g., child/pet-proof, ADA, elderly user)"
  - "Code or permit requirement — I'll specify"
```
**Examples of occupant constraints**: Lever handles can be opened by dogs or young children — knobs required. ADA requires lever handles (contradiction — must flag if both apply).

### Question 4 — Budget
```
header: "Budget tier"
question: "What price tier should the options span?"
options:
  - "Budget + mid-range (show both, recommend mid)"
  - "Mid-range + luxury (show both, recommend mid)"
  - "Full range — budget through luxury"
  - "I have a specific per-unit budget (click Other)"
```
**For hardware**: always ask for quantity to compute total cost — $150/door sounds reasonable; $900 for 6 doors may change the decision.

### Question 5 — Visual Coordination
```
header: "Coordination"
question: "What existing items does this need to visually coordinate with?"
options:
  - "Other items in the same room — I'll list them (click Other)"
  - "An existing product already specified for this project"
  - "No specific coordination requirement"
  - "I'll describe the overall design direction (click Other)"
```
Record all coordination constraints — they narrow options significantly and prevent mismatches.

### Question 6 — Output Format
```
header: "Output use"
question: "How will you use the comparison?"
options:
  - "Email to stakeholder for approval (need inline images + links)"
  - "Update the project wiki page"
  - "Both — email and wiki"
  - "Just for my own reference"
```
This determines whether to run full image validation (email requires confirmed image URLs) or a lighter wiki-only format.

### Pre-search Checklist
Before proceeding, confirm:
- [ ] Product category is specific (not "faucet" — "single-hole bar faucet, gooseneck, 1.8 GPM")
- [ ] Finish is locked and any "must match" item is identified by model number
- [ ] Functional constraints are captured (especially occupant constraints like pet/child)
- [ ] Quantity is known if this is hardware (knobs, hinges, pulls, etc.)
- [ ] Visual coordination notes are recorded

---

## Phase 1 — Search Strategy

Run 2–3 parallel WebSearch calls based on requirements gathered in Phase 0.

### Query Templates
```
"[specific product name] [finish] [brand if constrained] comparison options"
"[specific product name] [finish] site:[accessible-brand].com"
"[specific product name] [finish] [brand] site:pinterest.com"   ← for image sourcing
```

### Identify Candidates
Find 2–4 candidates across price tiers. For each, record:
- Product name + model number/SKU (both manufacturer and retailer SKUs if different)
- Brand
- Approximate price (note source and date — prices drift)
- Retailer URLs (even blocked domains — they're for human-clickable links, not WebFetch)
- Any confirmed constraints it satisfies or violates

---

## Phase 2 — Image Sourcing

### Critical Domain Routing

**BLOCKED — Never WebFetch these for images or validation:**
| Domain | Failure mode |
|---|---|
| signaturehardware.com | 403 Forbidden |
| ferguson.com | Akamai bot (shows Akamai logo only) |
| fergusonhome.com | 403 Forbidden |
| homedepot.com | 403 Forbidden |
| lowes.com | 403 Forbidden |
| wayfair.com | 429 / 403 |
| amazon.com | 500 / robot challenge |
| walmart.com | Robot challenge |
| ebay.com | Timeout |
| faucet.com | 404 (stale URL patterns) |
| faucetdirect.com | 404 (stale URL patterns) |
| build.com → fergusonhome.com | 403 Forbidden |

These still appear in WebSearch results. Use their URLs as human-clickable links only.

**ACCESSIBLE — Use for images and validation:**
| Domain | Notes |
|---|---|
| **i.pinimg.com** | Pinterest CDN — most reliable fallback for any product |
| **emtek.com** | Full pages + CDN images |
| **baldwinhardware.com** | Product pages; images at images.baldwinhardware.com |
| **images.baldwinhardware.com** | Scene7 CDN — use `?fmt=jpeg&wid=600` |
| **kohler.com** | Accessible |
| **deltafaucet.com** | Accessible |
| **moen.com** | Accessible |
| **schlage.com** | Accessible |
| **kwikset.com** | Accessible |
| **houseofrohl.com** | Official Rohl site — accessible; images on BigCommerce CDN |
| **cdn11.bigcommerce.com** | BigCommerce CDN — usually accessible |
| Pinterest pin pages (pinterest.com/pin/...) | Fetch og:image to get pinimg.com URL |

### Image Sourcing Priority Order

For each candidate product:

**1. Official brand website CDN** (best quality, most stable)
- Fetch the brand's own product page (only if domain is on ACCESSIBLE list)
- Extract og:image or main img src
- Emtek CDN pattern: `https://www.emtek.com/media/salsify/images/[size]/[hash]-[date]-[ProductName]_EM_KO.jpg`
- Baldwin CDN: `https://images.baldwinhardware.com/is/image/Baldwin/[sku]?fmt=jpeg&wid=600`

**2. Pinterest pins** (reliable fallback for any brand)
- Search: `site:pinterest.com "[exact product name] [finish]"`
- Prefer pins with specific product name AND finish in the title (e.g., "amberley-singlehole-bar-faucet-chrome-in-2024")
- UK/regional Pinterest pins often have cleaner titles: try `uk.pinterest.com`
- Fetch the pin page: `WebFetch(url, "Find the og:image meta tag content URL. Return the full pinimg.com URL and confirm the product name and finish shown.")`
- Validate the returned i.pinimg.com URL

**3. Accessible third-party CDNs**
- houseofrohl.com products use BigCommerce CDN (cdn11.bigcommerce.com)
- Some specialty retailers (patioliving.com, focalpointhardware.com) have accessible CDNs

**If no image found after all three attempts:** Note "image available at [brand URL] — opens in browser" in the comparison. Never fabricate or guess an image URL.

---

## Phase 3 — URL Validation

**Validate every URL before including it — no exceptions.**

### Image URL Validation
```python
WebFetch(url=image_url, prompt="Is this a valid accessible image? Return HTTP status and approximate file size in KB.")
```
**Interpreting results** (WebFetch can't render binary images — it will call them "corrupted"):
- Valid signal: Binary JPEG/PNG file saved, size **> 5KB** → confirmed working image
- Invalid: HTTP 403 or 404 → discard, find alternative
- Ambiguous: File saved but < 3KB → likely a placeholder or error icon → discard

### Product Page Validation
```python
WebFetch(url=product_url, prompt="Return HTTP status and page title.")
```
- HTTP 200 + matching page title → confirmed ✓
- HTTP 404 → URL is stale; search for updated URL on the same domain
- HTTP 403 → domain is blocked; note "accessible in browser, blocked to automated access"; still usable as human link

### Validation Status Tags
Use these in the final output:
- `✓ confirmed` — WebFetch returned 200 + matching content
- `✓ image confirmed` — image URL returns JPEG/PNG > 5KB
- `⚠ browser only` — product link accessible in browser but blocked to WebFetch (signaturehardware.com, etc.)
- `❌ broken` — 404 or 403 with no alternative found

---

## Phase 4 — Format Output

### Comparison Table (wiki format)
```markdown
## [Category] Options

**Requirements**: [finish] · [functional constraint] · [coordination note]

| Option | Brand/Model | Price | Image | Link | Status |
|--------|-------------|-------|-------|------|--------|
| ⭐ A (Recommended) | Brand Model SKU | ~$X | [confirmed image URL] | [product link] | ✓ confirmed |
| B | ... | ~$X | [confirmed image URL] | [product link] | ✓ confirmed |
| C | ... | ~$X | N/A | [product link] | ⚠ browser only |

**Recommendation**: [1–2 sentences — finish match, value, design rationale]
**Total cost** (if hardware): [unit price × quantity] = [range]
```

### Email Format (stakeholder-shareable)
When output is for email, use inline images with Markdown:
```markdown
### ⭐ Option A — [Brand Model] · ~$[price] · RECOMMENDED

![Alt description](https://confirmed-image-url.jpg)
👉 [View on [Site]](https://product-page-url)

| | |
|---|---|
| **Brand** | ... |
| **Model** | ... |
| **Finish match** | [specific note] |
| **Price** | ~$X |
```

**Email format rules:**
- Every option must have either a confirmed inline image OR an explicit note explaining why the image isn't embeddable
- All product links must be validated (200 or noted as "browser only")
- Total cost at bottom if hardware
- Summary table of recommendations at the end

---

## Phase 5 — Record Decision

After the user selects an option, update the relevant wiki page in `logseq/pages/`:

1. **Update the options table** to mark the selected item
2. **Move item from "Outstanding Items — Owner's Side"** to "Decisions Made / Locked"
3. **Add status**: `[ ] Pending approval` → `[x] Approved` → `[ ] Ordered`
4. **Record the rationale** (1 sentence — why this option was chosen)

```markdown
## Decisions Made / Locked
- **[Category]**: [Brand Model SKU] — [finish] — [rationale, e.g., "matches Levi faucet finish, same brand"] — [x] Approved / [ ] Ordered
```

---

## Known Product Category Sources

### Plumbing Fixtures
| Brand | Website | Image access | Notes |
|---|---|---|---|
| Signature Hardware | signaturehardware.com | ❌ 403 | Use Pinterest pins for images |
| Rohl / Perrin & Rowe | houseofrohl.com | ✓ | Images on BigCommerce CDN |
| Kohler | kohler.com | ✓ | CDN at content.kohler.com |
| Delta / Brizo | deltafaucet.com | ✓ | |
| Moen | moen.com | ✓ | |
| Hansgrohe | hansgrohe-usa.com | ✓ | |

### Door & Cabinet Hardware
| Brand | Website | Image access | Notes |
|---|---|---|---|
| Emtek | emtek.com | ✓ | Images at /media/salsify/images/ |
| Baldwin Reserve | baldwinhardware.com | ✓ | Scene7 CDN at images.baldwinhardware.com |
| Schlage | schlage.com | ✓ | |
| Kwikset | kwikset.com | ✓ | |
| Top Knobs | topknobs.com | check | |

### Appliances
| Brand | Notes |
|---|---|
| Viking | vikingrange.com |
| Bosch | bosch-home.com/en-us/ |
| Zephyr | zephyronline.com |
| Wolf | subzero-wolf.com |

### Tile & Stone
| Brand | Notes |
|---|---|
| Zia Tile | ziatile.com |
| Fireclay | fireclaytile.com |
| Ann Sacks | annsacks.com |
| Caesarstone | caesarstoneus.com |

---

## Common Failure Modes & Recovery

| Failure | Cause | Fix |
|---|---|---|
| Image URL returns 403/404 | Retailer CDN blocking or stale URL | Try Pinterest pin for same product |
| Image returns < 3KB | Placeholder/icon served instead | URL is wrong; search for correct CDN path |
| Product page returns 404 | Retailer restructured URLs | Re-search `site:[domain] "[product name]"` |
| No image found on any source | Product only sold on blocked retailer | Note "images at [URL] — opens in browser"; provide description instead |
| Pinterest pin shows wrong finish | Multiple finishes share pins | Search for finish-specific pin (e.g., add "chrome" or "polished" to search) |
| Price seems wrong | Prices drift; older search results | Cross-reference 2 sources; note "approximate" and date |

---

## Quality Checklist Before Delivering Output

- [ ] All image URLs return JPEG/PNG > 5KB (or explicitly noted as unavailable)
- [ ] All product page links return 200 or noted as "browser only"
- [ ] Finish described exactly matches requirement (e.g., "polished chrome" ≠ "chrome" ≠ "brushed chrome")
- [ ] Model numbers confirmed against ≥ 2 sources
- [ ] Prices marked "approximate" with basis noted
- [ ] Total cost calculated if hardware (unit × quantity)
- [ ] At least 2 price tiers represented
- [ ] Recommendation includes finish-match and design rationale
- [ ] Functional constraints satisfied (checked against Phase 0 answers)
- [ ] Occupant constraints noted (dog-proof, ADA, child-safe, etc.)

---

## Related Skills

- [[design-review]] — Verify selected products against CD set specs before ordering
- [[knowledge-synthesis]] — Synthesize product research into permanent wiki notes
- [[handy:plan]] — Plan installation of selected products
