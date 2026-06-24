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

**CRITICAL: Use parallel Agent calls, not coordinator subagents.**

At each phase that benefits from concurrency, send a single message containing multiple `Agent` tool calls. Each agent is independent — it reads its input from disk, does its work, and writes its output to disk. The parent thread collects summaries from all agents before proceeding.

Never use a "coordinator agent" that internally spawns further agents. Dispatch agents directly from this thread in parallel.

---

## Phase 1 — Ideate (this thread)

Read `.claude/commands/sdd/1-ideate.md` and execute its instructions exactly.

Orchestration addition: if `$ARGUMENTS[0]` was provided, use it as the project name and skip the project name question.

After writing requirements.md, confirm with the user before proceeding:
```
header: "Continue"
question: "requirements.md written. Proceed with automated research, planning, and validation?"
options:
  - "Yes — run phases 2–4 now"
  - "No — I'll review requirements.md first (resume with /sdd:2-research)"
```

---

## Phase 2 — Research (6 parallel Agent calls)

Read `.claude/commands/sdd/2-research.md` for the full agent prompts and output file paths.

Dispatch all 6 research agents in a **single parallel message** from this thread. Each agent reads requirements.md, does its research, writes its file, and returns a 3-bullet summary.

Wait for all 6 to complete. Do not re-read research files in full — use the summaries.

---

## Phase 3 — Plan (parallel Agent calls)

Read `.claude/commands/sdd/3-plan.md` for the full planning, architecture review, adversarial review, and UX design agent prompts.

Orchestration:
1. Dispatch the **planning/synthesis agent** first (it must write plan.md before reviewers can read it)
2. Once plan.md exists, dispatch the **architecture review agent**, **adversarial reviewer agent**, and (for user-facing features) **UX design agent** all in a single parallel message
3. If any reviewer returns BLOCKED: patch plan.md and re-run that reviewer only
4. Do not proceed until all reviewers are CONCERNS or CLEAN

Wait for all to complete. Use summaries — do not re-read plan.md in full.

---

## Phase 4 — Validate (three parallel Agent calls)

Read `.claude/commands/sdd/4-validate.md` for the full subagent prompts and readiness gate criteria.

Dispatch the **validation agent**, **pre-mortem agent**, and **cross-artifact consistency agent** in a single parallel message. Wait for all three to complete.

If the readiness gate returns FAIL: patch plan.md for P1 pre-mortem items, halt and surface remaining failures to the user. Do not proceed to Phase 5.
If the triad review returns NOT READY: halt and tell the user which leg to fix first.

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

Dispatch workers directly from this thread in parallel — do not use a coordinator agent.

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
