# QA Report Format, Session State Update, and Acceptance Tests

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

## Acceptance Tests (from validation.md)

| Test | Pass criterion |
|---|---|
| SA-05: PASS_WITH_WARNINGS after south aisle fix | `last_qa_verdict == "PASS_WITH_WARNINGS"`, `island_south_aisle` in `resolved_issues`, `cannot_verify` non-empty, no open FAIL items |
| SA-06: Fresh compliance JSON (no stale cache) | `compliance_layer1.json` mtime > stale mtime written in test setup |
| NF-06: FAIL verdict on unmodified spec | `last_qa_verdict == "FAIL"` |
