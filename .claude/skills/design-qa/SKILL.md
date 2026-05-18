---
name: design-qa
description: "Use this skill when Tyler asks to QA the current state after a manual edit, verify the pipeline ran cleanly, check whether a recent change resolves a compliance issue, or confirm the 5 PDF sheets are fresh relative to the current spec. Produces a verdict: PASS, PASS_WITH_WARNINGS, or BLOCKED. DO NOT invoke for a full review (use design:review) or the iterative loop (use design:loop)."
---

# design:qa — Post-Modification Quality Gate

## What This Skill Does

After a `design:modify` run (or any manual spec edit), re-runs compliance checks
from scratch and produces a verdict that accurately reflects the current state of
the drawings. Never reads cached compliance JSON.

Verdicts:
- **PASS** — All previously-FAIL items are now PASS; no regressions; no CANNOT_VERIFY.
- **PASS_WITH_WARNINGS** — All previously-FAIL items now PASS; CANNOT_VERIFY items
  remain (e.g., GFCI). Human review required for warnings before permit submission.
- **BLOCKED** — A regression was detected (previously-PASS item is now FAIL), a new
  FAIL appeared, no progress was made, or the pipeline produced stale outputs.
  Human action required before proceeding.

---

## Prerequisites

- `design_spec.py` importable: `python3 -c "from design_spec import SPEC" # exit 0`
- `~/.claude/skills/freecad-review/scripts/` contains `extract_clearances.py` and
  `check_compliance.py`
- `~/.claude/skills/pdf-proof/.venv` contains ezdxf, Pillow, PyMuPDF (fitz)
- `.design-loop/` directory exists
- A prior `review_N.json` exists in `/tmp/kitchen-design-loop/` to use as baseline.
  If no baseline exists (fresh QA run), all current FAIL items are treated as
  pre-existing — no regression detection is possible.

---

## Step 1: Cache Invalidation (unconditional)

At the start of every design:qa run, delete any cached compliance JSON regardless
of how it was invoked (from loop or directly):

```bash
rm -f /tmp/compliance_layer1.json /tmp/clearances.json
```

Then verify that the compliance JSON to be generated will be newer than
`design_spec.py` mtime. If a compliance JSON already exists after this `rm`,
something is wrong — halt and report.

---

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

---

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
using the same AISLE_MAP as `design:review` Step 1d (see design-review/SKILL.md).

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

---

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

---

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

---

## Step 6: Determine Verdict (Precedence Order)

Apply rules in this exact order. First matching rule sets the verdict:

1. Any regression (previously PASS now FAIL) → **BLOCKED**
2. Any new FAIL not in pre-modify baseline → **BLOCKED**
3. No-progress (all FAILs persist, iteration >= 2) → **BLOCKED**
4. Any pipeline failure or stale output (Steps 2 or 4 raised AssertionError) → **BLOCKED**
5. All previously-FAIL items now PASS; no CANNOT_VERIFY items → **PASS**
6. All previously-FAIL items now PASS; CANNOT_VERIFY items present → **PASS_WITH_WARNINGS**
7. Any FAIL item remains unresolved (no regression, no new FAIL) → **FAIL**
   (loop continues if iteration < max_iterations)

---

## Step 7: Update Session State and Session Log

```python
import json, pathlib, datetime, hashlib

state_path = pathlib.Path(
    '/home/tstapler/Documents/711-N60th-Plans/.design-loop/session_state.json')

if state_path.exists():
    state = json.loads(state_path.read_text())
else:
    state = {
        "session_id": datetime.datetime.utcnow().isoformat() + "Z",
        "iteration": 1,
        "max_iterations": 3,
        "started_at": datetime.datetime.utcnow().isoformat() + "Z",
        "status": "in_progress",
        "open_issues": [],
        "resolved_issues": [],
        "cannot_verify": [],
        "last_qa_verdict": None,
        "spec_hash": "",
        "spec_hashes_seen": [],
        "awaiting_human": False,
        "human_escalation_reason": None,
    }

# Move resolved items from open_issues to resolved_issues
for item_id in resolved:
    matching = [i for i in state.get("open_issues", []) if i["id"] == item_id]
    state.setdefault("resolved_issues", []).extend(matching)
state["open_issues"] = [
    i for i in state.get("open_issues", []) if i["id"] not in resolved]

# Update CANNOT_VERIFY list
state["cannot_verify"] = [
    v["id"] for v in fresh_verdicts.values()
    if v["result"] == "CANNOT_VERIFY"
]

# Set verdict and status
state["last_qa_verdict"] = qa_verdict
if qa_verdict == "PASS":
    state["status"] = "pass"
elif qa_verdict == "PASS_WITH_WARNINGS":
    state["status"] = "pass_with_warnings"
elif qa_verdict == "BLOCKED":
    state["status"] = "blocked"
    state["awaiting_human"] = True
    if not state.get("human_escalation_reason"):
        state["human_escalation_reason"] = escalation_reason
# FAIL: leave status as in_progress

# Update spec hash
spec_bytes = open(
    '/home/tstapler/Documents/711-N60th-Plans/design_spec.py', 'rb').read()
state["spec_hash"] = hashlib.sha256(spec_bytes).hexdigest()[:12]
state["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"

state_path.write_text(json.dumps(state, indent=2))

# Append to session log
log_path = '/home/tstapler/Documents/711-N60th-Plans/.design-loop/session_log.md'
log_entry = f"""
## Iteration {state['iteration']} — design:qa — {state['last_updated']}

**Verdict**: {qa_verdict}

| Issue | Was | Now |
|---|---|---|
{chr(10).join(f"| {r} | FAIL | PASS (resolved) |" for r in resolved)}
{chr(10).join(f"| {p} | FAIL | FAIL (persisting) |" for p in persisting)}
{chr(10).join(f"| {r} | PASS | FAIL (REGRESSION) |" for r in regressions)}

**CANNOT_VERIFY**: {state['cannot_verify']}
"""
with open(log_path, 'a') as f:
    f.write(log_entry)
```

---

## QA Report Output Format

Print to the conversation:

```
# Kitchen QA Report — Iteration {N}
**Date**: {timestamp}  |  **Spec hash**: {spec_hash}  |  **Verdict**: {verdict}

## Layer 1 Compliance Delta

| Issue | Baseline | Now | Change |
|---|---|---|---|
| island_south_aisle | FAIL (30.0") | PASS (43.0") | Resolved |
| island_north_aisle | PASS (55.0") | PASS (42.0") | Tighter but passing |
| GFCI outlet        | CANNOT_VERIFY | CANNOT_VERIFY | Unchanged |

## Output Verification

All 5 PDF sheets present and newer than design_spec.py:
  kitchen_floor_plan_annotated.pdf  ✓
  kitchen_elev_north.pdf            ✓
  kitchen_elev_south.pdf            ✓
  kitchen_elev_east.pdf             ✓
  kitchen_elev_west.pdf             ✓

## Items Requiring Human Review

- GFCI outlet: Cannot be verified from floor plan SVG. Requires electrical drawing
  or site inspection for permit submission.

## Verdict: PASS_WITH_WARNINGS

South aisle FAIL resolved. GFCI outlet requires human verification before permit
submission. Run design:loop for full orchestrated cycle.
```

---

## Acceptance Tests (from validation.md)

| Test | Pass criterion |
|---|---|
| SA-05: PASS_WITH_WARNINGS after south aisle fix | `last_qa_verdict == "PASS_WITH_WARNINGS"`, `island_south_aisle` in `resolved_issues`, `cannot_verify` non-empty, no open FAIL items |
| SA-06: Fresh compliance JSON (no stale cache) | `compliance_layer1.json` mtime > stale mtime written in test setup |
| NF-06: FAIL verdict on unmodified spec | `last_qa_verdict == "FAIL"` |

---

## Related Skills

- `design:review` — full compliance review; produces the baseline JSON that QA compares against
- `design:modify` — applies spec changes that QA verifies
- `design:loop` — orchestrates review → modify → QA in a capped cycle
- `freecad-review` — Layer 1 compliance scripts (`extract_clearances.py`, `check_compliance.py`)
