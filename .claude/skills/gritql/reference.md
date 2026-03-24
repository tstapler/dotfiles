# GritQL Advanced Reference

## How GritQL Pattern Matching Works

GritQL's backtick snippets (`` `Foo` ``) perform **structural (CST/AST) matching, not string matching**. GritQL:

1. Parses the snippet into a partial syntax tree in an **expression context**
2. Auto-wraps the pattern with `contains` at the file level by default
3. Traverses the entire target file's tree **node-by-node**, including children of already-transformed nodes

This auto-wrapping `contains` behavior is the root cause of several Go-specific issues.

---

## Known Limitations and Workarounds

### Problem 1: Double-Prefix (Idempotency Issue)

**Symptom**: After applying `` `FooType` => `pkg.FooType` ``, some identifiers end up as `pkg.pkg.FooType`.

**Root Cause**: GritQL auto-wraps patterns with `contains` and traverses bottom-up through the entire tree. After rewriting `FooType` → `detection.FooType`, the new `selector_expression` (or `qualified_type`) node has an inner `identifier` child named `FooType`. GritQL's traversal visits that inner child and matches it again.

In Go's tree-sitter grammar:
- `pkg.FooType` in **expression context** → `selector_expression { operand: identifier("pkg"), field: identifier("FooType") }`
- `pkg.FooType` in **type context** → `qualified_type { package: identifier("pkg"), name: type_identifier("FooType") }`

The `FooType` sub-node inside both is still matchable.

**Fix**: Add a `not within` guard with the specific prefix:

```grit
language go

// CORRECT: prevents matching FooType when already inside detection.*
`FooType` => `detection.FooType` where {
  $_ <: not within `detection.$_`
}
```

Or using the more general form to prevent any selector expression:
```grit
`FooType` => `detection.FooType` where {
  $_ <: not within `$_.$_`
}
```

---

### Problem 2: Struct Field Type Declarations Not Matched

**Symptom**: After applying `` `FooType` => `detection.FooType` ``, struct field type annotations are not rewritten:

```go
// This is NOT matched by `FooType` pattern:
type MyStruct struct {
    Status FooType   // ← missed!
    Req    *FooType  // ← pointer form may or may not be matched
}

// These ARE matched:
var x FooType              // var declaration
func f() *FooType {}       // pointer return type
slice := []*FooType{}      // slice literal
```

**Root Cause**: **Different tree-sitter node types** for identifiers depending on syntactic position:

| Position | Node Type | Matched by backtick? |
|----------|-----------|---------------------|
| Expression (`x = FooType{}`) | `identifier` | ✅ |
| Var declaration (`var x FooType`) | `type_identifier` | Often ✅ |
| Struct field type (`Status FooType`) | `field_declaration > type_identifier` | ❌ Missed |
| Pointer struct field (`Req *FooType`) | `field_declaration > pointer_type > type_identifier` | ❌ Missed |

GritQL parses `` `FooType` `` in **expression context**, producing an `identifier` node. But struct field type positions produce `type_identifier` nodes — a **different node type** in tree-sitter's Go grammar. They look identical as text but are different AST nodes.

From tree-sitter-go `node-types.json`, a `field_declaration` has:
```
field_declaration:
  name: identifier
  type: _type | generic_type | qualified_type | type_identifier
```

The type child is explicitly `type_identifier`, not `identifier`.

**Workarounds**:

**Option A**: Explicitly match pointer forms (which use `pointer_type > type_identifier`, sometimes matched):
```grit
or {
  `FooType` => `detection.FooType` where { $_ <: not within `detection.$_` },
  `*FooType` => `*detection.FooType`
}
```

**Option B**: Use `gofmt -r` which uses Go's own AST and handles all type positions correctly:
```bash
gofmt -r 'FooType -> detection.FooType' -w ./...
gofmt -r 'DetectedStatus -> detection.DetectedStatus' -w ./...
```

**Option C**: After GritQL, run `go build ./...` to find remaining undefined errors, then fix with `Edit`.

---

### Problem 3: Multi-Pattern Files — Correct Syntax

When a `.grit` file has multiple top-level patterns, use `sequential` with explicit `contains` and `not within` guards:

```grit
language go

sequential {
  bubble file($body) where $body <: contains `OldType1` => `pkg.OldType1` where {
    $_ <: not within `pkg.$_`
  },
  bubble file($body) where $body <: contains `OldType2` => `pkg.OldType2` where {
    $_ <: not within `pkg.$_`
  }
}
```

**Rules for `sequential`**:
- Only supported at the **top level** of a Grit program
- Each step needs explicit `contains` (NOT auto-wrapped)
- Each step needs its own `not within` guard
- Without `sequential`, multiple top-level patterns run as `or`, not sequentially

---

## Go-Specific Pattern Templates

### Safely Add Package Prefix to a Type (Single)

```grit
language go

`FooType` => `detection.FooType` where {
  $_ <: not within `detection.$_`
}
```

### Safely Add Package Prefix to Multiple Types

```grit
language go

sequential {
  bubble file($body) where $body <: contains `TypeA` => `pkg.TypeA` where {
    $_ <: not within `pkg.$_`
  },
  bubble file($body) where $body <: contains `TypeB` => `pkg.TypeB` where {
    $_ <: not within `pkg.$_`
  },
  bubble file($body) where $body <: contains `FuncA($$$args)` => `pkg.FuncA($$$args)` where {
    $_ <: not within `pkg.$_`
  }
}
```

### Handle Both Regular and Pointer Types

```grit
language go

or {
  `FooType` => `detection.FooType` where { $_ <: not within `detection.$_` },
  `*FooType` => `*detection.FooType`
}
```

### Rename Function Call

```grit
language go

`$obj.OldMethod($$$args)` => `$obj.NewMethod($$$args)`
```

### Update Import Path

```grit
language go

`"old/package/path"` => `"new/package/path"`
```

---

## The `not within` Predicate

`not within` traverses **upward** through the AST from the matched node and fails the match if it encounters the specified pattern.

```grit
// Prevent matching if already inside `detection.anything`
`FooType` => `detection.FooType` where {
  $_ <: not within `detection.$_`
}

// Multiple exclusions using or
`FooType` => `detection.FooType` where {
  $_ <: not within or {
    `detection.FooType`,
    `other.FooType`
  }
}
```

---

## The `sequential` Clause

`sequential` applies patterns one at a time to the accumulated result of previous steps.

**Important**: Steps in `sequential` are NOT auto-wrapped with `contains`. You must add `contains` explicitly:

```grit
language go

sequential {
  // CORRECT: explicit contains
  bubble file($body) where $body <: contains `OldA` => `NewA`,

  // WRONG: missing contains (will not match anything)
  `OldB` => `NewB`
}
```

---

## Hybrid Workflow for Go Package Migrations

For complete coverage when moving types to a new package:

```bash
# Step 1: Apply GritQL for most expression-context identifiers
grit apply migration.grit --dry-run
grit apply migration.grit

# Step 2: Use gofmt -r for struct field type positions (GritQL misses these)
gofmt -r 'OldType -> pkg.OldType' -w ./...

# Step 3: Find any remaining occurrences
go build ./... 2>&1 | grep "undefined:"
grep -rn "OldType" . --include="*.go"

# Step 4: Fix remaining with Edit tool
```

---

## When GritQL Is NOT the Right Tool

Prefer `gofmt -r`, `MultiEdit`, or `Grep`+`Edit` for:

1. **Simple single-file changes** — overhead isn't worth it
2. **Go struct field type annotations** — GritQL misses `type_identifier` nodes
3. **Import block changes** — `gofmt -r` or `Edit` is more reliable
4. **Comments and strings** — GritQL skips these by design

---

## Pattern File Format Summary

```grit
language go

// Simple: single pattern (auto-wrapped with contains)
`FooType` => `detection.FooType` where {
  $_ <: not within `detection.$_`
}

// Multiple alternatives in one pass: use or
or {
  `FooType` => `detection.FooType`,
  `*FooType` => `*detection.FooType`
}

// Sequential multi-step transforms: use sequential
sequential {
  bubble file($body) where $body <: contains `A` => `pkg.A`,
  bubble file($body) where $body <: contains `B` => `pkg.B`
}
```

---

## Sources

- [GritQL Patterns](https://docs.grit.io/language/patterns)
- [Pattern Modifiers](https://docs.grit.io/language/modifiers) — `contains`, `sequential`, `not within`
- [Conditions](https://docs.grit.io/language/conditions) — `where`, `not within`
- [tree-sitter-go node-types.json](https://github.com/tree-sitter/tree-sitter-go/blob/master/src/node-types.json)
