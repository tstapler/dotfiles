---
description: "Phase 2 — Parallel research across 6 dimensions. Outputs: project_plans/<project>/research/*.md"
user-invocable: true
---

# sdd:2-research

Spawn 6 parallel subagents to research the problem — covering stack, features, architecture, pitfalls, UX, and build-vs-buy. All research happens in subagents — the coordinator (this thread) only reads summaries back, keeping context clean for implementation.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Read `project_plans/<PROJECT_NAME>/requirements.md`.** Halt if missing — run `/sdd:1-ideate` first.

2.5. **Calibrate research depth from the Complexity field in requirements.md**:
   - **Complexity 1** (quick task): run Agents 1, 4, 6 only (stack, pitfalls, build-vs-buy). Skip agents 2, 3, 5 unless requirements mention edge cases, architecture, or UX.
   - **Complexity 2–3** (feature / system design): run all 6 agents.
   - **Complexity 4** (high-stakes): run all 6 agents. In Agent 3's prompt, add: "Separately evaluate failure modes specific to the migration or compliance aspect."
   - If no Complexity field found in requirements.md: default to all 6 agents.

3. **Dispatch research agents in parallel using the `Task` tool** (all 6 in a single message — do not run sequentially):

   Each agent prompt must include:
   - The full text of `requirements.md`
   - Its specific research question (below)
   - An instruction to **write its output directly to the target file** and return a 3-bullet summary

   **Agent 1 — Stack** → writes `project_plans/<PROJECT_NAME>/research/stack.md`:
   > Research the technology stack for this feature. Which specific libraries, frameworks, versions, and patterns apply? What dependencies will be needed? What are the current community-recommended versions? Write your findings to `project_plans/<PROJECT_NAME>/research/stack.md`, then return a 3-bullet summary.

   **Agent 2 — Features** → writes `project_plans/<PROJECT_NAME>/research/features.md`:
   > Research the feature landscape for this requirement. What similar features exist in the codebase or industry? What edge cases and failure modes should the design handle? What are users' unstated needs beyond the explicit requirements? Write your findings to `project_plans/<PROJECT_NAME>/research/features.md`, then return a 3-bullet summary.

   **Agent 3 — Architecture** → writes `project_plans/<PROJECT_NAME>/research/architecture.md`:
   > Research the architecture approach. What architectural patterns apply to this type of problem? What are the integration points with existing systems? What are the data flow and consistency requirements?
   >
   > **If the requirements describe a complex business domain involving multiple actors, systems, or business rules** (not simple CRUD): produce an Event-Command-Policy table using EventStorming grammar. This surfaces bounded context boundaries and business rules before planning begins:
   >
   > | Domain Event (what happened) | Policy trigger (whenever X, then…) | Command (intent to change state) | Actor / System |
   > |---|---|---|---|
   > | `<Noun> <Past-tense verb>` | `Whenever <event>, then <command>` | `<Verb> <Noun>` | `<User role / Service name>` |
   >
   > Skip this table for simple CRUD features with no multi-step business logic.
   >
   > Write your findings to `project_plans/<PROJECT_NAME>/research/architecture.md`, then return a 3-bullet summary.

   **Agent 4 — Pitfalls** → writes `project_plans/<PROJECT_NAME>/research/pitfalls.md`:
   > Research known pitfalls and risks for this type of feature. What commonly goes wrong? What are the risks in the chosen stack? What should be explicitly designed against? Write your findings to `project_plans/<PROJECT_NAME>/research/pitfalls.md`, then return a 3-bullet summary.

   **Agent 5 — UX Research** → writes `project_plans/<PROJECT_NAME>/research/ux.md`:
   > Research the user experience for this feature. Cover: (1) comparable UX patterns in similar products — what interaction flows work well and why; (2) user mental models and expectations for this type of feature; (3) accessibility requirements (WCAG, ARIA, keyboard navigation) that apply; (4) error states and edge cases that must have graceful UX handling; (5) the job-to-be-done lens — what functional, emotional, and social jobs does this feature fulfill for the user? Skip if this feature has no user-facing surface (pure infrastructure). Write your findings to `project_plans/<PROJECT_NAME>/research/ux.md`, then return a 3-bullet summary.

   **Agent 6 — Build vs. Buy** → writes `project_plans/<PROJECT_NAME>/research/build-vs-buy.md`:
   > Research whether this feature should be built from scratch or sourced from an existing solution. Evaluate each option below and recommend the best approach with rationale:
   > 1. **Existing OSS library or framework** — what packages exist that solve all or part of this? Assess: maturity, maintenance, license, fit to requirements, and what would need custom wrapping.
   > 2. **SaaS / managed API** — does a hosted service already do this? Assess: cost, data residency, vendor lock-in, and integration complexity.
   > 3. **LLM-generated implementation vs. battle-tested library** — for any algorithm or data structure involved: compare the correctness risk of a bespoke LLM-generated implementation against adopting a widely-used, tested library. When is custom code worth the maintenance burden? When is it reckless?
   > 4. **Fork or adapt** — is there an existing implementation close enough to fork or adapt rather than build from scratch?
   > For each option: Pros / Cons / Verdict (Recommended / Viable / Not recommended).
   > Write your findings to `project_plans/<PROJECT_NAME>/research/build-vs-buy.md`, then return a 3-bullet summary.

4. **Wait for all agents to complete.** Do not summarise until all have returned.

4.5. **Open question resolution gate.** Check requirements.md → `## Open Questions`:
   - For each question, scan the research files to see if any agent answered it.
   - If all open questions are answered: proceed to synthesis.
   - If any remain unanswered, ask the user via `AskUserQuestion`:
     ```
     header: "Open questions"
     question: "The following questions from requirements.md were not resolved by research: <list>. How would you like to proceed?"
     options:
       - "Accept the uncertainty — add to plan.md Unresolved Questions and continue"
       - "I'll answer one now (click Other)"
       - "Halt — research these further before planning"
     ```
   - If user proceeds with open questions: add them to requirements.md under `## Open Questions` with a note `*(unresolved after Phase 2 research)*`.

5. **Synthesise** the 6 agent summaries (do not re-read the full files — use the summaries they returned):
   ```
   ✅ Phase 2 complete — research written to project_plans/<PROJECT_NAME>/research/

   Key findings:
   - Stack: <1-line summary>
   - Architecture: <1-line summary>
   - Features: <1-line summary of edge cases, unstated needs, or comparable implementations found>
   - UX: <1-line summary, or "N/A — no user-facing surface">
   - Build vs. Buy recommendation: <1-line: build / adopt <library> / use <SaaS>>
   - Top risk: <1 pitfall to watch>

   Next step: /sdd:3-plan
   ```
