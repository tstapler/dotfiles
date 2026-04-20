---
name: code-refactoring
description: Orchestrate large structural code refactors combining semantic search
  (ast-grep) with AST-based transformation (gritql). Use for multi-file renames, API
  migrations, and pattern modernization with mandatory quality gates.
---

# Code Refactoring

Orchestrate large structural refactors using `code-ast-grep` to discover scope and `code-gritql` to apply transformations safely.

## When to Use

**Use this skill for:**
- Multi-file refactoring (rename classes, methods, variables)
- API migrations (framework updates, library changes)
- Pattern refactoring (inheritance → composition)
- Code modernization (language idioms, best practices)

**Don't use for:**
- Single-file simple changes → Use `Edit` tool directly
- Logic changes requiring context → Manual review
- Non-code files (YAML, JSON, MD) → Use `Edit` tool

## Workflow

### 1. Pre-Flight Checks

```bash
git status          # Must be clean
git checkout -b refactor/<description>
```

Run baseline build + tests before starting.

### 2. Discover Scope with ast-grep

Before transforming anything, understand the full impact:

```bash
# Find all sites that will be affected
sg --pattern '$obj.oldMethod($$$)' --lang java src/

# Verify count and locations are expected
```

See `code-ast-grep` skill for full pattern syntax.

### 3. Preview with gritql (MANDATORY)

```bash
grit apply '<pattern>' --dry-run > /tmp/preview.diff
# Review ALL changes before applying
```

See `code-gritql` skill for transformation pattern syntax.

### 4. Apply and Verify (MANDATORY)

```bash
grit apply '<pattern>'

# Format
./gradlew spotlessApply  # or equivalent formatter

# Compile
./gradlew compileJava compileKotlin

# Full test suite
./gradlew test testIntegration

# Review diff
git diff HEAD
```

### 5. Commit

```bash
git add -u
git commit -m "refactor: <clear description>"
```

## Quality Gates

Before completing any refactor:
- [ ] ast-grep scope review done before applying
- [ ] Dry-run previewed and all changes intentional
- [ ] Code formatted
- [ ] Clean build (no compilation errors)
- [ ] Tests passing
- [ ] Git diff reviewed

## Tool Selection

| Scenario | Tool |
|----------|------|
| Find all affected code sites | `code-ast-grep` (`sg`) |
| Multi-file structural transformation | `code-gritql` |
| Single file, simple change | `Edit` |
| Same text change across files | `MultiEdit` |

## Progressive Context

- For transformation patterns (rename, import, annotation migration): see `code-gritql` skill and `reference.md`
- For search patterns (finding callers, usages, class definitions): see `code-ast-grep` skill