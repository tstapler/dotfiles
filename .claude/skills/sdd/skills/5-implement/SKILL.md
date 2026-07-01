---
description: "Phase 5 — Execute plan via parallel worker subagents. START IN A FRESH SESSION."
user-invocable: true
effort: high
allowed-tools: Read, Write, Edit, Bash, Agent, AskUserQuestion
---

# sdd:5-implement

Execute the implementation plan using parallel worker subagents dispatched directly from this thread.

## ⚠️ FRESH SESSION REQUIRED

If this session was used for planning (ideate/research/plan/validate), **stop now**.
Close this session and open a new one, then run `/sdd:5-implement` again.
Planning context degrades code generation quality — this is not optional.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME and REPO_ROOT.

2. **Read required inputs** — halt with a clear error message if any are missing:
   - `project_plans/<PROJECT_NAME>/implementation/plan.md`
   - `project_plans/<PROJECT_NAME>/implementation/validation.md`
   - `project_plans/<PROJECT_NAME>/design/ux.md` (optional — include if present)

3. **Read the dependency visualization** in plan.md. Identify which epics can run concurrently:
   - Epics with **no shared file writes** can run in the same parallel batch
   - Epics that write to the same file as another epic must run sequentially
   - Use the ASCII dependency diagram in plan.md as the authoritative source — do not re-derive it

4. **Dispatch all independent epics in a single parallel message** using the `Agent` tool.

   Each worker agent receives this prompt template (fill in for each epic):

   > You are implementing Epic `<N>` of the `<PROJECT_NAME>` implementation plan.
   >
   > **Inputs — read these files at the start:**
   > - `project_plans/<PROJECT_NAME>/implementation/plan.md` — read Epic `<N>` and its stories/tasks only
   > - `project_plans/<PROJECT_NAME>/implementation/validation.md` — read the test cases for stories in this epic
   > - `project_plans/<PROJECT_NAME>/design/ux.md` — read if this epic contains user-facing stories (skip otherwise)
   >
   > **Codebase orientation (before writing any code):**
   > Understand the existing code context for this epic using context-efficient techniques — do NOT read entire files or directories blindly:
   > - `Glob` to find files by pattern (e.g., `src/**/*.ts`, `**/*service*.go`)
   > - `sg --pattern '<pattern>' --lang <lang>` for structural code searches — finding existing function signatures, interface definitions, type declarations, or call sites. Use `sg` (ast-grep) instead of `grep` for code structure: it's syntax-aware and token-efficient. See `/code-ast-grep` for pattern syntax.
   > - `Grep` for text-based searches in configs, docs, or non-code files
   > - `Read` only targeted line ranges you need — not whole files
   > Orient yourself in ≤5 tool calls before writing anything.
   >
   > **For each task in this epic:**
   > 1. Implement the task — exact files listed in plan.md
   > 2. Write the corresponding tests from validation.md (use the pre-designed test names exactly)
   > 3. Run the tests for these specific files only — show output
   > 4. Fix any failures before moving to the next task
   >
   > **Do NOT implement other epics.** Do NOT modify files outside the task's listed files.
   >
   > **Return:**
   > - Tasks completed (N/N)
   > - Test results (N passing, N failing)
   > - Any warnings or gaps found

5. **Wait for all parallel workers to complete.** Do not start the next batch until all current workers have returned.

   **Worker failure recovery**:
   - If a worker returns with failing tests: run the worker repair loop (max 5 iterations):
     ```
     ITERATION = 0, MAX = 5
     while (worker has failing tests) and (ITERATION < MAX):
       ITERATION++
       1. Collect exact failure output: test name, assertion failure, stack trace
       2. Spawn a fresh fix subagent (lean-agent-loop pattern):
          - Provide: failure output, epic tasks + files from plan.md, repo path
          - Agent: edits implementation files, does NOT change other epics' files, commits
          - Agent returns: what was changed + commit SHA
       3. Re-run only the failing tests to verify (not the full suite).
       4. Update failure list. Remove resolved tests.

     If all tests pass: continue to next epic batch.
     If MAX reached: diagnose root cause type —
       - Planning error (plan assumed incorrect API, wrong dependency, infeasible approach):
         propose a specific plan patch via AskUserQuestion: "Worker for Epic N STUCK after
         5 cycles. Root cause: [diagnosis]. Proposed plan change: [specific amendment].
         Approve and apply, or take manual control?" Apply only if user approves.
       - Implementation bug or unclear: escalate raw error + all 5 fix attempts to user.
     ```
   - If a worker crashes mid-task (no return): re-dispatch the same worker prompt. The worker will re-read plan.md and pick up from where files are missing.

6. **Dispatch the next wave** for any remaining epics that are now unblocked (their dependencies completed in the previous batch). Repeat until all epics are done.

7. **Spec compliance sweep** — after all epics complete, dispatch a single spec compliance agent:

   > Read `project_plans/<PROJECT_NAME>/implementation/plan.md` and `project_plans/<PROJECT_NAME>/implementation/validation.md`.
   > Run `git diff main...HEAD`.
   > For each story acceptance criterion in plan.md, verify it is satisfied in the diff.
   > For each test name in validation.md, verify the test exists in the diff.
   > Return: criteria met (N/N), tests present (N/N), gaps found.

   If gaps are found: run the spec compliance repair loop (max 5 iterations):
   ```
   ITERATION = 0, MAX = 5
   while (gaps_remain) and (ITERATION < MAX):
     ITERATION++
     1. Collect all open gaps: { story/criterion, what's missing, relevant files }
     2. Dispatch targeted fix agents in parallel (one per gap, lean-agent-loop pattern):
        - Each agent: implements the missing piece, writes or fixes the missing test,
          commits — does NOT touch other stories' files
        - Each agent returns: what was added + commit SHA
     3. Re-run the spec compliance sweep scoped to previously gapped items only.
     4. Remove resolved gaps from open list.

   If all gaps resolved: proceed to Phase 5 summary.
   If MAX reached: escalate remaining gaps to user with list of what each fix agent
   attempted and why it didn't converge.
   ```

8. **Output the Phase 5 summary:**
   ```
   ✅ Phase 5 complete

   Epics completed: <N>/<N>
   Tasks completed: <N>/<N>
   Tests: <N> passing, <N> failing
   Spec criteria met: <N>/<N>
   Gaps fixed: <N>
   Escalated to user: <N> (list below)

   Warnings: <list or "none">

   Next step: /sdd:6-verify
   ```
