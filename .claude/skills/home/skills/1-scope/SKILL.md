---
description: "Phase 1 — Interview to scope the home project. Outputs: home_plans/<project>/scope.md"
user-invocable: true
---

# home:1-scope

Conduct a structured interview to capture the full scope of the home project and produce `scope.md`.

## HARD GATE

**Do not propose solutions, materials, or approaches during the interview.** If you catch yourself suggesting how to do something, stop and ask another scoping question instead. The interview is about understanding the problem and constraints — research comes in Phase 2.

## Instructions

1. **Follow [SETUP.md](SETUP.md)** — identify PROJECT_NAME, and mark this stage's task `in_progress` if a task tool is available (Check 3).

2. **Load wiki context first.** Check `logseq/pages/` for existing pages about the space or topic (house/room pages, prior project pages, relevant product/retailer zettels). Extract any known dimensions, constraints, or prior decisions and use them to pre-fill answers — skip interview questions the wiki already answers.

3. **Run the interview using `AskUserQuestion` for each question.** Ask one at a time — wait for each answer before asking the next. Skip any question already resolved by the wiki context above.

   **Question 1:**
   ```
   header: "Area"
   question: "Which area of the home does this project involve?"
   options:
     - "Kitchen"
     - "Bathroom(s)"
     - "Bedroom / living space"
     - "Outdoor / garage / basement"
   ```

   **Question 2:**
   ```
   header: "Goal"
   question: "What is the primary goal of this project?"
   options:
     - "Repair or fix something broken"
     - "Install or add something new"
     - "Organize, declutter, or rearrange"
     - "Maintain, service, or update"
   ```

   **Question 3:**
   ```
   header: "Urgency"
   question: "How urgent is this?"
   options:
     - "Safety or health issue — needs immediate attention"
     - "Functionally broken — affecting daily life now"
     - "Quality of life improvement — would be nice to have done"
     - "Planned upgrade — no time pressure"
   ```

   **Question 4:**
   ```
   header: "Budget"
   question: "What is your approximate budget for this project?"
   options:
     - "Under $100 — quick fix or supplies only"
     - "$100–$500 — weekend project range"
     - "$500–$2,000 — larger DIY or small contractor job"
     - "$2,000+ — I'll specify (click Other)"
   ```

   **Question 5:**
   ```
   header: "Labor"
   question: "How do you want to approach the work?"
   options:
     - "Fully DIY — I'll do all the work"
     - "Hire a contractor for everything"
     - "Hybrid — DIY where possible, hire for specific parts"
     - "Not sure yet — help me decide"
   ```

   **Question 6:**
   ```
   header: "Timeline"
   question: "When does this need to be done?"
   options:
     - "This weekend"
     - "Within the next month"
     - "No hard deadline — whenever it's ready"
     - "By a specific date — I'll specify (click Other)"
   ```

   **Question 7:**
   ```
   header: "Disruption"
   question: "What disruptions are acceptable while the project is underway?"
   options:
     - "None — the space must remain fully functional throughout"
     - "Limited — some disruption is OK during specific hours"
     - "Major disruption is fine — we can vacate the space"
     - "Outdoor or storage area — disruption doesn't matter"
   ```

   **Question 8 (optional — ask only if the project involves fixed hardware):**
   ```
   header: "Hardware"
   question: "Any constraints on hardware or fixtures being installed?"
   options:
     - "Must use knobs (not lever handles) — Mochi opens levers"
     - "No specific constraints"
     - "I'll describe the constraint (click Other)"
   ```

4. **Exit gate — anti-rationalization check.** Before writing `scope.md`, confirm:
   - You have a clear problem or goal statement
   - You know the budget range
   - You know the acceptable labor approach
   - You understand the timeline and disruption constraints

   Do not write `scope.md` until all four are true — ask a follow-up question instead of guessing.

5. **Write `home_plans/<PROJECT_NAME>/scope.md`:**

```markdown
# Scope: <PROJECT_NAME>

**Date**: <YYYY-MM-DD>
**Area**: <kitchen | bathroom | bedroom | outdoor | garage | basement | other>
**Type**: <repair | installation | organization | maintenance | renovation>

## Problem / Goal
<What needs to happen and why. One clear paragraph.>

## Success Criteria
<What does done look like? How will we know it's finished and working?>

## Constraints

### Budget
<Approved budget range>

### Timeline
<Deadline or target date, or "no hard deadline">

### Labor Approach
<DIY / contractor / hybrid — and any specific skills available>

### Disruption Tolerance
<What is acceptable during the project>

### Physical Constraints
<Hardware limitations, pet safety, aesthetic requirements, HOA rules, etc.>

## Out of Scope
<Explicit exclusions — what this project does NOT cover>

## Open Questions
<Anything unresolved that research should answer>
```

6. **Verify the exit gate before advancing**: confirm `scope.md` was actually written and is non-empty. Mark this stage's task `completed` if a task tool is available, then output:
   ```
   ✅ Phase 1 complete — scope.md written to home_plans/<PROJECT_NAME>/

   Next step: /home:2-research
   ```
