# Step 3: Owner Requirements Verification

Read `SPEC.owner_requirements` and produce a per-item verdict.

## Verification mapping

| Requirement | Verification method | Confidence |
|---|---|---|
| Range on island with ceiling-mounted hood | Layer 1: range position vs island Y coordinates | HIGH |
| Island seating for 3 (bar height south face) | Layer 1: `bar_ns_mm / 609.6 >= 3` (24" per seat) | MEDIUM |
| Refrigerator in northeast quadrant | Layer 3 element inventory: zone in {D1, E1, F1} | MEDIUM |
| Sink on north wall centered under W-101 window | Layer 1: sink Y > KI_N - threshold (within 12" of north wall) | HIGH |
| Dishwasher on east wall south of refrigerator | Layer 3 element inventory: zone in {F2, F3, G2, G3} | MEDIUM |
| Patio door (G3KH) preserved on south wall | Layer 3: G3KH present in zone {D5, E5} | MEDIUM |
| Glulam beam (S2.1) visible — no dropped soffit | Elevation review only — CANNOT_VERIFY from plan view | LOW |
| Upper cabinets to ceiling height (7'-0") | Layer 1: `SPEC.ucab_bot_mm + SPEC.ucab_h_mm >= SPEC.ceil_ht_mm - 25.4` | HIGH |

Rules for each item:
- HIGH confidence: check programmatically from SPEC or Layer 1 clearances data
- MEDIUM confidence: requires element inventory from Layer 3 Pass 1
- LOW confidence: requires elevation visual review — always CANNOT_VERIFY from plan

Write results to review JSON under `"owner_requirements"` key:
```json
{
  "owner_requirements": [
    {
      "requirement": "Range on island with ceiling-mounted hood",
      "result": "PASS",
      "confidence": "HIGH",
      "evidence": "Layer 1: range Y position confirmed within island footprint"
    }
  ]
}
```
