# Steps 4–5: Build Review JSON, Generate Markdown Report, and Reference Data

## Step 4: Build and Write Review JSON

```python
import json, datetime, hashlib, pathlib

spec_bytes = open('/home/tstapler/Documents/711-N60th-Plans/design_spec.py', 'rb').read()
spec_hash = hashlib.sha256(spec_bytes).hexdigest()[:12]

overall = 'FAIL' if any(v['result'] == 'FAIL' for v in verdicts) else (
    'CANNOT_VERIFY' if any(v['result'] == 'CANNOT_VERIFY' for v in verdicts) else 'PASS'
)

review_doc = {
    'iteration': iteration,
    'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
    'spec_hash': spec_hash,
    'layer1': {
        'checks': layer1.get('checks', []),
        'clearances': clearances,
    },
    'cd_comparison': cd_comparison,
    'owner_requirements': owner_req_results,   # from Step 3
    'verdicts': verdicts,
    'overall': overall,
}

pathlib.Path('/tmp/kitchen-design-loop').mkdir(parents=True, exist_ok=True)
with open(f'/tmp/kitchen-design-loop/review_{iteration}.json', 'w') as f:
    json.dump(review_doc, f, indent=2)
```

## Step 5: Generate Markdown Report

```markdown
# Kitchen Compliance Review — Iteration {iteration}
**Date**: {timestamp}  |  **Spec hash**: {spec_hash}  |  **Overall**: {overall}

## Layer 1 — Programmatic Compliance (Authoritative)

| Requirement | Rule | Measured | Required | Preferred | Result |
|---|---|---|---|---|---|
| Island south aisle | NKBA-G12 | {south_aisle_in}" | ≥ 42" | ≥ 48" | {result} |
| Island north aisle | NKBA-G4  | {north_aisle_in}" | ≥ 42" | — | {result} |
| Island east aisle  | NKBA-G4  | {east_aisle_in}"  | ≥ 42" | — | {result} |
| Island west aisle  | NKBA-G4  | {west_aisle_in}"  | ≥ 42" | — | {result} |
| GFCI island outlet | NEC 210.8 | — | Required | — | CANNOT_VERIFY |
| Work triangle      | NKBA-G4  | {wt_ft} ft | ≤ 26 ft | — | {result} |

Use ✅ PASS, ❌ FAIL, ⚠️ CANNOT_VERIFY symbols in the Result column.

## CD Set Comparison

| Sheet | CD Page | Scale match | Changes detected |
|---|---|---|---|
| Floor plan | 4 | No (2× upscale needed) | Element-zone comparison only |
| Casework elev | 9 | Yes | {count} changes |
| Casework elev | 10 | Yes | {count} changes |

## Owner Requirements

| Requirement | Result | Confidence | Evidence |
|---|---|---|---|
{rows from Step 3}

## Items Requiring Human Review

For each CANNOT_VERIFY or LOW-confidence item:
- [ ] **{item}** — {reason why programmatic check cannot confirm}

## Recommended Next Actions

{ordered by severity — FAIL items only}
```

## Output Report Format Details

### Result column values

| Symbol | Meaning | Auto-fixable by design:modify? |
|---|---|---|
| ✅ PASS | Measurement meets or exceeds minimum | n/a |
| ❌ FAIL | Measurement below minimum | Only if `auto_fixable: true` in review JSON |
| ⚠️ CANNOT_VERIFY | Script could not produce a measurement | Never — requires human |

### FAIL vs CANNOT_VERIFY distinction

**FAIL**: The Layer 1 script ran and produced a measured value that is below the
required minimum. The measurement is reliable. `design:modify` can compute a fix.

**CANNOT_VERIFY**: Either (a) the script could not extract the relevant geometry
(electrical layer missing, element not in SVG), or (b) the check requires visual
inspection (elevation view, hood CFM spec sheet). Claude never upgrades a
CANNOT_VERIFY to PASS without a fresh script result that returns a numeric measurement.

### CANNOT_VERIFY escalation rules (Story 2.1.3)

Every CANNOT_VERIFY item in the review JSON must have:
- `auto_fixable: false`
- A human-readable note explaining what evidence is needed
- Appearance in the "Items Requiring Human Review" section
- Persistence across iterations until fresh script evidence arrives

## Issues for design:modify

This section lists only FAIL items with `auto_fixable: true` and a suggested fix.
Design:modify reads this section when invoked from design:loop.

Format:
```
## Issues for design:modify

| Field | Current value | Suggested fix | Predicted result |
|---|---|---|---|
| bar_y_offset_mm | 762.0 mm (south aisle 30.0") | 1066.8 mm min / 1092.2 mm preferred | South aisle ≥ 42" |
```

The suggested fix values are computed by the constraint simulator (see design:modify
SKILL.md, Story 3.1). This section is informational in the review output — the actual
simulation and validation happen inside design:modify before any file write.

## Coordinate and Unit Reference

From `kitchen_permit_docs.py` derivations (all values in mm unless noted):
- `SVG_PER_INCH = 3.306`
- `KIT_SVG_X0 = 297.1` (interior west wall SVG x)
- `KIT_SVG_Y0 = 166.0` (interior north wall SVG y)
- `KI_S = SPEC.kit_s_out_mm + SPEC.ext_thk_mm` = -182.4 mm
- `KI_N = KI_S + SPEC.kit_ns_mm` = 2992.6 mm
- `KI_W = SPEC.kit_w_out_mm + SPEC.ext_thk_mm`
- `KI_E = KI_W + SPEC.kit_ew_mm`
- Ground truth (default spec): south aisle = 30.0", north aisle = 55.0"
