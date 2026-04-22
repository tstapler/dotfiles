---
description: "Phase 2 — Parallel research across 4 dimensions. Outputs: project_plans/<project>/research/*.md"
user-invocable: true
---

# sdd:2-research

Spawn 4 parallel subagents to research the problem. All research happens in subagents — the coordinator (this thread) only reads summaries back, keeping context clean for implementation.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Read `project_plans/<PROJECT_NAME>/requirements.md`.** Halt if missing — run `/sdd:1-ideate` first.

3. **Dispatch 4 research agents in parallel using the `Task` tool** (all 4 in a single message — do not run sequentially):

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

   **Agent 4 — Pitfalls** → writes `project_plans/<PROJECT_NAME>/research/pitfalls.md`:
   > Research known pitfalls and risks for this type of feature. What commonly goes wrong? What are the risks in the chosen stack? What should be explicitly designed against? Write your findings to `project_plans/<PROJECT_NAME>/research/pitfalls.md`, then return a 3-bullet summary.

4. **Wait for all 4 agents to complete.** Do not summarise until all have returned.

5. **Synthesise** the 4 agent summaries (do not re-read the full files — use the summaries they returned):
   ```
   ✅ Phase 2 complete — research written to project_plans/<PROJECT_NAME>/research/

   Key findings:
   - Stack: <1-line summary>
   - Architecture: <1-line summary>
   - Top risk: <1 pitfall to watch>

   Next step: /sdd:3-plan
   ```
