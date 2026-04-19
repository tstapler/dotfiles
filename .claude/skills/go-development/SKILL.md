---
name: go-development
description: Apply idiomatic, well-structured Go development practices. Use when writing, reviewing, or refactoring Go code. Covers error handling, interfaces, concurrency, testing, naming, project structure, and anti-patterns based on Effective Go, Go Code Review Comments, and Go Proverbs.
---

# Go Development

Apply idiomatic Go principles from Effective Go, the Go Code Review Comments wiki, and Go Proverbs to all code in this session.

## Core Principles (Go Proverbs)

- Don't communicate by sharing memory; share memory by communicating
- The bigger the interface, the weaker the abstraction
- Make the zero value useful
- Errors are values — handle them, don't just check them
- A little copying is better than a little dependency
- Don't panic — use errors for normal control flow

---

## Error Handling

Always return errors as the last value. Use early returns — no `else` after an `if err != nil` block.

```go
f, err := os.Open(path)
if err != nil {
    return fmt.Errorf("open config %s: %w", path, err)
}
defer f.Close()
```

- Wrap with `%w` to preserve chain: `fmt.Errorf("read user %d: %w", id, err)`
- Inspect with `errors.Is(err, ErrNotFound)` and `errors.As(err, &target)`
- Sentinel errors for expected conditions: `var ErrNotFound = errors.New("not found")`
- Custom error types implement `Error() string` and optionally `Unwrap() error`
- Error strings: lowercase, no trailing punctuation, include context
- Never silently drop errors — `_ = f.Close()` requires a documented reason

---

## Interfaces

- Define interfaces in the **consuming** package, not the producer
- Keep interfaces small (1–3 methods): `Reader`, `Writer`, `Closer`
- Single-method interfaces use the `-er` suffix: `Stringer`, `Formatter`
- Verify interface satisfaction at compile time: `var _ io.Writer = (*MyType)(nil)`
- Avoid `interface{}` / `any` unless truly necessary

```go
// Good: small interface defined where it's used
type Fetcher interface {
    Fetch(ctx context.Context, id string) (*Item, error)
}
```

---

## Naming

| Context | Convention | Example |
|---------|-----------|---------|
| Packages | lowercase, single word | `bufio`, `httputil` |
| Exported | PascalCase | `ServeHTTP`, `ParseURL` |
| Unexported | camelCase | `maxRetries`, `parseToken` |
| Acronyms | consistent casing | `userID`, `HTTPServer`, `xmlParser` |
| Receivers | 1–2 letters, consistent | `c` for Client, `f` for File |
| Loop vars | scope-proportional | `i` for 2 lines; `index` for 20 lines |

- Avoid `util`, `common`, `helpers`, `misc` package names
- Avoid `me`, `this`, `self` as receiver names
- Be consistent — if any method uses `*T`, all should use `*T`

---

## Project Structure

```
cmd/myapp/main.go       # Thin entry point, delegates to internal/
internal/               # Private code — compiler enforces no external import
  app/                  # Application logic
  store/                # Data access
pkg/                    # Public library code (only if genuinely reusable)
go.mod
go.sum
```

- `cmd/` should be minimal — delegate to `internal/`
- `internal/` enforces boundaries; the compiler prevents external imports
- Don't create `pkg/` unless you have genuine external consumers

---

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

## Testing

Table-driven tests are the Go standard:
```go
func TestParse(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        want    int
        wantErr bool
    }{
        {"valid", "42", 42, false},
        {"invalid", "abc", 0, true},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := Parse(tt.input)
            if (err != nil) != tt.wantErr {
                t.Fatalf("wantErr=%v, got err=%v", tt.wantErr, err)
            }
            if got != tt.want {
                t.Errorf("got %d, want %d", got, tt.want)
            }
        })
    }
}
```

- `t.Run` for subtests — run individually with `go test -run TestParse/valid`
- `t.Cleanup` for resource teardown (works correctly with `t.Parallel`)
- `t.Helper()` in assertion helpers so errors point to the caller's line
- `t.TempDir()` for temporary files — auto-cleaned after test
- Always `go test -race ./...` to catch data races
- Prefer stdlib `testing` over testify for simple assertions

---

## Anti-Patterns to Avoid

**Global mutable state** — use dependency injection:
```go
// Bad: var db *Database
// Good:
type App struct{ db *Database }
func NewApp(db *Database) *App { return &App{db: db} }
```

**`init()` abuse** — limit to driver/plugin registration only; real initialization belongs in `main()` or constructors with proper error handling.

**Interface pollution** — never create interfaces with 8+ methods; small interfaces compose better.

**Goroutine variable capture:**
```go
// Bad: all goroutines share the same `item`
for _, item := range items { go func() { process(item) }() }

// Good:
for _, item := range items { item := item; go func() { process(item) }() }
```

**`import .`** — never; always qualify identifiers with package name.

---

## Tooling (Run Before Every Commit)

```bash
go vet ./...          # Compiler-level issues
gofmt -w .            # Format (non-negotiable)
staticcheck ./...     # High-precision static analysis
go test -race ./...   # Race detection
golangci-lint run     # Meta-linter
```

Recommended golangci-lint linters: `staticcheck`, `gosimple`, `govet`, `errcheck`, `gosec`, `revive`, `misspell`, `unconvert`.

---

## Design Patterns

When structuring Go code, apply patterns from the `design-patterns` skill. Key patterns most relevant to Go:

- **Repository** — data access abstraction; define interface in domain, implement in infrastructure
- **Service Layer** — orchestrate use cases; no business logic here, that belongs in domain objects
- **Value Object** — immutable domain concepts (`Money`, `EmailAddress`) with value semantics
- **Domain Model vs Transaction Script** — rich domain model for complex logic; transaction script for simple CRUD
- **Middleware / Decorator** — cross-cutting concerns (logging, auth, caching) via `func(Handler) Handler`
- **Strategy** — swappable algorithms via function types, not one-method interfaces
- **Functional Options** — preferred Go form of Builder for structs with many optional fields

Avoid applying patterns for their own sake — use them when the recurring problem they solve is actually present.

---

## Type-Driven Design

Apply techniques from the `type-driven-design` skill to encode invariants directly into Go's type system.

**Core Go techniques:**
- `type UserID string` — newtype (never `= string` alias); prevents parameter mixups at compile time
- Phantom types: `type ID[T any] string` — `ID[User]` and `ID[Order]` are incompatible
- Smart constructors: unexported type + `func ParseEmail(s string) (Email, error)` — holding the type proves validity
- Sum types: unexported marker interface (`orderStatus()`) + distinct structs per state
- Typestate pattern: `Connection[Open]` vs `Connection[Closed]` — invalid transitions are compile errors
- Parse at the HTTP/CLI boundary; pass proven types (`Email`, `UserID`, `Money`) into the application layer

**Signs you need this skill:** magic string comparisons (`status == "pending"`), functions that take two `string` parameters that could be swapped, validation logic repeated across multiple functions, `nil` pointer panics from missing construction checks.

---

## Checklist for Every Go PR

- [ ] Every error is handled — none silently dropped
- [ ] Every goroutine has a documented exit condition
- [ ] Every I/O function accepts and respects `ctx context.Context`
- [ ] Interfaces have ≤3 methods; large ones are split
- [ ] Acronyms consistently cased; receiver names consistent across all methods
- [ ] `go vet`, `staticcheck`, `golangci-lint` pass clean
- [ ] `go test -race ./...` passes
