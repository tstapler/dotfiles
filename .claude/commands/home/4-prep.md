---
description: "Phase 4 — Pre-execution readiness gate. Outputs: home_plans/<project>/prep-checklist.md"
user-invocable: true
---

# home:4-prep

Build a pre-execution readiness checklist from the project plan and run the readiness gate. **Do not start physical work until this gate passes.**

## HARD GATE

If any BLOCKER items are unchecked, work must not begin. Blockers are safety hazards, missing permits, or unavailable materials that will halt progress mid-job.

## Instructions

1. **Follow [SETUP.md](SETUP.md)** — identify PROJECT_NAME.

2. **Read required inputs:**
   - `home_plans/<PROJECT_NAME>/plan.md` — halt if missing, run `/home:3-plan` first
   - `home_plans/<PROJECT_NAME>/scope.md`
   - `home_plans/<PROJECT_NAME>/adversarial-review.md` (if present)

3. **Write `home_plans/<PROJECT_NAME>/prep-checklist.md`** based on the plan:

```markdown
# Pre-Execution Checklist: <PROJECT_NAME>

**Date**: <YYYY-MM-DD>
**Planned Start**: <date or "TBD">

---

## 🚫 Permits & Regulatory
- [ ] <permit type> — obtained? (or: not required for this project)

---

## 🛒 Materials
<!-- One line per item from the materials list in plan.md -->
- [ ] <Item name> — <qty> — from <source> — ~$<cost>
- [ ] ...

**Materials total**: ~$<X>

---

## 🔧 Tools
- [ ] <tool> — owned / rented (rent from: <where>, ~$<X>/day)
- [ ] ...

---

## 🏠 Space Preparation
- [ ] Area cleared and furniture moved
- [ ] Drop cloths / floor protection in place
- [ ] <any other prep specific to this project>

---

## 🐾 Occupant & Pet Safety
- [ ] Plan for Mochi during hazardous phases: <specify — kennel, back yard, another room>
- [ ] <Any toxic fumes, sharp debris, or access restriction steps>

---

## ⚡ Utility Shutoffs Required Before Starting
- [ ] <e.g., "Shut off water at main valve" — or "None required">

---

## 🦺 Safety Gear
- [ ] <PPE items: gloves, eye protection, respirator, knee pads, etc.>

---

## 📋 Outstanding Decisions
<!-- From plan.md Decisions & Open Questions section -->
- [ ] <decision to make before starting>

---

## Readiness Gate

| # | Check | Status |
|---|-------|--------|
| 1 | All materials purchased or confirmed in stock | |
| 2 | All tools available (owned or reserved for rental) | |
| 3 | Required permits obtained (or confirmed not needed) | |
| 4 | Space prepared and area cleared | |
| 5 | Safety precautions understood and gear on hand | |
| 6 | Pet/occupant plan in place for hazardous phases | |
| 7 | All open decisions resolved | |
```

4. **Run the readiness gate inline.** For each criterion:

   | # | Criterion | Pass? |
   |---|-----------|-------|
   | 1 | All materials listed in plan.md are purchased or confirmed available | |
   | 2 | All tools are on hand or a rental reservation exists | |
   | 3 | Permits either obtained or explicitly confirmed not required | |
   | 4 | No BLOCKER items remain in adversarial-review.md (or file absent) | |
   | 5 | All open decisions in plan.md are resolved | |

   Verdict:
   - **READY** — all criteria met → output summary and proceed.
   - **ALMOST** — minor gaps (tools not yet rented, some materials not purchased) → note what's outstanding, confirm user wants to proceed.
   - **NOT READY** — blockers or permits unresolved → halt with clear list of what must be done first. Do not proceed to `/home:5-execute`.

5. **Output the coordinator summary:**
   ```
   ✅ Phase 4 complete — prep-checklist.md written to home_plans/<PROJECT_NAME>/

   Materials ready: <N>/<N>
   Tools ready: <N>/<N>
   Permits: <obtained / not required / MISSING>
   Readiness gate: <READY|ALMOST|NOT READY>

   Next step: /home:5-execute
   ```
