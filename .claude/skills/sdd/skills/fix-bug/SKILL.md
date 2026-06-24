---
description: Maintenance shortcut — pick highest priority bug, find root cause, fix, verify
user-invocable: true
---

# sdd:fix-bug

Three-phase maintenance workflow: root cause → fix → verify.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — verify prerequisites.

2. **Select the bug.** If an argument is provided, use it. Otherwise scan `docs/bugs/open/` and select the highest priority open bug.

3. **Phase A — Root cause (do not skip).**

   **Iron Law: No fix without root cause investigation first. Symptom fixes are failure.**

   Before proposing any fix:
   - Read the full error, stack trace, and surrounding context
   - Reproduce the failure locally or identify the exact condition that triggers it
   - Check recent commits for related changes (`git log --oneline -20`)
   - Form a hypothesis: "The root cause is X because Y"

4. **Phase B — Fix.**

   - Fix the root cause, not the symptom
   - Write a regression test that would have caught this bug

5. **Phase C — Verify.**

   **Iron Law: No completion claim without running the test and showing the output.**

   Run the relevant test(s) using the appropriate test command for the stack.
   Show the full output. Only claim the bug is fixed after seeing green.

6. **Update the bug document** in `docs/bugs/open/` → move to `docs/bugs/resolved/`.

7. Output:
   ```
   ✅ Bug fixed and verified

   Root cause: <one sentence>
   Fix: <one sentence>
   Regression test: <test name>
   ```
