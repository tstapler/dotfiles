# Identify Unmerged Changes

Scans all git worktrees (excluding main) to identify uncommitted changes and commits that haven't been merged back to the main branch.

## What it does

1. **Discovers all worktrees for the current repository** using `git worktree list`
2. **Identifies the main repository location** (typically ~/IdeaProjects)
3. **For each non-main worktree of the same project**:
   - Checks for uncommitted/unstaged changes
   - Identifies commits ahead of main branch
   - Shows file modification summaries
   - Calculates merge-ability status
4. **Provides a summary report** of all unmerged work for this project only

**Note**: Only analyzes worktrees that belong to the current git repository, not other projects that may share the same worktree directory structure.

## Output format

```
🔍 Scanning worktrees for unmerged changes...

📁 /Users/user/.claude-squad/worktrees/feature-xyz_abc123
   Branch: feature/performance-improvements
   Status: 🟡 Has unmerged commits
   
   📊 Ahead of main: 4 commits
   🔄 Uncommitted changes: 2 files
   📝 Modified files: app/app.go, ui/list.go
   
   Recent commits not in main:
   - abc123f perf: implement debounced navigation
   - def456a feat: add session caching
   
   Uncommitted changes:
   M  config/config.go
   ?? temp/debug.log

📁 /Users/user/.claude-squad/worktrees/bugfix-abc_def456
   Branch: fix/session-crashes  
   Status: ✅ Clean (all committed, not merged to main)
   
   📊 Ahead of main: 1 commit
   🔄 Uncommitted changes: 0 files
   
   Recent commits not in main:
   - ghi789b fix: prevent session crash on startup

📁 /Users/user/.claude-squad/worktrees/experiment_123abc
   Branch: experiment/new-ui
   Status: 🔴 Has uncommitted work
   
   📊 Ahead of main: 0 commits  
   🔄 Uncommitted changes: 5 files
   📝 Modified files: ui/*, app/experimental.go
   
   Uncommitted changes:
   M  ui/new_component.go
   M  ui/styles.go
   A  app/experimental.go
   ?? ui/temp.backup

===============================================
📋 SUMMARY:
- Total worktrees: 3
- Worktrees with unmerged commits: 2
- Worktrees with uncommitted changes: 2  
- Total unmerged commits: 5
- Estimated merge conflicts: 0 (based on file overlap)
===============================================

🔄 RECOMMENDED ACTIONS:
1. Review feature/performance-improvements - ready to merge but has uncommitted changes
2. Merge fix/session-crashes - clean and ready
3. Commit or stash changes in experiment/new-ui before merging
```

## Use cases

- **Before cleanup** - See what work exists before removing old worktrees
- **Project status** - Get overview of all active development branches  
- **Merge planning** - Identify which branches are ready to merge
- **Work recovery** - Find uncommitted changes that might be lost
- **Conflict detection** - Preview potential merge conflicts across branches

## Safety features

- **Read-only operation** - Never modifies any files or commits
- **Detailed file status** - Shows exactly what files are changed where
- **Merge conflict preview** - Identifies potential conflicts before merging
- **Branch relationship mapping** - Shows how each branch relates to main

## Key insights from analysis

This command helps you understand the "work debt" across your development environment:

- **Large commit counts** (100+ commits ahead) often indicate long-running feature branches or different projects
- **Mixed uncommitted + committed changes** suggest active development that needs attention
- **Clean but unmerged branches** are prime candidates for review and merging
- **High file change counts** may indicate merge conflicts or scope creep

## Common patterns identified

1. **Stale experimental branches** - Many commits ahead but clean working directory
2. **Active development branches** - Both commits and uncommitted changes
3. **Cleanup candidates** - Branches that diverged significantly from main
4. **Merge-ready branches** - Clean state with focused commit count

## Optional flags

- `--verbose` - Show detailed file diffs and commit messages
- `--uncommitted-only` - Only show worktrees with uncommitted changes
- `--commits-only` - Only show worktrees with unmerged commits  
- `--summary-only` - Show just the summary without per-worktree details
- `--merge-candidates` - Only show branches that appear ready to merge (clean + focused)
- `--stale-threshold=N` - Highlight branches more than N commits ahead as potentially stale