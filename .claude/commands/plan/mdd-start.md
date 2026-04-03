---
title: Start MDD Project
description: Run ideation interview and create requirements.md to start a new Manifest-Driven Development project
arguments: [project_name]
---

# MDD Project Start: Ideation → requirements.md

You are starting a new Manifest-Driven Development (MDD) project. This command runs the ideation phase (Phase 1) and produces `requirements.md` as its output artifact.

## What This Command Does

1. Runs a structured ideation interview using `AskUserQuestion`
2. Creates `project_plans/<project>/requirements.md` from the answers
3. Presents the 4-dimension research spawn plan for user approval

## Step 1: Determine Project Name

If `$ARGUMENTS` was provided, use it as the project name (normalized to lowercase-kebab-case). Otherwise, derive it from the conversation or ask.

## Step 2: Run Ideation Interview

Ask the following questions (use `AskUserQuestion` with 2–3 questions at a time):

**Round 1 — Core definition:**
- "What problem does this project solve? Who has this problem?"
- "What does success look like in 3 months? What's the measurable outcome?"

**Round 2 — Scope & constraints:**
- "What are the must-have capabilities (MoSCoW Must)? What's explicitly out of scope?"
- "What constraints exist — tech stack, timeline, team size, dependencies on other systems?"

**Round 3 — Context:**
- "What have you already tried or researched? What decisions are already made?"
- "Who are the key stakeholders or users?"

## Step 3: Create requirements.md

Write to `project_plans/<project-name>/requirements.md` with this structure:

```markdown
# Requirements: <Project Name>

**Status**: Draft | **Phase**: 1 — Ideation complete
**Created**: <date>

## Problem Statement

<What problem this solves and who has it>

## Success Criteria

<Measurable outcomes for 3-month horizon>

## Scope

### Must Have (MoSCoW)
- ...

### Out of Scope
- ...

## Constraints

- **Tech stack**: <existing or required tech>
- **Timeline**: <if known>
- **Dependencies**: <upstream systems or teams>

## Context

### Existing Work
<What's been tried or decided already>

### Stakeholders
<Who cares about this>

## Research Dimensions Needed

- [ ] Stack — evaluate technology options
- [ ] Features — survey comparable tools/approaches
- [ ] Architecture — design patterns and tradeoffs
- [ ] Pitfalls — known failure modes and risks
```

## Step 4: Present Research Spawn Plan

After writing requirements.md, output this to the user:

---

**Phase 1 complete.** `requirements.md` written to `project_plans/<project>/`.

**Next: Phase 2 — Research** (requires fresh context or parallel agents)

To run research in parallel, spawn 4 agents simultaneously with `/research-workflow`:

| Dimension | Focus |
|---|---|
| Stack | Evaluate technology options for this project |
| Features | Survey comparable tools, libraries, or approaches |
| Architecture | Design patterns, tradeoffs, integration points |
| Pitfalls | Known failure modes, gotchas, things that go wrong |

Each agent reads `requirements.md` as input and writes to `project_plans/<project>/research/<dimension>.md`.

**Proceed to research?** (or open a fresh session and run `/research-workflow` with the requirements file)

---

## Rules

- Never skip phases — requirements.md is required input for research
- Keep requirements.md factual, not prescriptive — capture what's known, not decisions
- If the user already has research, confirm which dimensions are covered before spawning agents
