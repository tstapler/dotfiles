---
name: home-project-planning
description: Structured home project planning workflow (scope → research → plan → prep → execute → close). Use for any home improvement, repair, installation, or maintenance project.
---

# Home Project Planning

A six-phase workflow for planning and executing home projects — from scoping a repair to closing out a renovation and capturing it in the Logseq wiki.

## When to invoke this skill

Invoke when the user mentions:
- A home repair, fix, or broken thing
- Installing, replacing, or adding something to the home
- Planning a renovation or remodel
- Organizing a room or space
- Home maintenance tasks
- "I need to figure out how to..." followed by a home topic

## Phase Overview

| Phase | Command | Output |
|-------|---------|--------|
| 1. Scope | `/home:1-scope` | `home_plans/<project>/scope.md` — requirements interview |
| 2. Research | `/home:2-research` | `home_plans/<project>/research/*.md` — 4 parallel research agents |
| 3. Plan | `/home:3-plan` | `home_plans/<project>/plan.md` — task sequence, materials list, budget |
| 4. Prep | `/home:4-prep` | `home_plans/<project>/prep-checklist.md` — readiness gate |
| 5. Execute | `/home:5-execute` | `home_plans/<project>/execution-log.md` — progress & cost tracking |
| 6. Close | `/home:6-close` | `logseq/pages/home-project-<project>.md` — wiki archive |

**Fast path**: `/home:quick` — for tasks under 2 hours with no permits and budget under ~$300.
**Dashboard**: `/home:status` — show all projects and their current phase.

## Key Differences from Software Planning (sdd)

| sdd concept | home equivalent |
|-------------|----------------|
| requirements.md | scope.md — problem, budget, labor approach |
| stack / architecture research | methods / materials / logistics / risks research |
| plan.md (tasks + code) | plan.md (tasks + materials list + budget) |
| validation.md (test plan) | prep-checklist.md (readiness gate) |
| implement (write code) | execute (log physical task completion) |
| verify (tests pass) | close (actuals vs estimates, wiki page) |

## Phase Gates

- **Phase 3 → 4**: Adversarial reviewer must return CONCERNS or CLEAN (no BLOCKERS) before prepping.
- **Phase 4 → 5**: Readiness gate must pass (or user explicitly accepts gaps) before starting physical work.
- **Phase 5 → 6**: All tasks in plan.md must appear in execution-log.md as completed.

## Safety First

The planning and adversarial review phases explicitly check for:
- Permits required (electrical, plumbing, structural, HVAC)
- Utility shutoff requirements
- PPE needs
- Pet and occupant safety (fumes, debris, access restriction)
- Proper task sequencing (e.g. don't tile before waterproofing)

## Artifacts Location

All project artifacts are stored in `home_plans/<project>/` relative to the wiki repo root. Completed projects are also documented as a Logseq page at `logseq/pages/home-project-<project>.md`.
