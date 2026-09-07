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

## Steps 1–5: Fresh Compliance Run

Full exact commands and code for each step are in
[references/compliance-steps.md](references/compliance-steps.md). Summary:

1. **Cache invalidation** (unconditional) — delete `/tmp/compliance_layer1.json`
   and `/tmp/clearances.json` before every run, from loop or direct invocation.
2. **Fresh Layer 1 run** — re-run `extract_clearances.py` and `check_compliance.py`;
   verify the resulting JSON is newer than `design_spec.py`'s mtime (staleness guard).
3. **Compare against pre-modify baseline** — load the prior `review_N.json`,
   classify each item as resolved / persisting / regression.
   - **Regression rule**: any previously-PASS item now FAIL → BLOCKED immediately.
   - **No-progress rule**: zero resolved items by iteration 2 or 3 → BLOCKED.
4. **Output freshness check** — all 5 expected PDFs must exist with mtime newer
   than `design_spec.py` (a hallucinated-PASS guard). Missing or stale → BLOCKED.
5. **Visual QA for changed drawings** — rasterize and zone-check any drawing with
   a changed element; any `confidence: LOW` result caps the verdict at
   PASS_WITH_WARNINGS.

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

## Step 7: Session State, Report, and Acceptance Tests

After the verdict is determined, update `session_state.json` and `session_log.md`,
then print the QA report. Full code, the report template, and the acceptance test
table are in [references/output-and-acceptance-tests.md](references/output-and-acceptance-tests.md).

---

## Related Skills

- `design:review` — full compliance review; produces the baseline JSON that QA compares against
- `design:modify` — applies spec changes that QA verifies
- `design:loop` — orchestrates review → modify → QA in a capped cycle
- `freecad-review` — Layer 1 compliance scripts (`extract_clearances.py`, `check_compliance.py`)
