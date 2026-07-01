---
description: "Phase 3 — Architecture + task breakdown. Outputs: project_plans/<project>/implementation/plan.md"
user-invocable: true
effort: high
allowed-tools: Read, Write, Edit, Task, AskUserQuestion
---

# sdd:3-plan

Dispatch a planning subagent to produce the implementation plan. The subagent does all the heavy work and writes plan.md directly — the coordinator (this thread) only reads the summary back.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Read all inputs (coordinator reads these to pass to subagent):**
   - `project_plans/<PROJECT_NAME>/requirements.md` — halt if missing
   - `project_plans/<PROJECT_NAME>/research/*.md` — warn if missing, continue with requirements only

3. **Dispatch a planning subagent using the `Task` tool.**

   The subagent prompt must include:
   - Full text of `requirements.md`
   - Full text of all `research/*.md` files (if present)
   - These exact instructions:

   > You are a planning subagent for Stapler-Driven Development. Produce a complete implementation plan.
   >
   > **Step 0.5 — CREATIVE pass (alternatives exploration):** Before committing to any architecture, brainstorm 2–3 distinct high-level approaches. For each, write one sentence on its key strength and one on its key weakness. Choose the strongest. Record the rejected approaches in the Pattern Decisions table using the "Alternative Rejected" and "Reason" columns — do not leave these blank. This prevents anchoring on the first idea and produces a richer plan.md that reviewers can challenge.
   >
   > **Step 1:** Review the requirements and research. Identify the type of system being built.
   >
   > **Step 2:** Define the ubiquitous language. List every domain term that will appear in code as a type name, method name, or variable — define each in one sentence. Write these to the Domain Glossary section of plan.md (template below). Consistency in naming across planning → implementation → tests prevents the implementation subagent from inventing alternate names for the same concept.
   >
   > **Step 3:** Validate technology choices and select design patterns. Do two things:
   > - **Technology validation**: flag anything with known stability, licensing, or security concerns. Write an ADR stub for any non-standard choices.
   > - **Pattern selection**: for each major component, explicitly choose the right pattern from these authorities:
   >   - *PoEAA (Fowler)*: Transaction Script vs. Domain Model vs. Repository vs. Service Layer vs. Unit of Work — match the pattern to the complexity level (don't use Domain Model for simple CRUD; don't use Transaction Script for complex business rules)
   >   - *GoF*: identify any creational, structural, or behavioral problems a standard pattern (Strategy, Decorator, Factory, Observer, etc.) would solve — but only add a pattern when the problem recurs
   >   - *Type-driven design*: identify all domain concepts that should be newtypes or value objects rather than primitives; identify any states that should be sum types or sealed interfaces
   > Add a "Pattern Decisions" section to plan.md listing each chosen pattern and the alternative rejected.
   >
   > **Step 4:** Write `project_plans/<PROJECT_NAME>/implementation/plan.md` following the template below. Use exact file paths — no placeholders. Task sizing: 2–5 minutes each, max 3–5 files per task. **For every acceptance criterion**, include one concrete Given-When-Then example (use Domain Glossary type names in the Given state, real data values in When/Then). If you cannot write a concrete example for a criterion, the criterion is ambiguous — rewrite it before writing plan.md.
   >
   > **Step 5:** Write any ADRs to `project_plans/<PROJECT_NAME>/decisions/ADR-NNN-<kebab-title>.md`.
   >
   > **Step 6:** Return a summary: epic count, story count, task count, any flagged choices, glossary term count.

   Plan template:
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

4. **Wait for the subagent to complete.** Do not continue until plan.md has been written.

5. **Dispatch the architecture review subagent, adversarial reviewer subagent, and (for user-facing features) UX design subagent ALL IN A SINGLE PARALLEL MESSAGE using the `Task` tool.**

   > Send all applicable subagent calls in one message — do not wait for the architecture review before dispatching the adversarial reviewer or UX agent. They have no dependencies on each other.

   **Architecture Review subagent** (use `code-architecture-best-practices` as the subagent type):

   The subagent prompt must include:
   - Full text of `plan.md`
   - Full text of `requirements.md`
   - These exact instructions:

   > You are an architecture review subagent. The plan has been written but NO CODE EXISTS YET — your job is to catch structural problems while they are still cheap to fix.
   >
   > **Constitution check (before the three lenses):** Check if `docs/adr/ADR-000-architecture-constitution.md` exists in the repository. If it does, read it and treat its principles as hard constraints — any plan element that violates the constitution is automatically a BLOCKER regardless of which lens catches it. List constitution violations under a "Constitution Violations" section before the three-lens findings.
   >
   > Apply these three lenses from the `code-architecture-best-practices`, `type-driven-design`, and `design-patterns` (GoF + PoEAA) skills:
   >
   > **Lens 1 — Structural integrity (code-architecture-best-practices)**
   > 1. **SOLID violations in the proposed design** — does the proposed structure respect Single Responsibility, Open/Closed, Liskov, Interface Segregation, Dependency Inversion? Flag any story or task that bakes in a violation.
   > 2. **Layer coupling** — does the plan respect Clean Architecture / Hexagonal boundaries? Will any story force a dependency from domain logic into infrastructure?
   > 3. **DDD aggregate boundaries** — for any data model work, are aggregate roots clearly bounded? Are there missing value objects or entity distinctions?
   > 4. **Testability** — can each proposed component be tested in isolation as designed, or does the plan force integration-only testing?
   >
   > **Lens 2 — Type-level design (type-driven-design)**
   > 5. **Primitive obsession** — does the plan use raw primitives (string, int, float) where domain types (Money, Email, OrderID) should be used? Identify domain concepts that need newtypes or value objects.
   > 6. **Illegal states** — does the data model allow combinations that are invalid in the domain? Flag cases where sum types, sealed interfaces, or typestate patterns would prevent runtime errors.
   > 7. **Parse-at-boundary** — is there a clear boundary where raw input (HTTP, CLI, message) is parsed into proven domain types? If not, where should it be?
   >
   > **Lens 3 — Pattern selection (design-patterns — GoF + PoEAA)**
   > 8. **PoEAA pattern fit** — for any persistence or service layer work: is the right pattern chosen for the complexity level? (Transaction Script for simple CRUD; Domain Model for complex rules; Data Mapper/Repository for testable persistence; Unit of Work for multi-aggregate transactions; Service Layer for use case orchestration.) Flag any mismatch between complexity and pattern.
   > 9. **GoF pattern appropriateness** — for component interactions: are there creational, structural, or behavioral problems that a standard pattern would solve cleanly? Conversely, are patterns being added where a simple function or interface would do?
   > 10. **API contract design** — are proposed interfaces stable? Would a consumer need to change if the implementation changes?
   > 11. **Consistency with build-vs-buy decision** — does the plan match the Phase 2 recommendation (build-vs-buy.md if present)?
   >
   > For each finding: the specific story/task it affects, classification (BLOCKER / CONCERN / NITPICK), and a concrete remediation (proposed restructure, not just "do better").
   >
   > Write findings to `project_plans/<PROJECT_NAME>/implementation/architecture-review.md` using:
   > ```markdown
   > # Architecture Review: <PROJECT_NAME>
   > **Date**: <YYYY-MM-DD>
   > **Verdict**: BLOCKED / CONCERNS / CLEAN
   >
   > ## Blockers
   > - [ ] <story/task ref> — <violation> — <remediation>
   >
   > ## Concerns
   > - [ ] <story/task ref> — <issue> — <recommendation>
   >
   > ## Nitpicks
   > - <item>
   > ```
   >
   > Return a one-line summary: verdict + count of blockers/concerns.

   **Adversarial reviewer subagent using the `Task` tool.**

   The subagent prompt must include:
   - Full text of `plan.md`
   - Full text of `requirements.md`
   - These exact instructions:

   > You are an adversarial architecture reviewer. Your job is to challenge this implementation plan and find weaknesses before any code is written.
   >
   > Review for:
   > 1. **Missing failure modes** — What happens when external dependencies fail? Are error paths, retries, or timeouts absent?
   > 2. **Architecture risks** — Are there components that will be hard to change, scale, or test in isolation?
   > 3. **Scope drift** — Are any tasks broader than their stated requirement? Is anything being built that wasn't asked for?
   > 4. **Technology bets** — Are there non-standard choices that could become liabilities (licensing, abandonment, performance)?
   > 5. **Missing coverage** — Are there user-facing behaviors implied by requirements that have no corresponding story or task?
   >
   > For each concern, classify as:
   > - **BLOCKER** — Must be resolved before implementation starts
   > - **CONCERN** — Should be addressed; will degrade quality if skipped
   > - **MINOR** — Low impact; note it but don't block
   >
   > Write your findings to `project_plans/<PROJECT_NAME>/implementation/adversarial-review.md` using this template:
   >
   > ```markdown
   > # Adversarial Review: <PROJECT_NAME>
   >
   > **Date**: <YYYY-MM-DD>
   > **Verdict**: BLOCKED / CONCERNS / CLEAN
   >
   > ## Blockers
   > - [ ] <issue> — <recommendation>
   >
   > ## Concerns
   > - [ ] <issue> — <recommendation>
   >
   > ## Minors
   > - <issue>
   > ```
   >
   > Return a one-line summary: verdict + count of blockers/concerns/minors.

   **UX design subagent** (for user-facing features only):

   Skip this subagent if: the feature has no user-facing surface (pure infrastructure, CLI tools with no interactive UI, background services). If `requirements.md` mentions users, user flows, screens, or UI, this subagent is required.

   The subagent prompt must include:
   - Full text of `requirements.md`
   - Full text of `research/ux.md` (if present)
   - These exact instructions:

   > You are a UX design subagent. Produce a UX design artifact for this feature before implementation begins.
   >
   > **Step 1:** Identify all user-facing surfaces (screens, modals, flows, error states, empty states, loading states).
   >
   > **Step 2:** For each surface, produce:
   > - An ASCII wireframe or flow diagram showing the layout and interaction model
   > - The interaction flow: what the user does and what the system responds with at each step
   > - Error and edge-case handling: what the user sees when something fails
   >
   > **Step 3:** Write acceptance criteria for UX — each criterion should be testable by a human:
   > - "User can complete <task> in ≤ N clicks/steps"
   > - "Error state shows <specific message> and offers <specific action>"
   > - "No dead ends — every error state has an exit path"
   > - Accessibility: keyboard-navigable, screen-reader labels present, color contrast ≥ 4.5:1
   >
   > **Step 4:** Write `project_plans/<PROJECT_NAME>/design/ux.md` with the wireframes, flows, and UX acceptance criteria.
   >
   > **Step 5:** Return a summary: number of surfaces designed, number of UX acceptance criteria written.

6. **Wait for all reviewers to complete.** Read all summaries. Then run each repair loop below independently.

   **Architecture review repair loop (max 5 iterations):**
   ```
   ITERATION = 0, MAX = 5
   while (architecture-review.md verdict == BLOCKED) and (ITERATION < MAX):
     ITERATION++
     1. Collect all BLOCKER findings from architecture-review.md:
        each entry = { story/task ref, violation, proposed remediation }
     2. Spawn a fresh fix subagent (lean-agent-loop pattern):
        - Provide: BLOCKER list, current plan.md, requirements.md
        - Agent: edits plan.md to resolve each BLOCKER (restructures stories/tasks,
          fixes pattern choices, corrects layer boundaries) — does NOT touch code
        - Agent returns: list of plan changes made
     3. Re-run the architecture review subagent on the updated plan.md.
        Scope its prompt to "re-review only previously BLOCKED items."
     4. Read new verdict. Remove resolved blockers from open list.

   If CONCERNS or CLEAN: proceed.
   If MAX reached with blockers remaining: stop — report "Architecture review STUCK after 5
   iterations" with unresolved blocker list. Do not proceed to Phase 4.
   ```

   **Adversarial review repair loop (max 5 iterations):**
   ```
   ITERATION = 0, MAX = 5
   while (adversarial-review.md verdict == BLOCKED) and (ITERATION < MAX):
     ITERATION++
     1. Collect all BLOCKER findings from adversarial-review.md:
        each entry = { issue description, recommendation }
     2. Spawn a fresh fix subagent (lean-agent-loop pattern):
        - Provide: BLOCKER list, current plan.md, requirements.md
        - Agent: edits plan.md to address each BLOCKER (adds failure modes, error paths,
          missing stories, or removes scope drift) — does NOT touch code
        - Agent returns: list of plan changes made
     3. Re-run the adversarial reviewer subagent on the updated plan.md.
        Scope its prompt to "re-review only previously BLOCKED items."
     4. Read new verdict. Remove resolved blockers from open list.

   If CONCERNS or CLEAN: proceed.
   If MAX reached with blockers remaining: stop — report "Adversarial review STUCK after 5
   iterations" with unresolved blocker list. Do not proceed to Phase 4.
   ```

   **UX blocker repair loop (max 3 iterations — run only if UX subagent ran):**
   ```
   ITERATION = 0, MAX = 3
   while (ux.md contains flows with no exit path or missing error states) and (ITERATION < MAX):
     ITERATION++
     1. Collect UX blockers: each entry = { surface, missing element, criterion text }
     2. Spawn a fresh fix subagent (lean-agent-loop pattern):
        - Provide: UX blocker list, current ux.md, requirements.md
        - Agent: edits ux.md to add missing exit paths, error states, or broken flows
        - Agent returns: list of ux.md changes made
     3. Re-check ux.md inline: does every flow have an exit path and error handling?
     4. Remove resolved items.

   If clean: proceed.
   If MAX reached: report "UX design STUCK after 3 iterations" with unresolved flows.
   ```

   **CONCERNS or CLEAN on all three, no STUCK verdicts** → proceed.

7. **Output the coordinator summary:**
   ```
   ✅ Phase 3 complete — plan.md written to project_plans/<PROJECT_NAME>/implementation/

   Epics: <N> | Stories: <N> | Tasks: <N>
   Flagged choices: <N> (ADRs written)
   Architecture review: <BLOCKED|CONCERNS|CLEAN> — <N> blockers, <N> concerns
   Adversarial review: <BLOCKED|CONCERNS|CLEAN> — <N> blockers, <N> concerns, <N> minors
   UX design: <N surfaces, N UX acceptance criteria | N/A — no user-facing surface>

   Next step: /sdd:4-validate
   ```

   Note: No fresh session required if proceeding to Phase 4 — all planning work happened in a subagent, not this thread.
