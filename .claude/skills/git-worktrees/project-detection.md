# Project Detection Reference

This file provides detailed patterns for detecting project types and running appropriate setup commands.

## Detection Priority Order

Check files in this order (first match wins):

1. CLAUDE.md `setup_command:` directive (highest priority - always respect user override)
2. package.json (Node.js ecosystem)
3. Cargo.toml (Rust)
4. pyproject.toml (Python modern)
5. requirements.txt (Python legacy)
6. go.mod (Go)
7. Makefile (Universal build system)
8. composer.json (PHP)
9. build.gradle / build.gradle.kts (Java/Kotlin - Gradle)
10. pom.xml (Java/Kotlin - Maven)

## Package Manager Detection Patterns

### Node.js (package.json)

**Detection**:
```bash
[ -f package.json ]
```

**Package Manager Selection**:
```bash
# Check for lock files to determine package manager
if [ -f pnpm-lock.yaml ]; then
  pnpm install
elif [ -f yarn.lock ]; then
  yarn install
else
  npm install
fi
```

**Test Command**:
```bash
npm test
```

### Rust (Cargo.toml)

**Detection**:
```bash
[ -f Cargo.toml ]
```

**Setup**:
```bash
cargo build
```

**Test Command**:
```bash
cargo test
```

### Python Modern (pyproject.toml)

**Detection**:
```bash
[ -f pyproject.toml ]
```

**Package Manager Selection**:
```bash
# Check for tool preference in pyproject.toml
if grep -q "tool.poetry" pyproject.toml; then
  poetry install
elif grep -q "tool.uv" pyproject.toml || [ -f uv.lock ]; then
  uv install
elif grep -q "tool.pdm" pyproject.toml; then
  pdm install
else
  # Fallback to pip with editable install
  pip install -e .
fi
```

**Test Command**:
```bash
pytest || poetry run pytest || uv run pytest
```

### Python Legacy (requirements.txt)

**Detection**:
```bash
[ -f requirements.txt ] && [ ! -f pyproject.toml ]
```

**Setup**:
```bash
pip install -r requirements.txt

# Check for dev requirements
if [ -f requirements-dev.txt ]; then
  pip install -r requirements-dev.txt
fi
```

**Test Command**:
```bash
pytest || python -m pytest
```

### Go (go.mod)

**Detection**:
```bash
[ -f go.mod ]
```

**Setup**:
```bash
go mod download
```

**Test Command**:
```bash
go test ./...
```

### Makefile (Universal)

**Detection**:
```bash
[ -f Makefile ]
```

**Setup**:
```bash
# Look for common setup targets (check in order)
if grep -q "^setup:" Makefile; then
  make setup
elif grep -q "^install:" Makefile; then
  make install
elif grep -q "^deps:" Makefile; then
  make deps
elif grep -q "^bootstrap:" Makefile; then
  make bootstrap
else
  # No setup target found
  echo "Makefile found but no setup target detected"
fi
```

**Test Command**:
```bash
if grep -q "^test:" Makefile; then
  make test
elif grep -q "^check:" Makefile; then
  make check
fi
```

### PHP (composer.json)

**Detection**:
```bash
[ -f composer.json ]
```

**Setup**:
```bash
composer install
```

**Test Command**:
```bash
composer test || ./vendor/bin/phpunit
```

### Java/Kotlin - Gradle

**Detection**:
```bash
[ -f build.gradle ] || [ -f build.gradle.kts ]
```

**Setup**:
```bash
./gradlew build
```

**Test Command**:
```bash
./gradlew test
```

### Java/Kotlin - Maven

**Detection**:
```bash
[ -f pom.xml ]
```

**Setup**:
```bash
mvn install -DskipTests
```

**Test Command**:
```bash
mvn test
```

## Multi-Language Projects

For projects with multiple languages (e.g., full-stack apps), run setup for each detected ecosystem:

```bash
# Frontend (Node.js)
if [ -f package.json ]; then
  npm install
fi

# Backend (Python)
if [ -f pyproject.toml ]; then
  poetry install
fi

# Rust tooling
if [ -f Cargo.toml ]; then
  cargo build
fi
```

## Custom Setup Commands via CLAUDE.md

Projects can override auto-detection by adding to `CLAUDE.md`:

```markdown
## Worktree Configuration

setup_command: |
  npm install
  cd backend && poetry install
  make proto

test_command: |
  npm test
  cd backend && pytest
```

**Important**: Always respect `setup_command` directive if present - it takes precedence over all auto-detection.

## Fallback Behavior

If no project type is detected:
1. Check for custom `setup_command` in CLAUDE.md
2. If none found, report: "No project setup detected. Proceeding without setup."
3. Continue with worktree creation (setup is optional)

## Performance Considerations

- **Parallel setup**: For multi-language projects, consider running setup commands in parallel
- **Skip tests for slow projects**: If tests take >5 minutes, ask user before running
- **Cache dependencies**: Some package managers support cache directories (npm, cargo) - ensure they work with worktrees

## Examples

### Example 1: Monorepo with Multiple Ecosystems
```bash
# Detected: package.json + pyproject.toml
# Action: Run both setups

npm install && cd backend && poetry install
```

### Example 2: Custom Setup via CLAUDE.md
```markdown
## Worktree Configuration
setup_command: docker-compose up -d && make migrate && npm install
```
```bash
# Action: Run custom command instead of auto-detection
docker-compose up -d && make migrate && npm install
```

### Example 3: No Setup Required
```bash
# Detected: No package.json, Cargo.toml, etc.
# Action: Report and skip setup

echo "No project setup detected. Proceeding without setup."
```
