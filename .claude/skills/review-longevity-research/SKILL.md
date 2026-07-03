---
name: review-longevity-research
description: How to research community reviews and longevity signals for a physical product — where to look, how to weigh sponsored vs. organic sources, and how to read warranty/repairability/failure-mode signals as durability proxies. Use as a sub-step inside a larger research or product-selection process, not as a standalone entry point.
---

# Review & Longevity Research

A focused method for answering one question about a specific product/part: **will this hold up, and what do people who've owned it for a while actually say?** This is a sub-skill — it assumes a candidate product is already identified (by `product-selection`, a `home:2-research` Materials/Risks agent, etc.) and slots into that caller's research phase.

## Where to Look

Search roughly in this order of trust, not in strict sequence — run 2-3 of these per product, not all of them:

1. **Long-term-use community discussion** — `site:reddit.com "[product name]" review` or subreddit-specific searches (r/BuyItForLife for durability-focused categories, r/HomeImprovement, r/[trade] for tool/material categories). Look for threads where people report back *after months or years of ownership*, not first-impression posts.
2. **Independent long-form reviews** — Wirecutter/NYT Wirecutter, Consumer Reports (if accessible), and specialist review sites for the category (e.g. a plumbing-fixture trade publication). These do more hands-on durability testing than a listicle.
3. **"N years later" video reviews** — search YouTube for `"[product name]" "years later"` or `"[product name]" review update` — these surface failure modes that don't show up in week-one reviews.
4. **Manufacturer support forums / warranty claim discussions** — a product with an active complaints thread on the manufacturer's own forum is a stronger signal (people only go there when something broke) than its absence of complaints on a retailer page.

## Weighing Sponsored vs. Organic Sources

- **Discount, don't ignore, affiliate-driven "best X of 2026" listicles.** They're useful for discovering candidates, weak for judging durability — most are written from spec sheets and unboxing, not months of use. Treat their durability claims as unverified until corroborated elsewhere.
- **Weight specific, reproducible complaints over vague praise.** "The hinge cracked after about 8 months of daily use" (specific, falsifiable, time-stamped) outweighs "great product, love it!" (generic, could be day-one bias) regardless of which source it's in.
- **Look for independent corroboration.** One complaint is an anecdote; the same failure mode showing up across 3+ unrelated sources (a subreddit thread, a Wirecutter review's "durability concerns" section, and a manufacturer forum) is a real signal worth flagging.
- **Note when a category has no organic long-term data** (e.g. a brand-new product) — say so explicitly rather than presenting week-one impressions as a durability verdict.

## Longevity Proxies (when direct long-term reviews are thin)

- **Warranty length** — a manufacturer backing a product for 10+ years signals more confidence than a 90-day warranty, all else equal. Note the warranty length as a data point, not a guarantee.
- **Repairability** — are replacement parts, exploded diagrams, or repair manuals available from the manufacturer or third parties (e.g. iFixit-style teardowns for electronics/appliances)? A repairable product has a longer practical lifespan even if individual parts fail.
- **Construction signals** — solid metal vs. plastic load-bearing parts, sealed vs. exposed mechanisms in wet/high-use environments — these are visible in product photos/spec sheets and correlate with reported longevity even before reviews exist.
- **Common-failure-mode clustering** — when synthesizing, explicitly name the failure mode and the typical time-to-failure if a pattern emerges (e.g. "multiple reports of the pull-out sprayer hose cracking around the 2-year mark") rather than a vague "some durability concerns."

## Folding Into the Price-Tier Decision

Longevity signal and price tier are separate axes — don't assume price implies durability. State both explicitly so the caller (and eventually the user) can trade them off: a cheaper option with a strong BIFL reputation and a long warranty can beat a pricier option with a recurring failure-mode complaint. Flag this kind of inversion when it appears; it's exactly the situation this research is meant to catch.

## Sourcing Discipline

Follow the `meta-research-workflow` skill's Source Documentation Requirements for everything found here — every review-derived claim (a failure mode, a warranty length, a corroborated complaint) needs a URL and title, not just a paraphrase. If synthesizing into a wiki page, this feeds directly into the `knowledge-synthesis` skill's Product & Retailer Zettel Template's "why recommended (or not)" field.

## Output Shape

Whatever the caller's format, report review/longevity findings as a short block, not a wall of prose:

```markdown
### Review & Longevity — <Product Name>
- **Organic signal**: <2-3 sentence synthesis of what long-term owners say, with sources>
- **Longevity proxies**: warranty <length>, repairability <yes/no/notes>, construction notes
- **Recurring failure mode** (if any): <what, typical time-to-failure, source count>
- **Price/longevity tradeoff note**: <if relevant — e.g. "cheaper option has stronger long-term reputation than the premium pick">
```

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `meta-research-workflow` | Sourcing/citation discipline for every claim made here |
| `knowledge-synthesis` | Where review/longevity findings land once synthesized into a wiki product page |
| `product-selection` | Primary caller — runs this as part of its search/comparison phases |
| `home:2-research` | Materials and Risks agents call this for community-review and common-failure-mode digging |
