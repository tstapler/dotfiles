---
description: "Fast path for small maintenance tasks, quick fixes, and simple installs under ~2 hours."
argument-hint: "[task description]"
user-invocable: true
---

# home:quick

Lightweight end-to-end workflow for home tasks simple enough to handle in one session. No project files written, no phase gates — just a clear plan and execution.

## When to use this

- Small repairs (leaky faucet, running toilet, stuck door, clogged drain)
- Simple installs (light switch, outlet, fixture, shelf, doorknob)
- Quick maintenance (filter replacement, caulk touch-up, painting a single wall)
- Anything you'd describe as "should take an afternoon"

**When NOT to use this**: Anything requiring permits, multi-day work, contractor coordination, or a budget over ~$300. Use `/home:1-scope` instead.

## Instructions

1. **Clarify the task.**

   If `$1` was provided, use it as the task description and skip this step. Otherwise ask:
   ```
   header: "Task"
   question: "What needs to be done?"
   options:
     - "Repair something broken — I'll describe it"
     - "Install or replace something"
     - "Quick maintenance or cleaning task"
     - "Something else — I'll describe it"
   ```

2. **Quick safety check.** Before anything else, flag if the task involves:
   - Electrical work beyond a simple fixture swap (requires shutting off breaker, GFCI, etc.)
   - Plumbing beyond simple fixture replacement (requires shutting off water supply)
   - Anything above 6 feet from the ground (ladder safety)
   - Chemical exposure (ventilation, gloves, respirator)
   - Anything that could affect Mochi (fumes, sharp debris, open access to hazardous area)

   State the safety precautions clearly before the task steps.

3. **List what's needed.**

   In two short lists:
   - **Materials**: specific items to buy, with suggested sources (Lowe's / Amazon preferred)
   - **Tools**: what to have on hand

4. **Give the step-by-step.**

   Number the steps. Be specific — not "tighten the bolt" but "tighten the packing nut clockwise until snug, then 1/4 turn more." Include:
   - When to shut off utilities (water, electricity) and how to restore them
   - Any wait times (caulk cure, paint dry, etc.)
   - How to know each step is done correctly

5. **State the done condition.**

   One sentence: what does success look like? (e.g., "No drip after running hot and cold for 60 seconds.")

6. **Offer next steps:**
   ```
   header: "Done?"
   question: "Did it go as planned?"
   options:
     - "Yes — all good"
     - "Yes, but I found something else that needs attention"
     - "No — ran into an issue"
     - "It's more involved than expected — start a full project"
   ```

   If "ran into an issue" or "more involved" → briefly describe how to back out safely (turn water back on, cap the wire, etc.) and suggest running `/home:1-scope` to plan it properly.
