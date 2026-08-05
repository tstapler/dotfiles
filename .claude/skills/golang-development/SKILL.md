---
name: golang-development
description: Apply idiomatic, well-structured Go development practices. Use when writing, reviewing, or refactoring Go code. Covers Go Proverbs, concurrency fundamentals, type-system maximization (generics, embedding, iota, receivers), primitive-obsession fixes, and anti-patterns based on Effective Go, Go Code Review Comments, and Go Proverbs. For error handling, naming, interfaces/structs, project layout, testing, and design patterns, see the dedicated `golang-error-handling`, `golang-naming`, `golang-structs-interfaces`, `golang-project-layout`, `golang-testing`, and `golang-design-patterns` skills.
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

### Concurrency is not parallelism

Concurrency is a program *structure* — independent, composable units of work — that's
correct regardless of how many cores run it. Parallelism is whether those units actually
execute simultaneously, which the Go runtime decides based on `GOMAXPROCS` and available
cores:

```go
// Structuring work as goroutines makes it concurrent; whether it runs in
// parallel is a runtime/scheduling decision, not something the code asserts.
runtime.GOMAXPROCS(runtime.NumCPU())
```

### Channels orchestrate; mutexes serialize

The `Pipeline` example above moves ownership of a `Job` between stages — that's
orchestration. The `Counter` example's `sync.Mutex` protects one persistent structure many
callers reach into — that's serialization. Reach for whichever matches the actual shape of
the problem: a pipeline of stages needs a channel; a single shared structure needs a mutex.

### `interface{}` / `any` says nothing

A generic constraint says something concrete about `T`; `any` says nothing at all about what
it holds:

```go
// The constraint documents exactly what Sum can operate on
func Sum[T int | float64](nums []T) T {
    var total T
    for _, n := range nums {
        total += n
    }
    return total
}
```

### Gofmt's style is no one's favorite, yet gofmt is everyone's favorite

Run `gofmt -w .` before every commit (see "Tooling" below) — one non-negotiable formatting
standard removes an entire class of style debate from every review.

### Clear is better than clever

Prefer the straightforward version over a compact one-liner — self-documenting names and
explicit branches read faster than they're saved by cleverness:

```go
func IsBusinessDay(t time.Time) bool {
    switch t.Weekday() {
    case time.Saturday, time.Sunday:
        return false
    default:
        return true
    }
}
```

### Reflection is never clear

Prefer an explicit type switch or generics over `reflect` whenever the set of types is known
at compile time. Reserve `reflect` for genuine serialization/framework code (`encoding/json`,
ORMs) where the type set truly isn't known ahead of time:

```go
func Describe(v any) string {
    switch x := v.(type) {
    case int:
        return fmt.Sprintf("int: %d", x)
    case string:
        return fmt.Sprintf("string: %q", x)
    default:
        return fmt.Sprintf("unknown: %v", x)
    }
}
```

### Escape hatches: syscall, cgo, and unsafe must be guarded and isolated

Guard any `syscall`- or `cgo`-dependent file with a `//go:build` tag naming exactly what it
depends on:

```go
//go:build linux

package platform

func setNonblocking(fd int) error {
    return syscall.SetNonblock(fd, true)
}
```

Treat a cgo-touching package as a foreign-function boundary, not ordinary Go — keep it small
and isolated behind a plain Go interface the rest of the codebase depends on instead of the
cgo package directly. Apply the same isolation to `unsafe`: confine it to one narrow,
documented wrapper so the invariant it relies on lives in exactly one place:

```go
// unsafe usage isolated behind one narrow, documented wrapper
func bytesToString(b []byte) string {
    return unsafe.String(unsafe.SliceData(b), len(b))
}
```

### Don't just check errors, handle them gracefully

Checking an error is `if err != nil { return err }`. Handling it gracefully means the caller
gets a degraded-but-useful result where one is available, not just a propagated failure:

```go
func (s *Service) GetUser(ctx context.Context, id string) (*User, error) {
    u, err := s.upstream.Get(ctx, id)
    if err != nil {
        if cached, ok := s.cache.Get(id); ok {
            return cached, nil // degrade gracefully instead of failing the caller outright
        }
        return nil, fmt.Errorf("get user %s: %w", id, err)
    }
    return u, nil
}
```

### Design the architecture, name the components, document the details

Package boundaries and names *are* the architecture documentation — see "Project Structure"
and "Naming" below. Keep them deliberate (name packages by what they provide) rather than
defaulting to `util`/`common`/`helpers`, which document nothing.

### Documentation is for users

Write doc comments from the caller's perspective — what it does and when it errors — not a
narration of the implementation:

```go
// ParseConfig reads and validates the YAML config file at path.
// It returns an error if the file is missing or fails schema validation.
func ParseConfig(path string) (*Config, error) {
    // ...
}
```

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
techniques for getting real leverage out of the type system.

### Pointer vs Value Receivers — Pick One Semantic Per Type

Value receivers copy; pointer receivers share and can mutate. Choose one per type and use it
for every method on that type — never mix them:

```go
// Value semantics: Point is small and safe to copy
type Point struct{ X, Y int }
func (p Point) Add(other Point) Point { return Point{p.X + other.X, p.Y + other.Y} }

// Pointer semantics: Buffer holds mutable, potentially large state
type Buffer struct{ data []byte }
func (b *Buffer) Write(p []byte) (int, error) { b.data = append(b.data, p...); return len(p), nil }
```

Rule of thumb: value receivers for small, immutable, comparable types; pointer receivers once
the type has mutable state or is expensive to copy.

### Struct Embedding for Composition, Never Inheritance

Embedding promotes an embedded type's methods and fields to the outer type, but the embedded
type has no idea it's embedded — this is composition, not a base class:

```go
type Reader struct{ r io.Reader }
type Logger struct{ log *slog.Logger }

// LoggingReader embeds both — Read() and Log() are promoted onto it, but
// neither Reader nor Logger knows LoggingReader exists
type LoggingReader struct {
    Reader
    Logger
}
```

If a promoted method ever needs overriding to "fix" the embedded type's behavior, that's the
signal that inheritance-shaped thinking crept in — prefer holding the type as a named field and
forwarding only the specific calls you need, rather than embedding for the override.

### `iota` for Typed Enums

Go has no `enum` keyword — a distinct type plus `iota` is the idiomatic replacement for magic
strings or ints:

```go
type Level int

const (
    LevelDebug Level = iota
    LevelInfo
    LevelWarn
    LevelError
)

func (l Level) String() string {
    return [...]string{"debug", "info", "warn", "error"}[l]
}
```

The distinct `Level` type — not a bare `int` — is what makes this a compile-time guarantee:
nothing can pass an arbitrary int where a `Level` is expected, the same protection a newtype
gives (see "Type-Driven Design" below).

### Generics: Constraints Document Intent

A type parameter's constraint is documentation the compiler enforces — pick the narrowest
constraint that expresses what the function actually needs:

```go
type Ordered interface {
    ~int | ~int64 | ~float64 | ~string
}

func Max[T Ordered](a, b T) T {
    if a > b {
        return a
    }
    return b
}
```

Reach for `comparable` when the function only needs `==`/`!=` (map keys, `slices.Contains`),
and a custom constraint like `Ordered` when it needs `<`/`>`. Don't reach for generics at all
when a concrete type or a five-line loop covers the one call site you actually have — see
"Concrete-First Design" above.

### Struct Tags at Serialization Boundaries

Struct tags describe how a type maps to an external wire format — keep them at the boundary,
not leaking into domain logic:

```go
type UserDTO struct {
    ID    string `json:"id"`
    Email string `json:"email"`
}
```

Parse a `UserDTO` into a domain `Email`/`UserID` (see "Type-Driven Design" below) immediately
after unmarshaling. Tags describe the wire format; the domain model stays tag-free.

---

## Type-Driven Design (Avoiding Primitive Obsession)

Apply these techniques to encode invariants directly into Go's type system so illegal states
are unrepresentable. Full cross-language coverage (Python, Java) lives in the
`type-driven-design` skill — this section is the Go-specific implementation of each.

### Newtypes

Give domain concepts their own type instead of passing raw primitives, so the compiler
catches parameter mixups:

```go
type UserID string
type AccountID string
type Cents int64

func Transfer(from, to AccountID, amount Cents) error { /* ... */ return nil }
```

Use `type Foo string` (a distinct type), never `type Foo = string` (an alias — no
type-checking protection).

### Phantom Types (Cross-Entity ID Safety)

```go
type ID[T any] string // T only exists at compile time, never at runtime

type User struct{}
type Order struct{}

type UserID = ID[User]
type OrderID = ID[Order]

func GetUser(id UserID) (*User, error) { return nil, nil }
// GetUser(orderID) is a compile error — UserID and OrderID are distinct types
```

### Smart Constructors

An unexported underlying type plus an exported parsing function — holding the type proves
the value was already validated. The validation itself can be a format check:

```go
type Email string // representation is unexported; can't be constructed directly from another package

func ParseEmail(s string) (Email, error) {
    if !emailRegex.MatchString(s) {
        return "", fmt.Errorf("invalid email %q", s)
    }
    return Email(s), nil
}

// Callers holding an Email never need to re-validate it
func SendWelcome(to Email) { /* ... */ }
```

...or just a presence check, which is all a non-empty ID needs — the type still stops an
empty string, and a distinct type per entity still stops parameter mixups:

```go
type UserID string

func NewUserID(s string) (UserID, error) {
    if s == "" {
        return "", errors.New("user ID cannot be empty")
    }
    return UserID(s), nil
}

// A UserID can only exist via NewUserID — an empty one can never reach this function
func GetUser(id UserID) (*User, error) { /* ... */ return nil, nil }
```

### Sum Types (Closed State Sets)

An unexported marker method seals the set of implementations; a `switch` on the concrete
type enforces exhaustive handling instead of comparing magic strings:

```go
type OrderStatus interface{ orderStatus() }

type Pending   struct{}
type Confirmed struct{}
type Shipped   struct{}
type Cancelled struct{}

func (Pending) orderStatus()   {}
func (Confirmed) orderStatus() {}
func (Shipped) orderStatus()   {}
func (Cancelled) orderStatus() {}

func (o *Order) Confirm() error {
    if _, ok := o.Status.(Pending); !ok {
        return fmt.Errorf("can only confirm a pending order, got %T", o.Status)
    }
    o.Status = Confirmed{}
    return nil
}
```

### Value Objects

Immutable, self-validating, equality-by-value types for domain concepts like money — see
`Money` in `type-driven-design` for the full pattern:

```go
type Money struct {
    cents    int64
    currency string
}

func NewMoney(amount float64, currency string) (Money, error) {
    if amount < 0 {
        return Money{}, errors.New("amount cannot be negative")
    }
    return Money{cents: int64(math.Round(amount * 100)), currency: currency}, nil
}

func (m Money) Add(other Money) (Money, error) {
    if m.currency != other.currency {
        return Money{}, errors.New("currency mismatch")
    }
    return Money{cents: m.cents + other.cents, currency: m.currency}, nil
}
```

### Refinement Types

A type that carries proof of a constraint, such as non-emptiness, so downstream code needs
no defensive check:

```go
type NonEmptySlice[T any] struct{ items []T }

func NewNonEmptySlice[T any](items ...T) (NonEmptySlice[T], error) {
    if len(items) == 0 {
        return NonEmptySlice[T]{}, errors.New("must not be empty")
    }
    return NonEmptySlice[T]{items: items}, nil
}

func (s NonEmptySlice[T]) Head() T { return s.items[0] } // safe — proven non-empty
```

### Typestate Pattern

Encode valid state transitions with phantom generics, so an invalid transition is a compile
error rather than a runtime check:

```go
type Open   struct{}
type Closed struct{}

type Connection[State any] struct{ addr string }

func NewConnection(addr string) Connection[Closed] { return Connection[Closed]{addr} }

func (c Connection[Closed]) Open() (Connection[Open], error) {
    return Connection[Open]{c.addr}, nil // dial happens here
}
func (c Connection[Open]) Query(sql string) (*Rows, error) { return nil, nil }
func (c Connection[Open]) Close() Connection[Closed]        { return Connection[Closed]{c.addr} }
// c.Query(sql) is a compile error if c is Connection[Closed]
```

### Parse at the Boundary, Trust Internally

Validate and parse exactly once at the HTTP/CLI/message boundary; pass the proven type
(`Email`, `UserID`, `Money`) through the rest of the call chain with no re-validation.

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
