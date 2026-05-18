---
name: design-loop
description: "Use this skill when Tyler asks to run the design loop, fix compliance issues autonomously, iterate on the kitchen design, or when the user says 'run design:loop'. Orchestrates design:review → design:modify → design:qa in a capped cycle (max 3 iterations). DO NOT invoke for a one-shot review (use design:review) or a single spec edit (use design:modify)."
---

# design:loop — Orchestrated Review → Modify → QA Cycle

## Quick Start

```
User: "run design:loop"
Claude: reads this SKILL.md and executes the protocol below inline
```

No subprocess skill calls. Claude reads each referenced SKILL.md (`design-review`,
`design-modify`, `design-qa`) and executes their protocols within this session.

---

## Workflow Diagram

```
                        design:loop START
                               |
                  ┌────────────▼────────────┐
                  │  Load or init session    │
                  │  session_state.json      │
                  └────────────┬────────────┘
                               |
                  ┌────────────▼────────────┐
                  │  Check oscillation       │◄─────────────────────┐
                  │  (spec hash seen before?)│                      │
                  └────┬────────────┬───────┘                      │
                  YES  │            │ NO                            │
                  ┌────▼───┐  ┌────▼────────────────────────┐      │
                  │BLOCKED │  │  Run design:review protocol  │      │
                  │Escalate│  │  → /tmp/.../review_N.json    │      │
                  └────────┘  └────┬───────────────┬─────────┘      │
                               FAIL│               │ No FAILs        │
                          ┌────────▼──────┐  ┌────▼────────────┐   │
                          │ For each FAIL │  │ Run design:qa   │   │
                          │ auto_fixable  │  │ → final verdict │   │
                          └────┬──────────┘  └────┬────────────┘   │
                          ┌────▼────────────────┐  │                │
                          │ design:modify:       │  │                │
                          │  simulate → edit     │  │                │
                          │  → pipeline → diff   │  │                │
                          └────┬────────┬────────┘  │                │
                       BLOCKED │        │ OK         │                │
                          ┌────▼───┐   └──────────► QA               │
                          │Escalate│                 │                │
                          └────────┘          PASS / │ PASS_WITH_WARN│
                                              ┌──────▼──────────┐    │
                                              │ Print git commit │    │
                                              │ EXIT LOOP        │    │
                                              └─────────────────-┘    │
                                                                       │
                                              FAIL (iteration < 3) ───┘
                                              BLOCKED → Escalate
                                              iteration >= 3 → Escalate
```

---

## Prerequisites

- `design_spec.py` exists and is importable:
  `python3 -c "from design_spec import SPEC" # must exit 0`
- `pixi run permit-docs` runs clean on current spec
- `~/.claude/skills/freecad-review/scripts/` contains the 4 compliance scripts
- `~/.claude/skills/pdf-proof/.venv` contains ezdxf, Pillow, PyMuPDF (fitz)
- `.design-loop/` directory (created below if missing)

---

## Phase 0: Session State Initialization

### 0a: Create .design-loop directory

```bash
mkdir -p /home/tstapler/Documents/711-N60th-Plans/.design-loop
```

### 0b: Check for existing session

```python
import json, pathlib, datetime, hashlib

state_path = pathlib.Path(
    '/home/tstapler/Documents/711-N60th-Plans/.design-loop/session_state.json')

if state_path.exists():
    state = json.loads(state_path.read_text())
    # RESUME PATH: report current state and ask for confirmation
    print(f"Resuming session from iteration {state['iteration']}.")
    print(f"Last verdict: {state.get('last_qa_verdict')}")
    print(f"Open issues: {[i['id'] for i in state.get('open_issues', [])]}")
    print(f"Status: {state['status']}")

    if state.get('awaiting_human'):
        print(f"\nHUMAN ACTION REQUIRED: {state['human_escalation_reason']}")
        print("Resolve the above before re-running design:loop.")
        # HALT — do not auto-continue from awaiting_human
        raise SystemExit("Awaiting human review. Loop halted.")

    # Ask user to confirm before proceeding past iteration 0
    if state['iteration'] > 0:
        print("\nContinue from current state? (Confirm to proceed.)")
        # Claude waits for user confirmation here before executing further steps

else:
    # FRESH START
    spec_bytes = open('/home/tstapler/Documents/711-N60th-Plans/design_spec.py', 'rb').read()
    spec_hash = hashlib.sha256(spec_bytes).hexdigest()[:12]

    state = {
        "session_id": datetime.datetime.utcnow().isoformat() + "Z",
        "iteration": 0,
        "max_iterations": 3,
        "started_at": datetime.datetime.utcnow().isoformat() + "Z",
        "last_updated": datetime.datetime.utcnow().isoformat() + "Z",
        "status": "in_progress",
        "open_issues": [],
        "resolved_issues": [],
        "cannot_verify": [],
        "last_qa_verdict": None,
        "spec_hash": spec_hash,
        "spec_hashes_seen": [],
        "awaiting_human": False,
        "human_escalation_reason": None,
    }
    state_path.write_text(json.dumps(state, indent=2))
```

### 0c: Session state schema reference

```json
{
  "session_id": "2026-05-10T14:23:00Z",
  "iteration": 0,
  "max_iterations": 3,
  "started_at": "ISO8601",
  "last_updated": "ISO8601",
  "status": "in_progress | pass | pass_with_warnings | blocked",
  "open_issues": [
    {
      "id": "string",
      "rule": "string",
      "measured_in": "float",
      "required_in": "float",
      "result": "FAIL",
      "attempts": 0,
      "fix_field": "string"
    }
  ],
  "resolved_issues": [],
  "cannot_verify": [],
  "last_qa_verdict": null,
  "spec_hash": "string (sha256[:12])",
  "spec_hashes_seen": [],
  "awaiting_human": false,
  "human_escalation_reason": null
}
```

### State transition rules

| From status | Trigger | To status |
|---|---|---|
| `in_progress` | QA returns PASS | `pass` |
| `in_progress` | QA returns PASS_WITH_WARNINGS | `pass_with_warnings` |
| `in_progress` | QA returns BLOCKED or pipeline fails | `blocked` |
| `in_progress` | iteration reaches max_iterations | `blocked` |
| `in_progress` | oscillation detected | `blocked` |
| `blocked` | human resolves escalation, re-runs loop | `in_progress` (fresh session) |

---

## Phase 1: Main Loop (max 3 iterations)

```
LOOP iterations 0 through max_iterations-1:
  1. Oscillation check
  2. design:review
  3. Evaluate FAIL items
  4. design:modify (if FAIL items exist)
  5. design:qa
  6. Evaluate QA verdict → EXIT or continue
```

### Step 1: Oscillation detection (start of each iteration)

```python
import hashlib, json, pathlib, datetime

spec_bytes = open(
    '/home/tstapler/Documents/711-N60th-Plans/design_spec.py', 'rb').read()
current_hash = hashlib.sha256(spec_bytes).hexdigest()[:12]

state_path = pathlib.Path(
    '/home/tstapler/Documents/711-N60th-Plans/.design-loop/session_state.json')
state = json.loads(state_path.read_text())

if current_hash in state["spec_hashes_seen"]:
    state["status"] = "blocked"
    state["awaiting_human"] = True
    state["human_escalation_reason"] = (
        f"Oscillation detected: spec hash {current_hash} appeared in a previous "
        "iteration. The loop is cycling between two states that both fail compliance. "
        "Manual adjustment of constraint targets or design parameters required."
    )
    state["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
    state_path.write_text(json.dumps(state, indent=2))
    print(f"\nOscillation detected. Human review required.")
    print(f"Reason: {state['human_escalation_reason']}")
    # EXIT LOOP
    raise SystemExit("Loop halted: oscillation detected.")

# Iteration cap check
if state["iteration"] >= state["max_iterations"]:
    state["status"] = "blocked"
    state["awaiting_human"] = True
    state["human_escalation_reason"] = (
        f"Max iterations ({state['max_iterations']}) reached without full compliance. "
        "Human review required to resolve remaining issues."
    )
    state["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
    state_path.write_text(json.dumps(state, indent=2))
    print(f"\nMax iterations reached. Human review required.")
    raise SystemExit("Loop halted: max iterations reached.")
```

Note per plan.md Known Issues: record spec hash at the END of each successful
modify step (after pipeline confirms success), not at the start of the iteration.
This prevents false-positive oscillation detection on interrupted-then-resumed sessions.

### Step 2: Execute design:review protocol

Read and execute the full protocol from
`~/.claude/skills/design-review/SKILL.md`.

Abbreviated sequence (see design-review/SKILL.md for full detail):

1. Determine iteration number from `session_state["iteration"] + 1`
2. `rm -f /tmp/compliance_layer1.json /tmp/clearances.json`
3. Run `extract_clearances.py --svg output/kitchen/kitchen_floor_plan_annotated.svg --output /tmp/clearances.json`
4. Run `check_compliance.py --dxf output/kitchen/kitchen_floor_plan_annotated.dxf --svg output/kitchen/kitchen_floor_plan_annotated.svg --output /tmp/compliance_layer1.json`
5. Parse results against `SPEC.compliance_targets`; build verdicts list
6. Run CD set comparison (element-zone for page 4; pixel-diff for pages 9/10)
7. Verify owner requirements per mapping table
8. Write `/tmp/kitchen-design-loop/review_{N}.json`
9. Print Markdown compliance report

Success criterion: `review_N.json` exists and is non-empty.
Failure action: halt, escalate.

### Step 3: Evaluate FAIL items

```python
import json, pathlib

N = state["iteration"] + 1
review = json.loads(
    pathlib.Path(f'/tmp/kitchen-design-loop/review_{N}.json').read_text())

fail_items = [v for v in review["verdicts"]
              if v["result"] == "FAIL" and v.get("auto_fixable")]
cannot_verify_items = [v for v in review["verdicts"]
                       if v["result"] == "CANNOT_VERIFY"]

# Update session state open_issues
state["open_issues"] = [
    {
        "id": v["id"],
        "rule": v["rule"],
        "measured_in": v.get("measured"),
        "required_in": v.get("required"),
        "result": v["result"],
        "attempts": 0,
        "fix_field": v.get("fix_field"),
    }
    for v in fail_items
]
state["cannot_verify"] = [v["id"] for v in cannot_verify_items]
```

**If no FAIL items with auto_fixable: true:**

```
→ Proceed directly to Step 5 (design:qa)
→ If QA returns PASS or PASS_WITH_WARNINGS → EXIT LOOP with success
```

### Step 4: Execute design:modify for each FAIL item

Read and execute the full protocol from
`~/.claude/skills/design-modify/SKILL.md`.

**No-progress detection (Story 5.3):**

Before each modify attempt, check if the same FAIL item was attempted in iteration
N-1 with the same proposed value. If yes: mark as `CANNOT_AUTO_FIX` and continue
to the next fail item without running modify again.

```python
# Check for prior attempt with same fix value
for item in fail_items:
    prior_attempts = [
        h for h in state.get("history", [])
        if h.get("item_id") == item["id"]
        and h.get("iteration") == state["iteration"] - 1
    ]
    if prior_attempts and prior_attempts[-1].get("outcome") == "NO_CHANGE":
        print(f"Loop detected: {item['id']} failed to resolve in iteration "
              f"{state['iteration'] - 1}. Escalating.")
        item["result"] = "CANNOT_AUTO_FIX"
        continue

    # Proceed with modify
```

**Abbreviated modify sequence per FAIL item** (see design-modify/SKILL.md for full detail):

1. Load SPEC values; compute current 4 aisle clearances
2. Validate ground-truth anchor (south=30.0", north=55.0" for default spec)
3. Run constraint simulation for proposed fix value
4. Print simulation table — ALL four aisles, before and after
5. Feasibility check: reject if any currently-passing aisle would drop below minimum
6. If infeasible: set `awaiting_human: true`, escalate, EXIT LOOP
7. Backup spec to `.design-loop/design_spec_backup_{ts}.py`
8. Write proposed content to `.design-loop/design_spec_proposed_{ts}.py`
9. Syntax check: `python3 -c "import ast; ast.parse(open(tmp_path).read())"` — must exit 0
10. Import check: `python3 -c "import sys; sys.path.insert(...); import ..."` — must exit 0
11. Field value assertion — must exit 0
12. `shutil.copy(tmp_path, spec_path)` — apply the edit
13. **Record spec hash after successful edit** (for oscillation detection):
    ```python
    new_hash = hashlib.sha256(open(spec_path, 'rb').read()).hexdigest()[:12]
    state["spec_hashes_seen"].append(new_hash)
    ```
14. Backup outputs; delete outputs; run pipeline: `pixi run permit-docs 2>&1 | tee .design-loop/pipeline_run_{ts}.log`
15. Failure check: exit code != 0 OR `grep "Traceback"` in log → rollback spec + outputs, set BLOCKED, EXIT LOOP
16. Output freshness check: all 5 PDFs present with mtime > run_start → if not, rollback, BLOCKED
17. Print diff summary; append to `.design-loop/session_log.md`

**If modify returns BLOCKED or pipeline FAIL:**

```python
state["status"] = "blocked"
state["awaiting_human"] = True
state["human_escalation_reason"] = f"Pipeline failure or infeasible constraint: {reason}"
state_path.write_text(json.dumps(state, indent=2))
print(f"\nHuman review required — {reason}")
# EXIT LOOP
```

**If modify returns NO_CHANGE (constraint simulator rejected all solutions):**

```python
item["result"] = "CANNOT_AUTO_FIX"
# Continue to next fail_item
```

**After all fail items processed — if all are CANNOT_AUTO_FIX:**

```
→ Proceed to Step 5 (design:qa)
→ QA will likely return FAIL (issues persist) → continue to next iteration or cap
```

### Step 5: Execute design:qa protocol

Read and execute the full protocol from
`~/.claude/skills/design-qa/SKILL.md`.

Abbreviated sequence (see design-qa/SKILL.md for full detail):

1. `rm -f /tmp/compliance_layer1.json /tmp/clearances.json` (unconditional)
2. Verify `design_spec.py` mtime is newer than any cached compliance JSON
3. Run `extract_clearances.py` and `check_compliance.py` fresh
4. Read baseline from `.design-loop/review_{N-1}.json` (or `review_{N}.json` if this is iteration 1)
5. Compare fresh results to baseline: classify as resolved / persisting / regression
6. If any regression: set QA verdict BLOCKED immediately
7. Verify all 5 PDFs have mtime newer than `design_spec.py` mtime
8. Run visual zone check for changed drawings (floor plan if bar_y_offset_mm changed)
9. Determine verdict per precedence rules (see design-qa/SKILL.md Step 5)
10. Update session_state with verdict, resolved_issues, cannot_verify
11. Append entry to `.design-loop/session_log.md`

### Step 6: Evaluate QA verdict and decide loop action

```python
qa_verdict = state.get("last_qa_verdict")

if qa_verdict in ("PASS", "PASS_WITH_WARNINGS"):
    # SUCCESS PATH
    state["status"] = qa_verdict.lower().replace(" ", "_")
    state["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
    state_path.write_text(json.dumps(state, indent=2))
    # Print exit report and git commit instruction
    _print_exit_report(state, qa_verdict)
    # EXIT LOOP

elif qa_verdict == "BLOCKED":
    state["status"] = "blocked"
    state["awaiting_human"] = True
    state["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
    state_path.write_text(json.dumps(state, indent=2))
    print(f"\nHuman review required. Reason: {state.get('human_escalation_reason')}")
    # EXIT LOOP

else:  # FAIL — continue loop
    state["iteration"] += 1
    state["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
    state_path.write_text(json.dumps(state, indent=2))
    # Continue to next iteration (go back to Step 1)
```

---

## Phase 2: Exit Report

### Loop exit report format

Written to `.design-loop/session_log.md` and printed to the user:

```
## design:loop Exit Report — {session_id}

**Final status**: {status}
**Iterations used**: {iteration} of {max_iterations}
**Session duration**: {elapsed}

### Changes Made

| Iteration | Field | Old value | New value | South aisle | North aisle |
|---|---|---|---|---|---|
| 1 | bar_y_offset_mm | 762.0 mm | 1092.2 mm | 30.0" → 43.0" | 55.0" → 42.0" |

### Resolved Issues

{list of resolved items with before/after measurements}

### Remaining Open Issues

{FAIL items that could not be auto-resolved, with reason}

### Cannot Verify (requires human)

{list of CANNOT_VERIFY items, one line each with required human action}

### Next Step
```

**On PASS or PASS_WITH_WARNINGS:** print git commit instruction:

```
Review the spec diff and run:
  git add /home/tstapler/Documents/711-N60th-Plans/design_spec.py
  git commit -m "design: fix south aisle clearance (bar_y_offset_mm 762→1092mm) — PASS_WITH_WARNINGS"

GFCI outlet requires manual permit-set annotation (CANNOT_VERIFY — see Items Requiring Human Review).
```

**On BLOCKED:** print escalation summary:

```
Human review required. Reason: {human_escalation_reason}

Open issues that require manual resolution:
{list}

When resolved, clear session_state.json and re-run design:loop.
```

---

## Session Log Format

Each entry appended to `.design-loop/session_log.md`:

```
## Iteration N — {phase} — {ISO8601 timestamp}

### Phase: {review | modify | qa}
{phase-specific content}
```

---

## Project File Paths

| Resource | Path |
|---|---|
| Design spec | `/home/tstapler/Documents/711-N60th-Plans/design_spec.py` |
| Session state | `/home/tstapler/Documents/711-N60th-Plans/.design-loop/session_state.json` |
| Session log | `/home/tstapler/Documents/711-N60th-Plans/.design-loop/session_log.md` |
| Review JSON (per iter) | `/tmp/kitchen-design-loop/review_N.json` |
| Output drawings | `/home/tstapler/Documents/711-N60th-Plans/output/kitchen/` |
| CD set | `/home/tstapler/Documents/711-N60th-Plans/260417-CD_SET_OWNER_REVIEW.pdf` |
| Pipeline command | `cd /home/tstapler/Documents/711-N60th-Plans && pixi run permit-docs` |
| Spec backups | `/home/tstapler/Documents/711-N60th-Plans/.design-loop/design_spec_backup_{ts}.py` |
| Output backups | `/home/tstapler/Documents/711-N60th-Plans/.design-loop/kitchen_output_backup_{ts}/` |

**.gitignore entry**: The `.design-loop/` directory is runtime state, not source.
It is ignored by git via `/home/tstapler/Documents/711-N60th-Plans/.gitignore`:
```
.design-loop/
```

---

## Acceptance Tests (from validation.md)

| Test | Verified by |
|---|---|
| SA-07: Loop runs ≤ 3 iterations, exits PASS | session_state["iteration"] <= 3 and status in (pass, pass_with_warnings) |
| SA-08: session_state.json has correct schema | All required keys present; iteration is int; max_iterations == 3 |
| NF-03: Unfixable FAIL → escalates, status blocked | status == "blocked", awaiting_human == true |
| NF-05: Oscillation detected, loop halts | "Oscillation" in human_escalation_reason |

---

## Related Skills

- `design:review` — full protocol at `~/.claude/skills/design-review/SKILL.md`
- `design:modify` — full protocol at `~/.claude/skills/design-modify/SKILL.md`
- `design:qa` — full protocol at `~/.claude/skills/design-qa/SKILL.md`
- `freecad-review` — Layer 1 scripts and Layer 3 dual-pass protocol
