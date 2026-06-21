---
description: "Phase 5 — Execute plan via parallel worker subagents. START IN A FRESH SESSION."
user-invocable: true
---

# sdd:5-implement

Execute the implementation plan using parallel worker subagents dispatched directly from this thread.

## ⚠️ FRESH SESSION REQUIRED

If this session was used for planning (ideate/research/plan/validate), **stop now**.
Close this session and open a new one, then run `/sdd:5-implement` again.
Planning context degrades code generation quality — this is not optional.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME and REPO_ROOT.

2. **Read required inputs** — halt with a clear error message if any are missing:
   - `project_plans/<PROJECT_NAME>/implementation/plan.md`
   - `project_plans/<PROJECT_NAME>/implementation/validation.md`
   - `project_plans/<PROJECT_NAME>/design/ux.md` (optional — include if present)

3. **Read the dependency visualization** in plan.md. Identify which epics can run concurrently:
   - Epics with **no shared file writes** can run in the same parallel batch
   - Epics that write to the same file as another epic must run sequentially
   - Use the ASCII dependency diagram in plan.md as the authoritative source — do not re-derive it

4. **Dispatch all independent epics in a single parallel message** using the `Agent` tool.

   Each worker agent receives this prompt template (fill in for each epic):

   > You are implementing Epic `<N>` of the `<PROJECT_NAME>` implementation plan.
   >
   > **Inputs — read these files at the start:**
   > - `project_plans/<PROJECT_NAME>/implementation/plan.md` — read Epic `<N>` and its stories/tasks only
   > - `project_plans/<PROJECT_NAME>/implementation/validation.md` — read the test cases for stories in this epic
   > - `project_plans/<PROJECT_NAME>/design/ux.md` — read if this epic contains user-facing stories (skip otherwise)
   >
   > **For each task in this epic:**
   > 1. Implement the task — exact files listed in plan.md
   > 2. Write the corresponding tests from validation.md (use the pre-designed test names exactly)
   > 3. Run the tests for these specific files only — show output
   > 4. Fix any failures before moving to the next task
   >
   > **Do NOT implement other epics.** Do NOT modify files outside the task's listed files.
   >
   > **Return:**
   > - Tasks completed (N/N)
   > - Test results (N passing, N failing)
   > - Any warnings or gaps found

5. **Wait for all parallel workers to complete.** Do not start the next batch until all current workers have returned.

   **Worker failure recovery**:
   - If a worker returns with failing tests: dispatch a fresh fix agent with the exact failure output. Re-run the failing tests to verify. Max 2 fix cycles per worker — if still failing after 2 cycles:
     1. **Diagnose root cause type**: Is this an implementation bug (wrong logic, missing case) or a planning error (plan assumed an incorrect API, wrong dependency, or infeasible approach)?
     2. **If a planning error**: propose a specific plan patch via `AskUserQuestion`: "Worker for Epic N is blocked after 2 fix cycles. Root cause: [diagnosis]. Proposed plan change: [specific amendment to plan.md]. Approve and apply, or take manual control?" Apply only if user approves.
     3. **If an implementation bug or unclear**: escalate the raw error to the user.
   - If a worker crashes mid-task (no return): re-dispatch the same worker prompt. The worker will re-read plan.md and pick up from where files are missing.

6. **Dispatch the next wave** for any remaining epics that are now unblocked (their dependencies completed in the previous batch). Repeat until all epics are done.

7. **Spec compliance sweep** — after all epics complete, dispatch a single spec compliance agent:

   > Read `project_plans/<PROJECT_NAME>/implementation/plan.md` and `project_plans/<PROJECT_NAME>/implementation/validation.md`.
   > Run `git diff main...HEAD`.
   > For each story acceptance criterion in plan.md, verify it is satisfied in the diff.
   > For each test name in validation.md, verify the test exists in the diff.
   > Return: criteria met (N/N), tests present (N/N), gaps found.

   If gaps are found: dispatch targeted fix agents (one per gap, in parallel). Re-run the spec sweep after fixes. Max 2 sweep cycles — escalate remaining gaps to the user if not resolved.

8. **Output the Phase 5 summary:**
   ```
   ✅ Phase 5 complete

   Epics completed: <N>/<N>
   Tasks completed: <N>/<N>
   Tests: <N> passing, <N> failing
   Spec criteria met: <N>/<N>
   Gaps fixed: <N>
   Escalated to user: <N> (list below)

   Warnings: <list or "none">

   Next step: /sdd:6-verify
   ```
