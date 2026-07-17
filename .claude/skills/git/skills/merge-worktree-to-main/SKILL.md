---
description: 
---

# Merge Worktree to Main

Merges the current git worktree branch back into the main branch locally without requiring remote pushes.

## What it does

1. **Identifies the main repository location** from the worktree setup
2. **Validates the current branch** can be merged cleanly
3. **Switches to the main worktree** (see Main Repository Path Resolution below)
4. **Performs a fast-forward merge** of the feature branch
5. **Optionally cleans up the feature worktree** after successful merge
6. **Shows a summary** of the changes merged

## Main Repository Path Resolution

When locating the main repository (and no `--main-path` is given), check in this order and
use the first one that exists:

1. `~/Programming/<repo-name>`
2. `~/WorkProjects/<repo-name>`
3. `~/IdeaProjects/<repo-name>` (fallback default)

Also account for repos whose main branch is checked out directly in a project directory
rather than under one of these roots (e.g. `~/Programming/<repo-name>` *is* the main
checkout, not a worktree parent) — if the current worktree's `git worktree list` already
shows a non-worktree checkout on the main branch, prefer merging into that path directly
over assuming one of the roots above.

## Prerequisites

- Must be run from within a git worktree (not the main repo)
- The main repository should be clean (no uncommitted changes)
- Feature branch should be up to date with any commits you want to merge

## Usage

Run this command from any git worktree:

```bash
/merge_worktree_to_main
```

## Optional flags

- `--cleanup` - Remove the current worktree after successful merge
- `--dry-run` - Show what would be merged without actually doing it
- `--main-path <path>` - Specify custom main repository path (default: first existing of ~/Programming, ~/WorkProjects, ~/IdeaProjects — see Main Repository Path Resolution)

## Example output

```
🌿 Current worktree: /Users/user/.claude-squad/worktrees/feature_abc123
📍 Main repository: /Users/user/IdeaProjects/claude-squad
🔄 Merging branch: feature/performance-improvements

✅ Fast-forward merge successful!
📈 15 files changed, 700 insertions(+), 292 deletions(-)

🧹 Clean up worktree? (y/N): 
```

## Safety features

- **Pre-merge validation** - Checks for uncommitted changes and merge conflicts
- **Branch verification** - Ensures you're not accidentally merging main into main
- **Path validation** - Confirms main repository location exists and is valid
- **Rollback capability** - Can undo merge if something goes wrong

## Common use cases

- **Feature development** - Merge completed features from worktrees
- **Bug fixes** - Integrate fixes developed in isolated worktrees  
- **Experimentation** - Bring successful experiments back to main
- **Collaborative work** - Merge changes without remote repository dependencies

