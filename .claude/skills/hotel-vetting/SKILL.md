---
name: hotel-vetting
description: Structured pipeline for vetting hotels before recommending them to wedding guests or event guests. Aggregates reviews from multiple sources, checks neighborhood safety, scores on five guest-fitness dimensions, and produces a structured verdict card per property.
---

# Hotel Vetting Skill

Use this skill whenever you need to evaluate hotels before recommending them to guests attending a wedding, rehearsal dinner, corporate event, or any hosted gathering where the host is vouching for the accommodations.

## When to Trigger

- User asks to vet, evaluate, or approve hotels for a guest room block
- User shares a list of hotel options near a venue and wants a recommendation
- User asks "is [hotel] a good option for guests?"
- User asks to find hotels near a venue and assess them
- User is building a travel guide or wedding website and needs vetted property options
- A hotel is on a corridor with a known reputation (Aurora Ave N, Highway strips, etc.)

**Default stance: skeptical.** Err toward DO NOT RECOMMEND when data is sparse, reviews are inconsistent, or the neighborhood is ambiguous. Guests trust the host's recommendation — a bad hotel reflects on the event organizer.

---

## Protocol Overview

Run Steps 1–3 in parallel using the Agent tool — one subagent per hotel, each executing the full pipeline. Synthesize results in Step 4. Produce output cards in Step 5.

```
For each hotel: [Step 1: Reviews] + [Step 2: Safety] run in parallel
                       ↓
              Step 3: Score all dimensions
                       ↓
              Step 4: Verdict
                       ↓
              Step 5: Output card
```

---

## Step 1 — Multi-Source Review Aggregation

For each hotel, collect ratings and review counts from four sources (Google Maps, TripAdvisor, Booking.com, Kayak/Hotels.com), normalize each to a 10-point scale, and compute a weighted composite score (Booking.com weighted highest at 0.35, then Google 0.30, TripAdvisor 0.25, Kayak/Hotels.com 0.10). Drop missing sources from the average rather than imputing them, and flag low review counts (< 50), review-count mismatches between sources, score divergence (> 2.0 points), and any recent rating cliff.

Full search queries, per-source normalization formulas, and flag definitions: [references/review-aggregation.md](references/review-aggregation.md).

---

## Step 2 — Neighborhood Safety Check

Run in parallel with Step 1. **Non-negotiable** — do not skip it even for brand-name hotels. Covers four checks: (a) whether the hotel sits on a known problematic corridor, (b) a recent crime search (address, neighborhood, hotel name), (c) local police blotter / news coverage, and (d) an OSM Overpass query for nearby POIs (bars, pawn shops, dispensaries) that signal neighborhood character.

A hotel on or within one block of a flagged corridor auto-caps the Safety dimension at 3/5.

Full search queries and the Overpass query template: [references/safety-check.md](references/safety-check.md).

---

## Step 3 — Wedding-Guest Fitness Scoring

Score five dimensions, 1–5, half-points allowed:

1. **Cleanliness** — from review evidence
2. **Safety** — neighborhood + property; auto-capped by Step 2 findings (corridor → max 3, on-property violent crime in last 12mo → max 2, multiple/active coverage → 1)
3. **Walkability to Event Venues** — always computed via the **geo-validation** skill, never estimated from memory
4. **Guest Experience** — staff, amenities, value
5. **Reputational Risk** — would recommending this hotel embarrass the host?

Full per-score evidence tables for all five dimensions: [references/scoring-rubric.md](references/scoring-rubric.md).

---

## Step 4 — Verdict

Apply the verdict rules strictly. Do not apply judgment to override the scoring rubric.

### Verdict Rules

**RECOMMEND** — all of the following:
- All five dimensions score 4 or above
- Composite review score ≥ 7.5/10
- No active safety flags from Step 2
- No low-count or divergence flags that were unresolvable

**RECOMMEND WITH CAVEAT** — all of the following:
- No dimension scores below 3
- Composite review score ≥ 6.5/10
- The caveat must be explicit: what should guests be told? (noise, limited parking, urban area, etc.)
- Reputational Risk ≥ 3 (host can stand behind the recommendation with caveats)

**DO NOT RECOMMEND** — any of the following:
- Any dimension scores 1 or 2
- Composite review score < 6.5/10
- Active safety flag (on-property crime, flagged corridor with low Safety score)
- Data is too sparse to score with confidence (< 50 reviews across all sources, only 1–2 sources found)
- Significant inconsistency across sources that cannot be explained

**When in doubt, DO NOT RECOMMEND.** The cost of sending guests to a bad hotel is much higher than the cost of having fewer options.

---

## Step 5 — Output Format

Produce one structured card per hotel. Cards are separated by `---`.

```
## [Hotel Name]
**Address**: [full street address]
**Star Rating**: [1–5 stars, official classification]
**Composite Review Score**: [X.X / 10] (Google: X.X | Booking: X.X | TripAdvisor: X.X | Kayak: X.X)
**Review Count**: [total across sources; flag if < 50 on any major source]

### Fitness Scores
| Dimension | Score | Notes |
|-----------|-------|-------|
| Cleanliness | X / 5 | [1-sentence rationale] |
| Safety | X / 5 | [1-sentence rationale] |
| Walkability | X / 5 | [distance + barrier summary from geo-validation] |
| Guest Experience | X / 5 | [1-sentence rationale] |
| Reputational Risk | X / 5 | [1-sentence rationale] |

### Verdict
[✅ RECOMMEND | ⚠️ RECOMMEND WITH CAVEAT | ❌ DO NOT RECOMMEND]

[If RECOMMEND or RECOMMEND WITH CAVEAT:]
**Guest-Facing Description** (2 sentences, copy-paste ready for travel guide):
> [Warm, accurate, guest-appropriate description of the hotel and its location. Do not mention safety research or internal findings.]

[If RECOMMEND WITH CAVEAT:]
**What to Tell Guests**: [Plain-language caveat the host can share — e.g., "This hotel is in an urban area; street parking requires a short walk at night."]

### Internal Notes
[What you found that guests don't need to see — crime search results, corridor concerns, review inconsistencies, data gaps, Overpass findings, anything the host should know but not publish.]
```

---

## Parallelization Instructions

When vetting a list of hotels, use the Agent tool to run one subagent per hotel simultaneously. Each subagent executes Steps 1–3 for its assigned hotel and returns a completed score table. The orchestrating agent runs Step 4 (verdict) and Step 5 (card formatting) after all subagents complete.

Template instruction to pass each subagent:

> You are vetting [Hotel Name] at [address] for wedding guest recommendation. Execute the hotel-vetting skill Steps 1–3: aggregate reviews from Google, TripAdvisor, Booking.com, and Kayak; run the neighborhood safety check (corridor check, crime search, police blotter, OSM Overpass); score all five dimensions using the rubric. Return a JSON object with: hotel_name, address, source_scores (dict), composite_10, dimension_scores (dict of 5 values), flags (list), safety_summary (string), walkability_raw (distance in miles, barriers found — use geo-validation skill), and internal_notes (string).

After all subagents return, synthesize into verdict cards.

---

## Checklist Before Finalizing

- [ ] All four review sources searched (note if any unavailable)
- [ ] Review counts recorded; low-count flag applied where appropriate
- [ ] Score divergence > 2.0 points investigated
- [ ] Corridor check run for the hotel's street
- [ ] All three crime searches executed (address, neighborhood, hotel name)
- [ ] Local news searched for last 12 months
- [ ] OSM Overpass run for nearby context POIs
- [ ] geo-validation skill used for walkability (not estimated)
- [ ] Verdict applied by rubric, not by gut feel
- [ ] Internal notes separated from guest-facing description
- [ ] Guest-facing description contains nothing alarming or internal

---

## Related Skills

- **geo-validation** — required for Walkability dimension; provides Nominatim geocoding, barrier detection, and walk time computation
- **deep-research** — use for hotels with sparse online presence or unusual news coverage that warrants deeper investigation
- **product-selection** — use if you need to find additional hotel options (not just vet a given list)
