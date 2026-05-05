---
name: subagent-driven-development
description: Execute an implementation plan by dispatching fresh subagents per task with dual-review (spec compliance + code quality). Use when running sdd:5-implement or executing any multi-task implementation plan.
---

# Subagent-Driven Development

Execute an implementation plan by dispatching one fresh subagent per task, each reviewed by a spec compliance reviewer and a code quality reviewer before the coordinator moves forward.

## Why Fresh Subagents?

Each subagent receives only the context it needs — task description, relevant files, and acceptance criteria. It does not inherit the coordinator's full session history. This prevents context poisoning and keeps each task focused.

## Coordinator Responsibilities

The coordinator:
1. Reads the full plan.md once
2. Dispatches subagents sequentially (or in parallel for independent tasks)
3. Reviews each task's output before proceeding
4. Patches failures without re-running the entire plan

## Per-Task Execution Pattern

For each task in plan.md:

### Step 1: Prepare task context

The coordinator identifies:
- The task description and acceptance criteria
- The exact files involved

### Step 2: Dispatch worker subagent

Worker receives ONLY:
```
Task: <task description>

Acceptance criteria:
<list from plan.md>

Files to create/modify:
<exact paths>
```

Worker must NOT receive: coordinator's full session history, other tasks, or the full plan.

### Step 3: Spec compliance review

Spec reviewer receives:
```
Diff:
<git diff of the worker's changes>

Task acceptance criteria:
<list from plan.md>

Check:
1. Are all acceptance criteria demonstrably met?
2. Are there any correctness issues?
3. Are there any security or data integrity gaps?

Output findings with severity: VIOLATION (blocks) or WARNING (noted, doesn't block).
```

### Step 4: Code quality review

Quality reviewer receives:
```
Diff:
<git diff of the worker's changes>

Validation plan test cases:
<relevant entries from validation.md>

Check:
1. Are there tests for all new public methods?
2. Do tests cover both happy path and error paths?
3. Are tests named descriptively?
4. Are assertions specific (not just "not null")?
```

### Step 5: Coordinator decision

- **Violations present** → patch the specific issues, re-run spec review on the patched diff
- **Warnings only** → note them, proceed to next task
- **Clean** → proceed to next task

## Progression Rules

- **Never skip reviews** — the dual-reviewer pattern is what enables autonomous multi-hour runs
- **Never force-progress with unfixed violations** — warnings are acceptable, violations are not
- **A task is only complete when spec review passes** — code quality warnings do not block
