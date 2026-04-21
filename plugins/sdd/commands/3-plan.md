---
description: "Phase 3 — Architecture + task breakdown. Outputs: project_plans/<project>/implementation/plan.md"
user-invocable: true
---

# sdd:3-plan

Produce a complete implementation plan grounded in the research.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Read all inputs:**
   - `project_plans/<PROJECT_NAME>/requirements.md` — halt if missing
   - `project_plans/<PROJECT_NAME>/research/*.md` — warn if missing, continue with requirements only

3. **Validate technology choices.** Extract proposed technologies from requirements + research.
   - Flag anything with known stability, licensing, or security concerns
   - For any non-standard choice, trigger `sdd:adr` before finalising the plan

4. **Write `project_plans/<PROJECT_NAME>/implementation/plan.md`:**

```markdown
# Implementation Plan: <PROJECT_NAME>

**Feature**: <one-line description>
**Date**: <YYYY-MM-DD>
**Status**: Ready for implementation
**ADRs**: <list any ADRs written, or "None">

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
- <measurable criterion>

**Files**: <exact file paths — no placeholders>

##### Task 1.1.1a: <name> (~<2-5> min)
- <exact steps>
- Files: <list>
```

   Task sizing rules:
   - Each task: 2–5 minutes of focused work
   - Max 3–5 files per task (1 primary + 2–4 supporting)
   - No placeholders — every task has exact file paths and complete code intent

5. **Write any ADRs** to `project_plans/<PROJECT_NAME>/decisions/ADR-NNN-<kebab-title>.md` for non-standard technology choices.

6. Output:
   ```
   ✅ Phase 3 complete — plan.md written to project_plans/<PROJECT_NAME>/implementation/

   Epics: <N> | Stories: <N> | Tasks: <N>

   ⚠️  OPEN A FRESH SESSION before running /sdd:4-validate or /sdd:5-implement.
       Planning context degrades implementation quality.

   Next step: /sdd:4-validate (in a fresh session)
   ```
