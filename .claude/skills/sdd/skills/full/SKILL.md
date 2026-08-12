---
description: "Full SDD workflow — ideate → research → plan → validate → implement → verify → ship. Planning runs in subagents; no fresh session required."
argument-hint: "[project name]"
user-invocable: true
---

# sdd:full

Run the complete SDD workflow from ideation through shipping. Each phase delegates to its own command file — full.md is a pure orchestrator and never duplicates phase logic.

## Delegation model

**Each phase section below says: read the phase file and execute its instructions.** This means full.md stays automatically in sync when individual phases are updated — it never re-implements them.

## Parallelization model

Use parallel Agent calls, not coordinator subagents. At each phase that benefits from concurrency, send a single message containing multiple `Agent` tool calls. Each agent is independent — it reads its input from disk, does its work, and writes its output to disk. The parent thread collects summaries from all agents before proceeding, dispatching them directly rather than through a "coordinator agent" that internally spawns further agents.

**Concrete rule, not a vibe:** when choosing `subagent_type` for these Agent calls, never pass `sdd` — its own description offers to run multiple phases (including "implement" — i.e. Phase 5) internally, which makes it a coordinator agent even when dispatched as if it were one plain worker among several. Use `general-purpose` (or another non-orchestrating type suited to the task) for every worker. If a dispatched agent's result reports resuming into, or waiting on, another agent instead of returning a summary directly, that is the coordinator-recursion failure — stop, do not re-brief a fresh agent to continue it, and re-dispatch the work as a plain worker instead.

---

## Phase 1 — Ideate (this thread)

Read `.claude/commands/sdd/1-ideate.md` and execute its instructions exactly.

Orchestration addition: if `$ARGUMENTS[0]` was provided, use it as the project name and skip the project name question.

After writing requirements.md, check the Complexity field it derived. If Complexity is 1: stop and suggest `/sdd:quick` instead — "This scored Complexity 1 (bug fix / small refactor). /sdd:full's remaining phases (research/plan/validate/verify) are built for Complexity 2+ work and will produce more planning artifact than the task needs. Continue with /sdd:full anyway, or switch to /sdd:quick?" — then proceed per the user's choice.

Otherwise, confirm with the user before proceeding:
```
header: "Continue"
question: "requirements.md written. Proceed with automated research, planning, and validation?"
options:
  - "Yes — run phases 2–4 now"
  - "No — I'll review requirements.md first (resume with /sdd:2-research)"
```

---

## Phase 2 — Research (parallel Agent calls)

Read `.claude/commands/sdd/2-research.md` for the full agent prompts, output file paths, and the complexity calibration in step 2.5 — that step decides how many of the 6 agents actually run, do not hardcode 6 here.

Dispatch the calibrated set of research agents in a **single parallel message** from this thread. Each agent reads requirements.md, does its research, writes its file, and returns a 3-bullet summary.

Wait for all dispatched agents to complete. Do not re-read research files in full — use the summaries.

---

## Phase 3 — Plan (parallel Agent calls)

Read `.claude/commands/sdd/3-plan.md` for the full planning, architecture review, adversarial review, and UX design agent prompts, and the complexity calibration in step 2.5 — that step decides which reviewers actually run and the repair-loop iteration cap, do not hardcode "all three" here.

Orchestration:
1. Dispatch the **planning/synthesis agent** first (it must write plan.md before reviewers can read it)
2. Once plan.md exists, dispatch the reviewers called for by the calibration (adversarial reviewer always; architecture review and UX design only when the calibration says so) in a single parallel message
3. If any reviewer returns BLOCKED: patch plan.md and re-run that reviewer only
4. Do not proceed until all dispatched reviewers are CONCERNS or CLEAN

Wait for all to complete. Use summaries — do not re-read plan.md in full.

---

## Phase 4 — Validate (parallel Agent calls)

Read `.claude/commands/sdd/4-validate.md` for the full subagent prompts, readiness gate criteria, and the complexity calibration in step 2.5 — that step decides which of the validation/pre-mortem/cross-artifact-consistency agents actually run and whether the triad review gate applies, do not hardcode "three" here.

Dispatch the calibrated set of agents in a single parallel message. Wait for all dispatched agents to complete.

If the readiness gate returns FAIL: patch plan.md for P1 pre-mortem items, halt and surface remaining failures to the user. Do not proceed to Phase 5.
If the triad review runs and returns NOT READY: halt and tell the user which leg to fix first.

---

## Checkpoint — Commit planning artifacts

Before implementation, commit all planning artifacts so they are versioned alongside the code:

```bash
git add project_plans/<PROJECT_NAME>/
git commit -m "chore(sdd): planning artifacts for <PROJECT_NAME>"
```

Then output:
```
✅ Planning complete

Artifacts committed:
  project_plans/<PROJECT_NAME>/requirements.md
  project_plans/<PROJECT_NAME>/research/ (6 files)
  project_plans/<PROJECT_NAME>/implementation/plan.md
  project_plans/<PROJECT_NAME>/implementation/adversarial-review.md
  project_plans/<PROJECT_NAME>/implementation/architecture-review.md
  project_plans/<PROJECT_NAME>/implementation/validation.md
  project_plans/<PROJECT_NAME>/implementation/pre-mortem.md
  project_plans/<PROJECT_NAME>/design/ux.md (if user-facing)
```

Ask:
```
header: "Implement"
question: "Planning complete. Ready to implement?"
options:
  - "Yes — start implementation now"
  - "Let me review the plan first — I'll run /sdd:5-implement when ready"
  - "Something needs changing — I'll edit the artifacts and re-run validation"
```

If not ready: stop here.

---

## Phase 5 — Implement (parallel Agent calls per epic)

⚠️ If this session was used for planning, stop and open a fresh session before Phase 5.

Read `.claude/commands/sdd/5-implement.md` for the full worker agent prompt template, dependency diagram reading, failure recovery rules, and spec compliance sweep instructions.

Dispatch workers directly from this thread in parallel — do not use a coordinator agent. Per the Parallelization model above: `subagent_type` for each epic worker must not be `sdd`.

---

## Phase 6 — Verify

Read `.claude/commands/sdd/6-verify.md` and execute its full 4-layer review:
- Layer 1: Language idioms (parallel agents per technology in surface map)
- Layer 2: Architecture + refactor candidates (parallel)
- Layer 3: Correctness, tests, security, error handling, observability
- Layer 4: UX/behavioral verification (Playwright → claude-in-chrome → ui-playwright fallback)

Do not inline the verification logic here — follow 6-verify.md exactly.

If REFACTOR or BLOCKED: return to Phase 5. Do not proceed to Phase 7.

---

## Phase 7 — Ship

Read `.claude/commands/sdd/7-ship.md` and execute its instructions exactly.

Key steps (per 7-ship.md):
1. Draft PR description (including rollback procedure and UX preview GIF if applicable)
2. Ask user for ship method
3. Create PR with `gh pr create`
4. For "drive to merge-ready" option: invoke `/github:pr-ship <PR_NUMBER>`
5. Clean up worktree after merge
6. Run `/knowledge:extract-learnings`
