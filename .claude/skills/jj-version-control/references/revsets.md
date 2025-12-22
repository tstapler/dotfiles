# Advanced Revsets Reference

## Complete Operator Reference

### Navigation Operators

| Operator | Meaning | Notes |
|----------|---------|-------|
| `-` suffix | Parent | `@-` = parent, `@--` = grandparent |
| `+` suffix | Child | Only works when child is unique |
| `::x` | All ancestors of x | Leading `::` |
| `x::` | All descendants of x | Trailing `::` |
| `x::y` | DAG range between x and y | Equivalent to `x:: & ::y` |
| `..x` | All ancestors of x | Same as `::x` |
| `x..` | All commits not ancestors of x | Everything after x |
| `x..y` | Commits reachable from y but not x | Range operator |

### Set Operators

| Operator | Meaning | SQL Equivalent |
|----------|---------|----------------|
| `\|` | Union | OR |
| `&` | Intersection | AND |
| `~` | Difference | NOT IN |
| `()` | Grouping | Parentheses |

### Operator Precedence (Highest to Lowest)

1. `()` - Grouping
2. `::`, `..` - Ancestry
3. `-`, `+` - Parent/child
4. `~` - Difference
5. `&` - Intersection
6. `|` - Union

## Complete Function Reference

### Selection Functions

```
root()              - Repository root commit
trunk()             - Main branch (auto-detects main/master from origin/upstream)
all()               - All commits in repository
none()              - Empty set
heads(revset)       - Commits with no children in revset
roots(revset)       - Commits with no parents in revset
parents(revset)     - Immediate parents of commits
children(revset)    - Immediate children of commits
ancestors(revset)   - All ancestors
ancestors(revset, depth)  - Ancestors up to depth
descendants(revset) - All descendants
```

### Reference Functions

```
bookmarks()         - All bookmarked commits
bookmarks(pattern)  - Bookmarks matching pattern
remote_bookmarks()  - All remote bookmarks
remote_bookmarks(pattern)     - Remote bookmarks matching pattern
remote_bookmarks(exact:"name") - Exact match
tags()              - All tagged commits
branches()          - All branch heads (Git backend)
```

### Author/Committer Functions

```
mine()              - Commits by current user
author(pattern)     - Commits by author matching pattern
author("email@")    - Substring match
author(exact:"Full Name")  - Exact match
committer(pattern)  - Commits with committer matching pattern
```

### Content Functions

```
description(pattern)    - Commits with message matching pattern
file(path)              - Commits touching file
file(pattern)           - Commits touching files matching pattern
diff_contains(pattern)  - Commits where diff contains pattern
```

### State Functions

```
empty()             - Commits with no changes
conflict()          - Commits with unresolved conflicts
immutable()         - Commits that shouldn't be rewritten
mutable()           - Commits that can be rewritten
hidden()            - Hidden commits
visible_heads()     - Visible head commits
```

### ID Functions

```
commit_id(id)       - Specific commit by full/partial ID
change_id(id)       - Specific change by ID
```

## Pattern Matching

### String Patterns

```bash
# Substring (default)
bookmarks("feature")        # Contains "feature"
author("alice")             # Author contains "alice"

# Exact match
bookmarks(exact:"main")     # Exactly "main"
author(exact:"Alice Smith") # Exactly "Alice Smith"

# Glob patterns
author("*@company.com")     # Email ending in @company.com
file("src/**/*.rs")         # Rust files in src/
```

## Practical Revset Recipes

### Branch Management

```bash
# Local-only bookmarks (not pushed)
jj log -r 'bookmarks() & ~remote_bookmarks()'

# Stale bookmarks (ancestor of trunk)
jj log -r 'bookmarks() & ::trunk()'

# Bookmarks with conflicts
jj log -r 'bookmarks() & conflict()'
```

### Work Organization

```bash
# My work since branching from trunk
jj log -r 'mine() & trunk()..@'

# My work in progress (non-empty, mutable)
jj log -r 'mine() & mutable() & ~empty()'

# Everything I can safely modify
jj log -r 'mutable() & mine()'

# Changes waiting for review (has bookmark, not merged)
jj log -r 'bookmarks() & ~::trunk()'
```

### Cleanup Operations

```bash
# Empty commits to remove
jj log -r 'empty() & mutable()'

# Abandoned work (no bookmark, not ancestor of any bookmark)
jj log -r 'mutable() & ~::bookmarks()'

# Conflicted commits needing resolution
jj log -r 'conflict()'
```

### History Exploration

```bash
# Recent commits by author
jj log -r 'author("alice") & trunk()..@'

# Commits touching specific file
jj log -r 'file("src/main.rs")'

# Commits mentioning bug in description
jj log -r 'description("fix") & trunk()..'

# Merge commits
jj log -r 'merge()'
```

### Rebase Operations

```bash
# Rebase all my branches onto updated trunk
jj rebase -s 'all:roots(trunk()..@)' -d trunk()

# Rebase specific branch and descendants
jj rebase -s feature:: -d main

# Rebase keeping merge structure
jj rebase -b feature -d main
```

## Revset Aliases

Define in `~/.jjconfig.toml`:

```toml
[revset-aliases]
# Work in progress
'wip' = 'mine() & mutable() & ~empty()'

# Current stack
'stack' = 'trunk()..@'

# Needs push
'unpushed' = 'bookmarks() & ~remote_bookmarks()'

# Ready for review
'review' = 'bookmarks() & ~::trunk() & ~conflict()'

# Cleanup candidates
'cleanup' = 'empty() & mutable()'

# Recent work
'recent' = 'committer_date(after:"1 week ago") & mine()'
```

## Using Revsets with Commands

### Commands Accepting `-r`/`--revisions`

```bash
jj log -r '<revset>'
jj diff -r '<revset>'
jj show -r '<revset>'
jj describe -r '<revset>'
jj abandon -r '<revset>'
```

### Commands with Source/Destination

```bash
jj rebase -s '<source_revset>' -d '<dest_revset>'
jj rebase -b '<branch_revset>' -d '<dest_revset>'
jj move --from '<revset>' --to '<revset>'
```

### Multiple Commits Require `all:` Prefix

When a revset matches multiple commits and the command needs explicit permission:

```bash
# ERROR: revset matches multiple commits
jj abandon 'empty()'

# Correct: use all: prefix
jj abandon 'all:empty()'
```

## Debugging Revsets

### Preview Before Actions

```bash
# See what a revset matches
jj log -r '<revset>'

# Count matches
jj log -r '<revset>' --no-graph | wc -l

# Show with template
jj log -r '<revset>' -T 'change_id.shortest() ++ " " ++ description.first_line() ++ "\n"'
```

### Common Revset Errors

**"Revset resolved to more than one revision"**
- Command expects single commit
- Solution: Narrow revset or use `all:` prefix

**"Revset resolved to no revisions"**
- Empty result
- Solution: Verify revset logic with `jj log -r`

**"Unknown function"**
- Typo in function name
- Solution: Check spelling, use tab completion
