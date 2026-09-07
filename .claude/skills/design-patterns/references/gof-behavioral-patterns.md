# GoF Behavioral Patterns

### Strategy
**Problem**: Swap interchangeable algorithms at runtime without changing the calling code.
```go
// Idiomatic: use a function type, not a Strategy interface
type SortFunc func([]int)

type Sorter struct{ fn SortFunc }
func (s *Sorter) Sort(data []int) { s.fn(data) }
```
- **Use when**: multiple algorithms for the same task chosen at runtime; replacing large if-else chains
- **Go note**: function types are more idiomatic than a one-method strategy interface

### Observer
**Problem**: Notify multiple dependents when an object's state changes.
```go
// Idiomatic: channels
type Bus struct{ listeners []chan Event }

func (b *Bus) Publish(e Event) {
    for _, ch := range b.listeners {
        go func(c chan Event) { c <- e }(ch)
    }
}
```
- **Use when**: decoupling event producers from consumers; one-to-many notifications
- **Go note**: channels and goroutines replace traditional observer objects

### Command
**Problem**: Encapsulate a request as an object for queueing, scheduling, or undo.
```go
// Idiomatic: first-class functions
type Command func() error

queue := []Command{
    func() error { return step1() },
    func() error { return step2() },
}
for _, cmd := range queue { if err := cmd(); err != nil { return err } }
```
- **Use when**: undo/redo, command queues, macro recording
- **Go note**: closures eliminate the need for Command objects in most cases

### Template Method
**Problem**: Define an algorithm's skeleton; let implementations fill in specific steps.
```go
type Processor interface {
    Validate([]byte) error
    Parse([]byte) (interface{}, error)
    Process(interface{}) error
}

func Run(p Processor, data []byte) error {
    if err := p.Validate(data); err != nil { return err }
    parsed, err := p.Parse(data)
    if err != nil { return err }
    return p.Process(parsed)
}
```
- **Use when**: multiple related types share an algorithm structure but differ in steps
- **Go note**: Go uses interfaces + a free function (like `Run` above) rather than abstract base classes

### Chain of Responsibility
**Problem**: Pass a request along a handler chain until one handles it.
```go
// Idiomatic: function composition
type Middleware func(http.Handler) http.Handler

func Chain(h http.Handler, mws ...Middleware) http.Handler {
    for i := len(mws) - 1; i >= 0; i-- { h = mws[i](h) }
    return h
}
```
- **Use when**: validation pipelines, middleware stacks, multi-stage processing
- **Go note**: HTTP middleware IS chain of responsibility — function composition is the idiomatic form

### State
**Problem**: Alter an object's behavior based on its internal state; eliminate large state-checking conditionals.
```go
type State interface{ Next(ctx *FSM) State }

type Pending struct{}
func (s *Pending) Next(f *FSM) State {
    if f.ready { return &Running{} }
    return s
}
```
- **Use when**: distinct behaviors per state with clear transition rules; replacing large state-flag conditionals
- **Avoid when**: 2–3 states (a simple switch is clearer)
