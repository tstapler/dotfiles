---
description: Holistic readiness check across Product, UX, and Engineering before building a feature. Supports iterative mode — re-run with fresh agents after fixing gaps until all three legs are green.
---

# Product Triad Review

Run a holistic readiness check on a feature across all three lenses of the product triad — Product (PM), Design (UX), and Engineering — before committing to build it.

## Feature

${1:-Please provide a feature name or path to docs/tasks/<feature>.md}

## When to Use

- Before starting implementation on a new feature
- When a feature feels "almost ready" but something seems off
- When checking if PM, UX, and Engineering are all aligned
- To identify which triad leg is the bottleneck before proceeding

## Instructions to Claude

**Step 1: Load the feature doc**

Check for an existing feature doc at `docs/tasks/$ARGUMENTS.md` or a close match (use Glob). If found, read it. If not found, note it as a gap.

**Step 2: Run three parallel assessments** using the Task tool — launch all three agents simultaneously.

Each agent follows the `lean-agent-loop` pattern: it writes its full analysis to a temp file, then returns **only** a short structured summary to the coordinator. The coordinator reads summaries to decide what to fix; it reads the temp file only when it needs the full detail to write a fix.

**Agent output format (return this only — nothing else):**
```json
{
  "lens": "product|ux|engineering",
  "status": "ready|needs-work|not-ready",
  "gaps": ["one-line gap description", "..."],
  "blockers": ["one-line blocker", "..."]
}
```
Full analysis → `/tmp/triad-<lens>-<feature>.txt`

### Agent 1 — Product (PM) Lens
Use the `pm-product-management` skill context to assess:
- Is the problem statement clear and falsifiable?
- Is the target user specific?
- Are success metrics defined and measurable?
- Is scope explicit — including what's OUT of scope?
- Has at least one risky assumption been named?
- Does this belong on the roadmap now (RICE/ICE score)?

Rate: `not-ready` / `needs-work` / `ready`

### Agent 2 — Design (UX) Lens
Use the `ux-expert` agent to assess:
- Is there a mapped user flow?
- Are all key states identified (empty, loading, error, success)?
- Are accessibility requirements noted?
- Does the interaction model match user mental models (Nielsen heuristics)?
- Are there usability risks in the current scope?

Rate: `not-ready` / `needs-work` / `ready`

### Agent 3 — Engineering Lens
Use the `project-coordinator` agent to assess:
- Can this be broken into atomic 1-4h tasks?
- Are technical dependencies identified?
- Are there open bugs that block this feature?
- Is the scope compatible with the current codebase architecture?
- Are non-functional requirements covered (performance, security, reliability)?

Rate: `not-ready` / `needs-work` / `ready`

**Step 3: Synthesize findings**

Produce a triad readiness report from the structured summaries:

```markdown
## Triad Readiness: <Feature Name>

| Lens        | Status          | Key Gaps |
|-------------|-----------------|----------|
| Product     | 🟢/🟡/🔴 Ready  | ...      |
| UX Design   | 🟢/🟡/🔴 Ready  | ...      |
| Engineering | 🟢/🟡/🔴 Ready  | ...      |

## Overall: [READY TO BUILD / NEEDS WORK / NOT READY]

### Blockers (must fix before building)
- ...

### Recommended Next Step
[Single clearest action to unblock the bottleneck leg]
```

To read a lens's full analysis: `cat /tmp/triad-<lens>-<feature>.txt`

**Step 4: Recommend next action**

Based on the weakest triad leg, recommend the specific command to run next:
- PM gap → invoke `pm-product-management` skill or write PRD
- UX gap → `/ux:design $ARGUMENTS`
- Engineering gap → invoke `@project-coordinator` with the feature doc

**Iterative mode** — when gaps are found and fixed, re-run until all three legs are green:

```
/goal all three triad legs are 🟢 ready, or stop after 4 iterations
```

Each re-run spawns **fresh agents with no knowledge of prior rounds**. This is intentional: fresh agents give an unanchored second opinion on whether the fixes actually resolved the gaps — they either confirm the fix resolved the issue (by not finding it) or surface it again independently, proving the fix was insufficient. The coordinator tracks progress across rounds; the agents do not. See `lean-agent-loop` skill for the full pattern.

Execute this workflow now for: ${1:-Please provide a feature name}
