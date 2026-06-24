---
description: "Phase 5 — Log task completion and track costs during active execution. Updates: home_plans/<project>/execution-log.md"
user-invocable: true
argument-hint: "[task completed or issue encountered]"
---

# home:5-execute

Log progress, task completions, issues, and actual costs during active execution of the project. Run this command each time you complete a task or encounter something noteworthy.

## When to use this

- After completing a task from the plan
- When you encounter an unexpected issue (bad substrate, wrong measurements, hidden damage)
- When actual costs differ from estimates
- When a decision is made mid-project that deviates from the plan

## Instructions

1. **Follow [SETUP.md](SETUP.md)** — identify PROJECT_NAME.

2. **Read `home_plans/<PROJECT_NAME>/plan.md`** to know the full task list.

3. **Read `home_plans/<PROJECT_NAME>/execution-log.md`** if it exists. If not, create it with this header:

```markdown
# Execution Log: <PROJECT_NAME>

**Started**: <YYYY-MM-DD>
**Estimated Budget**: $<X>–$<X>

---

## Actual Costs Tracker

| Date | Item | Estimated | Actual | Notes |
|------|------|-----------|--------|-------|

**Running total**: $0 / $<estimated>

---

## Task Log

```

4. **If `$1` was provided**, use it as the update. Otherwise ask:
   ```
   header: "Update type"
   question: "What do you want to log?"
   options:
     - "Task completed — I'll describe which one"
     - "Issue or surprise encountered"
     - "Actual cost that differs from estimate"
     - "Decision made that changes the plan"
   ```

5. **Append an entry to `execution-log.md`:**

   For a **completed task**:
   ```markdown
   ### [YYYY-MM-DD] ✅ Task <X.Y>: <task name>
   **Duration**: <actual time> (estimated: <plan estimate>)
   **Notes**: <anything notable — what went well, what was harder than expected>
   ```

   For an **issue or surprise**:
   ```markdown
   ### [YYYY-MM-DD] ⚠️ Issue: <short title>
   **Phase**: <which phase of work>
   **What happened**: <describe the issue>
   **Impact**: <does this change the plan? add cost? add time?>
   **Resolution**: <how was it handled, or what's the plan>
   ```

   For an **actual cost**:
   ```markdown
   ### [YYYY-MM-DD] 💰 Cost: <item>
   - Estimated: $<X>
   - Actual: $<X>
   - Notes: <why the difference>
   ```
   Also add a row to the Actual Costs Tracker table and update the running total.

   For a **plan deviation**:
   ```markdown
   ### [YYYY-MM-DD] 🔄 Decision: <short title>
   **Changed from**: <what the plan said>
   **Changed to**: <what was actually done>
   **Reason**: <why>
   ```

6. **After appending**, show the user:
   - Which tasks from plan.md are now complete vs remaining
   - The current running cost vs estimate
   - What the next task in the plan is

7. **When all tasks are marked complete**, prompt:
   ```
   header: "Project done?"
   question: "All tasks appear complete. Ready to close out the project?"
   options:
     - "Yes — run /home:6-close to document and archive"
     - "Not quite — there's still more to do"
   ```
