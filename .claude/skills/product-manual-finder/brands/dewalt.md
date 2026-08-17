# Brand Reference — DeWalt

Verified 2026-08-16 by fetching live pages and HEAD-checking the PDF URLs below directly — not inferred from search snippets. Re-verify anything older than a few months before trusting it blind; retail/CDN structures drift.

## Tier 1 — The Real Pattern: `assets.dewalt.com`

DeWalt hosts every published manual, exploded parts diagram, and spec sheet on an **unblocked, non-bot-gated Akamai CDN** at `assets.dewalt.com`. This is the actual manual source of truth — everything else (aggregators, retailer mirrors) is a copy of what originates here.

**URL template:**
```
https://assets.dewalt.com/GLOBALBOM/<CODE>/<MODEL>/<TYPE>/Instruction_Manual/EN/<filename>.pdf
```
- `<CODE>` — has been `QU` in every case checked so far; treat as a constant, not something to vary.
- `<MODEL>` — the model number, uppercase (e.g. `DWS780`, `DCS356B`).
- `<TYPE>` — the tool's revision "Type" number, printed on the rating label next to the model number (e.g. `24`, `2`). **This is not guessable from the model number alone** — it varies per revision and isn't on the product page as visible text either.
- `<filename>` — an opaque internal doc ID (e.g. `NA379778_DWS780_NA.pdf`, `N682755.pdf`). Also not guessable.

**You cannot construct this URL from the model number alone.** The only reliable way to get `<TYPE>` and `<filename>` is to fetch the product's own page and read them off the "Downloads and manuals" section — see Tier 2.

Confirmed working examples (HTTP 200, `Content-Type: application/pdf`, served by `AkamaiNetStorage`):
- `https://assets.dewalt.com/GLOBALBOM/QU/DWS780/24/Instruction_Manual/EN/NA379778_DWS780_NA.pdf` (DWS780 miter saw, 22.6 MB)
- `https://assets.dewalt.com/GLOBALBOM/QU/DCS356B/2/Instruction_Manual/EN/N682755.pdf` (DCS356B oscillating tool, 7.1 MB)
- The same section also links `Exploded_Diagram` `.gif` files (parts diagrams) at the same path structure — worth grabbing alongside the manual for the wiki page's part-number references.

## Tier 2 — Finding the assets.dewalt.com Link: the Product Page

**Step 1 — find the exact product-page URL.** Do not guess the slug. `WebSearch site:dewalt.com "<model>"` and take the `dewalt.com/en-us/product/<model-lowercase>/<slug>` result. The slug must match exactly — `dewalt.com/en-us/product/<model>/` with no slug, or a guessed slug, both 404. A `dewalt.com/product/<model>/<slug>` (no `/en-us/`) URL also exists on some pages and appears to redirect/resolve fine.

**Step 2 — fetch the product page with `WebFetch`, and ask specifically for the download section.** Plain `WebFetch` works directly on `dewalt.com` product pages — they are **not** Cloudflare-gated (only `support.dewalt.com` is; see Tier 4). Prompt it explicitly:
> "List every downloadable document/PDF link under a 'Documents and Manuals' or 'Downloads and manuals' heading. Give the exact href/URL for each."
Asking generically ("summarize this product") tends to miss the section — it's asked for by name.

**If the section is absent:** the product genuinely has no published manual. Confirmed twice this way already — DWHT75900 (hammer tacker) and DWHT80276 (staple gun), both simple unpowered hand tools, both checked with two independent tools (`WebFetch` and the MCP crawler) and neither surfaced a Documents/Downloads section. Simple manual hand tools (staplers, hammer tackers, basic hand tools) frequently ship with only a printed insert and never get a PDF published — this is a real, expected outcome, not a tool failure. Don't force a spec sheet or a different model's manual into the gap; document the absence per the parent skill's Phase 5.3.

## Tier 3 — Retailer Mirrors (when Tier 1/2 comes up empty or you want a second source)

- **`pdf.lowes.com`** — Lowe's mirrors manufacturer PDFs under an opaque per-product path (`pdf.lowes.com/productdocuments/<uuid>/<id>.pdf`) — not constructible, but reliably unblocked once found. Find via `WebSearch site:pdf.lowes.com "<model>"` or by fetching the model's Lowe's product page and asking for document links, same as Tier 2's technique.
- **Home Depot** product pages sometimes carry a "Product Manuals & Documentation" attachment; same discovery technique (fetch + ask for document links by name) applies, though homedepot.com itself blocks WebFetch (403/error) — use the MCP crawler tools first.
- **Amazon** product listings occasionally attach the manufacturer PDF directly under the listing's document section; amazon.com blocks WebFetch — same fallback chain as the parent skill's Phase 2.

## Tier 4 — Do NOT Rely On

- **`support.dewalt.com`** — the Zendesk-hosted help center. Sits behind a Cloudflare JS challenge ("Performing security verification...") that blocks both `WebFetch` and headless MCP browsers (`fetch_page`/`read_website` return the challenge page, not content). DeWalt's own "How to locate your product manual" support article says manuals live in a "Documents and Manuals" section on the product page (Tier 2) — go there directly rather than through this gated portal.
- **`toolservicenet.com`** — DeWalt's own support docs point here as an alternative parts/manual lookup ("type the model number in the top search bar"). As of 2026-08-16 it returns `ERR_HTTP2_PROTOCOL_ERROR` / unreachable. Don't spend time on it; re-check only if the DeWalt support article stops mentioning it (a sign it's been formally retired) or comes back online.
- **`manuals.plus`** — Cloudflare 403 on every fetch method tried (`WebFetch`, MCP crawler). Skip straight to Chrome MCP if you need it specifically, otherwise don't bother.

## Tier 5 — Aggregators (last resort, verify everything per the parent skill's Phase 3)

- **`manua.ls/staplers/dewalt`** (and other `manua.ls/<category>/dewalt` catalog pages) — reachable via plain fetch, but the catalog is incomplete: as of 2026-08-16 it lists 102 DeWalt "stapler" manuals and neither DWHT75900 nor DWHT80276 is among them, which is consistent with Tier 2's finding that no manual exists for either — a useful cross-check, not a first stop.
- **`manualslib.com`** — general aggregator; not blocked, coverage untested in bulk this pass. Treat like any aggregator: a hit still needs Phase 3 verification (right model, actually instructions).

## Finding the Model Number and Type

DeWalt model numbers are on the rating label/data plate on the tool itself, always starting with a letter (commonly `D`, `DW`, `DC`, `DCS`, `DWHT`, `DCF`...). The **Type** number needed for the Tier 1 URL pattern is printed on the same label, usually as `TYPE <n>` near the model number — capture it in the same photo-zoom pass used to read the model number (see the parent skill's Phase 0). It is not necessarily the same as any date/batch code also printed there (e.g. a DWHT80276 unit checked this week showed `MFD 10-24`, a manufacture date code — not a Type number).

## Query Templates

```
site:dewalt.com "<model>"                                  ← find the exact product-page slug
"<model>" filetype:pdf site:assets.dewalt.com               ← sometimes indexed directly
site:pdf.lowes.com "<model>"                                 ← retailer mirror
"<model>" manual site:manualslib.com OR site:manua.ls        ← aggregator cross-check
```
