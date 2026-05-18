---
name: drawing-to-spec
description: "Use this skill when Tyler asks to extract dimensions from a CD set drawing, read a floor plan or elevation back into design_spec.py, verify the spec matches the architect's drawings, or populate spec fields from a PDF/SVG/PNG. Triggers on: 'read the drawing', 'extract from page N', 'what does the CD set say about X', 'update spec from the drawing', 'verify spec against CD'. Works on PDF pages (260417-CD_SET_OWNER_REVIEW.pdf), SVG output from the BIM pipeline, or PNG images. DO NOT invoke for compliance review of BIM output (use freecad-review) or to make design changes (use design-modify)."
---

# drawing-to-spec — Architectural Drawing → design_spec.py Extraction

## What This Skill Does

Reads an architectural drawing (CD set PDF page, BIM SVG output, or PNG) and extracts
labeled dimension values to populate or verify `design_spec.py` fields.

This is the REVERSE of the normal pipeline direction (FreeCAD → drawings).
Use it to:
1. **Populate spec fields** from CD set drawings when starting a new iteration
2. **Verify spec accuracy** — confirm design_spec.py matches what the architect drew
3. **Detect drift** — find fields where the BIM spec has diverged from the stamped CD set
4. **Resolve ambiguity** — when a dimension is unknown, read it from the authoritative source

The skill never estimates values. Every proposed field change must be backed by a visible
dimension label in the drawing. Fields without visible labels are output as CANNOT_VERIFY.

**Write protection**: The skill NEVER writes to `design_spec.py` without explicit user
confirmation. After showing the extraction report, it asks: "Apply HIGH-confidence
changes? [Y/n]"

---

## Critical: How Claude Reads Drawing Files

**PDF pages → rasterize first.** Claude cannot read PDF geometry. Always extract the
page as PNG via `rasterize_pdf_page.py` before any visual review.

**SVG files → extract text labels programmatically, then rasterize for geometry.**
Claude reads `<text>` nodes as strings but CANNOT interpret SVG spatial layout.
The SVG label extraction is authoritative for text content; PNG is required for
spatial/positional reading.

**PNG files → visual analysis only.** Claude can read layout and position from a PNG
but may misread small or rotated dimension text. Always inject programmatically
extracted labels when an SVG source is available.

**Rule**: never trust Claude's visual reading of a dimension that can be extracted from
SVG text nodes or PDF text layer. Use programmatic extraction as the authoritative source
and visual review as the fallback for unlabeled or LOW-confidence fields only.

---

## CD Set Page Reference (711 N60th Plans)

CD set path: `/home/tstapler/Documents/711-N60th-Plans/260417-CD_SET_OWNER_REVIEW.pdf`

| Page | Drawing | Scale | pts/ft | Best source for |
|------|---------|-------|--------|-----------------|
| 4 | Level 1 Floor Plan | 1/4"=1'-0" | 18 | `kit_ew_mm`, `kit_ns_mm`, `ext_thk_mm`, `int_thk_mm`, `bar_y_offset_mm` |
| 8 | Kitchen Interior Elevations | 1/4"=1'-0" | 18 | `ctr_h_mm`, `ucab_bot_mm`, `ucab_h_mm`, `hood_aff_mm`, `sink_w_mm` |
| 9 | Kitchen Casework Elevations | 1/2"=1'-0" | 36 | `island_ew_mm`, `island_ns_mm`, `bar_ns_mm`, `fridge_w_mm`, `range_w_mm`, `dw_w_mm` |
| 10 | Kitchen Casework Elevations | 1/2"=1'-0" | 36 | Cabinet sizes, appliance widths, countertop overhangs |

Scale conversion: `real_inches = pixel_distance / (pts_per_ft / 12.0)` at native PDF resolution.
At 2000px output width, use the pixel-to-inch ratio reported by `rasterize_pdf_page.py --info`.

---

## Field → Drawing Source Map

| design_spec.py field | Source page | Confidence (if labeled) | Notes |
|---|---|---|---|
| `kit_ew_mm` | 4 | HIGH | Interior east-west dimension string |
| `kit_ns_mm` | 4 | HIGH | Interior north-south dimension string |
| `ext_thk_mm` | 4 | MEDIUM | Requires scale rule — wall thickness usually unlabeled |
| `int_thk_mm` | 4 | MEDIUM | Interior partition thickness — usually unlabeled |
| `bar_y_offset_mm` | 4 | MEDIUM | Bar distance from south wall — needs careful spatial reading |
| `island_ew_mm` | 9/10 | HIGH | "5'-6"" label at island north edge |
| `island_ns_mm` | 9/10 | HIGH | Island body depth label |
| `bar_ns_mm` | 9/10 | HIGH | "1'-3"" bar overhang label at south face |
| `fridge_w_mm` | 9/10 | HIGH | "4'-0"" label at refrigerator opening |
| `range_w_mm` | 9/10 | HIGH | Range width label |
| `dw_w_mm` | 9/10 | HIGH | Dishwasher width label |
| `sink_w_mm` | 8/9 | HIGH | Sink base cabinet width label |
| `ctr_h_mm` | 8 | HIGH | Counter height AFF label |
| `ucab_bot_mm` | 8 | HIGH | Upper cabinet bottom AFF label |
| `ucab_h_mm` | 8 | HIGH | Upper cabinet height label |
| `hood_aff_mm` | 8 | HIGH | Hood bottom AFF label |

Fields not in this table (color values, owner requirements, compliance targets,
cd_page_references) are NOT extractable from drawings — skip them.

---

## 5-Step Workflow

### Step 1: Identify Drawing Source

Accept one of:
- `--pdf page N` — extract page N from the CD set
- `--svg /path/to/file.svg` — read BIM SVG output
- `--png /path/to/file.png` — read a rasterized drawing

**For PDF input:**

```bash
VENV=~/.claude/skills/pdf-proof/.venv/bin/python3
CD_SET=/home/tstapler/Documents/711-N60th-Plans/260417-CD_SET_OWNER_REVIEW.pdf
PAGE=9        # set to target page number
OUT_PNG=/tmp/cd_page${PAGE}.png

# Inspect scale metadata first
$VENV ~/.claude/skills/freecad-review/scripts/rasterize_pdf_page.py \
  --pdf "$CD_SET" --page "$PAGE" --out /dev/null --info

# Extract page at 2000px width
$VENV ~/.claude/skills/freecad-review/scripts/rasterize_pdf_page.py \
  --pdf "$CD_SET" --page "$PAGE" --out "$OUT_PNG" --width 2000
```

The `--info` flag prints:
```
Page 9: 1224×792 pts | scale: 1/2"=1'-0" | pts_per_ft: 36 | px_per_inch (at 2000px): 18.5
```

Record `px_per_inch` for use in Step 2 geometry extraction.

**For SVG input:**

```bash
SVG=/home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_floor_plan_annotated.svg
OUT_PNG=/tmp/bim_floor_plan.png

# Rasterize for visual review
rsvg-convert -w 2000 "$SVG" -o "$OUT_PNG"
```

If `rsvg-convert` is missing: `brew install librsvg`

**For PNG input:** use as-is; record the known scale if available.

---

### Step 2: Extract Text Labels and Geometry

Run both extractors and merge results. The programmatic extractor is authoritative for
any field it resolves; visual review (Step 3) only fills gaps.

#### 2a: SVG text label extraction (SVG source only)

```python
import xml.etree.ElementTree as ET

def extract_svg_labels(svg_path: str) -> list[str]:
    """Return all non-empty text strings from an SVG file."""
    ns = '{http://www.w3.org/2000/svg}'
    tree = ET.parse(svg_path)
    labels = []
    for el in tree.iter(f'{ns}text'):
        text = (el.text or '').strip()
        if text:
            labels.append(text)
        # Also collect tspan children
        for tspan in el.iter(f'{ns}tspan'):
            t = (tspan.text or '').strip()
            if t and t not in labels:
                labels.append(t)
    return labels

labels = extract_svg_labels('/path/to/drawing.svg')
print('\n'.join(labels))
```

Save output to `/tmp/svg_labels.txt` for injection into Step 3 prompt.

#### 2b: Programmatic clearances/geometry extraction (SVG source only)

```bash
VENV=~/.claude/skills/pdf-proof/.venv/bin/python3

# Appliance positions from SVG geometry (authoritative)
$VENV ~/.claude/skills/freecad-review/scripts/extract_clearances.py \
  --svg /path/to/drawing.svg \
  --output /tmp/clearances.json

# DXF entity inventory + text labels (if DXF available)
$VENV ~/.claude/skills/freecad-review/scripts/check_compliance.py \
  --svg /path/to/drawing.svg \
  --output /tmp/compliance.json
```

#### 2c: Spec field extraction script (PDF/PNG source)

```bash
# extract_spec_from_drawing.py returns proposed spec fields with confidence levels
$VENV ~/.claude/skills/drawing-to-spec/scripts/extract_spec_from_drawing.py \
  --png "$OUT_PNG" \
  --page "$PAGE" \
  --px-per-inch 18.5 \
  --output /tmp/proposed_fields.json
```

Output schema for `proposed_fields.json`:

```json
{
  "source": "260417-CD_SET_OWNER_REVIEW.pdf page 9",
  "scale": "1/2\"=1'-0\"",
  "px_per_inch": 18.5,
  "fields": {
    "island_ew_mm": {
      "value_mm": 1676.4,
      "confidence": "HIGH",
      "source": "programmatic",
      "evidence": "Label \"5'-6\"\" at island north edge — 66.0\" × 25.4 = 1676.4 mm"
    },
    "bar_ns_mm": {
      "value_mm": 381.0,
      "confidence": "HIGH",
      "source": "programmatic",
      "evidence": "Label \"1'-3\"\" at bar south face — 15.0\" × 25.4 = 381.0 mm"
    },
    "bar_y_offset_mm": {
      "value_mm": null,
      "confidence": "CANNOT_VERIFY",
      "source": "programmatic",
      "evidence": "Not labeled on page 9 — requires floor plan (page 4)"
    }
  }
}
```

If `extract_spec_from_drawing.py` does not yet exist, build the proposed_fields dict
manually from the SVG label list and clearances JSON in Step 2a/2b, then save it.

---

### Step 3: Claude Visual Review Pass (gap-filling only)

Run this pass ONLY for fields that are `null` or `LOW` confidence after Step 2.
Do NOT re-estimate fields already resolved with HIGH confidence.

#### 3a: Add calibrated grid overlay

```bash
VENV=~/.claude/skills/pdf-proof/.venv/bin/python3

$VENV ~/.claude/skills/freecad-review/scripts/add_grid.py \
  --svg /path/to/source.svg \
  --png "$OUT_PNG" \
  --out /tmp/drawing_grid.png
```

For PDF-sourced PNGs (no SVG available), the grid anchor must be estimated visually.
Pass `--no-svg` flag and provide approximate interior corner pixel coordinates:

```bash
$VENV ~/.claude/skills/freecad-review/scripts/add_grid.py \
  --no-svg \
  --kitchen-x0 420 --kitchen-y0 180 --kitchen-x1 1820 --kitchen-y1 1540 \
  --png "$OUT_PNG" \
  --out /tmp/drawing_grid.png
```

#### 3b: Structured visual extraction prompt

Send `/tmp/drawing_grid.png` as a PNG attachment with this prompt. Replace
`{labels_list}` with the output from Step 2a. Replace `{unresolved_fields}` with only
those fields that are null or LOW confidence.

```
System:
You are reviewing an architectural drawing for the 711 N60th St kitchen remodel.
All programmatically extracted dimension labels are provided below.

RULES (strictly enforced):
1. Only report a value if it is explicitly labeled in the drawing.
2. If a dimension is not labeled, output CANNOT_VERIFY — never estimate.
3. Do not re-report fields already listed in ALREADY_RESOLVED.
4. For each field you do report, cite the exact label text as evidence.
5. Convert all values to millimeters: value_mm = inches × 25.4

User:
[PNG image: /tmp/drawing_grid.png]

DRAWING SOURCE: {source_description}
SCALE: {scale_string} ({px_per_inch:.1f} px/inch at 2000px width)

LABELED DIMENSIONS IN DRAWING (programmatic extraction):
{labels_list}

ALREADY_RESOLVED (do not re-examine):
{high_confidence_fields_list}

FIELDS TO RESOLVE (examine only these):
{unresolved_fields_list}

For each field in FIELDS TO RESOLVE, output JSON:
{
  "field_name": {
    "value_mm": <float or null>,
    "confidence": "HIGH" | "MEDIUM" | "LOW" | "CANNOT_VERIFY",
    "evidence": "<exact label text and location>" or ""
  }
}

Output CANNOT_VERIFY if you cannot find an explicit label.
```

#### 3c: Merge visual results into proposed_fields

```python
import json

proposed = json.load(open('/tmp/proposed_fields.json'))
visual = json.loads(claude_response_text)  # parsed from Step 3b response

for field_name, result in visual.items():
    existing = proposed['fields'].get(field_name, {})
    existing_confidence = existing.get('confidence', 'CANNOT_VERIFY')

    # Only upgrade if visual review found evidence and existing was unresolved
    if (existing_confidence in ('CANNOT_VERIFY', 'LOW', None)
            and result.get('value_mm') is not None
            and result.get('evidence', '')):
        proposed['fields'][field_name] = {
            'value_mm': result['value_mm'],
            'confidence': result['confidence'],
            'source': 'visual_review',
            'evidence': result['evidence'],
        }

with open('/tmp/proposed_fields.json', 'w') as f:
    json.dump(proposed, f, indent=2)
```

---

### Step 4: Constraint Simulation

Run the constraint simulator against the FULL proposed spec BEFORE presenting the diff.
Any proposed change that introduces a new FAIL is demoted to MEDIUM confidence and
flagged for human review — it is not auto-writable.

```bash
VENV=~/.claude/skills/pdf-proof/.venv/bin/python3

# Write a temporary spec with proposed HIGH-confidence values substituted
python3 -c "
import json, sys, pathlib, shutil, time

proposed = json.load(open('/tmp/proposed_fields.json'))
spec_path = pathlib.Path('/home/tstapler/Documents/711-N60th-Plans/design_spec.py')
content = spec_path.read_text()

# Apply only HIGH-confidence fields that differ from current spec
from design_spec import SPEC
changes = []
for field_name, info in proposed['fields'].items():
    if info['confidence'] != 'HIGH' or info['value_mm'] is None:
        continue
    current_val = getattr(SPEC, field_name, None)
    if current_val is None:
        continue
    proposed_val = info['value_mm']
    if abs(proposed_val - current_val) < 0.01:
        continue  # no change
    changes.append((field_name, current_val, proposed_val))

# Write temp spec for simulation
tmp = pathlib.Path('/tmp/design_spec_sim.py')
sim_content = content
for field_name, current_val, proposed_val in changes:
    sim_content = sim_content.replace(
        f'default={current_val}',
        f'default={proposed_val}',
        1  # replace first occurrence only
    )
tmp.write_text(sim_content)
print(json.dumps(changes))
" > /tmp/sim_changes.json

# Run constraint simulator against temp spec
$VENV ~/.claude/skills/design-modify/scripts/constraint_simulator.py \
  --spec /tmp/design_spec_sim.py \
  --output /tmp/sim_results.json 2>/dev/null \
  || echo "constraint_simulator.py not yet callable with --spec flag; run inline simulation"
```

If `constraint_simulator.py` does not support `--spec`, run the inline simulation
from `design-modify` SKILL.md Step 1b–1d directly in Claude's reasoning, substituting
the proposed HIGH-confidence values.

**Demotion rule**: if the simulator reports a new FAIL for aisle clearances that was
previously PASS, demote the field(s) that caused the failure from HIGH to MEDIUM
confidence and add them to the "Requires Human Review" section of the report.

Simulation table format (print to conversation before presenting the diff):

```
Constraint Simulation — proposed changes from {source}

Aisle         | Current  | Proposed | Required | Status
--------------|----------|----------|----------|--------
South aisle   | 30.0"    | {s}"     | ≥ 42"    | {PASS/FAIL ⚠}
North aisle   | 55.0"    | {n}"     | ≥ 42"    | {PASS/FAIL}
East aisle    | 46.5"    | {e}"     | ≥ 42"    | {PASS/FAIL}
West aisle    | 46.5"    | {w}"     | ≥ 42"    | {PASS/FAIL}
```

---

### Step 5: Present Diff and Write (human-gated)

#### 5a: Build and print the extraction report

Print the full report to the conversation (format in Output Report section below).

Separate proposed fields into two buckets:
- **AUTO bucket** — `confidence == HIGH` AND no constraint simulation failure introduced
- **REVIEW bucket** — `confidence in (MEDIUM, LOW, CANNOT_VERIFY)` OR constraint
  simulation demoted the field

#### 5b: Print proposed diff to design_spec.py

For each field in the AUTO bucket that differs from current spec value:

```python
from design_spec import SPEC
import json

proposed = json.load(open('/tmp/proposed_fields.json'))

for field_name, info in proposed['fields'].items():
    if info['confidence'] != 'HIGH' or info['value_mm'] is None:
        continue
    current_val = getattr(SPEC, field_name, None)
    if current_val is None:
        continue
    proposed_val = info['value_mm']
    if abs(proposed_val - current_val) < 0.01:
        continue
    print(f"- {field_name}: float = field(default={current_val}, ...)")
    print(f"+ {field_name}: float = field(default={proposed_val}, ...)")
    print()
```

If all proposed values match current spec: print "No changes — design_spec.py matches drawing."

#### 5c: Prompt for confirmation

```
Apply {N} HIGH-confidence change(s) to design_spec.py? [Y/n]
```

**WAIT for explicit "Y" or "yes" response before proceeding.**

Do not auto-apply. Do not proceed on ambiguous responses like "looks good" or "sure".
Require an explicit affirmative.

#### 5d: Apply changes using safe spec editor protocol

On confirmed "Y", apply each change using the safe spec editor from `design-modify`
SKILL.md Step 2 (backup → temp file → syntax check → import check → field assertion →
atomic copy). Apply changes one field at a time, running all safety checks for each.

```python
import shutil, time, pathlib, ast, subprocess

SPEC_PATH = pathlib.Path('/home/tstapler/Documents/711-N60th-Plans/design_spec.py')
LOOP_DIR  = pathlib.Path('/home/tstapler/Documents/711-N60th-Plans/.design-loop')
LOOP_DIR.mkdir(parents=True, exist_ok=True)

ts = int(time.time())
backup_path = LOOP_DIR / f'design_spec_backup_{ts}.py'
shutil.copy(SPEC_PATH, backup_path)
original_content = SPEC_PATH.read_text()

for field_name, info in changes_to_apply.items():
    current_val = info['current_value_mm']
    proposed_val = info['value_mm']

    new_content = original_content.replace(
        f'default={current_val}',
        f'default={proposed_val}',
        1
    )

    # Syntax check
    tmp_path = LOOP_DIR / f'design_spec_proposed_{ts}.py'
    tmp_path.write_text(new_content)

    try:
        ast.parse(new_content)
    except SyntaxError as e:
        print(f"SYNTAX ERROR in proposed change for {field_name}: {e}")
        print("Rolling back.")
        SPEC_PATH.write_text(original_content)
        break

    # Import check
    result = subprocess.run(
        ['python3', '-c',
         f'import sys; sys.path.insert(0, "{LOOP_DIR}"); '
         f'import design_spec_proposed_{ts} as ds; print(ds.SPEC.{field_name})'],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"IMPORT ERROR for {field_name}: {result.stderr}")
        print("Rolling back.")
        SPEC_PATH.write_text(original_content)
        break

    # Apply
    shutil.copy(tmp_path, SPEC_PATH)
    original_content = new_content  # chain for next field
    print(f"Applied: {field_name} = {proposed_val} mm")
```

#### 5e: On rejection — save proposed changes for later

If user responds "n" or "no":

```python
import json, pathlib

out = pathlib.Path(
    '/home/tstapler/Documents/711-N60th-Plans/.design-loop/proposed_spec_changes.json')
json.dump(
    json.load(open('/tmp/proposed_fields.json')),
    open(out, 'w'), indent=2
)
print(f"Proposed changes saved to {out}")
print("Re-run drawing-to-spec and answer Y to apply, or use design-modify for individual fields.")
```

---

## Output Report Format

Print this report to the conversation before presenting the confirmation prompt.

```markdown
# Drawing → Spec Extraction Report
Source: 260417-CD_SET_OWNER_REVIEW.pdf page 9
Scale: 1/2"=1'-0" (36 pts/ft, 18.5 px/inch at 2000px)
Date: 2026-05-10
design_spec.py: /home/tstapler/Documents/711-N60th-Plans/design_spec.py

## Extracted Fields
| Field | Current (mm) | Current (in) | Proposed (mm) | Proposed (in) | Confidence | Evidence |
|---|---|---|---|---|---|---|
| island_ew_mm | 1676.4 | 66.0" | 1676.4 | 66.0" | HIGH ✅ | Label "5'-6"" at island north edge |
| bar_ns_mm | 381.0 | 15.0" | 381.0 | 15.0" | HIGH ✅ | Label "1'-3"" at bar south face |
| fridge_w_mm | 1219.2 | 48.0" | 1219.2 | 48.0" | HIGH ✅ | Label "4'-0"" at refrigerator |
| range_w_mm | 1219.2 | 48.0" | 1219.2 | 48.0" | HIGH ✅ | Label "4'-0"" at range/island |
| dw_w_mm | 609.6 | 24.0" | 609.6 | 24.0" | HIGH ✅ | Label "2'-0"" at dishwasher |

## Changes Detected
No changes — current design_spec.py matches drawing.
(OR: N fields differ — see diff below)

## Fields Requiring Human Review (MEDIUM/LOW/CANNOT_VERIFY)
- bar_y_offset_mm: CANNOT_VERIFY — not labeled on page 9; requires floor plan (page 4)
- ext_thk_mm: MEDIUM — wall thickness visible but not dimensioned; requires scale rule

## Constraint Simulation
Aisle         | Current  | Proposed | Required | Status
South aisle   | 30.0"    | 30.0"    | ≥ 42"    | ⚠ FAIL (existing, not introduced by this extraction)
North aisle   | 55.0"    | 55.0"    | ≥ 42"    | ✅ PASS
East aisle    | 46.5"    | 46.5"    | ≥ 42"    | ✅ PASS
West aisle    | 46.5"    | 46.5"    | ≥ 42"    | ✅ PASS

Note: Existing FAIL items are not caused by this extraction. Use design-modify to resolve.

## Proposed diff to design_spec.py
No changes — current spec matches drawing.
(OR: show field-by-field diff for changed fields)

---
Apply 0 HIGH-confidence changes to design_spec.py? [Y/n]
```

---

## Idempotency

The skill is designed to be re-runnable. Running it twice on the same drawing:
1. Produces the same `proposed_fields.json` (deterministic extraction)
2. Reports "No changes" if spec already matches (second run is a no-op)
3. Does not create duplicate backups if no write occurs

The only side effect is `/tmp/` files (overwritten each run) and
`.design-loop/proposed_spec_changes.json` (overwritten on rejection).

---

## mm ↔ inch Conversion Reference

All spec fields use millimeters. All CD set drawings use feet-and-inches.
Always show the conversion explicitly in evidence strings.

```python
# Convert architect's label to mm
def label_to_mm(feet: int, inches: float) -> float:
    """Convert feet + inches label to millimeters."""
    return (feet * 12 + inches) * 25.4

# Examples:
label_to_mm(5, 6)   # "5'-6"" → 1676.4 mm
label_to_mm(1, 3)   # "1'-3"" → 381.0 mm
label_to_mm(4, 0)   # "4'-0"" → 1219.2 mm
label_to_mm(2, 0)   # "2'-0"" → 609.6 mm
label_to_mm(3, 0)   # "3'-0"" → 914.4 mm
label_to_mm(0, 42)  # "42""   → 1066.8 mm
label_to_mm(6, 6)   # "6'-6"" → 1981.2 mm
label_to_mm(13, 3)  # "13'-3"" → 4038.0 mm  (kit_ew_mm)
label_to_mm(10, 5)  # "10'-5"" → 3175.0 mm  (kit_ns_mm)

# Reverse: mm to feet-and-inches for display
def mm_to_ft_in(mm: float) -> str:
    total_in = mm / 25.4
    feet = int(total_in // 12)
    inches = total_in % 12
    return f"{feet}'-{inches:.3g}\""
```

---

## Confidence Level Definitions

| Confidence | Meaning | Can auto-apply? |
|---|---|---|
| HIGH | Explicit dimension label visible in drawing; converted cleanly | Yes, after user confirms |
| MEDIUM | Dimension inferred from scale rule or spatial measurement without explicit label | No — human review required |
| LOW | Partially visible or ambiguous label; Claude's reading is uncertain | No — human review required |
| CANNOT_VERIFY | Dimension not present in this drawing; wrong page or not labeled | No — field skipped |

**HIGH requires both**: an exact label (e.g., "5'-6"") AND a clean conversion to mm
(value × 25.4 must match spec field units exactly, no rounding beyond 0.01 mm).

---

## Dependencies

### Python venv (shared with freecad-review and pdf-proof)

```bash
VENV=~/.claude/skills/pdf-proof/.venv/bin/python3

# Verify deps
$VENV -c "import fitz, PIL, ezdxf, xml.etree.ElementTree; print('All deps OK')"
```

Already installed (verified 2026-05-10):
- `PyMuPDF (fitz)` — PDF rasterization and page extraction
- `Pillow` — image operations for grid overlay and cropping
- `ezdxf` — DXF geometry extraction (via freecad-review scripts)
- `xml.etree.ElementTree` — SVG label extraction (standard library)

If any missing:
```bash
~/.claude/skills/pdf-proof/.venv/bin/pip install PyMuPDF Pillow ezdxf
```

### System tools

```bash
# SVG rasterization (required for BIM SVG inputs)
which rsvg-convert || brew install librsvg

# Quick check
rsvg-convert --version
~/.claude/skills/pdf-proof/.venv/bin/python3 -c "import fitz, PIL; print('OK')"
```

---

## Scripts Reference

All scripts use: `~/.claude/skills/pdf-proof/.venv/bin/python3`

### Reused from freecad-review (`~/.claude/skills/freecad-review/scripts/`)

**`rasterize_pdf_page.py`** — Extract a CD set page as PNG with scale metadata.
See freecad-review SKILL.md Scripts Reference for full usage. Key flags:
- `--info` — print page dimensions and scale without writing output
- `--width 2000` — output width in pixels (maintains aspect ratio)
- `--crop x0 y0 x1 y1` — crop to a sub-region in PDF points

**`extract_clearances.py`** — Read SVG appliance geometry → clearance measurements.
Returns appliance bounding boxes in real inches; used to verify geometry matches labels.

**`check_compliance.py`** — Extract SVG `<text>` labels and DXF entity inventory.
Use `--svg` flag to get the label list for injection into Claude prompts.

**`add_grid.py`** — Add calibrated 2-ft grid overlay to a PNG.
Grid cells A1–G5 provide spatial reference for visual extraction prompts.

### New scripts (`~/.claude/skills/drawing-to-spec/scripts/`)

**`extract_spec_from_drawing.py`** — Primary extraction script for PDF/PNG inputs.
Reads a rasterized drawing PNG and returns proposed spec fields with confidence levels.

```bash
~/.claude/skills/pdf-proof/.venv/bin/python3 \
  ~/.claude/skills/drawing-to-spec/scripts/extract_spec_from_drawing.py \
  --png /tmp/cd_page9.png \
  --page 9 \
  --px-per-inch 18.5 \
  --output /tmp/proposed_fields.json
```

If this script does not yet exist, Claude constructs `proposed_fields.json` manually
from the SVG label list (Step 2a) and clearances JSON (Step 2b), then saves the file
in the schema shown in Step 2c. The script is built incrementally — create it when the
manual approach proves repetitive across multiple extraction sessions.

---

## Scope Boundaries

This skill handles:
- Extracting spec field values from CD set drawings or BIM SVGs
- Verifying that `design_spec.py` matches the architect's stamped drawings
- Proposing and (with confirmation) applying HIGH-confidence field updates

This skill does NOT:
- Make design decisions or suggest alternative values
- Run the full BIM pipeline (`pixi run permit-docs`) — that is `design-modify`'s job
- Perform IRC compliance review — use `freecad-review` for that
- Commit to git — Tyler reviews and commits manually
- Override MEDIUM/LOW fields without explicit human confirmation

---

## Verified Results (2026-05-11)

Running `extract_spec_from_drawing.py` against the 260417-CD_SET_OWNER_REVIEW.pdf:

| Page | Fields extracted | Fields CHANGED vs spec | Fields CONFIRMED |
|------|-----------------|------------------------|------------------|
| 8 (elevations, 1/4") | 4 | 3 | 1 |
| 9 (casework, 1/2") | 0 | 0 | 0 |
| 4 (floor plan, 1/4") | 0 | 0 | 0 |

**Page 8 discrepancies** (architect drew vs current spec):
| Field | CD Set Value | Spec Value | Delta |
|-------|-------------|------------|-------|
| `ucab_bot_mm` | 4'-4 3/4" = 1339.85mm | 1371.6mm (4'-6") | -31.75mm (-1.25") |
| `ucab_h_mm` | 2'-6 1/2" = 774.7mm | 762.0mm (2'-6") | +12.7mm (+0.5") |
| `hood_aff_mm` | 7'-0" = 2133.6mm | 1981.2mm (6'-6") | +152.4mm (+6") |
| `ctr_h_mm` | 3'-0" = 914.4mm | 914.4mm | ✅ CONFIRMED |

**Why page 9/10 yields 0 fields**: The CD casework drawings use graphical widths (drawn to
scale) rather than explicit dimension callout strings for appliances. `extract_spec_from_drawing.py`
relies on text proximity to element labels — since appliance widths are not labeled with
text strings, Step 3 (Claude visual review) is required to extract these from the rasterized PNG.

**Why page 4 yields 0 fields**: Overall kitchen dimension strings appear to be in a PDF
annotation layer or embedded in vector graphics rather than as extractable text objects.
Step 3 (Claude visual review) required.

---

## Project File Paths

| File | Path |
|---|---|
| CD set PDF | `/home/tstapler/Documents/711-N60th-Plans/260417-CD_SET_OWNER_REVIEW.pdf` |
| design_spec.py | `/home/tstapler/Documents/711-N60th-Plans/design_spec.py` |
| BIM floor plan SVG | `/home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_floor_plan_annotated.svg` |
| BIM elevation SVGs | `/home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_elev_*.svg` |
| Output dir | `/home/tstapler/Documents/711-N60th-Plans/output/kitchen/` |
| Script dir (new) | `~/.claude/skills/drawing-to-spec/scripts/` |
| Script dir (reuse) | `~/.claude/skills/freecad-review/scripts/` |
| Session state dir | `/home/tstapler/Documents/711-N60th-Plans/.design-loop/` |
| Proposed changes (rejected) | `/home/tstapler/Documents/711-N60th-Plans/.design-loop/proposed_spec_changes.json` |

---

## Related Skills

- `freecad-review` — validates BIM SVG/DXF output against IRC compliance; provides the
  scripts reused in Steps 1–2 of this skill
- `design-modify` — applies deliberate design changes to `design_spec.py` with full
  constraint simulation and pipeline re-run; use after `drawing-to-spec` to resolve FAILs
- `design-loop` — orchestrates the iterative review → modify → QA cycle
- `pdf-proof` — visual proof and annotation of specific values in PDFs
