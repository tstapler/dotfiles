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
- Code *searching* → use `ast-grep` instead

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

For large codebases, use `ast-grep` to understand scope before applying gritql:

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