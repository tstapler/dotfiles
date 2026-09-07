# QA Compliance Steps — Full Detail

Full commands and code for design:qa Steps 1–5. See SKILL.md for the verdict
precedence order these results feed into.

## Step 1: Cache Invalidation (unconditional)

At the start of every design:qa run, delete any cached compliance JSON regardless
of how it was invoked (from loop or directly):

```bash
rm -f /tmp/compliance_layer1.json /tmp/clearances.json
```

Then verify that the compliance JSON to be generated will be newer than
`design_spec.py` mtime. If a compliance JSON already exists after this `rm`,
something is wrong — halt and report.

## Step 2: Fresh Layer 1 Compliance Run

### 2a: Run extract_clearances.py

```bash
~/.claude/skills/pdf-proof/.venv/bin/python3 \
  ~/.claude/skills/freecad-review/scripts/extract_clearances.py \
  --svg /home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_floor_plan_annotated.svg \
  --output /tmp/clearances.json
```

Verify: `test -s /tmp/clearances.json`

### 2b: Run check_compliance.py

```bash
~/.claude/skills/pdf-proof/.venv/bin/python3 \
  ~/.claude/skills/freecad-review/scripts/check_compliance.py \
  --dxf /home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_floor_plan_annotated.dxf \
  --svg /home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_floor_plan_annotated.svg \
  --output /tmp/compliance_layer1.json
```

Verify: `test -s /tmp/compliance_layer1.json`

If either file is missing or empty: treat as pipeline failure → BLOCKED verdict.

### 2c: Verify compliance JSON is not stale

```python
import os

spec_mtime = os.path.getmtime(
    '/home/tstapler/Documents/711-N60th-Plans/design_spec.py')
cl1_mtime = os.path.getmtime('/tmp/compliance_layer1.json')

if cl1_mtime < spec_mtime:
    raise AssertionError(
        "compliance_layer1.json predates design_spec.py — stale result. "
        "Re-run extract_clearances.py and check_compliance.py."
    )
```

## Step 3: Compare Against Pre-Modify Baseline

### 3a: Load baseline review JSON

```python
import json, pathlib

state_path = pathlib.Path(
    '/home/tstapler/Documents/711-N60th-Plans/.design-loop/session_state.json')

if state_path.exists():
    state = json.loads(state_path.read_text())
    N_prev = state.get("iteration", 0)
else:
    state = None
    N_prev = 0

baseline_path = pathlib.Path(f'/tmp/kitchen-design-loop/review_{N_prev}.json')
if baseline_path.exists():
    baseline = json.loads(baseline_path.read_text())
    baseline_verdicts = {v["id"]: v for v in baseline.get("verdicts", [])}
else:
    baseline = None
    baseline_verdicts = {}
```

### 3b: Build fresh verdicts from Layer 1 results

Parse `compliance_layer1.json` and `clearances.json` against `SPEC.compliance_targets`
using the same AISLE_MAP as `design:review` Step 1d (see
`~/.claude/skills/design-review/references/layer1-compliance.md`).

### 3c: Classify changes

```python
resolved = []
persisting = []
regressions = []

for item_id, fresh_v in fresh_verdicts.items():
    baseline_v = baseline_verdicts.get(item_id)
    if baseline_v is None:
        # No baseline — treat as new item, cannot classify as regression
        if fresh_v["result"] == "FAIL":
            persisting.append(item_id)
        continue

    if baseline_v["result"] == "FAIL" and fresh_v["result"] == "PASS":
        resolved.append(item_id)
    elif baseline_v["result"] == "FAIL" and fresh_v["result"] == "FAIL":
        persisting.append(item_id)
    elif baseline_v["result"] == "PASS" and fresh_v["result"] == "FAIL":
        regressions.append(item_id)  # triggers BLOCKED immediately
```

**Regression rule**: if `len(regressions) > 0`, set verdict to BLOCKED immediately.
Do not continue. Update session state. Print escalation message.

**No-progress rule**: if all FAIL items from baseline are still FAIL in fresh results
(zero resolved), AND this is iteration 2 or 3 in the session, set verdict to BLOCKED:
"No progress detected. The same failures persist after modification."

## Step 4: Output Freshness Check

All 5 expected PDFs must exist and have mtime newer than `design_spec.py` mtime.
A PDF older than the spec indicates the pipeline has not been run since the last
spec edit — this is a hallucinated-PASS guard.

```python
import os

spec_mtime = os.path.getmtime(
    '/home/tstapler/Documents/711-N60th-Plans/design_spec.py')

expected_pdfs = [
    '/home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_floor_plan_annotated.pdf',
    '/home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_elev_north.pdf',
    '/home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_elev_south.pdf',
    '/home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_elev_east.pdf',
    '/home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_elev_west.pdf',
]

for pdf in expected_pdfs:
    if not os.path.exists(pdf):
        raise AssertionError(f"Missing output: {pdf}")
    pdf_mtime = os.path.getmtime(pdf)
    if pdf_mtime < spec_mtime:
        raise AssertionError(
            f"Stale output: {pdf} predates design_spec.py. "
            "Run pixi run permit-docs to regenerate."
        )
```

If any PDF is missing or stale: verdict is BLOCKED.

## Step 5: Visual QA for Changed Drawings

For any drawing that shows a changed element (per the modify diff summary),
run a zone-level check to confirm the changed element is in the expected zone.

For the south-aisle / `bar_y_offset_mm` case:

1. Rasterize the new floor plan SVG:
   ```bash
   rsvg-convert -w 2000 \
     /home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_floor_plan_annotated.svg \
     -o /tmp/bim_floor_plan_qa.png
   ```

2. Extract SVG text labels:
   ```python
   import xml.etree.ElementTree as ET
   ns = '{http://www.w3.org/2000/svg}'
   tree = ET.parse(
       '/home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_floor_plan_annotated.svg')
   labels = [el.text.strip() for el in tree.iter(f'{ns}text')
             if el.text and el.text.strip()]
   ```

3. Run Layer 3 Pass 1 (element inventory) on the PNG + labels.
   Zone grid: A=west, G=east, 1=north, 5=south.
   - Confirm bar seating zone has moved south compared to baseline
   - Confirm island body is still in zones C3-E4

4. Any element result with `confidence: LOW` is added to the CANNOT_VERIFY list.
   The overall verdict is at most PASS_WITH_WARNINGS if LOW-confidence items exist.
