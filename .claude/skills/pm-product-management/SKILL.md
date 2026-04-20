---
name: pm-product-management
description: >-
  Guide product thinking for solo developers acting as their own PM. Use when writing PRDs,
  creating outcome-based roadmaps, drafting user stories with acceptance criteria, scoping
  features, analyzing trade-offs, or applying prioritization frameworks (RICE, MoSCoW, Kano,
  Jobs-to-be-Done). Covers continuous discovery and modern PM practices.
---

# Product Management

Help solo developers structure product thinking: define what to build, why, and in what order.

## When to Use This Skill

- Writing or reviewing a PRD for a feature
- Creating or updating a project roadmap
- Drafting user stories with acceptance criteria
- Scoping a feature (what's in, what's out)
- Analyzing trade-offs between approaches
- Prioritizing a backlog or feature set
- Structuring product thinking around a vague idea

## Core Philosophy

**Outcome over output.** Define the change you want to see in the world, then work backward to features. Every artifact should answer: what problem does this solve, for whom, and how will we know it worked?

### Principles

1. **Start with the job** - What is the user trying to accomplish? (Jobs-to-be-Done)
2. **Outcomes over features** - Measure success by behavior change, not shipping
3. **Smallest viable scope** - What is the least you can build to learn?
4. **Continuous discovery** - Validate assumptions before and during building
5. **One-way vs. two-way doors** - Reversible decisions fast, irreversible decisions careful
6. **Explicit trade-offs** - Every scope decision has a cost; name it

## Decision Tree

```
WHAT DO YOU NEED?
|
+-- "I have a vague idea"
|   -> Run Discovery Interview (below)
|   -> Output: problem statement + initial JTBD
|
+-- "I need to define a feature"
|   -> Write PRD using template (templates.md)
|   -> Apply JTBD framing for user needs
|   -> Define success metrics
|
+-- "I need to prioritize features"
|   -> Apply RICE or ICE scoring (frameworks.md)
|   -> Use Kano for user satisfaction analysis
|   -> Output: ranked backlog with rationale
|
+-- "I need to plan a roadmap"
|   -> Use outcome-based roadmap template (templates.md)
|   -> Group by outcome themes, not dates
|   -> Apply Now/Next/Later buckets
|
+-- "I need to write stories for implementation"
|   -> Use user story template (templates.md)
|   -> Write acceptance criteria as Given/When/Then
|   -> Tag with parent PRD or roadmap item
|
+-- "I need to decide between approaches"
    -> Write feature scope doc (templates.md)
    -> Score with RICE or ICE (frameworks.md)
    -> Document trade-offs explicitly
```

## Discovery Interview

When a user has a vague idea, guide them through structured questions:

1. **Problem**: What problem are you solving? Who has it? How often?
2. **Current state**: How is this handled today? What's painful about it?
3. **Desired outcome**: What does success look like? How would you measure it?
4. **Users**: Who are the primary users? Are there secondary users?
5. **Constraints**: Timeline? Technical constraints? Dependencies?
6. **Assumptions**: What must be true for this to work? What's riskiest?
7. **Scope boundary**: What is explicitly NOT in scope?

Output: structured problem statement suitable for PRD or requirements.md.

## Workflow Integration

This skill sits **upstream** of execution. PM artifacts feed directly into `@project-coordinator` for breakdown into atomic tasks:

| PM Artifact | Maps To | Consumed By |
|-------------|---------|-------------|
| Feature PRD | `docs/tasks/<feature-name>.md` | `@project-coordinator` Epic/Story breakdown |
| Major project proposal | `project_plans/<project>/PROJECT_PROPOSAL.md` | `@project-coordinator` Epic Definition |
| Roadmap | `project_plans/<project>/README.md` | Feature sequencing priority |
| Bug | `docs/bugs/open/BUG-###-<name>.md` | `@project-coordinator` bug triage |

### Handoff to UX (for UI-touching features)

Before handing off to engineering, check: **does this feature have a user-facing interface?**

- **Yes (UI feature)**: Invoke `/ux:design <feature-name>` — pass the PRD path so UX reads from the existing doc rather than starting blind. UX design guidance should be appended to or linked from `docs/tasks/<feature-name>.md` before breaking into engineering tasks.
- **No (pure backend/API/CLI)**: Skip UX, go directly to `@project-coordinator`.

**UX readiness gate**: A feature with UI is not ready for `@project-coordinator` task decomposition until it has:
- [ ] User flow mapped
- [ ] Key states identified (empty, loading, error, success)
- [ ] Accessibility requirements noted

### Handoff to @project-coordinator

Once a PRD is written (and UX guidance appended for UI features), hand off to `@project-coordinator`:
1. PRD becomes the **Epic** input — project-coordinator defines success metrics and decomposes into Stories
2. User stories become **Story** inputs — project-coordinator breaks them into atomic 1-4h Tasks
3. Roadmap order drives **prioritization** — project-coordinator works features in roadmap sequence

**Trigger phrase**: "Break this PRD into tasks" → invoke `@project-coordinator` with the feature doc as input.

### File Locations

Use the right tier based on scope:

**Active feature work** (most common — small to medium features):
- PRD / feature plan: `docs/tasks/<feature-name>.md`
- Bug tracking: `docs/bugs/open/BUG-###-<short-name>.md`

**Major initiatives** (multi-epic, multi-week projects):
- Project proposal: `project_plans/<project>/PROJECT_PROPOSAL.md`
- Roadmap: `project_plans/<project>/README.md`
- Architecture: `project_plans/<project>/docs/explanation/ARCHITECTURE.md`
- Stories: sections within `docs/tasks/<feature-name>.md` per epic

**Decision rule**: If it fits in one feature doc (~100-300 lines), use `docs/tasks/`. If it spans multiple epics with architecture decisions, use `project_plans/`.

## Quality Standards

### PRD Quality Checklist

- [ ] Problem statement is falsifiable (could be proven wrong)
- [ ] Target user is specific (not "users" or "everyone")
- [ ] Success metrics are measurable without new tooling
- [ ] Scope has explicit "out of scope" section
- [ ] At least one assumption is identified as risky
- [ ] Non-functional requirements addressed (performance, security, compatibility)

### User Story Quality

- [ ] Follows "As a [user], I want [goal], so that [reason]" format
- [ ] Acceptance criteria use Given/When/Then
- [ ] Story is independently testable
- [ ] Story is small enough to complete in one work session
- [ ] Edge cases are addressed in acceptance criteria

### Roadmap Quality

- [ ] Organized by outcomes, not features
- [ ] Uses Now/Next/Later, not specific dates (unless committed)
- [ ] Each item links to a problem or JTBD
- [ ] Dependencies are explicit
- [ ] "Later" items are less detailed than "Now" items (progressive detail)

## References

| Topic | When to Use | File |
|-------|-------------|------|
| Prioritization frameworks | Scoring, ranking, trade-offs | [frameworks.md](./frameworks.md) |
| Document templates | Generating PRDs, stories, roadmaps | [templates.md](./templates.md) |
| Worked examples | Seeing what good artifacts look like | [examples.md](./examples.md) |

## Anti-Patterns

- **Feature factory**: Listing features without connecting to user problems
- **Scope creep by implication**: Adding "nice to haves" without explicit trade-off
- **Vanity metrics**: Choosing metrics that always go up regardless of success
- **Date-driven roadmaps**: Promising dates for uncertain scope
- **Gold plating PRDs**: Writing 10-page PRDs for small features (match detail to risk)
- **Orphan stories**: User stories disconnected from any PRD or outcome
