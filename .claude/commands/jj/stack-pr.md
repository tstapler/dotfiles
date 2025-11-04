---
title: JJ Stack PR
description: Create granular commits and stacked PRs using Jujutsu (jj) version control
arguments: [action]
---

# Jujutsu Stacked PR Workflow

You are being invoked to help with Jujutsu (jj) stacked PR workflows. Use the **jj-stacked-pr** agent to provide specialized expertise in:
- Creating granular, reviewable commits from large changes
- Building stacked commit dependencies
- Managing GitHub PRs for commit stacks
- Rebasing and maintaining commit stacks
- Splitting/squashing commits using jj commands

## Prerequisites Check

**BEFORE proceeding with any jj operations, you MUST verify that jj is installed:**

```bash
# Check if jj is installed
jj --version
```

### If jj is NOT installed:

**Installation Instructions for macOS (Homebrew):**
```bash
# Install jj using Homebrew
brew install jj

# Verify installation
jj --version
```

**Alternative Installation Methods:**

**Using Cargo (Rust package manager):**
```bash
# Install from crates.io
cargo install --locked jj-cli

# Add to PATH if needed
export PATH="$HOME/.cargo/bin:$PATH"

# Verify
jj --version
```

**From source:**
```bash
# Clone repository
git clone https://github.com/martinvonz/jj.git
cd jj

# Build and install
cargo install --path cli

# Verify
jj --version
```

**For other platforms**, see: https://github.com/martinvonz/jj#installation

### Common Installation Issues

**Issue: "command not found: jj"**
- Solution: Install jj using one of the methods above
- Verify PATH includes Homebrew binaries: `echo $PATH | grep homebrew`

**Issue: "jj: command not found" after installation**
- Solution: Restart your terminal or run `source ~/.zshrc` (or `~/.bashrc`)
- Check installation location: `which jj`

**Issue: Permission errors during installation**
- Solution: Use `sudo` with Homebrew or ensure Cargo directory is writable
- Homebrew: `sudo chown -R $(whoami) /opt/homebrew`

### First-Time jj Setup

**After installing jj for the first time, configure your identity:**
```bash
# Set your name and email
jj config set --user user.name "Your Name"
jj config set --user user.email "your.email@example.com"

# Verify configuration
jj config list --user
```

### Repository Check

**Verify this is a jj repository:**
```bash
# Check repository status
jj status
```

**If you get "not a jj repository" error:**
```bash
# Option 1: Initialize jj in existing git repo
jj git init --colocate

# Option 2: Clone with jj
jj git clone <repository-url>
```

### GitHub CLI Check

**Stacked PRs require GitHub CLI (gh) for creating multiple PRs:**
```bash
# Check if gh is installed
gh --version
```

**If gh is not installed:**
```bash
# macOS with Homebrew
brew install gh

# Authenticate with GitHub
gh auth login

# Verify
gh auth status
```

**For more information:**
- jj Documentation: https://martinvonz.github.io/jj/
- jj GitHub: https://github.com/martinvonz/jj
- jj Tutorial: https://martinvonz.github.io/jj/latest/tutorial/
- gh Documentation: https://cli.github.com/

---

## Action Requested

**ONLY proceed after verifying jj and gh are installed and configured.**

$ARGUMENTS

## Workflow

Invoke the **jj-stacked-pr** agent using the Task tool to handle this request. The agent has deep expertise in:
- Jujutsu CLI operations (split, squash, rebase, etc.)
- Stacked diff best practices
- Revsets for commit queries
- GitHub PR chain management
- Granular commit crafting

## Expected Process

The jj-stacked-pr agent will:

1. **Verify prerequisites** - Check jj and gh installation
2. **Analyze** the current state using `jj log` and `jj status`
3. **Plan** the commit stack structure and logical boundaries
4. **Execute** commit operations using jj commands
5. **Create** GitHub PRs with proper base branch targeting
6. **Document** the stack with clear PR descriptions

## Common Use Cases

### **Split large changes**
"Split my current changes into reviewable commits"
- Agent analyzes working directory
- Identifies logical boundaries
- Uses `jj split` to create granular commits
- Ensures each commit is independently reviewable

### **Create stack**
"Create a stack of PRs for this feature"
- Agent examines commit history
- Creates GitHub branches for each commit
- Opens PRs with proper base branch targeting
- Links PRs together in descriptions

### **Rebase stack**
"Rebase my stack on latest main"
- Agent fetches latest main/trunk
- Uses `jj rebase` to update stack
- Handles conflicts if they occur
- Force-pushes updated branches

### **Fix commit**
"Edit commit X in the middle of my stack"
- Agent uses `jj edit` to modify specific commit
- Automatically rebases descendants
- Updates affected GitHub PRs
- Preserves stack integrity

### **Insert commit**
"Add a new commit between X and Y"
- Agent creates new commit at desired location
- Rebases dependent commits
- Creates new PR in the stack
- Updates PR descriptions to reflect new order

## Key jj Commands for Stacked Workflows

### **Commit Operations**
```bash
jj split              # Interactively split changes into commits
jj squash             # Squash current changes into parent
jj describe -m "msg"  # Set commit message
jj new                # Create new commit
jj edit <change-id>   # Edit specific commit in stack
```

### **Stack Navigation**
```bash
jj log                # View commit graph
jj log -r 'trunk..@'  # View commits from trunk to current
jj prev               # Move to parent commit
jj next               # Move to child commit
```

### **Stack Rebasing**
```bash
jj rebase -d trunk                        # Rebase current on trunk
jj rebase -s 'all:roots(trunk..@)' -d trunk  # Rebase entire stack
jj rebase -s <change-id> -d <dest>       # Rebase specific commit
```

### **Branch Management**
```bash
jj branch create feature-part-1          # Create branch at current commit
jj branch set feature-part-1             # Move branch to current commit
jj git push --branch feature-part-1      # Push branch to remote
```

## GitHub PR Stack Management

### **Creating Stacked PRs**
```bash
# For each commit in the stack:
jj edit <change-id>
jj branch create feature-part-N
jj git push --branch feature-part-N

# Then use gh to create PR
gh pr create --base <parent-branch> --head feature-part-N \
  --title "Part N: Description" \
  --body "Stack: Builds on #PARENT_PR"
```

### **PR Stack Description Template**
```markdown
## Stack Position
- **Builds on**: #123 (previous PR in stack)
- **Depended on by**: #125 (next PR in stack)

## What This PR Does
Brief description of this specific commit's changes.

## Review Notes
- Review this independently from the rest of the stack
- Changes are self-contained within this commit
- Safe to merge once parent PR is merged
```

## Error Handling

**If you encounter "command not found: jj":**
1. Stop immediately
2. Provide installation instructions (see Prerequisites section above)
3. Wait for user to install jj
4. Verify installation with `jj --version`
5. Only then proceed with stack operations

**If you encounter "command not found: gh":**
1. Stop immediately
2. Provide gh installation instructions
3. Ensure user authenticates with `gh auth login`
4. Verify with `gh auth status`
5. Only then proceed with PR creation

**If you encounter "not a jj repository":**
1. Check if this is a git repository
2. If yes: Run `jj git init --colocate` to initialize jj
3. If no: User needs to initialize repository first

**If stack rebasing causes conflicts:**
1. Don't panic - conflicts are expected
2. Show conflicted files with `jj status`
3. Guide user through conflict resolution
4. Continue with `jj commit` after resolution
5. If needed: `jj undo` to abort rebase

**If PR creation fails:**
1. Verify gh authentication: `gh auth status`
2. Check branch exists remotely: `jj git push --branch <name>`
3. Verify base branch exists and is up to date
4. Check GitHub permissions for repository

## Best Practices for Stacked PRs

### **Commit Granularity**
✅ Each commit should:
- Represent one logical change
- Be independently reviewable (< 15 min review time)
- Have a clear, descriptive message
- Build successfully and pass tests

❌ Avoid:
- Mixing unrelated changes
- Creating dependencies between unrelated commits
- Making commits too small (single line changes)
- Making commits too large (> 500 lines)

### **Stack Ordering**
✅ Proper order:
1. Infrastructure/schema changes
2. Core functionality
3. API/interface changes
4. UI/frontend changes
5. Tests
6. Documentation

❌ Wrong order:
- Using new APIs before they're defined
- Referencing database tables before migrations
- Tests before implementation exists

### **PR Descriptions**
✅ Good descriptions:
- Clear stack position (part N of M)
- Links to parent and child PRs
- Explains what THIS commit does
- Notes any review considerations

❌ Poor descriptions:
- "Part 2" (no context)
- Missing stack links
- Describing entire feature instead of this commit
- No guidance for reviewers

## Stacked PR Review Workflow

For reviewers:
1. Start with the bottom PR (closest to trunk)
2. Review each PR independently
3. Approve and merge bottom PR first
4. GitHub will automatically update base branches
5. Continue up the stack

For authors:
1. Address review feedback on affected commits
2. Use `jj edit` to modify specific commits
3. Force push updated branches
4. PRs update automatically
5. Notify reviewers of updates

## Advanced: Revsets for Stacks

**Useful revset queries:**
```bash
# All commits in current stack
jj log -r 'trunk..@'

# Root commits of the stack
jj log -r 'all:roots(trunk..@)'

# Descendants of a specific commit
jj log -r 'descendants(<change-id>)'

# Commits that changed specific files
jj log -r 'file(path/to/file.java)'

# Commits in last N days
jj log -r 'trunk..@ & committer-date(after:"7 days ago")'
```

## Example Complete Stacked PR Workflow

```bash
# 1. Verify prerequisites
jj --version && gh --version

# 2. Start from trunk
jj new trunk

# 3. Make changes and split into commits
# ... make changes ...
jj split  # Create first logical commit
jj describe -m "feat(db): add user_preferences table"

jj new  # Start next commit
# ... make more changes ...
jj split  # Create second logical commit
jj describe -m "feat(api): add preferences endpoints"

# 4. Create branches and push
jj edit <commit-1-change-id>
jj branch create feature-db-schema
jj git push --branch feature-db-schema

jj edit <commit-2-change-id>
jj branch create feature-api-endpoints
jj git push --branch feature-api-endpoints

# 5. Create PRs
gh pr create --base trunk --head feature-db-schema \
  --title "Part 1: Add user preferences table"

gh pr create --base feature-db-schema --head feature-api-endpoints \
  --title "Part 2: Add preferences API endpoints"

# 6. View the stack
jj log -r 'trunk..@'
```

## Troubleshooting Stack Issues

**Problem: Lost track of stack structure**
```bash
# Visualize the entire stack
jj log -r 'trunk..@'

# See operation history
jj op log
```

**Problem: Need to insert commit in middle**
```bash
# Navigate to parent of insertion point
jj edit <parent-change-id>

# Create new commit
jj new
# ... make changes ...
jj commit -m "new commit"

# Rebase old children onto new commit
jj rebase -s <old-child-change-id> -d @
```

**Problem: Need to remove commit from stack**
```bash
# Option 1: Squash into parent
jj squash -r <change-id>

# Option 2: Abandon commit
jj abandon <change-id>
# Children automatically rebase onto parent
```

**Problem: Stack got out of sync with remote**
```bash
# Fetch latest
jj git fetch

# Rebase entire stack
jj rebase -s 'all:roots(trunk..@)' -d trunk

# Force push all branches
jj git push --all --force
```

## Workflow Summary

Invoke the **jj-stacked-pr** agent to handle any stacked PR workflow. The agent will:

1. ✅ Verify all prerequisites (jj, gh, repository state)
2. ✅ Analyze current state and plan approach
3. ✅ Execute jj commands safely with error handling
4. ✅ Create and manage GitHub PRs correctly
5. ✅ Provide clear guidance and documentation
6. ✅ Handle errors gracefully with actionable solutions

The agent ensures your stacked PR workflow is smooth, safe, and follows best practices.

Proceed by invoking the jj-stacked-pr agent with the Task tool.
