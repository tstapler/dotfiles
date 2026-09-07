# Step 2: CD Set Comparison

## Scale normalization guard

Before any pixel comparison, read `SPEC.cd_page_references` and check `scale_factor`
for the target page. If `scale_factor != 1.0`, skip pixel-diff and use element-zone
comparison only (pixel-diff on mismatched scales produces misleading results).

CD set path: `SPEC.cd_page_references['cd_set_path']`
(= `/home/tstapler/Documents/711-N60th-Plans/260417-CD_SET_OWNER_REVIEW.pdf`)

## 2a: Floor plan comparison (CD page 4 vs BIM floor plan SVG)

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

## 2b: Casework elevation comparison (CD pages 9 and 10 vs BIM elevation SVGs)

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

## 2c: Run Layer 3 dual-pass visual inventory

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

## 2d: Write CD comparison results to review JSON

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
