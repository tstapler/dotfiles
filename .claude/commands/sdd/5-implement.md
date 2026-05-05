---
description: "Phase 5 — Execute plan via subagent dispatcher. START IN A FRESH SESSION."
user-invocable: true
---

# sdd:5-implement

Execute the implementation plan using the subagent-driven-development pattern.

## ⚠️ FRESH SESSION REQUIRED

If this session was used for planning (ideate/research/plan/validate), **stop now**.
Close this session and open a new one, then run `/sdd:5-implement` again.
Planning context degrades code generation quality — this is not optional.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Read required inputs** — halt with clear message if either is missing:
   - `project_plans/<PROJECT_NAME>/implementation/plan.md`
   - `project_plans/<PROJECT_NAME>/implementation/validation.md`

3. **Invoke the subagent-driven-development skill** — see `skills/subagent-driven-development/SKILL.md`.

4. **For each task in plan.md**, the subagent pattern is:

   **Coordinator** reads the full plan, then for each task:

   a. **Worker subagent** receives ONLY:
      - The task description + acceptance criteria
      - The exact files to create/modify

   b. **Spec compliance reviewer** receives the diff and:
      - Checks every acceptance criterion is met
      - Reports any gaps

   c. **Code quality reviewer** receives the diff and:
      - Checks test coverage against validation.md test cases
      - Verifies test naming and assertion patterns

   d. **Coordinator** patches violations before moving to next task.
      Warnings are logged but do not block.

5. **After all tasks complete**, output a summary:
   ```
   ✅ Phase 5 complete

   Tasks completed: <N>/<N>
   Gaps fixed: <N>
   Warnings noted: <N> (see below)

   Next step: /sdd:6-verify
   ```
