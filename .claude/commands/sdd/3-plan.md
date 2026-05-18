---
description: "Phase 3 — Architecture + task breakdown. Outputs: project_plans/<project>/implementation/plan.md"
user-invocable: true
---

# sdd:3-plan

Dispatch a planning subagent to produce the implementation plan. The subagent does all the heavy work and writes plan.md directly — the coordinator (this thread) only reads the summary back.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Read all inputs (coordinator reads these to pass to subagent):**
   - `project_plans/<PROJECT_NAME>/requirements.md` — halt if missing
   - `project_plans/<PROJECT_NAME>/research/*.md` — warn if missing, continue with requirements only

3. **Dispatch a planning subagent using the `Task` tool.**

   The subagent prompt must include:
   - Full text of `requirements.md`
   - Full text of all `research/*.md` files (if present)
   - These exact instructions:

   > You are a planning subagent for Stapler-Driven Development. Produce a complete implementation plan.
   >
   > **Step 1:** Review the requirements and research. Identify the type of system being built.
   >
   > **Step 2:** Validate technology choices. Flag anything with known stability, licensing, or security concerns. Write an ADR stub for any non-standard choices.
   >
   > **Step 3:** Write `project_plans/<PROJECT_NAME>/implementation/plan.md` following the template below. Use exact file paths — no placeholders. Task sizing: 2–5 minutes each, max 3–5 files per task.
   >
   > **Step 4:** Write any ADRs to `project_plans/<PROJECT_NAME>/decisions/ADR-NNN-<kebab-title>.md`.
   >
   > **Step 5:** Return a summary: epic count, story count, task count, any flagged choices.

   Plan template:
   ```markdown
   # Implementation Plan: <PROJECT_NAME>

   **Feature**: <one-line description>
   **Date**: <YYYY-MM-DD>
   **Status**: Ready for implementation
   **ADRs**: <list or "None">

   ---

   ## Dependency Visualization
   [ASCII diagram showing task dependencies]

   ---

   ## Phase 1: <name>
   ### Epic 1.1: <name>
   **Goal**: <what this epic achieves>

   #### Story 1.1.1: <name>
   **As a** <role>, **I want** <capability>, **so that** <value>.
   **Acceptance Criteria**:
   - <measurable criterion>
   **Files**: <exact file paths>

   ##### Task 1.1.1a: <name> (~<2-5> min)
   - <exact steps>
   - Files: <list>
   ```

4. **Wait for the subagent to complete.** Do not continue until plan.md has been written.

5. **Dispatch an adversarial reviewer subagent using the `Task` tool.**

   The subagent prompt must include:
   - Full text of `plan.md`
   - Full text of `requirements.md`
   - These exact instructions:

   > You are an adversarial architecture reviewer. Your job is to challenge this implementation plan and find weaknesses before any code is written.
   >
   > Review for:
   > 1. **Missing failure modes** — What happens when external dependencies fail? Are error paths, retries, or timeouts absent?
   > 2. **Architecture risks** — Are there components that will be hard to change, scale, or test in isolation?
   > 3. **Scope drift** — Are any tasks broader than their stated requirement? Is anything being built that wasn't asked for?
   > 4. **Technology bets** — Are there non-standard choices that could become liabilities (licensing, abandonment, performance)?
   > 5. **Missing coverage** — Are there user-facing behaviors implied by requirements that have no corresponding story or task?
   >
   > For each concern, classify as:
   > - **BLOCKER** — Must be resolved before implementation starts
   > - **CONCERN** — Should be addressed; will degrade quality if skipped
   > - **MINOR** — Low impact; note it but don't block
   >
   > Write your findings to `project_plans/<PROJECT_NAME>/implementation/adversarial-review.md` using this template:
   >
   > ```markdown
   > # Adversarial Review: <PROJECT_NAME>
   >
   > **Date**: <YYYY-MM-DD>
   > **Verdict**: BLOCKED / CONCERNS / CLEAN
   >
   > ## Blockers
   > - [ ] <issue> — <recommendation>
   >
   > ## Concerns
   > - [ ] <issue> — <recommendation>
   >
   > ## Minors
   > - <issue>
   > ```
   >
   > Return a one-line summary: verdict + count of blockers/concerns/minors.

6. **Wait for the adversarial reviewer to complete.** Read the summary.

   - **BLOCKED** → read adversarial-review.md, patch plan.md to resolve each BLOCKER, then re-run the adversarial reviewer on the updated plan (repeat until CONCERNS or CLEAN).
   - **CONCERNS or CLEAN** → proceed.

7. **Output the coordinator summary:**
   ```
   ✅ Phase 3 complete — plan.md written to project_plans/<PROJECT_NAME>/implementation/

   Epics: <N> | Stories: <N> | Tasks: <N>
   Flagged choices: <N> (ADRs written)
   Adversarial review: <BLOCKED|CONCERNS|CLEAN> — <N> blockers, <N> concerns, <N> minors

   Next step: /sdd:4-validate
   ```

   Note: No fresh session required if proceeding to Phase 4 — all planning work happened in a subagent, not this thread.
