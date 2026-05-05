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

2. **Run the interview using `AskUserQuestion` for each question.** Ask one at a time — wait for each answer before asking the next. Use "Other" answers for custom/freeform input.

   **Question 1:**
   ```
   header: "Problem"
   question: "What problem does this solve? Who experiences it and how often?"
   options:
     - "A user-facing bug or broken feature"
     - "A missing capability users need"
     - "A technical issue (performance, reliability, or debt)"
     - "A compliance or regulatory requirement"
   ```

   **Question 2:**
   ```
   header: "Users"
   question: "Who are the users or systems that will interact with this?"
   options:
     - "End users (human operators or customers)"
     - "Downstream services or internal APIs"
     - "Both human users and automated systems"
     - "Internal tooling or developer experience"
   ```

   **Question 3:**
   ```
   header: "Success"
   question: "What does success look like? How will we measure it?"
   options:
     - "Specific metric improves (latency, error rate, conversion)"
     - "Feature is shipped and working correctly"
     - "Bug is gone with regression test preventing recurrence"
     - "I'll describe the success metric (click Other)"
   ```

   **Question 4:**
   ```
   header: "Constraints"
   question: "What are the hard constraints? (deadline, performance targets, compliance)"
   options:
     - "Deadline-driven — I'll specify the date (click Other)"
     - "Performance or SLA target — I'll specify (click Other)"
     - "Compliance or security requirement"
     - "No hard constraints"
   ```

   **Question 5:**
   ```
   header: "Scope type"
   question: "Is this a new project or a change to an existing one?"
   options:
     - "New project (greenfield)"
     - "New feature in an existing project"
     - "Refactor or improvement to existing code"
     - "Bug fix in an existing project"
   ```

   **Question 6:**
   ```
   header: "Out of scope"
   question: "What must this NOT do? (out of scope, known exclusions)"
   options:
     - "I'll list specific exclusions (click Other)"
     - "Scope is fully clear — no explicit exclusions"
     - "No hard exclusions yet — leave open questions in requirements"
   ```

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
