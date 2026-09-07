# GoF Creational Patterns

### Factory Method / Abstract Factory
**Problem**: Create objects without hardcoding concrete types; decouple creation from use.
```go
func NewReader(format string) Reader {
    switch format {
    case "json": return &JSONReader{}
    case "xml":  return &XMLReader{}
    default:     return &TextReader{}
    }
}
```
- **Use when**: multiple concrete types implement the same interface; creation logic varies by context
- **Avoid when**: only one concrete type exists (just use a direct constructor)
- **Go note**: return interfaces, not concrete types; constructor functions are more idiomatic than factory objects

### Builder / Functional Options
**Problem**: Construct complex objects step-by-step, managing many optional parameters cleanly.
```go
// Idiomatic Go: functional options
type Option func(*Server)

func WithTimeout(d time.Duration) Option { return func(s *Server) { s.timeout = d } }
func WithLogger(l Logger) Option         { return func(s *Server) { s.logger = l } }

func NewServer(addr string, opts ...Option) *Server {
    s := &Server{addr: addr}
    for _, o := range opts { o(s) }
    return s
}
```
- **Use when**: many optional/conditional parameters; complex validation at construction time
- **Avoid when**: 1–2 parameters (use a direct constructor)
- **Go note**: functional options (`func New(opts ...Option)`) are more idiomatic than a fluent builder chain

### Singleton
**Problem**: Ensure exactly one instance with thread-safe initialization.
```go
var once sync.Once
var instance *DB

func GetDB() *DB {
    once.Do(func() { instance = connect() })
    return instance
}
```
- **Use when**: coordinating a shared resource that genuinely must be singular
- **Avoid when**: dependency injection can pass the instance instead (almost always preferred — singletons hurt testability)
- **Go note**: treat `sync.Once` as the implementation mechanism, not a design goal
