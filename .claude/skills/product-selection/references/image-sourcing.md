# Image Sourcing & Domain Routing Reference

Detail supporting Phase 3 (Image Sourcing) and Phase 4 (URL Validation) of the main
`SKILL.md` workflow.

## Fetch Tool Hierarchy

Use tools in this order when a domain blocks WebFetch:

1. **`WebFetch`** — try first; fast and sufficient for accessible domains
2. **`mcp__stapler-mcp__read_website`** — try when WebFetch returns 403/429; often bypasses bot protection that blocks WebFetch. Save to `/tmp` if page is large.
3. **Chrome MCP (`mcp__claude-in-chrome__navigate` + `mcp__claude-in-chrome__get_page_text`)** — last resort for pages that require JavaScript rendering or are behind login walls. Use when stapler-mcp also fails. Load tools via ToolSearch before calling.

Never give up on a preferred retailer (Lowe's, Amazon) without trying all three tools.

## Critical Domain Routing

**Try `mcp__stapler-mcp__read_website` before giving up — may bypass bot protection:**

| Domain | WebFetch result | Fallback |
|---|---|---|
| lowes.com | 403 Forbidden — **preferred human link** | try stapler-mcp, then Chrome MCP |
| amazon.com | 500 / robot challenge — **preferred human link** | try stapler-mcp, then Chrome MCP |
| homedepot.com | 403 Forbidden | try stapler-mcp |
| wayfair.com | 429 / 403 | try stapler-mcp |
| walmart.com | Robot challenge | try stapler-mcp |
| signaturehardware.com | 403 Forbidden | try stapler-mcp |
| ferguson.com | Akamai bot | try stapler-mcp |
| fergusonhome.com | 403 Forbidden | try stapler-mcp |
| ebay.com | Timeout | try stapler-mcp |
| faucet.com | 404 (stale URL patterns) | re-search for updated URL |
| faucetdirect.com | 404 (stale URL patterns) | re-search for updated URL |
| build.com → fergusonhome.com | 403 Forbidden | try stapler-mcp |

Only mark a domain ⚠ browser only after all three fetch methods have failed.

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

## Image Sourcing Priority Order

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

## Image URL Validation

Try tools in order until one succeeds:
```
1. WebFetch(url=image_url, prompt="Is this a valid accessible image? Return HTTP status and approximate file size in KB.")
2. mcp__stapler-mcp__read_website(url=image_url) — if WebFetch blocked
3. Chrome MCP navigate + screenshot — if both above fail and domain is a preferred retailer
```
**Interpreting results** (WebFetch/stapler-mcp can't render binary images — binary saves are valid):
- Valid signal: Binary JPEG/PNG file saved, size **> 5KB** → confirmed working image
- Invalid: HTTP 403 or 404 on all three tools → discard, find alternative
- Ambiguous: File saved but < 3KB → likely a placeholder or error icon → discard

## Product Page Validation

Try tools in order:
```
1. WebFetch(url=product_url, prompt="Return HTTP status and page title.")
2. mcp__stapler-mcp__read_website(url=product_url) — if WebFetch blocked
3. Chrome MCP navigate — if both above fail; navigate and read page text
```
- Success + matching page title → confirmed ✓
- HTTP 404 on all tools → URL is stale; search for updated URL on the same domain
- All tools blocked → note ⚠ browser only; URL still usable as human link
