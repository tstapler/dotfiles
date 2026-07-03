---
description: "Full home project workflow — scope → research → plan → prep. Research and planning run in subagents. Hand off to /home:5-execute when ready to work."
argument-hint: "[project description]"
user-invocable: true
---

# home:full

Guide the complete home project planning workflow in one session. Scope interview runs here; research and planning offload to subagents. Stop after the readiness gate — physical execution is tracked separately with `/home:5-execute`.

## Persistent home context (always apply)

- **Hardware**: All interior hardware at 711 N 60th must use **knobs, not lever handles** — Mochi (the dog) opens levers.
- **Aesthetic (Rebekah)**: Sage/forest green, warm honey/walnut wood, brass hardware, artisan materials, biophilic/plants. **Never** chrome, cool gray, or stark white minimalism. See `logseq/pages/Rebekah Reynolds Taste Profile.md` for full detail.
- **Retailer preference**: Lowe's first, Amazon second.
- **Location**: 711 N 60th Street, Seattle, WA — Seattle DCI permits apply.

---

## Phase 1 — Scope (this thread)

### Step 1: Identify project name

- If `$1` was provided, derive a short kebab-case slug from it (e.g. "fix leaky faucet" → `leaky-faucet`).
- If `home_plans/` has existing subdirectories, list them and ask whether to continue an existing project or start a new one.
- Otherwise ask the user for a short kebab-case project name.

Store as `PROJECT_NAME`. Create `home_plans/<PROJECT_NAME>/` if it doesn't exist.

**Track progress with the task tool (if available).** Each phase below is a discrete stage with an entry gate and an exit gate. If a task tool is available in this environment, create one task per phase now (Scope, Research, Plan, Prep) and update status as each stage starts/passes its exit gate — this preserves position if the session is interrupted. Claude Code: `TaskCreate`/`TaskUpdate`. Gemini CLI/Antigravity: `write_todos`. If no task tool is available, skip this — it's a convenience, not a requirement. Mark the Scope task `in_progress` now.

### Step 2: Load wiki context

Before asking any questions, check `logseq/pages/` for pages about the space or topic (e.g. "711 N 60th Kitchen", "Primary Bedroom", "711 N 60th.md"). Extract any known dimensions, constraints, or prior decisions. Use this to pre-fill scope answers and skip questions the wiki already answers.

### Step 3: Scope interview

**Do not propose solutions, materials, or approaches.** Extract what the user already said in their message. Then ask only what's genuinely unclear.

Minimum required to write scope.md:
- What specifically needs to happen and why
- Budget range
- DIY / contractor / hybrid
- Timeline / urgency
- Hard constraints (space dimensions, permit sensitivity, aesthetic)

Use `AskUserQuestion` to cover any gaps — combine into as few questions as possible. Skip questions the user already answered or the wiki already resolved.

### Step 4: Write `home_plans/<PROJECT_NAME>/scope.md`

```markdown
# Scope: <PROJECT_NAME>

**Date**: <YYYY-MM-DD>
**Area**: <kitchen | bathroom | bedroom | outdoor | garage | basement | other>
**Type**: <repair | installation | organization | maintenance | renovation>

## Problem / Goal
<What needs to happen and why. One clear paragraph.>

## Success Criteria
<What does done look like?>

## Constraints

### Budget
<Approved budget range>

### Timeline
<Deadline or target, or "no hard deadline">

### Labor Approach
<DIY / contractor / hybrid>

### Disruption Tolerance
<What is acceptable during the project>

### Physical Constraints
<Hardware, aesthetic, pet safety, HOA, dimensions, etc.>

## Out of Scope
<Explicit exclusions>

## Open Questions
<Anything unresolved that research should answer>
```

### Step 5: Exit gate and continue

Verify `scope.md` was actually written and is non-empty before advancing. Mark the Scope task `completed` if a task tool is available.

```
header: "Continue?"
question: "scope.md written. Run research and planning now?"
options:
  - "Yes — run all phases now"
  - "No — I want to review scope.md first (resume with /home:full)"
```

If "No": stop. User resumes by re-running `/home:full` (it will detect the existing project).

---

## Phase 2 — Research (subagents)

**Entry gate**: Read `home_plans/<PROJECT_NAME>/scope.md`. Halt if missing — that means Phase 1 didn't complete. Mark the Research task `in_progress` if a task tool is available. Dispatch **4 parallel subagents** in a single `Agent` tool call. Each receives the full scope.md text and writes its output directly to the target file.

**Every agent must follow the `research-workflow` skill's Source Documentation Requirements**: cite a full URL and title for every non-obvious factual claim (price, code requirement, safety statistic, common failure mode); no fact without attribution; end its file with a `## Sources` list of every URL cited.

**Agent 1 — Methods** → `home_plans/<PROJECT_NAME>/research/methods.md`
> Research the best DIY approaches for this project. What are the standard methods? What skills and tools are required? When should a pro be hired instead? What resources (YouTube, subreddits, guides) are authoritative for this type of work? Follow the `research-workflow` skill's sourcing requirements. Write findings to the target file with a trailing `## Sources` list, then return a 3-bullet summary.

**Agent 2 — Materials** → `home_plans/<PROJECT_NAME>/research/materials.md`
> Research materials, products, and supplies needed. What are community-recommended products (not brand-sponsored)? What are the quality tiers and price ranges? What quantities are needed? Prefer Lowe's, then Amazon. Note anything to avoid based on common complaints. Follow the `review-longevity-research` skill for how to dig up community reviews and longevity signals, and the `research-workflow` skill's sourcing requirements for every price/quality claim.
>
> **Before writing new wiki content**, `Grep`/`Glob` `logseq/pages/` for existing pages on each retailer, product, or part you plan to recommend. If a page already exists, read it and don't duplicate it — only add genuinely new information you learned (a better price, a caveat, a better source) as an update, and reuse it in your links.
>
> For each retailer, specific product, or reusable part that does **not** already have a wiki page and is distinctive enough to plausibly recur in future home projects (skip one-off consumables like a single tube of caulk), create a page at `logseq/pages/<Name>.md` following the **Product & Retailer Zettel Template** in the `knowledge-synthesis` skill (core definition, price/quality tier, source URL, links to the retailer and related products, tags including `#[[Products]]`).
>
> Write findings to the target file, using `[[Product Name]]` wiki-links for anything with a wiki page, with a trailing `## Sources` list, then return a 3-bullet summary plus a list of any new or updated wiki pages.

**Agent 3 — Logistics** → `home_plans/<PROJECT_NAME>/research/logistics.md`
> Research permits, codes, and logistics. Are permits required (Seattle DCI)? What building codes apply? What inspections are needed? What is the realistic timeline including cure times, delivery lead times, and scheduling? Follow the `research-workflow` skill's sourcing requirements for every code/permit claim. Write findings to the target file with a trailing `## Sources` list, then return a 3-bullet summary.

**Agent 4 — Risks** → `home_plans/<PROJECT_NAME>/research/risks.md`
> Research safety hazards, common DIY mistakes, and hidden costs. What are the most frequent errors for this type of project? What safety precautions are non-negotiable? What hidden costs or surprises commonly blow budgets? What failure modes exist if done incorrectly? Follow the `review-longevity-research` skill for mining common-failure-mode clusters from community sources, and the `research-workflow` skill's sourcing requirements for every claim. Write findings to the target file with a trailing `## Sources` list, then return a 3-bullet summary.

**Exit gate**: wait for all 4 to complete, then verify all 4 files exist and are non-trivial (real content, not stubs) before proceeding. Mark the Research task `completed` if a task tool is available. Note any new/updated wiki pages (from Agent 2) when reporting the Phase 2 result to the user.

---

## Phase 3 — Plan (subagents)

**Entry gate**: confirm the 4 research files from Phase 2 exist (or that Phase 2 was explicitly skipped). Mark the Plan task `in_progress` if a task tool is available.

### Planning subagent

Dispatch a planning subagent with the full text of scope.md and all 4 research files.

> You are a home project planning subagent. Read the scope and research provided. Produce a complete, actionable project plan and write it to `home_plans/<PROJECT_NAME>/plan.md`. Ground the plan in the research provided — do not invent facts the research doesn't support.
>
> The plan must include: safety precautions, task sequence (tasks sized 30min–3hrs each), materials list with specific products and quantities, tools list, budget breakdown, and timeline. Use concrete product names — no vague references. Flag any permits required at the top. Where a research file linked a product to a wiki page (`[[Product Name]]`), reuse that same wiki-link in the Materials List instead of plain text. Carry forward source citations from the research files — every non-obvious budget, code, or safety claim should trace to a source, listed in the plan's trailing `## Sources` section.
>
> Plan template:
>
> ```markdown
> # Project Plan: <PROJECT_NAME>
>
> **Date**: <YYYY-MM-DD>
> **Permits Required**: Yes/No — <type if yes>
> **Estimated Total Cost**: $<low>–$<high>
> **Estimated Duration**: <X days / weekends>
>
> ## ⚠️ Safety Precautions
> <Utilities to shut off, PPE, hazards, pet safety>
>
> ## Task Sequence
>
> ### Phase 1: Prep & Procurement
> #### Task 1.1: <name> (~<duration>)
> - <steps>
> - **Done when**: <observable criterion>
>
> ### Phase 2: <Core Work>
> #### Task 2.1: ...
>
> ### Phase 3: Finishing & Cleanup
> #### Task 3.1: ...
>
> ## Materials List
>
> | Item | Spec / Model | Qty | Unit Cost | Total | Source |
> |------|-------------|-----|-----------|-------|--------|
>
> **Materials subtotal**: $<X>
>
> ## Tools Required
>
> | Tool | Own / Rent / Buy |
> |------|-----------------|
>
> ## Budget Breakdown
>
> | Category | Estimate |
> |----------|---------|
> | Materials | $<X> |
> | Tool rental | $<X> |
> | Permits | $<X> |
> | Contingency (15%) | $<X> |
> | **Total** | **$<X>–$<X>** |
>
> ## Timeline
>
> | Day / Weekend | Work |
> |--------------|------|
>
> ## Decisions & Open Questions
> <Choices to make before or during execution>
>
> ## Sources
> <URLs carried forward from the research files, backing the budget/code/safety claims above>
> ```
>
> Return: phase count, task count, total budget estimate, permits required (yes/no).

### Adversarial reviewer subagent

After plan.md is written, dispatch an adversarial reviewer subagent with the full text of plan.md and scope.md.

> You are an adversarial reviewer for a home project plan. Find gaps before any physical work begins.
>
> Review for: (1) missing safety steps — hazards without precautions, utilities not shut off, PPE not specified; (2) permit gaps — work that likely needs a Seattle permit; (3) budget underestimates — unrealistic costs, missing contingency, hidden costs; (4) sequencing errors — tasks in the wrong order; (5) missing consumables — sandpaper, tape, caulk, primer, fasteners; (6) pet/occupant safety — fumes, sharp debris, access restriction for Mochi; (7) missing citations — budget, code, or safety claims stated as fact with no source in the plan's `## Sources` section or the underlying research.
>
> Classify each finding:
> - **BLOCKER** — must resolve before work starts
> - **CONCERN** — will likely cause problems if ignored
> - **MINOR** — low impact
>
> Write findings to `home_plans/<PROJECT_NAME>/adversarial-review.md`:
>
> ```markdown
> # Adversarial Review: <PROJECT_NAME>
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
> Return: verdict + counts (blockers / concerns / minors).

If verdict is **BLOCKED**: read adversarial-review.md, patch plan.md to resolve each BLOCKER, re-run the adversarial reviewer. Repeat until CONCERNS or CLEAN.

**Exit gate**: confirm `plan.md` and `adversarial-review.md` both exist and are non-trivial, and that the verdict is CONCERNS or CLEAN — never advance past BLOCKED. Mark the Plan task `completed` if a task tool is available.

---

## Checkpoint

```
✅ Research and planning complete

Artifacts:
  home_plans/<PROJECT_NAME>/scope.md
  home_plans/<PROJECT_NAME>/research/methods.md
  home_plans/<PROJECT_NAME>/research/materials.md
  home_plans/<PROJECT_NAME>/research/logistics.md
  home_plans/<PROJECT_NAME>/research/risks.md
  home_plans/<PROJECT_NAME>/plan.md
  home_plans/<PROJECT_NAME>/adversarial-review.md

Budget estimate: $<X>–$<X>
Permits: <yes — <type> | no>
Plan: <N> phases, <N> tasks
Review: <BLOCKED|CONCERNS|CLEAN> — <N> blockers, <N> concerns
New/updated wiki pages: <list, or "none">
```

Ask:
```
header: "Continue to readiness check?"
question: "Plan complete. Run the readiness gate now?"
options:
  - "Yes — check readiness"
  - "No — I want to review plan.md first"
```

---

## Phase 4 — Prep (this thread)

**Entry gate**: confirm `plan.md` exists (it must, if Phase 3 completed). Mark the Prep task `in_progress` if a task tool is available.

Write `home_plans/<PROJECT_NAME>/prep-checklist.md` from plan.md:

```markdown
# Pre-Execution Checklist: <PROJECT_NAME>

**Date**: <YYYY-MM-DD>

## 🚫 Permits
- [ ] <permit type obtained, or confirmed not required>

## 🛒 Materials
- [ ] <Item> — <qty> — <source> — ~$<cost>
<!-- one line per item from materials list -->

## 🔧 Tools
- [ ] <tool> — owned / rent from <where> (~$<X>/day)

## 🏠 Space Prep
- [ ] Area cleared and furniture moved
- [ ] Drop cloths / floor protection in place

## 🐾 Pet & Occupant Safety
- [ ] Plan for Mochi during hazardous phases: <kennel / backyard / another room>
- [ ] <fume/debris/access steps if applicable>

## ⚡ Utility Shutoffs
- [ ] <what to shut off, or "None required">

## 🦺 Safety Gear
- [ ] <PPE items>

## 📋 Open Decisions
- [ ] <decisions to resolve before starting>

## Readiness Gate

| # | Check | Status |
|---|-------|--------|
| 1 | All materials purchased or confirmed in stock | ☐ |
| 2 | All tools available or rental reserved | ☐ |
| 3 | Permits obtained or confirmed not required | ☐ |
| 4 | No BLOCKERs in adversarial-review.md | ☐ |
| 5 | All open decisions resolved | ☐ |
| 6 | Pet plan in place for hazardous phases | ☐ |
```

Run the readiness gate (this is the exit gate — do not proceed past NOT READY):
- **READY** — all criteria met → proceed to handoff.
- **ALMOST** — minor gaps (materials not yet purchased, tools not yet rented) → note outstanding items, confirm user wants to proceed.
- **NOT READY** — blockers or permits unresolved → halt. List exactly what must happen before starting. Do not proceed.

Mark the Prep task `completed` if a task tool is available and the verdict is READY or ALMOST (leave it `in_progress` if NOT READY).

---

## Handoff

```
✅ Planning complete — ready to execute

  home_plans/<PROJECT_NAME>/prep-checklist.md

Budget: $<X>–$<X>
Permits: <yes/no>
Readiness: <READY | ALMOST — <what's outstanding> | NOT READY — <blockers>>

When you start working:
  /home:5-execute  — log each completed task, surprise, or cost deviation
  /home:6-close    — archive the project when all work is done
```
