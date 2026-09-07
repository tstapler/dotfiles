# Completion Report Template and Quick Lookup Tables

## Phase 6: Completion Report

```markdown
✅ Worktree ready at <full-path>

**Branch**: <branch-name>
**Base Branch**: <base-branch>

**Setup Status**:
- Project type: <detected-type>
- Setup command: <executed-command>
- Result: ✅ Success / ⚠️ Failed / ⏭️ Skipped

**Test Status**:
- Test command: <executed-command>
- Result: ✅ Pass (<N> tests) / ❌ Fail / ⏭️ Skipped
- Duration: <seconds>s

**Next Steps**:
1. cd <worktree-path>
2. Start working on your feature
3. When done: git worktree remove <worktree-path>

**Cleanup Command**:
```bash
git worktree remove <worktree-path>
```
```

## Quick Reference

| Situation | Action |
|-----------|--------|
| `.worktrees/` exists | Use it (verify ignored) |
| `worktrees/` exists | Use it (verify ignored) |
| Both exist | Use `.worktrees/` |
| Neither exists | Check CLAUDE.md → Ask user |
| Directory not ignored | Add to .gitignore + commit |
| Tests fail during baseline | Report failures + ask |
| No package.json/Cargo.toml | Skip dependency install |
| CLAUDE.md has setup_command | Use custom command instead of auto-detect |

## Common Mistakes

### ❌ Skipping ignore verification
- **Problem**: Worktree contents get tracked, pollute git status
- **Fix**: Always use `git check-ignore` before creating project-local worktree

### ❌ Assuming directory location
- **Problem**: Creates inconsistency, violates project conventions
- **Fix**: Follow priority: existing > CLAUDE.md > ask

### ❌ Proceeding with failing tests
- **Problem**: Can't distinguish new bugs from pre-existing issues
- **Fix**: Report failures, get explicit permission to proceed

### ❌ Hardcoding setup commands
- **Problem**: Breaks on projects using different tools
- **Fix**: Auto-detect from project files (package.json, Cargo.toml, etc.)

### ❌ Creating worktree without changing directory
- **Problem**: Setup and tests run in wrong directory
- **Fix**: Always `cd` into worktree before running setup/tests

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `fatal: invalid reference` | Branch name conflicts with existing branch | Choose different branch name |
| `fatal: '<path>' already exists` | Worktree directory exists | Remove existing directory or choose new path |
| `npm: command not found` | Missing package manager | Install package manager or skip setup |
| Tests failed in baseline | Pre-existing test failures | Report to user, get permission to continue |
| Permission denied | Insufficient permissions | Check directory permissions |

For detailed troubleshooting: See `../troubleshooting.md`.
