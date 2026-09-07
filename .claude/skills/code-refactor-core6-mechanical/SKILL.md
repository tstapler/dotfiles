---
name: code-refactor-core6-mechanical
description: >
  Execute Arlo Belshee's Core 6 Refactorings mechanically using available CLI tools
  across TypeScript, Go, Rust, and Java. Evaluates tool availability, routes to the
  most precise tool, and produces a reviewable git diff. Use for: rename symbol,
  extract function, inline variable, introduce variable, change signature, move symbol.
  Never hand-edits at scale. Covers: rename, extract, inline, introduce-variable,
  change-signature, move. Triggers on: Core 6, Belshee, mechanical refactor, rename method,
  extract function, inline call, introduce variable, change signature, move class.
triggers:
  - "refactor"
  - "rename"
  - "extract function"
  - "inline"
  - "introduce variable"
  - "change signature"
  - "move symbol"
  - "mechanical refactor"
  - "core 6"
---

# Core 6 Mechanical Refactoring

Execute the Core 6 mechanically — tools drive every transformation; Claude selects the best available tool, runs it, and verifies the result. No hand-editing at scale.

## When to Use

**Use this skill for:**

| Trigger | Example |
|---------|---------|
| Explicit rename request | "Rename `processUser` to `handleUser` everywhere" |
| Extract function/method | "Extract this block into a function called `validateInput`" |
| Inline a function/variable | "Inline `isValid` — it has only one call site" |
| Introduce variable | "Name this expression `totalWithTax`" |
| Change function signature | "Add `ctx context.Context` as first param to `FetchData`" |
| Move symbol | "Move `UserService` to `src/core/`" |
| Naming improvement | "This abbreviation `ttlPrc` should be `totalPrice`" |
| Any "Core 6" / Belshee refactoring request | "Do a mechanical refactor on this" |

**Don't use for:**

- Formatting or whitespace changes → use `gofmt`, `prettier`, `rustfmt`
- Logic changes or bug fixes → manual review required
- YAML/JSON/Markdown edits → use `Edit` tool directly
- Refactorings beyond Core 6 (Extract Class, Extract Interface, etc.) → use `code-refactoring` skill
- Languages outside TypeScript, Go, Rust, Java → no coverage here
- Arbitrary rewrites that aren't behavior-preserving → not mechanical

---

## Step 0: Pre-Flight

```bash
# Verify clean git state before any refactoring
git status   # must show no uncommitted changes (or stash first)

# Create a feature branch for the refactor
git checkout -b refactor/<description>

# Run baseline build to confirm the codebase compiles before starting
# TypeScript:
npx tsc --noEmit

# Go:
go build ./...

# Rust:
cargo check

# Java (Maven):
mvn compile -q

# Java (Gradle):
./gradlew compileJava -q
```

Record the baseline test count before starting. Any regression in test count after the refactor indicates a problem.

---

## Step 1: Inventory Available Tools

Run these checks at the start of every refactoring session. Record results before routing.

```bash
# LSP tool (Claude Code deferred tool — check via ToolSearch, not CLI)
# Run: ToolSearch("select:LSP") — if schema is returned, LSP is available
# LSP exposes: findReferences, goToDefinition, documentSymbol, hover, getDiagnostics
# LSP does NOT expose: rename, codeAction — those require language-specific tools

# ast-grep (structural search + rewrite)
sg --version 2>/dev/null && echo "sg:AVAILABLE" || echo "sg:MISSING"

# gritql (transformation complement to ast-grep)
grit --version 2>/dev/null && echo "grit:AVAILABLE" || echo "grit:MISSING"

# gopls (Go — semantic rename, code actions)
gopls version 2>/dev/null && echo "gopls:AVAILABLE" || echo "gopls:MISSING"
# NOTE: gorename is deprecated and does not support Go modules — never use it

# rust-analyzer (Rust — LSP server; no standalone rename CLI)
rust-analyzer --version 2>/dev/null && echo "rust-analyzer:AVAILABLE (LSP only)" || echo "rust-analyzer:MISSING"

# ts-morph (TypeScript — type-aware rename via npx)
npx --yes ts-morph --version 2>/dev/null && echo "ts-morph:AVAILABLE" || echo "ts-morph:UNAVAILABLE"

# Maven / Gradle wrapper (Java — OpenRewrite)
test -f mvnw && echo "mvnw:AVAILABLE" || echo "mvnw:MISSING"
test -f gradlew && echo "gradlew:AVAILABLE" || echo "gradlew:MISSING"
test -f pom.xml && echo "pom.xml:PRESENT" || echo "pom.xml:MISSING"
```

**Record all results in a summary before proceeding. The execution path depends entirely on what is available.**

---

## Step 2: Select the Refactoring

| Refactoring | Intent | Tier | Notes |
|-------------|--------|------|-------|
| **Rename** | Rename a symbol project-wide, all use sites | A | CLI-feasible for all 4 languages |
| **Change Signature** | Add/remove/reorder function parameters | A | CLI-feasible; compiler catches mismatches |
| **Move** | Relocate symbol to different file/package | A | CLI-feasible with per-language procedure |
| **Extract** | Pull a block into a named function | B | LSP required; no CLI path for TS/Rust/Java |
| **Inline** | Replace call/reference with body/value | B | LSP required; Java partial via OpenRewrite |
| **Introduce Variable** | Name an expression as a local variable | B | LSP required; Java has no extract-variable recipe |

**Tier A** = CLI tools can execute it fully. **Tier B** = requires LSP or is IDE-only.

---

## Step 3: Route to Execution Path

```
REFACTORING REQUEST
│
├─ Tier A (Rename, Change Signature, Move)?
│  └─ YES → proceed to ## Tier A Execution
│           Route by language:
│           TypeScript → ts-morph primary, ast-grep fallback
│           Go → gopls rename (NEVER gorename — deprecated)
│           Rust → ast-grep (no stable rename CLI; warn on trait methods)
│           Java → OpenRewrite (mvnw/gradlew rewrite:run)
│
└─ Tier B (Extract, Inline, Introduce Variable)?
   ├─ Java + Inline → OpenRewrite InlineVariable (Tier A exception — use CLI)
   ├─ LSP available? (ToolSearch "select:LSP" returns schema)
   │  └─ YES → proceed to ## Tier B Execution (LSP)
   └─ LSP NOT available?
      └─ proceed to ## No-Tool Fallback Protocol
         NEVER attempt Tier B without LSP or the Java/OpenRewrite exception
```

---

## Tier A Execution

### TypeScript — Rename

**Primary: ts-morph (type-aware, project-wide)**

```bash
# Inline ts-morph rename via npx tsx (no global install needed)
# Replace: old symbol name, new symbol name, source file path
npx tsx -e "
const { Project } = require('ts-morph');
const project = new Project({ tsConfigFilePath: './tsconfig.json' });
const sourceFile = project.getSourceFileOrThrow('src/user.ts');
const fn = sourceFile.getFunctionOrThrow('processUser');
fn.rename('handleUser');
project.saveSync();
console.log('Renamed processUser -> handleUser across', project.getSourceFiles().length, 'files');
"

# For renaming a class or interface, swap getFunctionOrThrow with:
# sourceFile.getClassOrThrow('ClassName').rename('NewName')
# sourceFile.getInterfaceOrThrow('IName').rename('INewName')
```

**Fallback: ast-grep (structural only — warns on scope)**

```bash
# WARN: ast-grep is NOT type-aware; it renames every syntactic occurrence
# Use only when ts-morph is unavailable and occurrences are unambiguous

# Scope check first — review all matches before applying
sg --pattern 'processUser' --lang typescript src/

# Apply (review scope output above before running)
sg --pattern 'processUser' --rewrite 'handleUser' --lang typescript src/ --update-all
```

**PITFALL — Dynamic property access is invisible to all rename tools:**
```typescript
// These are NOT updated by ts-morph, ast-grep, or any rename tool:
obj['processUser']        // bracket notation
record['processUser']     // Record<string, ...> access
```
After any TypeScript rename, run:
```bash
grep -r '"processUser"\|'"'"'processUser'"'"'' src/ --include="*.ts"
```
Review each hit — not every string match is a reference.

Fixture: `~/.claude/skills/fixtures/core6-mechanical/typescript/rename/`  
Verify: `npx tsc --noEmit`

---

### TypeScript — Change Signature

**Primary: ts-morph script (add/remove/reorder parameters)**

```bash
# Add an optional parameter to fetchData(url: string)
npx tsx -e "
const { Project } = require('ts-morph');
const project = new Project({ tsConfigFilePath: './tsconfig.json' });
const sourceFile = project.getSourceFileOrThrow('src/api.ts');
const fn = sourceFile.getFunctionOrThrow('fetchData');
fn.addParameter({ name: 'options', type: 'RequestOptions', hasQuestionToken: true });
project.saveSync();
"

# Scope check: find all call sites before changing signature
sg --pattern 'fetchData($$$ARGS)' --lang typescript src/
```

**Fallback: ast-grep + gritql for call-site rewriting**

```bash
# Step 1: find all call sites
sg --pattern 'fetchData($A, $B)' --lang typescript src/

# Step 2: rewrite call sites (grit)
grit apply '`fetchData($a, $b)` => `fetchData($b, $a)`' src/

# WARNING: named parameters and destructuring are NOT handled by grit patterns
```

Fixture: `~/.claude/skills/fixtures/core6-mechanical/typescript/change-signature/`  
Verify: `npx tsc --noEmit`

---

### TypeScript — Move

**Primary: ts-morph moveToDirectory (file-level move with import updates)**

```bash
# Move entire file to new directory (imports updated project-wide)
npx tsx -e "
const { Project } = require('ts-morph');
const project = new Project({ tsConfigFilePath: './tsconfig.json' });
const sourceFile = project.getSourceFileOrThrow('src/services/user.ts');
sourceFile.moveToDirectory('src/core/');
project.saveSync();
console.log('Moved file; imports updated across project');
"
```

For moving a single export from one file to another (not whole-file move), write a custom script using `getExportedDeclarations()` + target file manipulation.

Fixture: `~/.claude/skills/fixtures/core6-mechanical/typescript/move/`  
Verify: `npx tsc --noEmit`

---

### Go — Rename

**Primary: gopls rename (semantic, module-graph-aware)**

```bash
# Dry-run first — review diff before applying
gopls rename -d ./pkg/handler.go:8:6 HandleRequest

# Apply when satisfied with the diff
gopls rename -w ./pkg/handler.go:8:6 HandleRequest

# Format: gopls rename [flags] <file>:<line>:<col> <new_name>
# -d = show diff only (do NOT modify files)
# -w = write changes to source files
```

**PITFALL — gorename is deprecated:**
```bash
# NEVER use this (broken for Go modules):
# gorename -from 'pkg.OldName' -to 'NewName'

# ALWAYS use gopls rename instead
```

**PITFALL — JSON struct field rename changes wire format:**
```go
// Renaming UserID renames the JSON key from "UserID" to the new name
// if no json:"..." struct tag is present. Check for json tags before renaming.
type Response struct { UserID int }  // json key: "UserID"
```

**PITFALL — gopls rejects some renames:**
- `main` package symbols
- `x_test` package symbols
- Anonymous embedded struct fields

**Fallback: ast-grep (structural only)**
```bash
# WARN: ast-grep cannot distinguish two functions with the same name in different packages
sg --pattern 'ProcessRequest($$$ARGS)' --lang go ./...

# Apply if occurrences are unambiguous
sg --pattern 'ProcessRequest' --rewrite 'HandleRequest' --lang go --update-all
```

Fixture: `~/.claude/skills/fixtures/core6-mechanical/go/rename/`  
Verify: `go build ./... && go vet ./...`

---

### Go — Change Signature

**gopls has move-param-left/right as LSP code action only (not a CLI subcommand).**  
Use ast-grep + gritql for call-site rewriting, then update the declaration manually.

```bash
# Step 1: scope check — find all call sites
sg --pattern 'FetchData($$$ARGS)' --lang go ./...

# Step 2: rewrite call sites to add ctx as first argument
grit apply '`FetchData($url)` => `FetchData(ctx, $url)`' ./

# Step 3: update the function declaration manually (one place)
# Change: func FetchData(url string)
# To:     func FetchData(ctx context.Context, url string)

# Step 4: verify — Go compiler catches ALL call-site mismatches
go build ./...
```

**PITFALL — context.Context is always the first parameter by Go convention.**

Fixture: `~/.claude/skills/fixtures/core6-mechanical/go/change-signature/`  
Verify: `go build ./...`

---

### Go — Move

**No direct CLI subcommand for cross-package move. Use this procedure:**

```bash
# Step 1: copy the declaration to the destination package (manual Edit)
# Step 2: use gopls rename to update all references to the fully-qualified new name
gopls rename -w ./internal/user/repo.go:5:6 repository.UserRepository

# Step 3: delete the old declaration from the source file (Edit)
# Step 4: verify — every broken reference is a compile error
go build ./...
```

**PITFALL — gopls only processes files within the current Go module graph.**  
Files in a different `go.mod` (monorepo sibling modules) are not updated.

Fixture: `~/.claude/skills/fixtures/core6-mechanical/go/move/`  
Verify: `go build ./...`

---

### Rust — Rename

**No stable standalone rename CLI for Rust. rust-analyzer is LSP-only.**  
Use ast-grep as the structural fallback with explicit warnings.

```bash
# Scope check — review ALL matches before applying
sg --pattern 'process_request' --lang rust src/

# Apply (structural rename — see warnings below)
sg --pattern 'process_request' --rewrite 'handle_request' --lang rust src/ --update-all
```

**CRITICAL PITFALL — Trait method rename (rust-analyzer#2977):**
```
ast-grep renames the declaration but NOT all trait implementations or call sites.
After rename, run `cargo check` and expect:
  - E0407: method not a member of trait (at unupdated impl blocks)
  - E0046: not all trait items implemented

Manually inspect all `impl Trait for T` blocks and update them.
```

**CRITICAL PITFALL — Proc-macro generated code (rust-analyzer#14137):**
```rust
// Renaming a field on this struct changes the serde JSON key
#[derive(Serialize, Deserialize)]
struct User { user_id: i32 }  // serde key: "user_id"

// After renaming user_id → id, the JSON key changes to "id"
// Add #[serde(rename = "user_id")] to preserve wire format
```

**PITFALL — cfg-gated methods (rust-analyzer#1527):**  
Platform-conditional methods may not all be visible on the current compilation target.  
After rename, compile for all target platforms.

Fixture: `~/.claude/skills/fixtures/core6-mechanical/rust/rename/`  
Verify: `cargo check && cargo test`

---

### Rust — Change Signature

**rust-analyzer has no change-signature assist as of 2025.**  
Use this rename-and-replace procedure:

```bash
# Step 1: scope check — find all call sites
sg --pattern 'process($$$ARGS)' --lang rust src/

# Step 2: rewrite call sites to add config parameter
grit apply '`process($items)` => `process($items, &config)`' src/

# Step 3: update the function declaration manually (Edit)
# Change: fn process(items: &[Item])
# To:     fn process(items: &[Item], config: &Config)

# Step 4: verify — borrow checker surfaces all mismatches
cargo check
```

**PITFALL — cfg attributes:** Check all platform-conditional variants are updated.

Fixture: `~/.claude/skills/fixtures/core6-mechanical/rust/change-signature/`  
Verify: `cargo check`

---

### Rust — Move

**No move-symbol assist in rust-analyzer.** Use this manual procedure:

```bash
# Step 1: move the item declaration to the destination module file (Edit)
# Step 2: add pub use re-export at old location (optional — preserves API stability)
# Step 3: update use statements project-wide
sg --pattern 'use services::UserService;' --lang rust src/

# Apply import path update
sg --pattern 'use services::UserService' --rewrite 'use core::user::UserService' --lang rust src/ --update-all

# Step 4: verify — Rust module system surfaces every broken reference
cargo check
```

Fixture: `~/.claude/skills/fixtures/core6-mechanical/rust/move/`  
Verify: `cargo check`

---

### Java — Rename

**Primary: OpenRewrite via Maven plugin (semantic, updates all references)**

```bash
# ALWAYS dry-run first — diff appears in target/rewrite/results/
mvn rewrite:dryRun

# Review the diff, then apply
mvn -U org.openrewrite.maven:rewrite-maven-plugin:run \
  -Drewrite.activeRecipes=org.openrewrite.java.ChangeMethodName \
  "-Drewrite.ChangeMethodName.methodPattern=com.example.RequestService processRequest(..)" \
  -Drewrite.ChangeMethodName.newMethodName=handleRequest

# For class/type rename:
mvn -U org.openrewrite.maven:rewrite-maven-plugin:run \
  -Drewrite.activeRecipes=org.openrewrite.java.ChangeType \
  -Drewrite.ChangeType.oldFullyQualifiedTypeName=com.example.old.UserService \
  -Drewrite.ChangeType.newFullyQualifiedTypeName=com.example.new.UserService

# Method pattern syntax: "fully.qualified.ClassName methodName(..)" — (..) matches any params
```

**PITFALL — Spring @Qualifier and @Value strings are NOT updated:**
```java
// These are invisible to OpenRewrite and all rename tools:
@Qualifier("processRequest")    // Spring bean name as string
@Value("${process.request}")    // property key as string
```
After rename:
```bash
grep -r 'processRequest\|ProcessRequest' src/main/resources/ --include="*.xml" --include="*.properties" --include="*.yml"
```

**PITFALL — Lombok/MapStruct generated code:**  
Rebuild is required after rename. Do not commit stale generated files.

**PITFALL — Serializable field rename changes binary format:**  
Treat as a schema migration. Update `serialVersionUID` explicitly.

**Fallback: ast-grep (structural only)**
```bash
# WARN: annotation strings (@Qualifier, @Value) are NOT updated; compile-only references are
sg --pattern 'processRequest($$$ARGS)' --lang java src/
sg --pattern 'processRequest' --rewrite 'handleRequest' --lang java --update-all
```

Fixture: `~/.claude/skills/fixtures/core6-mechanical/java/rename/`  
Verify: `mvn compile && mvn test`

---

### Java — Change Signature

**Primary: OpenRewrite recipes (declaration + all call sites)**

```bash
# Reorder parameters: createUser(email, name) → createUser(name, email)
mvn -U org.openrewrite.maven:rewrite-maven-plugin:run \
  -Drewrite.activeRecipes=org.openrewrite.java.ReorderMethodArguments \
  "-Drewrite.ReorderMethodArguments.methodPattern=com.example.UserService createUser(String, String)" \
  "-Drewrite.ReorderMethodArguments.newParameterNames=[name, email]" \
  "-Drewrite.ReorderMethodArguments.oldParameterNames=[email, name]"

# Add a new parameter
mvn -U org.openrewrite.maven:rewrite-maven-plugin:run \
  -Drewrite.activeRecipes=org.openrewrite.java.AddMethodParameter \
  "-Drewrite.AddMethodParameter.methodPattern=com.example.UserService createUser(String, String)" \
  -Drewrite.AddMethodParameter.parameterType=java.lang.String \
  -Drewrite.AddMethodParameter.parameterName=role \
  -Drewrite.AddMethodParameter.parameterIndex=0
```

Fixture: `~/.claude/skills/fixtures/core6-mechanical/java/change-signature/`  
Verify: `mvn compile`

---

### Java — Move

**Primary: OpenRewrite ChangePackage (all import references updated)**

```bash
# Move class to new package
mvn -U org.openrewrite.maven:rewrite-maven-plugin:run \
  -Drewrite.activeRecipes=org.openrewrite.java.ChangePackage \
  -Drewrite.ChangePackage.oldPackageName=com.example.services \
  -Drewrite.ChangePackage.newPackageName=com.example.repository

# Or move a specific type
mvn -U org.openrewrite.maven:rewrite-maven-plugin:run \
  -Drewrite.activeRecipes=org.openrewrite.java.ChangeType \
  -Drewrite.ChangeType.oldFullyQualifiedTypeName=com.example.services.UserRepository \
  -Drewrite.ChangeType.newFullyQualifiedTypeName=com.example.repository.UserRepository
```

**PITFALL — XML bean configuration files are NOT updated:**
```xml
<!-- These are invisible to OpenRewrite: -->
<bean class="com.example.services.UserRepository"/>
<property name="userRepository"/>
```
After move:
```bash
grep -r 'UserRepository\|com.example.services' src/main/resources/ --include="*.xml"
```

Fixture: `~/.claude/skills/fixtures/core6-mechanical/java/move/`  
Verify: `mvn compile`

---

## Tier B Execution

**Tier B operations — Extract, Inline, Introduce Variable — require LSP.**  
No CLI-only path exists for any of these in TypeScript, Go, or Rust.

**Java exception:** OpenRewrite `InlineVariable` and `InlineMethodCalls` are CLI-feasible (see Java / Inline below).

**LSP detection:** Before proceeding, run `ToolSearch("select:LSP")`. If a schema is returned, the LSP tool is available. If not, go to **No-Tool Fallback Protocol**.

**Important:** The Claude Code LSP tool exposes `findReferences`, `goToDefinition`, `documentSymbol`, `hover`, and `getDiagnostics`. It does NOT expose `rename` or `codeAction`. Tier B operations use `findReferences` to scope the extraction and then Edit to construct the new function/variable.

---

### Extract (All Languages)

Extract requires LSP for all 4 languages. No CLI-only path exists.

**Go (closest to CLI):**
```bash
# gopls has refactor.extract.function as a code action — byte-range form (experimental)
gopls codeaction -exec -kind refactor.extract.function -diff ./main.go:#100-#250
# WARNING: byte ranges are fragile — recompute offset after every file change
# Remove -diff to apply; with -diff only shows the diff
```

**Rust (LSP assist):**  
rust-analyzer `extract_function` assist — available via LSP code action in any LSP-capable editor.  
Note: extracted function gets default name `fun_name` — rename it immediately.

**TypeScript:**  
No CLI. TypeScript compiler API supports `getEditsForRefactor` but requires custom scripting.  
Use Claude Code LSP tool: `findReferences` to scope, then Edit to create function.

**Java:**  
No OpenRewrite recipe for arbitrary extraction. IDE/LSP only.

Fixtures: `~/.claude/skills/fixtures/core6-mechanical/<lang>/extract/`  
The `command.sh` in each Tier B extract fixture documents the LSP invocation sequence.

---

### Inline (All Languages)

**Java — CLI-feasible via OpenRewrite (Tier A exception):**

```bash
# Inline single-use local variables (eliminates temp vars used exactly once)
mvn -U org.openrewrite.maven:rewrite-maven-plugin:run \
  --define rewrite.recipeArtifactCoordinates=org.openrewrite.recipe:rewrite-static-analysis:RELEASE \
  --define rewrite.activeRecipes=org.openrewrite.staticanalysis.InlineVariable \
  --define rewrite.exportDatatables=true

# Inline specific method calls (replace call with method body for a pattern)
mvn -U org.openrewrite.maven:rewrite-maven-plugin:run \
  --define rewrite.activeRecipes=org.openrewrite.java.InlineMethodCalls \
  "--define rewrite.InlineMethodCalls.methodPattern=com.google.common.base.Preconditions checkNotNull(..)" \
  "--define rewrite.InlineMethodCalls.replacement=java.util.Objects.requireNonNull(#{p0})" \
  "--define rewrite.InlineMethodCalls.imports=[\"java.util.Objects\"]"
```

**Go (LSP code action):**  
gopls `refactor.inline.call` — available as LSP code action. As of v0.17, comment handling is still imperfect.

**Rust (LSP assists):**  
rust-analyzer `inline_local_variable` — inline a `let` binding at all use sites.  
rust-analyzer `inline_call` — replace function call with callee body (edge cases with early returns).

**TypeScript:**  
No CLI path. IDE-only.

Fixtures: `~/.claude/skills/fixtures/core6-mechanical/<lang>/inline/`

---

### Introduce Variable (All Languages)

All languages require LSP for introduce-variable. No CLI path.

**Go (LSP code action):**  
gopls `refactor.extract.variable` — includes extract-all-occurrences variant.

**Rust (LSP assist):**  
rust-analyzer `extract_variable` — prompts for variable name (added in PR #17587).

**TypeScript:**  
TypeScript language service supports it via `getEditsForRefactor` — no CLI.

**Java:**  
No OpenRewrite recipe for introduce-variable (OpenRewrite has `InlineVariable` — the inverse — but not extract-variable).  
IDE-only.

Fixtures: `~/.claude/skills/fixtures/core6-mechanical/<lang>/introduce-variable/`

---

## No-Tool Fallback Protocol

When no tier is available for the requested refactoring × language combination:

**Do NOT hand-edit.** Hand-editing is appropriate only for 1–5 occurrences, single file, all occurrences visible in context. For anything larger: stop and document the gap.

**Why hand-editing is risky:**
- Scale: 30+ files cannot be held in context simultaneously; misses are inevitable
- Alias ambiguity: `import { OldName as Alias }` misses text search
- Dynamic references: string literals, XML config, annotation strings require a separate pass that is easy to forget

**Gap documentation template:**
```
TOOL GAP: <timestamp>
Language: <Go / TypeScript / Rust / Java>
Operation: <rename symbol X to Y on type T>
Reason gap exists: <tool not installed / symbol type unsupported / monorepo boundary>
Required tool: <name + install command>
Files partially updated: <list>
Files pending: <list>
Unblocking step: <what needs to happen before this can be completed>
```

Save to: `/tmp/refactor-gap-$(date +%Y%m%d-%H%M%S).md`

**Install commands for missing tools:**

```bash
# ast-grep
brew install ast-grep
sg --version   # verify

# gritql
brew install grit
grit --version   # verify

# gopls (Go)
go install golang.org/x/tools/gopls@latest
gopls version   # verify

# rust-analyzer (Rust)
rustup component add rust-analyzer
rust-analyzer --version   # verify

# ts-morph (TypeScript — per-project)
npm install --save-dev ts-morph
# Or one-off: npx tsx with ts-morph inline

# OpenRewrite (Java — requires Maven/Gradle project)
# No install needed; runs via Maven plugin (-U flag downloads automatically)
# Prerequisite: project must have pom.xml or build.gradle
```

---

## Verification Gate

Run after every refactoring before accepting the result.

**Per-language verification commands:**

| Language | Compile | Tests | Lint |
|----------|---------|-------|------|
| Go | `go build ./...` | `go test ./...` | `go vet ./...` |
| Rust | `cargo check` | `cargo test` | `cargo clippy` |
| TypeScript | `npx tsc --noEmit` | `npm test` or `npx jest` | `npx tsc --noEmit --strict` |
| Java (Maven) | `mvn compile` | `mvn test` | `mvn verify` |
| Java (Gradle) | `./gradlew compileJava` | `./gradlew test` | `./gradlew check` |

**Post-rename text search (ALL languages):**

After any rename, search for the old name as a string literal in non-source files:
```bash
# Go — JSON struct tags, XML configs
grep -r '"OldName"\|json:"OldName"' . --include="*.go" --include="*.xml" --include="*.json"

# Java — Spring annotations, XML bean config, properties
grep -r 'OldName' src/main/resources/ --include="*.xml" --include="*.properties" --include="*.yml"

# TypeScript — dynamic property access, test fixtures
grep -r '"OldName"\|'"'"'OldName'"'"'' src/ --include="*.ts" --include="*.json"

# Rust — serde rename attributes, test strings
grep -r '"old_name"' src/ --include="*.rs" --include="*.json"
```

---

## Quality Gates Checklist

Before claiming a refactoring is complete:

- [ ] Tool inventory run before starting
- [ ] Pre-flight: git clean, on feature branch
- [ ] Baseline build passed before refactoring
- [ ] Baseline test count recorded before refactoring
- [ ] Scope confirmed via `sg` or equivalent before transforming
- [ ] Dry-run output reviewed before applying
- [ ] Post-refactor compile passes with zero errors
- [ ] Post-refactor test count matches baseline (no regressions)
- [ ] `git diff HEAD` reviewed — all changed files are intentional
- [ ] Old name text-searched as string literal in all XML/JSON/properties files
- [ ] Hand-editing not used as substitute for mechanical tool

---

## Decision Matrix

| Refactoring | TypeScript | Go | Rust | Java |
|-------------|-----------|-----|------|------|
| **Rename** | Tier A — ts-morph (type-aware) / ast-grep fallback | Tier A — `gopls rename -w` | Tier A — ast-grep ⚠ trait methods incomplete | Tier A — OpenRewrite `ChangeMethodName`/`ChangeType` |
| **Extract** | Tier B — LSP only | Tier B — gopls `refactor.extract.function` (LSP) | Tier B — rust-analyzer `extract_function` (LSP) | Tier B — LSP only; no OpenRewrite recipe |
| **Inline** | Tier B — LSP only | Tier B — gopls `refactor.inline.call` (LSP) | Tier B — rust-analyzer `inline_local_variable` (LSP) | **Tier A/B** — OpenRewrite `InlineVariable` (variable inline); `InlineMethodCalls` (pattern) |
| **Introduce Variable** | Tier B — LSP only | Tier B — gopls `refactor.extract.variable` (LSP) | Tier B — rust-analyzer `extract_variable` (LSP) | Tier B — LSP only; OpenRewrite has no extract-variable recipe |
| **Change Signature** | Tier A — ts-morph script / ast-grep + gritql call-site rewrite | Tier A — ast-grep + gritql (gopls move-param via LSP only) | Tier A — ast-grep + gritql + manual declaration update | Tier A — OpenRewrite `ReorderMethodArguments`/`AddMethodParameter` |
| **Move** | Tier A — ts-morph `moveToDirectory()` | Tier A — manual copy + `gopls rename` for reference updates | Tier A — manual + ast-grep for `use` statement updates | Tier A — OpenRewrite `ChangePackage`/`ChangeType` |

---

## Known Limitations

**TypeScript:**
- Dynamic property access (`obj['name']`) is invisible to all rename tools including ts-morph and IDE LSP
- Files not included in `tsconfig.json` `include` patterns are invisible to ts-morph
- Monorepo project references must be kept in sync manually

**Go:**
- gorename is deprecated and does not support Go modules — never use it
- gopls cannot process files outside the current module graph
- Interface satisfaction via reflection or `any` + type assertion is invisible to gopls
- JSON struct field rename changes wire format (check `json:"..."` tags before renaming)
- Platform-specific files (`_linux.go`) may not all be in scope on the current platform

**Rust:**
- rust-analyzer has no stable standalone rename CLI — all rename is via LSP
- Trait method rename via ast-grep renames declaration only; impls and call sites require manual update
- Proc-macro boundaries are opaque; `#[derive(Serialize)]` field rename changes JSON wire format — add `#[serde(rename = "old_name")]` to preserve
- `cfg`-gated methods may not all be visible on the current compilation platform
- `cargo check` is the fastest way to surface all missed rename sites

**Java:**
- Spring `@Qualifier("beanName")` and `@Value("${key}")` string references are not updated by any tool
- XML bean configuration (legacy Spring XML, `web.xml`, `persistence.xml`) is not updated by OpenRewrite
- Lombok/MapStruct generated code requires rebuild — do not commit stale generated files
- `Serializable` field rename changes binary format — treat as schema migration
- OpenRewrite requires a Maven or Gradle build file; cannot run on arbitrary Java files

**All languages:**
- Generated files should be excluded from refactoring tools; add them to ignore lists
- Reflection-based references (runtime name lookups, ORM column mapping) require separate audit

---

## Fixture Reference

Fixtures are at: `~/.claude/skills/fixtures/core6-mechanical/`

| Language | Refactoring | Path |
|----------|-------------|------|
| TypeScript | rename | `typescript/rename/` |
| TypeScript | extract | `typescript/extract/` |
| TypeScript | inline | `typescript/inline/` |
| TypeScript | introduce-variable | `typescript/introduce-variable/` |
| TypeScript | change-signature | `typescript/change-signature/` |
| TypeScript | move | `typescript/move/` |
| Go | rename | `go/rename/` |
| Go | extract | `go/extract/` |
| Go | inline | `go/inline/` |
| Go | introduce-variable | `go/introduce-variable/` |
| Go | change-signature | `go/change-signature/` |
| Go | move | `go/move/` |
| Rust | rename | `rust/rename/` |
| Rust | extract | `rust/extract/` |
| Rust | inline | `rust/inline/` |
| Rust | introduce-variable | `rust/introduce-variable/` |
| Rust | change-signature | `rust/change-signature/` |
| Rust | move | `rust/move/` |
| Java | rename | `java/rename/` |
| Java | extract | `java/extract/` |
| Java | inline | `java/inline/` |
| Java | introduce-variable | `java/introduce-variable/` |
| Java | change-signature | `java/change-signature/` |
| Java | move | `java/move/` |

Each fixture directory contains: `before.<ext>`, `after.<ext>`, `command.sh` (dry-run by default), `verify.sh` (exits 0 if after.* compiles).

---

## Integration

- `code-refactoring` skill — for non-Core-6 structural refactors (Extract Class, Extract Interface, etc.)
- `code-ast-grep` skill — full ast-grep pattern syntax reference
- `code-gritql` skill — full gritql pattern syntax and known limitations
- `code-review` skill — apply after completing any refactoring before committing
