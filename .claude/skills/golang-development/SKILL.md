---
name: golang-development
description: Apply idiomatic, well-structured Go development practices. Use when writing, reviewing, or refactoring Go code. Covers Go Proverbs, concurrency fundamentals, type-system maximization (generics, embedding, iota, receivers), primitive-obsession fixes, and anti-patterns based on Effective Go, Go Code Review Comments, and Go Proverbs. For error handling, naming, interfaces/structs, project layout, testing, and design patterns, see the dedicated `golang-error-handling`, `golang-naming`, `golang-structs-interfaces`, `golang-project-layout`, `golang-testing`, and `golang-design-patterns` skills.
paths: "**/*.go"
---

# Go Development

Apply idiomatic Go principles from Effective Go, the Go Code Review Comments wiki, and Go Proverbs to all code in this session.

## Core Principles (Go Proverbs)

Each proverb is paired with the concrete pattern that implements it. Full code for every entry below lives in [Go Proverbs](references/go-proverbs.md).

1. **Don't communicate by sharing memory; share memory by communicating** — pass ownership of data through a channel instead of sharing a pointer multiple goroutines mutate under a mutex. A mutex is still right for protecting one genuinely shared structure (e.g. an in-memory cache); channels model transferring ownership, mutexes model serialized access to a structure that stays put.
2. **The bigger the interface, the weaker the abstraction** — keep interfaces to 1–3 methods, defined at the consumer. See `golang-structs-interfaces`.
3. **Make the zero value useful** — design a type so `var x T` is immediately usable with no constructor call.
4. **Errors are values — handle them, don't just check them** — program *with* errors instead of checking at every call site; Rob Pike's `errWriter` pattern absorbs an error across several operations and checks it once. See `golang-error-handling` for wrapping/sentinel conventions.
5. **A little copying is better than a little dependency** — copy a small, self-contained helper into the package that needs it rather than importing a dependency for one function.
6. **Don't panic — use errors for normal control flow** — return an error for expected failures; reserve `panic`/`recover` for a top-level boundary that must survive a handler panic.
7. **Concurrency is not parallelism** — concurrency is a program *structure* correct regardless of core count; parallelism is whether units actually run simultaneously, which `GOMAXPROCS` and the runtime decide.
8. **Channels orchestrate; mutexes serialize** — a pipeline of stages needs a channel; a single shared structure needs a mutex. Match the tool to the actual shape of the problem.
9. **`interface{}` / `any` says nothing** — a generic constraint (`[T int | float64]`) documents what a function operates on; `any` documents nothing.
10. **Gofmt's style is no one's favorite, yet gofmt is everyone's favorite** — run `gofmt -w .` before every commit (see "Tooling" below); one non-negotiable standard removes a whole class of style debate.
11. **Clear is better than clever** — prefer the straightforward version over a compact one-liner; explicit branches read faster than they're saved by cleverness.
12. **Reflection is never clear** — prefer an explicit type switch or generics over `reflect` whenever the type set is known at compile time; reserve `reflect` for genuine serialization/framework code.
13. **Escape hatches: syscall, cgo, and unsafe must be guarded and isolated** — guard `syscall`/`cgo` files with a `//go:build` tag naming the dependency; treat cgo as a foreign-function boundary kept small and isolated behind a plain Go interface; confine `unsafe` to one narrow, documented wrapper.
14. **Don't just check errors, handle them gracefully** — handling means the caller gets a degraded-but-useful result where one is available (e.g. serve a cached value on upstream failure), not just a propagated failure.
15. **Design the architecture, name the components, document the details** — package boundaries and names *are* the architecture documentation; name packages by what they provide, not `util`/`common`/`helpers`.
16. **Documentation is for users** — write doc comments from the caller's perspective (what it does, when it errors), not a narration of the implementation.

---

> For error creation/wrapping/inspection conventions, apply the `golang-error-handling` skill.
> For interface and struct design, apply the `golang-structs-interfaces` skill.
> For naming conventions, apply the `golang-naming` skill.
> For project/directory layout, apply the `golang-project-layout` skill.

## Concurrency

Always pass `context.Context` as the first parameter for I/O or goroutine-spawning functions:
```go
func (s *Service) Process(ctx context.Context, req Request) (Result, error)
```

Always defer cancel immediately:
```go
ctx, cancel := context.WithTimeout(parent, 5*time.Second)
defer cancel()
```

Select on cancellation in every blocking goroutine:
```go
select {
case <-ctx.Done():
    return ctx.Err()
case result := <-ch:
    return result
}
```

Use `errgroup` for parallel work with error propagation:
```go
eg, ctx := errgroup.WithContext(ctx)
for _, item := range items {
    item := item  // capture loop variable
    eg.Go(func() error { return process(ctx, item) })
}
if err := eg.Wait(); err != nil { return err }
```

- **Channels** for signaling, coordination, passing ownership
- **Mutexes** for protecting shared data structures
- **Prefer synchronous APIs** — let callers add concurrency; avoids goroutine leaks

---

> For table-driven tests, testify, mocking, and test naming, apply the `golang-testing` skill.

## Anti-Patterns to Avoid

**Global mutable state** — use dependency injection; pass dependencies through a constructor:
```go
type App struct{ db *Database }
func NewApp(db *Database) *App { return &App{db: db} }
```

**`init()` abuse** — limit to driver/plugin registration only; real initialization belongs in `main()` or constructors with proper error handling.

**Interface pollution** — never create interfaces with 8+ methods; small interfaces compose better. This is one symptom of a broader problem — see "Concrete-First Design" below.

**Goroutine variable capture** — rebind the loop variable per iteration before use in a closure:
```go
for _, item := range items { item := item; go func() { process(item) }() }
```

**`import .`** — never; always qualify identifiers with package name.

---

## Concrete-First Design (Avoiding Leaky Abstractions)

LLM-generated Go code characteristically reproduces Java/Spring-shaped abstractions —
interfaces-first, Repository/Manager/Service layering, getter/setter pairs — because that
style is over-represented in training data relative to idiomatic Go. These abstractions
don't mesh with Go's data model and make code harder to maintain, not easier. Before adding
any new type, interface, or layer, check it against the smell on the left; do the thing on
the right instead.

| Smell (don't) | Do instead |
|---|---|
| Interface with exactly one implementation, no near-term second one | Use the concrete type directly. Extract an interface only when a second real implementation exists or is imminent |
| Interface defined in the same package as its implementation | Define it in the **consuming** package, containing only the methods that consumer needs |
| Getter/setter pair wrapping a field with no logic | Export the field directly (`u.Name`, not `u.GetName()`) unless the accessor does real validation or computation |
| `Manager`/`Handler`/`Processor`/`Service` type that only forwards calls | Delete the wrapper; call the wrapped type directly. Only keep a wrapping type if it adds behavior (caching, locking, metrics) at that layer |
| Generic function/type where a concrete type or a plain loop would do | Write the concrete version first. Generalize only when 2+ real call sites need the identical logic |
| Struct-wraps-struct-wraps-struct with no new exported behavior per layer | Collapse to one struct. Each layer must earn its existence by adding behavior, not by relaying calls |

Run this check specifically on code an LLM just generated, not just human-written diffs —
it's the fastest way to catch this drift before it compounds.

---

> For CPU and memory performance analysis, apply the `golang-profiling` skill.

## Tooling (Run Before Every Commit)

```bash
go vet ./...          # Compiler-level issues
gofmt -w .            # Format (non-negotiable)
staticcheck ./...     # High-precision static analysis
go test -race ./...   # Race detection
golangci-lint run     # Meta-linter
```

Recommended golangci-lint linters: `staticcheck`, `gosimple`, `govet`, `errcheck`, `gosec`, `revive`, `misspell`, `unconvert`, `exhaustive` (enforces switch exhaustiveness over `iota`-based enums).

---

> For Repository, Service Layer, Middleware/Decorator, Strategy, Functional Options, and other
> Go-idiomatic design patterns, apply the `golang-design-patterns` skill (and `design-patterns`
> for the underlying GoF/PoEAA theory).

---

## Maximizing Go's Type System

Beyond primitive obsession (see "Type-Driven Design" below), these are the core Go-specific
techniques for getting real leverage out of the type system. Full code for each: [Type System Patterns](references/type-system-patterns.md).

- **Pointer vs value receivers — pick one semantic per type.** Value receivers copy; pointer receivers share and can mutate. Use pointer receivers once a type has mutable state or is expensive to copy; use value receivers for small, immutable, comparable types. Never mix the two on the same type.
- **Struct embedding for composition, never inheritance.** Embedding promotes an embedded type's methods and fields to the outer type, but the embedded type has no idea it's embedded. If a promoted method ever needs overriding, that's a sign inheritance-shaped thinking crept in — prefer a named field with explicit forwarding instead.
- **`iota` for typed enums.** Go has no `enum` keyword; a distinct type plus `iota` is the idiomatic replacement for magic strings or ints — the distinct type is what makes an invalid value a compile-time error.
- **Generics: constraints document intent.** Pick the narrowest constraint the function needs — `comparable` for `==`/`!=`, a custom constraint like `Ordered` for `<`/`>`. Don't reach for generics when a concrete type or a five-line loop covers the one call site you have — see "Concrete-First Design" above.
- **Struct tags at serialization boundaries.** Struct tags describe the wire format; keep them at the boundary and parse into a domain type (see Type-Driven Design below) immediately after unmarshaling — the domain model itself stays tag-free.

---

## Type-Driven Design (Avoiding Primitive Obsession)

Apply these techniques to encode invariants directly into Go's type system so illegal states
are unrepresentable. Full cross-language coverage (Python, Java) lives in the
`type-driven-design` skill; full Go code for every technique below is in
[Type-Driven Design Patterns](references/type-driven-design-patterns.md).

- **Newtypes** — give domain concepts their own type (`type UserID string`, never `type UserID = string`) so the compiler catches parameter mixups.
- **Phantom types** — a generic type parameter that exists only at compile time (`type ID[T any] string`) gives cross-entity ID safety: `UserID` and `OrderID` become distinct types even though both are strings underneath.
- **Smart constructors** — an unexported underlying type plus an exported parsing function (`ParseEmail`, `NewUserID`) so holding the type proves the value was already validated, from a format check down to a simple non-empty check.
- **Sum types (closed state sets)** — an unexported marker method seals the set of implementations; a `switch` on the concrete type enforces exhaustive handling instead of comparing magic strings.
- **Value objects** — immutable, self-validating, equality-by-value types for domain concepts like money.
- **Refinement types** — a type that carries proof of a constraint (e.g. non-emptiness) so downstream code needs no defensive check.
- **Typestate pattern** — encode valid state transitions with phantom generics (`Connection[Closed]` vs `Connection[Open]`) so an invalid transition is a compile error, not a runtime check.
- **Parse at the boundary, trust internally** — validate and parse exactly once at the HTTP/CLI/message boundary; pass the proven type through the rest of the call chain with no re-validation.

**Signs you need this section:** magic string comparisons (`status == "pending"`), functions
that take two `string` parameters that could be swapped, validation logic repeated across
multiple functions, `nil` pointer panics from missing construction checks.

---

## Checklist for Every Go PR

- [ ] Every error is handled — none silently dropped
- [ ] Every goroutine has a documented exit condition
- [ ] Every I/O function accepts and respects `ctx context.Context`
- [ ] Interfaces have ≤3 methods; large ones are split
- [ ] No speculative interfaces, forwarding-only wrapper types, or no-op getters/setters (see Concrete-First Design)
- [ ] Domain concepts use newtypes/value objects/sum types, not raw `string`/`int`/`float64` (see Type-Driven Design)
- [ ] Acronyms consistently cased; receiver names consistent across all methods
- [ ] `go vet`, `staticcheck`, `golangci-lint` pass clean
- [ ] `go test -race ./...` passes

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `golang-error-handling` | Error creation, wrapping, and inspection conventions |
| `golang-naming` | Naming conventions for packages, types, and identifiers |
| `golang-structs-interfaces` | Interface and struct design |
| `golang-project-layout` | Project and directory layout |
| `golang-testing` | Table-driven tests, testify, mocking, test naming |
| `golang-design-patterns` | Repository, Service Layer, Strategy, Functional Options, and other Go-idiomatic patterns |
| `golang-profiling` | Profile CPU, memory, goroutines, or benchmark a Go binary |
| `code-refactoring` | Structural refactors after identifying anti-patterns |
| `code-debugging` | Systematic investigation of a Go bug or panic |
| `security-review` | OWASP audit or secrets scan on Go code |
| `github-actions-debugging` | Debug CI failures for Go tests or linting |
| `lean-agent-loop` | Parallelize pre-commit tool passes (vet, staticcheck, golangci-lint, test -race) and iterate until all green |
