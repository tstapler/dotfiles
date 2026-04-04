---
description: Analyze working directory and create granular commits for all features/functionality
  implemented
prompt: "# Jujutsu Granular Commit Creation\n\nYou are being invoked to analyze the\
  \ current working directory and create **as many granular commits as necessary**\
  \ to properly capture all the features/functionality that have been implemented.\n\
  \n## Prerequisites Check\n\n**BEFORE proceeding with any jj operations, you MUST\
  \ verify that jj is installed:**\n\n```bash\n# Check if jj is installed\njj --version\n\
  ```\n\n### If jj is NOT installed:\n\n**Installation Instructions for macOS (Homebrew):**\n\
  ```bash\n# Install jj using Homebrew\nbrew install jj\n\n# Verify installation\n\
  jj --version\n```\n\n**Alternative Installation Methods:**\n\n**Using Cargo (Rust\
  \ package manager):**\n```bash\n# Install from crates.io\ncargo install --locked\
  \ jj-cli\n\n# Add to PATH if needed\nexport PATH=\"$HOME/.cargo/bin:$PATH\"\n\n\
  # Verify\njj --version\n```\n\n**From source:**\n```bash\n# Clone repository\ngit\
  \ clone https://github.com/martinvonz/jj.git\ncd jj\n\n# Build and install\ncargo\
  \ install --path cli\n\n# Verify\njj --version\n```\n\n**For other platforms**,\
  \ see: https://github.com/martinvonz/jj#installation\n\n### Common Installation\
  \ Issues\n\n**Issue: \"command not found: jj\"**\n- Solution: Install jj using one\
  \ of the methods above\n- Verify PATH includes Homebrew binaries: `echo $PATH |\
  \ grep homebrew`\n\n**Issue: \"jj: command not found\" after installation**\n- Solution:\
  \ Restart your terminal or run `source ~/.zshrc` (or `~/.bashrc`)\n- Check installation\
  \ location: `which jj`\n\n**Issue: Permission errors during installation**\n- Solution:\
  \ Use `sudo` with Homebrew or ensure Cargo directory is writable\n- Homebrew: `sudo\
  \ chown -R $(whoami) /opt/homebrew`\n\n### First-Time jj Setup\n\n**After installing\
  \ jj for the first time, configure your identity:**\n```bash\n# Set your name and\
  \ email\njj config set --user user.name \"Your Name\"\njj config set --user user.email\
  \ \"your.email@example.com\"\n\n# Verify configuration\njj config list --user\n\
  ```\n\n### Repository Check\n\n**Verify this is a jj repository:**\n```bash\n# Check\
  \ repository status\njj status\n```\n\n**If you get \"not a jj repository\" error:**\n\
  ```bash\n# Option 1: Initialize jj in existing git repo\njj git init --colocate\n\
  \n# Option 2: Clone with jj\njj git clone <repository-url>\n```\n\n**For more information\
  \ on jj:**\n- Documentation: https://martinvonz.github.io/jj/\n- GitHub: https://github.com/martinvonz/jj\n\
  - Tutorial: https://martinvonz.github.io/jj/latest/tutorial/\n\n---\n\n## Mission\n\
  \n**ONLY proceed after verifying jj is installed and configured.**\n\nDo NOT create\
  \ a single monolithic commit. Instead:\n\n1. **Analyze** all changes in the working\
  \ directory using `jj diff` or `jj status`\n2. **Identify** logical boundaries between\
  \ different features, concerns, or functionality\n3. **Create multiple commits**,\
  \ one for each distinct logical change\n4. **Ensure** each commit is independently\
  \ reviewable and represents ONE thing\n\n## Analysis Criteria\n\nWhen examining\
  \ the working directory, look for these logical boundaries:\n\n### **Architectural\
  \ Layers**\n- Database schema changes (migrations, models)\n- API/Service layer\
  \ changes (business logic)\n- UI/Frontend changes (components, views)\n- Configuration\
  \ changes (settings, env vars)\n- Infrastructure changes (Docker, K8s, CI/CD)\n\n\
  ### **Functional Concerns**\n- New features vs. bug fixes\n- Refactoring vs. new\
  \ functionality\n- Tests vs. implementation\n- Documentation vs. code\n\n### **Dependencies**\n\
  - Changes that must come before others (schema before usage)\n- Changes that are\
  \ independent and can stand alone\n- Changes that form a logical sequence\n\n###\
  \ **File Patterns**\n- Related files that change together\n- Files in the same module/package\n\
  - Files serving the same purpose\n\n## Execution Process\n\nUse the **jj-stacked-pr**\
  \ agent via the Task tool to:\n\n1. **Verify prerequisites** - Check jj installation\n\
  2. **Run** `jj status` and `jj diff` to see all changes\n3. **Analyze** the changes\
  \ to identify distinct features/functionality\n4. **Group** changes into logical\
  \ units\n5. **Create commits** using `jj split` for each logical unit:\n   ```bash\n\
  \   jj split  # Interactively select files/hunks for first logical change\n   jj\
  \ describe -m \"type: clear description of first change\"\n\n   # If more changes\
  \ remain:\n   jj new  # Create next commit\n   jj split  # Select files/hunks for\
  \ second logical change\n   jj describe -m \"type: clear description of second change\"\
  \n\n   # Repeat until all changes are committed\n   ```\n\n6. **Verify** each commit\
  \ is:\n   - **Atomic**: Represents ONE logical change\n   - **Complete**: Includes\
  \ all files needed for that change\n   - **Ordered**: Dependencies come before usage\n\
  \   - **Clear**: Has a descriptive commit message\n\n## Commit Message Format\n\n\
  Use Conventional Commits format:\n\n```\ntype(scope): brief description\n\nLonger\
  \ explanation if needed.\n\n- Bullet point details\n- More context\n```\n\n**Types**:\
  \ `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `style`, `perf`\n\n## Example\
  \ Scenario\n\n**Working Directory Has:**\n- Database migration file\n- New service\
  \ methods\n- API endpoint changes\n- Frontend component updates\n- Test files\n\
  - Documentation updates\n\n**Should Create:**\n1. `feat(db): add user_preferences\
  \ table migration`\n2. `feat(service): implement user preferences service layer`\n\
  3. `feat(api): add /api/preferences endpoints`\n4. `feat(ui): add preferences settings\
  \ component`\n5. `test: add preferences feature tests`\n6. `docs: update API documentation\
  \ for preferences`\n\nEach commit is independently reviewable and represents one\
  \ logical piece of functionality.\n\n## Quality Standards\n\n- ✅ Each commit should\
  \ take < 15 minutes to review\n- ✅ Each commit message clearly explains WHAT and\
  \ WHY\n- ✅ Commits are ordered by dependency (infrastructure first, usage later)\n\
  - ✅ No commit mixes unrelated concerns\n- ✅ Tests are separate from implementation\
  \ (unless tiny change)\n\n## What NOT to Do\n\n❌ Don't create one giant commit with\
  \ everything\n❌ Don't mix refactoring with new features\n❌ Don't combine multiple\
  \ unrelated bug fixes\n❌ Don't put schema changes and usage in same commit\n❌ Don't\
  \ create commits that can't be reviewed independently\n\n## Error Handling\n\n**If\
  \ you encounter \"command not found: jj\":**\n1. Stop immediately\n2. Provide installation\
  \ instructions (see Prerequisites section above)\n3. Wait for user to install jj\n\
  4. Verify installation with `jj --version`\n5. Only then proceed with commit operations\n\
  \n**If you encounter \"not a jj repository\":**\n1. Check if this is a git repository\n\
  2. If yes: Run `jj git init --colocate` to initialize jj\n3. If no: User needs to\
  \ initialize repository first\n\nInvoke the **jj-stacked-pr** agent now to analyze\
  \ the working directory and create the appropriate granular commits.\n"
---

# Jujutsu Granular Commit Creation

You are being invoked to analyze the current working directory and create **as many granular commits as necessary** to properly capture all the features/functionality that have been implemented.

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

## Mission

**ONLY proceed after verifying jj is installed and configured.**

Do NOT create a single monolithic commit. Instead:

1. **Analyze** all changes in the working directory using `jj diff` or `jj status`
2. **Identify** logical boundaries between different features, concerns, or functionality
3. **Create multiple commits**, one for each distinct logical change
4. **Ensure** each commit is independently reviewable and represents ONE thing

## Analysis Criteria

When examining the working directory, look for these logical boundaries:

### **Architectural Layers**
- Database schema changes (migrations, models)
- API/Service layer changes (business logic)
- UI/Frontend changes (components, views)
- Configuration changes (settings, env vars)
- Infrastructure changes (Docker, K8s, CI/CD)

### **Functional Concerns**
- New features vs. bug fixes
- Refactoring vs. new functionality
- Tests vs. implementation
- Documentation vs. code

### **Dependencies**
- Changes that must come before others (schema before usage)
- Changes that are independent and can stand alone
- Changes that form a logical sequence

### **File Patterns**
- Related files that change together
- Files in the same module/package
- Files serving the same purpose

## Execution Process

Use the **jj-stacked-pr** agent via the Task tool to:

1. **Verify prerequisites** - Check jj installation
2. **Run** `jj status` and `jj diff` to see all changes
3. **Analyze** the changes to identify distinct features/functionality
4. **Group** changes into logical units
5. **Create commits** using `jj split` for each logical unit:
   ```bash
   jj split  # Interactively select files/hunks for first logical change
   jj describe -m "type: clear description of first change"

   # If more changes remain:
   jj new  # Create next commit
   jj split  # Select files/hunks for second logical change
   jj describe -m "type: clear description of second change"

   # Repeat until all changes are committed
   ```

6. **Verify** each commit is:
   - **Atomic**: Represents ONE logical change
   - **Complete**: Includes all files needed for that change
   - **Ordered**: Dependencies come before usage
   - **Clear**: Has a descriptive commit message

## Commit Message Format

Use Conventional Commits format:

```
type(scope): brief description

Longer explanation if needed.

- Bullet point details
- More context
```

**Types**: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `style`, `perf`

## Example Scenario

**Working Directory Has:**
- Database migration file
- New service methods
- API endpoint changes
- Frontend component updates
- Test files
- Documentation updates

**Should Create:**
1. `feat(db): add user_preferences table migration`
2. `feat(service): implement user preferences service layer`
3. `feat(api): add /api/preferences endpoints`
4. `feat(ui): add preferences settings component`
5. `test: add preferences feature tests`
6. `docs: update API documentation for preferences`

Each commit is independently reviewable and represents one logical piece of functionality.

## Quality Standards

- ✅ Each commit should take < 15 minutes to review
- ✅ Each commit message clearly explains WHAT and WHY
- ✅ Commits are ordered by dependency (infrastructure first, usage later)
- ✅ No commit mixes unrelated concerns
- ✅ Tests are separate from implementation (unless tiny change)

## What NOT to Do

❌ Don't create one giant commit with everything
❌ Don't mix refactoring with new features
❌ Don't combine multiple unrelated bug fixes
❌ Don't put schema changes and usage in same commit
❌ Don't create commits that can't be reviewed independently

## Error Handling

**If you encounter "command not found: jj":**
1. Stop immediately
2. Provide installation instructions (see Prerequisites section above)
3. Wait for user to install jj
4. Verify installation with `jj --version`
5. Only then proceed with commit operations

**If you encounter "not a jj repository":**
1. Check if this is a git repository
2. If yes: Run `jj git init --colocate` to initialize jj
3. If no: User needs to initialize repository first

Invoke the **jj-stacked-pr** agent now to analyze the working directory and create the appropriate granular commits.
