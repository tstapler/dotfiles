---
description: "Phase 6 — Close out the project: document results, actuals, and create a Logseq wiki page."
user-invocable: true
---

# home:6-close

Document the completed project, record final costs, extract lessons learned, and create a Logseq wiki page as the permanent record.

## Instructions

1. **Follow [SETUP.md](SETUP.md)** — identify PROJECT_NAME.

2. **Read all project artifacts:**
   - `home_plans/<PROJECT_NAME>/scope.md`
   - `home_plans/<PROJECT_NAME>/plan.md`
   - `home_plans/<PROJECT_NAME>/execution-log.md` — halt if missing; the project isn't tracked as executed yet

3. **Calculate actuals.** From the execution log:
   - Total actual cost vs estimated cost
   - Total actual duration vs estimated duration
   - Count of surprises/issues encountered

4. **Ask one closing question:**
   ```
   header: "Outcome"
   question: "How did the project turn out?"
   options:
     - "Complete success — everything went to plan"
     - "Done, but with notable issues or changes from the plan"
     - "Partially done — some tasks deferred to later"
     - "Abandoned or significantly descoped"
   ```

5. **Write the Logseq wiki page** to `logseq/pages/home-project-<PROJECT_NAME>.md`:

```markdown
---
title: Home Project- <Human-Readable Project Name>
tags: home-project, [[Home Improvement]]
date-completed: <YYYY-MM-DD>
---

- **Project**: [[<PROJECT_NAME>]]
- **Completed**: <YYYY-MM-DD>
- **Area**: <kitchen | bathroom | bedroom | outdoor | etc.>
- **Type**: <repair | installation | renovation | maintenance>

## Summary
<2-3 sentence summary of what was done and the outcome>

## Cost
| | Estimated | Actual |
|--|-----------|--------|
| Materials | $<X> | $<X> |
| Labor/Contractor | $<X> | $<X> |
| Permits | $<X> | $<X> |
| Contingency used | — | $<X> |
| **Total** | **$<X>** | **$<X>** |

## Duration
- Estimated: <X>
- Actual: <X>

## What Went Well
- <bullet>

## What to Do Differently Next Time
- <bullet>

## Surprises & Issues
<List significant issues from the execution log, or "None">

## Resources & References
<Any products, contractors, or techniques worth remembering for future projects>

## Related Projects
- [[<any related home projects>]]
```

6. **Check for follow-up maintenance.** Based on the project, note any recurring maintenance items:
   - If paint was applied: "Touch up in 3–5 years"
   - If caulk was applied: "Inspect annually, replace as needed"
   - If a mechanical system was serviced: "Next service in X months"

   If maintenance items exist, ask:
   ```
   header: "Maintenance reminders"
   question: "Do you want to add recurring maintenance reminders to your Todoist Home project?"
   options:
     - "Yes — add them to Todoist"
     - "No — just document them in the wiki page"
   ```

7. **Output the close summary:**
   ```
   ✅ Phase 6 complete — project closed

   Final cost: $<X> (estimated: $<X>) — <over/under/on budget>
   Duration: <X> (estimated: <X>)
   Wiki page: logseq/pages/home-project-<PROJECT_NAME>.md

   Project archive: home_plans/<PROJECT_NAME>/ (keep for reference)
   ```
