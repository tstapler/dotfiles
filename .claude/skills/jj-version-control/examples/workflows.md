# Common jj Workflows

## Initial Setup

### New Repository

```bash
# Initialize new jj repo with Git backend
jj git init
# Or with existing directory
jj git init .
```

### Clone Existing Repository

```bash
# Clone Git repository
jj git clone https://github.com/user/repo
cd repo
```

### Add jj to Existing Git Repo (Colocated)

```bash
cd existing-git-repo
jj git init --colocate
# Now both .git and .jj exist
# Both git and jj commands work
```

## Daily Development Workflow

### Starting Fresh Feature

```bash
# Ensure on latest main
jj git fetch
jj new -r main -m "feat: add new user authentication"

# Work on feature
# ... edit files ...

# Check status
jj status
jj diff

# Update description as work progresses
jj describe -m "feat: add user authentication with JWT support"

# When done with this logical change
jj new -m "refactor: extract token validation"
# Continue with next change...
```

### The Squash Workflow (Iterative)

```bash
# Start with a change
jj new -r main -m "feat: initial implementation"

# Work incrementally, squashing into parent
jj describe -m "WIP"
# ... make small changes ...
jj squash  # Moves changes into parent (main)

# Actually, keep building up current change
jj describe -m "WIP"
# ... more changes ...
jj squash  # Again into parent

# When ready, describe properly
jj describe -m "feat: complete feature with tests"
```

### Edit Workflow (Amend in Place)

```bash
# Start feature
jj new -r main -m "feat: user profiles"

# Work is automatically in current commit
# ... edit files ...

# Changes are already part of @
jj status  # Shows changes in current commit

# Want to add more? Just edit, changes auto-include
# ... more edits ...

# Description stays the same unless you change it
jj describe -m "feat: user profiles with avatar support"
```

## Rebasing Workflows

### Rebase Feature Branch onto Main

```bash
# Fetch latest
jj git fetch

# Rebase current branch
jj rebase -b @ -d main

# If conflicts, either:
# 1. Resolve immediately
jj resolve

# 2. Or continue working and resolve later
jj new  # Conflicts stay in history, resolve when convenient
```

### Rebase All Work onto Main

```bash
jj git fetch

# Rebase all branches (commits from trunk to @)
jj rebase -s 'all:roots(trunk()..@)' -d main

# Update bookmarks
jj bookmark set my-feature
jj git push
```

### Interactive Rebase (Insert Commit)

```bash
# Insert a commit between two existing commits
# Current: A -> B -> C (@)
# Want: A -> B -> NEW -> C (@)

jj new -A B  # Insert after B, before C
jj describe -m "refactor: add logging"
# ... make changes ...

# Now: A -> B -> NEW -> C
# C automatically rebased onto NEW
```

## Push Workflows

### First-Time Push

```bash
# Create bookmark
jj bookmark create my-feature

# Push (--allow-new required for new bookmarks)
jj git push --allow-new
```

### Subsequent Pushes

```bash
# Make changes
# ... edit files ...

# Update bookmark to current location
jj bookmark set my-feature

# Push
jj git push
```

### Quick Push Current Change

```bash
# Auto-create bookmark and push
jj git push -c @

# Creates bookmark named push-<change-id>
# Useful for one-off pushes but creates ugly names
```

## Conflict Resolution Workflows

### Resolve Immediately

```bash
# After operation creates conflict
jj status  # Shows conflict

# Option 1: Interactive TUI
jj resolve

# Option 2: Edit conflict markers directly
# Files have <<< === >>> markers like Git
vim conflicted-file.rs
jj describe -m "fix: resolved merge conflict"
```

### Defer Resolution

```bash
# Rebase creates conflict
jj rebase -b @ -d main
# Conflict in middle of history

# Continue working on top
jj new -m "feat: continue development"
# ... work normally ...

# Resolve later
jj edit <conflicted-commit>
jj resolve
# Resolution propagates to descendants
```

## History Cleanup Workflows

### Squash Multiple Commits

```bash
# Have: A -> B -> C -> D (@)
# Want: A -> (B+C+D combined)

jj squash  # D into C
jj squash  # C+D into B
# Now: A -> B (contains B+C+D changes)
```

### Split Commit Into Multiple

```bash
# Have commit with mixed changes
jj split

# Interactive editor opens
# LEFT side: what stays in first commit
# RIGHT side: what goes to second commit
# Remove from RIGHT what should stay in first

# After split:
# Original commit now has subset
# New commit has the rest
```

### Remove Empty Commits

```bash
# Find empty commits
jj log -r 'empty() & mutable()'

# Abandon them
jj abandon 'all:empty() & mutable()'
```

### Move Changes Between Commits

```bash
# Have: A (has X and Y changes) -> B
# Want: A (only X) -> B (has Y)

jj move --from A --to B --interactive
# Select which changes from A go to B
```

## Recovery Workflows

### Undo Last Operation

```bash
# Made a mistake? Undo it
jj undo

# Can undo multiple times
jj undo
jj undo
```

### View Operation History

```bash
# See all operations
jj op log

# Detailed view
jj op log --limit 10
```

### Restore to Previous State

```bash
# Find operation to restore to
jj op log

# Restore to that state
jj op restore --operation <operation-id>
```

### See How Commit Evolved

```bash
# See all versions of a change
jj evolog

# For specific change
jj evolog -r <change-id>
```

## Multi-Branch Workflows

### Work on Multiple Features

```bash
# Create feature A from main
jj new -r main -m "feat: feature A"
# ... work on A ...

# Switch to create feature B
jj new -r main -m "feat: feature B"
# ... work on B ...

# Switch between them
jj edit <feature-a-change-id>
jj edit <feature-b-change-id>

# View all work
jj log
```

### Simultaneous Editing (Advanced)

```bash
# Create merge commit to work on all branches at once
jj new feature-a feature-b feature-c

# Changes here visible when on any branch
# ... make cross-cutting changes ...

# Split changes to appropriate branches
jj move --to feature-a --interactive
jj move --to feature-b --interactive
```

## GitHub PR Workflow

### Create PR

```bash
# Finish work
jj describe -m "feat: complete feature description"

# Create/update bookmark
jj bookmark create pr-feature  # or: jj bookmark set pr-feature

# Push
jj git push --allow-new

# Create PR (using GitHub CLI)
gh pr create --title "Add feature" --body "Description"
```

### Update PR After Review

```bash
# Make requested changes
# ... edit files ...

# Changes are in current commit
jj describe -m "feat: updated per review feedback"

# Update bookmark and push
jj bookmark set pr-feature
jj git push  # Force push is normal
```

### PR Merged - Clean Up

```bash
# Fetch to get merged changes
jj git fetch

# Delete local bookmark
jj bookmark forget pr-feature

# Or if you want to delete from remote too
jj bookmark delete pr-feature
jj git push
```

## Configuration Examples

### Basic User Config

```toml
# ~/.jjconfig.toml

[user]
name = "Your Name"
email = "you@example.com"

[ui]
default-command = "log"
diff-editor = ":builtin"
paginate = "auto"

[git]
push-bookmark-prefix = "push-"
```

### Useful Aliases

```toml
[aliases]
# Tug: move nearest bookmark to current commit
tug = ['bookmark', 'move', '--from', 'heads(::@- & bookmarks())', '--to', '@']

# Show current stack
stack = ['log', '-r', 'trunk()..@']

# Show unpushed work
unpushed = ['log', '-r', 'bookmarks() & ~remote_bookmarks()']
```

### Revset Aliases

```toml
[revset-aliases]
'wip' = 'mine() & mutable() & ~empty()'
'review' = 'bookmarks() & ~::trunk() & ~conflict()'
'cleanup' = 'empty() & mutable()'
```
