---
description: "Phase 1 — Interview to capture requirements. Outputs: project_plans/<project>/requirements.md"
user-invocable: true
---

# sdd:1-ideate

Conduct a structured requirements interview and produce `requirements.md`.

## HARD GATE

**Do not discuss implementation approaches, technology choices, or architecture until `requirements.md` is written and confirmed by the user.** If you catch yourself proposing solutions during the interview, stop and ask another requirements question instead.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Run the interview.** Ask these questions one at a time — wait for each answer before asking the next:

   1. "What problem does this solve? Who experiences it and how often?"
   2. "Who are the users or systems that will interact with this?"
   3. "What does success look like? How will we measure it?"
   4. "What are the hard constraints? (deadline, performance targets, compliance requirements)"
   5. "Is this a new service or a change to an existing one? If existing, what's the repo?"
   6. "What must this NOT do? (out of scope, known exclusions)"

3. **Anti-rationalization check.** Before writing `requirements.md`, confirm:
   - You have a problem statement (not a solution statement)
   - You know the success metric
   - You have enough context to research the right technology stack in Phase 2

4. **Write `project_plans/<PROJECT_NAME>/requirements.md`:**

```markdown
# Requirements: <PROJECT_NAME>

**Date**: <YYYY-MM-DD>
**Type**: <new service | feature addition | migration | bug fix>

## Problem Statement
<what problem this solves, for whom>

## Users / Consumers
<who or what systems interact with this>

## Success Metrics
<measurable outcomes>

## Constraints
<hard constraints: deadlines, performance, compliance, team>

## Scope
### In Scope
<what this covers>

### Out of Scope
<explicit exclusions>

## Open Questions
<unresolved questions for research phase>
```

5. **After writing the file**, output:
   ```
   ✅ Phase 1 complete — requirements.md written to project_plans/<PROJECT_NAME>/

   Next step: /sdd:2-research
   ```
