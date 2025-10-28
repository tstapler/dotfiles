---
title: Plan Status
description: Review current plan status and recommend next action
---

# Project Plan Status Check

This command uses the `project-coordinator` agent to analyze current project state and recommend what to work on next.

## Agent Delegation

```
@task project-coordinator

Analyze current project status and recommend next action.

**Context**:
- Repository: [Automatically detected]
- Git Branch: [Current branch from git status]
- Uncommitted Changes: [Detect from git status]

**Analysis Tasks**:

1. **Scan Active Plans**:
   - Check TODO.md in root directory
   - Find all non-archived files in docs/tasks/
   - Find all non-archived files in docs/projects/
   - Review git status for uncommitted changes

2. **Analyze Current State**:
   - Identify in-progress tasks (marked with 🔄, "IN PROGRESS", or similar)
   - Review recently completed tasks (last 7 days from git log)
   - Check for blocked tasks or dependency issues
   - Assess overall project momentum

3. **Provide Status Report** with:
   - **Overall Health**: [Healthy | At Risk | Blocked]
   - **Active Tasks**: Count and list
   - **Blockers**: Count and specific issues
   - **Recent Velocity**: [High | Medium | Low]

4. **Detail Each Category**:
   - **In Progress**: Tasks with progress indicators and estimated remaining effort
   - **Blockers**: Specific reasons and what's needed to unblock
   - **Recently Completed**: Last 5 completed tasks with dates
   - **Upcoming**: Next 3 prioritized tasks from TODO.md

5. **Recommend Next Action** with:
   - **Task Name**: From TODO.md or task files
   - **Rationale**: Why this task now (priority, dependencies, flow state)
   - **Estimated Time**: Time to completion
   - **Prerequisites**: Any context needed before starting
   - **Files to Load**: Specific files to understand before beginning

**Expected Output Format**:

```markdown
## Project Status Summary

**Overall Health**: [Status]
**Active Tasks**: [Count]
**Blockers**: [Count]
**Recent Velocity**: [Assessment]

### In Progress ([N] tasks)
[Detailed list with progress and estimates]

### Blockers ([N] tasks)
[List with reasons and unblocking requirements]

### Recently Completed (last 7 days)
[Last 5 with completion dates]

### Upcoming (next 3 priorities)
[Prioritized list from TODO.md]

## 🎯 Recommended Next Action

**Start**: [Task Name]

**Rationale**:
[Why this task now - priority, flow, dependencies]

**Estimated Time**: [Hours to completion]

**Prerequisites**:
[Context needed before starting]

**Files to Load Before Starting**:
1. [File with purpose]
2. [File with purpose]
...

**Next Steps**:
1. [Action item]
2. [Action item]
...
```

**Focus**: Eliminate decision paralysis by providing clear, actionable recommendation based on current project state, dependencies, and maintaining flow.
```

## Usage Tips

```bash
# Run at the start of each work session
/plan:status
```

The agent will:
- ✅ Scan all active planning documents
- ✅ Identify in-progress, blocked, and upcoming tasks
- ✅ Assess project momentum
- ✅ Recommend the single best next task
- ✅ Provide clear rationale and prerequisites

This eliminates decision paralysis and helps maintain flow state throughout your work session.

## When to Use

- **Start of work session** - "What should I work on?"
- **After completing a task** - "What's next?"
- **When feeling stuck** - "Am I blocked or just uncertain?"
- **Before context switching** - "Should I finish this or pivot?"
