---
description: Capture an architecture decision record
argument-hint: "<decision title>"
user-invocable: true
---

# sdd:adr

Write an Architecture Decision Record (ADR).

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Run the interview using `AskUserQuestion` for each question.**

   **Question 1:**
   ```
   header: "Decision type"
   question: "What decision are you recording?"
   options:
     - "Technology or library choice"
     - "Architecture pattern selection"
     - "API or data model design"
     - "Process or workflow decision"
   ```

   **Question 2:**
   ```
   header: "Alternatives"
   question: "What alternatives did you consider?"
   options:
     - "I'll list the alternatives (click Other)"
     - "No alternatives — only one viable option existed"
     - "Alternatives were obvious non-starters — I'll note them briefly"
   ```

   **Question 3:**
   ```
   header: "Choice + rationale"
   question: "What did you choose and why?"
   options:
     - "I'll explain my choice and reasoning (click Other)"
   ```

   **Question 4:**
   ```
   header: "Standards"
   question: "Does this deviate from an established team or project standard?"
   options:
     - "Yes — it deviates from a standard (I'll explain)"
     - "No — aligns with all established standards"
     - "There is no relevant standard yet"
   ```

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
