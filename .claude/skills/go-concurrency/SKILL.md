---
name: go-concurrency
description: Choose and apply the right Go concurrency primitive — channels, mutexes, atomics, or lock-free data structures. Use when designing concurrent access to shared state, diagnosing lock contention (paired with go-profiling), choosing between sync.RWMutex and atomic.Pointer copy-on-write, or evaluating a lock-free queue/ring-buffer library. Covers stdlib sync/atomic, golang.org/x/sync, and third-party lock-free libraries (Workiva/go-datastructures, golang-design/lockfree).
paths: "**/*.go"
---

# Go Concurrency

A decision framework for concurrent access to shared state in Go, plus the specific libraries and data structures worth reaching for. Pairs with `go-development` (general idiom) and `go-profiling` (proving contention is real before fixing it).

## The Ladder

Stop at the first rung that holds. Don't skip to lock-free structures because they sound fast — most contention is fixed at rung 2 or 3.

1. **Do these goroutines need to share state at all?** If one goroutine can own the data and others talk to it via a channel, do that. (Go proverb: share memory by communicating.)
2. **Is it a single value — counter, flag, or pointer?** Use a typed `sync/atomic` wrapper. No mutex needed.
3. **Is it read constantly, written rarely?** Use the atomic.Pointer copy-on-write/RCU pattern (below). Readers pay one atomic load, zero lock contention.
4. **Is it a small critical section with mixed reads/writes at moderate concurrency?** Plain `sync.Mutex` or `sync.RWMutex`. This is correct for the vast majority of Go code — don't preemptively avoid it.
5. **Is it a read-mostly map keyed by a stable set of keys?** `sync.Map`.
6. **Is it a genuine high-throughput producer/consumer queue and you've profiled `sync.Mutex`/channels as the bottleneck?** Only now consider a third-party lock-free queue/ring buffer (below).

Never start at rung 6. Lock-free data structures fix a narrow problem (queue throughput under heavy MPMC contention) and are easy to misapply to a problem that's actually rung 2–4.

---

## Rung 2–3: `sync/atomic` and Copy-on-Write

Go 1.19+ has typed atomics — use these, not raw `unsafe.Pointer` or untyped `atomic.Value`:

```go
var requestCount atomic.Int64
requestCount.Add(1)

var enabled atomic.Bool
enabled.Store(true)
```

### Copy-on-write / RCU pattern

The standard fix for "many readers, occasional writer" — e.g. hot config, a status snapshot, anything read on every request and written rarely:

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

The struct behind the pointer is treated as immutable once published — writers build a full new copy, never mutate in place. This eliminates `RWMutex.RLock()`'s cache-line invalidation cost entirely, which matters because **`sync.RWMutex` does not scale on high core counts for read-heavy workloads**: every `RLock()` does an atomic increment on shared internal state, so readers across cores still contend with each other even though they're not blocking each other logically.

Worked example (see `go-profiling` for how this was found): a per-session `Instance.stateMutex sync.RWMutex` guarded mutable fields like `Status`/`Title` that were read on every `ListSessions`/`WatchSessions` call and write-locked briefly but frequently by `Pause()`/`Resume()`. `go tool pprof` on the mutex profile showed seconds of cumulative reader wait time attributed to the writer's unlock call. If the read path only needs a consistent snapshot (not the latest possible value), swapping the hot fields to an `atomic.Pointer[InstanceSnapshot]` removes the contention without touching the write path's correctness.

---

## Rung 4: `sync.Mutex` / `sync.RWMutex`

Still correct for most code. Rules that actually matter:

- **Never hold a lock across I/O** (disk, network, git, subprocess exec). Acquire, mutate in-memory state, release, *then* do I/O. Holding a lock across a syscall turns a microsecond critical section into a multi-second one under any disk/CPU pressure.
- **`RWMutex` only pays off when reads significantly outnumber writes** and the critical section is non-trivial. For short critical sections, plain `Mutex` can outperform `RWMutex` because `RWMutex` has higher per-op overhead — measure before assuming `RWMutex` is the fast choice.
- **Keep critical sections to field mutation only.** If you need to call another method that might itself lock something, check for lock-order cycles first (the classic deadlock source).
- **Shard the mutex if one struct serves many independent keys.** A single `map[string]*Instance` protected by one `RWMutex` serializes all sessions behind one lock; N independent per-key mutexes (or a sharded map) scales better than one global lock once N is large.

---

## Rung 5: `sync.Map`

Use only when:
- Keys are stable (mostly inserted once, rarely deleted), and
- Reads vastly outnumber writes, and
- You don't need to iterate-and-mutate atomically (no compound "read N keys, then write" transactions).

If you need transactional multi-key updates, a regular `map` behind a `Mutex` is simpler and easier to reason about than fighting `sync.Map`'s semantics.

---

## `golang.org/x/sync` Toolkit

Not lock-free, but the standard answer for common coordination patterns before reaching for raw channels/mutexes:

| Package | Use for |
|---|---|
| `errgroup` | Parallel work with first-error cancellation propagation |
| `semaphore` | Bounding concurrency (N-at-a-time worker limits) |
| `singleflight` | Collapsing duplicate concurrent calls (cache stampede prevention) |

```go
eg, ctx := errgroup.WithContext(ctx)
for _, item := range items {
    eg.Go(func() error { return process(ctx, item) })
}
if err := eg.Wait(); err != nil { return err }
```

---

## Rung 6: Lock-Free Queues and Ring Buffers

Only reach here after profiling (`go-profiling`'s mutex/block profile) shows a genuine MPMC queue is the bottleneck — not a guess. Two libraries are worth using; avoid the long tail of smaller, less-maintained lock-free packages.

### `Workiva/go-datastructures` (preferred default)

CAS-based bounded MPMC ring buffer, production-proven (used in real high-throughput pipelines). Blocking semantics with explicit `Dispose()` to unblock waiters on shutdown — this matters in practice, since a pure spin-CAS queue with no dispose path leaks goroutines on shutdown.

```go
import "github.com/Workiva/go-datastructures/queue"

rb := queue.NewRingBuffer(1024) // capacity must be a power of 2

// producer
err := rb.Put(item) // blocks if full

// consumer
item, err := rb.Get() // blocks if empty

// shutdown: unblocks any goroutine stuck in Put/Get
rb.Dispose()
```

Use when: you have genuine multiple producers and/or multiple consumers, need backpressure (bounded capacity), and need clean shutdown semantics. This is the right default when a lock-free structure is actually warranted.

### `golang-design/lockfree`

Michael-Scott lock-free queue/stack/ring buffer. Good alternative when you specifically need an *unbounded* lock-free queue or a lock-free stack (Workiva's package doesn't offer a stack). Smaller surface area, no dispose/shutdown primitive — you own that coordination yourself.

```go
import "github.com/golang-design/lockfree"

q := lockfree.NewQueue()
q.Enqueue(item)
v := q.Dequeue() // nil if empty — check before use
```

### Why not hand-roll one, and why not grab the first GitHub result

Hand-rolled lock-free structures are a common source of subtle bugs: the ABA problem, and unsafe memory reclamation are easy to get wrong even for experienced engineers. Go's GC actually makes CAS-based structures *safer* here than in C/C++ (no need for hazard pointers — the GC won't free a node while a pointer to it is reachable), which is part of why the two libraries above can exist safely. But that safety doesn't transfer to a structure you write yourself without the same scrutiny.

Smaller/newer lock-free libraries (low stars, single maintainer, no CI, last commit irrelevant to your Go version) are not worth the risk for what is usually a solved problem — pick `Workiva/go-datastructures` or `golang-design/lockfree` rather than searching for alternatives.

### What lock-free structures do *not* fix

A lock-free queue is a data structure for passing items between producers and consumers. It is **not** a substitute for a mutex guarding a mutable struct's fields. If your actual problem is "many goroutines read/write fields on a shared object," the fix is the copy-on-write pattern (rung 3) or a plain `RWMutex` (rung 4) — restructuring that object into queued commands processed by a single owning goroutine (the only way a queue *would* fix it) is a much bigger design change than the problem usually warrants. Reach for that restructuring only if you're already committed to an actor-model design for other reasons.

---

## Diagnosis Workflow

Don't guess at contention — prove it first:

1. `go-profiling` skill → capture `mutex` and `block` pprof profiles while the slowdown is happening.
2. `go tool pprof -top -cum mutex.prof` — find which call path holds locks waiters are queued behind.
3. Identify the rung: is the contended thing a single value (rung 2), a read-mostly struct (rung 3), or a genuine queue (rung 6)?
4. Apply the narrowest fix for that rung. Re-profile to confirm the contention moved or disappeared.

---

## Anti-Patterns

- **Reaching for a lock-free queue before profiling.** Adds a dependency and complexity for a problem you haven't confirmed exists.
- **Using a lock-free queue to guard struct fields.** Wrong tool — see above.
- **Holding a mutex across I/O** (disk, network, subprocess, git). Release before blocking calls.
- **One global `RWMutex` over a large map/collection of independent entities.** Shard it, or move to per-entity locks/atomics.
- **`sync.Map` for compound transactional updates.** It only gives you atomicity per-operation, not across a read-then-write sequence.
- **Unbounded goroutine-per-request with no semaphore/errgroup bound.** Use `x/sync/semaphore` or a worker pool to cap concurrency.

---

## Related Skills

| Skill | When to apply |
|---|---|
| `go-development` | General idiomatic Go — this skill assumes that baseline |
| `go-profiling` | Capture and read CPU/mutex/block profiles before picking a concurrency fix |
| `code-refactoring` | Structural changes once the concurrency fix is chosen |
