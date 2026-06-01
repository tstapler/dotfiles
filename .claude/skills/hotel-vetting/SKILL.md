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

For each hotel, collect ratings and review counts from four sources. Normalize all to a 10-point scale.

### Sources and Search Queries

**Google Maps**
- Search: `"[Hotel Name] [City]" site:google.com/maps OR "[Hotel Name] [address] Google reviews"`
- Use `WebSearch` or `mcp__brave-search__brave_web_search` — do not fabricate a star count
- Record: star rating (1–5), review count, top-cited complaints
- Normalize: `google_10 = star_rating * 2`

**TripAdvisor**
- Search: `"[Hotel Name] [City]" site:tripadvisor.com`
- Record: bubble rating (1–5), traveler rating label (Terrible/Poor/Average/Very Good/Excellent), review count
- Normalize: `ta_10 = bubble_rating * 2`

**Booking.com**
- Search: `"[Hotel Name] [City]" site:booking.com`
- Record: score (0–10, already normalized), review count, category subscores if visible (staff, cleanliness, location, value)
- Normalize: direct (0–10 scale)

**Kayak / Hotels.com**
- Search: `"[Hotel Name] [City]" site:kayak.com OR site:hotels.com`
- Record: rating (typically 0–10 or 0–5), review count
- Normalize to 10-point scale accordingly

### Composite Score

```
composite_10 = weighted average of available sources:
  - Google: weight 0.30
  - Booking.com: weight 0.35  (largest review base, most granular)
  - TripAdvisor: weight 0.25
  - Kayak/Hotels.com: weight 0.10
```

Drop a source from the average if it cannot be found (do not impute). Note which sources are missing.

### Flags

- **Low review count**: < 50 reviews on any major source → flag with (low-count)
- **Review count mismatch**: one source shows 500+ reviews, another shows < 20 → flag inconsistency, investigate
- **Score divergence**: any two sources differ by > 2.0 normalized points → flag, note the outlier and its likely cause
- **Recent rating cliff**: if you can detect a recent drop in ratings (post-2023), flag it — could indicate ownership change, renovation disruption, or management decline

---

## Step 2 — Neighborhood Safety Check

Run in parallel with Step 1. This step is non-negotiable — do not skip it even for brand-name hotels.

### 2a. Corridor Check

Identify the street the hotel is on. Check whether it is a known problematic corridor:

Known high-concern corridors (non-exhaustive — always search regardless):
- Aurora Ave N (Seattle) — prostitution, drug activity, motel culture
- Highway 99 strips (various WA cities)
- Pacific Hwy S (SeaTac/Tukwila)
- Any "motel row" adjacent to a freeway interchange

Search: `"[street name] [city] safety"` and `"[street name] [city] crime"`

If the hotel is on or within one block of a flagged corridor: automatic Safety dimension cap at 3/5 (see Step 3). Guests will encounter the environment even if the property itself is managed.

### 2b. Recent Crime Search

Run all three searches:
1. `"[hotel address]" crime OR incident OR police`
2. `"[neighborhood name] [city] crime 2024"` or `"[neighborhood name] [city] crime 2025"`
3. `"[hotel name] [city]" assault OR robbery OR theft OR arrest`

Record any hits from the last 12 months. Distinguish between:
- Isolated incidents (single reports, not a pattern) — note but do not penalize heavily
- Patterns (multiple incidents, same type, recurring) — penalize Safety dimension
- On-property incidents vs. nearby street incidents

### 2c. Local Police Blotter / News

Search: `"[hotel name]" OR "[hotel address]" site:[localpolice].gov OR site:[localnews].com`

Examples for Seattle: `"[hotel name]" site:seattle.gov OR site:seattletimes.com OR site:crosscut.com`

Check for:
- Police calls for service at the address
- Local news coverage of incidents at the property
- SPD (or local PD) public log mentions

### 2d. OSM Overpass — Nearby POI Context

Use the geo-validation skill's Overpass query pattern to pull nearby POIs that signal neighborhood character:

```python
# Query for POIs within 500m of the hotel that may concern guests
query = f"""
[out:json][timeout:25];
(
  node["amenity"~"casino|nightclub|bar|social_facility|shelter"](around:500,{lat},{lon});
  node["shop"~"alcohol|cannabis|pawn"](around:500,{lat},{lon});
  node["highway"="motorway"](around:200,{lat},{lon});
);
out body;
"""
```

A concentration of bars, pawn shops, or cannabis dispensaries within 200m is a contextual flag — not disqualifying on its own, but relevant for a family-friendly guest list.

---

## Step 3 — Wedding-Guest Fitness Scoring

Score each dimension 1–5. Half-points allowed (e.g., 3.5). Use the rubric below.

### Dimension 1: Cleanliness (from reviews)

| Score | Evidence |
|-------|----------|
| 5 | Cleanliness consistently praised across all sources; Booking.com cleanliness subscore ≥ 9.0 |
| 4 | Mostly positive; occasional isolated complaint about a specific room |
| 3 | Mixed; some recent reviews cite dirty rooms, stained linens, or maintenance neglect |
| 2 | Multiple recent complaints about cleanliness; Booking.com cleanliness subscore < 7.0 |
| 1 | Systemic cleanliness failures; bed bug reports; health department citations in news |

### Dimension 2: Safety (neighborhood + property)

| Score | Evidence |
|-------|----------|
| 5 | Quiet residential or commercial neighborhood; no crime hits; no corridor concerns |
| 4 | Urban/mixed-use but no specific incidents; minor corridor proximity; guests safe walking at night |
| 3 | Notable corridor proximity OR 1–2 isolated incidents in the last 12 months; guests should be aware |
| 2 | Known problematic corridor AND/OR pattern of incidents; guests need explicit warning |
| 1 | Active crime pattern at or adjacent to property; do not send guests here |

**Auto-cap rules:**
- On a flagged corridor: max score 3
- Any on-property violent crime in last 12 months: max score 2
- Multiple violent incidents or active news coverage: score 1

### Dimension 3: Walkability to Event Venues

Use the **geo-validation skill** to compute actual walking distances and barrier analysis.

| Score | Evidence |
|-------|----------|
| 5 | < 0.3 miles to primary venue with no major road barriers; guests can walk in event attire |
| 4 | 0.3–0.7 miles, or slightly farther with good pedestrian infrastructure |
| 3 | 0.7–1.2 miles OR barrier exists but crossing is safe and documented |
| 2 | > 1.2 miles OR crossing a motorway/major arterial without a safe pedestrian crossing |
| 1 | Requires rideshare for all guests; walking is unsafe or impractical |

**Always run geo-validation before scoring this dimension.** Do not estimate walk time from memory.

For guests arriving by car: note parking situation and cost in internal notes.
For guests arriving by transit: note nearest transit stop and travel time.

### Dimension 4: Guest Experience (staff, amenities, value)

| Score | Evidence |
|-------|----------|
| 5 | Staff consistently praised; amenities match or exceed price point; no surprise fees |
| 4 | Solid reviews on staff; standard amenities; minor value complaints |
| 3 | Mixed staff reviews; amenities adequate but not noteworthy; some value complaints |
| 2 | Frequent complaints about staff responsiveness, hidden fees, or misleading listings |
| 1 | Systemic guest complaints; owner responses combative; do not recommend on guest experience alone |

### Dimension 5: Reputational Risk

This dimension protects the event host. Would guests be uncomfortable or surprised by the surroundings? Would recommending this hotel embarrass the host?

| Score | Evidence |
|-------|----------|
| 5 | Guests will have no surprises; property matches or exceeds expectations set by recommendation |
| 4 | Minor surprises (urban grit, noise) but nothing the host should feel responsible for |
| 3 | Some guests may be uncomfortable; host should caveat the recommendation |
| 2 | A meaningful portion of guests will feel misled or unsafe; significant reputational risk |
| 1 | Recommending this hotel would actively embarrass the host; guests would question judgment |

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
