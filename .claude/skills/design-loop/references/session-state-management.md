# Phase 0: Session State Initialization

## 0a: Create .design-loop directory

```bash
mkdir -p /home/tstapler/Documents/711-N60th-Plans/.design-loop
```

## 0b: Check for existing session

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

## 0c: Session state schema reference

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

## State transition rules

| From status | Trigger | To status |
|---|---|---|
| `in_progress` | QA returns PASS | `pass` |
| `in_progress` | QA returns PASS_WITH_WARNINGS | `pass_with_warnings` |
| `in_progress` | QA returns BLOCKED or pipeline fails | `blocked` |
| `in_progress` | iteration reaches max_iterations | `blocked` |
| `in_progress` | oscillation detected | `blocked` |
| `blocked` | human resolves escalation, re-runs loop | `in_progress` (fresh session) |
