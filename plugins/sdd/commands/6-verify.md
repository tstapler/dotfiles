---
description: "Phase 6 — Code review + test coverage hard gate before shipping."
user-invocable: true
---

# sdd:6-verify

Review the implementation for correctness and verify all acceptance criteria are met.

## HARD GATE

**Violations block progression.** Do not proceed to `/sdd:7-ship` until all issues are resolved.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Get the diff to review:**
   ```bash
   git diff main...HEAD
   ```
   If on a worktree or different base branch, adjust accordingly.

3. **Review the diff** for:
   - Correctness against `plan.md` acceptance criteria
   - Security issues (injection, auth gaps, exposed secrets)
   - Obvious performance problems
   - Missing error handling at system boundaries

4. **Verify acceptance criteria.** For each story in `plan.md`, confirm every acceptance criterion is demonstrably met in the diff.

5. **Verify validation.md test cases.** Run the test suite using the appropriate command for the stack.
   All tests in validation.md must pass. Show the output — do not claim tests pass without running them.

6. **Output the verification report:**

```
## Verification Report — <PROJECT_NAME>

### Code Review
| Area | Findings |
|------|----------|
| Correctness | ✅ All acceptance criteria met |
| Security | ⚠️ Warning: <description> |
| Error handling | ❌ Missing: <description> |

### Acceptance Criteria
| Story | Criterion | Status |
|-------|-----------|--------|
| 1.1.1 | <criterion> | ✅ |

### Test Results
Tests: <N> passed, <N> failed, <N> skipped

### Verdict
<✅ PASS — ready for /sdd:7-ship>
<❌ BLOCKED — fix N issue(s) before proceeding>
```

7. **If blocked**: list each issue with a concrete fix suggestion. Do not proceed until all violations are fixed and the review is re-run.
