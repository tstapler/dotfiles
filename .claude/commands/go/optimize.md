---
description: Apply Go-specific performance fix patterns to a profiling finding. Given a pprof hotspot (location, cycles, count, profile type), walks the decision tree to select the right pattern (atomic shadow, early-return guard, sync.RWMutex, xsync.Map, TTL cache, direct SQL UPDATE), implements the fix, and produces an enforcement test at the highest achievable ladder level.
prompt: |
  # go:optimize — Fix a Go Performance Hotspot

  You are given a pprof finding from the stapler-squad codebase. Apply the correct
  Go-specific pattern, implement the fix, and add the enforcement test that would
  catch a regression. Do NOT add CLAUDE.md notes — implement runnable enforcement.

  ## Input

  The finding to fix is provided in the command arguments. If no finding is given,
  ask for: profile type (mutex/block/allocs), file:line, cycles, count, and a one-
  sentence description of what the hot function does.

  ---

  ## Step 1 — Classify the finding

  Route to the matching pattern using this decision tree:

  ```
  Profile type?
  ├── mutex (cycles waiting for a lock)
  │   ├── Hot read path (called >1000x/min, lock only protects a read)?
  │   │   └── PATTERN A: Atomic shadow field
  │   ├── Read-heavy map/queue with exclusive mutex?
  │   │   └── PATTERN B: sync.RWMutex for read-only ops
  │   ├── Map + mutex replaced by lock-free structure?
  │   │   └── PATTERN C: xsync.Map (puzpuzpuz/xsync/v4)
  │   └── Repeated expensive computation with same inputs?
  │       └── PATTERN D: TTL cache (sync.Map + expiry field)
  ├── allocs (allocation rate too high)
  │   ├── State check happens AFTER alloc that's only used on hot path?
  │   │   └── PATTERN E: Early-return guard before alloc
  │   ├── Regexp/string op called on input that rarely needs it?
  │   │   └── PATTERN F: Fast-path guard (ContainsRune / HasPrefix before regexp)
  │   ├── Slice grown by append in loop?
  │   │   └── PATTERN G: Preallocate with make([]T, 0, capacity)
  │   └── Short-lived objects allocated per request?
  │       └── PATTERN H: sync.Pool
  └── block (scheduler blocking)
      └── Per-frame log call in streaming goroutine?
          └── PATTERN I: Remove or gate the log call
  ```

  ---

  ## Step 2 — Apply the pattern

  ### PATTERN A — Atomic shadow field

  **When**: A `time.Time` or similar value is read on every poll tick under a
  `deadlock.RWMutex` or `sync.RWMutex`. The lock is only there to protect the read.

  **Mechanism**: Add a parallel `int64` field storing UnixNano, updated atomically
  on every write. The hot read path loads the int64 with no lock.

  **Critical Go gotcha**: Use raw `int64` + `atomic.Load/StoreInt64`, NOT
  `atomic.Int64`. The `atomic.Int64` type embeds a `noCopy` sentinel that causes
  `go vet` to flag copies of the containing struct (struct literals, function args).
  Raw `int64` is semantically identical and avoids the vet issue.

  ```go
  // In struct — raw int64, not atomic.Int64
  lastOutputNs int64 // shadow of LastOutput as UnixNano; atomic access only

  // Write path (caller already holds write lock — no extra cost)
  rs.LastOutput = now
  atomic.StoreInt64(&rs.lastOutputNs, now.UnixNano())

  // Read hot path — NO lock
  ns := atomic.LoadInt64(&rs.lastOutputNs)
  if ns != 0 {
      return time.Since(time.Unix(0, ns))
  }
  // Fallback when atomic not yet seeded (cold start / test code)
  i.mu.RLock()
  defer i.mu.RUnlock()
  return i.TimeSince(i.CreatedAt)

  // After load from storage — seed the atomic from the time.Time field
  func (rs *ReviewState) SyncAtomicTimestamps() {
      if !rs.LastOutput.IsZero() {
          atomic.StoreInt64(&rs.lastOutputNs, rs.LastOutput.UnixNano())
      }
  }
  ```

  **Enforcement**: `TestXxx_ZeroAllocsHotPath` using `testing.AllocsPerRun(100, f)`.
  Seed the atomic first; assert `allocs == 0`.

  ---

  ### PATTERN B — sync.RWMutex for read-heavy maps/queues

  **When**: A struct uses `sync.Mutex` exclusively, but `Get`, `Has`, `List`,
  `Count` operations make up >80% of calls.

  **Mechanism**: Change `mu sync.Mutex` → `mu sync.RWMutex`. Replace `mu.Lock()`
  with `mu.RLock()` / `mu.RUnlock()` in all read-only methods. Keep `mu.Lock()`
  for `Add`, `Remove`, `Clear`.

  **Gotcha**: Observers/callbacks must be called AFTER the lock is released to
  avoid re-entrancy deadlocks. Copy the observer slice under the lock, then call
  outside:
  ```go
  rq.mu.Lock()
  observersCopy := append([]Observer(nil), rq.observers...)
  rq.mu.Unlock()
  for _, obs := range observersCopy { obs.OnChange() }
  ```

  **Enforcement**: `BenchmarkXxx_ConcurrentReads` with `b.RunParallel` and
  `-race` flag. Must complete without DATA RACE output.

  ---

  ### PATTERN C — xsync.Map (lock-free concurrent map)

  **When**: A `map[K]V + sync.RWMutex` pair has high concurrency and the API
  allows callers to hold the lock across I/O (a latent deadlock risk).

  **Mechanism**: Replace with `xsync.Map[K, V]` from `puzpuzpuz/xsync/v4`.
  The CLHT-based map has NO exported Lock/Unlock — callers physically cannot hold
  the map lock across I/O. Mutations use `Compute` with COW for value types:

  ```go
  m.Compute(key, func(v MyVal, loaded bool) (MyVal, xsync.ComputeOp) {
      if !loaded { return v, xsync.CancelOp }
      newV := v          // COW copy
      newV.Field = x
      return newV, xsync.UpdateOp
  })
  ```

  **Nil-receiver guard**: If the map owner may be nil (e.g. loaded from storage
  before init), add `if r == nil { return zero, false }` to every method. Nil
  pointer method calls are legal in Go; nil dereferences are not.

  **Enforcement**: Compile-time — the absence of `Lock()`/`Unlock()` methods on
  `xsync.Map` means the old lock-holding pattern doesn't compile.

  ---

  ### PATTERN D — TTL cache (sync.Map + expiry)

  **When**: The same expensive computation (go-git `wt.Status()`, ORM query,
  external API) is repeated with the same key within a short window.

  **Mechanism**: Package-level `sync.Map` keyed by the natural cache key. Value
  is a struct with the result and an `expiry time.Time`. Race on miss is benign
  (last writer wins; both compute the same value):

  ```go
  const cacheTTL = 30 * time.Second

  type cacheEntry struct {
      result Result
      expiry time.Time
  }
  var cache sync.Map // key: string, value: cacheEntry

  func expensiveOp(key string) (Result, error) {
      if v, ok := cache.Load(key); ok {
          if e := v.(cacheEntry); time.Now().Before(e.expiry) {
              return e.result, nil
          }
      }
      result, err := expensiveOpUncached(key)
      if err == nil {
          cache.Store(key, cacheEntry{result: result, expiry: time.Now().Add(cacheTTL)})
      }
      return result, err
  }
  ```

  **Enforcement**: `BenchmarkXxxCached` — warm cache with one real call, then
  assert `allocs/op == 0` via `testing.AllocsPerRun`. A `<1µs` latency assertion
  is also appropriate.

  ---

  ### PATTERN E — Early-return guard before alloc

  **When**: A function converts `[]byte → string` (or similar alloc) before
  checking state that causes an early return in the common case.

  **Mechanism**: Move ALL state checks above the alloc:

  ```go
  // BEFORE: alloc then check
  output := string(data)      // allocates on every call
  if d.state != StateActive { return }

  // AFTER: check then alloc
  if d.state != StateActive { return }
  if time.Since(d.last) < d.cooldown { return }
  output := string(data)      // only reached when work is needed
  ```

  **Enforcement**: `TestXxx_ZeroAllocsEarlyReturn` — set state to the inactive
  path, call the function, assert `AllocsPerRun == 0`.

  ---

  ### PATTERN F — Fast-path guard before regexp

  **When**: A regexp or string allocation is called on input that is ASCII in
  the common case (e.g. AI assistant output, log lines without ANSI codes).

  **Mechanism**: Check for the triggering character first:

  ```go
  func stripANSI(s string) string {
      if !strings.ContainsRune(s, '\x1b') {
          return s // fast path: no allocation, no regexp engine
      }
      return ansiRe.ReplaceAllString(s, "")
  }
  ```

  **Enforcement**: `TestXxx_ZeroAllocsPlainText` using `AllocsPerRun(100, f)`.

  ---

  ### PATTERN G — Preallocate slices

  **When**: `prealloc` linter flags a `var s []T` followed by `append` in a loop
  where the length is known or bounded.

  **Mechanism**:
  ```go
  // BEFORE
  var results []Result
  for _, item := range items {
      results = append(results, process(item))
  }

  // AFTER
  results := make([]Result, 0, len(items))
  for _, item := range items {
      results = append(results, process(item))
  }
  ```

  **Enforcement**: `prealloc` golangci-lint rule (already enabled in this repo).

  ---

  ### PATTERN H — sync.Pool for short-lived objects

  **When**: allocs profile shows the same type allocated millions of times per
  second from a hot path (proto messages, buffers, encoder state).

  **Mechanism**:
  ```go
  var msgPool = sync.Pool{New: func() any { return new(MyMsg) }}

  func hotPath() {
      msg := msgPool.Get().(*MyMsg)
      defer msgPool.Put(msg)
      // reset msg fields before use
      *msg = MyMsg{}
      // use msg...
  }
  ```

  **Enforcement**: `BenchmarkXxx_PooledAllocs` asserting `allocs/op == 0` for
  the pooled path.

  ---

  ### PATTERN I — Remove hot-path log calls

  **When**: block profile shows high cycles in a streaming/send goroutine at a
  `log.Printf` or `log.DebugLog.Printf` call inside the send loop.

  **Mechanism**: Remove the log call, or gate it:
  ```go
  // Remove entirely — the caller's error handling provides the signal
  // OR gate on debug flag
  if log.DebugLog != nil {
      log.DebugLog.Printf("sending frame %d", n)
  }
  ```

  **Enforcement**: `BenchmarkXxxStreamSend` with `b.ReportAllocs()` — log call
  in the loop shows up as allocs/op > 0 even when the output is discarded.

  ---

  ## Step 3 — Implement the fix

  1. Read the hot file and the surrounding 50 lines of context.
  2. Apply the pattern. Keep the change minimal — no unrelated cleanup.
  3. Call `SyncAtomicTimestamps()` (Pattern A) or similar init wherever the
     struct is constructed from persisted data (`FromInstanceData`, `newInstance`).
  4. Build: `go build ./...` must pass.
  5. Run affected tests: `go test ./path/to/pkg/... -count=1`.

  ---

  ## Step 4 — Enforce

  Work down this ladder. Stop at the first achievable level:

  ```
  1. Compile     → type change makes the bad pattern impossible to express
  2. Lint        → golangci-lint rule fires on the bad pattern (prealloc, forbidigo)
  3. Benchmark   → AllocsPerRun or ns/op asserts the fast path; must fail pre-fix
  4. Unit test   → asserts correct behaviour; must fail pre-fix
  5. CLAUDE.md   → only when 1-4 are genuinely unreachable
  ```

  Write the enforcement test/benchmark, run it, confirm it passes.

  ---

  ## Step 5 — Add to CI (if benchmark)

  Add the new benchmark to the Tier 1 regex in `.github/workflows/benchmark.yml`:

  ```yaml
  -bench='...|BenchmarkYourNewBenchmark'
  ```

  Add the package to the package list if not already present.

  ---

  ## Output format

  Produce in order:
  1. **Classification**: which pattern, one sentence why.
  2. **Diff summary**: what changed and where (file:line range).
  3. **Enforcement**: test/benchmark name and what it asserts.
  4. **Verification**: `go test -run/bench` command that confirms it passes.
  5. **CI update**: benchmark.yml change if applicable.

  Do NOT produce proposals only — implement the fix and enforcement.
---

# go:optimize

Given a pprof hotspot, classify it, apply the correct Go performance pattern,
implement the fix, and add an enforcement test at the highest achievable level
on the ladder (compile → lint → benchmark → test → CLAUDE.md).

Patterns covered:
- **A** Atomic shadow field (lock-free hot reads of `time.Time` values)
- **B** `sync.RWMutex` for read-heavy maps/queues
- **C** `xsync.Map` for lock-scope-safe concurrent maps
- **D** TTL cache (`sync.Map` + expiry) for repeated expensive ops
- **E** Early-return guard before heap allocation
- **F** Fast-path guard (`ContainsRune` / `HasPrefix`) before regexp
- **G** Slice preallocation (`make([]T, 0, n)`)
- **H** `sync.Pool` for short-lived objects
- **I** Remove/gate hot-path log calls in streaming goroutines

Usage: `/go:optimize <profile_type> <file:line> <cycles> <count> [description]`
