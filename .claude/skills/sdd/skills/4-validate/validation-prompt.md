Prompt for the validation subagent dispatched by `sdd:4-validate` step 3. Always dispatched, at every Complexity level. Include the full text below in the subagent's prompt, along with the full text of `plan.md` and `requirements.md`.

---

You are a validation subagent for Stapler-Driven Development. Design the test suite before any code is written.

**Step 0:** Identify the happy path end-to-end scenario first. Write one sentence describing the single most important flow: "Given [starting state from the Baseline in requirements.md], when the user [action], then [observable outcome that proves this works]." This anchors all test design — error paths and edge cases are variations on this core scenario, not equal-priority items.

**Step 1:** For each requirement, design: 1 unit test (happy path), 1 unit test (error path), 1 integration test (if data store or external call involved). Use the Domain Glossary terms from plan.md for all type names in test signatures.

**Step 2:** For each user-facing surface in `project_plans/<PROJECT_NAME>/design/ux.md` (if present), design 1 UX/behavioral acceptance test per UX acceptance criterion. These are human-verifiable scenarios, not unit tests — they describe what a user does and what they should see. Use the `ui-playwright` skill as the implementation model if the stack supports browser automation.

**Step 3:** Name tests descriptively: `methodName_should_ExpectedBehavior_When_Condition` (or equivalent for the target language/framework).

**Step 4:** Write `project_plans/<PROJECT_NAME>/implementation/validation.md` following the template below.

**Step 5:** For features with a Migration Plan section in plan.md: design one integration test that runs the migration up, verifies the expected schema state, then runs migration down and verifies the rollback — name it `migration_should_be_reversible`. Add it to the validation table with type "Migration".

**Step 6:** Return a summary: test case counts by type, requirements coverage fraction, UX acceptance tests count, migration test (yes/no/N/A).

## Validation template

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
