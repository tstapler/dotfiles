---
description: "Phase 1 — Interview to capture requirements. Outputs: project_plans/<project>/requirements.md"
user-invocable: true
allowed-tools: Read, Write, AskUserQuestion, Bash
---

# sdd:1-ideate

Conduct a structured requirements interview and produce `requirements.md`.

## HARD GATE

**Do not discuss implementation approaches, technology choices, or architecture until `requirements.md` is written and confirmed by the user.** If you catch yourself proposing solutions during the interview, stop and ask another requirements question instead.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Gather context before asking anything.**

   Read the codebase and user's request to derive what you can without asking:
   - `git log --oneline -10` — recent work, clues about scope and language
   - Top-level directory structure — tech stack, project type, existing patterns
   - The user's initial request — problem type, implied users, implied scope

   From this, pre-fill what you can confidently determine:
   - Scope type (new project vs. existing — usually obvious from context)
   - Likely users (often derivable from the codebase or request)
   - Tech stack constraints (don't ask what you can read)

3. **Think about what's still unknown.**

   Before asking any question, reason about:
   - What information is genuinely missing that you cannot infer?
   - Which gaps would most change the requirements or research direction if answered differently?
   - What project-specific nuances (this stack, this team, this domain) make the standard questions poor fits?

   From this reasoning, generate only the questions needed to fill real gaps. If context and the user's request already cover all the information goals, write `requirements.md` without asking anything. Every question must earn its place.

4. **Design each question for this specific project.**

   For each question you decide to ask:
   - Write the `header` (≤ 12 chars) as the information goal, not a generic category
   - Write the `question` text referencing actual project specifics (file names, tech, known patterns) where relevant
   - Write `options` that reflect realistic answers *for this project* — not generic possibilities
   - Add `multiSelect: true` only when multiple selections are genuinely independent and meaningful
   - Always include an "Other — I'll describe it" option so the user isn't trapped

   Example: instead of `"What are the hard constraints?"` with generic options, write `"This touches the payments service — are there PCI or SLA constraints that bound the approach?"` with options drawn from what you know about this codebase.

5. **Ask questions one at a time** using `AskUserQuestion`, only for genuine gaps. Wait for each answer before asking the next. Do not batch. If there are no gaps, skip directly to step 7.

6. **Information goals** — your questions must collectively cover these before you can write `requirements.md`. You decide which questions elicit which goals; some goals may be covered by one question, some by context alone.

   **Always required:**
   - Problem statement (what breaks or is missing, for whom)
   - Baseline (what users do today without this)
   - Success metric (measurable behavior change — not "shipped")
   - Appetite (time budget that constrains scope)

   **Required unless clearly inferable from context:**
   - Hard constraints (deadline, compliance, performance target)
   - Out-of-scope boundary (what this must NOT do)
   - Feasibility risks and rabbit holes

   **Required only for complexity ≥ 3:**
   - Observability requirements (metrics, alerts)
   - Risk control decision (feature flag, rollback, staged rollout)

   **Derive without asking (do not ask the user):**
   - Scope type (new vs. existing) — read from context
   - Users / consumers — infer from problem statement and codebase
   - Tech stack — read from the repo

7. **Anti-rationalization check.** Before writing `requirements.md`, confirm:
   - You have a problem statement (not a solution statement)
   - The baseline is captured so success can be measured against it
   - The success metric describes a behavior change, not just delivery
   - Appetite is captured (the time budget that constrains scope)
   - Alternatives, feasibility risks, and rabbit holes are captured
   - **Complexity score derived** — assign 1–4:
     - **1** = Bug fix or small refactor with Small appetite
     - **2** = New feature with Small or Medium appetite
     - **3** = New project, multiple epics, or feature with ≥1 external integration and Medium/Large appetite
     - **4** = Migration, compliance/security-critical, or cross-cutting change with Large appetite
   - **For complexity ≥ 3**: observability requirements and risk control decision are captured

8. **Write `project_plans/<PROJECT_NAME>/requirements.md`:**

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
<who or what systems interact with this — derived from context>

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
<approaches considered — library, SaaS, LLM-generated, etc.>

## Feasibility Risks
<known or suspected blockers>

## Observability Requirements
*(complexity ≥ 3 only)* <what to log, what metrics to emit, what oncall alert condition if any, or "standard request logging sufficient">

## Risk Control
*(complexity ≥ 3 only)* <feature flag name if applicable | rollback procedure | staged rollout plan | "not needed — low risk">

## Open Questions
<unresolved questions for research phase>
```

9. **After writing the file**, output:
   ```
   ✅ Phase 1 complete — requirements.md written to project_plans/<PROJECT_NAME>/

   Next step: /sdd:2-research
   ```
