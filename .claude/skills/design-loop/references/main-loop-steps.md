# Phase 1: Main Loop (max 3 iterations) — Full Step Detail

```
LOOP iterations 0 through max_iterations-1:
  1. Oscillation check
  2. design:review
  3. Evaluate FAIL items
  4. design:modify (if FAIL items exist)
  5. design:qa
  6. Evaluate QA verdict → EXIT or continue
```

## Step 1: Oscillation detection (start of each iteration)

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

## Step 2: Execute design:review protocol

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

## Step 3: Evaluate FAIL items

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

## Step 4: Execute design:modify for each FAIL item

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

## Step 5: Execute design:qa protocol

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

## Step 6: Evaluate QA verdict and decide loop action

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
