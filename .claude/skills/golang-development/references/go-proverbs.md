# Go Proverbs — Full Patterns and Code

Full code examples for each Go Proverb summarized in the main SKILL.md's "Core Principles" section.

## Don't communicate by sharing memory; share memory by communicating

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

## The bigger the interface, the weaker the abstraction

Keep interfaces to 1–3 methods, defined at the consumer — see the `golang-structs-interfaces`
skill for the full guidance and example.

## Make the zero value useful

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

## Errors are values — handle them, don't just check them

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

See the `golang-error-handling` skill for wrapping and sentinel-error conventions.

## A little copying is better than a little dependency

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

## Don't panic — use errors for normal control flow

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

## Concurrency is not parallelism

Concurrency is a program *structure* — independent, composable units of work — that's
correct regardless of how many cores run it. Parallelism is whether those units actually
execute simultaneously, which the Go runtime decides based on `GOMAXPROCS` and available
cores:

```go
// Structuring work as goroutines makes it concurrent; whether it runs in
// parallel is a runtime/scheduling decision, not something the code asserts.
runtime.GOMAXPROCS(runtime.NumCPU())
```

## Channels orchestrate; mutexes serialize

The `Pipeline` example above moves ownership of a `Job` between stages — that's
orchestration. The `Counter` example's `sync.Mutex` protects one persistent structure many
callers reach into — that's serialization. Reach for whichever matches the actual shape of
the problem: a pipeline of stages needs a channel; a single shared structure needs a mutex.

## `interface{}` / `any` says nothing

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

## Gofmt's style is no one's favorite, yet gofmt is everyone's favorite

Run `gofmt -w .` before every commit (see "Tooling" in the main skill) — one non-negotiable
formatting standard removes an entire class of style debate from every review.

## Clear is better than clever

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

## Reflection is never clear

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

## Escape hatches: syscall, cgo, and unsafe must be guarded and isolated

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

## Don't just check errors, handle them gracefully

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

## Design the architecture, name the components, document the details

Package boundaries and names *are* the architecture documentation — see "Project Structure"
and "Naming" in the main skill. Keep them deliberate (name packages by what they provide)
rather than defaulting to `util`/`common`/`helpers`, which document nothing.

## Documentation is for users

Write doc comments from the caller's perspective — what it does and when it errors — not a
narration of the implementation:

```go
// ParseConfig reads and validates the YAML config file at path.
// It returns an error if the file is missing or fails schema validation.
func ParseConfig(path string) (*Config, error) {
    // ...
}
```
