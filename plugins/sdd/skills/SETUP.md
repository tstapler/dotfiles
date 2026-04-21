## Verify prerequisites before any sdd: command

### Check 1: Identify the project

Determine the project name for `project_plans/<project>/` path:

- If `project_plans/` already exists with subdirectories, list them and ask which project
- If this is a new project, ask for a short kebab-case project name (e.g., `payment-service`)
- Store as `PROJECT_NAME` for use throughout the session
