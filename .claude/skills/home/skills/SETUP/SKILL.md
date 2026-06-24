## Verify prerequisites before any home: command

### Check 1: Identify the project

Determine the project name for `home_plans/<project>/` path:

- If `home_plans/` already exists with subdirectories, list them and ask which project to work on (or whether to start a new one)
- If this is a new project, ask for a short kebab-case project name that describes the work (e.g., `basement-bathroom-tile`, `kitchen-faucet-replacement`, `garage-shelving`)
- Store as `PROJECT_NAME` for use throughout the session

### Check 2: Working directory context

These commands are designed for use inside the personal wiki repo. The `home_plans/` directory lives at the repo root alongside `logseq/`. Verify you are in the right directory if unsure.
