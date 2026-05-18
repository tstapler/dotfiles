---
name: design-modify
description: "Use this skill when Tyler asks to change a specific design parameter, fix a compliance FAIL item, move the island, adjust bar seating clearance, or apply a named change to design_spec.py. Requires a specific change target (field name or FAIL item from a review). DO NOT invoke for a general compliance review (use design:review) or the full iterative loop (use design:loop)."
---

# design:modify — Spec-Aware Design Changes with Safety Checks

## What This Skill Does

Given a FAIL item from a `design:review` output (or a direct change request from Tyler),
modifies `design_spec.py` safely:

1. **Constraint simulation** — compute all 4 aisle clearances BEFORE writing any file
2. **Feasibility check** — reject changes that resolve one FAIL but introduce another
3. **Safe spec editor** — validate Python syntax and import before applying
4. **Pipeline runner** — execute `pixi run permit-docs`, detect silent failures
5. **Diff reporter** — show what changed in spec and which PDFs were regenerated

Never writes to `design_spec.py` without passing all safety checks.

---

## Prerequisites

- `design_spec.py` importable: `python3 -c "from design_spec import SPEC" # exit 0`
- `pixi run permit-docs` runs clean on current spec
- `~/.claude/skills/pdf-proof/.venv` contains ezdxf, Pillow, PyMuPDF
- `.design-loop/` directory exists (or create it: `mkdir -p /home/tstapler/Documents/711-N60th-Plans/.design-loop/`)

---

## Step 1: Constraint Simulation (BEFORE any file write)

The simulation runs in Claude's reasoning using SPEC field values. No subprocess.
All formulas use `/ 25.4` for mm-to-inch conversion explicitly.

### 1a: Load current SPEC values

```python
from design_spec import SPEC

# Kitchen interior corners (mm)
KI_W = SPEC.kit_w_out_mm + SPEC.ext_thk_mm
KI_S = SPEC.kit_s_out_mm + SPEC.ext_thk_mm
KI_N = KI_S + SPEC.kit_ns_mm
KI_E = KI_W + SPEC.kit_ew_mm

# Island east-west offset: centered in kitchen
# ISLAND_X is derived in kitchen_permit_docs.py; replicate here:
ISLAND_X = KI_W + (SPEC.kit_ew_mm - SPEC.island_ew_mm) / 2.0
```

### 1b: Compute current clearances (ground-truth validation)

Before simulating any proposed change, verify the simulator reproduces the known
ground-truth values for the default spec. If either check fails, halt and report
the formula discrepancy — do not trust the simulator for proposed changes.

```python
# Current state (bar_y_offset_mm = 762.0 in default spec)
BAR_Y_current = KI_S + SPEC.bar_y_offset_mm
ISLAND_Y_current = BAR_Y_current + SPEC.bar_ns_mm
ISLAND_TOP_Y_current = ISLAND_Y_current + SPEC.island_ns_mm

south_aisle_in_current = (BAR_Y_current - KI_S) / 25.4
north_aisle_in_current = (KI_N - ISLAND_TOP_Y_current) / 25.4
east_aisle_in_current  = (KI_E - (ISLAND_X + SPEC.island_ew_mm)) / 25.4
west_aisle_in_current  = (ISLAND_X - KI_W) / 25.4

# Ground-truth anchors (verified 2026-05-10 against extract_clearances.py output):
# south_aisle_in_current should equal 30.0 ± 0.01
# north_aisle_in_current should equal 55.0 ± 0.1
```

Key formula notes:
- `south_aisle_in = (BAR_Y - KI_S) / 25.4`
  = `bar_y_offset_mm / 25.4` (bar_y_offset_mm is the south aisle in mm directly)
- `north_aisle_in = (KI_N - ISLAND_TOP_Y) / 25.4`
  where `ISLAND_TOP_Y = KI_S + bar_y_offset_mm + bar_ns_mm + island_ns_mm`
  **Critical**: include `bar_ns_mm` in the chain — the north aisle is measured from
  the top of the island body, not the top of the bar overhang.
- `east_aisle_in = (KI_E - (ISLAND_X + island_ew_mm)) / 25.4`
- `west_aisle_in = (ISLAND_X - KI_W) / 25.4`

### 1c: Compute proposed clearances

Substitute the proposed value for the field being changed. Compute all four aisles.

```python
# Example: changing bar_y_offset_mm
proposed_bar_y_offset = <proposed_value_mm>

BAR_Y_proposed = KI_S + proposed_bar_y_offset
ISLAND_Y_proposed = BAR_Y_proposed + SPEC.bar_ns_mm
ISLAND_TOP_Y_proposed = ISLAND_Y_proposed + SPEC.island_ns_mm

south_aisle_in_proposed = (BAR_Y_proposed - KI_S) / 25.4
north_aisle_in_proposed = (KI_N - ISLAND_TOP_Y_proposed) / 25.4
east_aisle_in_proposed  = east_aisle_in_current   # unchanged (bar_y doesn't affect EW)
west_aisle_in_proposed  = west_aisle_in_current   # unchanged
```

### 1d: Print simulation table (always, before any edit)

Print this table to the conversation before any file operation:

```
Constraint Simulation — bar_y_offset_mm: {current} → {proposed} mm

Aisle         | Current  | Proposed | Required | Status
--------------|----------|----------|----------|--------
South aisle   | 30.0"    | {s}"     | ≥ 42"    | {PASS/FAIL}
North aisle   | 55.0"    | {n}"     | ≥ 42"    | {PASS/FAIL}
East aisle    | 46.5"    | {e}"     | ≥ 42"    | {PASS/FAIL}
West aisle    | 46.5"    | {w}"     | ≥ 42"    | {PASS/FAIL}
```

### 1e: Feasibility check

Rules:
1. If the proposed change **resolves** the target FAIL and **all currently-passing checks
   remain passing** → proceed to Step 2.
2. If any currently-passing aisle would drop below its minimum → **REJECT**:
   - Do NOT write any file
   - Report: "Proposed change would resolve [FAIL item] but introduce [NEW FAIL] in
     [field]. Cannot auto-apply. Human review required."
   - Set session state `awaiting_human: true`
   - Halt.
3. If the target FAIL is not resolved by the proposed change → recompute using the
   feasible range formula (Step 1f).

### 1f: Feasible range for bar_y_offset_mm (south-aisle case)

```python
# Minimum bar_y_offset_mm for south aisle >= 42":
min_for_south = SPEC.compliance_targets['min_south_aisle_in'] * 25.4
# = 42 * 25.4 = 1066.8 mm

# Preferred bar_y_offset_mm for south aisle >= 48":
pref_for_south = SPEC.compliance_targets.get('preferred_south_aisle_in', 48) * 25.4
# = 48 * 25.4 = 1219.2 mm

# Maximum bar_y_offset_mm before north aisle < 42":
# KI_N - (KI_S + bar_y_offset + bar_ns + island_ns) >= 42 * 25.4
# bar_y_offset <= KI_N - KI_S - bar_ns - island_ns - 1066.8
max_for_north = (KI_N - KI_S
                 - SPEC.bar_ns_mm
                 - SPEC.island_ns_mm
                 - SPEC.compliance_targets['min_north_aisle_in'] * 25.4)
# With default values:
# max_for_north = 3175.0 - 381.0 - 635.0 - 1066.8 = 1092.2 mm

# Choose: preferred if feasible, otherwise minimum
if pref_for_south <= max_for_north:
    target_value = pref_for_south
elif min_for_south <= max_for_north:
    target_value = max_for_north  # maximum that keeps north aisle passing
else:
    # No feasible value exists — escalate to human
    target_value = None
```

With default spec values: `max_for_north = 1092.2 mm`.
Since `pref_for_south = 1219.2 > 1092.2`, the preferred 48" is not feasible.
Use `1092.2 mm` → south aisle = `1092.2 / 25.4 = 43.0"` (rounds to 42.99").

---

## Step 2: Safe Spec Editor

Protocol executes in this exact order. A failure at any step halts and triggers rollback.

### 2a: Backup current spec

```python
import shutil, time, pathlib

spec_path = '/home/tstapler/Documents/711-N60th-Plans/design_spec.py'
ts = int(time.time())
backup_path = f'/home/tstapler/Documents/711-N60th-Plans/.design-loop/design_spec_backup_{ts}.py'

pathlib.Path('/home/tstapler/Documents/711-N60th-Plans/.design-loop').mkdir(
    parents=True, exist_ok=True)
shutil.copy(spec_path, backup_path)
original_content = open(spec_path).read()
```

**Why project dir, not /tmp**: `/tmp` is typically a tmpfs mount on Linux. `os.replace()`
across different filesystems raises `OSError: [Errno 18] Invalid cross-device link`.
Storing the backup in `.design-loop/` (same filesystem as `design_spec.py`) avoids this.

### 2a2: Snapshot pre-modify compliance into session state

**Required by design:qa** — must run before ANY spec change is written.

```python
import json, pathlib, subprocess

state_path = pathlib.Path('/home/tstapler/Documents/711-N60th-Plans/.design-loop/session_state.json')
state = json.loads(state_path.read_text()) if state_path.exists() else {}

# Run constraint simulator to capture current baseline
sim = subprocess.run(
    ['python3', '/home/tstapler/.claude/skills/design-modify/scripts/constraint_simulator.py'],
    capture_output=True, text=True,
    cwd='/home/tstapler/Documents/711-N60th-Plans'
)
# Also run extract_clearances for the authoritative Layer 1 snapshot
extract = subprocess.run(
    ['~/.claude/skills/pdf-proof/.venv/bin/python3',
     '~/.claude/skills/freecad-review/scripts/extract_clearances.py',
     '--svg', 'output/kitchen/kitchen_floor_plan_annotated.svg',
     '--output', '/tmp/pre_modify_clearances.json'],
    capture_output=True, text=True, shell=False,
    cwd='/home/tstapler/Documents/711-N60th-Plans'
)
if pathlib.Path('/tmp/pre_modify_clearances.json').exists():
    pre_compliance = json.loads(open('/tmp/pre_modify_clearances.json').read())
else:
    pre_compliance = {'source': 'constraint_simulator', 'output': sim.stdout}

state['pre_modify_compliance'] = pre_compliance
state_path.write_text(json.dumps(state, indent=2))
```

### 2b: Write proposed content to temp file in project dir

```python
proposed_content = original_content.replace(
    f'{field_name}: float = {current_value}',
    f'{field_name}: float = {new_value}'
)

tmp_path = f'/home/tstapler/Documents/711-N60th-Plans/.design-loop/design_spec_proposed_{ts}.py'
with open(tmp_path, 'w') as f:
    f.write(proposed_content)
```

### 2c: Syntax check

```bash
python3 -c "import ast; ast.parse(open('${tmp_path}').read())"
```

If exit code != 0: do not proceed. Log the syntax error. Restore from backup.

### 2d: Import check

```bash
python3 -c "import sys; sys.path.insert(0, '/home/tstapler/Documents/711-N60th-Plans/.design-loop'); \
  import design_spec_proposed_${ts} as ds; print(ds.SPEC)"
```

The module name must match the filename stem. If exit code != 0: do not proceed.
Log the import error. Restore from backup.

### 2e: Field value assertion

```bash
python3 -c "
import sys
sys.path.insert(0, '/home/tstapler/Documents/711-N60th-Plans/.design-loop')
import design_spec_proposed_${ts} as ds
assert ds.SPEC.${field_name} == ${new_value}, \
    f'Expected ${new_value}, got {ds.SPEC.${field_name}}'
print('field check OK')
"
```

If exit code != 0: do not proceed. Log the assertion failure. Restore from backup.

### 2f: Atomic copy (same-filesystem)

```python
import shutil
# shutil.copy is NOT atomic, but on the same filesystem the window is minimal.
# os.replace would be atomic but tmp may be on tmpfs (different device).
# Since both paths are on the same filesystem here, use shutil.copy then verify.
shutil.copy(tmp_path, spec_path)
# Verify the copy landed correctly
assert open(spec_path).read() == proposed_content, "Copy verification failed"
```

### 2g: Rollback procedure

If ANY step (2c, 2d, 2e, or 2f) fails:

```python
# Restore original spec
with open(spec_path, 'w') as f:
    f.write(original_content)

# Log failure
import datetime
log_path = '/home/tstapler/Documents/711-N60th-Plans/.design-loop/session_log.md'
with open(log_path, 'a') as log:
    log.write(f"\n## ROLLBACK {datetime.datetime.utcnow().isoformat()}Z\n")
    log.write(f"Reason: {failure_reason}\n")
    log.write(f"Proposed value: {field_name} = {new_value}\n")
    log.write(f"Backup at: {backup_path}\n")

# Update session state
import json, pathlib
state_path = pathlib.Path('/home/tstapler/Documents/711-N60th-Plans/.design-loop/session_state.json')
if state_path.exists():
    state = json.loads(state_path.read_text())
    state['status'] = 'blocked'
    state['awaiting_human'] = True
    state['human_escalation_reason'] = f"Spec edit rollback: {failure_reason}"
    state_path.write_text(json.dumps(state, indent=2))
```

---

## Step 3: Pipeline Runner

### 3a: Record start time and backup current outputs

**Must write `pipeline_start_ts` to session_state.json before running pipeline** — design:qa uses this as the freshness floor for PDF timestamp verification.

```bash
RUN_START=$(date +%s)

# Persist to session state immediately
python3 -c "
import json, pathlib
p = pathlib.Path('/home/tstapler/Documents/711-N60th-Plans/.design-loop/session_state.json')
s = json.loads(p.read_text()) if p.exists() else {}
s['pipeline_start_ts'] = $RUN_START
p.write_text(json.dumps(s, indent=2))
"

# Backup current outputs
cp -r /home/tstapler/Documents/711-N60th-Plans/output/kitchen/ \
  /home/tstapler/Documents/711-N60th-Plans/.design-loop/kitchen_output_backup_${RUN_START}/

# Delete outputs to force fresh generation
rm -f /home/tstapler/Documents/711-N60th-Plans/output/kitchen/*.pdf
rm -f /home/tstapler/Documents/711-N60th-Plans/output/kitchen/*.svg
rm -f /home/tstapler/Documents/711-N60th-Plans/output/kitchen/*.png
```

### 3b: Run pipeline

```bash
cd /home/tstapler/Documents/711-N60th-Plans
pixi run permit-docs 2>&1 | tee /home/tstapler/Documents/711-N60th-Plans/.design-loop/pipeline_run_${RUN_START}.log
PIPELINE_RC=${PIPESTATUS[0]}
```

Note: `2>&1` captures both stdout and stderr into the log. This is required because
FreeCAD has been observed returning exit code 0 on unhandled Python exceptions while
printing the traceback to stdout rather than stderr.

### 3c: Failure detection (two conditions — either triggers rollback)

```bash
# Condition 1: non-zero exit code
if [ "$PIPELINE_RC" -ne 0 ]; then
    echo "PIPELINE FAILED: exit code ${PIPELINE_RC}"
    PIPELINE_FAILED=true
fi

# Condition 2: Traceback in combined output (catches FreeCAD silent failures)
if grep -q "Traceback (most recent call last)" \
    /home/tstapler/Documents/711-N60th-Plans/.design-loop/pipeline_run_${RUN_START}.log; then
    echo "PIPELINE FAILED: Traceback detected in output"
    PIPELINE_FAILED=true
fi
```

On failure: restore outputs from `.design-loop/kitchen_output_backup_${RUN_START}/`,
revert `design_spec.py` from backup (Step 2g rollback procedure), set session
state to BLOCKED.

### 3d: Output freshness check

After a reported-success run (no failure conditions), verify all 5 expected PDFs
exist and have mtime after RUN_START:

```python
import os, time

run_start = int(open('/tmp/run_start').read().strip())  # or pass as variable
expected_files = [
    '/home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_floor_plan_annotated.pdf',
    '/home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_elev_north.pdf',
    '/home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_elev_south.pdf',
    '/home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_elev_east.pdf',
    '/home/tstapler/Documents/711-N60th-Plans/output/kitchen/kitchen_elev_west.pdf',
]

for f in expected_files:
    if not os.path.exists(f):
        raise AssertionError(f"Missing output: {f}")
    mtime = os.path.getmtime(f)
    if mtime <= run_start:
        raise AssertionError(f"Stale output (mtime {mtime} <= run_start {run_start}): {f}")

# Report runtime
pipeline_duration = int(time.time()) - run_start
n_files = len(expected_files)
print(f"Pipeline ran in {pipeline_duration}s, {n_files} files regenerated")
```

If any file is missing or stale after a reported-success run: treat as silent failure
and perform full rollback (spec + outputs). This is a defense against the case where
FreeCAD exits 0, prints no Traceback, but produces no output.

---

## Step 4: Diff Reporter

### 4a: Spec diff

```bash
rtk git diff /home/tstapler/Documents/711-N60th-Plans/design_spec.py
```

Only show the spec diff, not generated files.

### 4b: Output files changed

```bash
# List PDFs with their new mtimes
ls -la /home/tstapler/Documents/711-N60th-Plans/output/kitchen/*.pdf
```

### 4c: Print summary to conversation

```
Spec change:
  field:  bar_y_offset_mm
  old:    762.0 mm  (south aisle was 30.0")
  new:    1092.2 mm (south aisle predicted 43.0")

Clearance simulation vs actual (run extract_clearances.py to get actual):
  south_aisle predicted: 43.0"
  north_aisle predicted: 42.0"  (was 55.0" — tighter but still passing)
  east_aisle:  46.5" (unchanged)
  west_aisle:  46.5" (unchanged)

Pipeline output (5/5 sheets regenerated):
  kitchen_floor_plan_annotated.pdf  ✓  mtime: {mtime}
  kitchen_elev_north.pdf            ✓  mtime: {mtime}
  kitchen_elev_south.pdf            ✓  mtime: {mtime}
  kitchen_elev_east.pdf             ✓  mtime: {mtime}
  kitchen_elev_west.pdf             ✓  mtime: {mtime}
```

### 4d: Append to session log

```python
import datetime

log_entry = f"""
## Iteration {iteration} — design:modify — {datetime.datetime.utcnow().isoformat()}Z

### Constraint Simulation
| Aisle | Before | After | Required | Result |
|---|---|---|---|---|
| South | {south_current:.1f}" | {south_proposed:.1f}" | ≥ 42" | {s_result} |
| North | {north_current:.1f}" | {north_proposed:.1f}" | ≥ 42" | {n_result} |
| East  | {east_current:.1f}"  | {east_proposed:.1f}"  | ≥ 42" | {e_result} |
| West  | {west_current:.1f}"  | {west_proposed:.1f}"  | ≥ 42" | {w_result} |

### Spec Change
- Field: `{field_name}`
- Old: {old_value}
- New: {new_value}

### Pipeline
- Duration: {duration}s
- Output: {n_regen}/5 PDFs regenerated
- Backup: `.design-loop/kitchen_output_backup_{run_start}/`
"""

with open('/home/tstapler/Documents/711-N60th-Plans/.design-loop/session_log.md', 'a') as f:
    f.write(log_entry)
```

---

## Coordinate and Unit Reference

All formulas use `/ 25.4` for mm-to-inch conversion explicitly. Never divide by 25.4
implicitly in prose — always show the division in code.

```python
# Kitchen interior corners (mm, from SPEC)
KI_S = SPEC.kit_s_out_mm + SPEC.ext_thk_mm          # south interior wall
KI_N = KI_S + SPEC.kit_ns_mm                         # north interior wall
KI_W = SPEC.kit_w_out_mm + SPEC.ext_thk_mm           # west interior wall
KI_E = KI_W + SPEC.kit_ew_mm                         # east interior wall

# Island position (Y axis — bar controls south aisle)
BAR_Y        = KI_S + bar_y_offset_mm                # bar south face
ISLAND_Y     = BAR_Y + SPEC.bar_ns_mm                # island south face
ISLAND_TOP_Y = ISLAND_Y + SPEC.island_ns_mm          # island north face

# Aisle clearances (inches = mm / 25.4)
south_aisle_in = (BAR_Y - KI_S)            / 25.4   # = bar_y_offset_mm / 25.4
north_aisle_in = (KI_N - ISLAND_TOP_Y)     / 25.4
east_aisle_in  = (KI_E - (ISLAND_X + SPEC.island_ew_mm)) / 25.4
west_aisle_in  = (ISLAND_X - KI_W)         / 25.4

# Ground truth (default spec, bar_y_offset_mm = 762.0):
#   south_aisle_in = 762.0 / 25.4 = 30.0"
#   north_aisle_in = (2992.6 - 1595.6) / 25.4 = 1397.0 / 25.4 = 55.0"
```

SVG constants (do not modify — hardcoded in freecad-review scripts):
- `SVG_PER_INCH = 3.306`
- `KIT_SVG_X0 = 297.1`
- `KIT_SVG_Y0 = 166.0`

---

## Scope Limitation

design:modify handles changes to `design_spec.py` numeric fields only.

It does NOT:
- Add new fields to the spec (that is an Epic 1 task)
- Modify `kitchen_permit_docs.py` geometry or drawing logic
- Override compliance targets in `SPEC.compliance_targets`
- Commit to git (Tyler reviews and commits manually)

---

## Related Skills

- `design:review` — produces the FAIL items that design:modify acts on
- `design:qa` — re-runs compliance checks after design:modify completes
- `design:loop` — orchestrates review → modify → QA in a capped cycle
- `freecad-review` — Layer 1 compliance scripts used for verification
