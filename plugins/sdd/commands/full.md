---
description: "Full SDD workflow — ideate → research → plan → validate → implement → verify → ship. Planning runs in subagents; no fresh session required."
argument-hint: "[project name]"
user-invocable: true
---

# sdd:full

Run the complete SDD workflow with minimal manual steps. Phases 2–5 run in subagents, keeping this thread clean for final verification and shipping.

## Why no fresh session required

All planning (research, plan, validation) and implementation run in subagents that write their output to disk. This thread only sees brief summaries. Planning context never accumulates here, so implementation quality is preserved without opening a new session.

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

### Phase 2 — Research (subagent coordinator)

Dispatch a research coordinator subagent with the full text of requirements.md.

Subagent prompt:
> Run sdd:2-research for the project below. Spawn 4 parallel research agents (stack, features, architecture, pitfalls). Each must write its findings directly to the appropriate file under `project_plans/<PROJECT_NAME>/research/`. Return a 3-bullet summary per agent when done.
>
> Requirements:
> <requirements.md content>

Wait for completion. Read the summary (do not re-read the research files in full).

---

### Phase 3 — Plan (subagent)

Dispatch a planning subagent with requirements.md + research file summaries.

Subagent prompt:
> Run sdd:3-plan. Read project_plans/<PROJECT_NAME>/requirements.md and project_plans/<PROJECT_NAME>/research/*.md. Validate technology choices. Write the implementation plan to project_plans/<PROJECT_NAME>/implementation/plan.md. Return: epic/story/task counts, any flagged choices.

Wait for completion. Use the summary — do not re-read plan.md in full.

---

### Phase 4 — Validate (subagent)

Dispatch a validation subagent.

Subagent prompt:
> Run sdd:4-validate. Read project_plans/<PROJECT_NAME>/implementation/plan.md and project_plans/<PROJECT_NAME>/requirements.md. Design the full test suite with requirement-to-test traceability. Write to project_plans/<PROJECT_NAME>/implementation/validation.md. Return: test case counts by type, requirements coverage fraction.

Wait for completion.

---

### Checkpoint

```
✅ Planning complete

Artifacts written:
  project_plans/<PROJECT_NAME>/requirements.md
  project_plans/<PROJECT_NAME>/research/ (4 files)
  project_plans/<PROJECT_NAME>/implementation/plan.md
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

### Phase 5 — Implement (subagent coordinator)

Dispatch an implementation coordinator subagent.

Subagent prompt:
> Run sdd:5-implement. Read project_plans/<PROJECT_NAME>/implementation/plan.md and project_plans/<PROJECT_NAME>/implementation/validation.md. For each task: dispatch a worker subagent, run spec compliance review and code quality review on the diff, fix violations before proceeding. Return: tasks completed, violations fixed, warnings noted.

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

```bash
cat > /tmp/pr-description.md <<'EOF'
<PR description>
EOF
gh pr create --title "<type>(<scope>): <description>" --body-file /tmp/pr-description.md
```

Output the PR URL.
