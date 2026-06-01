---
name: outfit-event-planner
description: "Plan a complete outfit (or coordinated couple's outfits) for a specific event. Anchors on a known statement piece (e.g. a partner's dress), derives a complementary color palette, audits owned wardrobe, identifies gaps, and builds a Logseq wiki lookbook page with images, product links, and 'why it works' pairing rationale. TRIGGER when the user wants to plan what to wear to a wedding, party, formal event, or date — or wants to coordinate looks with a partner."
---

# outfit-event-planner

## What This Skill Does

Given an event and an anchor piece, this skill:

1. **Analyzes** the event context (dress code, venue, formality, season)
2. **Anchors** on a known statement piece (usually the woman's dress, or any already-decided item)
3. **Derives** a complementary color palette for the partner's look
4. **Audits** the existing wardrobe for usable pieces
5. **Identifies** gaps — what needs to be purchased
6. **Researches** specific products to fill gaps (calls clothing-product-sourcer as needed)
7. **Builds** a Logseq wiki lookbook page with images, product links, and pairing rationale

---

## Phase 0 — Event & Anchor Discovery

Ask the following before doing any research. Use `AskUserQuestion` for each. Adapt based on answers.

### Q1 — Event Details
```
header: "Event"
question: "What is the event and dress code?"
options:
  - "Wedding — Garden Formal"
  - "Wedding — Dressy Casual / Garden Party"
  - "Wedding — Black Tie or Formal"
  - "Other event (click Other to describe)"
```

### Q2 — Anchor Piece
```
header: "Anchor"
question: "Is there a known statement piece to coordinate around?"
options:
  - "Yes — partner's dress (describe or share photo)"
  - "Yes — my own suit/outfit is already decided"
  - "No anchor — planning from scratch"
  - "Both outfits need planning"
```

If anchor exists: get a photo or detailed description (base color, print/pattern, dominant accent colors, silhouette, fabric). This is the single most important input — do not proceed without it.

### Q3 — Owned Inventory
```
header: "Wardrobe"
question: "What relevant pieces do you already own?"
```
Free-text. Record: suits, blazers, trousers, shirts, shoes, accessories. Note brand/color/size for each.

### Q4 — Budget
```
header: "Budget"
question: "What's your total budget for new purchases?"
options:
  - "Under $200"
  - "$200–$400"
  - "$400–$800"
  - "No hard limit — find the best options"
```

### Q5 — Output
```
header: "Output"
question: "What do you want as the output?"
options:
  - "Wiki lookbook page (Logseq)"
  - "Just a recommendation — no wiki update"
  - "Both — recommendation + wiki page"
```

---

## Phase 1 — Palette Derivation

### Reading the Anchor Piece

From the anchor piece (typically the woman's dress), extract:

| Layer | What to identify |
|---|---|
| **Base** | Dominant background color (black, navy, cream, etc.) |
| **Primary accent** | The largest/loudest print element color |
| **Secondary accent** | Supporting print color |
| **Tertiary accent** | Smallest/subtlest element (often a good tie/pocket square color) |
| **Overall energy** | Bold and graphic / soft and romantic / earthy and textured |

### Building the Partner's Palette

Apply these principles:

**1. Contrast the base, echo the accents**
- If her base is dark (black, navy) → his base tones should be lighter (cream, tan, stone) for visual separation as a couple
- If her base is light → he can go slightly deeper (warm navy, caramel, rust)

**2. Echo one accent color directly**
- Pick the most wearable accent from her dress and match it in his shirt or pocket square
- "Echo, don't copy" — same color family, different scale (e.g., her peach florals → his terracotta shirt)

**3. Neutral base reads as "intentional"**
- Tan, cream, stone, warm grey all work as his trouser/jacket base
- Avoid competing patterns unless intentionally leaning into a couple's statement look

**4. Dress code shapes formality level**
- Garden Formal: matching suit + tie + dress shoe
- Dressy Casual: odd jacket + different trousers + open collar (no tie, or optional)
- Black Tie: tuxedo or dark suit

### Palette Output Format
```
Anchor: [Dress description]
Base colors: [hers] → [his]
Primary echo: [her accent] → [his shirt/jacket]
Secondary echo: [her accent] → [his pocket square/tie]
Neutral anchor: [his trouser/shoe]
Overall concept: [1-line palette name, e.g. "Warm Earth meets Bold Floral"]
```

---

## Phase 2 — Wardrobe Audit

For each owned piece, evaluate:
- Does it fit the palette derived in Phase 1?
- Is it appropriate for the dress code?
- Does it still fit / is it in good condition?

Tag each piece as:
- ✅ **Use** — confirmed in the look
- 🔄 **Maybe** — works with right pairing
- ❌ **Skip** — wrong palette, wrong formality, or don't use at both events (avoid repeating)

**Key rule:** If attending two events close together (e.g., two weddings), flag any piece being used at both — wearing the exact same outfit twice is fine; wearing the exact same *hero piece* (e.g., the main suit) looks repetitive. Recommend different hero pieces for each event.

---

## Phase 3 — Gap Analysis

List what's needed that isn't owned. For each gap:

```
Gap: [item category]
Role in look: [e.g. "trouser to pair with blazer — off-white or cream, dressy casual weight"]
Size: [from user's measurements]
Budget: [portion of total budget]
Priority: Must-have / Nice-to-have
```

Standard gaps to check:
- [ ] Hero layer (blazer/jacket/suit)
- [ ] Trousers
- [ ] Shirt
- [ ] Shoes (the most commonly overlooked gap)
- [ ] Pocket square or tie
- [ ] Belt (if trousers require one)

---

## Phase 3b — Color Verification (MANDATORY before finalizing)

**Run `outfit-color extract` on every pending purchase before writing it into the wiki as confirmed.**

### Near-White Clash Rule (the failure mode we learned from)
Mixing near-whites from different brands is the #1 outfit mismatch trap. "Cream," "off-white," "ivory," "natural," and "ecru" are NOT interchangeable — they have different hue temperatures:
- **Warm cream** (yellow cast, H:40–60°): Percival, DDM, most linen naturals
- **Cool off-white** (neutral/blue cast, H:0–10° or S<5%): many Suitsupply whites, dress shirts

Two near-whites with different undertones look like a mistake, not a choice.

**Rule:** When combining any two light/neutral garments, run `outfit-color extract` on both product images and compare the H° and undertone. If undertones differ by more than 20° or one is warm and one is cool, **they will clash**. Switch to:
- Same brand/fabric match (guaranteed same dye lot), OR
- A clearly different color (navy, charcoal) that avoids the matching game entirely

### Verification Checklist Before Confirming a Look
```
For each pair of light/neutral garments:
[ ] Run outfit-color extract on both product images
[ ] Compare H° — within 20°? Same undertone (warm/cool)?
[ ] If mismatched: either match source (same brand/fabric) or switch to clearly different color
[ ] Run outfit-color analyze on the full look — score ≥ 7 before marking confirmed
```

---

## Phase 4 — Product Research

For each Must-have gap, run clothing-product-sourcer (or research inline if gaps are simple).

### Clothing Research Domain Table

| Domain | WebFetch | Notes |
|---|---|---|
| dandydelmar.com | ✓ (sometimes) | Direct fetch often works |
| fahertybrand.com | 403 | Links only; images sometimes via CDN |
| suitsupply.com | Partial | Category pages 404; product pages work |
| thetiebar.com | ✓ | Product pages accessible; images at cdn.shopify.com |
| thursdayboots.com | ✓ | Images at CDN URL |
| amberjack.shop | ✓ | |
| express.com | 403 | Links only; user screenshots needed for images |
| jcrew.com | 503 | Intermittent; try product pages directly |
| balticborn.com | 403 | Links only |
| vicicollection.com | 403 | Links only |
| bananarepublic.gap.com | 404/302 | Hard to scrape; search for direct product URLs |
| abercrombie.com | ✓ | CDN images accessible |
| sezane.com | ✓ | Images at media.sezane.com |
| thereformation.com | ✓ | Images at media.thereformation.com |
| cdn.suitsupply.com | ✓ | Direct image CDN always works |

### Sizing Notes (Tyler Stapler)
- Shirts: S (Ministry of Supply, DDM)
- Blazers: S in most brands; 38 chest in numeric sizing (verify Faherty — S=38-40"; J.Crew S=36-38")
- Trousers: 31W × 32L; Suitsupply sells even waists only — order 32W, tailor in 1"
- Shoes: (confirm with user)

---

## Phase 5 — Lookbook Assembly

Build the Logseq wiki page. Use this structure:

```markdown
tags:: [[Wedding]], [[Outfit]], [[Clothing]], [[Events]]

- **Event:** [Event name]
- **Dress Code:** [Dress code]
- ## Our Looks
    - **[Partner A]** — [dress description] (owned / purchase needed)
        - ![Photo](../assets/[filename])
        - [Color breakdown]
    - **[Partner B]** — [summary of full look]
    - *Coordination: [1–2 sentences on palette logic — how the two looks connect]*
- ## [Partner B]'s Look
    - *[Palette framing line]*
    - ### ⭐ Look 1 — [Name] *(recommended)*
        - [Each item with image, product link, size, price]
        - **Why it works:** [Specific pairing rationale referencing the anchor piece]
    - ### Look 2 — [Name] *(alternative)*
        - ...
    - ### Notes
        - **Together:** [Explicit bridge note — which item echoes which element of the anchor]
        - [Sizing/tailoring notes]
        - [Shoe note if applicable]
- ## Pocket Square / Tie
    - ...
- ## Shoes
    - ...
- ## Related
    - [[Wedding Outfit Combinations]]
    - [[Wardrobe]]
```

### Image Handling
- Product images: embed inline with `![alt](https://cdn-url)` — CDN URLs only, no guessed paths
- Personal photos: copy to `logseq/assets/[descriptive-name.jpg]` and reference as `../assets/[name]`
- If image unavailable: note `⚠️ Add photo to assets as [suggested-filename]`

---

## Phase 6 — Confirmation & Record

After presenting the lookbook:
1. Ask user to confirm the final look selection
2. Mark the confirmed look with `✅ Confirmed:` at the top of the Tyler/partner section
3. Update the `## Our Looks` summary to reflect the final choices
4. Note any outstanding purchases

---

## Related Skills

- [[clothing-product-sourcer]] — Research and source specific clothing items
- [[product-selection]] — General product research with URL/image validation
- [[knowledge-synthesis]] — Synthesize outfit research into permanent wiki notes
