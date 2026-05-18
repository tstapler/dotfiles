---
name: design-review
description: "Use this skill when Tyler asks to review the kitchen design, run compliance checks, compare the BIM drawings to the CD set, or verify owner requirements. Produces a structured Markdown compliance report with PASS/FAIL/CANNOT_VERIFY per item. Standalone — does not modify anything. DO NOT invoke for a single spec edit (use design:modify) or the full iterative loop (use design:loop)."
---

# design:review — Kitchen Design Compliance & Intent Review

## What This Skill Does

Reads `design_spec.py` and the current output drawings, then produces a structured
Markdown compliance report covering:

1. **Layer 1** — Programmatic compliance using freecad-review scripts (authoritative)
2. **CD set comparison** — Rasterize-and-compare against the permit drawing set
3. **Owner requirements** — Per-item PASS / CANNOT_VERIFY verdict for each entry in `SPEC.owner_requirements`

Writes a machine-readable JSON to `/tmp/kitchen-design-loop/review_N.json` (N = iteration
number read from `.design-loop/session_state.json`, defaulting to 1).

Does NOT write to `design_spec.py` or any project source file.

---

## Prerequisites

- `design_spec.py` exists at `/home/tstapler/Documents/711-N60th-Plans/design_spec.py`
  and is importable: `python3 -c "from design_spec import SPEC" # must exit 0`
- `pixi run permit-docs` has been run and output files exist in `output/kitchen/`
- `~/.claude/skills/freecad-review/scripts/` contains `extract_clearances.py`,
  `check_compliance.py`, `rasterize_pdf_page.py`, and `add_grid.py`
- `~/.claude/skills/pdf-proof/.venv` contains ezdxf, Pillow, PyMuPDF (fitz)

---

## Step 0: Determine Iteration Number

```python
import json, os, pathlib

state_path = pathlib.Path('/home/tstapler/Documents/711-N60th-Plans/.design-loop/session_state.json')
if state_path.exists():
    state = json.loads(state_path.read_text())
    iteration = state.get('iteration', 0) + 1
else:
    iteration = 1

review_dir = pathlib.Path('/tmp/kitchen-design-loop')
review_dir.mkdir(parents=True, exist_ok=True)
review_json_path = review_dir / f'review_{iteration}.json'
```

---

## Step 1: Layer 1 — Programmatic Compliance (Authoritative)

Layer 1 is the sole source of truth for measured clearances. No Claude vision is used
for measurements — only programmatic geometry extraction.

### 1a: Clear cached results

```bash
rm -f /tmp/compliance_layer1.json /tmp/clearances.json
```

### 1b: Run extract_clearances.py

```bash
~/.claude/skills/pdf-proof/.venv/bin/python3 \
  ~/.claude/skills/freecad-review/scripts/extract_clearances.py \
  --svg /home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_floor_plan_annotated.svg \
  --output /tmp/clearances.json
```

Verify: `test -s /tmp/clearances.json` (file must exist and be non-empty).

### 1c: Run check_compliance.py

```bash
~/.claude/skills/pdf-proof/.venv/bin/python3 \
  ~/.claude/skills/freecad-review/scripts/check_compliance.py \
  --dxf /home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_floor_plan_annotated.dxf \
  --svg /home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_floor_plan_annotated.svg \
  --output /tmp/compliance_layer1.json
```

Verify: `test -s /tmp/compliance_layer1.json`.

If either file is missing or empty after running, report the script error and halt —
do not proceed with stale or missing data.

### 1d: Parse results against SPEC.compliance_targets

```python
import json
from design_spec import SPEC

clearances = json.loads(open('/tmp/clearances.json').read())
layer1 = json.loads(open('/tmp/compliance_layer1.json').read())
targets = SPEC.compliance_targets

# Build verdicts list
verdicts = []

# Map clearance keys to compliance_targets keys and rule names
AISLE_MAP = {
    'south_aisle_in': {
        'target_key': 'min_south_aisle_in',
        'preferred_key': 'preferred_south_aisle_in',
        'rule': 'NKBA-G12-aisle-with-seating',
        'id': 'island_south_aisle',
        'auto_fixable': True,
        'fix_field': 'bar_y_offset_mm',
    },
    'north_aisle_in': {
        'target_key': 'min_north_aisle_in',
        'preferred_key': None,
        'rule': 'NKBA-G4-aisle',
        'id': 'island_north_aisle',
        'auto_fixable': False,
        'fix_field': None,
    },
    'east_aisle_in': {
        'target_key': 'min_east_aisle_in',
        'preferred_key': None,
        'rule': 'NKBA-G4-aisle',
        'id': 'island_east_aisle',
        'auto_fixable': False,
        'fix_field': None,
    },
    'west_aisle_in': {
        'target_key': 'min_west_aisle_in',
        'preferred_key': None,
        'rule': 'NKBA-G4-aisle',
        'id': 'island_west_aisle',
        'auto_fixable': False,
        'fix_field': None,
    },
}

for clearance_key, meta in AISLE_MAP.items():
    measured = clearances.get(clearance_key)
    if measured is None:
        result = 'CANNOT_VERIFY'
        confidence = 'LOW'
    else:
        required = targets[meta['target_key']]
        preferred = targets.get(meta['preferred_key']) if meta['preferred_key'] else None
        if measured >= required:
            result = 'PASS'
            confidence = 'HIGH'
        else:
            result = 'FAIL'
            confidence = 'HIGH'

    verdicts.append({
        'id': meta['id'],
        'layer': 1,
        'rule': meta['rule'],
        'measured': measured,
        'required': targets.get(meta['target_key']),
        'preferred': preferred if 'preferred' in dir() else None,
        'result': result,
        'confidence': confidence,
        'auto_fixable': meta['auto_fixable'] if result == 'FAIL' else False,
        'fix_field': meta['fix_field'] if result == 'FAIL' else None,
    })
```

### 1e: Carry through check_compliance.py results

For each item in `layer1['checks']`, if `result == 'CANNOT_VERIFY'`, append to verdicts
with `auto_fixable: false`. This is how GFCI and other electrical items surface in the
report — they come directly from check_compliance.py and are never resolved by Claude
without fresh programmatic evidence.

Rule: any item that arrives as `CANNOT_VERIFY` from a script stays `CANNOT_VERIFY`
in the review JSON. It can only change if the Layer 1 script produces a new result
in a subsequent run with updated drawing data.

---

## Step 2: CD Set Comparison

### Scale normalization guard

Before any pixel comparison, read `SPEC.cd_page_references` and check `scale_factor`
for the target page. If `scale_factor != 1.0`, skip pixel-diff and use element-zone
comparison only (pixel-diff on mismatched scales produces misleading results).

CD set path: `SPEC.cd_page_references['cd_set_path']`
(= `/home/tstapler/Documents/711-N60th-Plans/260417-CD_SET_OWNER_REVIEW.pdf`)

### 2a: Floor plan comparison (CD page 4 vs BIM floor plan SVG)

CD page 4 is at 1/4" scale; BIM SVGs are at 1/2" scale → `scale_factor = 2.0`.
Skip pixel-diff. Use element-zone comparison only.

```bash
# Extract CD page 4
~/.claude/skills/pdf-proof/.venv/bin/python3 \
  ~/.claude/skills/freecad-review/scripts/rasterize_pdf_page.py \
  --pdf /home/tstapler/Documents/711-N60th-Plans/260417-CD_SET_OWNER_REVIEW.pdf \
  --page 4 --out /tmp/cd_page4.png --width 2000

# Rasterize BIM floor plan SVG
rsvg-convert -w 2000 \
  /home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_floor_plan_annotated.svg \
  -o /tmp/bim_floor_plan.png
```

If `rsvg-convert` is not installed: `brew install librsvg`

### 2b: Casework elevation comparison (CD pages 9 and 10 vs BIM elevation SVGs)

CD pages 9 and 10 are at 1/2" scale; BIM SVGs are at 1/2" scale → `scale_factor = 1.0`.
Pixel-diff is valid for these pages.

```bash
# Extract CD page 9
~/.claude/skills/pdf-proof/.venv/bin/python3 \
  ~/.claude/skills/freecad-review/scripts/rasterize_pdf_page.py \
  --pdf /home/tstapler/Documents/711-N60th-Plans/260417-CD_SET_OWNER_REVIEW.pdf \
  --page 9 --out /tmp/cd_page9.png --width 2000

# Rasterize matching BIM elevation SVG (north elevation)
rsvg-convert -w 2000 \
  /home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_elev_north.svg \
  -o /tmp/bim_elev_north.png
```

For pixel-diff (only when scale_factor == 1.0):
```python
from PIL import Image, ImageChops
cd = Image.open('/tmp/cd_page9.png').convert('RGB')
bim = Image.open('/tmp/bim_elev_north.png').convert('RGB')
# Resize to same dimensions before diff
if cd.size != bim.size:
    bim = bim.resize(cd.size, Image.LANCZOS)
diff = ImageChops.difference(cd, bim)
diff.save('/tmp/cd_bim_diff_p9.png')
```

### 2c: Run Layer 3 dual-pass visual inventory

**Pass 1 — Element Inventory on each PNG**

For each PNG (CD and BIM), extract SVG text labels then run Claude visual review:

```python
# Extract BIM SVG labels
import xml.etree.ElementTree as ET
ns = '{http://www.w3.org/2000/svg}'
tree = ET.parse('/home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_floor_plan_annotated.svg')
labels = [el.text.strip() for el in tree.iter(f'{ns}text')
          if el.text and el.text.strip()]
```

Send each rasterized PNG plus the extracted labels to Claude for element inventory.
Use the zone grid from freecad-review SKILL.md:
`A=west, G=east, 1=north, 5=south; Island=C3-E4, Bar=C4-D4, Sink=B1, Fridge=D1`

Prompt for Pass 1:
```
You are reviewing a kitchen floor plan. Labeled dimensions are provided below.
Do not estimate any dimension not in that list — output CANNOT_VERIFY for anything unlabeled.

LABELED DIMENSIONS: {labels}

List every named element (appliances, island, counters, walls, openings) and its
approximate zone position using grid A1-G5. Output JSON:
{"elements": [{"name": str, "zone": str, "notes": str, "label_evidence": [str]}]}
```

**Pass 2 — Change Detection** (text-only, no image needed)

```
Compare these two kitchen element inventories and identify every element that moved,
was added, or was removed.

EXISTING (CD set): {cd_inventory_json}
PROPOSED (BIM): {bim_inventory_json}

For each change, cite specific label evidence. If no evidence is visible, set
confidence to LOW. Output JSON:
{"changes": [...], "unchanged": [...], "low_confidence_items": [...]}
```

### 2d: Write CD comparison results to review JSON

```python
cd_comparison = {
    'page': 4,
    'scale_matched': False,   # scale_factor == 2.0 for page 4
    'pixel_diff_used': False,
    'changes': [],            # filled from Pass 2
    'unchanged': [],
    'low_confidence_items': [],
}
```

---

## Step 3: Owner Requirements Verification

Read `SPEC.owner_requirements` and produce a per-item verdict.

### Verification mapping

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

---

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

---

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

---

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

---

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

---

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

---

## Related Skills

- `freecad-review` — Layer 1 scripts, Layer 3 dual-pass protocol, IRC compliance checklist
- `design:modify` — apply a fix from the "Issues for design:modify" section
- `design:loop` — orchestrates review → modify → QA in a capped cycle
