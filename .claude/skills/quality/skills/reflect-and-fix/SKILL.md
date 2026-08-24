---
description: Post-mortem cycle that turns fixed bugs into structural enforcement. For each bug just fixed, classifies the root cause, finds the earliest possible detection point on the enforcement ladder (compile → lint → test → checklist), implements it, and verifies it would have caught the original bug. Language-agnostic. Goal is to eliminate the class, not just the instance.
---

# Reflect & Fix — Shift Left After Every Bug

After fixing bugs, the work isn't done until recurrence is structurally impossible.
Run a 4-phase post-mortem that produces **runnable enforcement** (tests, lint rules,
type changes) — not documentation or promises.

This command is language-agnostic. Detect the stack from the repo (build files,
file extensions, lockfiles) and apply the enforcement using that stack's tools.
Examples below are given across several languages — use the one that matches, or
translate the idea to your language.

## Phase 1 — Enumerate

From the current session context, list every bug that was fixed. For each state:
- One sentence: what went wrong
- One sentence: what correct behavior looks like

If bugs aren't obvious from context, ask the user to list them before continuing.

## Phase 2 — Classify

Apply this taxonomy to each bug. Pick the **primary** failure mode.

| Category | Signature | Why it slips through |
|----------|-----------|---------------------|
| **Semantic/Intent** | Syntactically correct, semantically wrong — wrong default, wrong condition, wrong constant, off-by-one | Static analysis cannot detect intent; only a test asserting the intent can |
| **Framework Pattern Misuse** | Valid code in the wrong framework/async/lifecycle context — React hook with wrong deps, Compose `remember` without key, goroutine/coroutine scope escape, wrong dispatcher/thread, unclosed resource | Linter rule absent, disabled, or has a detection gap |
| **API Contract Gap** | Caller omits a required step the interface doesn't enforce — permission request, init call, cleanup, annotation | Interface doesn't express the contract at the type level |
| **Type Safety Gap** | Null/optional mishandled, wrong type, primitive/unit confusion, missing discriminant | Type isn't leveraged; a wrapper, union, or non-null type would prevent it |
| **Integration Gap** | Two individually-correct components interact incorrectly across a seam | Unit tests with mocks pass; the seam is never exercised together |
| **Dependency/Build Gap** | A dependency, version, or build-graph change introduces a crash/regression — bad transitive dep, init-time panic, version skew | `build`/unit tests pass; the failure is environmental or only at startup |
| **Duplicated/Divergent Logic** | The same precondition, invariant, or operation is implemented or invoked separately at multiple call sites; a fix applied to one site leaves the others broken (Fowler's "Shotgun Surgery" / "Divergent Change") | Nothing forces every call site to stay in sync — the class of "I fixed it but missed a caller" bug |

Fill this table before proceeding to Phase 3:

| Bug | Category | Why it slipped through | Earliest detection |
|-----|----------|----------------------|-------------------|
| ... | ... | ... | ... |

## Phase 3 — Implement Enforcement

Work down the **enforcement ladder** — implement at the highest (earliest) level achievable.
Never accept level 5 when 1–4 is reachable. "We'll be more careful" is not a system.
Always start at Level 0: if the fix touched more than one call site, or a future call site
could skip it, consolidate to a single source of truth first — enforcement applied to one of
several duplicated call sites is not enforcement, it's a fix that hasn't finished failing yet.

```
0.  Consolidate   → if the same precondition lives at 2+ call sites, merge to one source of
                    truth BEFORE picking a level below — you can't type-check or lint-guard
                    an invariant that's duplicated in three places (evaluate first, always)
1. Compile time   → make illegal states unrepresentable: non-null/non-optional type,
                    sealed/union type, value/newtype wrapper, required parameter, opt-in marker
1b. Type-Driven Design gate (evaluate before reaching for a linter)
2. Lint / static  → enable an existing linter rule, or write a custom one (incl. ast-grep/semgrep)
3. Unit test      → asserts the exact failed behavior; must FAIL against pre-fix code
4. Integration    → exercises both sides of a seam with minimal mocking
5. Checklist      → CLAUDE.md / docs entry only when 1–4 are genuinely not achievable
```

### Level 0 — Consolidate (mandatory gate, run before Level 1)

Run this check on every bug, not just ones classified as Duplicated/Divergent Logic — a fix
that only touches the call site you happened to find is the most common way "enforcement"
quietly fails to hold.

**1. Did fixing this bug require touching more than one call site**, or would a *future*
call site need the same fix repeated to stay correct? If a second caller of the same
operation can be added without inheriting the fix, the class isn't closed yet.

**2. Name the smell** (Fowler, *Refactoring*, ch. 3):
- **Shotgun Surgery** — one conceptual change requires edits scattered across many places.
- **Divergent Change** — one module/file changes for many unrelated reasons because it
  absorbed logic that belongs elsewhere.
- **Duplicated Code** — the plainest form: the same precondition copy-pasted at each caller.

**3. Consolidate to a single source of truth before enforcing anything**, using the smallest
refactoring that fits (Fowler's catalog; also Clean Code's DRY/SRP and Parnas's information
hiding — hide the invariant behind one module so callers physically cannot bypass it):
- **Extract Function** — pull the duplicated precondition into one function; make every call
  site call it.
- **Move Function** — relocate logic that's drifted into the wrong module back next to the
  state it protects.
- **Combine Functions into Class/Module** — when the same few operations keep needing the
  same setup, own that setup once instead of at each entry point.
- **Replace Function with Command / wrap the primitive** — if a lower-level primitive
  (an RPC sender, a raw setter) is directly reachable and easy to call without its
  precondition, shadow it: rename the raw import/destructure to a private name, and expose
  the *only* public-facing name in scope as the version that already does the required step.
  This is the cheapest form of "make the wrong usage unrepresentable" (poka-yoke / Josh
  Bloch's "design APIs that are hard to misuse") when a full Level 1 type change isn't
  practical — a caller would have to go out of their way to reach the unsafe primitive.
- **Introduce Parameter Object / Encapsulate Variable** — when the duplication is a group of
  values callers assemble separately instead of asking for one object that's always valid.

**4. After consolidating, re-run the ladder at the single remaining site.** Consolidation is
not itself the enforcement — it's what makes Level 1/1b/2/3 actually stick, because now there
is exactly one place to put a type constraint, a lint rule, or a test. Skipping straight to
"I wrapped it" without also asking whether Level 1 (compile-time) is now reachable at that one
site is under-enforcing; the ladder still applies after consolidation, not instead of it.

**Verify**: would a new call site added later automatically get the fix, or does the next
person have to remember to call the wrapper? If they have to remember, consolidation isn't
finished — the unsafe primitive is still exported/reachable.

### Level 1b — Type-Driven Design Gate (mandatory before writing a lint rule)

Before writing a lint rule, apply the `type-driven-design` skill to evaluate whether the
type system can eliminate this class of error entirely. A lint rule catches the pattern
after it's written; a type change makes the wrong pattern impossible to write.

Ask these questions in order. Stop at the first "yes" and implement it instead of a lint rule.

**1. Can the wrong usage be made unrepresentable?**
- Is there a *different type* for the return/value of the API that would prevent the bad pattern?
- Can a smart constructor, branded/newtype, or wrapper make the invalid state impossible to construct?
- Examples:
  - *TypeScript*: replace `id: string` with a branded `type UserId = string & { _brand: 'UserId' }` so a raw string can't be passed.
  - *Go*: replace `string` with `type UserID string` and only mint it via a constructor that validates.
  - *Kotlin*: expose `fun PageUuid.asKey(): String = value` and mark the raw accessor `@RequiresOptIn(ERROR)`.
  - *Rust*: wrap in a newtype `struct UserId(String)` with a checked constructor.

**2. Can the API be reshaped to only accept valid inputs?**
- Can the signature accept a stronger type instead of `any`/`interface{}`/`Object`?
- Can you wrap the call site in a typed helper that encodes the correct behavior?
- Examples:
  - *Go*: `func Items[T any](items []T, key func(T) string)` forces `key` to return `string`, not `any`.
  - *TypeScript*: a generic `typedItems<T>(items: T[], key: (t: T) => string)` instead of `key: (t) => unknown`.
  - *Python*: annotate with `Callable[[T], str]` and run a type checker (mypy/pyright) in CI.

**3. Can a state machine / union type prevent the transition?**
- Does the bug represent an invalid state transition (calling X before Y, using a result in the wrong phase)?
- If so, a typestate pattern or sealed/discriminated union may be the right tool (Rust typestate,
  Kotlin sealed interface, TS discriminated union, Go distinct types per phase).

**4. Can the correct path be made ergonomically dominant?**
- Even if you can't block the wrong path, can you make the right path the shortest one?
- If yes, implement it as a complement to the lint rule, not instead of it.

**Verdict table** — fill this in before proceeding to lint:

| TDD question | Answer | Evidence |
|---|---|---|
| Wrong usage unrepresentable via types? | yes / no / partial | reason |
| API reshape possible? | yes / no / partial | reason |
| State machine / union applicable? | yes / no | reason |
| Ergonomic dominant path available? | yes / no | what it looks like |

**If any answer is "yes"**: implement the type change. It replaces the lint rule — do not add both
unless the type change only partially covers the class.

**If all answers are "no" or "partial"**: proceed to lint (Level 2), but document *why* the type
system cannot close this gap in the rule's doc comment. This is the evidence that Level 1 was
genuinely evaluated, not skipped.

### Semantic/Intent → Write the failing test

Write a test that:
- Sets up the exact conditions that produced the bug
- Asserts the correct outcome
- **Must fail against the pre-fix code** — revert and run it to confirm, or reason through why it fails

```go
// Go
func TestDiscount_AppliesFloorNotCeiling(t *testing.T) {
    // Arrange: the exact inputs that produced the wrong result
    // Act
    // Assert — must fail against pre-fix code
}
```
```ts
// TypeScript
it("clamps to the floor, not the ceiling", () => { /* arrange / act / assert */ });
```
```kotlin
// Kotlin
@Test fun `clamps to the floor not the ceiling`() { /* arrange / act / assert */ }
```
```python
# Python
def test_clamps_to_floor_not_ceiling(): ...  # arrange / act / assert
```

Place it in the matching test target/source set for the package under test.

### Framework Pattern Misuse → Lint rule

1. Check whether your linter already has a rule for this pattern, then enable it:
   - *Go*: `go vet`, `staticcheck`, `golangci-lint` (enable the relevant analyzer)
   - *JS/TS*: ESLint (`eslint-plugin-react-hooks`, etc.) — flip the rule to `error`
   - *Kotlin*: detekt / Android Lint — set `active: true`
   - *Python*: ruff / flake8 / pylint — enable the rule code
2. Address existing violations, then run the linter to confirm it's wired into CI.
3. If no rule exists, write a custom one. Cheapest portable option first:
   - **`ast-grep` or `semgrep`** — a YAML/pattern rule that works across languages and runs in CI
     (see the `code-ast-grep` skill). Often the fastest path for a project-specific pattern.
   - Native custom analyzer when you need type/semantic info:
     - *Go*: a `golang.org/x/tools/go/analysis` Analyzer, wired into `golangci-lint`
     - *JS/TS*: a custom ESLint rule (`create(context) { return { CallExpression(node) {…} } }`)
     - *Kotlin*: a detekt `Rule` registered in a `RuleSetProvider`
4. **Write a test for the rule itself** — it must fire on the bad pattern and stay silent on the good one.
5. Verify by temporarily reverting the fix and confirming the linter reports the violation.

### API Contract Gap → Encode the contract in the type

Prefer in this order:
1. **Required parameter / field** — if it's omitted, it won't compile
2. **Opt-in / explicit marker** — caller must acknowledge (Kotlin `@RequiresOptIn(ERROR)`,
   Rust `unsafe`/sealed trait, TS required discriminant field)
3. **Lint rule** — flag call sites that use the API without the prerequisite step

```kotlin
// Before: contract documented but not enforced
class Recorder(val context: Context)            // caller must also request RECORD_AUDIO — easy to forget
// After: contract is a required dependency
class Recorder(val context: Context, val requestPermission: suspend () -> Boolean)
```
```go
// Before: caller must remember to call Init() first
func New() *Client { ... }
// After: the only constructor does the required setup; zero value is unusable
func New(ctx context.Context, cfg Config) (*Client, error) { ... }   // returns ready-to-use client
```
```ts
// Before: open(opts?) — easy to omit the required handle
// After: the required field is non-optional in the param type
function open(opts: { handle: FileHandle; mode: Mode }): Stream { ... }
```

### Type Safety Gap → Harden the type

- Replace nullable/optional with a non-null type where null is not a valid state
  (*Kotlin* `T?`→`T`, *TS* `T | undefined`→`T`, *Go* `*T`→`T`, *Python* `Optional[T]`→`T`).
- Replace stringly/primitive-typed values with a wrapper or enum/union
  (*Go* named type, *TS* branded type or discriminated union, *Kotlin* `value class`/`sealed`,
  *Rust* newtype/enum, *Python* `NewType`/`Enum`/`Literal`).
- Make all cases explicit and exhaustive (sealed/union + exhaustive switch with a compile-time
  `never`/`else -> error` arm).

### Integration Gap → Integration test

Write a test that:
- Instantiates **both** components — no mocking the seam itself
- Uses in-memory fakes for external dependencies (not mocks of the components under test)
- Exercises the interaction path that was broken
- Must fail against pre-fix code

### Dependency/Build Gap → Build-graph or smoke guard

When the regression came from a dependency or build change (bad transitive dep, init-time crash,
version skew), enforce at the build graph or startup, since unit tests won't see it:
- **Forbidden-dependency test**: assert a known-bad module/package is absent from the compiled graph.
  - *Go*: `go list -deps ./...` in a test, fail if a banned import path appears.
  - *JS/TS*: a test/CI step over `npm ls`/the lockfile asserting a banned package is gone.
  - *Gradle/Maven*: a dependency-verification or `forbidden` configuration rule.
- **Startup smoke test**: launch the built artifact in CI and assert it reaches a healthy state
  (catches any init-time panic/segfault, not just one dependency).
- **Version pin + checksum/lockfile verification** in CI to prevent silent skew.

## Phase 4 — Verify

For **every** enforcement added, answer: would this have caught the original bug?

| Enforcement added | Pre-fix behaviour | Verdict |
|-------------------|------------------|---------|
| New test `...` | fails ✓ / passes ✗ | catches it / insufficient |
| Lint rule `...` | fires ✓ / silent ✗ | catches it / insufficient |
| Type change `...` | doesn't compile ✓ / compiles ✗ | catches it / insufficient |
| Dep/smoke guard `...` | fails ✓ / passes ✗ | catches it / insufficient |

If any row says "insufficient", escalate to a stronger level. Do not close out until
every bug has at least one enforcement that would have caught it.

## Anti-patterns to reject

- Adding a CLAUDE.md note instead of a test — notes rot, tests don't
- Writing a test that mocks the broken component — it won't catch the regression
- Writing a custom lint rule with no test for the rule itself — rules break silently on refactors
- Stopping at "the fix is in" — the class is still alive until enforcement is in place
- **Patching only the call site you found** — if the same precondition is duplicated at other
  call sites, the bug survives there; run the Level 0 consolidation check first
