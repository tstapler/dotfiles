---
title: Log Bug
description: Quickly document a new bug into docs/bugs/open/ using the project-coordinator format
arguments: [bug_description]
---

# Log Bug

Quickly capture and document a new bug into `docs/bugs/open/` following the project-coordinator bug tracking format.

## Bug

${1:-Describe the bug}

## Instructions to Claude

**Step 1: Gather bug details**

If `$ARGUMENTS` provides enough context, proceed. Otherwise ask for:
- What happened vs. what was expected?
- How to reproduce it (steps if known)
- Severity assessment: Critical / High / Medium / Low
  - **Critical**: Blocks core functionality, data loss risk
  - **High**: Major feature broken, significant impact
  - **Medium**: Noticeable issue, workaround exists
  - **Low**: Minor / cosmetic / edge case

**Step 2: Determine next BUG ID**

Scan `docs/bugs/` across all subdirectories to find the highest existing BUG-### number, then increment by 1.

```bash
find docs/bugs -name "BUG-*.md" | sort | tail -5
```

**Step 3: Create the bug file**

Create `docs/bugs/open/BUG-{###}-{kebab-case-title}.md` with this structure:

```markdown
# BUG-{###}: {Short Title} [SEVERITY: {Level}]

**Status**: 🐛 Open
**Discovered**: {today's date}
**Impact**: {what functionality is affected and who is impacted}

## Problem Description

{Clear description of what's wrong}

## Reproduction Steps

1. {Step 1}
2. {Step 2}
3. Expected: {what should happen}
4. Actual: {what actually happens}

## Root Cause

{Unknown — needs investigation / or analysis if known}

## Files Likely Affected

- {file path} — {why it's relevant}

## Fix Approach

{Unknown / or proposed approach if obvious}

## Verification

{How to confirm the bug is fixed}

## Related Tasks

{Links to any related docs/tasks/ files if applicable}
```

**Step 4: Surface the bug**

After creating the file, output a summary:
- Bug ID and title
- Severity and why
- Recommended priority relative to current work (check `docs/bugs/open/` for existing bugs)
- Whether this should interrupt current work or be queued

Execute this workflow now for: ${1:-Describe the bug}
