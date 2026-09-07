# Phase 2: Exit Report, Session Log, File Paths, and Acceptance Tests

## Loop exit report format

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

## Session Log Format

Each entry appended to `.design-loop/session_log.md`:

```
## Iteration N — {phase} — {ISO8601 timestamp}

### Phase: {review | modify | qa}
{phase-specific content}
```

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

## Acceptance Tests (from validation.md)

| Test | Verified by |
|---|---|
| SA-07: Loop runs ≤ 3 iterations, exits PASS | session_state["iteration"] <= 3 and status in (pass, pass_with_warnings) |
| SA-08: session_state.json has correct schema | All required keys present; iteration is int; max_iterations == 3 |
| NF-03: Unfixable FAIL → escalates, status blocked | status == "blocked", awaiting_human == true |
| NF-05: Oscillation detected, loop halts | "Oscillation" in human_escalation_reason |
