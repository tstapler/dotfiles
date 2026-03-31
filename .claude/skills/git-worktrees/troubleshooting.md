# Troubleshooting Guide

Common issues when creating and managing git worktrees, with solutions.

## Worktree Creation Errors

### Error: `fatal: invalid reference: <branch-name>`

**Cause**: Branch name conflicts with existing branch, tag, or remote reference.

**Solution**:
1. List existing branches: `git branch -a`
2. Choose a different, unique branch name
3. Retry with new name

**Prevention**: Use descriptive prefixes like `feature/`, `fix/`, `refactor/`

---

### Error: `fatal: '<path>' already exists`

**Cause**: Target directory already exists (from previous worktree or other files).

**Solution**:
```bash
# Check if it's a worktree
git worktree list

# If it's a stale worktree
git worktree remove <path> --force

# If it's a regular directory
rm -rf <path>

# Then retry creation
git worktree add <path> -b <branch-name>
```

**Prevention**: Always clean up worktrees when done: `git worktree remove <path>`

---

### Error: `fatal: '<path>' is already checked out at '<other-path>'`

**Cause**: Attempting to check out a branch that's already checked out in another worktree.

**Solution**:
1. List all worktrees: `git worktree list`
2. Either:
   - Use the existing worktree at `<other-path>`
   - Create a new branch instead: `git worktree add <path> -b <new-branch-name>`
   - Remove the other worktree if no longer needed

**Prevention**: Use unique branch names per worktree

---

### Error: `fatal: not a valid object name: <base-branch>`

**Cause**: Base branch doesn't exist locally or remotely.

**Solution**:
```bash
# Fetch latest from remote
git fetch origin

# Retry with explicit remote branch
git worktree add <path> -b <branch-name> origin/main
```

**Prevention**: Run `git fetch` before creating worktrees

---

## Project Setup Errors

### Error: `npm: command not found`

**Cause**: Node.js/npm not installed or not in PATH.

**Solution**:
1. Install Node.js:
   - macOS: `brew install node`
   - Linux: Use system package manager or [nvm](https://github.com/nvm-sh/nvm)
   - Windows: Download from [nodejs.org](https://nodejs.org)
2. Verify installation: `npm --version`
3. Retry setup

**Workaround**: Skip setup if you don't need to run the project in this worktree

---

### Error: `cargo: command not found`

**Cause**: Rust toolchain not installed.

**Solution**:
1. Install Rust: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
2. Reload shell: `source $HOME/.cargo/env`
3. Verify: `cargo --version`
4. Retry setup

---

### Error: `poetry: command not found`

**Cause**: Poetry not installed.

**Solution**:
1. Install Poetry: `curl -sSL https://install.python-poetry.org | python3 -`
2. Add to PATH (if needed): `export PATH="$HOME/.local/bin:$PATH"`
3. Verify: `poetry --version`
4. Retry setup

**Alternative**: Use `uv` instead: `pip install uv && uv install`

---

### Error: `npm ERR! code ENOENT`

**Cause**: npm trying to access files/directories that don't exist, often during postinstall scripts.

**Solution**:
```bash
# Clean npm cache
npm cache clean --force

# Remove node_modules and lockfile
rm -rf node_modules package-lock.json

# Retry install
npm install
```

**Workaround**: Use `npm install --legacy-peer-deps` if peer dependency conflicts

---

### Error: `cargo build` fails with linker errors

**Cause**: Missing system libraries or compiler toolchain.

**Solution**:
- macOS: `xcode-select --install`
- Linux: `sudo apt-get install build-essential` (Ubuntu/Debian)
- Verify: `gcc --version`

---

## Test Baseline Errors

### Error: Tests failing in clean worktree

**Cause**: Pre-existing test failures in the codebase.

**Solution**:
1. Report failures to user
2. Ask: "Tests are failing in the base branch. Continue anyway?"
3. If yes: Proceed with worktree (note in report that baseline has failures)
4. If no: Investigate and fix failing tests in main branch first

**Prevention**: Keep main branch tests passing at all times

---

### Error: `pytest: command not found`

**Cause**: pytest not installed in environment.

**Solution**:
```bash
# Install pytest
pip install pytest

# Or if using poetry
poetry add --group dev pytest

# Or if using uv
uv pip install pytest

# Retry tests
pytest
```

---

### Error: Tests timeout after 5 minutes

**Cause**: Test suite is very slow or has hanging tests.

**Solution**:
1. Report timeout to user
2. Ask: "Tests timed out. Skip test baseline validation?"
3. If yes: Proceed without test validation
4. If no: Investigate slow/hanging tests

**Prevention**: Add `test_command` to CLAUDE.md with faster subset: `make test-fast`

---

## Permission Errors

### Error: `Permission denied` creating worktree directory

**Cause**: Insufficient permissions for target directory.

**Solution**:
```bash
# Check permissions
ls -ld $(dirname <worktree-path>)

# Fix permissions
sudo chown -R $USER:$USER $(dirname <worktree-path>)

# Or choose different location
# Use ~/.claude/worktrees/<project>/ instead
```

---

### Error: `Permission denied` during `npm install`

**Cause**: npm trying to write to system directories.

**Solution**:
```bash
# Fix npm permissions (don't use sudo with npm!)
npm config set prefix ~/.npm-global
export PATH=~/.npm-global/bin:$PATH

# Add to shell profile
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc

# Retry install
npm install
```

---

## Git Configuration Issues

### Error: `.worktrees/` directory being tracked by git

**Cause**: Directory not in .gitignore.

**Solution** (automatic):
```bash
# Add to .gitignore
echo ".worktrees/" >> .gitignore

# Commit change
git add .gitignore
git commit -m "chore: ignore worktree directory"
```

**Verification**:
```bash
# Verify directory is ignored
git check-ignore -v .worktrees
# Should output: .gitignore:N:.worktrees/	.worktrees
```

---

### Error: Worktree has uncommitted changes from main repo

**Cause**: Worktree was created while main repo had uncommitted changes, and they were copied.

**Solution**:
```bash
# Check status
git status

# Decide what to do:
# Option 1: Commit changes if they belong to this feature
git add . && git commit -m "..."

# Option 2: Stash changes if they don't belong
git stash

# Option 3: Remove changes
git reset --hard HEAD
```

**Prevention**: Ensure main repo is clean before creating worktrees

---

## Cleanup Issues

### Error: `fatal: '<path>' is not a working tree` when removing

**Cause**: Worktree directory was manually deleted without using `git worktree remove`.

**Solution**:
```bash
# Prune stale worktree entries
git worktree prune

# Verify it's gone
git worktree list
```

---

### Error: Cannot remove worktree with uncommitted changes

**Cause**: Git prevents removing worktrees with uncommitted changes by default.

**Solution**:
```bash
# Option 1: Commit or stash changes first
cd <worktree-path>
git add . && git commit -m "..."

# Option 2: Force removal (loses changes!)
git worktree remove <path> --force
```

---

## CLAUDE.md Configuration Issues

### Error: setup_command not being recognized

**Cause**: Incorrect format or indentation in CLAUDE.md.

**Solution**:
Ensure exact format:
```markdown
## Worktree Configuration

setup_command: make dev-setup
```

Not:
```markdown
worktree_setup_command: ...  # Wrong key
setup-command: ...            # Wrong format (use underscore)
  setup_command: ...          # Wrong indentation
```

**Verification**:
```bash
grep -A 2 "Worktree Configuration" CLAUDE.md
```

---

## Advanced Issues

### Issue: Symlinks broken after worktree creation

**Cause**: Symlinks pointing to absolute paths that don't exist in worktree.

**Solution**:
1. Convert absolute symlinks to relative: `ln -sf ../relative/path target`
2. Or re-run setup to regenerate symlinks
3. Document in CLAUDE.md: `setup_command: make setup-links`

---

### Issue: Worktree using different version of dependencies

**Cause**: Shared dependency cache between worktrees causing conflicts.

**Solution**:
```bash
# For Node.js: Use different cache per worktree
npm install --cache .npm-cache

# For Rust: Worktrees share target/ by default (usually OK)
# If needed, use separate target: CARGO_TARGET_DIR=target-worktree cargo build

# For Python with poetry: Each worktree gets its own venv
poetry install  # Creates .venv in worktree
```

---

## Getting Help

If you encounter an error not listed here:

1. **Check git worktree documentation**: `git worktree --help`
2. **Check package manager docs**: npm, cargo, poetry, etc.
3. **Search error message**: Often points to known issues
4. **Report to user**: Provide error details and suggest manual investigation

## Common Patterns

### Pattern: "Command not found" errors
**Solution**: Install missing tool or skip that step

### Pattern: Permission errors
**Solution**: Fix permissions or use different location

### Pattern: "Already exists" errors
**Solution**: Clean up old worktrees/files first

### Pattern: Failing tests
**Solution**: Report to user, get permission to proceed

### Pattern: Network errors during setup
**Solution**: Check internet connection, retry, or use cached dependencies
