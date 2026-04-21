---
description: "Phase 4 — Map test coverage to requirements before writing a line of code. Outputs: project_plans/<project>/implementation/validation.md"
user-invocable: true
---

# sdd:4-validate

Design the test suite against requirements before implementation begins.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Read inputs:**
   - `project_plans/<PROJECT_NAME>/implementation/plan.md` — halt if missing, run `/sdd:3-plan` first
   - `project_plans/<PROJECT_NAME>/requirements.md`

3. **For each requirement in requirements.md**, design at minimum:
   - One unit test (happy path)
   - One unit test (error/exception path)
   - One integration test (if data store or external call involved)

4. **Write `project_plans/<PROJECT_NAME>/implementation/validation.md`:**

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

5. Output:
   ```
   ✅ Phase 4 complete — validation.md written to project_plans/<PROJECT_NAME>/implementation/

   Test cases designed: <N> unit, <N> integration
   Requirements covered: <N>/<N>

   ⚠️  OPEN A FRESH SESSION before implementing.
       Planning context degrades implementation quality.

   Next step: /sdd:5-implement (in a fresh session — bring plan.md + validation.md)
   ```
