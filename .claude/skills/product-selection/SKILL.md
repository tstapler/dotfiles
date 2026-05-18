---
name: product-selection
description: "Find, validate, and compare home renovation products (fixtures, hardware, appliances, finishes) with confirmed working image URLs and product links. Handles retailer bot-protection by routing image sourcing through accessible CDNs. Output is a comparison table ready to paste into a wiki page or shareable email."
---

# product-selection — Home Renovation Product Research & Validation

## What This Skill Does

Given a product category and requirements, this skill:

1. Searches for 2–4 options at different price/quality tiers
2. Finds working image URLs for each (not guessed — validated before including)
3. Validates all product page links return HTTP 200
4. Formats a comparison table suitable for a wiki page or email to stakeholders

Use it any time you need to: select a fixture, choose hardware, research appliance options, find a replacement product, or build a shareable decision summary.

---

## Critical Domain Routing (read this first)

Many home products retailers **block automated access**. Always check this list before attempting a WebFetch:

### BLOCKED — Do not WebFetch these domains
| Domain | Failure mode |
|---|---|
| signaturehardware.com | 403 Forbidden |
| ferguson.com | Akamai bot challenge (shows only `Akamai` logo) |
| fergusonhome.com | 403 Forbidden |
| homedepot.com | 403 Forbidden |
| lowes.com | 403 Forbidden |
| wayfair.com | 429 / 403 |
| amazon.com | 500 / robot challenge |
| walmart.com | Robot challenge |
| ebay.com | Timeout |
| faucet.com | 404 (URL patterns stale) |
| faucetdirect.com | 404 (URL patterns stale) |
| build.com | Redirects to fergusonhome.com → 403 |

**These domains still appear in WebSearch results.** Use their URLs as product references / links for humans, but never attempt to WebFetch them for images or validation.

### ACCESSIBLE — Use these for images and page validation
| Domain | Notes |
|---|---|
| **i.pinimg.com** | Pinterest CDN — most reliable image source |
| **emtek.com** | Full product pages + CDN images accessible |
| **baldwinhardware.com** | Product pages 200 OK |
| **images.baldwinhardware.com** | Scene7 CDN — use `?fmt=jpeg&wid=600` parameter |
| **kohler.com** | Product pages accessible |
| **deltafaucet.com** | Product pages + images accessible |
| **moen.com** | Product pages + images accessible |
| **pfisterfaucets.com** | Accessible |
| **americanstandard-us.com** | Accessible |
| **schlage.com** | Accessible |
| **kwikset.com** | Accessible |
| **cdn11.bigcommerce.com** | Third-party retailer CDN — usually works |
| Pinterest pin pages | For og:image extraction — fetch `https://www.pinterest.com/pin/...` → extract og:image |

---

## Step-by-Step Workflow

### Step 1 — Define requirements

Before searching, establish:
- **Category**: (e.g., "single-hole bar faucet", "passage door lever", "under-cabinet lighting")
- **Finish**: (e.g., polished chrome, brushed nickel, matte black)
- **Brand constraint**: (e.g., "must match [existing product]" or "no brand constraint")
- **Price range**: (budget / mid-tier / luxury)
- **Compatibility note**: (e.g., "must match existing Signature Hardware Levi faucet finish")
- **Quantity** if hardware: (important for total cost calculation)

### Step 2 — Search for candidates

Run 2–3 parallel WebSearch calls:
```
WebSearch: "[category] [finish] [brand if constrained] options comparison"
WebSearch: "[category] [finish] site:[accessible-brand].com"
WebSearch: "[category] [finish] [brand] site:pinterest.com"  ← for image sourcing
```

Identify 2–4 candidates at different price tiers. Record:
- Product name, model number, SKU
- Retailer URLs (even if blocked — these are links for humans, not for WebFetch)
- Approximate price

### Step 3 — Find working image URLs

For each candidate, work through this priority order:

**Priority 1: Official brand website CDN**
- Fetch the official brand product page (only if brand is on the ACCESSIBLE list)
- Look for og:image meta tag or main product img src
- Brand CDN patterns to try:
  - Emtek: `https://www.emtek.com/media/salsify/images/[size]/[hash]-[date]-[ProductName]_EM_KO.jpg`
  - Baldwin: `https://images.baldwinhardware.com/is/image/Baldwin/[sku]?fmt=jpeg&wid=600`
  - Kohler: usually in `content.kohler.com` or `img.kohler.com`

**Priority 2: Pinterest pins**
- Search: `site:pinterest.com "[product name] [finish]"`
- Pick the most specific matching pin (exact product, exact finish)
- WebFetch the pin URL with prompt: "Find the og:image meta tag content URL. Return the full pinimg.com URL and describe the product and finish shown."
- The returned `https://i.pinimg.com/736x/...` URL is the image — validate it

**Priority 3: Accessible third-party retailers**
- Try kohler.com, deltafaucet.com, moen.com, schlage.com for brand-specific searches
- Try cdn11.bigcommerce.com URLs found via Google image search

**Never use**: images served from BLOCKED domains — even if a URL looks like it might work.

### Step 4 — Validate ALL URLs

Before finalizing any URL (image or product link), run WebFetch to confirm:

**For image URLs:**
```
WebFetch(url=image_url, prompt="Is this a valid accessible image? Return HTTP status and file size in KB.")
```
- Confirmed valid: response contains binary JPEG/PNG data with file size > 5KB
- 404 or 403: discard, find alternative
- Note: WebFetch can't render binary images — it will describe them as "corrupted binary" even when valid. The real signal is whether it saves a file and the file size is reasonable (>5KB for a product photo).

**For product page links:**
```
WebFetch(url=product_url, prompt="Return HTTP status and page title.")
```
- 200 + page title matching product: confirmed ✓
- 404: find correct URL (brand sites often restructure URLs)
- 403: domain is blocked — still usable as a human-clickable link, just note "opens in browser"

### Step 5 — Build comparison output

Format as a Markdown comparison table:

```markdown
## [Category] Options

| Option | Brand/Model | Price | Image | Link | Validated |
|--------|-------------|-------|-------|------|-----------|
| ⭐ A (Recommended) | ... | ~$X | [confirmed CDN URL] | [link] | ✓ |
| B | ... | ~$X | [confirmed CDN URL] | [link] | ✓ |
| C | ... | ~$X | N/A — view at link | [link] | link blocked |

**Recommendation**: [1-2 sentences on why Option A is recommended]
```

For email format (shareable with stakeholders), use inline images:
```markdown
### ⭐ Option A — [Brand Model] · ~$[price] · RECOMMENDED
![Product description](https://confirmed-image-url.jpg)
[Product name](https://product-page-url) · [any notes about URL accessibility]
```

---

## Saving Results to Wiki

After selection is made, update the relevant project page in `logseq/pages/`:

```markdown
## [Category] Selection

| Option | Model | Price | Notes |
|--------|-------|-------|-------|
| A (Selected) | ... | ~$X | [reason] |
| B | ... | ~$X | [reason] |

**Selection**: Option A — [reason for selection]
**Status**: [ ] Pending Rebekah approval / [x] Approved / [ ] Ordered
```

Update `## Outstanding Items — Owner's Side` if the item was listed there.

---

## Common Product Categories — Known Working Sources

### Plumbing Fixtures (faucets, etc.)
- **Signature Hardware**: Pages accessible to browser, blocked to WebFetch. Images: search Pinterest for brand pins.
- **Rohl**: BigCommerce CDN works (`cdn11.bigcommerce.com`). Official site may work.
- **Kohler**: `kohler.com` accessible. CDN at `content.kohler.com`.
- **Delta/Brizo**: `deltafaucet.com` accessible.
- **Moen**: `moen.com` accessible.

### Door Hardware (levers, knobs, deadbolts)
- **Emtek**: `emtek.com` fully accessible — product pages + CDN images.
- **Baldwin Reserve**: `baldwinhardware.com` pages + `images.baldwinhardware.com` CDN.
- **Schlage**: `schlage.com` accessible.
- **Kwikset**: `kwikset.com` accessible.

### Appliances
- **Viking**: `vikingrange.com` accessible.
- **Zephyr**: `zephyronline.com` — check directly.
- **Bosch**: `bosch-home.com/en-us/` accessible.

### Tile & Stone
- **Zia Tile**: Direct brand site.
- **Fireclay**: Accessible.

---

## Quality Checklist Before Finalizing

- [ ] All image URLs return a JPEG/PNG file (>5KB)
- [ ] All product page links return HTTP 200 (or noted as "accessible in browser" if blocked)
- [ ] Prices are current (within ~6 months) — note "approximate" if from older sources
- [ ] Finish described matches the project requirement (e.g., "polished chrome" not "chrome" or "brushed chrome")
- [ ] Model numbers confirmed against at least 2 sources
- [ ] For hardware: total cost calculated (unit price × quantity)
- [ ] At least 2 options cover different price tiers
- [ ] Recommendation includes reason (finish match, brand consistency, value, etc.)

---

## Related Skills

- [[design-review]] — Compliance checking against CD set; complements product selection for spec verification
- [[knowledge-synthesis]] — After selection, synthesize product research into permanent wiki notes
- [[handy:plan]] — When planning installation of selected products
