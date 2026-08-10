---
description: "Phase 4 — Map test coverage to requirements + run pre-mortem before writing any code. Outputs: validation.md + pre-mortem.md in project_plans/<project>/implementation/"
user-invocable: true
effort: high
allowed-tools: Read, Write, Edit, Task, AskUserQuestion
---

# sdd:4-validate

Dispatch a validation subagent to design the test suite. The subagent writes validation.md directly — the coordinator (this thread) only reads the summary back.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Read inputs (coordinator reads these to pass to subagent):**
   - `project_plans/<PROJECT_NAME>/implementation/plan.md` — halt if missing, run `/sdd:3-plan` first
   - `project_plans/<PROJECT_NAME>/requirements.md`
   - `project_plans/<PROJECT_NAME>/design/ux.md` — if present, include in subagent prompt for UX acceptance test design; skip if absent

2.5. **Calibrate validation depth from the Complexity field in requirements.md**:
   - **Complexity 1**: Dispatch the validation subagent only (1 test per requirement, skip the
     unit+error+integration triad). Skip pre-mortem and cross-artifact-consistency subagents.
     Skip the Product Triad Review gate (step 6).
   - **Complexity 2**: Dispatch validation + pre-mortem. Skip cross-artifact-consistency unless
     both design/ux.md and plan.md exist (terminology drift only matters with ≥2 artifacts to
     drift between). Triad review still runs.
   - **Complexity 3–4**: Current behavior — all three subagents + triad review.
   - If no Complexity field found: treat as Complexity 2.

3. **Dispatch subagents per the calibration above in a single parallel message using the `Task` tool** (at Complexity 3-4, all three: the validation subagent, the pre-mortem subagent, AND the cross-artifact consistency subagent).

   > Send all three calls in one message — they are independent and share only the plan.md / requirements.md inputs.

   **Validation subagent** (always dispatched): prompt = full text of `plan.md` + `requirements.md` + [validation-prompt.md](validation-prompt.md) (steps + validation.md template).

   **Pre-mortem subagent** (dispatched per calibration, Complexity 2+): prompt = full text of `plan.md` + `requirements.md` + [pre-mortem-prompt.md](pre-mortem-prompt.md).

   **Cross-artifact consistency subagent** (dispatched per calibration): prompt = full text of `requirements.md` + `plan.md` + `design/ux.md` (if present) + [cross-artifact-consistency-prompt.md](cross-artifact-consistency-prompt.md).

4. **Wait for all dispatched subagents to complete.** Do not continue until validation.md has been written, and pre-mortem.md/the consistency subagent's findings are in (whichever ran per the calibration).

   **Handle consistency findings**: If the consistency subagent returned any BLOCKERs:
   - Patch plan.md to resolve each blocker (add missing stories; clarify scope; align terminology in the Domain Glossary).
   - Note CONCERNs and NITPICKs in the coordinator summary but do not block on them.

5. **Run the implementation readiness gate.**

   Inline check — no subagent needed. Read the following files:
   - `project_plans/<PROJECT_NAME>/requirements.md`
   - `project_plans/<PROJECT_NAME>/implementation/plan.md`
   - `project_plans/<PROJECT_NAME>/implementation/validation.md`
   - `project_plans/<PROJECT_NAME>/implementation/adversarial-review.md` (if present)

   Check each criterion:

   | # | Criterion | Pass? |
   |---|-----------|-------|
   | 1 | Every requirement in requirements.md has ≥1 test case in validation.md | |
   | 2 | plan.md has no TODO/TBD placeholders in architecture or task sections | |
   | 3 | All ADRs referenced in plan.md exist on disk | |
   | 4 | No BLOCKER items remain in adversarial-review.md (or file is absent) | |
   | 5 | No BLOCKER items remain in architecture-review.md (or file is absent) | |
   | 6 | For schema changes: Migration Plan section in plan.md defines reversibility + zero-downtime strategy | |
   | 7 | No P1 items remain open in pre-mortem.md (or file is absent) | |

   Verdict:
   - **PASS** — all criteria met → output summary and proceed.
   - **CONCERNS** — criteria 2–3 have minor gaps → ask with `AskUserQuestion`: "Proceed despite gaps, or fix first?" Halt if user chooses to fix.
   - **FAIL** — criterion 1, 4, or 7 not met → halt with a clear list of what's missing. For pre-mortem P1 items: patch plan.md with the prevention from pre-mortem.md, then proceed. User must resolve before running `/sdd:5-implement`.

6. **Run the Product Triad Review gate** (skip entirely at Complexity 1, per step 2.5).

   Invoke `/pm:triad-review <PROJECT_NAME>` inline (do not skip — it catches UX and PM gaps that engineering-only review misses).

   - If verdict is **READY TO BUILD** → proceed.
   - If verdict is **NEEDS WORK** → run the triad repair loop (max 3 iterations):
     ```
     ITERATION = 0, MAX = 3
     while (verdict == NEEDS WORK) and (ITERATION < MAX):
       ITERATION++
       1. Collect all blocker items from the triad review result:
          each entry = { leg (PM/UX/Eng), issue, recommendation }
       2. Spawn a fresh fix subagent (lean-agent-loop pattern):
          - Provide: blocker list, current plan.md, requirements.md, ux.md (if present)
          - Agent: patches plan.md to address PM/Eng gaps; patches ux.md for UX gaps
          - Agent returns: list of changes made
       3. Re-run `/pm:triad-review <PROJECT_NAME>` on the updated artifacts.
       4. Read new verdict. Remove resolved items.

     If READY TO BUILD: proceed.
     If MAX reached: stop — report "Triad Review STUCK after 3 iterations" with
     unresolved items. Do not proceed to Phase 5 without human sign-off.
     ```
   - If verdict is **NOT READY** → halt. Return to the weakest leg: PM gap → re-run `/sdd:1-ideate`; UX gap → run `/ux:design <PROJECT_NAME>`; Engineering gap → patch `plan.md`.

7. **Output the coordinator summary:**
   ```
   ✅ Phase 4 complete — validation.md written to project_plans/<PROJECT_NAME>/implementation/

   Test cases designed: <N> unit, <N> integration, <N> UX acceptance
   Requirements covered: <N>/<N>
   UX criteria covered: <N>/<N> (or N/A)
   Pre-mortem: <N> P1, <N> P2, <N> P3 — top risk: <one sentence>
   Consistency: <N> blockers fixed, <N> concerns noted, <N> nitpicks
   Readiness gate: <PASS|CONCERNS|FAIL>
   Triad review: <READY TO BUILD|NEEDS WORK|NOT READY>

   Next step: /sdd:5-implement
   ```

   Note: If phases 2–4 all ran as subagents (e.g. via `/sdd:full`), no fresh session is required. If you ran phases 1–4 inline in this thread, open a fresh session before `/sdd:5-implement`.
