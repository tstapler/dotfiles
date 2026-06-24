---
description: "Phase 3 — Task breakdown, materials list, and budget. Outputs: home_plans/<project>/plan.md"
user-invocable: true
---

# home:3-plan

Dispatch a planning subagent to produce the full project plan — task sequence, materials list, budget, and timeline. Then run an adversarial reviewer to catch gaps before work begins.

## Instructions

1. **Follow [SETUP.md](SETUP.md)** — identify PROJECT_NAME.

2. **Read all inputs (coordinator reads these to pass to subagent):**
   - `home_plans/<PROJECT_NAME>/scope.md` — halt if missing, run `/home:1-scope` first
   - `home_plans/<PROJECT_NAME>/research/methods.md` — warn if missing, continue with scope only
   - `home_plans/<PROJECT_NAME>/research/materials.md`
   - `home_plans/<PROJECT_NAME>/research/logistics.md`
   - `home_plans/<PROJECT_NAME>/research/risks.md`

3. **Dispatch a planning subagent using the `Agent` tool.**

   The subagent prompt must include:
   - Full text of `scope.md`
   - Full text of all research files (if present)
   - These exact instructions:

   > You are a home project planning subagent. Produce a complete, actionable project plan.
   >
   > **Step 1:** Review the scope and research. Identify whether any permits are required — if so, note them prominently at the top of the plan.
   >
   > **Step 2:** Write `home_plans/<PROJECT_NAME>/plan.md` following the template below. Use concrete product names and quantities — no vague references. Tasks should be sized for a single work session (30 min–3 hrs each).
   >
   > **Step 3:** Return a summary: phase count, task count, total budget estimate, whether permits are required.

   Plan template:
   ```markdown
   # Project Plan: <PROJECT_NAME>

   **Date**: <YYYY-MM-DD>
   **Project**: <one-line description>
   **Status**: Ready to execute
   **Permits Required**: Yes/No — <type and estimated cost if yes>
   **Estimated Total Cost**: $<low>–$<high>
   **Estimated Duration**: <X days / X weekends>

   ---

   ## ⚠️ Safety Precautions
   <Non-negotiable safety steps — utilities to shut off, PPE required, hazards to avoid>

   ---

   ## Task Sequence

   ### Phase 1: Prep & Procurement
   #### Task 1.1: <name> (~<duration>)
   - <Step-by-step actions>
   - **Done when**: <specific observable completion criterion>

   #### Task 1.2: <name> (~<duration>)
   ...

   ### Phase 2: <Core Work Phase Name>
   #### Task 2.1: <name> (~<duration>)
   ...

   ### Phase 3: Finishing & Cleanup
   #### Task 3.1: <name> (~<duration>)
   ...

   ---

   ## Materials List

   | Item | Spec / Model | Qty | Unit Cost | Total | Source |
   |------|-------------|-----|-----------|-------|--------|
   | <item> | <specific product or spec> | <N> | $<X> | $<X> | Lowe's / Amazon / etc. |

   **Materials subtotal**: $<X>

   ---

   ## Tools Required

   | Tool | Own / Rent / Buy |
   |------|-----------------|
   | <tool> | Own |
   | <tool> | Rent from Home Depot (~$<X>/day) |

   ---

   ## Budget Breakdown

   | Category | Estimate |
   |----------|---------|
   | Materials | $<X> |
   | Tool rental | $<X> |
   | Permits | $<X> |
   | Contractor labor (if any) | $<X> |
   | Contingency (15%) | $<X> |
   | **Total** | **$<X>–$<X>** |

   ---

   ## Timeline

   | Day / Weekend | Work |
   |--------------|------|
   | Day 1 | <tasks> |
   | Day 2 | <tasks> |

   ---

   ## Contractor Requirements
   <If any work requires a licensed contractor: what license, what scope, and what to verify before hiring>
   <"None required" if fully DIY>

   ---

   ## Decisions & Open Questions
   <Any choices that need to be made before or during execution>
   ```

4. **Wait for the subagent to complete.** Do not continue until plan.md has been written.

5. **Dispatch an adversarial reviewer subagent using the `Agent` tool.**

   The subagent prompt must include:
   - Full text of `plan.md`
   - Full text of `scope.md`
   - These exact instructions:

   > You are an adversarial reviewer for a home project plan. Find gaps before any work begins.
   >
   > Review for:
   > 1. **Missing safety steps** — Are there hazards (electrical, plumbing, structural, chemical) without explicit precautions? Should utilities be shut off? Is PPE specified?
   > 2. **Permit gaps** — Does the scope require a permit that isn't noted? (Electrical work, structural changes, plumbing changes, HVAC modifications often require permits.)
   > 3. **Budget underestimates** — Are costs realistic? Are common hidden costs (demo surprises, disposal fees, primer coats, drying time, re-work) accounted for? Is the contingency sufficient?
   > 4. **Sequencing errors** — Are any tasks ordered incorrectly? (e.g., painting before priming, installing before measuring, ordering materials without lead time buffer)
   > 5. **Missing materials** — Are consumables (sandpaper, tape, drop cloths, fasteners, caulk, primer) accounted for?
   > 6. **Scope creep** — Are any tasks broader than what the scope asked for?
   > 7. **Pet and occupant safety** — Are there steps requiring the space to be vacated? Toxic fumes? Sharp debris?
   >
   > For each concern, classify as:
   > - **BLOCKER** — Must be resolved before work starts (safety hazard, required permit, impossible task sequence)
   > - **CONCERN** — Should be addressed; will likely cause problems if ignored
   > - **MINOR** — Low impact; note it but don't block
   >
   > Write findings to `home_plans/<PROJECT_NAME>/adversarial-review.md`:
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

6. **Wait for the adversarial reviewer to complete.** Read the summary.

   - **BLOCKED** → read adversarial-review.md, patch plan.md to resolve each BLOCKER, then re-run the adversarial reviewer on the updated plan (repeat until CONCERNS or CLEAN).
   - **CONCERNS or CLEAN** → proceed.

7. **Output the coordinator summary:**
   ```
   ✅ Phase 3 complete — plan.md written to home_plans/<PROJECT_NAME>/

   Phases: <N> | Tasks: <N>
   Budget estimate: $<X>–$<X>
   Permits required: Yes/No
   Adversarial review: <BLOCKED|CONCERNS|CLEAN> — <N> blockers, <N> concerns, <N> minors

   Next step: /home:4-prep
   ```
