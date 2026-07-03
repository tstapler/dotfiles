---
description: "Phase 2 — Parallel research across 4 dimensions. Outputs: home_plans/<project>/research/*.md"
user-invocable: true
---

# home:2-research

Spawn 4 parallel subagents to research the home project. All research happens in subagents — the coordinator only reads summaries back.

## Instructions

1. **Follow [SETUP.md](SETUP.md)** — identify PROJECT_NAME, and mark this stage's task `in_progress` if a task tool is available (Check 3).

2. **Entry gate**: Read `home_plans/<PROJECT_NAME>/scope.md`. Halt if missing — run `/home:1-scope` first.

3. **Dispatch 4 research agents in parallel using the `Agent` tool** (all 4 in a single message — do not run sequentially):

   Each agent must include:
   - The full text of `scope.md`
   - Its specific research question
   - An instruction to **write its output directly to the target file** and return a 3-bullet summary
   - **The `meta-research-workflow` skill's Source Documentation Requirements**: cite a full URL and title for every non-obvious factual claim (price, code requirement, safety statistic, common failure mode); no fact without attribution; end the file with a `## Sources` list of every URL cited.

   **Agent 1 — Methods** → writes `home_plans/<PROJECT_NAME>/research/methods.md`:
   > Research the best approach(es) for this home project. What are the standard DIY methods? When does it make sense to hire a professional versus DIY? What specific techniques, tools, or skills are required? What does a professional approach look like versus a competent DIYer? What YouTube channels, subreddits (r/DIY, r/HomeImprovement, r/Plumbing, etc.), or resources are most authoritative for this type of project? Follow the `meta-research-workflow` skill's sourcing requirements. Write your findings to `home_plans/<PROJECT_NAME>/research/methods.md` with a trailing `## Sources` list, then return a 3-bullet summary.

   **Agent 2 — Materials** → writes `home_plans/<PROJECT_NAME>/research/materials.md`:
   > Research the materials, products, and supplies needed for this project. What specific products are community-recommended (not just brand-sponsored)? What are the quality tiers and price ranges? What quantities will be needed? What are the best places to purchase (Lowe's, Home Depot, Amazon, specialty suppliers)? Are there any products to avoid based on common complaints? Follow the `review-longevity-research` skill for how to dig up community reviews and longevity signals, and the `meta-research-workflow` skill's sourcing requirements for every price/quality claim.
   >
   > **Before writing new wiki content**, `Grep`/`Glob` `logseq/pages/` for existing pages on each retailer, product, or part you plan to recommend. If a page already exists, read it and do not duplicate it — only add genuinely new information you learned (a better price, a new caveat, a better source) as an update to that existing page, and reuse it in your links.
   >
   > For each retailer, specific product, or reusable part that does **not** already have a wiki page and is distinctive enough to plausibly recur in future home projects (skip one-off consumables like a single tube of caulk), create a page at `logseq/pages/<Name>.md` following the **Product & Retailer Zettel Template** in the `knowledge-synthesis` skill (core definition, price/quality tier, source URL, links to the retailer and related products, tags including `#[[Products]]`).
   >
   > Write your findings to `home_plans/<PROJECT_NAME>/research/materials.md`, using `[[Product Name]]` wiki-links for anything with a wiki page, with a trailing `## Sources` list, then return a 3-bullet summary plus a list of any new or updated wiki pages.

   **Agent 3 — Logistics** → writes `home_plans/<PROJECT_NAME>/research/logistics.md`:
   > Research the logistical requirements for this project. Are permits required, and if so, what type and approximate cost? What building codes or regulations apply (electrical codes, plumbing codes, structural requirements)? What inspections are required? If hiring a contractor, what licenses should they hold, and what does fair market pricing look like? What is the realistic timeline including drying times, cure times, delivery lead times, and contractor scheduling? Follow the `meta-research-workflow` skill's sourcing requirements for every code/permit claim. Write your findings to `home_plans/<PROJECT_NAME>/research/logistics.md` with a trailing `## Sources` list, then return a 3-bullet summary.

   **Agent 4 — Risks** → writes `home_plans/<PROJECT_NAME>/research/risks.md`:
   > Research the safety hazards, common mistakes, and hidden costs for this type of project. What are the most frequent DIY errors that make the job harder or cause damage? What safety precautions are non-negotiable? What hidden costs or surprises commonly blow budgets? What "while you're in there" work is commonly discovered and how much does it add? What are the failure modes if this is done incorrectly? Follow the `review-longevity-research` skill for mining common-failure-mode clusters from community sources, and the `meta-research-workflow` skill's sourcing requirements for every claim. Write your findings to `home_plans/<PROJECT_NAME>/research/risks.md` with a trailing `## Sources` list, then return a 3-bullet summary.

4. **Wait for all 4 agents to complete.** Do not summarise until all have returned.

5. **Exit gate**: verify all 4 files exist under `home_plans/<PROJECT_NAME>/research/` and are non-trivial (each has real content and a `## Sources` list, not a stub). Mark this stage's task `completed` if a task tool is available, then synthesise the 4 agent summaries:
   ```
   ✅ Phase 2 complete — research written to home_plans/<PROJECT_NAME>/research/

   Key findings:
   - Methods: <1-line summary>
   - Materials: <1-line summary and rough cost estimate>
   - Logistics: <permits required? contractor licensing? timeline?>
   - Top risk: <1 critical pitfall to watch>
   - New/updated wiki pages: <list from Agent 2, or "none">

   Next step: /home:3-plan
   ```
