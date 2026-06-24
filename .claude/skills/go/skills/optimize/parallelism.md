---
description: Go fearless concurrency — decision tree and patterns for atomic operations, lock-free data structures, singleflight, and avoiding mutex contention in high-throughput services.
prompt: |
  # go:parallelism — Fearless Concurrency in Go

  You are advising on concurrency design for a Go service. Apply the decision tree and
  patterns below to choose the right primitive, then implement it correctly.

  The user's request is provided in the command arguments. If no request is given, ask
  for: what shared state exists, how many goroutines read vs write, and whether I/O occurs
  near the lock site.

  ---

  ## Core Principle

  > **Never hold a mutex across I/O.**
  > Any lock held during a network call, git subprocess, database query, or file read
  > serializes all concurrent callers for the full duration of that I/O. Find it, kill it.

  A mutex is a last resort — reach for it only after all other options are exhausted.
  Prefer: atomic operations > lock-free structures > singleflight > sync.RWMutex > sync.Mutex.

  ---

  ## Decision Tree

  ```
  What kind of shared state?
  │
  ├── Single value (bool, int, pointer, struct) updated atomically?
  │   ├── Primitive (int64, bool, uint32): atomic.Int64 / atomic.Bool / atomic.Uint32
  │   ├── Pointer to struct: atomic.Pointer[T] (Go 1.19+)
  │   └── Struct with multiple fields (must read all fields consistently):
  │       └── atomic.Value storing an IMMUTABLE snapshot struct
  │           → Readers call Load(); writers build a new struct and call Store()
  │           → Never mutate the stored struct in place after Store()
  │
  ├── Concurrent map?
  │   ├── Write-rarely / read-often (e.g. cache, registry, ETag store):
  │   │   └── sync.Map — lock-free reads in the steady state
  │   ├── Typed values, higher throughput, or writes are frequent:
  │   │   └── xsync.MapOf[K, V] (puzpuzpuz/xsync/v4) — CLHT-based lock-free map
  │   │       → Use .Compute() for CAS-style atomic updates
  │   │       → Cannot hold its internal lock across I/O (structural guarantee)
  │   └── Extremely write-heavy, high key cardinality:
  │       └── Sharded map: N xsync.MapOf shards, key routed by hash(key) % N
  │
  ├── Concurrent list/slice (append-heavy)?
  │   ├── Rare writes, many readers: atomic.Value storing immutable []T snapshot
  │   │   → Writers: copy slice, append, Store new slice (COW)
  │   │   → Readers: Load(), range over snapshot — no lock
  │   └── Frequent writes: sync.Mutex protecting the slice (small critical section only)
  │
  ├── Duplicate concurrent requests for the same expensive operation?
  │   └── singleflight.Group — coalesces N identical in-flight calls into 1
  │       → All callers share the single result; no thundering herd
  │       → Combine with atomic.Value cache: check cache first, miss → singleflight
  │
  ├── One-time initialization?
  │   └── sync.Once — guaranteed single execution, zero lock after first call
  │
  └── Truly complex multi-field update where atomics don't compose?
      └── sync.Mutex (last resort)
          → Critical section must be < 10µs (no I/O, no subprocess, no allocation loop)
          → Prefer sync.RWMutex if read:write ratio > 5:1
          → Document WHY a mutex was unavoidable (it's a code smell, not a feature)
  ```

  ---

  ## Pattern Implementations

  ### 1. atomic.Value — Immutable Snapshot

  Use when multiple fields must be read consistently (e.g., auth state, config, cache snapshot).

  ```go
  type authResult struct {
      ok        bool
      checkedAt time.Time
  }

  type Service struct {
      auth atomic.Value // stores authResult; nil = not yet checked
  }

  // Read — lock-free
  func (s *Service) isAuthFresh() (bool, bool) {
      v := s.auth.Load()
      if v == nil {
          return false, false
      }
      r := v.(authResult)
      return r.ok, time.Since(r.checkedAt) < 5*time.Minute
  }

  // Write — atomic swap (safe to call from any goroutine)
  func (s *Service) setAuth(ok bool) {
      s.auth.Store(authResult{ok: ok, checkedAt: time.Now()})
  }
  ```

  **Rules**:
  - The stored type must be the same across all `Store()` calls (Go panics otherwise).
  - Never modify fields of the loaded struct — it may be concurrently loaded elsewhere.
  - Use `CompareAndSwap` (Go 1.17+) when you need to update only if the value hasn't changed.

  ---

  ### 2. sync.Map — Write-Seldom Concurrent Map

  Use for caches, registries, and ETag stores where entries are written once and read many times.

  Allocation profile for string keys (confirmed by benchmark, directional only — see caveat):
  - 99% reads: 0 B/op (same as xsync.MapOf)
  - 90% reads: 3 B/op (vs xsync.MapOf 1 B/op)
  - 75% reads: 9 B/op (vs xsync.MapOf 2 B/op)

  > **Go 1.24 note**: As of Go 1.24, `sync.Map` uses a HashTrieMap backend that improves
  > write performance. If you are on Go 1.24+, `sync.Map` may be sufficient for mixed
  > workloads without reaching for `xsync.MapOf`. Benchmark your actual workload.

  ```go
  var cache sync.Map // key: string, value: cacheEntry

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
          cache.Delete(key) // best-effort eviction
          return "", false
      }
      return e.result, true
  }

  func set(key, result string, ttl time.Duration) {
      cache.Store(key, cacheEntry{result: result, expiry: time.Now().Add(ttl)})
  }
  ```

  **When NOT to use sync.Map**: Write-heavy maps (every key is written frequently).
  `sync.Map` has higher per-op cost than `map + sync.Mutex` in that case. Use `xsync.MapOf`.

  ---

  ### 3. xsync.MapOf — Typed Lock-Free Map (puzpuzpuz/xsync/v4)

  Use when you need generic type safety and/or higher write throughput than `sync.Map` on
  Go < 1.24, or when the no-exported-lock structural guarantee matters.

  **Verified property** (3-0 adversarial review): `Load` and `Range` are obstruction-free —
  they perform zero writes to shared memory and acquire no locks or CAS operations. Writes
  use fine-grained lock sharding (one lock per hash bucket group, not one global lock).

  > **Benchmark provenance caveat**: The xsync vs sync.Map benchmarks are authored by the
  > xsync library's creator. The allocation numbers (0/1/2 B/op at 99%/90%/75% reads) are
  > internally consistent and confirmed by adversarial review, but run your own benchmarks
  > before treating xsync.MapOf as categorically faster. On Go 1.24+ sync.Map may be
  > competitive. The claim "xsync outperforms sync.Map across all scenarios" is explicitly
  > refuted — do not repeat it.

  ```go
  import "github.com/puzpuzpuz/xsync/v4"

  type ETagCache struct {
      store *xsync.MapOf[string, etagEntry]
  }

  func NewETagCache() *ETagCache {
      return &ETagCache{store: xsync.NewMapOf[string, etagEntry]()}
  }

  func (c *ETagCache) Get(key string) (etagEntry, bool) {
      return c.store.Load(key)
  }

  func (c *ETagCache) Set(key string, e etagEntry) {
      c.store.Store(key, e)
  }

  // Atomic conditional update (no separate load+store race):
  func (c *ETagCache) UpdateETag(key, newETag string) {
      c.store.Compute(key, func(e etagEntry, loaded bool) (etagEntry, xsync.ComputeOp) {
          if !loaded {
              return etagEntry{}, xsync.CancelOp
          }
          ne := e // COW copy — never mutate e in place
          ne.etag = newETag
          return ne, xsync.UpdateOp
      })
  }
  ```

  **Key property**: `xsync.MapOf` has no exported `Lock()`/`Unlock()` methods. It is
  structurally impossible to hold its internal lock across an I/O call.

  ---

  ### 4. singleflight — Request Coalescing

  Use when a cache miss triggers an expensive operation (HTTP call, git subprocess, SQL query)
  and concurrent misses for the same key should share one result.

  ```go
  import "golang.org/x/sync/singleflight"

  type Service struct {
      cache  sync.Map
      group  singleflight.Group
  }

  func (s *Service) getOrFetch(key string) (string, error) {
      // Fast path: cache hit (lock-free)
      if v, ok := s.cache.Load(key); ok {
          return v.(string), nil
      }

      // Slow path: coalesce concurrent misses
      v, err, _ := s.group.Do(key, func() (any, error) {
          // Only one goroutine runs this per key per miss wave
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

  **When to use the shared=true return value**: `singleflight.Do` returns `(v, err, shared)`.
  If `shared == true`, the result was produced by another goroutine — useful for metrics.

  **Panic propagation** (production critical): If the executing goroutine's function panics,
  the panic is propagated to ALL waiting goroutines for that key. A single panic cascades
  to every concurrent caller. Wrap the inner function with recover if panics are possible.

  **Do NOT use singleflight for writes** — it is only for reads where the value doesn't
  change between callers. For cache invalidation, call `group.Forget(key)`.

  **At extreme scale**: The standard `singleflight.Group` uses a single global `sync.Mutex`
  protecting the entire key map — confirmed bottleneck under very high core-count concurrency
  (3-0 adversarial vote). For services where `Do` is called thousands of times per second
  across hundreds of goroutines, consider `github.com/tarndt/shardedsingleflight` (shards
  the key space across N groups). The magnitude of improvement is unverified; the
  architectural bottleneck is confirmed.

  ---

  ### 5. atomic.Pointer[T] — Lock-Free Pointer Swap (Go 1.19+)

  Use when the shared value is large (avoids `atomic.Value`'s interface boxing overhead)
  or when you want generic type safety.

  ```go
  type Config struct {
      Timeout   time.Duration
      MaxConns  int
      AuthToken string
  }

  type Service struct {
      cfg atomic.Pointer[Config]
  }

  func (s *Service) LoadConfig() *Config {
      return s.cfg.Load() // returns nil if not yet set
  }

  func (s *Service) UpdateConfig(c *Config) {
      s.cfg.Store(c)
  }
  ```

  **Rule**: Once stored, the `*Config` must be treated as immutable. Callers may hold a
  pointer to the old config while a new one is being stored — that is correct and expected.

  ---

  ### 6. COW Slice via atomic.Value — Immutable List

  Use for rarely-modified lists (plugin registries, subscriber lists, poller instance lists).

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
      // Read current snapshot, copy, append, store new snapshot atomically
      cur := p.loadInstances()
      next := make([]Instance, len(cur)+1)
      copy(next, cur)
      next[len(cur)] = inst
      p.instances.Store(next)
  }

  // Poll tick — reads instance list with zero locking
  func (p *Poller) pollOnce() {
      for _, inst := range p.loadInstances() { // lock-free
          go p.pollInstance(inst)
      }
  }
  ```

  ---

  ### 7. Atomic Primitives Cheat Sheet (Go 1.19+)

  | Need | Type | Notes |
  |------|------|-------|
  | Integer counter | `atomic.Int64` | No noCopy issue in Go 1.19+ |
  | Boolean flag | `atomic.Bool` | Replaces `sync.Mutex` + `bool` |
  | Typed pointer | `atomic.Pointer[T]` | Generic; replaces `unsafe.Pointer` |
  | Any value | `atomic.Value` | Must always Store same concrete type |
  | Shadow timestamp | `int64` + `atomic.LoadInt64` | Avoid `atomic.Int64` in copied structs (noCopy) |

  **noCopy pitfall**: `atomic.Int64`, `atomic.Bool`, etc. embed a `noCopy` sentinel.
  If the containing struct is passed by value or used in a slice-of-structs, `go vet` will
  flag it. Use raw `int64` + `atomic.LoadInt64/StoreInt64` when the struct is copied, or
  store an `*atomic.Int64` pointer instead.

  ---

  ## When a Mutex Is Acceptable

  A `sync.Mutex` is fine when ALL of these are true:

  1. The critical section contains no I/O, no subprocess, no allocation-heavy loop.
  2. The critical section runs in < 10µs in the worst case.
  3. The write:read ratio is high enough that `sync.RWMutex` would add complexity without benefit.
  4. `singleflight` cannot coalesce the callers (different keys, non-idempotent operations).

  Even then, add a comment explaining why a mutex was chosen over an atomic approach.

  ---

  ## Anti-Patterns to Refuse

  ```go
  // ❌ Lock held across HTTP call
  mu.Lock()
  resp, err := http.Get(url)
  mu.Unlock()

  // ❌ Lock held across git subprocess
  mu.Lock()
  out, _ := exec.Command("git", "status").Output()
  mu.Unlock()

  // ❌ Multiple goroutines each fetch on cache miss (thundering herd)
  mu.RLock(); entry, ok := cache[key]; mu.RUnlock()
  if !ok { entry = expensiveFetch(key) } // all misses run this in parallel

  // ❌ sync.Mutex for a read-dominated map
  type Registry struct { mu sync.Mutex; m map[string]Handler }

  // ❌ Mutating a value loaded from atomic.Value
  v := val.Load().(MyStruct)
  v.Field = x // RACE: another goroutine holds the same pointer
  val.Store(v)
  ```

  ---

  ## Libraries

  | Library | Import | Use Case |
  |---------|--------|----------|
  | `sync/atomic` | stdlib | Primitive atomics (Int64, Bool, Pointer, Value) |
  | `sync` | stdlib | sync.Map, sync.Once, sync.Pool |
  | `golang.org/x/sync/singleflight` | x/sync | Request coalescing |
  | `puzpuzpuz/xsync/v4` | third-party | Typed lock-free map (xsync.MapOf) |
  | `orcaman/concurrent-map/v2` | third-party | Sharded map for write-heavy workloads |

  ---

  ## Output Format

  Given a concurrency problem:
  1. **Classify**: which primitive fits and why (one sentence per option ruled out).
  2. **Implement**: show the minimal correct implementation with no unrelated changes.
  3. **Anti-pattern eliminated**: what was wrong with the old approach.
  4. **Test/benchmark**: `go test -race` command + benchmark name that confirms correctness.
---

# go:parallelism

Go fearless concurrency — select the right primitive and implement it correctly.

Covers: `atomic.Value`, `atomic.Pointer[T]`, `atomic.Int64/Bool`, `sync.Map`,
`xsync.MapOf`, `singleflight`, COW slice via atomic.Value, and when a mutex is acceptable.

Decision tree routes from "what kind of shared state?" to the correct primitive,
with copy-paste implementations and anti-patterns to refuse.

Usage: `/go:parallelism <description of the shared state and access pattern>`
