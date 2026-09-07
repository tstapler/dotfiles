# Preventing Struct Copies with `noCopy`

Some structs must never be copied after first use (e.g., those containing a mutex, a channel, or internal pointers). Embed a `noCopy` sentinel to make `go vet` catch accidental copies:

```go
// noCopy may be added to structs which must not be copied after first use.
// See https://pkg.go.dev/sync#noCopy
type noCopy struct{}

func (*noCopy) Lock()   {}
func (*noCopy) Unlock() {}

type ConnPool struct {
    noCopy noCopy
    mu     sync.Mutex
    conns  []*Conn
}
```

`go vet` reports an error if a `ConnPool` value is copied (passed by value, assigned, etc.). This is the same technique the standard library uses for `sync.WaitGroup`, `sync.Mutex`, `strings.Builder`, and others.

Always pass these structs by pointer:

```go
// Good
func process(pool *ConnPool) { ... }

// Bad — go vet will flag this
func process(pool ConnPool) { ... }
```
