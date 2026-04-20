# Product Management Templates

Copy-paste-ready templates. Adjust section depth to match feature complexity.

## PRD Template

```markdown
# PRD: [Feature Name]

## Problem Statement

**Who**: [Specific target user]
**Problem**: [What they struggle with today]
**Frequency**: [How often this problem occurs]
**Impact**: [Consequence of the problem remaining unsolved]

## Jobs-to-be-Done

> When [situation], I want to [motivation], so I can [expected outcome].

## Proposed Solution

[2-3 paragraph description of what you intend to build]

## Success Metrics

| Metric | Current | Target | Measurement Method |
|--------|---------|--------|-------------------|
| [metric 1] | [baseline or "unknown"] | [target] | [how to measure] |
| [metric 2] | | | |

## Scope

### In Scope

- [Feature/behavior 1]
- [Feature/behavior 2]

### Out of Scope

- [Explicitly excluded item 1] -- rationale: [why]
- [Explicitly excluded item 2] -- rationale: [why]

## User Stories

[Link to stories or embed key stories here]

## Technical Considerations

- **Dependencies**: [external services, libraries, APIs]
- **Performance**: [latency, throughput requirements]
- **Security**: [auth, data sensitivity]
- **Compatibility**: [platforms, browsers, devices]

## Assumptions and Risks

| Assumption | Risk if Wrong | Mitigation |
|-----------|--------------|------------|
| [assumption 1] | [consequence] | [how to validate or reduce risk] |

## Timeline

| Phase | Scope | Estimate |
|-------|-------|----------|
| MVP | [minimal scope] | [duration] |
| V1 | [full initial scope] | [duration] |
| Future | [deferred items] | TBD |

## Open Questions

- [ ] [Question 1]
- [ ] [Question 2]
```

### PRD Sizing Guide

| Feature Size | PRD Depth | Sections Required |
|-------------|----------|-------------------|
| Small (< 1 day) | Lightweight | Problem, Solution, Scope, Stories |
| Medium (1-5 days) | Standard | All sections, brief |
| Large (1+ weeks) | Full | All sections, detailed + research |

## User Story Template

```markdown
### [Story ID]: [Short title]

**As a** [specific user role],
**I want** [goal/action],
**So that** [reason/outcome].

**Priority**: [Must/Should/Could]
**Estimate**: [T-shirt size or hours]
**Parent**: [PRD or roadmap item reference]

#### Acceptance Criteria

- [ ] **Given** [precondition], **When** [action], **Then** [expected result]
- [ ] **Given** [precondition], **When** [action], **Then** [expected result]

#### Edge Cases

- [ ] [Edge case 1]: [expected behavior]
- [ ] [Edge case 2]: [expected behavior]

#### Notes

[Implementation hints, design references, or constraints]
```

### Story Splitting Patterns

When a story is too large, split by:

| Pattern | When to Use | Example |
|---------|-------------|---------|
| **Workflow steps** | Multi-step process | "Create account" -> "Enter info", "Verify email", "Set preferences" |
| **Business rules** | Complex logic | "Calculate price" -> "Base price", "Apply discount", "Apply tax" |
| **Data variations** | Multiple input types | "Import data" -> "Import CSV", "Import JSON", "Import API" |
| **Happy path / edge cases** | Core vs. error handling | "Submit form" -> "Valid submission", "Handle validation errors" |
| **CRUD** | Data management | "Manage books" -> "Add book", "Edit book", "Delete book", "List books" |

## Outcome-Based Roadmap Template

```markdown
# Roadmap: [Project Name]

Last updated: [date]

## Vision

[1-2 sentences: what does the world look like when this project succeeds?]

## Now (Committed -- current focus)

### Outcome: [Desired behavior change or metric improvement]

| Item | Type | Status | Est. |
|------|------|--------|------|
| [Feature/initiative] | [Build/Research/Fix] | [Not started/In progress/Done] | [days] |
| [Feature/initiative] | | | |

**Key result**: [measurable target]

## Next (Planned -- high confidence, not yet started)

### Outcome: [Desired behavior change]

| Item | Type | Dependency | Est. |
|------|------|-----------|------|
| [Feature/initiative] | | [if any] | [days] |

**Key result**: [measurable target]

## Later (Exploring -- lower confidence, needs research)

### Outcome: [Hypothesis about what matters]

- [Rough idea 1]
- [Rough idea 2]

**Open questions**: [what needs to be true for this to move to "Next"]

## Parking Lot (Captured but not prioritized)

- [Idea] -- source: [where it came from]
- [Idea] -- source: [where it came from]
```

### Roadmap Rules

1. "Now" items have PRDs or requirements.md written
2. "Next" items have at least a problem statement
3. "Later" items are hypotheses, not commitments
4. Review and reorder quarterly (or monthly for active projects)
5. Items flow: Parking Lot -> Later -> Next -> Now -> Done

## Feature Scope Document Template

```markdown
# Feature Scope: [Feature Name]

**Parent**: [PRD or roadmap item]
**Author**: [name]
**Date**: [date]
**Status**: [Draft/Review/Approved]

## Context

[Why are we considering this? What prompted the discussion?]

## Options

### Option A: [Name]

- **Description**: [what this approach entails]
- **Pros**: [benefits]
- **Cons**: [drawbacks]
- **Effort**: [estimate]
- **Risk**: [what could go wrong]
- **Reversibility**: [easy to undo? hard to undo?]

### Option B: [Name]

[same structure]

## Recommendation

**Choice**: [Option A/B]
**Rationale**: [specific reasoning]
**Trade-offs accepted**: [what we're giving up and why that's OK]

## MoSCoW Scope (for chosen option)

| Feature | Category | Rationale |
|---------|----------|-----------|
| [feature] | Must | [why non-negotiable] |
| [feature] | Should | [why important] |
| [feature] | Could | [why desirable] |
| [feature] | Won't (this time) | [why deferred] |
```
