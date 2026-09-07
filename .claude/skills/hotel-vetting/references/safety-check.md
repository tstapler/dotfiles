# Step 2 — Neighborhood Safety Check (Full Detail)

Run in parallel with review aggregation. This step is non-negotiable — do not skip it even for brand-name hotels.

## 2a. Corridor Check

Identify the street the hotel is on. Check whether it is a known problematic corridor:

Known high-concern corridors (non-exhaustive — always search regardless):
- Aurora Ave N (Seattle) — prostitution, drug activity, motel culture
- Highway 99 strips (various WA cities)
- Pacific Hwy S (SeaTac/Tukwila)
- Any "motel row" adjacent to a freeway interchange

Search: `"[street name] [city] safety"` and `"[street name] [city] crime"`

If the hotel is on or within one block of a flagged corridor: automatic Safety dimension cap at 3/5 (see the scoring rubric). Guests will encounter the environment even if the property itself is managed.

## 2b. Recent Crime Search

Run all three searches:
1. `"[hotel address]" crime OR incident OR police`
2. `"[neighborhood name] [city] crime 2024"` or `"[neighborhood name] [city] crime 2025"`
3. `"[hotel name] [city]" assault OR robbery OR theft OR arrest`

Record any hits from the last 12 months. Distinguish between:
- Isolated incidents (single reports, not a pattern) — note but do not penalize heavily
- Patterns (multiple incidents, same type, recurring) — penalize Safety dimension
- On-property incidents vs. nearby street incidents

## 2c. Local Police Blotter / News

Search: `"[hotel name]" OR "[hotel address]" site:[localpolice].gov OR site:[localnews].com`

Examples for Seattle: `"[hotel name]" site:seattle.gov OR site:seattletimes.com OR site:crosscut.com`

Check for:
- Police calls for service at the address
- Local news coverage of incidents at the property
- SPD (or local PD) public log mentions

## 2d. OSM Overpass — Nearby POI Context

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
