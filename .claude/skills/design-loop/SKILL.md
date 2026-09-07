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

On each invocation: create `.design-loop/` if missing, then either resume an
existing `session_state.json` (reporting iteration, last verdict, open issues —
and halting immediately if `awaiting_human` is set) or initialize a fresh session
with `iteration: 0`, `max_iterations: 3`, and a hash of the current spec.

Full init code, the session-state JSON schema, and the status transition table
(`in_progress` → `pass` / `pass_with_warnings` / `blocked`):
[references/session-state-management.md](references/session-state-management.md)

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

1. **Oscillation detection** — if the current spec hash was already seen in
   `spec_hashes_seen`, or `iteration >= max_iterations`, set `blocked` and halt.
   Spec hashes are recorded at the end of each successful modify step (not the
   start of the iteration) to avoid false positives on resumed sessions.
2. **design:review** — run the full protocol from
   `~/.claude/skills/design-review/SKILL.md`, writing `review_{N}.json`.
3. **Evaluate FAIL items** — build `open_issues` from `auto_fixable: true` FAILs.
   If none, skip straight to Step 5 (design:qa).
4. **design:modify** — run `~/.claude/skills/design-modify/SKILL.md` per FAIL
   item, with no-progress detection (same item + same proposed value as the
   prior iteration → mark `CANNOT_AUTO_FIX` instead of retrying). A pipeline
   failure or infeasible constraint sets `blocked` and exits the loop.
5. **design:qa** — run `~/.claude/skills/design-qa/SKILL.md` for the final verdict.
6. **Evaluate QA verdict** — PASS/PASS_WITH_WARNINGS exits with success; BLOCKED
   exits and escalates; FAIL increments `iteration` and loops back to Step 1.

Full code for every step above (oscillation check, review/modify/qa invocation
sequences, verdict handling) is in
[references/main-loop-steps.md](references/main-loop-steps.md).

---

## Phase 2: Exit Report

On PASS or PASS_WITH_WARNINGS, print the exit report (changes made, resolved
issues, remaining open issues, CANNOT_VERIFY items) and a git commit instruction.
On BLOCKED, print the escalation summary and the human action needed before
re-running the loop.

Full exit report template, the session log entry format, the project file paths
table, and the acceptance test table:
[references/exit-and-logging.md](references/exit-and-logging.md)

---

## Related Skills

- `design:review` — full protocol at `~/.claude/skills/design-review/SKILL.md`
- `design:modify` — full protocol at `~/.claude/skills/design-modify/SKILL.md`
- `design:qa` — full protocol at `~/.claude/skills/design-qa/SKILL.md`
- `freecad-review` — Layer 1 scripts and Layer 3 dual-pass protocol
