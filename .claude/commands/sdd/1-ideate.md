---
description: "Phase 1 — Interview to capture requirements. Outputs: project_plans/<project>/requirements.md"
user-invocable: true
allowed-tools: Read, Write, AskUserQuestion
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
   header: "Baseline & Success"
   question: "What are users doing today without this (the workaround or baseline)? And what measurable behavior change proves the new approach is better? (Shipping is not a success metric.)"
   options:
     - "There's a manual workaround — I'll describe it (click Other); success = users stop doing it"
     - "Specific metric improves over baseline (latency, error rate, conversion rate, p95)"
     - "User completes task X in under N steps / seconds vs. the current N+M"
     - "Bug is gone with regression test preventing recurrence; baseline = bug reproduced"
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

   **Question 7:**
   ```
   header: "Alternatives"
   question: "Have you considered other approaches? (This shapes the Phase 2 build-vs-buy research.)"
   options:
     - "Use an existing library or OSS project instead of building"
     - "Use a SaaS/API instead of building"
     - "Have the LLM generate the algorithm vs. use a battle-tested library"
     - "Already decided — want to research alternatives anyway"
   multiSelect: true
   ```

   **Question 8:**
   ```
   header: "Feasibility"
   question: "What technical blockers or rabbit holes could derail this? (Rabbit holes = things that sound simple but have unknown depth once you dig in.)"
   options:
     - "Unknown — research needed (Phase 2 will surface blockers and rabbit holes)"
     - "Known blocker I'll describe (click Other)"
     - "Suspected rabbit hole I'll flag (click Other)"
     - "Prior attempt failed — I'll explain (click Other)"
   ```

   **Question 9:**
   ```
   header: "Observability"
   question: "What should be logged, measured, or alerted on for this feature?"
   options:
     - "Define specific metrics/logs (click Other)"
     - "Standard request logging is sufficient"
     - "Oncall alert needed — I'll describe the condition (click Other)"
     - "Not applicable (no runtime behavior / pure tooling)"
   ```

   **Question 10:**
   ```
   header: "Risk control"
   question: "Does this change need a feature flag, rollback plan, or staged rollout?"
   options:
     - "Feature flag — gate behind a flag so it can be disabled without a deploy"
     - "Rollback plan — define how to revert if this causes incidents"
     - "Staged rollout — % of traffic or specific cohort first"
     - "Not needed — low risk, no special rollout required"
   multiSelect: true
   ```

   **Question 11:**
   ```
   header: "Appetite"
   question: "What is your time appetite — the maximum you'd invest before cutting scope or abandoning? (Shape Up: appetite constrains scope, not the other way around.)"
   options:
     - "Small: 1–2 days — must be a minimal, surgical change"
     - "Medium: 1–2 weeks — a focused feature build"
     - "Large: 3–6 weeks — a substantive investment"
     - "Not set — let research and planning determine scope"
   ```

3. **Anti-rationalization check.** Before writing `requirements.md`, confirm:
   - You have a problem statement (not a solution statement)
   - The baseline (current workaround) is captured so success can be measured against it
   - The success metric describes a behavior change, not just delivery
   - You have enough context to research the right technology stack in Phase 2
   - Alternatives, feasibility risks, and rabbit holes are captured
   - Observability requirements are captured (even if "standard logging sufficient")
   - Risk control decision is captured (feature flag / rollback / none)
   - Appetite is captured (the time budget that constrains scope, not just a deadline)
   - **Complexity score derived** — assign 1–4 and write it in requirements.md:
     - **1** = Bug fix or small refactor with Small appetite
     - **2** = New feature with Small or Medium appetite
     - **3** = New project, multiple epics, or feature with ≥1 external integration and Medium/Large appetite
     - **4** = Migration, compliance/security-critical, or cross-cutting change with Large appetite

4. **Write `project_plans/<PROJECT_NAME>/requirements.md`:**

```markdown
# Requirements: <PROJECT_NAME>

**Date**: <YYYY-MM-DD>
**Type**: <new service | feature addition | migration | bug fix>
**Complexity**: <1 — quick task | 2 — focused feature | 3 — system design | 4 — high-stakes / cross-cutting>

## Problem Statement
<what problem this solves, for whom>

## Baseline
<what users do today without this feature — the current workaround or absent behavior. Used to evaluate whether the solution is better than the status quo, and as the regression anchor in Phase 6 verify.>

## Users / Consumers
<who or what systems interact with this>

## Success Metrics
<measurable outcomes — tied to the baseline above: what changes, by how much, compared to what>

## Appetite
<Small (1–2 days) | Medium (1–2 weeks) | Large (3–6 weeks) | TBD>
*(Scope must fit the appetite. If it doesn't fit, cut scope — do not move the deadline.)*

## Constraints
<hard constraints: deadlines, team size, budget>

## Non-functional Requirements
- **Performance SLO**: <p99 latency target, throughput, or "not specified">
- **Scalability**: <expected data volume, concurrent users, or "not applicable">
- **Security classification**: <public / internal / confidential / regulated>
- **Data residency**: <regional data constraints, or "no special requirements">

## Scope
### In Scope
<what this covers>

### Out of Scope
<explicit exclusions>

## Rabbit Holes
<things that sound in-scope and simple, but could have unknown depth or complexity once implementation starts — flag these for Phase 3 planning to explicitly resolve or de-risk>

## Alternatives Considered
<approaches evaluated from Question 7 — library, SaaS, LLM-generated, etc.>

## Feasibility Risks
<known or suspected blockers from Question 8>

## Observability Requirements
<what to log, what metrics to emit, what oncall alert condition if any, or "standard request logging sufficient">

## Risk Control
<feature flag name if applicable | rollback procedure | staged rollout plan | "not needed — low risk">

## Open Questions
<unresolved questions for research phase>
```

5. **After writing the file**, output:
   ```
   ✅ Phase 1 complete — requirements.md written to project_plans/<PROJECT_NAME>/

   Next step: /sdd:2-research
   ```
