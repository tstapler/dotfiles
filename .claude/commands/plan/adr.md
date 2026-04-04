---
description: Create a numbered ADR in project_plans/<project>/decisions/ for a significant
  architectural choice
prompt: '# Create ADR: Architecture Decision Record


  Creates `project_plans/<project>/decisions/ADR-NNN-<title>.md`.


  Use when making a significant architectural choice during Phase 3 (Planning) or
  whenever a decision warrants documentation:

  - Choosing between two non-trivial approaches

  - Adopting or rejecting a technology/library

  - Establishing a pattern that other work will follow

  - Deciding something that would be hard to reverse


  **Not every decision needs an ADR.** Small, obvious, or easily reversible choices
  don''t.


  ## Step 1: Determine project and ADR number


  If `{{args}}` is provided, parse `project` and `title` from it.

  Otherwise, infer project from context (open files, current task, recent messages)
  or ask.


  Scan `project_plans/<project>/decisions/` to find existing ADRs and determine the
  next sequential number (e.g., if ADR-001 and ADR-002 exist, next is ADR-003). If
  no decisions/ directory exists, start at 001.


  ## Step 2: Ask clarifying questions (if not already clear)


  Use `AskUserQuestion` to get what''s needed:


  - "What decision was made?" (the choice itself — one clear sentence)

  - "What were the alternatives considered?" (at least one alternative, even if obvious)

  - "What are the key consequences or trade-offs?"


  If the context makes these clear, skip the questions and draft from context.


  ## Step 3: Write the ADR file


  Create `project_plans/<project>/decisions/ADR-NNN-<kebab-title>.md`:


  ```markdown

  # ADR-NNN: <Title>


  **Status**: Proposed

  **Date**: <YYYY-MM-DD>

  **Project**: <project>


  ## Context


  <What forces, constraints, or circumstances led to this decision? What problem needed
  solving? What was the trigger?>


  ## Decision


  <What was decided? Be specific and unambiguous. One clear statement.>


  ## Alternatives Considered


  - **<Alternative A>**: <Why it was rejected or not chosen>

  - **<Alternative B>**: <Why it was rejected or not chosen>


  ## Rationale


  <Why this option over the alternatives? What made it the right call given the constraints?>


  ## Consequences


  **Positive:**

  - <Trade-off or benefit 1>


  **Negative / Risks:**

  - <Trade-off or risk 1>


  **Follow-up work:**

  - <Any work this decision creates or requires>


  ## Related


  - Requirements: `project_plans/<project>/requirements.md`

  - Supersedes: (none)

  - Related ADRs: (none)

  ```


  ## Step 4: Confirm output


  Tell the user:

  - File created: `project_plans/<project>/decisions/ADR-NNN-<title>.md`

  - Status is `Proposed` — change to `Accepted` when the team/stakeholders agree

  - Reference this ADR from `plan.md` under the architectural decisions section


  ## ADR Status Lifecycle


  | Status | Meaning |

  |--------|---------|

  | `Proposed` | Decision drafted, not yet reviewed |

  | `Accepted` | Decision approved and in effect |

  | `Deprecated` | Decision was valid but no longer applies |

  | `Superseded` | Replaced by a newer ADR (link to it) |


  ## Rules


  - Number sequentially per project — ADR-001, ADR-002, etc.

  - One decision per ADR — if you''re documenting two decisions, create two ADRs

  - Write in past tense ("We decided to...") once Accepted

  - Never delete ADRs — deprecate or supersede them instead

  '
---

# Create ADR: Architecture Decision Record

Creates `project_plans/<project>/decisions/ADR-NNN-<title>.md`.

Use when making a significant architectural choice during Phase 3 (Planning) or whenever a decision warrants documentation:
- Choosing between two non-trivial approaches
- Adopting or rejecting a technology/library
- Establishing a pattern that other work will follow
- Deciding something that would be hard to reverse

**Not every decision needs an ADR.** Small, obvious, or easily reversible choices don't.

## Step 1: Determine project and ADR number

If `$ARGUMENTS` is provided, parse `project` and `title` from it.
Otherwise, infer project from context (open files, current task, recent messages) or ask.

Scan `project_plans/<project>/decisions/` to find existing ADRs and determine the next sequential number (e.g., if ADR-001 and ADR-002 exist, next is ADR-003). If no decisions/ directory exists, start at 001.

## Step 2: Ask clarifying questions (if not already clear)

Use `AskUserQuestion` to get what's needed:

- "What decision was made?" (the choice itself — one clear sentence)
- "What were the alternatives considered?" (at least one alternative, even if obvious)
- "What are the key consequences or trade-offs?"

If the context makes these clear, skip the questions and draft from context.

## Step 3: Write the ADR file

Create `project_plans/<project>/decisions/ADR-NNN-<kebab-title>.md`:

```markdown
# ADR-NNN: <Title>

**Status**: Proposed
**Date**: <YYYY-MM-DD>
**Project**: <project>

## Context

<What forces, constraints, or circumstances led to this decision? What problem needed solving? What was the trigger?>

## Decision

<What was decided? Be specific and unambiguous. One clear statement.>

## Alternatives Considered

- **<Alternative A>**: <Why it was rejected or not chosen>
- **<Alternative B>**: <Why it was rejected or not chosen>

## Rationale

<Why this option over the alternatives? What made it the right call given the constraints?>

## Consequences

**Positive:**
- <Trade-off or benefit 1>

**Negative / Risks:**
- <Trade-off or risk 1>

**Follow-up work:**
- <Any work this decision creates or requires>

## Related

- Requirements: `project_plans/<project>/requirements.md`
- Supersedes: (none)
- Related ADRs: (none)
```

## Step 4: Confirm output

Tell the user:
- File created: `project_plans/<project>/decisions/ADR-NNN-<title>.md`
- Status is `Proposed` — change to `Accepted` when the team/stakeholders agree
- Reference this ADR from `plan.md` under the architectural decisions section

## ADR Status Lifecycle

| Status | Meaning |
|--------|---------|
| `Proposed` | Decision drafted, not yet reviewed |
| `Accepted` | Decision approved and in effect |
| `Deprecated` | Decision was valid but no longer applies |
| `Superseded` | Replaced by a newer ADR (link to it) |

## Rules

- Number sequentially per project — ADR-001, ADR-002, etc.
- One decision per ADR — if you're documenting two decisions, create two ADRs
- Write in past tense ("We decided to...") once Accepted
- Never delete ADRs — deprecate or supersede them instead
