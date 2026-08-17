---
name: product-manual-finder
description: "Find the official instruction manual/PDF for a specific owned product (by model number or photo), verify it's actually the right document (not a spec sheet or the wrong model), make sure it has a searchable text layer (OCR if it's scan-only), save it into the wiki's assets folder, and synthesize a product page that links and summarizes it. TRIGGER when the user asks to find/gather/look up a manual, instructions, or documentation for a specific tool or appliance they own, or asks how to operate/troubleshoot/reload/reset something and no manual is on file yet."
---

# product-manual-finder

## What This Skill Does

Given a product (photo, model number, or name), this skill:

1. **Pins down the exact model number** — from the item itself, not a guess
2. **Searches** manufacturer, retailer-mirror, and aggregator sources for the real instruction manual — not a spec sheet, not a similar model
3. **Fetches** it through the site's actual access path, working around bot-gating (WebFetch → MCP crawler → Chrome MCP)
4. **Verifies** the PDF is (a) actually the claimed model and (b) actually an instructions document, not a marketing page
5. **Ensures it has an OCR text layer** so it's searchable in a PDF viewer and in Logseq's own PDF annotation view
6. **Saves** it to `logseq/assets/` and **synthesizes** a product page per `logseq-wiki-syntax` that links it and pulls out the parts someone will actually come back for (loading, resets, part numbers, troubleshooting table)
7. **States plainly when no manual exists** rather than substituting a spec sheet or a different model's manual and calling it close enough

This skill produces one artifact type — a manual, verified and stored — as part of the wider `knowledge-synthesis` Recall → Refine → Research → Link loop this wiki runs on. It doesn't replace that loop; it fills in the "find and validate a primary source document" step within it.

---

## Phase 0 — Identify the Exact Product

**Entry gate**: a photo, model number, or product name from the user.

The single most common way this goes wrong is attaching the right brand's *wrong model's* manual. Do not skip this phase to save time.

- If given a **photo**: zoom into the model/serial sticker (crop + resize with `magick`/`convert`, see `Bash` — a 3-4x crop on the sticker region is usually enough to read a blurry label). Cross-check the model number against ≥2 independent sources (official product page + one retailer listing) before treating it as confirmed — model numbers get OCR'd wrong on blurry photos more often than you'd expect.
- If given a **model number directly**: still confirm it resolves to a real, specific product (not a family/series name) via one search before proceeding.
- Note the **manufacturer** and the **product category** (power tool, appliance, furniture, electronics) — this determines which source tier in Phase 1 is likely to pay off first.

**Exit gate**: exact model number confirmed against ≥2 sources, manufacturer identified.

---

## Phase 1 — Source Tiers (search in this order)

**Check `brands/<manufacturer-slug>.md` first.** If a brand reference file exists for this manufacturer, it already documents the verified URL patterns, which domains are bot-gated, and which are dead ends — follow it instead of rediscovering the same things from scratch. See "Brand References" below for the current list and the template for adding a new one.

Stop as soon as a tier produces a verified match (Phase 3) — don't burn searches on lower tiers once a higher one succeeds.

1. **Manufacturer's own manuals/support page** — best when reachable. Often JS-rendered and/or Cloudflare-gated (see Phase 2 fetch hierarchy). Search: `site:<manufacturer>.com "<model>" manual OR "instruction sheet" filetype:pdf`
2. **Direct manufacturer PDF via general search** — `"<model>" filetype:pdf manual site:<manufacturer>.com`
3. **Retailer-mirrored manufacturer PDFs** — retailers frequently host the *same* PDF the manufacturer publishes, on infrastructure that isn't bot-gated. Worth trying even before aggregators:
   - `pdf.lowes.com/productdocuments/...`
   - Home Depot / Amazon product-detail "user manual" attachments
   - Distributor CDNs (e.g. `rexel-cdn.com`) — **caveat**: these sometimes turn out to be a browser print-to-PDF of the *product page*, not the instruction manual. Looks identical to a real manual in search results. Phase 3 catches this — it has real text, but it won't read like step-by-step instructions or contain a parts diagram.
4. **Aggregator manual sites** — ManualsLib, Manua.ls, Manuals.plus, iFixit. Lowest trust tier — a missing model here is *not* proof no manual exists (catalogs are incomplete), but a hit still needs Phase 3 verification like everything else. Several of these (`manuals.plus`, and often `support.<brand>.com`) sit behind a Cloudflare JS challenge that blocks both WebFetch and headless MCP browsers — see Phase 2.
5. **No manual found** — after checking tiers 1-4, say so explicitly on the wiki page (Phase 5) with what was checked and the date. This is a legitimate, expected outcome for simple/unpowered tools (hand staplers, hammer tackers, basic hand tools often ship with only a printed insert, never a published PDF) — do not force a spec sheet or a different model's manual into that gap.

---

## Phase 2 — Fetch Tool Hierarchy

Same discipline as `product-selection`'s Phase 3 — try in order, don't give up after one failure. **Don't hardcode specific MCP tool names** — the exact servers connected vary by project/session (this wiki's session has `stapler-mcp`; another project might have `read-website-fast`, a different crawler, or none at all). Instead, escalate by *role*, and at each rung use `ToolSearch` to discover what's actually available and pick the best match by reading its description rather than assuming a name:

1. **`WebFetch`** — try first; no discovery needed, it's always available.
2. **A readability-extraction MCP crawler** — reach for this on 403/429 or a JS-rendered page. Run `ToolSearch` with a query like `"read website"` / `"fetch url"` / `"crawl"` and compare the returned tools' descriptions — look for one that converts a page to clean markdown/text and (ideally) can follow same-host links via a depth/page-count param, useful for crawling a manuals index page to find the right model's link. In this session that's `mcp__stapler-mcp__read_website`; treat the name as an example, not a requirement — search fresh each time you're in an unfamiliar project.
3. **A headless-browser-render MCP tool** — use when the previous rung returns empty text on a page that clearly has content (client-side rendered). Same discovery approach: `ToolSearch` for `"render page"` / `"headless browser"` / `"fetch page"` and pick by description. In this session that's `mcp__stapler-mcp__fetch_page`.
4. **Chrome MCP** (`navigate` + `get_page_text`, real logged-in browser) — last resort for a Cloudflare JS challenge or login wall that blocks both of the above. `ToolSearch` for `"select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__get_page_text"` (load the whole batch in one call, not one at a time). If Chrome MCP itself isn't connected in this session, say so and stop trying rather than looping on the same failure — don't fabricate a result to fill the gap.

Once you've found the right tool for a given project, it's fine to keep using it for the rest of that session — the point is not re-searching every call, it's not *assuming* a name before checking once.

**Downloading the PDF itself**: once you have a direct PDF URL, fetch it (WebFetch will save binary content; or `curl`/`Bash` if the URL is plain and un-gated). Confirm it's actually a PDF (`file <path>` or `pdfinfo <path>`) before treating the download as successful — a Cloudflare challenge page saved with a `.pdf` extension will fail `pdfinfo` immediately, which is a fast, cheap check worth running every time.

---

## Phase 3 — Verify It's the Right Document

**Entry gate**: a PDF has been downloaded.

Two independent checks — both matter, neither substitutes for the other:

### 3a. Right model?

Run `scripts/verify_manual_pdf.sh <pdf> <model_number>`. It extracts text and greps for the model number. `MATCH` → proceed. `NO MATCH` → one of two things is true, and you must determine which before proceeding:
- The PDF has no text layer yet (scan-only) → run Phase 4 first, then re-verify.
- The PDF genuinely isn't for this model → discard it, don't cite it.

If still uncertain after OCR, fall back to visually confirming via the `Read` tool directly on the PDF (Claude Code can read PDF pages as images) — check the cover page or first diagram page for the model number printed on the product itself.

### 3b. Actually a manual, not a marketing page?

A hit that passes 3a can still be the wrong *kind* of document — a printed product page, a spec sheet, or a warranty card can all contain the model number without containing a single instruction. Skim the extracted text (or the first few pages via `Read`) for manual-shaped content: numbered steps, a parts diagram, a troubleshooting table, safety warnings. If it reads like ad copy ("features", "buy now", star ratings) rather than instructions, it is not the manual — keep searching, or fall through to the Phase 1.5 "no manual found" outcome.

**Exit gate**: PDF passes both 3a and 3b, or the search has been declared exhausted per Phase 1's tier list.

---

## Phase 4 — Ensure a Searchable Text Layer

**Entry gate**: PDF passed Phase 3 (or is pending re-verification after OCR).

1. Run `scripts/check_pdf_searchable.sh <pdf>`. `SEARCHABLE` → skip to Phase 5. `IMAGE_ONLY` → continue.
2. Run `scripts/make_searchable.sh <pdf>` to add an OCR text layer via `ocrmypdf` (skips pages that already have text, so it's safe on mixed scan+typeset manuals). If `ocrmypdf` isn't installed, install it first — `brew install ocrmypdf` (it pulls in `tesseract`; check `which tesseract` first since it's often already present).
3. Re-run `check_pdf_searchable.sh` to confirm the OCR pass worked, then re-run `verify_manual_pdf.sh` if Phase 3a was previously blocked by missing text.

**Exit gate**: `check_pdf_searchable.sh` reports `SEARCHABLE`.

---

## Phase 5 — Save and Synthesize

**Entry gate**: PDF verified (Phase 3) and searchable (Phase 4).

1. **Save** the PDF to `logseq/assets/` with a descriptive kebab-case filename: `<brand>-<model>-manual.pdf` (e.g. `dewalt-dwht75900-manual.pdf`) — never the retailer's opaque download filename.
2. **Create or update the product's wiki page** per `logseq-wiki-syntax` (Zettelkasten style; check for an existing page first per the wiki's Recall-first rule — this skill commonly runs right after a page like the ones in `DeWalt DWHT75900 Hammer Tacker.md` already exists from an earlier troubleshooting session).
   - Link the manual: `[Manual (PDF)](../assets/<filename>.pdf)`
   - Don't just link it — **synthesize**: pull the specific sections someone will actually search the page for later — load/reload procedure, reset sequence, safety warnings, replacement part numbers, troubleshooting table — into the page body itself, citing the manual page number where useful (`p. 12`).
   - Note the manual's source URL and the date it was fetched, so staleness is checkable later.
3. **If no manual was found** (Phase 1's fallback): say so explicitly on the page — what was checked, when — and link whatever authoritative source does exist instead (official product page, retailer listing). Never leave this ambiguous or silently omit the manual section.

**Exit gate**: wiki page exists, links the verified+searchable PDF (or explicitly documents that none exists), and includes synthesized content beyond a bare link.

---

## Brand References

Per-manufacturer notes live in `brands/<slug>.md` — the actual PDF-hosting URL pattern (when there is one), which support/aggregator domains are bot-gated vs. reachable, which are dead links despite the manufacturer's own docs pointing at them, and manufacturer-specific model/type-number quirks. These exist because rediscovering "is support.acme.com Cloudflare-gated" from scratch every time is exactly the kind of repeated work this skill should eliminate.

| Brand | File | Key pattern |
|---|---|---|
| DeWalt | `brands/dewalt.md` | Manuals live on an unblocked Akamai CDN (`assets.dewalt.com/GLOBALBOM/...`), discoverable only via the product page's "Downloads and manuals" section — not guessable from the model number alone |

**Adding a new brand**: once you've done the Phase 1/2/3 legwork for a manufacturer you expect to see again (the user owns several of their tools, or the pattern took real digging to find), write it up as `brands/<slug>.md` using `brands/dewalt.md`'s structure as the template:
- Tier 1: the real PDF-hosting pattern, if one exists — URL template, what's guessable vs. not, ≥2 verified working examples (HEAD-check them, don't just cite search snippets)
- Tier 2: how to *discover* Tier 1's URLs (usually: fetch the product page, ask specifically for the downloads/documents section by name)
- Tier 3: retailer mirrors worth trying
- Tier 4: sources to explicitly avoid (dead links, Cloudflare-gated support portals) and why
- Tier 5: aggregator coverage notes
- Model/type-number quirks specific to that brand's labeling
- Query templates

Don't write a brand file after a single lookup — the value is in patterns confirmed across ≥2 products from that brand (as `dewalt.md` did with DWS780 and DCS356B) so the "pattern" claim isn't just one lucky hit. A single one-off lookup doesn't need a file; note anything useful for that model directly on its wiki page instead. Add the new brand to the table above.

---

## Bundled Scripts

| Script | Purpose |
|---|---|
| `scripts/check_pdf_searchable.sh <pdf>` | Reports `SEARCHABLE` / `IMAGE_ONLY` by sampling extracted text from the first 3 pages |
| `scripts/make_searchable.sh <pdf> [out]` | Adds an OCR text layer via `ocrmypdf --skip-text`; installs guidance if `ocrmypdf` is missing |
| `scripts/verify_manual_pdf.sh <pdf> <model>` | Confirms the model number appears in the extracted text — the model-mismatch gate |

All three are thin wrappers over `pdftotext`/`pdffonts`/`ocrmypdf` (poppler-utils; `pdftotext`/`pdfinfo`/`pdffonts` are already present on this machine). No Python — this is exactly the kind of job three CLI tools already solve; don't add a dependency to wrap them.

---

## Known Failure Modes

| Failure | Cause | Fix |
|---|---|---|
| Manufacturer product page 404s | SKU delisted/discontinued | Fall back to retailer listings (Home Depot, Amazon) for confirmation; note the 404 and date on the wiki page |
| `support.<brand>.com` returns "Just a moment..." / security check | Cloudflare JS challenge blocks WebFetch and headless MCP browsers alike | Try Chrome MCP (real browser); if unavailable, note the source as unreachable rather than fabricating |
| `manuals.plus` (and similar aggregators) return 403 on every fetch tool | Cloudflare bot protection | Same as above — Chrome MCP or mark unreachable |
| A distributor-CDN PDF has real, extractable text but reads like ad copy | It's a browser print-to-PDF of the *product page*, not the instructions — happens more than expected on CDN-hosted "spec sheet" links | Phase 3b catches this — check for step/diagram content, not just presence of text |
| `verify_manual_pdf.sh` reports NO MATCH on a PDF you can see the model number in | `grep -q` piped directly from `pdftotext` under `set -o pipefail` SIGPIPEs the producer and corrupts the pipeline's exit code even on a real match | Already fixed in this skill's script (extracts to a variable first) — if you hand-roll a similar check elsewhere, avoid `producer | grep -q` under `pipefail` |
| Aggregator catalog (e.g. Manua.ls) doesn't list the model | Catalog incompleteness, not proof the manual doesn't exist | Treat as one negative data point among several tiers, not a final answer |
| Simple unpowered tool (hand stapler, hammer tacker) has no manual anywhere | Many ship with only a printed insert, never a published PDF | Document that explicitly (Phase 5.3) — this is a correct, expected outcome, not a failed search |

---

## Related Skills

- [[knowledge-synthesis]] — the wider Recall → Refine → Research → Link loop this skill's output feeds into; supplies the wiki-page and Decision Write-Back patterns
- [[logseq-wiki-syntax]] — page conventions, filename rules, and the asset-image-embedding pattern this skill's PDF-linking mirrors
- [[product-selection]] / [[clothing-product-sourcer]] — sibling research skills; this skill's Fetch Tool Hierarchy (Phase 2) follows the same discipline they use for product pages and images
- [[meta-research-workflow]] — general search/sourcing methodology used throughout Phase 1
