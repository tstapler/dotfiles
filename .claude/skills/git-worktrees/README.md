# Git Worktrees Skill

Manages git worktrees for isolated feature development with automatic project setup and test validation.

## What This Skill Does

This skill automates the complete workflow for creating isolated git worktrees:

1. **Directory Selection**: Systematically checks existing directories, CLAUDE.md preferences, or prompts user
2. **Safety Verification**: Ensures project-local worktree directories are in .gitignore
3. **Worktree Creation**: Creates new branch and worktree in appropriate location
4. **Project Setup**: Auto-detects project type (npm/cargo/poetry/go/make) and runs setup
5. **Test Baseline**: Validates tests pass in clean worktree before handing off
6. **Completion Report**: Provides clear status and next steps

## Installation

This skill is already installed in your user-global skills directory:

```bash
~/.claude/skills/git/worktrees/
```

It's automatically available across all your projects. No additional installation needed.

## Usage

This skill is automatically discovered by Claude when you request worktree operations.

### Trigger Phrases

Claude will use this skill when you say things like:
- "Create a worktree for [feature name]"
- "Set up an isolated workspace for [feature]"
- "I need to work on [feature] in a separate worktree"
- "Create a new branch in a worktree"

### Manual Invocation

You can also explicitly reference it:
```
Use the git-worktrees skill to set up a workspace for authentication feature
```

## Configuration

### Repository-Specific Settings (Optional)

Add these directives to your repository's `CLAUDE.md` to customize behavior:

```markdown
## Worktree Configuration

worktree_directory: .worktrees    # Default directory for worktrees
setup_command: make dev-setup     # Override auto-detected setup
test_command: make verify         # Override auto-detected tests
```

### Directory Options

The skill supports three location strategies:

1. **Project-local hidden**: `.worktrees/` (recommended for team projects)
2. **Project-local visible**: `worktrees/`
3. **Global location**: `~/.claude/worktrees/<project-name>/` (recommended for personal projects)

The skill will:
- Use existing directory if found
- Respect CLAUDE.md `worktree_directory` preference
- Ask you to choose if neither exists

## Examples

### Example 1: Simple Feature Worktree

```
You: Create a worktree for authentication feature

Claude: I'm using the git-worktrees skill to set up an isolated workspace.

[Checking for existing directories...]
Found .worktrees/ directory
Verified .worktrees/ is ignored by git ✓

[Creating worktree...]
git worktree add .worktrees/feature-authentication -b feature/authentication
Worktree created ✓

[Setting up project...]
Detected: Node.js project (package.json)
Running: npm install
Dependencies installed ✓

[Running tests...]
npm test
✅ 47 tests passing

✅ Worktree ready at /Users/you/project/.worktrees/feature-authentication
Branch: feature/authentication
Ready to implement authentication feature

Next steps:
1. cd .worktrees/feature-authentication
2. Start working on your feature
3. When done: git worktree remove .worktrees/feature-authentication
```

### Example 2: Custom Setup via CLAUDE.md

**CLAUDE.md**:
```markdown
## Worktree Configuration

worktree_directory: ~/worktrees
setup_command: docker-compose up -d && make migrate && npm install
test_command: make test-fast
```

**Usage**:
```
You: Set up a worktree for database refactoring

Claude: I'm using the git-worktrees skill to set up an isolated workspace.

[Using CLAUDE.md preferences...]
worktree_directory: ~/worktrees ✓
setup_command: docker-compose up -d && make migrate && npm install ✓

[Creating worktree...]
git worktree add ~/worktrees/personal-wiki/refactor-database -b refactor/database
Worktree created ✓

[Running custom setup...]
docker-compose up -d && make migrate && npm install
Custom setup completed ✓

[Running custom tests...]
make test-fast
✅ 23 tests passing (fast suite)

✅ Worktree ready at ~/worktrees/personal-wiki/refactor-database
```

### Example 3: Multi-Language Project

```
You: Create a worktree for API redesign

Claude: [Detects both package.json and pyproject.toml]

[Setting up frontend...]
npm install
Frontend dependencies installed ✓

[Setting up backend...]
poetry install
Backend dependencies installed ✓

[Running tests...]
npm test → 47 passing
cd backend && pytest → 123 passing

✅ Worktree ready with both frontend and backend set up
```

## File Structure

```
~/.claude/skills/git/worktrees/
├── SKILL.md                    # Core workflow (loaded automatically)
├── project-detection.md        # Package manager patterns (loaded on-demand)
├── troubleshooting.md          # Common issues (loaded on-demand)
└── README.md                   # This file
```

### Progressive Context Loading

- **SKILL.md**: Always loaded when skill is triggered (~3,500 tokens)
- **project-detection.md**: Loaded when auto-detection needs detailed patterns (~800 tokens)
- **troubleshooting.md**: Loaded when errors occur (~1,200 tokens)

This design keeps initial token usage low while providing detailed context when needed.

## Supported Project Types

The skill auto-detects and sets up:

| Language/Framework | Detection File | Setup Command |
|-------------------|----------------|---------------|
| Node.js | package.json | npm/yarn/pnpm install |
| Rust | Cargo.toml | cargo build |
| Python (modern) | pyproject.toml | poetry/uv install |
| Python (legacy) | requirements.txt | pip install -r requirements.txt |
| Go | go.mod | go mod download |
| PHP | composer.json | composer install |
| Java/Kotlin | build.gradle, pom.xml | gradle build, mvn install |
| Universal | Makefile | make setup/install |

For custom or complex setups, use `setup_command` in CLAUDE.md.

## Best Practices

1. **Keep main branch clean**: Always create worktrees from clean state
2. **Use descriptive branch names**: Use prefixes like `feature/`, `fix/`, `refactor/`
3. **Clean up when done**: Always remove worktrees after merging
4. **Document project setup**: Add `setup_command` to CLAUDE.md for complex projects
5. **Run fast test suite**: Use `test_command: make test-fast` for slow test suites
6. **Verify .gitignore**: Ensure worktree directories are ignored for project-local locations

## Troubleshooting

Common issues and solutions:

| Issue | Solution |
|-------|----------|
| "Command not found" | Install missing tool or skip that step |
| "Already exists" | Remove existing directory/worktree first |
| "Permission denied" | Fix permissions or use `~/.claude/worktrees/` |
| Tests failing | Report to user, get permission to proceed |
| Wrong setup detected | Add `setup_command` to CLAUDE.md |

For detailed troubleshooting, see `troubleshooting.md`.

## Token Budget

| Component | Tokens | When Loaded |
|-----------|--------|-------------|
| SKILL.md | ~3,500 | Always (skill invocation) |
| project-detection.md | ~800 | On-demand (detection issues) |
| troubleshooting.md | ~1,200 | On-demand (errors) |
| **Total (typical)** | **3,500** | Most invocations |
| **Total (max)** | **5,500** | Complex troubleshooting |

## Version History

- **v1.0.0** (2026-01-26): Initial release
  - Automatic directory selection with priority ordering
  - Safety verification via `git check-ignore`
  - Multi-language project detection
  - Test baseline validation
  - CLAUDE.md integration
  - Progressive context loading

## Related Skills

This skill pairs well with:
- **git/commit**: Commit changes in worktree
- **git/merge-worktree-to-main**: Merge and cleanup when done

## Contributing

Found a bug or have a suggestion? This is a personal skill, but feel free to:
1. Add new project type detection patterns to `project-detection.md`
2. Add troubleshooting entries to `troubleshooting.md`
3. Suggest workflow improvements to SKILL.md

## References

- **Conceptual**: See your [[Agent Skills]] Zettel for architecture
- **Git Worktrees**: `git worktree --help`
- **Original Inspiration**: [obra/superpowers using-git-worktrees skill](https://github.com/obra/superpowers/tree/main/skills/using-git-worktrees)
