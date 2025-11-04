---
title: JJ Undo
description: Safely undo operations using Jujutsu's operation log
arguments: [steps]
---

# Jujutsu Undo Operations

You are being invoked to help safely undo operations using Jujutsu's powerful operation log feature.

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

## Jujutsu Operation Log: Your Safety Net

Jujutsu records EVERY operation you perform in an operation log. This means:
- ✅ **Nothing is ever truly lost** - all operations are recorded
- ✅ **Complete undo capability** - revert any operation
- ✅ **Time travel** - restore to any previous state
- ✅ **Safe experimentation** - try anything, undo if it doesn't work

## Operation Log Commands

### **View Operation History**
```bash
jj op log                    # View all operations
jj op log --limit 10         # View last 10 operations
jj op show <operation-id>    # View details of specific operation
```

### **Undo Operations**
```bash
jj undo                      # Undo last operation
jj undo <operation-id>       # Undo specific operation
jj op restore <operation-id> # Restore to exact state at that operation
```

### **Understanding the Difference**
- `jj undo`: Reverses the effects of an operation (creates new operation)
- `jj op restore`: Restores repo to exact state at that operation (creates new operation)

## Common Undo Scenarios

Use the **jj-stacked-pr** agent to handle:

### **1. Undo Last Commit**
```bash
jj undo
```
Reverts the last operation (e.g., commit, rebase, squash).

### **2. Undo Multiple Operations**
```bash
jj op log  # Find the operation before the mistakes
jj op restore <operation-id>
```
Restores to state before the mistakes began.

### **3. Undo Rebase Gone Wrong**
```bash
jj undo
```
Immediately reverts the rebase operation.

### **4. Recover Deleted Commit**
```bash
jj op log  # Find operation before deletion
jj op restore <operation-id>
```
Restores deleted commit.

### **5. Undo Accidental Force Push**
```bash
jj undo  # Reverts local changes
# Then force push again to restore remote
```

## Operation Log Structure

Each operation shows:
- **Operation ID**: Unique identifier for the operation
- **Timestamp**: When operation occurred
- **User**: Who performed the operation
- **Command**: What command was run
- **Changes**: What changed in the operation

Example output:
```
@  f8a3b2c1 2025-10-28 10:23:45 tyler@laptop
│  jj rebase -d trunk
│
○  d9e7f6a4 2025-10-28 10:20:12 tyler@laptop
│  jj commit -m "feat: add new feature"
```

## Safety Best Practices

✅ **Before risky operations:**
1. Run `jj op log` to note current operation ID
2. Perform the risky operation
3. Verify result with `jj log`
4. If wrong: `jj undo` immediately

✅ **Regular operation log checks:**
```bash
jj op log --limit 5  # Check recent operations
```
Helps you understand what you've been doing.

✅ **Experiment freely:**
Since everything can be undone, try things! If it doesn't work, just `jj undo`.

## Undo vs Restore: When to Use Each

### **Use `jj undo`** when:
- You want to reverse the last operation
- You made a mistake and want to revert it
- You want to undo a specific operation's effects

### **Use `jj op restore`** when:
- You want to go back to an exact previous state
- Multiple operations need to be undone
- You want to "time travel" to a known good state

## Advanced: Undo History

Operations form a **log**, not a tree:
- Each undo creates a new operation
- You can undo an undo!
- The operation log keeps growing
- Old operations can be garbage collected (rare)

```
Original:  A → B → C → D
After undo: A → B → C → D → E (E undoes D)
```

## Example Workflows

**Workflow 1: Undo Bad Commit**
```bash
# Made a bad commit
jj commit -m "bad commit"

# Immediately undo
jj undo

# Changes are back in working copy
```

**Workflow 2: Undo Several Operations**
```bash
# View recent operations
jj op log --limit 10

# Find operation before mistakes (e.g., operation d9e7f6a4)
jj op restore d9e7f6a4

# Repo restored to that state
```

**Workflow 3: Redo After Undo**
```bash
# Undo something
jj undo

# Wait, that was wrong, redo it
jj undo  # Undo the undo!
```

**Workflow 4: Recover Lost Work**
```bash
# Oh no, I lost my commit!
jj op log  # Find when commit existed

# Restore to that state
jj op restore <operation-id>

# Or create new commit with those changes
jj new <old-change-id>
```

## Error Handling

**If you encounter "command not found: jj":**
1. Stop immediately
2. Provide installation instructions (see Prerequisites section above)
3. Wait for user to install jj
4. Verify installation with `jj --version`
5. Only then proceed with undo operations

**If you encounter "not a jj repository":**
1. Check if this is a git repository
2. If yes: Run `jj git init --colocate` to initialize jj
3. If no: User needs to initialize repository first

**If you can't find the operation to restore:**
1. Use `jj op log` with no limit to see full history
2. Use `jj op show <operation-id>` to verify it's the right one
3. Operation IDs can be partial (first few characters)

**If undo doesn't seem to work:**
1. Check what `jj undo` actually did with `jj op log`
2. Remember: `jj undo` creates a new operation that reverses effects
3. If confused, use `jj op restore` to go to known good state

## Troubleshooting Common Issues

**"I can't find my old commit"**
- Run `jj op log` and look for when it existed
- Use `jj op restore` to go back to that state
- Then `jj new <change-id>` to recreate it

**"I undid too much"**
- Run `jj op log` to see the undo operation
- Run `jj undo` to undo the undo

**"My operation log is huge"**
- Normal! Operations accumulate over time
- jj will eventually garbage collect very old operations
- You can manually clean with `jj operation abandon` (advanced)

**"I'm lost and don't know what state I'm in"**
1. Run `jj log` to see commit state
2. Run `jj op log --limit 20` to see recent operations
3. Run `jj status` to see working directory state
4. If needed: `jj op restore <safe-operation-id>` to known good state

## Understanding Operation IDs

**Operation IDs are unique identifiers:**
- Full ID: `f8a3b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9`
- You can use short form: `f8a3b2c1` (first 8 chars)
- As long as it's unique, shorter is fine

**Finding operations:**
```bash
# Recent operations
jj op log --limit 10

# Search operation log (shows descriptions)
jj op log | grep "commit"

# Show specific operation details
jj op show f8a3b2c1
```

## Mental Model

Think of the operation log as a **complete audit trail**:
- Every action is recorded
- You can rewind to any point
- Nothing is ever truly deleted
- Experimentation is safe

This is jj's superpower: **fearless version control**.

## Practical Examples

**Example 1: Accidentally committed to wrong branch**
```bash
# Committed to wrong location
jj commit -m "feature work"

# Undo the commit
jj undo

# Now create commit at correct location
jj new <correct-parent-change-id>
jj commit -m "feature work"
```

**Example 2: Rebased wrong commits**
```bash
# Did a rebase that went wrong
jj rebase -s <change-id> -d trunk

# Verify it's wrong
jj log

# Undo the rebase
jj undo

# Check state is restored
jj log
```

**Example 3: Want to see what changed in an operation**
```bash
# View specific operation details
jj op show <operation-id>

# This shows:
# - What command was run
# - What commits changed
# - What files were affected
```

**Example 4: Going back in time to debug**
```bash
# Want to see repo state from yesterday
jj op log --limit 50  # Find operation from yesterday

# Restore to that state
jj op restore <operation-id>

# Investigate...
jj log
jj status

# When done, restore to current state
jj op restore <latest-operation-id>
```

## Workflow

Invoke the **jj-stacked-pr** agent to:

1. **Verify prerequisites** - Check jj installation
2. **Analyze operation log** with `jj op log`
3. **Identify** the operation to undo or restore to
4. **Execute** appropriate undo/restore command
5. **Verify** the result with `jj log` and `jj status`
6. **Continue work** with confidence

The agent will ensure safe, correct undo operations using jj's operation log.

---

**Remember**: With jj, you can't break anything permanently. If something goes wrong, just `jj undo`!
