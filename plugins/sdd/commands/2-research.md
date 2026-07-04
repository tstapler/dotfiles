---
description: "Phase 2 — Parallel research across 4 dimensions. Outputs: project_plans/<project>/research/*.md"
user-invocable: true
---

# sdd:2-research

Spawn 4 parallel subagents to research the problem. All research happens in subagents — the coordinator (this thread) only reads summaries back, keeping context clean for implementation.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Read `project_plans/<PROJECT_NAME>/requirements.md`.** Halt if missing — run `/sdd:1-ideate` first.

3. **Check for existing hotspot/architecture analysis before dispatching fresh research.** Search
   the repo for any prior maintainability or architecture work touching the same file(s)/module(s)
   named in `requirements.md`:
   - `docs/architecture-audit-*.md` — complexity×churn hotspot analyses (see the
     `code-hotspot-analysis` skill)
   - `docs/architecture-review-*.md` — prior targeted architecture reviews (see the
     `quality:architecture-review` skill)
   - Any `project_plans/*/research/architecture.md` from an earlier SDD run covering an
     overlapping file/module

   If a match exists, note its path and a one-line summary of its relevant findings — this gets
   handed to Agent 3 below instead of having it re-derive the same analysis from scratch. If
   nothing matches, proceed as normal; this is a cheap grep, not a blocker.

4. **Dispatch 4 research agents in parallel using the `Task` tool** (all 4 in a single message — do not run sequentially):

   Each agent prompt must include:
   - The full text of `requirements.md`
   - Its specific research question (below)
   - An instruction to **write its output directly to the target file** and return a 3-bullet summary

   **Agent 1 — Stack** → writes `project_plans/<PROJECT_NAME>/research/stack.md`:
   > Research the technology stack for this feature. Which specific libraries, frameworks, versions, and patterns apply? What dependencies will be needed? What are the current community-recommended versions? Write your findings to `project_plans/<PROJECT_NAME>/research/stack.md`, then return a 3-bullet summary.

   **Agent 2 — Features** → writes `project_plans/<PROJECT_NAME>/research/features.md`:
   > Research the feature landscape for this requirement. What similar features exist in the codebase or industry? What edge cases and failure modes should the design handle? What are users' unstated needs beyond the explicit requirements? Write your findings to `project_plans/<PROJECT_NAME>/research/features.md`, then return a 3-bullet summary.

   **Agent 3 — Architecture** → writes `project_plans/<PROJECT_NAME>/research/architecture.md`:
   > Research the architecture approach. What architectural patterns apply to this type of problem? What are the integration points with existing systems? What are the data flow and consistency requirements? Write your findings to `project_plans/<PROJECT_NAME>/research/architecture.md`, then return a 3-bullet summary.
   >
   > If step 3 above found an existing hotspot/architecture analysis covering this area, its path is: `<path from step 3, or "none found">`. Read it first and build on it explicitly — cite its findings by file:line where relevant instead of re-deriving them, and focus your own research on filling gaps it didn't cover (e.g. it may have flagged *that* a class is a God Object without researching *how* this specific requirement should be layered around it). Do not silently ignore it and produce a parallel, disconnected analysis.

   **Agent 4 — Pitfalls** → writes `project_plans/<PROJECT_NAME>/research/pitfalls.md`:
   > Research known pitfalls and risks for this type of feature. What commonly goes wrong? What are the risks in the chosen stack? What should be explicitly designed against? Write your findings to `project_plans/<PROJECT_NAME>/research/pitfalls.md`, then return a 3-bullet summary.

5. **Wait for all 4 agents to complete.** Do not summarise until all have returned.

6. **Synthesise** the 4 agent summaries (do not re-read the full files — use the summaries they returned):
   ```
   ✅ Phase 2 complete — research written to project_plans/<PROJECT_NAME>/research/

   Key findings:
   - Stack: <1-line summary>
   - Architecture: <1-line summary>
   - Top risk: <1 pitfall to watch>
   - Prior analysis incorporated: <path, or "none found">

   Next step: /sdd:3-plan
   ```
