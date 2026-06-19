---
description: "Full SDD workflow — ideate → research → plan → validate → implement → verify → ship. Planning runs in subagents; no fresh session required."
argument-hint: "[project name]"
user-invocable: true
---

# sdd:full

Run the complete SDD workflow with minimal manual steps. Phases 2–5 run as parallel Claude Agent calls, keeping this thread clean for final verification and shipping.

## Why no fresh session required

All planning (research, plan, validation) and implementation run in parallel Agent calls that write their output to disk. This thread only sees brief summaries. Planning context never accumulates here, so implementation quality is preserved without opening a new session.

## Parallelization model

**CRITICAL: Use parallel Agent calls, not coordinator subagents.**

At each phase that benefits from concurrency, send a single message containing multiple `Agent` tool calls. Each agent is independent — it reads its input from disk, does its work, and writes its output to disk. The parent thread collects summaries from all agents before proceeding.

Never use a "coordinator agent" that internally spawns further agents — that adds a middleman and wastes context. Dispatch agents directly from this thread in parallel.

## Instructions

### Phase 1 — Ideate (this thread)

Run the ideate interview using `AskUserQuestion` (see `sdd:1-ideate` for the full question set). Write `project_plans/<PROJECT_NAME>/requirements.md`.

If `$1` was provided, use it as the project name and skip the project name question.

After writing requirements.md, confirm:
```
header: "Continue"
question: "requirements.md written. Proceed with automated research, planning, and validation?"
options:
  - "Yes — run phases 2–4 now (takes a few minutes)"
  - "No — I want to review requirements.md first"
```

If "No": output path to requirements.md and stop. User resumes with `/sdd:2-research`.

---

### Phase 2 — Research (4 parallel Agent calls)

Read requirements.md, then send a **single message** with 4 parallel `Agent` tool calls — one per research domain. Each agent:
- Reads `project_plans/<PROJECT_NAME>/requirements.md` independently
- Performs its research (web fetches, gh CLI, code exploration)
- Writes its findings to its own file under `project_plans/<PROJECT_NAME>/research/`
- Returns a 3-bullet summary

Standard research domains (adapt to project type):

| Agent | Focus | Output file |
|-------|-------|-------------|
| Stack agent | Language/framework/library choices — alternatives, tradeoffs, community health | `research/stack.md` |
| Features agent | Comparable products/OSS projects — what they do, what to borrow | `research/features.md` |
| Architecture agent | Design patterns, data flows, integration points relevant to this problem | `research/architecture.md` |
| Pitfalls agent | Known failure modes, security issues, performance traps, migration costs | `research/pitfalls.md` |

Wait for all 4 to complete. Collect summaries — do not re-read research files in full.

---

### Phase 3 — Plan (parallel Agent calls)

Send a **single message** with Agent calls to parallelize planning work:

- **Synthesis agent** (required): reads all research files + requirements.md, writes `project_plans/<PROJECT_NAME>/implementation/plan.md` in the standard SDD format (epics → stories → tasks). Returns: epic/story/task counts, flagged choices.
- **ADR agent** (if technology decisions were flagged): writes decision records to `docs/adr/ADR-NNN-*.md`. Returns: count of ADRs, decisions recorded.
- **Adversarial reviewer agent** (after synthesis completes — send in a second message once plan.md exists): reads plan.md, writes `project_plans/<PROJECT_NAME>/implementation/adversarial-review.md`. Returns: verdict (BLOCKED/CONCERNS/CLEAN). If BLOCKED, patch plan.md and re-run.

If no technology decisions need recording, omit the ADR agent and use just the synthesis agent.

Wait for completion. Use summaries — do not re-read plan.md in full.

---

### Phase 4 — Validate (single Agent call)

Dispatch one Agent:

Prompt:
> Run sdd:4-validate. Read project_plans/<PROJECT_NAME>/implementation/plan.md and project_plans/<PROJECT_NAME>/requirements.md. Design the full test suite with requirement-to-test traceability. Write to project_plans/<PROJECT_NAME>/implementation/validation.md. Then run the implementation readiness gate: check all 4 criteria against requirements.md, plan.md, validation.md, and adversarial-review.md. Return: test case counts by type, requirements coverage fraction, readiness gate verdict (PASS/CONCERNS/FAIL).

Wait for completion. If readiness gate returns FAIL, halt and surface the failures to the user.

---

### Checkpoint

Commit the planning artifacts before implementation so they are versioned alongside the code:

```bash
git add project_plans/<PROJECT_NAME>/
git commit -m "chore(sdd): add planning artifacts for <PROJECT_NAME>"
```

Then output the checkpoint summary and ask:

```
✅ Planning complete

Artifacts written and committed:
  project_plans/<PROJECT_NAME>/requirements.md
  project_plans/<PROJECT_NAME>/research/ (4 files)
  project_plans/<PROJECT_NAME>/implementation/plan.md
  project_plans/<PROJECT_NAME>/implementation/adversarial-review.md
  project_plans/<PROJECT_NAME>/implementation/validation.md

<Subagent summaries here>
```

Ask:
```
header: "Implement"
question: "Planning complete. Ready to implement?"
options:
  - "Yes — start implementation now"
  - "Let me review the plan first — I'll run /sdd:5-implement when ready"
  - "Something needs changing — I'll edit the artifacts and re-run"
```

If not ready: stop here. User resumes with `/sdd:5-implement`.

---

### Phase 5 — Implement (parallel Agent calls per epic)

Read plan.md and group tasks into independent epics. Send a **single message** with one Agent call per epic that can run concurrently (epics with no shared file writes). For each worker agent:

Prompt template:
> You are implementing Epic N of plan.md for project <PROJECT_NAME>. Read project_plans/<PROJECT_NAME>/implementation/plan.md (Epic N only) and project_plans/<PROJECT_NAME>/implementation/validation.md. Implement all tasks in this epic. After each task: run the associated tests, fix failures. Return: tasks completed, test results, warnings.

After all parallel agents complete, dispatch a second wave for any remaining dependent epics.

Do NOT use a coordinator agent — dispatch workers directly from this thread.

---

### Phase 6 — Verify (this thread)

Run verification inline — you need to see live test output:

1. Run `git diff main...HEAD`
2. Check all acceptance criteria against plan.md
3. Run tests using the appropriate command for the stack. Show output.
4. Review diff for security, correctness, and error handling gaps
5. Output the verification report with PASS / BLOCKED verdict

If BLOCKED: fix violations and re-run before proceeding.

---

### Phase 7 — Ship (this thread)

Draft the PR description and use `AskUserQuestion` to confirm ship method (see `sdd:7-ship`).

Commit and push **all** staged/unstaged changes — both implementation files and any remaining `project_plans/` artifacts — before opening the PR:

```bash
git add <implementation files> project_plans/<PROJECT_NAME>/
git commit -m "<type>(<scope>): <description>"
git push -u origin <branch>
```

Then create the PR:

```bash
cat > /tmp/pr-description.md <<'EOF'
<PR description>
EOF
gh pr create --title "<type>(<scope>): <description>" --body-file /tmp/pr-description.md
```

Output the PR URL.
