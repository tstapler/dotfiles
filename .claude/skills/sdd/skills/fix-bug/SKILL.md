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

6. **Phase D — Reflect (fix the class, not the instance).**

   A regression test proves *this* bug won't come back. It doesn't prove the *shape* of bug
   won't recur elsewhere. Before closing out, apply the `quality:reflect-and-fix` taxonomy to
   the root cause you found in Phase A:

   - Classify it: Semantic/Intent, Framework Pattern Misuse, API Contract Gap, Type Safety
     Gap, Integration Gap, or Dependency/Build Gap.
   - Ask: what's the *earliest* point on the enforcement ladder (compile-time type →
     lint/static → unit test → integration test → checklist) that would have caught this?
     If the Phase B regression test is already the earliest achievable level, say so and move
     on — don't manufacture enforcement for its own sake.
   - If a type change, lint rule, or ast-grep/semgrep pattern could have caught it earlier
     than a runtime test, implement that too (invoke `quality:reflect-and-fix` for the full
     4-phase version if the bug is non-trivial; apply the ladder inline if it's a quick call).
   - **Recurring-shape check**: is this the Nth bug with the same underlying pattern — e.g.
     "a spawn call silently no-ops instead of erroring," "a sweep meant to catch dead state
     excludes the exact case it should catch," "an event is lost across a restart with no
     catch-up path"? If so, this is a systemic gap, not an isolated bug — the fix must close
     the whole class (e.g. a shared helper with the invariant enforced once, a lint rule
     banning the unsafe pattern repo-wide, a structural test asserting the sweep's exclusion
     guard can't self-defeat) rather than patching this one call site. Say explicitly in the
     bug doc which recurring shape this is, so a future bug-fix or audit doesn't re-derive it
     as new.

7. **Update the bug document** in `docs/bugs/open/` → move to `docs/bugs/resolved/`, including
   the Phase D classification and any recurring-shape note.

8. Output:
   ```
   ✅ Bug fixed and verified

   Root cause: <one sentence>
   Fix: <one sentence>
   Regression test: <test name>
   Systemic fix: <enforcement added beyond the regression test, or "none needed — test is the
     earliest achievable level">
   Recurring shape: <name of the pattern if this is the Nth instance, or "none identified">
   ```
