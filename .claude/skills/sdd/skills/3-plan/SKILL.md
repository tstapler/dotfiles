---
description: "Phase 3 — Architecture + task breakdown. Outputs: project_plans/<project>/implementation/plan.md"
user-invocable: true
effort: high
allowed-tools: Read, Write, Edit, Task, AskUserQuestion
---

# sdd:3-plan

Dispatch a planning subagent to produce the implementation plan. The subagent does all the heavy work and writes plan.md directly — the coordinator (this thread) only reads the summary back.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Read all inputs (coordinator reads these to pass to subagent):**
   - `project_plans/<PROJECT_NAME>/requirements.md` — halt if missing
   - `project_plans/<PROJECT_NAME>/research/*.md` — warn if missing, continue with requirements only

2.5. **Calibrate plan depth from the Complexity field in requirements.md**:
   - **Complexity 1**: Omit Domain Glossary unless ≥2 new domain types are introduced. Mark
     Migration Plan / Observability Plan / Risk Control as "N/A — complexity 1" without
     elaboration. Dispatch only the adversarial reviewer (skip architecture-review and UX
     subagents unless requirements.md explicitly names a user-facing surface). Repair loop
     max: 2 iterations.
   - **Complexity 2**: Full plan.md template. Dispatch adversarial reviewer always; dispatch
     architecture-review only if the plan touches ≥3 files or introduces a new package/module
     boundary. UX subagent only if user-facing. Repair loop max: 3 iterations.
   - **Complexity 3–4**: Current behavior — all sections, all three reviewers, 5-iteration
     repair loops.
   - If no Complexity field found: treat as Complexity 2 (not 3-4).

3. **Dispatch a planning subagent using the `Task` tool.**

   The subagent prompt must include:
   - Full text of `requirements.md`
   - Full text of all `research/*.md` files (if present)
   - The full text of [planning-prompt.md](planning-prompt.md) (steps 0.5–6, plus the plan.md template)

4. **Wait for the subagent to complete.** Do not continue until plan.md has been written.

5. **Dispatch the reviewers called for by the step 2.5 calibration ALL IN A SINGLE PARALLEL MESSAGE using the `Task` tool.**

   > Send all applicable subagent calls in one message — do not wait for the architecture review before dispatching the adversarial reviewer or UX agent. They have no dependencies on each other.

   **Architecture Review subagent** (use `code-architecture-best-practices` as the subagent type; dispatched per calibration, not at Complexity 1 unless user-facing): prompt = full text of `plan.md` + `requirements.md` + [architecture-review-prompt.md](architecture-review-prompt.md).

   **Adversarial reviewer subagent** (always dispatched, every Complexity level): prompt = full text of `plan.md` + `requirements.md` + [adversarial-review-prompt.md](adversarial-review-prompt.md).

   **UX design subagent** (dispatched per calibration, user-facing features only — skip for pure infrastructure or non-interactive CLI tools): prompt = full text of `requirements.md` + `research/ux.md` (if present) + [ux-design-prompt.md](ux-design-prompt.md).

6. **Wait for all reviewers to complete.** Read all summaries. Then run each repair loop below independently.

   **Architecture review repair loop (MAX = the repair loop cap from step 2.5):**
   ```
   ITERATION = 0, MAX = <2 | 3 | 5, per step 2.5 calibration>
   while (architecture-review.md verdict == BLOCKED) and (ITERATION < MAX):
     ITERATION++
     1. Collect all BLOCKER findings from architecture-review.md:
        each entry = { story/task ref, violation, proposed remediation }
     2. Spawn a fresh fix subagent (lean-agent-loop pattern):
        - Provide: BLOCKER list, current plan.md, requirements.md
        - Agent: edits plan.md to resolve each BLOCKER (restructures stories/tasks,
          fixes pattern choices, corrects layer boundaries) — does NOT touch code
        - Agent returns: list of plan changes made
     3. Re-run the architecture review subagent on the updated plan.md.
        Scope its prompt to "re-review only previously BLOCKED items."
     4. Read new verdict. Remove resolved blockers from open list.

   If CONCERNS or CLEAN: proceed.
   If MAX reached with blockers remaining: stop — report "Architecture review STUCK after MAX
   iterations" with unresolved blocker list. Do not proceed to Phase 4.
   ```

   **Adversarial review repair loop (MAX = the repair loop cap from step 2.5):**
   ```
   ITERATION = 0, MAX = <2 | 3 | 5, per step 2.5 calibration>
   while (adversarial-review.md verdict == BLOCKED) and (ITERATION < MAX):
     ITERATION++
     1. Collect all BLOCKER findings from adversarial-review.md:
        each entry = { issue description, recommendation }
     2. Spawn a fresh fix subagent (lean-agent-loop pattern):
        - Provide: BLOCKER list, current plan.md, requirements.md
        - Agent: edits plan.md to address each BLOCKER (adds failure modes, error paths,
          missing stories, or removes scope drift) — does NOT touch code
        - Agent returns: list of plan changes made
     3. Re-run the adversarial reviewer subagent on the updated plan.md.
        Scope its prompt to "re-review only previously BLOCKED items."
     4. Read new verdict. Remove resolved blockers from open list.

   If CONCERNS or CLEAN: proceed.
   If MAX reached with blockers remaining: stop — report "Adversarial review STUCK after MAX
   iterations" with unresolved blocker list. Do not proceed to Phase 4.
   ```

   **UX blocker repair loop (MAX = the repair loop cap from step 2.5 — run only if UX subagent ran):**
   ```
   ITERATION = 0, MAX = <2 | 3 | 5, per step 2.5 calibration>
   while (ux.md contains flows with no exit path or missing error states) and (ITERATION < MAX):
     ITERATION++
     1. Collect UX blockers: each entry = { surface, missing element, criterion text }
     2. Spawn a fresh fix subagent (lean-agent-loop pattern):
        - Provide: UX blocker list, current ux.md, requirements.md
        - Agent: edits ux.md to add missing exit paths, error states, or broken flows
        - Agent returns: list of ux.md changes made
     3. Re-check ux.md inline: does every flow have an exit path and error handling?
     4. Remove resolved items.

   If clean: proceed.
   If MAX reached: report "UX design STUCK after MAX iterations" with unresolved flows.
   ```

   **CONCERNS or CLEAN on all three, no STUCK verdicts** → proceed.

7. **Output the coordinator summary:**
   ```
   ✅ Phase 3 complete — plan.md written to project_plans/<PROJECT_NAME>/implementation/

   Epics: <N> | Stories: <N> | Tasks: <N>
   Flagged choices: <N> (ADRs written)
   Architecture review: <BLOCKED|CONCERNS|CLEAN> — <N> blockers, <N> concerns
   Adversarial review: <BLOCKED|CONCERNS|CLEAN> — <N> blockers, <N> concerns, <N> minors
   UX design: <N surfaces, N UX acceptance criteria | N/A — no user-facing surface>

   Next step: /sdd:4-validate
   ```

   Note: No fresh session required if proceeding to Phase 4 — all planning work happened in a subagent, not this thread.
