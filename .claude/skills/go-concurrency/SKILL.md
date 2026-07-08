---
name: go-concurrency
description: Choose and apply the right Go concurrency primitive — channels, mutexes, atomics, copy-on-write, singleflight, and lock-free data structures. Use when designing concurrent access to shared state, diagnosing lock contention (paired with go-profiling), choosing between sync.RWMutex and atomic.Pointer copy-on-write, evaluating concurrent map options (sync.Map vs xsync.MapOf), implementing singleflight request coalescing, or reaching for a lock-free queue/ring-buffer library. Covers stdlib sync/atomic, golang.org/x/sync, puzpuzpuz/xsync, Workiva/go-datastructures, and golang-design/lockfree.
paths: "**/*.go"
---

# Go Concurrency

A decision framework for concurrent access to shared state in Go, plus the specific libraries and data structures worth reaching for. Pairs with `go-development` (general idiom) and `go-profiling` (proving contention is real before fixing it).

---

## Core Principle

> **Never hold a mutex across I/O.**
> Any lock held during a network call, git subprocess, database query, or file read
> serializes all concurrent callers for the full duration of that I/O. Find it, kill it.

---

## The Ladder

Stop at the first rung that holds. Don't skip to lock-free structures because they sound fast — most contention is fixed at rung 2 or 3.

1. **Do these goroutines need to share state at all?** If one goroutine can own the data and others talk to it via a channel, do that. (Go proverb: share memory by communicating.)
2. **Is it a single value — counter, flag?** Use a typed `sync/atomic` wrapper. No mutex needed.
3. **Is it a struct or pointer read constantly, written rarely?** Use the copy-on-write/RCU pattern — `atomic.Pointer[T]` for a single struct, `atomic.Value` for a multi-field snapshot, or a COW slice for rarely-updated lists. Readers pay one atomic load, zero lock contention.
4. **Is it a small critical section with mixed reads/writes at moderate concurrency?** Plain `sync.Mutex` or `sync.RWMutex`. This is correct for the vast majority of Go code — don't preemptively avoid it.
5. **Is it a concurrent map?** Pick `sync.Map` (stable keys, read-heavy), `xsync.MapOf` (typed, higher write throughput on Go < 1.24), or a sharded map (extreme write-heavy + high key cardinality).
6. **Duplicate concurrent requests for the same expensive operation?** `singleflight.Group` — coalesces N identical in-flight calls into 1.
7. **Is it a genuine high-throughput producer/consumer queue and you've profiled `sync.Mutex`/channels as the bottleneck?** Only now consider a third-party lock-free queue/ring buffer.

Never start at rung 7. Lock-free data structures fix a narrow problem and are easy to misapply.

---

## Decision Tree

```
What kind of shared state?
│
├── Single primitive (int64, bool, uint32)?
│   └── atomic.Int64 / atomic.Bool / atomic.Uint32
│
├── Single pointer to struct, read on every request, written rarely?
│   └── atomic.Pointer[T] (Go 1.19+) — single atomic load, zero lock
│
├── Multiple fields that must be read consistently (config, auth state, snapshot)?
│   └── atomic.Value storing an IMMUTABLE snapshot struct
│       → Readers call Load(); writers build a new struct and call Store()
│       → Never mutate the stored struct in place after Store()
│
├── Rarely-modified list (plugin registry, subscriber list, poller instances)?
│   └── COW slice via atomic.Value + writeMu to serialize writers
│
├── One-time initialization?
│   └── sync.Once — guaranteed single execution, zero lock after first call
│
├── Concurrent map?
│   ├── Write-rarely / read-often (cache, registry, ETag store):
│   │   └── sync.Map — lock-free reads in the steady state
│   ├── Typed values, moderate writes, or Go < 1.24:
│   │   └── xsync.MapOf[K, V] (puzpuzpuz/xsync/v4) — fine-grained sharded locking
│   │       → Use .Compute() for CAS-style atomic updates
│   │       → Structurally impossible to hold its internal lock across I/O
│   └── Extremely write-heavy, high key cardinality:
│       └── Sharded map: N xsync.MapOf shards, key routed by hash(key) % N
│
├── Duplicate concurrent requests for the same expensive operation?
│   └── singleflight.Group — coalesces N identical in-flight calls into 1
│       → Combine with atomic.Value/sync.Map cache: check cache first, miss → singleflight
│
├── Parallel work with first-error cancellation?
│   └── errgroup.WithContext (golang.org/x/sync)
│
├── Limit concurrency to N at a time?
│   └── semaphore (golang.org/x/sync)
│
├── Truly complex multi-field update where atomics don't compose?
│   └── sync.Mutex (last resort)
│       → Critical section must be < 10µs (no I/O, no subprocess, no allocation loop)
│       → Prefer sync.RWMutex if read:write ratio > 5:1
│       → Document WHY a mutex was unavoidable
│
└── Genuine MPMC queue bottleneck, confirmed by profiling?
    └── Workiva/go-datastructures (bounded, blocking, Dispose()) or golang-design/lockfree (unbounded)
```

---

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

---

## Rung 3: Copy-on-Write Patterns

The standard fix for "many readers, occasional writer." Writers build a full new value and swap the pointer atomically — readers pay one atomic load, zero lock contention.

### 3a. atomic.Pointer[T] — Single-Value COW

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

---

## Rung 4: sync.Mutex / sync.RWMutex

Still correct for most code. A `sync.Mutex` is the right choice when ALL of these are true:

1. The critical section contains no I/O, no subprocess, no allocation-heavy loop.
2. The critical section runs in < 10µs in the worst case.
3. The write:read ratio is high enough that `sync.RWMutex` would add complexity without benefit.
4. `singleflight` cannot coalesce the callers (different keys, non-idempotent operations).

### Rules that actually matter

- **Never hold a lock across I/O** — acquire, mutate in-memory state, release, *then* do I/O.
- **`RWMutex` only pays off when reads significantly outnumber writes** and the critical section is non-trivial. For short critical sections, plain `Mutex` can outperform `RWMutex` because `RWMutex` has higher per-op overhead. At high core counts, `RWMutex` reader contention is still real (see Rung 3a).
- **Keep critical sections to field mutation only.** If you need to call another method that might itself lock something, check for lock-order cycles first.
- **Shard the mutex if one struct serves many independent keys.** N independent per-key mutexes (or a sharded map — see Rung 5) scales better than one global lock once N is large.

---

## Rung 5: Concurrent Maps

### sync.Map

Use when keys are stable (mostly inserted once, rarely deleted) and reads vastly outnumber writes.

```go
var cache sync.Map

type cacheEntry struct {
    result string
    expiry time.Time
}

func get(key string) (string, bool) {
    v, ok := cache.Load(key)
    if !ok {
        return "", false
    }
    e := v.(cacheEntry)
    if time.Now().After(e.expiry) {
        cache.Delete(key)
        return "", false
    }
    return e.result, true
}
```

Allocation profile (directional — benchmark your workload): 0 B/op at 99% reads, 3 B/op at 90%, 9 B/op at 75%.

> **Go 1.24 note**: `sync.Map` uses a HashTrieMap backend that improves write performance. On Go 1.24+, `sync.Map` may be sufficient for mixed workloads without reaching for `xsync.MapOf`. Benchmark your actual workload.

Do NOT use `sync.Map` for compound transactional updates — it only gives atomicity per-operation, not across a read-then-write sequence.

### xsync.MapOf (puzpuzpuz/xsync/v4)

Use when you need generic type safety and/or higher write throughput than `sync.Map` on Go < 1.24, or when the no-exported-lock structural guarantee matters.

```go
import "github.com/puzpuzpuz/xsync/v4"

type ETagCache struct {
    store *xsync.MapOf[string, etagEntry]
}

func NewETagCache() *ETagCache {
    return &ETagCache{store: xsync.NewMapOf[string, etagEntry]()}
}

// Atomic conditional update — no separate load+store race:
func (c *ETagCache) UpdateETag(key, newETag string) {
    c.store.Compute(key, func(e etagEntry, loaded bool) (etagEntry, xsync.ComputeOp) {
        if !loaded {
            return etagEntry{}, xsync.CancelOp
        }
        ne := e
        ne.etag = newETag
        return ne, xsync.UpdateOp
    })
}
```

**Key property**: `xsync.MapOf` has no exported `Lock()`/`Unlock()` — structurally impossible to hold its internal lock across I/O.

> **Benchmark caveat**: xsync benchmarks are authored by the library's creator. Run your own before treating xsync as categorically faster than `sync.Map`.

### Sharded Maps

For extremely write-heavy workloads with high key cardinality:

```go
import cmap "github.com/orcaman/concurrent-map/v2"

m := cmap.New[string]()
m.Set("key", "value")
v, ok := m.Get("key")
```

Or shard manually: N `xsync.MapOf` shards, key routed by `hash(key) % N`.

---

## golang.org/x/sync Toolkit

| Package | Use for |
|---|---|
| `errgroup` | Parallel work with first-error cancellation propagation |
| `semaphore` | Bounding concurrency (N-at-a-time worker limits) |
| `singleflight` | Collapsing duplicate concurrent calls (cache stampede prevention) |

### errgroup

```go
eg, ctx := errgroup.WithContext(ctx)
for _, item := range items {
    eg.Go(func() error { return process(ctx, item) })
}
if err := eg.Wait(); err != nil { return err }
```

### singleflight — Request Coalescing

```go
import "golang.org/x/sync/singleflight"

type Service struct {
    cache sync.Map
    group singleflight.Group
}

func (s *Service) getOrFetch(key string) (string, error) {
    if v, ok := s.cache.Load(key); ok {
        return v.(string), nil
    }
    v, err, _ := s.group.Do(key, func() (any, error) {
        result, err := expensiveFetch(key)
        if err == nil {
            s.cache.Store(key, result)
        }
        return result, err
    })
    if err != nil {
        return "", err
    }
    return v.(string), nil
}
```

**Panic propagation (production critical)**: If the executing goroutine panics, the panic is propagated to ALL waiting goroutines for that key. Wrap the inner function with `recover` if panics are possible.

**Cache invalidation**: Call `group.Forget(key)` to allow the next call for that key to re-execute.

**At extreme scale**: `singleflight.Group` uses a single global mutex over the key map. Under very high goroutine concurrency, consider `github.com/tarndt/shardedsingleflight`.

---

## sync.Once

```go
var (
    instance *Service
    once     sync.Once
)

func GetService() *Service {
    once.Do(func() { instance = &Service{...} })
    return instance
}
```

---

## Rung 7: Lock-Free Queues and Ring Buffers

Only reach here after profiling shows a genuine MPMC queue is the bottleneck.

### Workiva/go-datastructures (preferred)

Bounded MPMC ring buffer with blocking semantics and `Dispose()` for clean shutdown:

```go
import "github.com/Workiva/go-datastructures/queue"

rb := queue.NewRingBuffer(1024) // capacity must be power of 2
rb.Put(item)   // blocks if full
rb.Get()       // blocks if empty
rb.Dispose()   // unblocks all waiters — call on shutdown
```

### golang-design/lockfree

Unbounded lock-free queue/stack. No `Dispose()` — own your shutdown coordination:

```go
import "github.com/golang-design/lockfree"

q := lockfree.NewQueue()
q.Enqueue(item)
v := q.Dequeue() // nil if empty
```

### What lock-free structures do NOT fix

A lock-free queue passes items between producers and consumers. It is **not** a substitute for a mutex guarding mutable struct fields. If many goroutines read/write fields on a shared object, the fix is copy-on-write (rung 3) or `RWMutex` (rung 4) — not a lock-free queue.

---

## Diagnosis Workflow

Don't guess at contention — prove it first:

1. `go-profiling` skill → capture `mutex` and `block` pprof profiles under load.
2. `go tool pprof -top -cum mutex.prof` — find which call path holds locks waiters queue behind.
3. Identify the rung: single value (2), read-mostly struct (3), concurrent map (5), or queue (7)?
4. Apply the narrowest fix. Re-profile to confirm contention moved.

---

## Anti-Patterns

```go
// ❌ Lock held across HTTP call — serializes all callers for full I/O duration
mu.Lock()
resp, err := http.Get(url)
mu.Unlock()

// ❌ Lock held across git subprocess
mu.Lock()
out, _ := exec.Command("git", "status").Output()
mu.Unlock()

// ❌ Thundering herd — all misses fetch independently; use singleflight
mu.RLock(); entry, ok := cache[key]; mu.RUnlock()
if !ok { entry = expensiveFetch(key) }

// ❌ sync.Mutex for a read-dominated map — use sync.Map or xsync.MapOf
type Registry struct { mu sync.Mutex; m map[string]Handler }

// ❌ Mutating a value loaded from atomic.Value — concurrent readers hold the same pointer
v := val.Load().(MyStruct)
v.Field = x // RACE
val.Store(v)

// ❌ One global RWMutex over a large map of independent entities — shard it
type SessionManager struct { mu sync.RWMutex; sessions map[string]*Session }

// ❌ Unbounded goroutine-per-request — use errgroup or semaphore
for _, req := range requests {
    go handle(req)
}
```

---

## Libraries Reference

| Library | Import | Use Case |
|---------|--------|----------|
| `sync/atomic` | stdlib | Primitive atomics (Int64, Bool, Pointer, Value) |
| `sync` | stdlib | Mutex, RWMutex, Map, Once, Pool |
| `golang.org/x/sync/errgroup` | x/sync | Parallel work with first-error cancellation |
| `golang.org/x/sync/semaphore` | x/sync | N-at-a-time concurrency bounding |
| `golang.org/x/sync/singleflight` | x/sync | Request coalescing / cache stampede prevention |
| `puzpuzpuz/xsync/v4` | third-party | Typed lock-free map (`xsync.MapOf`) |
| `orcaman/concurrent-map/v2` | third-party | Sharded map for write-heavy workloads |
| `Workiva/go-datastructures` | third-party | Bounded MPMC ring buffer with `Dispose()` |
| `golang-design/lockfree` | third-party | Unbounded lock-free queue/stack |

---

## Related Skills

| Skill | When to apply |
|---|---|
| `go-development` | General idiomatic Go — this skill assumes that baseline |
| `go-profiling` | Capture and read CPU/mutex/block profiles before picking a concurrency fix |
| `code-refactoring` | Structural changes once the concurrency fix is chosen |
