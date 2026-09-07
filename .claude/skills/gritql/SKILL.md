---
name: gritql
description: Use gritql (grit) for AST-based multi-file code transformations. Use
  when renaming methods/classes, migrating APIs, or modernizing patterns across a
  codebase. Always preview before applying. Pairs with ast-grep for search-then-transform
  workflows.
---

# gritql: AST-Based Code Transformation

Use `grit` for structural code rewrites. Unlike text-based find/replace, gritql understands code syntax and rewrites safely across all occurrences.

## When to Use

**Use gritql for:**
- Renaming methods, classes, variables across many files
- API migrations (library version upgrades)
- Pattern modernization (legacy → idiomatic code)
- Any change where "find all + replace" needs syntax awareness

**Don't use for:**
- Single-file edits → use `Edit` tool
- Non-code files (YAML, JSON, MD) → use `Edit` tool
- Simple text substitution → use `MultiEdit`
- Code *searching* → use `code-ast-grep` instead

## ⚠️ Kotlin Limitations (v0.1.1)

GritQL's Kotlin support is expression-level only. Know what works before attempting a transform.

### What works ✅
- Function call rewrites: `` `logger.error($msg)` => `logger.warn($msg)` ``
- Method chains: `` `$obj.old($$$args)` => `$obj.new($$$args)` ``
- Import replacements: `` `import old.Pkg` => `import new.Pkg` ``

### What fails ❌
- **`catch` blocks** — `catch (e: Exception) { $body }` → `code 200: Could not find variable` or 0 matches. Kotlin catch clauses are `catch_block` statement nodes in the tree-sitter grammar; GritQL backtick patterns only reach expression nodes.
- **Any statement-level pattern** — `if`, `for`, variable declarations, `try` blocks, `return` statements all fail similarly.
- **`where` clause with `contains`/`not contains`** — parses without error in v0.1.1 but consistently returns 0 matches. Use this as a confirmation guard only after verifying the base pattern matches first.

### No Kotlin stdlib patterns
The GritQL stdlib has patterns for Go, Java, JS, Python, Rust — but **no Kotlin**. Don't search `grit list` expecting Kotlin helpers.

### For Kotlin statement-level transforms
Use `ast-grep` with a YAML rule file, or use the `Edit` tool for targeted single-location changes:

```bash
# ast-grep can match catch blocks:
sg --pattern 'catch ($e: $T) { $$$body }' --lang kotlin kmp/src/

# YAML rule for structural rewrite (sg --rewrite)
```

## ⚠️ stdlib Init Fails (SSH auth error)

`grit init` uses libgit2 to clone `getgrit/stdlib` from GitHub. It ignores git `insteadOf` config and attempts SSH, which fails without an agent:

```
Error: Failed to fetch grit module getgrit/stdlib:
  authentication required but no callback set; class=Ssh (23)
```

### Workaround: symlink the bundled stdlib

The stdlib is bundled inside the npm package. Locate it and symlink it into your project's `.grit/` directory:

```bash
# Find the bundled stdlib (works on macOS + Linux)
GRIT_STDLIB=$(npm root -g)/@getgrit/cli/node_modules/.grit/.gritmodules

mkdir -p .grit
ln -sf "$GRIT_STDLIB" .grit/.gritmodules
```

Run from the project root. This makes `where` clause predicates and named patterns available without SSH.

## ⚠️ Critical: Go Package Prefix Migrations

When adding package prefixes to Go types (e.g., `FooType` → `pkg.FooType`), two things WILL go wrong without guards:

**1. Double-prefix** — GritQL visits sub-nodes of already-rewritten code. Fix with `not within`:

```grit
language go

// WRONG: causes detection.detection.FooType
`FooType` => `detection.FooType`

// CORRECT: use specific not within guard
`FooType` => `detection.FooType` where {
  $_ <: not within `detection.$_`
}
```

**2. Struct field types missed** — Go uses `type_identifier` AST node in struct fields; GritQL backtick patterns compile as `identifier` (different node type) and don't match. Use `gofmt -r` to cover these:

```bash
gofmt -r 'FooType -> detection.FooType' -w ./...
```

Then run `go build ./...` to catch any remaining occurrences.

## Installation

```bash
brew install gritql
```

Verify: `grit --version`

## Mandatory Workflow

### 1. Always Preview First

```bash
grit apply '<pattern>' --dry-run > /tmp/preview.diff
# Review before applying
```

### 2. Apply

```bash
grit apply '<pattern>'
```

### 3. Verify

```bash
# Run build + tests to confirm nothing broke
```

## Pattern Syntax

### Basic Rewrite

```
`old_expression($$$args)` => `new_expression($$$args)`
```

- `` `...` `` — backtick-quoted code pattern
- `$NAME` — matches one AST node
- `$$$NAME` — matches zero or more nodes (variadic/spread)

### Examples

**Rename a method call:**
```bash
grit apply '`$obj.oldMethod($$$args)` => `$obj.newMethod($$$args)`' --dry-run
```

**Update an import:**
```bash
grit apply '`import OldClass from "old-lib"` => `import NewClass from "new-lib"`' --dry-run
```

**Add a parameter to all calls:**
```bash
grit apply '`myFunc($$$args)` => `myFunc($$$args, { version: 2 })`' --dry-run
```

**Rename a class:**
```bash
grit apply '`class OldName` => `class NewName`' --dry-run
```

## Quick Reference

| Task | Pattern |
|------|---------|
| Rename method | `` `$o.old($$$a)` => `$o.new($$$a)` `` |
| Rename class | `` `class Old` => `class New` `` |
| Update import | `` `import old.Cls` => `import new.Cls` `` |
| Wrap expression | `` `unwrapped($$$a)` => `wrapped(unwrapped($$$a))` `` |

## Quality Gates

Before completing any gritql transformation:
- [ ] Dry-run reviewed and all changes are intentional
- [ ] Code formatted after apply
- [ ] Build passes (no compilation errors)
- [ ] Tests passing
- [ ] Git diff reviewed

## Search First, Then Transform

For large codebases, use `code-ast-grep` to understand scope before applying gritql:

```bash
# 1. Find all affected sites
sg --pattern '$obj.oldMethod($$$)' --lang java src/

# 2. Review count and locations
# 3. Apply gritql transform
grit apply '`$obj.oldMethod($$$args)` => `$obj.newMethod($$$args)`' --dry-run
```

## Go Gotchas Quick Reference

| Issue | Cause | Fix |
|-------|-------|-----|
| `detection.detection.FooType` | Pattern matches `FooType` inside already-prefixed `detection.FooType` | Add `where { $_ <: not within \`$_.$_\` }` |
| Struct field types not rewritten | Go uses `type_identifier` node for type positions; may not match backtick pattern | After GritQL, run `go build ./...` and fix with `Edit` |
| Missing `qualified_type` in type context | `pkg.Type` in type vs expression position uses different AST nodes | Use `not within` guards; supplement with manual edits |

## Advanced Patterns Reference

For annotation migration, API migration across versions, multi-step transformations, and Go-specific workarounds, see `reference.md`.