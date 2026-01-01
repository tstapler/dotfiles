# Stacked PRs with Jujutsu

Stacked diffs (or stacked PRs) organize related changes into a sequence of dependent commits, each building on the previous. jj naturally supports this workflow.

## Stacked Diffs Mental Model

```
main: A - B - C
              \
               D (refactor: restructure)    <- PR #1 (merge first)
                \
                 E (feat: add validation)   <- PR #2
                  \
                   F (feat: add API)        <- PR #3
                    \
                     G (test: add tests)    <- PR #4
```

Each letter is a separate PR. They must merge in order (D first, then E, etc.).

## Creating a Stack

### Method 1: Build Bottom-Up

```bash
# Start from main
jj new -r main -m "refactor: restructure for new feature"
# ... make changes ...

# Stack next change on top
jj new -m "feat: add validation layer"
# ... make changes ...

# Continue stacking
jj new -m "feat: add API endpoint"
# ... make changes ...

jj new -m "test: add comprehensive tests"
# ... make changes ...
```

### Method 2: Split Existing Work

```bash
# Start with all changes in one commit
jj describe -m "feat: complete feature"

# Split into logical pieces
jj split  # Interactive: remove changes that belong in second commit
jj describe -m "refactor: restructure"

# Move to the new commit (changes removed from first)
jj edit @+
jj describe -m "feat: add validation"

# Split again if needed
jj split
# Continue...
```

## Creating PRs for Each Stack Level

### Manual Approach (Recommended)

```bash
# Create bookmark for each level in stack
jj bookmark create pr-1-refactor -r 'roots(main..@)'
jj bookmark create pr-2-validation -r 'roots(main..@)+'
jj bookmark create pr-3-api -r '@-'
jj bookmark create pr-4-tests -r '@'

# Push all at once
jj git push --allow-new
```

### Using Revsets to Navigate Stack

```bash
# Find all commits in current stack
jj log -r 'trunk()..@'

# Get the root of the stack (first commit)
jj log -r 'roots(trunk()..@)'

# Get specific level (e.g., second commit from trunk)
jj log -r 'roots(trunk()..@)+'
jj log -r 'roots(trunk()..@)++'  # Third level
```

## Updating a Stack

### Editing Middle of Stack

```bash
# Move working copy to commit needing changes
jj edit <change-id>

# Make changes (they automatically snapshot)
# ... edit files ...

# Descendants automatically rebase
jj log  # Verify stack is intact
```

### Rebasing Entire Stack onto Updated Main

```bash
# Fetch latest main
jj git fetch

# Rebase all roots of current stack onto main
jj rebase -s 'all:roots(trunk()..@)' -d main

# Resolve conflicts if any
jj resolve  # Or edit conflict markers directly

# Update all bookmarks
jj bookmark set pr-1-refactor -r 'roots(trunk()..@)'
jj bookmark set pr-2-validation -r 'roots(trunk()..@)+'
# ... etc ...

# Push (force push expected)
jj git push
```

### After Bottom PR Merges

```bash
# Fetch updated main (now contains PR #1)
jj git fetch

# Rebase remaining stack
jj rebase -s 'all:roots(trunk()..@)' -d main

# PR #2 is now the root, update bookmarks
jj bookmark set pr-2-validation -r 'roots(trunk()..@)'
jj bookmark set pr-3-api -r 'roots(trunk()..@)+'
# ... etc ...

# Push
jj git push
```

## Reordering Stack

```bash
# See current order
jj log -r 'trunk()..@'

# Rebase commit E to come before D (swap order)
jj rebase -r E -d C    # Move E to be based on C
jj rebase -r D -d E    # Move D to be based on E

# Alternatively, use new -B to insert
jj new -B D            # Insert new commit before D
jj move --from E --to @  # Move E's changes into new commit
jj abandon E           # Remove now-empty E
```

## Handling Conflicts in Stack

### Conflicts Are Normal

```bash
# Rebase creates conflict in middle of stack
jj rebase -s 'all:roots(trunk()..@)' -d main
# Shows: Rebased 4 commits, 1 with conflicts

# Continue working on other changes if needed
jj edit @  # Work on top of stack

# Resolve conflict when ready
jj edit <conflicted-commit>
jj resolve  # Opens interactive resolver
# Or edit conflict markers directly

# Descendants automatically get resolution
```

### Preview Conflict Impact

```bash
# See which commits have conflicts
jj log -r 'conflict() & trunk()..@'

# See conflict details
jj show -r <conflicted-commit>
```

## Stack Workflow Patterns

### Pattern 1: Feature with Cleanup First

```bash
# Stack structure:
# 1. Cleanup/refactor (can merge independently)
# 2. Feature implementation (needs cleanup)
# 3. Tests (needs feature)

jj new -r main -m "refactor: clean up X for new feature"
# ... cleanup ...
jj new -m "feat: implement feature Y"
# ... implementation ...
jj new -m "test: add tests for feature Y"
# ... tests ...
```

### Pattern 2: Breaking Large PR

```bash
# Start with everything in one commit
jj new -r main -m "feat: large feature"
# ... all changes ...

# Split by file
jj split  # Remove API changes
jj describe -m "refactor: prepare data models"

jj new
jj split  # Remove UI changes
jj describe -m "feat: add API endpoints"

jj new
jj describe -m "feat: add UI components"
```

### Pattern 3: Parallel Stacks

```bash
# Two independent features from same base
jj new -r main -m "feat: feature A"
# ... work on A ...

# Start feature B from same main
jj new -r main -m "feat: feature B"
# ... work on B ...

# Work on both using edit
jj log  # See both branches
jj edit <feature-a-id>  # Switch to A
jj edit <feature-b-id>  # Switch to B
```

## GitHub Integration Tips

### PR Descriptions

Reference dependencies in PR description:
```
## Dependencies
- Depends on #123 (pr-1-refactor)
- Blocked until #123 merges
```

### Force Push Handling

jj rewrites history frequently. GitHub shows "force-pushed" but loses review context.

Mitigation strategies:
- Use "Squash and merge" setting (reduces diff noise)
- Update PRs less frequently
- Add comment before force push explaining changes

### Reviewing Stacked PRs

Reviewers should:
1. Review bottom PR first
2. Review subsequent PRs based on previous
3. Approve in order (bottom to top)

### Merge Order

Always merge bottom of stack first:
1. Merge PR #1
2. Wait for CI on PR #2 (now rebased)
3. Merge PR #2
4. Continue up stack

## Tooling Options

### Manual (Recommended to Learn)

Use raw jj commands as shown above. Best for understanding.

### jj-stack (Community Tool)

```bash
# Install
cargo install jj-stack

# Create stacked PRs
jj-stack create

# Update all PRs in stack
jj-stack update
```

### GitHub CLI Integration

```bash
# Create PR for current commit
gh pr create --base main --head <bookmark-name>

# Create PR targeting another PR
gh pr create --base pr-1-refactor --head pr-2-validation
```

## Best Practices

1. **Keep stacks shallow**: 3-5 levels max for reviewability
2. **One logical change per level**: Each PR should be independently valuable
3. **Bottom commits should be stable**: Minimize changes to already-reviewed levels
4. **Update bookmarks before push**: `jj bookmark set` for each level
5. **Communicate dependencies**: Note in PR description which PRs are blocked
6. **Merge promptly**: Land approved PRs to unblock stack
7. **Rebase frequently**: Keep stack fresh with main to avoid large conflicts
