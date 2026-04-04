---
description: Create granular commits and stacked PRs using Jujutsu (jj) version control.
  ONLY use this skill when the user explicitly mentions jj or Jujutsu. For standard
  git commits, branches, or PRs use the git:commit or git:create-pr skills instead.
prompt: "# Jujutsu Stacked PR Workflow\n\n> **IMPORTANT**: This skill is for **Jujutsu\
  \ (jj)** workflows only. If the user asked for a commit, branch, or PR without mentioning\
  \ `jj`, stop and use the `git:commit` or `git:create-pr` skill instead.\n\nYou are\
  \ being invoked to help with Jujutsu (jj) stacked PR workflows. Use the **jj-stacked-pr**\
  \ agent to provide specialized expertise in:\n- Creating granular, reviewable commits\
  \ from large changes\n- Building stacked commit dependencies\n- Managing GitHub\
  \ PRs for commit stacks\n- Rebasing and maintaining commit stacks\n- Splitting/squashing\
  \ commits using jj commands\n\n## Prerequisites Check\n\n**BEFORE proceeding with\
  \ any jj operations, you MUST verify that jj is installed:**\n\n```bash\n# Check\
  \ if jj is installed\njj --version\n```\n\n### If jj is NOT installed:\n\n**Installation\
  \ Instructions for macOS (Homebrew):**\n```bash\n# Install jj using Homebrew\nbrew\
  \ install jj\n\n# Verify installation\njj --version\n```\n\n**Alternative Installation\
  \ Methods:**\n\n**Using Cargo (Rust package manager):**\n```bash\n# Install from\
  \ crates.io\ncargo install --locked jj-cli\n\n# Add to PATH if needed\nexport PATH=\"\
  $HOME/.cargo/bin:$PATH\"\n\n# Verify\njj --version\n```\n\n**From source:**\n```bash\n\
  # Clone repository\ngit clone https://github.com/martinvonz/jj.git\ncd jj\n\n# Build\
  \ and install\ncargo install --path cli\n\n# Verify\njj --version\n```\n\n**For\
  \ other platforms**, see: https://github.com/martinvonz/jj#installation\n\n### Common\
  \ Installation Issues\n\n**Issue: \"command not found: jj\"**\n- Solution: Install\
  \ jj using one of the methods above\n- Verify PATH includes Homebrew binaries: `echo\
  \ $PATH | grep homebrew`\n\n**Issue: \"jj: command not found\" after installation**\n\
  - Solution: Restart your terminal or run `source ~/.zshrc` (or `~/.bashrc`)\n- Check\
  \ installation location: `which jj`\n\n**Issue: Permission errors during installation**\n\
  - Solution: Use `sudo` with Homebrew or ensure Cargo directory is writable\n- Homebrew:\
  \ `sudo chown -R $(whoami) /opt/homebrew`\n\n### First-Time jj Setup\n\n**After\
  \ installing jj for the first time, configure your identity:**\n```bash\n# Set your\
  \ name and email\njj config set --user user.name \"Your Name\"\njj config set --user\
  \ user.email \"your.email@example.com\"\n\n# Verify configuration\njj config list\
  \ --user\n```\n\n### Repository Check\n\n**Verify this is a jj repository:**\n```bash\n\
  # Check repository status\njj status\n```\n\n**If you get \"not a jj repository\"\
  \ error:**\n```bash\n# Option 1: Initialize jj in existing git repo\njj git init\
  \ --colocate\n\n# Option 2: Clone with jj\njj git clone <repository-url>\n```\n\n\
  ### GitHub CLI Check\n\n**Stacked PRs require GitHub CLI (gh) for creating multiple\
  \ PRs:**\n```bash\n# Check if gh is installed\ngh --version\n```\n\n**If gh is not\
  \ installed:**\n```bash\n# macOS with Homebrew\nbrew install gh\n\n# Authenticate\
  \ with GitHub\ngh auth login\n\n# Verify\ngh auth status\n```\n\n**For more information:**\n\
  - jj Documentation: https://martinvonz.github.io/jj/\n- jj GitHub: https://github.com/martinvonz/jj\n\
  - jj Tutorial: https://martinvonz.github.io/jj/latest/tutorial/\n- gh Documentation:\
  \ https://cli.github.com/\n\n---\n\n## Action Requested\n\n**ONLY proceed after\
  \ verifying jj and gh are installed and configured.**\n\n{{args}}\n\n## Workflow\n\
  \nInvoke the **jj-stacked-pr** agent using the Task tool to handle this request.\
  \ The agent has deep expertise in:\n- Jujutsu CLI operations (split, squash, rebase,\
  \ etc.)\n- Stacked diff best practices\n- Revsets for commit queries\n- GitHub PR\
  \ chain management\n- Granular commit crafting\n\n## Expected Process\n\nThe jj-stacked-pr\
  \ agent will:\n\n1. **Verify prerequisites** - Check jj and gh installation\n2.\
  \ **Analyze** the current state using `jj log` and `jj status`\n3. **Plan** the\
  \ commit stack structure and logical boundaries\n4. **Execute** commit operations\
  \ using jj commands\n5. **Create** GitHub PRs with proper base branch targeting\n\
  6. **Document** the stack with clear PR descriptions\n\n## Common Use Cases\n\n\
  ### **Split large changes**\n\"Split my current changes into reviewable commits\"\
  \n- Agent analyzes working directory\n- Identifies logical boundaries\n- Uses `jj\
  \ split` to create granular commits\n- Ensures each commit is independently reviewable\n\
  \n### **Create stack**\n\"Create a stack of PRs for this feature\"\n- Agent examines\
  \ commit history\n- Creates GitHub branches for each commit\n- Opens PRs with proper\
  \ base branch targeting\n- Links PRs together in descriptions\n\n### **Rebase stack**\n\
  \"Rebase my stack on latest main\"\n- Agent fetches latest main/trunk\n- Uses `jj\
  \ rebase` to update stack\n- Handles conflicts if they occur\n- Force-pushes updated\
  \ branches\n\n### **Fix commit**\n\"Edit commit X in the middle of my stack\"\n\
  - Agent uses `jj edit` to modify specific commit\n- Automatically rebases descendants\n\
  - Updates affected GitHub PRs\n- Preserves stack integrity\n\n### **Insert commit**\n\
  \"Add a new commit between X and Y\"\n- Agent creates new commit at desired location\n\
  - Rebases dependent commits\n- Creates new PR in the stack\n- Updates PR descriptions\
  \ to reflect new order\n\n## Key jj Commands for Stacked Workflows\n\n### **Commit\
  \ Operations**\n```bash\njj split              # Interactively split changes into\
  \ commits\njj squash             # Squash current changes into parent\njj describe\
  \ -m \"msg\"  # Set commit message\njj new                # Create new commit\n\
  jj edit <change-id>   # Edit specific commit in stack\n```\n\n### **Stack Navigation**\n\
  ```bash\njj log                # View commit graph\njj log -r 'trunk..@'  # View\
  \ commits from trunk to current\njj prev               # Move to parent commit\n\
  jj next               # Move to child commit\n```\n\n### **Stack Rebasing**\n```bash\n\
  jj rebase -d trunk                        # Rebase current on trunk\njj rebase -s\
  \ 'all:roots(trunk..@)' -d trunk  # Rebase entire stack\njj rebase -s <change-id>\
  \ -d <dest>       # Rebase specific commit\n```\n\n### **Branch Management**\n```bash\n\
  jj branch create feature-part-1          # Create branch at current commit\njj branch\
  \ set feature-part-1             # Move branch to current commit\njj git push --branch\
  \ feature-part-1      # Push branch to remote\n```\n\n## GitHub PR Stack Management\n\
  \n### **Creating Stacked PRs**\n```bash\n# For each commit in the stack:\njj edit\
  \ <change-id>\njj branch create feature-part-N\njj git push --branch feature-part-N\n\
  \n# Then use gh to create PR\ngh pr create --base <parent-branch> --head feature-part-N\
  \ \\\n  --title \"Part N: Description\" \\\n  --body \"Stack: Builds on #PARENT_PR\"\
  \n```\n\n### **PR Stack Description Template**\n```markdown\n## Stack Position\n\
  - **Builds on**: #123 (previous PR in stack)\n- **Depended on by**: #125 (next PR\
  \ in stack)\n\n## What This PR Does\nBrief description of this specific commit's\
  \ changes.\n\n## Review Notes\n- Review this independently from the rest of the\
  \ stack\n- Changes are self-contained within this commit\n- Safe to merge once parent\
  \ PR is merged\n```\n\n## Error Handling\n\n**If you encounter \"command not found:\
  \ jj\":**\n1. Stop immediately\n2. Provide installation instructions (see Prerequisites\
  \ section above)\n3. Wait for user to install jj\n4. Verify installation with `jj\
  \ --version`\n5. Only then proceed with stack operations\n\n**If you encounter \"\
  command not found: gh\":**\n1. Stop immediately\n2. Provide gh installation instructions\n\
  3. Ensure user authenticates with `gh auth login`\n4. Verify with `gh auth status`\n\
  5. Only then proceed with PR creation\n\n**If you encounter \"not a jj repository\"\
  :**\n1. Check if this is a git repository\n2. If yes: Run `jj git init --colocate`\
  \ to initialize jj\n3. If no: User needs to initialize repository first\n\n**If\
  \ stack rebasing causes conflicts:**\n1. Don't panic - conflicts are expected\n\
  2. Show conflicted files with `jj status`\n3. Guide user through conflict resolution\n\
  4. Continue with `jj commit` after resolution\n5. If needed: `jj undo` to abort\
  \ rebase\n\n**If PR creation fails:**\n1. Verify gh authentication: `gh auth status`\n\
  2. Check branch exists remotely: `jj git push --branch <name>`\n3. Verify base branch\
  \ exists and is up to date\n4. Check GitHub permissions for repository\n\n## Best\
  \ Practices for Stacked PRs\n\n### **Commit Granularity**\n✅ Each commit should:\n\
  - Represent one logical change\n- Be independently reviewable (< 15 min review time)\n\
  - Have a clear, descriptive message\n- Build successfully and pass tests\n\n❌ Avoid:\n\
  - Mixing unrelated changes\n- Creating dependencies between unrelated commits\n\
  - Making commits too small (single line changes)\n- Making commits too large (>\
  \ 500 lines)\n\n### **Stack Ordering**\n✅ Proper order:\n1. Infrastructure/schema\
  \ changes\n2. Core functionality\n3. API/interface changes\n4. UI/frontend changes\n\
  5. Tests\n6. Documentation\n\n❌ Wrong order:\n- Using new APIs before they're defined\n\
  - Referencing database tables before migrations\n- Tests before implementation exists\n\
  \n### **PR Descriptions**\n✅ Good descriptions:\n- Clear stack position (part N\
  \ of M)\n- Links to parent and child PRs\n- Explains what THIS commit does\n- Notes\
  \ any review considerations\n\n❌ Poor descriptions:\n- \"Part 2\" (no context)\n\
  - Missing stack links\n- Describing entire feature instead of this commit\n- No\
  \ guidance for reviewers\n\n## Stacked PR Review Workflow\n\nFor reviewers:\n1.\
  \ Start with the bottom PR (closest to trunk)\n2. Review each PR independently\n\
  3. Approve and merge bottom PR first\n4. GitHub will automatically update base branches\n\
  5. Continue up the stack\n\nFor authors:\n1. Address review feedback on affected\
  \ commits\n2. Use `jj edit` to modify specific commits\n3. Force push updated branches\n\
  4. PRs update automatically\n5. Notify reviewers of updates\n\n## Advanced: Revsets\
  \ for Stacks\n\n**Useful revset queries:**\n```bash\n# All commits in current stack\n\
  jj log -r 'trunk..@'\n\n# Root commits of the stack\njj log -r 'all:roots(trunk..@)'\n\
  \n# Descendants of a specific commit\njj log -r 'descendants(<change-id>)'\n\n#\
  \ Commits that changed specific files\njj log -r 'file(path/to/file.java)'\n\n#\
  \ Commits in last N days\njj log -r 'trunk..@ & committer-date(after:\"7 days ago\"\
  )'\n```\n\n## Example Complete Stacked PR Workflow\n\n```bash\n# 1. Verify prerequisites\n\
  jj --version && gh --version\n\n# 2. Start from trunk\njj new trunk\n\n# 3. Make\
  \ changes and split into commits\n# ... make changes ...\njj split  # Create first\
  \ logical commit\njj describe -m \"feat(db): add user_preferences table\"\n\njj\
  \ new  # Start next commit\n# ... make more changes ...\njj split  # Create second\
  \ logical commit\njj describe -m \"feat(api): add preferences endpoints\"\n\n# 4.\
  \ Create branches and push\njj edit <commit-1-change-id>\njj branch create feature-db-schema\n\
  jj git push --branch feature-db-schema\n\njj edit <commit-2-change-id>\njj branch\
  \ create feature-api-endpoints\njj git push --branch feature-api-endpoints\n\n#\
  \ 5. Create PRs\ngh pr create --base trunk --head feature-db-schema \\\n  --title\
  \ \"Part 1: Add user preferences table\"\n\ngh pr create --base feature-db-schema\
  \ --head feature-api-endpoints \\\n  --title \"Part 2: Add preferences API endpoints\"\
  \n\n# 6. View the stack\njj log -r 'trunk..@'\n```\n\n## Troubleshooting Stack Issues\n\
  \n**Problem: Lost track of stack structure**\n```bash\n# Visualize the entire stack\n\
  jj log -r 'trunk..@'\n\n# See operation history\njj op log\n```\n\n**Problem: Need\
  \ to insert commit in middle**\n```bash\n# Navigate to parent of insertion point\n\
  jj edit <parent-change-id>\n\n# Create new commit\njj new\n# ... make changes ...\n\
  jj commit -m \"new commit\"\n\n# Rebase old children onto new commit\njj rebase\
  \ -s <old-child-change-id> -d @\n```\n\n**Problem: Need to remove commit from stack**\n\
  ```bash\n# Option 1: Squash into parent\njj squash -r <change-id>\n\n# Option 2:\
  \ Abandon commit\njj abandon <change-id>\n# Children automatically rebase onto parent\n\
  ```\n\n**Problem: Stack got out of sync with remote**\n```bash\n# Fetch latest\n\
  jj git fetch\n\n# Rebase entire stack\njj rebase -s 'all:roots(trunk..@)' -d trunk\n\
  \n# Force push all branches\njj git push --all --force\n```\n\n## Workflow Summary\n\
  \nInvoke the **jj-stacked-pr** agent to handle any stacked PR workflow. The agent\
  \ will:\n\n1. ✅ Verify all prerequisites (jj, gh, repository state)\n2. ✅ Analyze\
  \ current state and plan approach\n3. ✅ Execute jj commands safely with error handling\n\
  4. ✅ Create and manage GitHub PRs correctly\n5. ✅ Provide clear guidance and documentation\n\
  6. ✅ Handle errors gracefully with actionable solutions\n\nThe agent ensures your\
  \ stacked PR workflow is smooth, safe, and follows best practices.\n\nProceed by\
  \ invoking the jj-stacked-pr agent with the Task tool.\n"
---

# Jujutsu Stacked PR Workflow

> **IMPORTANT**: This skill is for **Jujutsu (jj)** workflows only. If the user asked for a commit, branch, or PR without mentioning `jj`, stop and use the `git:commit` or `git:create-pr` skill instead.

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
