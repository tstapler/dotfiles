# Stacked-PR Examples

## Stage 2 — Stack Plan Output Format

Produce a plan in this format:

```
Stack: feat/JIRA-123

Layer 1 (feat/JIRA-123-db-schema)
  - What: Add users table migration
  - Why first: all other layers read this table
  - CI risk: low (additive schema only)
  - Files: db/migrations/*, models/user.go

Layer 2 (feat/JIRA-123-auth)
  - What: Auth middleware using users table
  - Depends on: Layer 1
  - CI risk: medium (new critical path)
  - Files: middleware/auth.go, middleware/auth_test.go

Layer 3 (feat/JIRA-123-api)
  - What: API endpoints behind auth
  - Depends on: Layer 2
  - CI risk: low
  - Files: handlers/user.go, handlers/user_test.go

Layer 4 (feat/JIRA-123-ui)
  - What: Frontend consuming API
  - Depends on: Layer 3
  - CI risk: low
  - Files: src/components/UserProfile.tsx
```

**Merge order:** always bottom-up (Layer 1 first). Each layer must pass CI independently.

**Rule of thumb:** 3–5 layers is comfortable. More than 7, consider sub-stacks.

## Stage 3 — PR Description Template

Include in every PR:

```markdown
## Stack
| # | PR | Status |
|---|---|---|
| 1 | #41 feat: add db schema | 👀 **← this PR** |
| 2 | #42 feat: add auth middleware | 🔲 draft |
| 3 | #43 feat: add API endpoints | 🔲 draft |

> Diff this PR against its base (`main`), not the full feature branch.

## This PR only
Add the users table migration. Auth middleware that reads it is in #42.
```
