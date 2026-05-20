---
name: design-validate
description: "Use this skill to run the full 5-layer validation pipeline on the kitchen permit drawings. Combines programmatic compliance (Layer 1), SVG text extraction (Layer 2), Claude dual-pass visual layout review (Layer 3), small-element checklist (Layer 4), and human escalation flags (Layer 5). Produces a unified validation report. Use for pre-permit sign-off or after any design change. DO NOT use for a quick single-check — use design:review instead."
---

# design:validate — 5-Layer Kitchen Drawing Validation

## What This Skill Does

Runs the layered validation pipeline from `research/synthesis.md` against the current
`output/kitchen/` drawings. Produces a unified report at `/tmp/kitchen-validate/report.md`
with a pass/fail verdict per layer.

**Layers:**
- **L1** — Programmatic clearance compliance (ezdxf geometry, no vision)
- **L2** — SVG text extraction (dimension labels injected into all prompts)
- **L3** — Claude dual-pass visual review (PNG spatial + text block)
- **L4** — Small-element checklist (GFCI, hood, outlets)
- **L5** — Human escalation flags (any LOW confidence item)

---

## Prerequisites

- `output/kitchen/` drawings are current: `pixi run permit-docs` was run after last spec change
- `~/.claude/skills/pdf-proof/.venv` has: ezdxf, Pillow, PyMuPDF (fitz), cairosvg
- `~/.claude/skills/freecad-review/scripts/` has: `extract_clearances.py`, `check_compliance.py`

---

## Step 1: L1 — Programmatic Compliance

Same as `design:review` Layer 1. Run `extract_clearances.py` and `check_compliance.py`
against `output/kitchen/kitchen_floor_plan_annotated.svg`.

```bash
~/.claude/skills/pdf-proof/.venv/bin/python3 \
  ~/.claude/skills/freecad-review/scripts/extract_clearances.py \
  --svg /home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_floor_plan_annotated.svg \
  --output /tmp/kitchen-validate/clearances.json

~/.claude/skills/pdf-proof/.venv/bin/python3 \
  ~/.claude/skills/freecad-review/scripts/check_compliance.py \
  --clearances /tmp/kitchen-validate/clearances.json \
  --spec /home/tstapler/Documents/711-N60th-Plans/design_spec.py \
  --output /tmp/kitchen-validate/layer1.json
```

Record: `L1_pass` (bool), `L1_failures` (list of {rule, measured, required}).

---

## Step 2: L2 — SVG Text Extraction

Extract all dimension labels from the floor plan SVG before any Claude vision call.
This prevents measurement hallucination by injecting known labels into prompts.

```python
import xml.etree.ElementTree as ET, json, pathlib

svg_path = '/home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_floor_plan_annotated.svg'
tree = ET.parse(svg_path)
ns = {'svg': 'http://www.w3.org/2000/svg'}
labels = [el.text.strip() for el in tree.iter('{http://www.w3.org/2000/svg}text')
          if el.text and el.text.strip()]
pathlib.Path('/tmp/kitchen-validate/layer2_labels.json').write_text(json.dumps(labels, indent=2))
print(f"Extracted {len(labels)} text labels")
```

Inject these labels as a preamble for all Claude vision calls in L3/L4:
> "Labeled dimensions in drawing: {labels}. Do not estimate any unlabeled dimension."

---

## Step 3: L3 — Claude Dual-Pass Visual Review

### 3a: Rasterize floor plan to PNG

```bash
~/.claude/skills/pdf-proof/.venv/bin/python3 - <<'EOF'
import cairosvg, pathlib
cairosvg.svg2png(
    url='/home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_floor_plan_annotated.svg',
    write_to='/tmp/kitchen-validate/floor_plan_2000px.png',
    output_width=2000
)
print("Rasterized")
EOF
```

### 3b: Pass 1 — Element Inventory

Read `/tmp/kitchen-validate/floor_plan_2000px.png` visually. Use this prompt structure:

**System context:** "You are reviewing a kitchen floor plan for a permit submission.
The following dimension labels are present in the drawing: {L2 labels}.
Do not estimate any unlabeled dimension — if a measurement is not in the label list,
mark it as UNKNOWN."

**Pass 1 prompt:** "Using only the labeled dimensions listed and what you can see in
the image, list every named element and its approximate zone position (use: north-wall,
south-wall, island, east-wall, west-wall). Output as JSON with fields:
element, zone, labeled_dimension (or null), notes."

Save output as `/tmp/kitchen-validate/layer3_inventory.json`.

### 3c: Pass 2 — Comparison vs. design_spec.py

Load `design_spec.py` SPEC values. Compare each inventoried element against spec:

**Pass 2 prompt:** "Given this element inventory {layer3_inventory} and this design spec
{SPEC.to_json()}, identify every element whose drawn position or dimension CONFLICTS with
the spec. For each conflict: cite the element, the drawn value, the spec value, and your
confidence (HIGH/MEDIUM/LOW). Output as JSON with fields: element, drawn, spec, confidence."

Save as `/tmp/kitchen-validate/layer3_conflicts.json`.

---

## Step 4: L4 — Small-Element Checklist

For each of the following, crop a 400×400px region around its expected position from
`floor_plan_2000px.png` and ask a yes/no question:

| Element | Expected Location | Check Question |
|---------|-----------------|----------------|
| GFCI outlet | N wall near sink | "Is a GFCI outlet symbol visible near the sink?" |
| Range hood | Island center | "Is a hood/ventilation symbol visible above the island range?" |
| DW outlet | E wall near DW | "Is an outlet symbol visible adjacent to the dishwasher?" |

Use the L2 label list as context. Record: `{element: pass/fail/cannot_verify}`.

---

## Step 5: L5 — Human Escalation Flags

Aggregate all LOW confidence items from L3 Pass 2 and any `cannot_verify` from L4.
These must be manually reviewed before permit submission.

```python
import json, pathlib

conflicts = json.loads(pathlib.Path('/tmp/kitchen-validate/layer3_conflicts.json').read_text())
low_conf = [c for c in conflicts if c.get('confidence') == 'LOW']

escalations = [
    {"source": "L3", "item": c['element'], "reason": c.get('notes', '')}
    for c in low_conf
]

pathlib.Path('/tmp/kitchen-validate/layer5_escalations.json').write_text(
    json.dumps(escalations, indent=2)
)
```

---

## Step 6: Write Unified Report

```python
import json, pathlib, datetime

out = pathlib.Path('/tmp/kitchen-validate')
layer1 = json.loads((out / 'layer1.json').read_text()) if (out / 'layer1.json').exists() else {}
labels = json.loads((out / 'layer2_labels.json').read_text()) if (out / 'layer2_labels.json').exists() else []
conflicts = json.loads((out / 'layer3_conflicts.json').read_text()) if (out / 'layer3_conflicts.json').exists() else []
escalations = json.loads((out / 'layer5_escalations.json').read_text()) if (out / 'layer5_escalations.json').exists() else []

l1_pass = layer1.get('all_pass', False)
l3_high_conf_conflicts = [c for c in conflicts if c.get('confidence') == 'HIGH']

verdict = 'PASS' if (l1_pass and not l3_high_conf_conflicts and not escalations) else \
          'FIX-REQUIRED' if (not l1_pass or l3_high_conf_conflicts) else 'REVIEW-NEEDED'

report = f"""# Kitchen Drawing Validation Report
Generated: {datetime.datetime.now().isoformat()}

## Verdict: {verdict}

## L1 Programmatic Compliance: {'PASS' if l1_pass else 'FAIL'}
{json.dumps(layer1.get('failures', []), indent=2)}

## L2 Dimension Labels Extracted: {len(labels)} labels

## L3 Visual Conflicts (HIGH confidence):
{json.dumps(l3_high_conf_conflicts, indent=2)}

## L4 Small-Element Checklist:
(see /tmp/kitchen-validate/layer4_checklist.json)

## L5 Human Escalation Required ({len(escalations)} items):
{json.dumps(escalations, indent=2)}
"""

(out / 'report.md').write_text(report)
print(report)
```

---

## Related Skills

- `design:review` — faster single-session review (Layers 0-3 only, no L4/L5)
- `design:loop` — iterative fix loop using design:review as the gate
- `design:modify` — apply a single spec change after a FAIL is identified
