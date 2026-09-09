---
name: code-refactoring
description: Orchestrate large structural code refactors combining semantic search (ast-grep) with AST-based transformation (gritql). Use for multi-file renames, API migrations, and pattern modernization with mandatory quality gates.
allowed-tools: "Bash(sg *),Read,Grep,Glob,Edit,Write,mcp__kibitzer__list_architecture_symbols,mcp__kibitzer__get_architecture_node,mcp__kibitzer__architecture_assessment"
---

# Code Refactoring

Orchestrate large structural refactors using `ast-grep` to discover scope and `gritql` to apply transformations safely.

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

The first two steps exist to answer "where, and what exactly" **before** any file gets read in
full or any transformation gets designed. Skipping them is the single biggest cause of a refactor
that turns into an unplanned full-file read-through, or a gritql pattern that's wrong on the first
try because it was written against a guess instead of a symbol map.

### 0. Locate — only if the target isn't already named

If the user pointed at a specific file, symbol, or pattern, skip straight to step 1. Otherwise,
rank candidates before touching anything — don't start reading files hoping to spot a smell:

- Repo has kibitzer (`.claude/inspect.json` present, or its MCP server connected)? Use
  `mcp__kibitzer__architecture_assessment` (scope it to the suspect package/dir) for
  complexity/layering hits, or `mcp__kibitzer__list_architecture_symbols` for God-Object-sized
  types by field/method count.
- Need churn as well as complexity, or kibitzer isn't configured for this repo? Run the
  `code-hotspot-analysis` skill — its complexity × churn hotspot score (static coupling + git
  temporal coupling) is a stronger signal than either metric alone, and it tells you *why* a file
  is a target (structural chokepoint vs. temporal coupling vs. both).
- Broader multi-metric sweep, or a language kibitzer's symbol export doesn't cover yet? Use
  `quality:find-refactor-candidates`.
- Pick the top 1-3 ranked hits — ideally ones flagged by more than one axis — as the actual
  target(s). Don't refactor an entire ranked list in one pass; re-run this step per target instead.

### 1. Map the Symbol Tree Before Reading Code

Before opening any file in full, build a structural map of the target so the transformation
pattern in step 3 is written against real signatures, not a guess:

- kibitzer available → `mcp__kibitzer__list_architecture_symbols` (scoped to the target
  package/dir) or `mcp__kibitzer__get_architecture_node` (one type/symbol by exact reference) —
  both return JSON: types, methods, fields, signatures, no file body.
- No kibitzer, or the language isn't in kibitzer's symbol-export coverage (Go/TS/TSX/JS today) →
  `Glob` for file layout, then `sg --pattern` structural queries (type/struct/interface/function
  signatures — see `code-ast-grep`) to inventory symbols without reading full files.
- Only once the map narrows the actual functions/types in play, `Read` with `offset`/`limit` on
  just those line ranges. A blind full-file `Read` at this point means the map step was skipped —
  go back and do it instead of reading on.

### 2. Pre-Flight Checks

```bash
git status          # Must be clean
git checkout -b refactor/<description>
```

Run baseline build + tests before starting.

### 3. Discover Scope with ast-grep

With the symbol map from step 1 in hand, confirm the full blast radius before transforming
anything:

```bash
# Find all sites that will be affected
sg --pattern '$obj.oldMethod($$$)' --lang java src/

# Verify count and locations are expected
```

See `code-ast-grep` skill for full pattern syntax.

### 4. Preview with gritql (MANDATORY)

```bash
grit apply '<pattern>' --dry-run > /tmp/preview.diff
# Review ALL changes before applying
```

See `code-gritql` skill for transformation pattern syntax.

### 5. Apply and Verify (MANDATORY)

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

### 6. Commit

If completing the refactor required any behavior change (not just structure), split it into its own commit — never mix the two (see `git:commit`).

```bash
git add -u
git commit -m "refactor: <clear description>"
```

## Quality Gates

Before completing any refactor:
- [ ] Target chosen from a ranked signal (hotspot score / kibitzer / find-refactor-candidates), not a hunch — unless the user named the target directly
- [ ] Symbol map built before any full-file read
- [ ] ast-grep scope review done before applying
- [ ] Dry-run previewed and all changes intentional
- [ ] Any behavior change needed to complete the refactor is in a separate commit from the structural change
- [ ] Code formatted
- [ ] Clean build (no compilation errors)
- [ ] Tests passing
- [ ] Git diff reviewed

## Tool Selection

| Scenario | Tool |
|----------|------|
| Find all affected code sites | `ast-grep` (`sg`) |
| Multi-file expression-level Kotlin rewrite | `gritql` |
| Kotlin catch/if/try block transformation | `Edit` (or `ast-grep --rewrite` YAML) |
| Multi-file structural transformation (non-Kotlin) | `gritql` |
| Single file, simple change | `Edit` |
| Same text change across files | `MultiEdit` |

### Kotlin-specific note
GritQL only handles expression-level Kotlin patterns (function calls, method chains, imports). For **statement-level changes** — catch blocks, if statements, variable declarations, try/finally — use `Edit` for targeted changes or `ast-grep` with a YAML rule for structural multi-file rewrites. See `code-gritql` skill for the full Kotlin limitations list.

## Progressive Context

- For transformation patterns (rename, import, annotation migration): see `code-gritql` skill and `reference.md`
- For search patterns (finding callers, usages, class definitions): see `code-ast-grep` skill

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `code-hotspot-analysis` | Step 0 — rank targets by complexity × churn (kibitzer or the Go toolchain + git temporal coupling) before picking what to touch |
| `quality:find-refactor-candidates` | Step 0 — broader multi-metric candidate sweep when kibitzer isn't configured or the finer hotspot methodology is overkill |
| `code-ast-grep` | Steps 1 and 3 — symbol inventory without full reads, then discover scope of changes before applying any transformation |
| `code-gritql` | Apply AST-based multi-file code transformations |
| `code-architecture-best-practices` | Validate refactored structure against SOLID/Clean Architecture |
| `code-review` | Verify refactor output before merging to main branch |
| `code-debugging` | Diagnose test failures or build errors introduced during refactoring |
| `lean-agent-loop` | Iterate quality gate failures (format, compile, test) with parallel agents until all pass |
