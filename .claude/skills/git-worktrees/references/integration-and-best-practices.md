# Integration Points, Best Practices, and Example

## CLAUDE.md Directives

Add these optional directives to your repository's `CLAUDE.md`:

```markdown
## Worktree Configuration

worktree_directory: .worktrees    # Default directory for worktrees
setup_command: make dev-setup     # Override auto-detected setup
test_command: make verify         # Override auto-detected tests
```

## Progressive Context Loading

- For detailed package manager detection: See `../project-detection.md`
- For troubleshooting common issues: See `../troubleshooting.md`

## Best Practices

1. **Always verify .gitignore** - Prevents accidentally committing worktree directories
2. **Use descriptive branch names** - Makes worktree management easier (e.g., `feature/auth`, `fix/bug-123`)
3. **Clean up when done** - Remove worktrees after merging: `git worktree remove <dir>`
4. **Check test baseline** - Ensures you start with passing tests
5. **Document in CLAUDE.md** - Add `worktree_directory` for consistent team usage
6. **Use project-local for team projects** - Use `.worktrees/` so team members use same location
7. **Use global for personal projects** - Use `~/.claude/worktrees/` to keep workspace clean

## Example Workflow

```
You: I need to work on authentication feature
```

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `git-upstream-fork` | Upstream filtered changes from a worktree to a target repo |
| `github-pr` | Open a PR after work in the worktree is complete |
