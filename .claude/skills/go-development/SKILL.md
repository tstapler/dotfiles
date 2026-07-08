---
name: go-development
description: Apply idiomatic, well-structured Go development practices. Use when writing, reviewing, or refactoring Go code. Covers error handling, interfaces, concurrency, testing, naming, project structure, and anti-patterns based on Effective Go, Go Code Review Comments, and Go Proverbs.
paths: "**/*.go"
---

# Go Development

Apply idiomatic Go principles from Effective Go, the Go Code Review Comments wiki, and Go Proverbs to all code in this session.

## Core Principles (Go Proverbs)

Each proverb below is paired with the concrete pattern that implements it.

### Don't communicate by sharing memory; share memory by communicating

Pass ownership of data to the next goroutine through a channel, instead of sharing a pointer
that multiple goroutines read/write under a mutex. The goroutine that receives a value off
the channel is its sole owner until it forwards the value again — no goroutine ever touches
the same data concurrently, so no lock is needed for that data:

```go
type Job struct {
    ID   string
    Data []byte
}

// Ownership of each Job transfers through the channel — the goroutine that
// receives it is the only one that touches it until it sends the Result on.
func Pipeline(ctx context.Context, jobs <-chan Job) <-chan Result {
    results := make(chan Result)
    go func() {
        defer close(results)
        for job := range jobs {
            select {
            case results <- process(job):
            case <-ctx.Done():
                return
            }
        }
    }()
    return results
}
```

A mutex is still the right tool for a different problem: protecting concurrent access to one
genuinely shared data structure (e.g. an in-memory cache many goroutines read and write).
Channels model transferring ownership between stages; mutexes model serialized access to a
structure that stays put. Reach for whichever matches the actual shape of the problem.

### The bigger the interface, the weaker the abstraction

Keep interfaces to 1–3 methods, defined at the consumer — see "Interfaces" below for the
full guidance and example.

### Make the zero value useful

Design a type so `var x T` is immediately usable with no constructor call:

```go
type Counter struct {
    mu    sync.Mutex // zero value is a valid, ready-to-use mutex
    count int        // zero value 0 is a valid starting count
}

func (c *Counter) Inc() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.count++
}

var c Counter // ready to use immediately — no NewCounter() needed
c.Inc()
```

### Errors are values — handle them, don't just check them

Program *with* errors instead of only checking them at every call site. Rob Pike's canonical
pattern absorbs an error across several operations and checks it exactly once:

```go
// errWriter absorbs the first error across many writes, checked once at the end
type errWriter struct {
    w   io.Writer
    err error
}

func (ew *errWriter) write(buf []byte) {
    if ew.err != nil {
        return
    }
    _, ew.err = ew.w.Write(buf)
}

func WriteHeader(w io.Writer, title string) error {
    ew := &errWriter{w: w}
    ew.write([]byte("# " + title + "\n"))
    ew.write([]byte("---\n"))
    return ew.err // checked exactly once, not after every write
}
```

See "Error Handling" below for wrapping and sentinel-error conventions.

### A little copying is better than a little dependency

Copy a small, self-contained helper into the package that needs it rather than importing a
whole dependency for one function:

```go
// Copied in rather than pulling in a full retry/backoff library for one function.
func backoff(attempt int) time.Duration {
    d := time.Duration(1<<attempt) * 100 * time.Millisecond
    if d > 5*time.Second {
        d = 5 * time.Second
    }
    return d
}
```

### Don't panic — use errors for normal control flow

Return an error for any expected failure condition. Reserve `panic`/`recover` for genuinely
unrecoverable situations, such as converting a handler panic into a controlled response at a
process boundary instead of crashing the whole service:

```go
func Divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, errors.New("divide by zero")
    }
    return a / b, nil
}

// The one legitimate place to reach for recover(): a top-level boundary that
// must stay up even if a handler panics.
func RecoverMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        defer func() {
            if rec := recover(); rec != nil {
                log.Printf("panic recovered: %v", rec)
                http.Error(w, "internal error", http.StatusInternalServerError)
            }
        }()
        next.ServeHTTP(w, r)
    })
}
```

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

- **Don't design with interfaces, discover them** (Rob Pike) — start concrete; extract an interface only when a second real implementation exists or is imminent, not for hypothetical future flexibility
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

> For CPU and memory performance analysis, apply the `go-profiling` skill.

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
- [ ] No speculative interfaces, forwarding-only wrapper types, or no-op getters/setters (see Concrete-First Design)
- [ ] Acronyms consistently cased; receiver names consistent across all methods
- [ ] `go vet`, `staticcheck`, `golangci-lint` pass clean
- [ ] `go test -race ./...` passes

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `go-profiling` | Profile CPU, memory, goroutines, or benchmark a Go binary |
| `code-refactoring` | Structural refactors after identifying anti-patterns |
| `code-debugging` | Systematic investigation of a Go bug or panic |
| `security-review` | OWASP audit or secrets scan on Go code |
| `github-actions-debugging` | Debug CI failures for Go tests or linting |
| `lean-agent-loop` | Parallelize pre-commit tool passes (vet, staticcheck, golangci-lint, test -race) and iterate until all green |
