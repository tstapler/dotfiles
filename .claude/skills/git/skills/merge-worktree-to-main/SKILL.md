---
description: ''
prompt: "# Merge Worktree to Main\n\nMerges the current git worktree branch back into\
  \ the main branch locally without requiring remote pushes.\n\n## What it does\n\n\
  1. **Identifies the main repository location** from the worktree setup\n2. **Validates\
  \ the current branch** can be merged cleanly\n3. **Switches to the main worktree**\
  \ (typically in ~/IdeaProjects)\n4. **Performs a fast-forward merge** of the feature\
  \ branch\n5. **Optionally cleans up the feature worktree** after successful merge\n\
  6. **Shows a summary** of the changes merged\n\n## Prerequisites\n\n- Must be run\
  \ from within a git worktree (not the main repo)\n- The main repository should be\
  \ clean (no uncommitted changes)\n- Feature branch should be up to date with any\
  \ commits you want to merge\n\n## Usage\n\nRun this command from any git worktree:\n\
  \n```bash\n/merge_worktree_to_main\n```\n\n## Optional flags\n\n- `--cleanup` -\
  \ Remove the current worktree after successful merge\n- `--dry-run` - Show what\
  \ would be merged without actually doing it\n- `--main-path <path>` - Specify custom\
  \ main repository path (default: ~/IdeaProjects)\n\n## Example output\n\n```\n\U0001F33F\
  \ Current worktree: /Users/user/.claude-squad/worktrees/feature_abc123\n\U0001F4CD\
  \ Main repository: /Users/user/IdeaProjects/claude-squad\n\U0001F504 Merging branch:\
  \ feature/performance-improvements\n\n✅ Fast-forward merge successful!\n\U0001F4C8\
  \ 15 files changed, 700 insertions(+), 292 deletions(-)\n\n\U0001F9F9 Clean up worktree?\
  \ (y/N): \n```\n\n## Safety features\n\n- **Pre-merge validation** - Checks for\
  \ uncommitted changes and merge conflicts\n- **Branch verification** - Ensures you're\
  \ not accidentally merging main into main\n- **Path validation** - Confirms main\
  \ repository location exists and is valid\n- **Rollback capability** - Can undo\
  \ merge if something goes wrong\n\n## Common use cases\n\n- **Feature development**\
  \ - Merge completed features from worktrees\n- **Bug fixes** - Integrate fixes developed\
  \ in isolated worktrees  \n- **Experimentation** - Bring successful experiments\
  \ back to main\n- **Collaborative work** - Merge changes without remote repository\
  \ dependencies\n"
---

# Merge Worktree to Main

Merges the current git worktree branch back into the main branch locally without requiring remote pushes.

## What it does

1. **Identifies the main repository location** from the worktree setup
2. **Validates the current branch** can be merged cleanly
3. **Switches to the main worktree** (typically in ~/IdeaProjects)
4. **Performs a fast-forward merge** of the feature branch
5. **Optionally cleans up the feature worktree** after successful merge
6. **Shows a summary** of the changes merged

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
- `--main-path <path>` - Specify custom main repository path (default: ~/IdeaProjects)

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
