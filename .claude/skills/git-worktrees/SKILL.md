---
name: git-worktrees
description: |
  Manage git worktrees for isolated feature development. Automatically handles directory selection,
  .gitignore safety verification, worktree creation, project setup (npm/cargo/poetry/go), and test
  baseline validation. Use when starting new feature branches, working on multiple features simultaneously,
  or needing clean isolated environments. Integrates with CLAUDE.md directives and handles common failure modes.
---

# Git Worktrees Skill

## Overview

Creates isolated git worktrees for feature development with automatic project setup and test verification.

**Core principle**: Systematic directory selection + safety verification + automated setup = reliable isolation.

**Announce at start**: "I'm using the git-worktrees skill to set up an isolated workspace."

## Workflow

### Phase 1: Directory Selection

Follow this priority order:

1. **Check for existing worktree directories**
   ```bash
   ls -d .worktrees 2>/dev/null     # Preferred (project-local, hidden)
   ls -d worktrees 2>/dev/null      # Alternative (project-local)
   ```
   - If `.worktrees/` exists → Use it
   - If `worktrees/` exists → Use it
   - If both exist → `.worktrees/` wins
   - If neither exists → Continue to step 2

2. **Check CLAUDE.md for worktree_directory directive**
   ```bash
   grep -i "worktree.*director" CLAUDE.md 2>/dev/null
   ```
   - If preference specified → Use it without asking
   - If not found → Continue to step 3

3. **Ask user**
   ```
   No worktree directory found. Where should I create worktrees?

   1. .worktrees/ (project-local, hidden)
   2. ~/.claude/worktrees/<project-name>/ (global location)

   Which would you prefer?
   ```

### Phase 2: Safety Verification

#### For Project-Local Directories (.worktrees or worktrees)

**MUST verify directory is ignored before creating worktree:**

```bash
# Check if directory is ignored (respects local, global, and system gitignore)
git check-ignore -q .worktrees 2>/dev/null || git check-ignore -q worktrees 2>/dev/null
```

**If NOT ignored:**
1. Add appropriate line to .gitignore
2. Commit the change with message: "chore: ignore worktree directory"
3. Proceed with worktree creation

**Why critical**: Prevents accidentally committing worktree contents to repository.

#### For Global Directory (~/.claude/worktrees)

No .gitignore verification needed - outside project entirely.

> For upstreaming changes across repos using worktrees as part of a fork workflow, apply the `git-upstream-fork` skill.

### Phase 3: Worktree Creation

**Step 1: Detect project name**
```bash
project=$(basename "$(git rev-parse --show-toplevel)")
```

**Step 2: Create worktree with new branch**
```bash
# Determine full path
case $LOCATION in
  .worktrees|worktrees)
    path="$LOCATION/$BRANCH_NAME"
    ;;
  ~/.claude/worktrees/*)
    path="~/.claude/worktrees/$project/$BRANCH_NAME"
    ;;
esac

# Create worktree with new branch
git worktree add "$path" -b "$BRANCH_NAME"
cd "$path"
```

**Step 3: Verify creation**
```bash
# List all worktrees to confirm
git worktree list
```

### Phase 4: Project Setup

**Step 1: Check CLAUDE.md for setup_command override**
```bash
grep -i "setup_command:" CLAUDE.md 2>/dev/null
```
- If found → Use custom command
- If not found → Auto-detect

**Step 2: Auto-detect project type and run setup**
```bash
# Node.js
if [ -f package.json ]; then
  npm install || yarn install || pnpm install
fi

# Rust
if [ -f Cargo.toml ]; then
  cargo build
fi

# Python
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
elif [ -f pyproject.toml ]; then
  poetry install || uv install
fi

# Go
if [ -f go.mod ]; then
  go mod download
fi

# Makefile
if [ -f Makefile ] && grep -q "^setup:" Makefile; then
  make setup
elif [ -f Makefile ] && grep -q "^install:" Makefile; then
  make install
fi
```

For PHP, Java/Kotlin (Gradle/Maven), multi-language projects, and the full package-manager detection order, see `project-detection.md`.

**Step 3: Handle setup failures**
- If setup fails → Read `project-detection.md` for alternatives
- Report error to user
- Offer to continue without setup or investigate

### Phase 5: Test Baseline Validation

**Step 1: Check CLAUDE.md for test_command**
```bash
grep -i "test_command:" CLAUDE.md 2>/dev/null
```
- If found → Use custom command
- If not found → Auto-detect

**Step 2: Auto-detect and run tests**
```bash
# Node.js
if [ -f package.json ]; then npm test; fi

# Rust
if [ -f Cargo.toml ]; then cargo test; fi

# Python
if [ -f pyproject.toml ]; then pytest || poetry run pytest; fi

# Go
if [ -f go.mod ]; then go test ./...; fi

# Makefile
if [ -f Makefile ] && grep -q "^test:" Makefile; then make test; fi
```

**Step 3: Report results**
- **If tests pass**: Report success and test count
- **If tests fail**: Report failures, ask whether to proceed or investigate
- **If tests skip**: Note that tests were skipped

### Phase 6: Completion Report

Report the worktree path, branch, setup status, and test status, then the cleanup command. See `references/completion-report-and-lookup.md` for the exact report template.

## Quick Reference

| Situation | Action |
|-----------|--------|
| `.worktrees/` exists | Use it (verify ignored) |
| Neither `.worktrees/` nor `worktrees/` exists | Check CLAUDE.md → Ask user |
| Directory not ignored | Add to .gitignore + commit |
| Tests fail during baseline | Report failures + ask |
| CLAUDE.md has setup_command | Use custom command instead of auto-detect |

Full quick-reference table, common mistakes, and error-to-resolution mapping: [references/completion-report-and-lookup.md](references/completion-report-and-lookup.md). Detailed troubleshooting by error message: `troubleshooting.md`.

## Integration Points

Repositories can override auto-detection via `CLAUDE.md` (`worktree_directory`, `setup_command`, `test_command`). See [references/integration-and-best-practices.md](references/integration-and-best-practices.md) for the directive format, best practices, and related skills.

For detailed package manager detection: See `project-detection.md`.
For troubleshooting common issues: See `troubleshooting.md`.

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `git-upstream-fork` | Upstream filtered changes from a worktree to a target repo |
| `github-pr` | Open a PR after work in the worktree is complete |
