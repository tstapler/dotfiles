---
description: Review current plan status and recommend next action
prompt: "# Project Plan Status Check\n\nThis command uses the `project-coordinator`\
  \ agent to analyze current project state and recommend what to work on next.\n\n\
  ## Agent Delegation\n\n```\n@task project-coordinator\n\nAnalyze current project\
  \ status and recommend next action.\n\n**Context**:\n- Repository: [Automatically\
  \ detected]\n- Git Branch: [Current branch from git status]\n- Uncommitted Changes:\
  \ [Detect from git status]\n\n**Analysis Tasks**:\n\n1. **Scan Active Plans**:\n\
  \   - Check TODO.md in root directory\n   - Find all non-archived files in docs/tasks/\n\
  \   - Find all non-archived files in docs/projects/\n   - Scan docs/bugs/ directory\
  \ for all bug documentation\n   - Review git status for uncommitted changes\n\n\
  2. **Analyze Current State**:\n   - Identify in-progress tasks (marked with \U0001F504\
  , \"IN PROGRESS\", or similar)\n   - Scan for open bugs and assess severity (Critical,\
  \ High, Medium, Low)\n   - Review recently completed tasks (last 7 days from git\
  \ log)\n   - Check for blocked tasks or dependency issues\n   - Identify bugs blocking\
  \ planned work\n   - Assess overall project momentum\n\n3. **Provide Status Report**\
  \ with:\n   - **Overall Health**: [Healthy | At Risk | Blocked]\n   - **Active Tasks**:\
  \ Count and list\n   - **Open Bugs**: Count by severity (Critical, High, Medium,\
  \ Low)\n   - **Blockers**: Count and specific issues (tasks and bugs)\n   - **Recent\
  \ Velocity**: [High | Medium | Low]\n\n4. **Detail Each Category**:\n   - **In Progress**:\
  \ Tasks with progress indicators and estimated remaining effort\n   - **Critical\
  \ Bugs**: Immediate blockers requiring attention (if any)\n   - **High-Severity\
  \ Bugs**: Important issues to prioritize (if any)\n   - **Blockers**: Specific reasons\
  \ and what's needed to unblock (including bug dependencies)\n   - **Recently Completed**:\
  \ Last 5 completed tasks with dates\n   - **Upcoming**: Next 3 prioritized tasks\
  \ from TODO.md (may include bug fixes)\n\n5. **Recommend Next Action** with:\n \
  \  - **Work Item**: Task or bug fix from TODO.md, task files, or bugs directory\n\
  \   - **Rationale**: Why this work now (priority, severity, dependencies, flow state,\
  \ bug impact)\n   - **Estimated Time**: Time to completion (respect 1-4 hour context\
  \ boundaries)\n   - **Prerequisites**: Any context needed before starting\n   -\
  \ **Files to Load**: Specific files to understand before beginning (3-5 max)\n\n\
  **Expected Output Format**:\n\n```markdown\n## Project Status Summary\n\n**Overall\
  \ Health**: [Status]\n**Active Tasks**: [Count]\n**Open Bugs**: [Count by severity\
  \ - Critical: N, High: N, Medium: N, Low: N]\n**Blockers**: [Count - including both\
  \ tasks and bugs]\n**Recent Velocity**: [Assessment]\n\n### In Progress ([N] tasks)\n\
  [Detailed list with progress and estimates]\n\n### \U0001F41B Critical Bugs ([N]\
  \ bugs)\n[ONLY if critical bugs exist - list with impact and recommended action]\n\
  \n### \U0001F41B High-Severity Bugs ([N] bugs)\n[ONLY if high-severity bugs exist\
  \ - list with impact]\n\n### Blockers ([N] items)\n[List with reasons and unblocking\
  \ requirements - include bug blockers]\n\n### Recently Completed (last 7 days)\n\
  [Last 5 with completion dates - include fixed bugs]\n\n### Upcoming (next 3 priorities)\n\
  [Prioritized list from TODO.md - may include bug fixes based on severity]\n\n##\
  \ \U0001F3AF Recommended Next Action\n\n**Start**: [Task Name]\n\n**Rationale**:\n\
  [Why this task now - priority, flow, dependencies]\n\n**Estimated Time**: [Hours\
  \ to completion]\n\n**Prerequisites**:\n[Context needed before starting]\n\n**Files\
  \ to Load Before Starting**:\n1. [File with purpose]\n2. [File with purpose]\n...\n\
  \n**Next Steps**:\n1. [Action item]\n2. [Action item]\n...\n```\n\n**Focus**: Eliminate\
  \ decision paralysis by providing clear, actionable recommendation based on current\
  \ project state, dependencies, and maintaining flow.\n```\n\n## Usage Tips\n\n```bash\n\
  # Run at the start of each work session\n/plan:status\n```\n\nThe agent will:\n\
  - ✅ Scan all active planning documents and bug tracking\n- ✅ Identify in-progress,\
  \ blocked, and upcoming tasks\n- ✅ Surface critical and high-severity bugs prominently\n\
  - ✅ Assess project momentum and bug impact\n- ✅ Recommend the single best next work\
  \ item (task or bug fix)\n- ✅ Provide bug-aware prioritization and rationale\n-\
  \ ✅ Provide clear rationale and prerequisites\n\nThis eliminates decision paralysis,\
  \ surfaces critical issues, and helps maintain flow state throughout your work session.\n\
  \n## When to Use\n\n- **Start of work session** - \"What should I work on?\"\n-\
  \ **After completing a task** - \"What's next?\"\n- **When feeling stuck** - \"\
  Am I blocked or just uncertain?\"\n- **Before context switching** - \"Should I finish\
  \ this or pivot?\"\n"
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
   - Scan docs/bugs/ directory for all bug documentation
   - Review git status for uncommitted changes

2. **Analyze Current State**:
   - Identify in-progress tasks (marked with 🔄, "IN PROGRESS", or similar)
   - Scan for open bugs and assess severity (Critical, High, Medium, Low)
   - Review recently completed tasks (last 7 days from git log)
   - Check for blocked tasks or dependency issues
   - Identify bugs blocking planned work
   - Assess overall project momentum

3. **Provide Status Report** with:
   - **Overall Health**: [Healthy | At Risk | Blocked]
   - **Active Tasks**: Count and list
   - **Open Bugs**: Count by severity (Critical, High, Medium, Low)
   - **Blockers**: Count and specific issues (tasks and bugs)
   - **Recent Velocity**: [High | Medium | Low]

4. **Detail Each Category**:
   - **In Progress**: Tasks with progress indicators and estimated remaining effort
   - **Critical Bugs**: Immediate blockers requiring attention (if any)
   - **High-Severity Bugs**: Important issues to prioritize (if any)
   - **Blockers**: Specific reasons and what's needed to unblock (including bug dependencies)
   - **Recently Completed**: Last 5 completed tasks with dates
   - **Upcoming**: Next 3 prioritized tasks from TODO.md (may include bug fixes)

5. **Recommend Next Action** with:
   - **Work Item**: Task or bug fix from TODO.md, task files, or bugs directory
   - **Rationale**: Why this work now (priority, severity, dependencies, flow state, bug impact)
   - **Estimated Time**: Time to completion (respect 1-4 hour context boundaries)
   - **Prerequisites**: Any context needed before starting
   - **Files to Load**: Specific files to understand before beginning (3-5 max)

**Expected Output Format**:

```markdown
## Project Status Summary

**Overall Health**: [Status]
**Active Tasks**: [Count]
**Open Bugs**: [Count by severity - Critical: N, High: N, Medium: N, Low: N]
**Blockers**: [Count - including both tasks and bugs]
**Recent Velocity**: [Assessment]

### In Progress ([N] tasks)
[Detailed list with progress and estimates]

### 🐛 Critical Bugs ([N] bugs)
[ONLY if critical bugs exist - list with impact and recommended action]

### 🐛 High-Severity Bugs ([N] bugs)
[ONLY if high-severity bugs exist - list with impact]

### Blockers ([N] items)
[List with reasons and unblocking requirements - include bug blockers]

### Recently Completed (last 7 days)
[Last 5 with completion dates - include fixed bugs]

### Upcoming (next 3 priorities)
[Prioritized list from TODO.md - may include bug fixes based on severity]

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
- ✅ Scan all active planning documents and bug tracking
- ✅ Identify in-progress, blocked, and upcoming tasks
- ✅ Surface critical and high-severity bugs prominently
- ✅ Assess project momentum and bug impact
- ✅ Recommend the single best next work item (task or bug fix)
- ✅ Provide bug-aware prioritization and rationale
- ✅ Provide clear rationale and prerequisites

This eliminates decision paralysis, surfaces critical issues, and helps maintain flow state throughout your work session.

## When to Use

- **Start of work session** - "What should I work on?"
- **After completing a task** - "What's next?"
- **When feeling stuck** - "Am I blocked or just uncertain?"
- **Before context switching** - "Should I finish this or pivot?"
