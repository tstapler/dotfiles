---
name: wardrobe-receipt-cataloger
description: "Scan Gmail for clothing purchase receipts, extract item details (brand, product, color, size, price, purchase date), download product images, then catalog each item in the Logseq wiki: update Wardrobe.md in the correct section, create/update brand pages, and link to the product page, Internet Archive snapshot, and original receipt email. TRIGGER when the user wants to sync recent clothing purchases to their wiki, catalog new wardrobe items from email receipts, or audit what they've bought."
---

# wardrobe-receipt-cataloger

## What This Skill Does

Given a date range (defaulting to the last 90 days), this skill:

1. **Searches** Gmail for clothing purchase receipts
2. **Parses** each receipt to extract: brand, product name, color/colorway, size, price, purchase date, product URL
3. **Downloads** product images to `logseq/assets/` with structured filenames
4. **Fetches** an Internet Archive (Wayback Machine) snapshot URL for each product
5. **Updates** `logseq/pages/Wardrobe.md` in the correct section
6. **Creates or updates** brand pages in `logseq/pages/`
7. **Links** each entry to the product page, Wayback Machine snapshot, purchase date journal entry, and original Gmail thread

---

## Phase 0 — Scope

Load Gmail tools first:

```
ToolSearch: select:mcp__claude_ai_Gmail__search_threads,mcp__claude_ai_Gmail__get_thread,mcp__claude_ai_Gmail__list_labels
```

Then ask:

```
AskUserQuestion:
  header: "Date range"
  question: "Which time window should I scan for clothing receipts?"
  options:
    - "Last 30 days (Recommended)"
    - "Last 90 days"
    - "Last 6 months"
    - "Custom range — I'll specify via Other"
```

```
AskUserQuestion:
  header: "Filter"
  question: "Should I catalog all clothing brands or focus on specific ones?"
  options:
    - "All clothing brands found in receipts (Recommended)"
    - "Only brands not yet in Wardrobe.md"
    - "Specific brands — I'll name them via Other"
```

---

## Phase 1 — Gmail Receipt Search

### 1a — Run parallel searches

Use `mcp__claude_ai_Gmail__search_threads` with these queries in parallel (one call per query):

```
"order confirmation" "clothing" newer_than:{days}d
"receipt" ("shirt" OR "pants" OR "jacket" OR "shorts" OR "shoes" OR "blazer" OR "hoodie" OR "trousers") newer_than:{days}d
"your order" ("Patagonia" OR "REI" OR "Roark" OR "Bonobos" OR "Dandy Del Mar" OR "lululemon" OR "prAna" OR "1620 Workwear" OR "Engelbert Strauss" OR "Taylor Stitch" OR "Faherty" OR "Suitsupply" OR "J.Crew" OR "Banana Republic" OR "Express" OR "Buck Mason") newer_than:{days}d
"shipping confirmation" ("apparel" OR "clothing" OR "wear" OR "shirt" OR "jacket") newer_than:{days}d
```

Replace `{days}` with: 30 → 30, 90 → 90, 6 months → 180.

### 1b — Deduplicate threads

Collect all thread IDs, deduplicate. Fetch each unique thread with `mcp__claude_ai_Gmail__get_thread`.

### 1c — Classify

For each thread, determine:
- Is this a **clothing purchase receipt**? (vs. tracking update, marketing, non-clothing)
- What **retailer/brand** is it from?
- Skip: tracking-only emails, marketing/promotional, returns/refunds unless re-purchased

---

## Phase 2 — Receipt Parsing

For each confirmed clothing receipt thread, extract:

| Field | Notes |
|---|---|
| `brand` | Retailer brand name (e.g., "Patagonia", "Roark") |
| `product_name` | Full product name as listed (e.g., "M's Houdini Jacket") |
| `color` | Color/colorway name (e.g., "Buckhorn Green") |
| `size` | Size as ordered (e.g., "M", "31W × 32L", "S") |
| `price` | Item price (USD) |
| `purchase_date` | Date of purchase (YYYY-MM-DD) |
| `product_url` | Direct product URL from receipt (if present) |
| `order_number` | Order number/ID |
| `gmail_thread_id` | Thread ID for back-linking to email |

**If multiple items in one order:** extract each item separately.

**Size normalization:**
- Tops: S / M / L / XL or brand-specific (Slim S, etc.) — preserve exact size code as ordered
- Pants: W × L format (e.g., 31×32)
- Shoes: US size

---

## Phase 3 — Image Acquisition

For each item:

### 3a — Try to get the product image

1. If `product_url` exists:
   - Load: `ToolSearch: select:mcp__read-website-fast__read_website`
   - Fetch the product page: `mcp__read-website-fast__read_website(url=product_url)`
   - Extract the main product image URL from the page (look for `og:image` or primary product photo)
2. If no image found from product page, search: `mcp__brave-search__brave_web_search` for `{brand} {product_name} {color} site:brand.com` to find a direct image URL

### 3b — Download the image

Load: `ToolSearch: select:mcp__website-downloader__download_page`

- Save to: `logseq/assets/{brand-slug}-{product-slug}.jpg`
- **Filename rules** (Android compatibility — NO `: * ? " < > | \`):
  - Brand slug: lowercase, spaces → hyphens (e.g., `dandy-del-mar`)
  - Product slug: lowercase, keep color, remove special chars (e.g., `houdini-jacket-buckhorn-green`)
  - Full example: `patagonia-houdini-jacket-buckhorn-green.jpg`
- If image download fails, note "image pending" and continue — don't block cataloging

### 3c — Fetch Wayback Machine snapshot

For each `product_url`:
- Archive URL pattern: `https://web.archive.org/web/*/{product_url}`
  - This retrieves the most recent available snapshot
- Also construct a save-request URL: `https://web.archive.org/save/{product_url}`
  - Note this in the catalog entry so the user can trigger a fresh save if desired

---

## Phase 4 — Section Classification

Map each item to the correct `Wardrobe.md` section:

| Item type | Section → Subsection |
|---|---|
| Blazer, sport coat, suit jacket | Tops → Dress / Smart Casual |
| Dress shirt, linen shirt | Tops → Dress / Smart Casual |
| Button-down, woven shirt, OCBD | Tops → Button-Down & Woven Shirts |
| T-shirt, polo, athletic shirt | Tops → T-Shirts & Athletic Shirts |
| Hoodie, fleece, long-sleeve performance | Tops → Hoodies & Long-Sleeve Performance |
| Sun sleeves, buff, neck gaiter | Tops → Sun Protection & Neckwear |
| Dress trousers, chinos, linen trousers | Bottoms → Pants |
| Jeans, casual pants, cargo pants | Bottoms → Pants |
| Shorts | Bottoms → Shorts |
| Jacket, vest, rain shell, wind shell | Outerwear & Layering |
| Tank top, undershirt | Dress Accessories |
| Hat, cap, beanie, sunglasses, belt | Headwear & Accessories |
| Shoes, boots, sneakers, sandals | Footwear |
| Work pants, work shirt, tool vest | Work & Trade Clothing |
| Jersey, fan apparel | Sports & Fan Apparel |

---

## Phase 5 — Wiki Updates

### 5a — Update Wardrobe.md

Read `logseq/pages/Wardrobe.md`. For each new item, append to the correct section:

```markdown
- [[{Brand}]] {Product Name} — {Color}, {Size} ({Month} {Year}) · [product]({product_url}) · [archive](https://web.archive.org/web/*/{product_url}) · [receipt](https://mail.google.com/mail/u/0/#inbox/{gmail_thread_id})
```

**Format rules:**
- Check for duplicates before appending: if an identical entry (same brand + product + color + size + year/month) already exists, skip
- Sort within subsections: most recent purchase last (chronological)
- If the subsection doesn't exist yet, create it under the correct parent section

**Example output:**
```markdown
- [[Patagonia]] M's Houdini Jacket — Buckhorn Green, M (Aug 2024) · [product](https://www.patagonia.com/product/mens-houdini-jacket/24142.html) · [archive](https://web.archive.org/web/*/https://www.patagonia.com/product/mens-houdini-jacket/24142.html) · [receipt](https://mail.google.com/mail/u/0/#inbox/18c3b2a1d0e9f7g6)
```

### 5b — Update or create brand page

Check if `logseq/pages/{Brand}.md` exists.

**If it doesn't exist**, create it with this template:

```markdown
tags:: [[Clothing]], [[Brand]], [[Shopping]]

- **{Brand}** — {one-line brand description from website or receipt context}
- ## Purchases
	- ### {Year}
		- **{Product Name}** — {Color}, {Size} · [product]({product_url}) · [archive](https://web.archive.org/web/*/{product_url})
			- ![{Brand} {Product Name}](../assets/{image-filename}.jpg)
			- Purchased {Month} {Year} · ${price} · [receipt](https://mail.google.com/mail/u/0/#inbox/{gmail_thread_id})
- ## Related
	- [[Wardrobe]]
```

**If it exists**, append the new item under `## Purchases` in the correct year subsection. Create the year subsection if it doesn't exist.

### 5c — Update Key Brands list in Wardrobe.md

If the brand is new (not already in the `## Key Brands` section), append:
```markdown
- [[{Brand}]] — {short descriptor}
```

And add it to the `## Related` section at the bottom.

---

## Phase 6 — Summary Report

After all items are processed, output a summary table:

```markdown
## Receipt Cataloging Summary

| Brand | Product | Color | Size | Date | Wardrobe Section | Image | Status |
|---|---|---|---|---|---|---|---|
| Patagonia | M's Houdini Jacket | Buckhorn Green | M | Aug 2024 | Outerwear | ✅ | Added |
| … | … | … | … | … | … | … | … |

### Skipped
- {Thread subject} — reason (e.g., "non-clothing", "already cataloged", "return/refund")

### Images Pending
- {Brand} {Product} — image URL not found; manually add to logseq/assets/{filename}.jpg
```

Then ask:

```
AskUserQuestion:
  header: "Next step"
  question: "Items cataloged. What would you like to do next?"
  options:
    - "Commit the changes to git"
    - "Review the Wardrobe.md changes first"
    - "Run again for a longer date range"
    - "Done for now"
```

---

## Execution — Reusable Scripts

Rather than making individual file edits (which require per-call approval), this skill uses two reusable scripts that only need one approval to run:

### Files

| File | Purpose |
|---|---|
| `~/.claude/skills/wardrobe-receipt-cataloger/catalog_wardrobe.py` | Main script: downloads images, updates Wardrobe.md, creates/updates brand pages |
| `~/.claude/skills/wardrobe-receipt-cataloger/receipts.json` | Data: extracted receipt data in structured JSON format |

### Workflow

1. **Extract** receipt data from Gmail threads into `receipts.json`
2. **Run** `catalog_wardrobe.py` once — single script approval covers all file writes
3. **Verify** with `--dry-run` first, then execute for real

```bash
# Dry run (preview only)
python3 ~/.claude/skills/wardrobe-receipt-cataloger/catalog_wardrobe.py \
  --wiki-root /path/to/personal-wiki \
  --dry-run

# Execute
python3 ~/.claude/skills/wardrobe-receipt-cataloger/catalog_wardrobe.py \
  --wiki-root /path/to/personal-wiki

# Skip already-processed receipts on re-runs
python3 ~/.claude/skills/wardrobe-receipt-cataloger/catalog_wardrobe.py \
  --wiki-root /path/to/personal-wiki \
  --skip-processed
```

### Adding new receipts

When new receipts are found, add entries to `receipts.json` in this format:
```json
{
  "thread_id": "19e75dd...",
  "brand": "Brand Name",
  "order_number": "12345",
  "order_date": "2026-05-29",
  "items": [
    {
      "product_name": "Product Name",
      "color": "Color Name",
      "size": "M",
      "price": 89.00,
      "wardrobe_section": "Tops",
      "wardrobe_subsection": "Button-Down & Woven Shirts",
      "existing_search": null,
      "image_url": "https://cdn.example.com/image.jpg",
      "image_filename": "brand-product-color.jpg",
      "product_url": "https://brand.com/product"
    }
  ]
}
```

Set `existing_search` to the exact text of an existing Wardrobe.md line to add receipt links to it instead of creating a new entry.

---

## Notes & Constraints

### Android filename safety
Never use `: * ? " < > | \` in any filename written to `logseq/assets/`. Always validate before writing.

### Duplicate detection
Before adding any entry to Wardrobe.md or a brand page, check if an entry with the same (brand + product slug + color + size + year) already exists. If so, skip silently.

### Wayback Machine links
Use the `*` wildcard form (`/web/*/url`) which redirects to the most recent snapshot — more robust than a dated snapshot URL that may not exist yet. If the product URL is very new, the archive may not have a snapshot; note this in the summary rather than failing.

### Gmail thread links
Gmail deep-link format: `https://mail.google.com/mail/u/0/#inbox/{thread_id}`
Use the thread ID from `mcp__claude_ai_Gmail__get_thread` response.

### Purchase date → journal link
Logseq journal format: `logseq/journals/YYYY_MM_DD.md`
If the journal entry for the purchase date exists, you may reference it as:
```markdown
[[{Month} {Day}th, {Year}]]
```
using Logseq's journal page link syntax.

### Rate limiting
If fetching many product pages, add brief pauses between requests. Prefer reading receipt email HTML for images over scraping retailer websites when possible.
