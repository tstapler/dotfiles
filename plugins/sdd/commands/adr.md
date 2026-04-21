---
description: Capture an architecture decision record
argument-hint: "<decision title>"
user-invocable: true
---

# sdd:adr

Write an Architecture Decision Record (ADR).

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Interview the user:**
   - "What decision are you recording?"
   - "What alternatives did you consider?"
   - "What did you choose and why?"
   - "Does this deviate from a team or project standard? If so, which one?"

3. **Auto-number the ADR.** Scan `project_plans/<PROJECT_NAME>/decisions/` for existing ADR files.
   Next number = highest existing N + 1, or ADR-001 if none exist.

4. **Write `project_plans/<PROJECT_NAME>/decisions/ADR-<NNN>-<kebab-title>.md`:**

```markdown
# ADR-<NNN>: <Title>

**Date**: <YYYY-MM-DD>
**Status**: Proposed
**Deciders**: <names or teams>

## Context
<Problem being solved and why a decision is needed>

## Decision
<What was chosen>

## Rationale
<Why this, and not the alternatives>

## Alternatives Considered
| Option | Rejected because |
|--------|-----------------|
| <alt> | <reason> |

## Consequences
<Trade-offs accepted, risks introduced, follow-up actions>

## Standard Deviation
<If deviating from an established team standard — which standard, why the exception>
<"None" if this aligns with all team standards>
```

5. Output: `✅ ADR-<NNN> written to project_plans/<PROJECT_NAME>/decisions/`
