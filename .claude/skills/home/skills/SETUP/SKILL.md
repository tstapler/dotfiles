## Verify prerequisites before any home: command

### Check 1: Identify the project

Determine the project name for `home_plans/<project>/` path:

- If `home_plans/` already exists with subdirectories, list them and ask which project to work on (or whether to start a new one)
- If this is a new project, ask for a short kebab-case project name that describes the work (e.g., `basement-bathroom-tile`, `kitchen-faucet-replacement`, `garage-shelving`)
- Store as `PROJECT_NAME` for use throughout the session

### Check 2: Working directory context

These commands are designed for use inside the personal wiki repo. The `home_plans/` directory lives at the repo root alongside `logseq/`. Verify you are in the right directory if unsure.

### Check 3: Track progress with the task tool (if available)

Each `home:N-*` command is one discrete stage. If a task-tracking tool is available in this environment, use it to record which stage `PROJECT_NAME` is in — this preserves position if the session is interrupted:

- **Claude Code**: `TaskCreate` one task per stage the first time you touch a project (e.g. "home:`<PROJECT_NAME>` — Phase 2 Research"); `TaskUpdate` it to `in_progress` when you start the stage and `completed` when its exit gate (Check 4) passes.
- **Gemini CLI / Antigravity**: `write_todos` with one entry per stage, updated the same way.

If no task tool is available in this environment, skip this — it's a convenience for resuming, not a requirement for the workflow to function.

### Check 4: Respect stage gates

Every `home:N-*` command is a discrete stage with two gates:

- **Entry gate** — halt and name the missing prerequisite if the required input file from the previous stage doesn't exist (e.g. `/home:3-plan` halts if `scope.md` is missing, telling the user to run `/home:1-scope` first). Never guess or fabricate a missing input to keep moving.
- **Exit gate** — before printing "Next step" and advancing, verify this stage's own output actually exists and is non-trivial (the file was written, isn't empty, and — where the stage defines one — its verdict/checklist passes, e.g. `/home:3-plan`'s adversarial review verdict, `/home:4-prep`'s readiness gate). Don't advance on the agent's summary alone; check the artifact.

Never silently skip a gate to save time — a gate failing is a normal, expected outcome that the command should surface, not suppress.
