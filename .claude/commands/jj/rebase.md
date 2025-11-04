---
title: JJ Rebase
description: Interactive rebasing help with Jujutsu's powerful rebase capabilities
arguments: [target, source]
---

# Jujutsu Interactive Rebase

You are being invoked to help with rebasing operations using Jujutsu's powerful and safe rebase capabilities.

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

**For more information on jj:**
- Documentation: https://martinvonz.github.io/jj/
- GitHub: https://github.com/martinvonz/jj
- Tutorial: https://martinvonz.github.io/jj/latest/tutorial/

---

## Request Details

**ONLY proceed after verifying jj is installed and configured.**

$ARGUMENTS

## Jujutsu Rebase Advantages

Unlike git, jj rebasing is:
- ✅ **Safe**: Operation log allows complete undo
- ✅ **Automatic**: Descendants rebase automatically when you edit a commit
- ✅ **Powerful**: Revsets allow rebasing entire stacks in one command
- ✅ **Non-destructive**: Original commits preserved in operation log

## Common Rebase Scenarios

Use the **jj-stacked-pr** agent to handle:

### **1. Rebase Current Commit on Trunk**
```bash
jj rebase -d trunk
```
Moves current commit (and descendants) onto trunk.

### **2. Rebase Entire Stack on Trunk**
```bash
jj rebase -s 'all:roots(trunk..@)' -d trunk
```
Rebases all commits in the stack from trunk to current position.

### **3. Rebase Specific Commit**
```bash
jj rebase -s <change-id> -d <destination>
```
Rebases a specific commit and its descendants to a new destination.

### **4. Rebase Range of Commits**
```bash
jj rebase -s <start-change-id> -d <destination>
```
Rebases from a specific commit to its descendants.

### **5. Insert Commit in Middle of Stack**
```bash
# Create new commit at desired location
jj new <parent-change-id>
# Make changes
jj commit -m "New commit"
# Rebase old children onto new commit
jj rebase -s <old-child-change-id> -d @
```

## Rebase Flags

- `-s, --source`: Source commit(s) to rebase (can use revsets)
- `-d, --destination`: Destination to rebase onto
- `-r, --revisions`: Specific revisions to rebase (use for non-contiguous)
- `-b, --branch`: Rebase entire branch

## Revsets for Rebasing

**Useful patterns:**
- `trunk..@` - All commits from trunk to current
- `all:roots(trunk..@)` - All root commits in the range
- `@-::@` - Last two commits (inclusive range)
- `descendants(@)` - All descendants of current commit

## Safety Features

**Operation Log:**
```bash
jj op log            # View all operations
jj op show <id>      # View specific operation details
jj undo              # Undo last operation
jj op restore <id>   # Restore to specific operation
```

If rebase goes wrong: `jj undo` to revert!

## Automatic Descendant Rebasing

When you rebase a commit, jj automatically rebases all descendants. This means:
- Edit any commit in a stack
- All commits above it update automatically
- No manual rebasing of each commit needed

## Example Workflows

**Workflow 1: Update Stack After Trunk Moves**
```bash
# Fetch latest
jj git fetch

# Rebase entire stack
jj rebase -s 'all:roots(trunk..@)' -d trunk

# Verify
jj log -r 'trunk..@'
```

**Workflow 2: Reorder Commits in Stack**
```bash
# Move commit X after commit Y
jj rebase -s <commit-x-id> -d <commit-y-id>

# Verify order
jj log
```

**Workflow 3: Resolve Rebase Conflicts**
```bash
# If conflicts occur during rebase
jj status  # See conflicted files

# Edit files to resolve conflicts
# ... resolve conflicts ...

# Continue (no special command needed, just commit)
jj commit -m "Resolved conflicts"
```

## When to Rebase

✅ **Good times to rebase:**
- Trunk has moved forward and you need latest changes
- You need to reorder commits in your stack
- You want to move commits to different parents
- You need to insert a commit in the middle of a stack

❌ **Think twice before rebasing:**
- Commits have already been merged (use new commits instead)
- You're rebasing shared branches others depend on
- You don't understand the current state (analyze first!)

## Error Handling

**If you encounter "command not found: jj":**
1. Stop immediately
2. Provide installation instructions (see Prerequisites section above)
3. Wait for user to install jj
4. Verify installation with `jj --version`
5. Only then proceed with rebase operations

**If you encounter "not a jj repository":**
1. Check if this is a git repository
2. If yes: Run `jj git init --colocate` to initialize jj
3. If no: User needs to initialize repository first

**If rebase results in conflicts:**
1. Don't panic - conflicts are normal
2. Run `jj status` to see conflicted files
3. Edit files to resolve conflicts manually
4. Conflicts are automatically resolved when you commit
5. If you want to abort: `jj undo` to revert the rebase

**If you're unsure about rebase state:**
1. Run `jj log` to visualize commit graph
2. Run `jj op log` to see recent operations
3. You can always `jj undo` to go back

## Workflow

Invoke the **jj-stacked-pr** agent to:

1. **Verify prerequisites** - Check jj installation
2. **Analyze current state** with `jj log` and revsets
3. **Plan the rebase** operation
4. **Execute** the rebase with appropriate flags
5. **Verify** the result with `jj log`
6. **Handle conflicts** if they occur
7. **Update remote branches** if needed

The agent will ensure safe, correct rebasing using jj's powerful capabilities.
