---
name: code-refactoring
description: Systematic AST-based code refactoring using gritql for safe, validated multi-file transformations with mandatory preview and verification steps
---

# Code Refactoring

Use AST-based tools (gritql) for systematic, safe code transformations. This skill provides a structured workflow for structural changes requiring code semantics understanding.

## When to Use

**Use this skill for:**
- Multi-file refactoring (rename classes, methods, variables)
- API migrations (framework updates, library changes)
- Pattern refactoring (inheritance → composition)
- Code modernization (language idioms, best practices)

**Don't use for:**
- Single-file simple changes → Use Edit tool
- Logic changes requiring context → Manual review
- Non-code files (YAML, JSON, MD) → Use Edit tool

## Core Workflow

### 1. Pre-Flight Checks

```bash
# Clean git state
git status

# Feature branch
git checkout -b refactor/<description>

# Baseline validation
./gradlew clean build && ./gradlew test
```

### 2. Preview (MANDATORY)

```bash
# Always dry-run first
grit apply '<pattern>' --dry-run > /tmp/preview.diff
less /tmp/preview.diff
```

### 3. Apply

```bash
grit apply '<pattern>'
./gradlew spotlessApply
git add -u
```

### 4. Verify (MANDATORY)

```bash
# Compilation
./gradlew compileJava compileKotlin

# Tests
./gradlew test testIntegration

# Review
git diff HEAD
```

### 5. Commit

```bash
git commit -m "refactor: <clear description>"
git push origin refactor/<description>
```

## Quick Reference

### Class Rename
```bash
grit apply 'class OldName' -> 'class NewName' --dry-run
```

### Method Rename
```bash
grit apply '`$obj.oldMethod($$$args)` => `$obj.newMethod($$$args)`' --dry-run
```

### Import Update
```bash
grit apply 'import old.package.Class' -> 'import new.package.Class' --dry-run
```

## Quality Gates

Before completing:
- [ ] Dry-run reviewed and validated
- [ ] Code formatted (spotlessApply)
- [ ] Clean build (no compilation errors)
- [ ] Tests passing (full suite)
- [ ] Git diff reviewed (all changes intentional)
- [ ] Descriptive commit message

## Tool Selection

| Scenario | Tool |
|----------|------|
| Multi-file structural changes | gritql |
| Single file, simple change | Edit |
| Same text change across files | MultiEdit |

## Progressive Context

- For advanced patterns (annotation migration, API migration): see `reference.md`
- For troubleshooting: see `reference.md`
