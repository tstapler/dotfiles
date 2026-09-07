# Step 1 — Multi-Source Review Aggregation (Full Detail)

For each hotel, collect ratings and review counts from four sources. Normalize all to a 10-point scale.

## Sources and Search Queries

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

## Composite Score

```
composite_10 = weighted average of available sources:
  - Google: weight 0.30
  - Booking.com: weight 0.35  (largest review base, most granular)
  - TripAdvisor: weight 0.25
  - Kayak/Hotels.com: weight 0.10
```

Drop a source from the average if it cannot be found (do not impute). Note which sources are missing.

## Flags

- **Low review count**: < 50 reviews on any major source → flag with (low-count)
- **Review count mismatch**: one source shows 500+ reviews, another shows < 20 → flag inconsistency, investigate
- **Score divergence**: any two sources differ by > 2.0 normalized points → flag, note the outlier and its likely cause
- **Recent rating cliff**: if you can detect a recent drop in ratings (post-2023), flag it — could indicate ownership change, renovation disruption, or management decline
