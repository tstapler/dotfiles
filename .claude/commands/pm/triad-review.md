---
description: Holistic readiness check across Product, UX, and Engineering before building
  a feature
prompt: '# Product Triad Review


  Run a holistic readiness check on a feature across all three lenses of the product
  triad — Product (PM), Design (UX), and Engineering — before committing to build
  it.


  ## Feature


  ${1:-Please provide a feature name or path to docs/tasks/<feature>.md}


  ## When to Use


  - Before starting implementation on a new feature

  - When a feature feels "almost ready" but something seems off

  - When checking if PM, UX, and Engineering are all aligned

  - To identify which triad leg is the bottleneck before proceeding


  ## Instructions to Claude


  **Step 1: Load the feature doc**


  Check for an existing feature doc at `docs/tasks/{{args}}.md` or a close match (use
  Glob). If found, read it. If not found, note it as a gap.


  **Step 2: Run three parallel assessments** using the Task tool — launch all three
  agents simultaneously:


  ### Agent 1 — Product (PM) Lens

  Use the `product-management` skill context to assess:

  - Is the problem statement clear and falsifiable?

  - Is the target user specific?

  - Are success metrics defined and measurable?

  - Is scope explicit — including what''s OUT of scope?

  - Has at least one risky assumption been named?

  - Does this belong on the roadmap now (RICE/ICE score)?


  Rate: 🔴 Not Ready / 🟡 Needs Work / 🟢 Ready


  ### Agent 2 — Design (UX) Lens

  Use the `ux-expert` agent to assess:

  - Is there a mapped user flow?

  - Are all key states identified (empty, loading, error, success)?

  - Are accessibility requirements noted?

  - Does the interaction model match user mental models (Nielsen heuristics)?

  - Are there usability risks in the current scope?


  Rate: 🔴 Not Ready / 🟡 Needs Work / 🟢 Ready


  ### Agent 3 — Engineering Lens

  Use the `project-coordinator` agent to assess:

  - Can this be broken into atomic 1-4h tasks?

  - Are technical dependencies identified?

  - Are there open bugs that block this feature?

  - Is the scope compatible with the current codebase architecture?

  - Are non-functional requirements covered (performance, security, reliability)?


  Rate: 🔴 Not Ready / 🟡 Needs Work / 🟢 Ready


  **Step 3: Synthesize findings**


  Produce a triad readiness report:


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


  **Step 4: Recommend next action**


  Based on the weakest triad leg, recommend the specific command to run next:

  - PM gap → invoke `product-management` skill or write PRD

  - UX gap → `/ux:design {{args}}`

  - Engineering gap → invoke `@project-coordinator` with the feature doc


  Execute this workflow now for: ${1:-Please provide a feature name}

  '
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

**Step 2: Run three parallel assessments** using the Task tool — launch all three agents simultaneously:

### Agent 1 — Product (PM) Lens
Use the `product-management` skill context to assess:
- Is the problem statement clear and falsifiable?
- Is the target user specific?
- Are success metrics defined and measurable?
- Is scope explicit — including what's OUT of scope?
- Has at least one risky assumption been named?
- Does this belong on the roadmap now (RICE/ICE score)?

Rate: 🔴 Not Ready / 🟡 Needs Work / 🟢 Ready

### Agent 2 — Design (UX) Lens
Use the `ux-expert` agent to assess:
- Is there a mapped user flow?
- Are all key states identified (empty, loading, error, success)?
- Are accessibility requirements noted?
- Does the interaction model match user mental models (Nielsen heuristics)?
- Are there usability risks in the current scope?

Rate: 🔴 Not Ready / 🟡 Needs Work / 🟢 Ready

### Agent 3 — Engineering Lens
Use the `project-coordinator` agent to assess:
- Can this be broken into atomic 1-4h tasks?
- Are technical dependencies identified?
- Are there open bugs that block this feature?
- Is the scope compatible with the current codebase architecture?
- Are non-functional requirements covered (performance, security, reliability)?

Rate: 🔴 Not Ready / 🟡 Needs Work / 🟢 Ready

**Step 3: Synthesize findings**

Produce a triad readiness report:

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

**Step 4: Recommend next action**

Based on the weakest triad leg, recommend the specific command to run next:
- PM gap → invoke `product-management` skill or write PRD
- UX gap → `/ux:design $ARGUMENTS`
- Engineering gap → invoke `@project-coordinator` with the feature doc

Execute this workflow now for: ${1:-Please provide a feature name}
