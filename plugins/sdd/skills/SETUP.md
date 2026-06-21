## Verify prerequisites before any sdd: command

### Check 1: Resolve the base path

All SDD artifacts live under `<REPO_ROOT>/project_plans/<PROJECT_NAME>/`. Resolve REPO_ROOT first:

```bash
git rev-parse --show-toplevel
```

If the command fails (not a git repo): halt and tell the user to run from inside a git repository.
Store the result as `REPO_ROOT`. All project_plans paths in subsequent phases are relative to REPO_ROOT, not $PWD.

### Check 2: Identify the project

Determine the project name for `REPO_ROOT/project_plans/<PROJECT_NAME>/`:

- If `project_plans/` already exists with subdirectories, list them and ask which project to work on (or "New project" to create one)
- If this is a new project, ask for a short kebab-case project name (e.g., `payment-service`)
- Store as `PROJECT_NAME` for use throughout the session

**Conflict check**: if `project_plans/<PROJECT_NAME>/` already exists and contains artifacts from a prior run, warn:
> ⚠️ `project_plans/<PROJECT_NAME>/` already has files. Re-running a phase will overwrite existing artifacts.
> Continue anyway? Or pick a different project name?

Ask via AskUserQuestion before overwriting.

### Check 3: Verify git branch (required before Phase 5 only)

Before running sdd:5-implement, verify a feature branch exists:

```bash
git branch --show-current
```

- If the result is `main`, `master`, or `develop`: halt. Tell the user to create a feature branch first:
  > Run: `git checkout -b feature/<PROJECT_NAME>`
- If the result is a feature branch: proceed.
- Skip this check for Phases 1–4 and 6–7 (planning phases may run on any branch).

### Check 4: Monorepo guidance

If REPO_ROOT contains multiple services (multiple `go.mod`, `package.json`, `pom.xml`, or `Cargo.toml` at different subdirectory depths), ask:
> This looks like a monorepo. Which service directory is this feature targeting?

Store the answer as `SERVICE_DIR`. Use `SERVICE_DIR` as the working directory for build/test commands in Phases 5–7. This does not change where project_plans/ artifacts are written (those always go in REPO_ROOT).
