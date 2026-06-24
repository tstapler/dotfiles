---
description: Show current SDD phase and the next command to run
user-invocable: true
---

# sdd:status

Detect the current SDD phase by checking which artifacts exist, then tell the user exactly what to do next.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Check for artifacts** in `project_plans/<PROJECT_NAME>/`:

   | Artifact | Phase complete |
   |----------|---------------|
   | `requirements.md` | Phase 1 (Ideate) |
   | `research/stack.md` + `research/features.md` + `research/architecture.md` + `research/pitfalls.md` | Phase 2 (Research) |
   | `implementation/plan.md` | Phase 3 (Plan) |
   | `implementation/validation.md` | Phase 4 (Validate) |

3. **Determine current phase** — the highest completed phase based on artifacts present.

4. **Output the status report:**

```
## SDD Status — <PROJECT_NAME>

**Current phase:** <N> (<phase name>) ✅
**Next command:** /sdd:<N+1>-<name>
**Next artifact:** <what it produces>

### Artifacts present
- ✅ requirements.md
- ✅ research/ (4 files)
- ❌ implementation/plan.md — run /sdd:3-plan
- ❌ implementation/validation.md

### Session boundary
⚠️  Phases 1–4 are planning. Open a FRESH SESSION before running /sdd:5-implement.
    Planning context degrades implementation quality.
```

5. **Special cases:**
   - No `project_plans/` at all → "No SDD project found. Run `/sdd:1-ideate` to start."
   - `implementation/plan.md` exists but no `validation.md` → warn "Do not skip validation — run `/sdd:4-validate` before implementing."
   - User appears to be in a session that already did planning (context contains requirements/research/plan discussion) → warn "This session has planning context. Open a fresh session before running `/sdd:5-implement`."
