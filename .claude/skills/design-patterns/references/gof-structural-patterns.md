# GoF Structural Patterns

### Adapter
**Problem**: Bridge two incompatible interfaces without modifying either.
```go
type PaymentProcessor interface { Process(amount float64) error }

type PaymentAdapter struct{ gateway *LegacyGateway }
func (a *PaymentAdapter) Process(amount float64) error { return a.gateway.Pay(amount) }
```
- **Use when**: integrating third-party/legacy code with an incompatible interface
- **Avoid when**: you can modify the source; adds indirection for no benefit

### Decorator / Middleware
**Problem**: Add behavior (logging, auth, caching) to objects/functions dynamically without modifying them.
```go
func Logging(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        log.Printf("%s %s", r.Method, r.URL)
        next.ServeHTTP(w, r)
    })
}
```
- **Use when**: cross-cutting concerns (logging, auth, caching, rate-limiting); composing behaviors at runtime
- **Avoid when**: decorator chain becomes too deep to reason about
- **Go note**: HTTP middleware is the canonical idiomatic form — function returning function is more natural than object wrapping object

### Facade
**Problem**: Provide a single simplified interface to a complex subsystem.
```go
// Well-designed package API is Go's natural facade
func (s *Store) FindUser(ctx context.Context, id int) (*User, error) {
    if u, ok := s.cache.Get(id); ok { return u, nil }
    u, err := s.repo.GetByID(ctx, id)
    if err != nil { return nil, err }
    s.cache.Set(id, u)
    return u, nil
}
```
- **Use when**: clients need one entry point to a complex set of collaborators
- **Avoid when**: facade becomes as complex as the subsystem; hiding things doesn't simplify them

### Proxy
**Problem**: Control access to an object — lazy init, auth checks, logging, remote calls.
- **Use when**: expensive resource that should be created lazily; transparent access control
- **Go note**: often implemented as middleware or a struct that wraps the real type and implements the same interface

### Composite
**Problem**: Treat individual objects and tree-structured compositions uniformly.
```go
type Node interface { Size() int64 }

type File struct{ size int64 }
func (f *File) Size() int64 { return f.size }

type Dir struct{ children []Node }
func (d *Dir) Size() int64 {
    var total int64
    for _, c := range d.children { total += c.Size() }
    return total
}
```
- **Use when**: tree structures (file systems, UI component trees, expression trees)
- **Go note**: a slice of interface types is the idiomatic composite
