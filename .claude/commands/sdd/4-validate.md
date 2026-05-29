---
description: "Phase 4 — Map test coverage to requirements before writing a line of code. Outputs: project_plans/<project>/implementation/validation.md"
user-invocable: true
---

# sdd:4-validate

Dispatch a validation subagent to design the test suite. The subagent writes validation.md directly — the coordinator (this thread) only reads the summary back.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Read inputs (coordinator reads these to pass to subagent):**
   - `project_plans/<PROJECT_NAME>/implementation/plan.md` — halt if missing, run `/sdd:3-plan` first
   - `project_plans/<PROJECT_NAME>/requirements.md`

3. **Dispatch a validation subagent using the `Agent` tool.**

   The subagent prompt must include:
   - Full text of `plan.md`
   - Full text of `requirements.md`
   - These exact instructions:

   > You are a validation subagent for Stapler-Driven Development. Design the test suite before any code is written.
   >
   > **Step 1:** For each requirement, design: 1 unit test (happy path), 1 unit test (error path), 1 integration test (if data store or external call involved).
   >
   > **Step 2:** Name tests descriptively: `methodName_should_ExpectedBehavior_When_Condition` (or equivalent for the target language/framework).
   >
   > **Step 3:** Write `project_plans/<PROJECT_NAME>/implementation/validation.md` following the template below.
   >
   > **Step 4:** Return a summary: test case counts by type, requirements coverage fraction.

   Validation template:
   ```markdown
   # Validation Plan: <PROJECT_NAME>

   **Date**: <YYYY-MM-DD>

   ## Requirement → Test Mapping

   | Requirement | Test File | Test Name | Type | Scenario |
   |-------------|-----------|-----------|------|----------|
   | REQ-1: <desc> | <TestFile> | <test name> | Unit | Happy path |
   | REQ-1: <desc> | <TestFile> | <test name> | Unit | Error path |
   | REQ-1: <desc> | <TestFile> | <test name> | Integration | <description> |

   ## Test Stack
   - **Unit**: <framework + assertion library>
   - **Integration**: <framework + test doubles>
   - **API/E2E**: <framework if applicable>

   ## Coverage Targets
   - Unit test coverage: ≥80% (line)
   - All public service methods: happy path + error paths
   - All external integrations: unit mocked + at least one integration test
   ```

4. **Wait for the subagent to complete.** Do not continue until validation.md has been written.

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

   Verdict:
   - **PASS** — all criteria met → output summary and proceed.
   - **CONCERNS** — criteria 2–3 have minor gaps → ask with `AskUserQuestion`: "Proceed despite gaps, or fix first?" Halt if user chooses to fix.
   - **FAIL** — criterion 1 or 4 not met → halt with a clear list of what's missing. User must resolve before running `/sdd:5-implement`.

6. **Output the coordinator summary:**
   ```
   ✅ Phase 4 complete — validation.md written to project_plans/<PROJECT_NAME>/implementation/

   Test cases designed: <N> unit, <N> integration
   Requirements covered: <N>/<N>
   Readiness gate: <PASS|CONCERNS|FAIL>

   Next step: /sdd:5-implement
   ```

   Note: If phases 2–4 all ran as subagents (e.g. via `/sdd:full`), no fresh session is required. If you ran phases 1–4 inline in this thread, open a fresh session before `/sdd:5-implement`.
