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

3. **Dispatch THREE subagents in a single parallel message using the `Task` tool: the validation subagent, the pre-mortem subagent, AND the cross-artifact consistency subagent.**

   > Send all three calls in one message — they are independent and share only the plan.md / requirements.md inputs.

   **Validation subagent** — subagent prompt must include:
   - Full text of `plan.md`
   - Full text of `requirements.md`
   - These exact instructions:

   > You are a validation subagent for Stapler-Driven Development. Design the test suite before any code is written.
   >
   > **Step 0:** Identify the happy path end-to-end scenario first. Write one sentence describing the single most important flow: "Given [starting state from the Baseline in requirements.md], when the user [action], then [observable outcome that proves this works]." This anchors all test design — error paths and edge cases are variations on this core scenario, not equal-priority items.
   >
   > **Step 1:** For each requirement, design: 1 unit test (happy path), 1 unit test (error path), 1 integration test (if data store or external call involved). Use the Domain Glossary terms from plan.md for all type names in test signatures.
   >
   > **Step 2:** For each user-facing surface in `project_plans/<PROJECT_NAME>/design/ux.md` (if present), design 1 UX/behavioral acceptance test per UX acceptance criterion. These are human-verifiable scenarios, not unit tests — they describe what a user does and what they should see. Use the `ui-playwright` skill as the implementation model if the stack supports browser automation.
   >
   > **Step 3:** Name tests descriptively: `methodName_should_ExpectedBehavior_When_Condition` (or equivalent for the target language/framework).
   >
   > **Step 4:** Write `project_plans/<PROJECT_NAME>/implementation/validation.md` following the template below.
   >
   > **Step 5:** For features with a Migration Plan section in plan.md: design one integration test that runs the migration up, verifies the expected schema state, then runs migration down and verifies the rollback — name it `migration_should_be_reversible`. Add it to the validation table with type "Migration".
   >
   > **Step 6:** Return a summary: test case counts by type, requirements coverage fraction, UX acceptance tests count, migration test (yes/no/N/A).

   Validation template:
   ```markdown
   # Validation Plan: <PROJECT_NAME>

   **Date**: <YYYY-MM-DD>

   ## Happy Path Scenario
   Given [baseline state from requirements.md], when [user action], then [observable outcome that proves the feature works]. *(One sentence — the anchor for all test design below.)*

   ## Requirement → Test Mapping

   | Requirement | Test File | Test Name | Type | Scenario |
   |-------------|-----------|-----------|------|----------|
   | REQ-1: <desc> | <TestFile> | <test name> | Unit | Happy path |
   | REQ-1: <desc> | <TestFile> | <test name> | Unit | Error path |
   | REQ-1: <desc> | <TestFile> | <test name> | Integration | <description> |

   ## UX Acceptance Tests
   (Complete this section only for user-facing features; omit for pure infrastructure.)

   | UX Criterion | Test File | Test Name | Tool | Steps |
   |---|---|---|---|---|
   | User completes <task> in ≤N steps | <e2e file> | <test name> | Playwright / manual | <user flow> |
   | Error state shows correct message | <e2e file> | <test name> | Playwright / manual | <error trigger + assertion> |
   | No dead ends — all errors have exit | manual | <scenario> | Manual | <steps> |
   | Keyboard navigable | manual | <scenario> | Manual | <tab order check> |

   ## Test Stack
   - **Unit**: <framework + assertion library>
   - **Integration**: <framework + test doubles>
   - **E2E / UX**: <Playwright / Cypress / manual checklist>

   ## Coverage Targets and How to Measure

   | Stack | Coverage command | Target |
   |---|---|---|
   | Go | `go test ./... -coverprofile=coverage.out && go tool cover -func=coverage.out` | ≥80% line |
   | TypeScript/Jest | `npx jest --coverage --coverageThreshold='{"global":{"lines":80}}'` | ≥80% line |
   | Kotlin/JVM | `./gradlew jacocoTestReport` → check `build/reports/jacoco/` | ≥80% line |
   | Java/Maven | `./mvnw jacoco:report` → check `target/site/jacoco/` | ≥80% line |
   | Rust | `cargo tarpaulin --out Stdout` | ≥80% line |

   - All public service methods: happy path + error paths covered
   - All external integrations: unit mocked + at least one integration test
   - UX acceptance criteria: each criterion in design/ux.md has a corresponding test or manual step
   ```

   **Pre-mortem subagent** — subagent prompt must include:
   - Full text of `plan.md`
   - Full text of `requirements.md`
   - These exact instructions:

   > You are a pre-mortem subagent for Stapler-Driven Development. Imagine this project has already shipped and failed.
   >
   > **Step 1:** List the 5 most plausible failure modes — things that would cause the project to ship but not solve the problem, or to break in production within the first month. Think adversarially: what assumption in the plan is most likely wrong?
   >
   > **Step 2:** For each failure mode:
   > - **Failure**: one sentence describing what went wrong
   > - **First symptom**: the earliest observable signal that this failure is happening (what a user or monitor would see)
   > - **Prevention**: one concrete change to plan.md, validation.md, or the implementation approach that would prevent or detect this
   > - **Severity**: P1 (likely AND catastrophic), P2 (likely but recoverable), or P3 (unlikely but catastrophic)
   >
   > **Step 3:** Write `project_plans/<PROJECT_NAME>/implementation/pre-mortem.md` using this template:
   > ```markdown
   > # Pre-mortem: <PROJECT_NAME>
   > **Date**: <YYYY-MM-DD>
   >
   > ## Failure Modes
   >
   > | # | Failure | First Symptom | Prevention | Severity |
   > |---|---------|--------------|------------|----------|
   > | 1 | <failure> | <symptom> | <prevention> | P1/P2/P3 |
   >
   > ## P1 Items (address before implementation)
   > - [ ] <failure #N> — <specific plan change needed>
   > ```
   >
   > **Step 4:** Return a summary: count of P1/P2/P3 items, top failure mode in one sentence.

   **Cross-artifact consistency subagent** — subagent prompt must include:
   - Full text of `requirements.md`
   - Full text of `plan.md`
   - Full text of `design/ux.md` (if present)
   - These exact instructions:

   > You are a cross-artifact consistency checker for Stapler-Driven Development. Check four areas:
   >
   > **1. Coverage gaps** — Every requirement in `## Scope → In Scope` of requirements.md must have ≥1 story in plan.md and will need ≥1 test. List any requirements with no corresponding story.
   >
   > **2. Scope drift** — Any story in plan.md that has no corresponding requirement in requirements.md is potential scope creep. List these.
   >
   > **3. UX-Plan misalignment** — Any user-facing surface described in ux.md that has no corresponding story or task in plan.md. List these.
   >
   > **4. Terminology drift** — Terms used differently across artifacts (e.g., plan.md calls it "UserProfile" but ux.md calls it "Account"). List mismatches — these will cause the Domain Glossary's ubiquitous language to diverge in implementation.
   >
   > **5. Direct contradictions** — Any statement in one artifact that directly contradicts another (e.g., requirements.md says "no PII stored" but plan.md includes a user profile DB table with personal fields).
   >
   > For each finding: which two artifacts conflict, severity (**BLOCKER** for contradictions and coverage gaps / **CONCERN** for scope drift and terminology / **NITPICK** for UX alignment), and a one-sentence resolution.
   >
   > **Do NOT write any files.** Return your findings as the response.
   >
   > Return a 2-line summary: total findings (N blockers, N concerns, N nitpicks) + the single highest-severity finding in one sentence.

4. **Wait for all three subagents to complete.** Do not continue until validation.md and pre-mortem.md have been written, and the consistency subagent has returned.

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

6. **Run the Product Triad Review gate.**

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
