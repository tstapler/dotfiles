---
description: "Phase 2 — Parallel research across 4 dimensions. Outputs: project_plans/<project>/research/*.md"
user-invocable: true
---

# sdd:2-research

Spawn 4 parallel research agents to investigate the problem from independent dimensions.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Read `project_plans/<PROJECT_NAME>/requirements.md`.** Halt if missing — run `/sdd:1-ideate` first.

3. **Spawn 4 agents in parallel** using the Task tool, each with the requirements.md content as context:

   **Agent 1 — Stack** (`research/stack.md`):
   > Research the technology stack for this feature. Which specific libraries, frameworks, versions, and patterns apply? What dependencies will be needed? What are the current community-recommended versions?

   **Agent 2 — Features** (`research/features.md`):
   > Research the feature landscape. What similar features exist in the codebase or industry? What edge cases and failure modes should the design handle? What are users' unstated needs beyond the explicit requirements?

   **Agent 3 — Architecture** (`research/architecture.md`):
   > Research the architecture approach. What architectural patterns apply to this type of problem? What are the integration points with existing systems? What are the data flow and consistency requirements?

   **Agent 4 — Pitfalls** (`research/pitfalls.md`):
   > Research known pitfalls and risks. What commonly goes wrong with this type of feature? What risks exist in the chosen stack? What should be explicitly designed against?

4. **Write each agent's output** to `project_plans/<PROJECT_NAME>/research/<dimension>.md`.

5. **Synthesise** a brief summary of the 4 research outputs and output:
   ```
   ✅ Phase 2 complete — research written to project_plans/<PROJECT_NAME>/research/

   Key findings:
   - Stack: <1-line summary>
   - Architecture: <1-line summary>
   - Top risk: <1 pitfall to watch>

   Next step: /sdd:3-plan
   ```
