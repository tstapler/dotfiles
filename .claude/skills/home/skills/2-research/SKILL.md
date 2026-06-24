---
description: "Phase 2 — Parallel research across 4 dimensions. Outputs: home_plans/<project>/research/*.md"
user-invocable: true
---

# home:2-research

Spawn 4 parallel subagents to research the home project. All research happens in subagents — the coordinator only reads summaries back.

## Instructions

1. **Follow [SETUP.md](SETUP.md)** — identify PROJECT_NAME.

2. **Read `home_plans/<PROJECT_NAME>/scope.md`.** Halt if missing — run `/home:1-scope` first.

3. **Dispatch 4 research agents in parallel using the `Agent` tool** (all 4 in a single message — do not run sequentially):

   Each agent must include:
   - The full text of `scope.md`
   - Its specific research question
   - An instruction to **write its output directly to the target file** and return a 3-bullet summary

   **Agent 1 — Methods** → writes `home_plans/<PROJECT_NAME>/research/methods.md`:
   > Research the best approach(es) for this home project. What are the standard DIY methods? When does it make sense to hire a professional versus DIY? What specific techniques, tools, or skills are required? What does a professional approach look like versus a competent DIYer? What YouTube channels, subreddits (r/DIY, r/HomeImprovement, r/Plumbing, etc.), or resources are most authoritative for this type of project? Write your findings to `home_plans/<PROJECT_NAME>/research/methods.md`, then return a 3-bullet summary.

   **Agent 2 — Materials** → writes `home_plans/<PROJECT_NAME>/research/materials.md`:
   > Research the materials, products, and supplies needed for this project. What specific products are community-recommended (not just brand-sponsored)? What are the quality tiers and price ranges? What quantities will be needed? What are the best places to purchase (Lowe's, Home Depot, Amazon, specialty suppliers)? Are there any products to avoid based on common complaints? Write your findings to `home_plans/<PROJECT_NAME>/research/materials.md`, then return a 3-bullet summary.

   **Agent 3 — Logistics** → writes `home_plans/<PROJECT_NAME>/research/logistics.md`:
   > Research the logistical requirements for this project. Are permits required, and if so, what type and approximate cost? What building codes or regulations apply (electrical codes, plumbing codes, structural requirements)? What inspections are required? If hiring a contractor, what licenses should they hold, and what does fair market pricing look like? What is the realistic timeline including drying times, cure times, delivery lead times, and contractor scheduling? Write your findings to `home_plans/<PROJECT_NAME>/research/logistics.md`, then return a 3-bullet summary.

   **Agent 4 — Risks** → writes `home_plans/<PROJECT_NAME>/research/risks.md`:
   > Research the safety hazards, common mistakes, and hidden costs for this type of project. What are the most frequent DIY errors that make the job harder or cause damage? What safety precautions are non-negotiable? What hidden costs or surprises commonly blow budgets? What "while you're in there" work is commonly discovered and how much does it add? What are the failure modes if this is done incorrectly? Write your findings to `home_plans/<PROJECT_NAME>/research/risks.md`, then return a 3-bullet summary.

4. **Wait for all 4 agents to complete.** Do not summarise until all have returned.

5. **Synthesise** the 4 agent summaries:
   ```
   ✅ Phase 2 complete — research written to home_plans/<PROJECT_NAME>/research/

   Key findings:
   - Methods: <1-line summary>
   - Materials: <1-line summary and rough cost estimate>
   - Logistics: <permits required? contractor licensing? timeline?>
   - Top risk: <1 critical pitfall to watch>

   Next step: /home:3-plan
   ```
