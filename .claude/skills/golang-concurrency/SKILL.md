---
name: golang-concurrency
description: Choose and apply the right Go concurrency primitive — channels, mutexes, atomics, copy-on-write, singleflight, and lock-free data structures. Use when designing concurrent access to shared state, diagnosing lock contention (paired with golang-profiling), choosing between sync.RWMutex and atomic.Pointer copy-on-write, evaluating concurrent map options (sync.Map vs xsync.MapOf), implementing singleflight request coalescing, or reaching for a lock-free queue/ring-buffer library. Covers stdlib sync/atomic, golang.org/x/sync, puzpuzpuz/xsync, Workiva/go-datastructures, and golang-design/lockfree.
paths: "**/*.go"
---

# Go Concurrency

A decision framework for concurrent access to shared state in Go, plus the specific libraries and data structures worth reaching for. Pairs with `golang-development` (general idiom) and `golang-profiling` (proving contention is real before fixing it).

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

## Rung 2-3: Typed Atomics and Copy-on-Write

**Rung 2 (single primitive)**: use a typed atomic (`atomic.Int64`, `atomic.Bool`, `atomic.Pointer[T]`) instead of raw `unsafe.Pointer` or untyped `atomic.Value`. Watch for the noCopy pitfall — these types embed a `noCopy` sentinel `go vet` flags if the containing struct is copied by value.

**Rung 3 (read-mostly struct or list)**: writers build a full new immutable value and atomically swap the pointer; readers pay one atomic load, zero lock contention. This beats `sync.RWMutex` at high core counts because `RLock()` still does an atomic increment that bounces cache lines across readers. Three shapes: `atomic.Pointer[T]` for a single uniform struct, `atomic.Value` for a multi-field snapshot whose type isn't uniform across stores, and a COW slice (`atomic.Value` + a writer-side `sync.Mutex`) for rarely-updated lists like plugin/subscriber registries.

See [Atomics and Copy-on-Write](references/atomics-and-copy-on-write.md) for the full cheat sheet and code for all three COW shapes.

---

## Rung 4: sync.Mutex / sync.RWMutex

Still correct for most code. A `sync.Mutex` is the right choice when ALL of these are true:

1. The critical section contains no I/O, no subprocess, no allocation-heavy loop.
2. The critical section runs in < 10µs in the worst case.
3. The write:read ratio is high enough that `sync.RWMutex` would add complexity without benefit.
4. `singleflight` cannot coalesce the callers (different keys, non-idempotent operations).

**Rules that actually matter**: never hold a lock across I/O; `RWMutex` only pays off when reads significantly outnumber writes on a non-trivial critical section (plain `Mutex` can win on short sections); keep critical sections to field mutation only, watching for lock-order cycles; shard the mutex once one struct serves many independent keys.

See [Mutexes and Concurrent Maps](references/mutexes-and-concurrent-maps.md) for the full rules and code.

---

## Rung 5: Concurrent Maps

Pick `sync.Map` for stable keys with read-heavy access (0 B/op at 99% reads — benchmark your workload; Go 1.24's HashTrieMap backend narrows the gap further). Pick `xsync.MapOf[K, V]` (puzpuzpuz/xsync/v4) for typed generics, higher write throughput on Go < 1.24, or when you need the structural guarantee that its internal lock can never be held across I/O (no exported `Lock()`). Pick a sharded map (`orcaman/concurrent-map/v2`, or N manual `xsync.MapOf` shards keyed by `hash(key) % N`) for extreme write-heavy, high-cardinality workloads. Never use `sync.Map` for compound transactional updates — it's only atomic per-operation.

See [Mutexes and Concurrent Maps](references/mutexes-and-concurrent-maps.md) for code for all three.

---

## golang.org/x/sync Toolkit, conc, and sync.Once

| Package | Use for |
|---|---|
| `errgroup` | Parallel work with first-error cancellation propagation — panics still crash the process |
| `sourcegraph/conc` | Same as errgroup, but panic-safe (repropagated on `Wait()`) and includes bounded pools |
| `semaphore` | Bounding concurrency (N-at-a-time worker limits) |
| `singleflight` | Collapsing duplicate concurrent calls for the same key (cache stampede prevention) |
| `sync.Once` | One-time initialization, zero lock after the first call |

Reach for `conc` over `errgroup` when goroutines call code you don't fully trust not to panic, or you want bounded concurrency without a separate `semaphore`. `singleflight`'s panic propagation fans out to every waiter on that key — wrap the inner function with `recover` if panics are possible — and `group.Forget(key)` clears a key for re-execution.

See [Concurrency Toolkit](references/concurrency-toolkit.md) for code for errgroup, conc, singleflight, and sync.Once.

---

## Rung 7: Lock-Free Queues and Ring Buffers

Only reach here after profiling shows a genuine MPMC queue is the bottleneck — never start here. Preferred: `Workiva/go-datastructures` (bounded ring buffer, blocking semantics, `Dispose()` for shutdown). Alternative: `golang-design/lockfree` (unbounded, no `Dispose()` — own your shutdown coordination). A lock-free queue is **not** a substitute for a mutex guarding mutable struct fields — that's copy-on-write (Rung 3) or `RWMutex` (Rung 4).

See [Lock-Free Structures](references/lock-free-structures.md) for code and the "what this doesn't fix" detail.

---

## Diagnosis Workflow

Don't guess at contention — prove it first:

1. `golang-profiling` skill → capture `mutex` and `block` pprof profiles under load.
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
| `sourcegraph/conc` | third-party | Panic-safe goroutine pools, bounded concurrency, `iter.Map`/`ForEach` |
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
| `golang-development` | General idiomatic Go — this skill assumes that baseline |
| `golang-profiling` | Capture and read CPU/mutex/block profiles before picking a concurrency fix |
| `code-refactoring` | Structural changes once the concurrency fix is chosen |
