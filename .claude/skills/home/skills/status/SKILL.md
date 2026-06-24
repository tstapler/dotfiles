---
description: "Show status of all home projects — phases completed, budget tracking, next steps."
user-invocable: true
---

# home:status

Show a dashboard of all home projects in `home_plans/`, their current phase, budget status, and next action.

## Instructions

1. **List all projects** by reading `home_plans/` directory. If the directory doesn't exist, output:
   ```
   No home projects found. Start one with /home:1-scope or /home:quick
   ```

2. **For each project directory**, check which files exist:

   | File | Phase completed |
   |------|----------------|
   | `scope.md` | Phase 1 (Scope) |
   | `research/*.md` | Phase 2 (Research) |
   | `plan.md` | Phase 3 (Plan) |
   | `prep-checklist.md` | Phase 4 (Prep) |
   | `execution-log.md` | Phase 5 (Execute — in progress or done) |
   | `logseq/pages/home-project-*.md` | Phase 6 (Closed) |

3. **For each project**, extract from the relevant files:
   - Current phase
   - Budget estimate (from plan.md if it exists)
   - Running actual cost (from execution-log.md if it exists)
   - Whether there are any BLOCKER items in adversarial-review.md
   - The next recommended action

4. **Output the dashboard:**

```
## Home Project Status — <YYYY-MM-DD>

### 🔴 BLOCKED
<project> — <blocked reason> — fix with: <command>

### 🟡 In Progress
<project>
  Phase: <N>/6 (<phase name>)
  Budget: $<X>–$<X> estimated | $<X> spent so far
  Next: <specific next action or command>

### 🟢 Ready to Start
<project>
  Phase: <N>/6 (<phase name>) — all gates passed
  Next: /home:<N+1>-<name>

### ✅ Recently Closed
<project> — completed <date> — $<X> final cost

---
Quick actions:
  Start new project:    /home:1-scope
  Quick fix:           /home:quick <description>
  Log task completion: /home:5-execute
```

5. **If any project has been in the same phase for more than 2 weeks** (based on file modification dates), flag it:
   ```
   ⚠️ <project> has been in Phase <N> for a while — consider: <next action>
   ```
