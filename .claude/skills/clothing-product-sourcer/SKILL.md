---
name: clothing-product-sourcer
description: "Research, find, and compare specific clothing items (blazers, trousers, shirts, shoes, ties, pocket squares) across multiple retailers at a target price point, style, and size. Validates product availability and sources working images. Outputs a comparison table ready for a wiki page. TRIGGER when the user needs to find a specific type of clothing item, compare options across brands, or fill a gap identified during outfit planning."
---

# clothing-product-sourcer

## What This Skill Does

Given a clothing category and requirements, this skill:

1. **Clarifies** requirements (style, color/pattern, size, budget, occasion)
2. **Searches** 3–5 retailers across price tiers
3. **Sources** product images from accessible CDNs
4. **Notes** sizing caveats and tailoring requirements
5. **Outputs** a wiki-ready comparison with links, images, and "why it works" notes

---

## Phase 0 — Requirements Definition

Collect the following before searching. Adapt questions based on what's already known from context (don't re-ask if the user already provided it).

### Item Category
What are you looking for?
- Blazer / Sport coat
- Suit jacket (to be worn as odd jacket)
- Trousers / dress pants
- Dress shirt
- Shoes (loafer, Oxford, Chelsea, etc.)
- Tie
- Pocket square
- Full outfit

### Style Requirements
- Formality level: Black Tie / Formal / Dressy Casual / Smart Casual / Casual
- Pattern preference: Solid / Herringbone / Houndstooth / Windowpane / Check / Floral / Paisley
- Color direction: warm neutrals / cool neutrals / earth tones / bold / specific color family

### Color Palette Context
If sourcing for a coordinated couple's look:
- Anchor piece colors (to echo or contrast)
- Partner B's confirmed pieces (to avoid clashing)
- Overall palette concept (e.g., "Warm Earth meets Bold Floral")

### Size
Always capture exact size before searching — avoid finding items that won't fit.

| Category | Size notes |
|---|---|
| Blazers (S/M/L brands) | S = 36–38" chest typically |
| Blazers (numeric chest) | 36, 38, 40… verify brand's chart |
| Trousers | W × L; note if brand sells even waists only (Suitsupply) |
| Shirts | S / M / L or neck × sleeve |
| Shoes | US size |

### Budget
- Under $100 / $100–$250 / $250–$500 / $500+ / No limit
- Bundle pricing: note if jacket+trouser bundles change the effective per-item price

---

## Phase 1 — Retailer Search Strategy

Search in parallel across price tiers. Always cover at least 3 brands.

### Tier Map by Category

**Blazers / Sport Coats**
| Tier | Brands | Price range |
|---|---|---|
| Budget | Express, J.Crew (sale), Banana Republic (sale), H&M | $50–$250 |
| Mid | J.Crew, Faherty, Taylor Stitch, Buck Mason | $200–$450 |
| Upper mid | Suitsupply, Club Monaco, Reiss | $450–$800 |
| Premium | Drake's, Sid Mashburn, Ring Jacket | $800+ |

**Trousers**
| Tier | Brands | Price range |
|---|---|---|
| Budget | Express, J.Crew, Banana Republic | $50–$130 |
| Mid | Suitsupply, Everlane, Todd Snyder | $100–$250 |
| Premium | Incotex, Suitsupply Havana | $200–$400 |

**Shoes**
| Tier | Brands | Price range |
|---|---|---|
| Budget | Clarks, Steve Madden | $80–$150 |
| Mid | Thursday Boot Co., Amberjack, Beckett Simonon | $150–$250 |
| Upper mid | Allen Edmonds, Grenson | $250–$450 |
| Premium | Crockett & Jones, Edward Green | $500+ |

**Ties & Pocket Squares**
- The Tie Bar: $14–$28 — large selection, accessible CDN, reliable images
- Drake's: £50–£175 — investment pieces, madder silk
- Spier & Mackay: ~$35

---

## Phase 2 — Domain Routing

### Accessible Domains (WebFetch works)

| Domain | Notes |
|---|---|
| thetiebar.com | Product pages + Shopify CDN images |
| thursdayboots.com | Full access; CDN at thursdayboots.com/cdn/shop |
| amberjack.shop | Full access |
| abercrombie.com | Full access; CDN images |
| sezane.com | Images at media.sezane.com |
| thereformation.com | Images at media.thereformation.com |
| dandydelmar.com | Partial — try product pages directly |
| cdn.suitsupply.com | Always accessible — direct image CDN |

### Blocked / Unreliable Domains (links only, no image fetch)

| Domain | Status | Workaround |
|---|---|---|
| express.com | 403 | User screenshots → assets folder |
| fahertybrand.com | 403 | Images sometimes via fahertybrand.com/cdn/shop/files/ |
| jcrew.com | 503 (intermittent) | Try product pages directly; images via s7-img-facade |
| bananarepublic.gap.com | 404/redirect | Search for direct product URLs; CDN via gap.com |
| balticborn.com | 403 | Links only |
| vicicollection.com | 403 | Links only |
| lulus.com | 403 | Links only |
| freepeople.com | 403 | Links only |
| buckmason.com | 404 | Try direct product pages |
| taylorstitch.com | 404/500 | Try direct product pages |
| suitsupply.com category pages | 404 | Use direct product URLs (e.g. /en-us/men/jackets/[slug]/[sku].html) |

### Image CDN Patterns (when product page is blocked)

| Brand | CDN pattern |
|---|---|
| Suitsupply | `https://cdn.suitsupply.com/image/upload/[transform]/products/[type]/default/Summer/[SKU]_1.jpg` |
| The Tie Bar | `https://cdn.shopify.com/s/files/1/0505/7019/9217/files/PDP_[sku]_main.jpg` |
| Thursday Boots | `https://thursdayboots.com/cdn/shop/files/[product-slug].jpg` |
| Abercrombie | `https://img.abercrombie.com/is/image/anf/[code]` |
| J.Crew | `https://www.jcrew.com/s7-img-facade/[SKU]_[COLOR]_m` |
| Faherty | `https://fahertybrand.com/cdn/shop/files/[filename]` |

---

## Phase 3 — Sizing Verification

Always check and note sizing caveats. Common traps:

**Blazers**
- S/M/L brands: S typically = 36–38" chest. Verify per-brand.
- Numeric chest brands (Suitsupply, Brooks Brothers): 36, 38, 40, 42. Tyler = 36 or 38.
- Faherty: S = 38–40". If ordering a Faherty S, Tyler's at the low end — may need to check.
- Short vs Regular vs Long: Short = shorter torso (under ~5'8"). Regular = standard.
- Final sale items: flag prominently — no returns if wrong size.

**Trousers**
- Suitsupply: even waist sizes only (32W, 34W…). For 31W, order 32W + tailor in 1". (~$20–30)
- Hem: order long, tailor to 32L at same visit.
- Express: W31 L32 available — no tailoring needed for Tyler.

**Shirts**
- Ministry of Supply S fits Tyler.
- DDM S fits Tyler.

---

## Phase 4 — Output Format

Present each option as:

```markdown
### ⭐ [Brand] [Product Name] · [Price]
- ![Image alt](https://cdn-image-url)
- [Product link](url) · [Fabric/material] · [Key construction notes]
- **Your size:** [size] [tailoring note if needed]
- **Why it works:** [Specific pairing rationale — reference the anchor piece colors, the palette, the occasion]
- **Total:** [if bundle pricing applies]
```

**Comparison table at end:**

| Option | Price | Fabric | Pattern | Size | Tailoring needed? |
|---|---|---|---|---|---|
| ⭐ [Brand] | $X | linen | herringbone | S / 38 | No |
| [Brand] | $X | ... | ... | ... | Yes — tailor waist |

---

## Phase 5 — Wiki Update

After user selects an option, update the relevant lookbook page:

1. Add the item under the correct section with image and product link
2. Update the `## Our Looks` summary to include the confirmed piece
3. Add sizing/tailoring notes
4. Mark look as `✅ Confirmed:` if the full look is now decided

---

## Known Failure Modes

| Failure | Cause | Fix |
|---|---|---|
| Image URL 403/404 | Retailer CDN blocking | Check known CDN patterns; note "screenshot to assets" if blocked |
| Product page 404 | Retailer changed URL structure | Search `site:[domain] "[product name]"` |
| Only one size available | Inventory running low | Note prominently; recommend ordering soon |
| Bundle price not reflecting | Cart quirk | Note that $249 bundle price reflects in cart — total ≠ sum of individual prices |
| Numeric vs S/M/L confusion | Brand uses both | Always verify the brand's specific sizing chart |
| "Short" vs "Regular" jacket length | Short = shorter torso | Flag if user's height suggests Regular or Long |

---

## Related Skills

- [[outfit-event-planner]] — The full outfit coordination workflow; calls this skill for gap research
- [[product-selection]] — General product research for home renovation items
