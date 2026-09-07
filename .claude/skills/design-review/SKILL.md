---
name: design-review
description: "Use this skill when Tyler asks to review the kitchen design, run compliance checks, compare the BIM drawings to the CD set, or verify owner requirements. Produces a structured Markdown compliance report with PASS/FAIL/CANNOT_VERIFY per item. Standalone — does not modify anything. DO NOT invoke for a single spec edit (use design:modify) or the full iterative loop (use design:loop)."
---

# design:review — Kitchen Design Compliance & Intent Review

## What This Skill Does

Reads `design_spec.py` and the current output drawings, then produces a structured
Markdown compliance report covering:

0. **Layer 0 (MCP)** — Direct FreeCAD model snapshot via `mcp__freecad-mcp__*` (fast, preferred)
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
- FreeCAD MCP server connected (optional but preferred — enables Step 0a)

---

## Step 0a: FreeCAD MCP Direct Model Snapshot (preferred, optional)

If the `mcp__freecad-mcp__*` tools are available, use them to get ground-truth model
state directly instead of inferring from SVG/DXF exports. This is faster and eliminates
export-lag false positives.

**Load schema first:**
```
ToolSearch: select:mcp__freecad-mcp__open_document,mcp__freecad-mcp__list_objects,mcp__freecad-mcp__inspect_object,mcp__freecad-mcp__get_screenshot
```

**Then run:**

1. Open the model:
   `mcp__freecad-mcp__open_document(path="/home/tstapler/Documents/711-N60th-Plans/711N60th_Sections.FCStd")`

2. List all kitchen objects to verify layer membership:
   `mcp__freecad-mcp__list_objects(document="711N60th_Sections")`
   Look for: `Proposed_Remodel` group contains island, range, sink, fridge, DW, beam.

3. Spot-check key dimensions by inspecting critical objects:
   `mcp__freecad-mcp__inspect_object(document="711N60th_Sections", object_name="<island_label>")`
   Verify bounding box matches `design_spec.py` SPEC values (ISLAND_EW=1676.4mm, ISLAND_NS=635mm).

4. Capture a visual confirmation screenshot:
   `mcp__freecad-mcp__get_screenshot(document="711N60th_Sections")`
   Note any obvious geometry errors before running the full SVG pipeline.

Record findings as `layer0_mcp` in the review JSON. If MCP is unavailable, skip and
proceed to Step 0b (iteration tracking) — Layer 1 SVG/DXF checks are still authoritative.

---

## Step 0c: Determine Iteration Number

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

Layer 1 is the sole source of truth for measured clearances — no Claude vision is
used for measurements, only programmatic geometry extraction. Clear cached results,
run `extract_clearances.py` and `check_compliance.py`, then parse against
`SPEC.compliance_targets` using the AISLE_MAP (south/north/east/west aisle rules).
Any `CANNOT_VERIFY` item from the scripts (e.g. GFCI) carries through unchanged —
it is never upgraded to PASS without fresh script evidence.

Full commands and the AISLE_MAP parsing code:
[references/layer1-compliance.md](references/layer1-compliance.md)

---

## Step 2: CD Set Comparison

Compare the BIM drawings against the permit CD set (`SPEC.cd_page_references`).
Check `scale_factor` first — mismatched-scale pages (e.g. floor plan, page 4 at
1/4" vs. BIM's 1/2") skip pixel-diff and use element-zone comparison only;
matched-scale pages (elevations, pages 9–10) get a pixel diff. Both paths feed a
Layer 3 dual-pass visual inventory (element inventory, then change detection).

Full rasterize commands, pixel-diff code, and inventory prompts:
[references/cd-comparison.md](references/cd-comparison.md)

---

## Step 3: Owner Requirements Verification

Read `SPEC.owner_requirements` and produce a per-item verdict at HIGH confidence
(checked programmatically from SPEC/Layer 1), MEDIUM (requires Layer 3 element
inventory), or LOW (elevation-only, always CANNOT_VERIFY from plan view).

Full verification mapping table: [references/owner-requirements.md](references/owner-requirements.md)

---

## Step 4: Build and Write Review JSON

Assemble `layer1`, `cd_comparison`, `owner_requirements`, and `verdicts` into
`review_doc` and write it to `/tmp/kitchen-design-loop/review_{iteration}.json`.
Overall status is FAIL if any verdict is FAIL, else CANNOT_VERIFY if any verdict
is CANNOT_VERIFY, else PASS.

Full assembly code: [references/review-json-and-markdown-report.md](references/review-json-and-markdown-report.md)

---

## Step 5: Generate Markdown Report

Print the compliance report to the conversation: Layer 1 table, CD Set Comparison
table, Owner Requirements table, "Items Requiring Human Review" checklist, and
"Recommended Next Actions" ordered by severity. Use ✅ PASS / ❌ FAIL / ⚠️
CANNOT_VERIFY symbols.

**FAIL vs CANNOT_VERIFY**: FAIL means the script produced a reliable measurement
below the required minimum — `design:modify` can compute a fix. CANNOT_VERIFY means
the script couldn't extract the geometry or the check needs visual inspection —
it requires a human and is never auto-resolved.

If any FAIL items have `auto_fixable: true`, append an "Issues for design:modify"
section with the field, current value, and suggested fix — `design:modify` reads
this section when invoked from `design:loop`.

Full report template, symbol/escalation rules, the modify-handoff format, and the
SVG coordinate/unit reference:
[references/review-json-and-markdown-report.md](references/review-json-and-markdown-report.md)

---

## Related Skills

- `freecad-review` — Layer 1 scripts, Layer 3 dual-pass protocol, IRC compliance checklist
- `design:modify` — apply a fix from the "Issues for design:modify" section
- `design:loop` — orchestrates review → modify → QA in a capped cycle
