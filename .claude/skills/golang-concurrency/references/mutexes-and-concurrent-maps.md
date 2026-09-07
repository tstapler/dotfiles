# Mutexes and Concurrent Maps

## Rung 4: sync.Mutex / sync.RWMutex

Still correct for most code. A `sync.Mutex` is the right choice when ALL of these are true:

1. The critical section contains no I/O, no subprocess, no allocation-heavy loop.
2. The critical section runs in < 10µs in the worst case.
3. The write:read ratio is high enough that `sync.RWMutex` would add complexity without benefit.
4. `singleflight` cannot coalesce the callers (different keys, non-idempotent operations).

### Rules that actually matter

- **Never hold a lock across I/O** — acquire, mutate in-memory state, release, *then* do I/O.
- **`RWMutex` only pays off when reads significantly outnumber writes** and the critical section is non-trivial. For short critical sections, plain `Mutex` can outperform `RWMutex` because `RWMutex` has higher per-op overhead. At high core counts, `RWMutex` reader contention is still real (see the `atomic.Pointer[T]` COW pattern in [Atomics and Copy-on-Write](atomics-and-copy-on-write.md)).
- **Keep critical sections to field mutation only.** If you need to call another method that might itself lock something, check for lock-order cycles first.
- **Shard the mutex if one struct serves many independent keys.** N independent per-key mutexes (or a sharded map — see below) scales better than one global lock once N is large.

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
