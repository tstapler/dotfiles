# Step 1: Layer 1 — Programmatic Compliance (Authoritative)

Layer 1 is the sole source of truth for measured clearances. No Claude vision is used
for measurements — only programmatic geometry extraction.

## 1a: Clear cached results

```bash
rm -f /tmp/compliance_layer1.json /tmp/clearances.json
```

## 1b: Run extract_clearances.py

```bash
~/.claude/skills/pdf-proof/.venv/bin/python3 \
  ~/.claude/skills/freecad-review/scripts/extract_clearances.py \
  --svg /home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_floor_plan_annotated.svg \
  --output /tmp/clearances.json
```

Verify: `test -s /tmp/clearances.json` (file must exist and be non-empty).

## 1c: Run check_compliance.py

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

## 1d: Parse results against SPEC.compliance_targets

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

## 1e: Carry through check_compliance.py results

For each item in `layer1['checks']`, if `result == 'CANNOT_VERIFY'`, append to verdicts
with `auto_fixable: false`. This is how GFCI and other electrical items surface in the
report — they come directly from check_compliance.py and are never resolved by Claude
without fresh programmatic evidence.

Rule: any item that arrives as `CANNOT_VERIFY` from a script stays `CANNOT_VERIFY`
in the review JSON. It can only change if the Layer 1 script produces a new result
in a subsequent run with updated drawing data.
