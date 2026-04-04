---
name: ast-grep
description: Use ast-grep (sg) for semantic, syntax-aware code searching. Prefer over
  Grep for code pattern searches that depend on structure rather than text matching.
  Use when searching for function calls, class definitions, import statements, or
  any pattern where syntax context matters.
---

# ast-grep: Semantic Code Search

Use `ast-grep` (command: `sg`) for structure-aware code searching. Unlike `Grep` (text search), ast-grep understands syntax and finds patterns by their role in the code, not their textual form.

## When to Use ast-grep vs Grep

| Use `ast-grep` | Use `Grep` |
|----------------|------------|
| Find all calls to a function | Find a string in any file |
| Find class definitions | Search logs or text files |
| Find import statements for a module | Find TODO comments |
| Find all uses of a decorator | Search non-code files (YAML, MD) |
| Find arrow functions vs regular functions | Quick text pattern in known file |
| Search within specific code constructs | Simple identifier search |

## Installation

```bash
brew install ast-grep
```

Verify: `ast-grep --version` or `sg --version`

## Core Usage

### Basic Pattern Search

```bash
# Find pattern in current directory
sg --pattern '<pattern>' --lang <language>

# Search specific directory
sg --pattern '<pattern>' --lang <language> <path>

# Show context lines
sg --pattern '<pattern>' --lang <language> -A 2 -B 2
```

### Language Flag Reference

| Language | Flag |
|----------|------|
| Python | `--lang python` |
| JavaScript | `--lang javascript` |
| TypeScript | `--lang typescript` |
| Java | `--lang java` |
| Kotlin | `--lang kotlin` |
| Rust | `--lang rust` |
| Go | `--lang go` |

## Pattern Syntax

### Metavariables

- `$NAME` — matches any single node (expression, identifier, etc.)
- `$$$NAME` — matches zero or more nodes (variadic)
- `$_` — matches any single node (unnamed/throwaway)

### Examples by Language

**Python — find all calls to a function:**
```bash
sg --pattern 'requests.get($$$)' --lang python
sg --pattern 'print($$$)' --lang python .
```

**Python — find class definitions:**
```bash
sg --pattern 'class $NAME($$$):' --lang python
```

**Python — find decorator usage:**
```bash
sg --pattern '@pytest.mark.parametrize($$$)' --lang python
```

**JavaScript/TypeScript — find async functions:**
```bash
sg --pattern 'async function $NAME($$$) { $$$ }' --lang typescript
```

**JavaScript — find all await expressions:**
```bash
sg --pattern 'await $EXPR' --lang javascript
```

**Java — find method calls:**
```bash
sg --pattern '$OBJ.getLogger($$$)' --lang java
sg --pattern 'log.error($$$)' --lang java
```

**Java — find annotation usage:**
```bash
sg --pattern '@SpringBootTest($$$)' --lang java
```

**General — find TODO comments (any language):**
```bash
sg --pattern '// TODO: $$$' --lang javascript
```

## Common Workflows

### Find All Callers of a Function

```bash
# Python
sg --pattern 'my_function($$$)' --lang python src/

# Java
sg --pattern '$_.myMethod($$$)' --lang java src/
```

### Find All Import/Require Statements

```bash
# Python imports
sg --pattern 'import $MODULE' --lang python
sg --pattern 'from $MODULE import $$$' --lang python

# JS/TS imports
sg --pattern 'import { $$$ } from "$MODULE"' --lang typescript
sg --pattern "require('$MODULE')" --lang javascript
```

### Understand Unfamiliar Codebase

```bash
# What functions are defined?
sg --pattern 'def $NAME($$$):' --lang python src/

# What classes exist?
sg --pattern 'class $NAME:' --lang python src/

# What's being logged?
sg --pattern 'logger.$LEVEL($$$)' --lang python src/
```

### Find Error Handling Patterns

```bash
# Python try/except
sg --pattern 'try: $$$ except $EXC: $$$' --lang python

# Java catch blocks
sg --pattern 'catch ($EXC $VAR) { $$$ }' --lang java
```

## Output Modes

```bash
# Default: show matching lines with file/line
sg --pattern '<pat>' --lang python

# JSON output for scripting
sg --pattern '<pat>' --lang python --json

# Count matches per file
sg --pattern '<pat>' --lang python --stats
```

## Integration with Other Skills

- **Before refactoring**: use `ast-grep` to find all affected sites first
- **Pair with `gritql`**: use ast-grep to search, gritql to transform
- **Replace Grep for code**: whenever the search is about code structure, prefer `sg` over `Grep`