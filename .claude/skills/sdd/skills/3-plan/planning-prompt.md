Prompt for the planning/synthesis subagent dispatched by `sdd:3-plan` step 3. Include the full text below in the subagent's prompt, along with `requirements.md` and all `research/*.md` files.

---

You are a planning subagent for Stapler-Driven Development. Produce a complete implementation plan.

**Step 0.5 — CREATIVE pass (alternatives exploration):** Before committing to any architecture, brainstorm 2–3 distinct high-level approaches. For each, write one sentence on its key strength and one on its key weakness. Choose the strongest. Record the rejected approaches in the Pattern Decisions table using the "Alternative Rejected" and "Reason" columns — do not leave these blank. This prevents anchoring on the first idea and produces a richer plan.md that reviewers can challenge.

**Step 1:** Review the requirements and research. Identify the type of system being built.

**Step 2:** Define the ubiquitous language. List every domain term that will appear in code as a type name, method name, or variable — define each in one sentence. Write these to the Domain Glossary section of plan.md (template below). Consistency in naming across planning → implementation → tests prevents the implementation subagent from inventing alternate names for the same concept.

**Step 3:** Validate technology choices and select design patterns. Do two things:
- **Technology validation**: flag anything with known stability, licensing, or security concerns. Write an ADR stub for any non-standard choices.
- **Pattern selection**: for each major component, explicitly choose the right pattern from these authorities:
  - *PoEAA (Fowler)*: Transaction Script vs. Domain Model vs. Repository vs. Service Layer vs. Unit of Work — match the pattern to the complexity level (don't use Domain Model for simple CRUD; don't use Transaction Script for complex business rules)
  - *GoF*: identify any creational, structural, or behavioral problems a standard pattern (Strategy, Decorator, Factory, Observer, etc.) would solve — but only add a pattern when the problem recurs
  - *Type-driven design*: identify all domain concepts that should be newtypes or value objects rather than primitives; identify any states that should be sum types or sealed interfaces
Add a "Pattern Decisions" section to plan.md listing each chosen pattern and the alternative rejected.

**Step 4:** Write `project_plans/<PROJECT_NAME>/implementation/plan.md` following the template below. Use exact file paths — no placeholders. Task sizing: 2–5 minutes each, max 3–5 files per task. **For every acceptance criterion**, include one concrete Given-When-Then example (use Domain Glossary type names in the Given state, real data values in When/Then). If you cannot write a concrete example for a criterion, the criterion is ambiguous — rewrite it before writing plan.md.

**Step 5:** Write any ADRs to `project_plans/<PROJECT_NAME>/decisions/ADR-NNN-<kebab-title>.md`.

**Step 6:** Return a summary: epic count, story count, task count, any flagged choices, glossary term count.

## Plan template

```markdown
# Implementation Plan: <PROJECT_NAME>

**Feature**: <one-line description>
**Date**: <YYYY-MM-DD>
**Status**: Ready for implementation
**ADRs**: <list or "None">

---

## Domain Glossary
*(Ubiquitous language — every domain term that appears as a type, method, or variable name. Exact names here must be used consistently in code, tests, and comments.)*

| Term | Definition | Notes |
|------|-----------|-------|
| `<OrderID>` | Unique identifier for a customer order; wraps a UUID | Newtype, not raw string |
| `<PaymentStatus>` | Enum: Pending / Authorized / Captured / Failed / Refunded | Sum type with exhaustive handling |

---

## Pattern Decisions

| Component | Pattern Chosen | Source | Alternative Rejected | Reason |
|-----------|---------------|--------|---------------------|--------|
| <e.g. OrderService> | Service Layer (PoEAA) | Fowler | Transaction Script | Complex cross-aggregate rules |
| <e.g. OrderID> | Newtype (type-driven-design) | Minsky | raw string | Prevent cross-entity ID confusion |
| <e.g. OrderStatus> | Sum type / sealed interface | type-driven-design | string enum | Compiler-enforced exhaustive handling |
| <e.g. PaymentGateway> | Adapter (GoF) | GoF | Direct call | Isolates third-party interface |

---

## Migration Plan
*(Omit this section if no schema or data changes are involved.)*
- **Migration file**: `<path/to/migration.sql or equivalent>`
- **Reversibility**: up/down scripts, or irreversible (explain why)
- **Zero-downtime strategy**: CONCURRENTLY index creation, column expansion then backfill, dual-write period, etc.
- **Rollback procedure**: steps to revert if this migration causes production issues

## Observability Plan
- **Logs**: structured log lines at entry/exit of new service boundaries; error paths log error + context
- **Metrics**: `<metric name>` measuring `<what>` (one entry per new operation >100ms)
- **Alerts**: `<condition>` → page oncall (or "no new alerts required")

## Risk Control
- **Feature flag**: `<flag name and default>` (or "not gated")
- **Rollback procedure**: `<specific steps>` (or "standard revert via PR close + revert commit")
- **Staged rollout**: `<% or cohort>` (or "full rollout on merge")

## Unresolved Questions
*(Anything still unknown at plan-approval time. Each item must be resolved before the story that depends on it starts. If none, write "None.")*
- [ ] <question> — blocks Story <X.Y.Z> — owner: <who resolves this>

## Dependency Visualization
[ASCII diagram showing task dependencies]

---

## Phase 1: <name>
### Epic 1.1: <name>
**Goal**: <what this epic achieves>

#### Story 1.1.1: <name>
**As a** <role>, **I want** <capability>, **so that** <value>.
**Acceptance Criteria**:
- <measurable criterion>
  - *Given* <concrete starting state with real data>, *When* <exact user action or system event>, *Then* <specific observable outcome>.
**Files**: <exact file paths>

##### Task 1.1.1a: <name> (~<2-5> min)
- <exact steps>
- Files: <list>
```
