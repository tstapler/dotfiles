# Typed Atomics and Copy-on-Write Patterns

## Rung 2: Typed Atomics (Go 1.19+)

Use these, not raw `unsafe.Pointer` or untyped `atomic.Value`, for single primitive values:

```go
var requestCount atomic.Int64
requestCount.Add(1)

var enabled atomic.Bool
enabled.Store(true)
```

### Atomic Primitives Cheat Sheet

| Need | Type | Notes |
|------|------|-------|
| Integer counter | `atomic.Int64` | Clean API, no noCopy issue in normal struct embedding |
| Boolean flag | `atomic.Bool` | Replaces `sync.Mutex` + `bool` |
| Typed pointer | `atomic.Pointer[T]` | Generic; replaces `unsafe.Pointer` |
| Any value | `atomic.Value` | Must always Store same concrete type |
| Counter in a copied struct | `int64` + `atomic.LoadInt64` | Avoid `atomic.Int64` when the struct is copied (noCopy) |

**noCopy pitfall**: `atomic.Int64`, `atomic.Bool`, etc. embed a `noCopy` sentinel. If the containing struct is passed by value or used in a slice-of-structs, `go vet` will flag it. Use raw `int64` + `atomic.LoadInt64/StoreInt64` when the struct is copied, or store an `*atomic.Int64` pointer instead.

## Rung 3: Copy-on-Write Patterns

The standard fix for "many readers, occasional writer." Writers build a full new value and swap the pointer atomically — readers pay one atomic load, zero lock contention.

### 3a. `atomic.Pointer[T]` — Single-Value COW

The cleanest option when the shared value is a single struct. Eliminates `RWMutex.RLock()`'s cache-line invalidation cost entirely, which matters because **`sync.RWMutex` does not scale on high core counts for read-heavy workloads**: every `RLock()` does an atomic increment on shared internal state, so readers across cores contend with each other even though they're not blocking each other logically.

```go
type Config struct {
    Timeout time.Duration
    Limits  map[string]int
}

type Service struct {
    cfg atomic.Pointer[Config]
}

func (s *Service) Config() *Config {
    return s.cfg.Load() // single atomic load, no lock, no cache-line bounce
}

func (s *Service) UpdateConfig(c *Config) {
    s.cfg.Store(c) // build the new value fully, then swap the pointer
}
```

The struct behind the pointer is treated as immutable once published — writers build a full new copy, never mutate in place. Callers may hold a pointer to the old config while a new one is being stored; that is correct and expected.

### 3b. atomic.Value — Multi-Field Snapshot

Use when multiple fields must be read consistently and the type is not uniform across all stores. Prefer `atomic.Pointer[T]` (3a) when the type is uniform — it avoids interface boxing overhead and is more type-safe.

```go
type authResult struct {
    ok        bool
    checkedAt time.Time
}

type Service struct {
    auth atomic.Value // stores authResult; nil = not yet checked
}

func (s *Service) isAuthFresh() (bool, bool) {
    v := s.auth.Load()
    if v == nil {
        return false, false
    }
    r := v.(authResult)
    return r.ok, time.Since(r.checkedAt) < 5*time.Minute
}

func (s *Service) setAuth(ok bool) {
    s.auth.Store(authResult{ok: ok, checkedAt: time.Now()})
}
```

**Rules**:
- The stored type must be the same across all `Store()` calls (Go panics otherwise).
- Never modify fields of the loaded struct — it may be concurrently loaded elsewhere.
- Use `CompareAndSwap` (Go 1.17+) when you need to update only if the value hasn't changed.

### 3c. COW Slice — Rarely-Updated Lists

Use for plugin registries, subscriber lists, poller instance lists — where readers iterate frequently and writes are occasional:

```go
type Poller struct {
    instances atomic.Value // stores []Instance (immutable snapshot)
    writeMu   sync.Mutex   // serializes concurrent writers only
}

func (p *Poller) loadInstances() []Instance {
    v := p.instances.Load()
    if v == nil {
        return nil
    }
    return v.([]Instance)
}

func (p *Poller) addInstance(inst Instance) {
    p.writeMu.Lock()
    defer p.writeMu.Unlock()
    cur := p.loadInstances()
    next := make([]Instance, len(cur)+1)
    copy(next, cur)
    next[len(cur)] = inst
    p.instances.Store(next)
}

func (p *Poller) pollOnce() {
    for _, inst := range p.loadInstances() { // lock-free
        go p.pollInstance(inst)
    }
}
```
