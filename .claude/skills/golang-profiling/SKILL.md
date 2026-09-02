---
name: golang-profiling
description: Profile Go processes using pprof. Covers CPU, memory, goroutine, and mutex profiles; flamegraph visualization; collapsed-stacks and annotated-call-tree output for LLM analysis (with bundled, tested scripts); and benchmark profiling.
---

# Go Profiling with pprof

End-to-end workflow: enable pprof → collect profile → collapsed stacks or annotated call tree (primary analysis formats) → flamegraph (visualization).

## Format Strategy

| Format | Best for | Command |
|--------|----------|---------|
| **Collapsed stacks** | Scripting, CI diffs, awk parsing, max compression | `go tool pprof -raw -output=collapsed` |
| **Annotated call tree** | LLM reasoning about *which call chain* to fix, without full collapsed-stacks token cost | see Step 3a below |
| HTML flamegraph | Interactive human exploration | `go tool pprof -http=:8081` |
| Text top | Quick terminal summary | `go tool pprof -top` |
| Raw `.prof` | Archive, future re-analysis | — |

**Use collapsed stacks when scripting or diffing; use the annotated call tree when handing a profile to an LLM to decide what to fix.** Collapsed-stacks format: `frame1;frame2;leaf N` — one line per unique call stack, count at end. It's the most compact representation but flattens call-path context into thousands of near-duplicate lines; the annotated tree (Step 3a) keeps the tree structure so the LLM can see *which caller* to fix, at roughly the token cost of a top-N table.

## Bundled Scripts

`scripts/` holds stdlib-only Python (no deps to install) with a `tests/` suite (`python3 -m unittest discover -s scripts/tests`):

| Script | Purpose | Used in |
|--------|---------|---------|
| `scripts/annotate_tree.py` | Builds the annotated call tree (self%/cum%, HOTSPOT markers, pruned) directly from `go tool pprof -raw` output | Step 3a |
| `scripts/pct_breakdown.py` | Leaf-frame percentage breakdown from collapsed stacks | Step 3 |

---

## Step 1 — Enable pprof in Your Application

### HTTP Server (long-running apps)

```go
import _ "net/http/pprof"

// In main() or init():
go func() {
    log.Println(http.ListenAndServe("localhost:6060", nil))
}()
```

Endpoints exposed automatically:
- `http://localhost:6060/debug/pprof/profile?seconds=30` — CPU (30s sample)
- `http://localhost:6060/debug/pprof/heap` — Memory (heap allocations)
- `http://localhost:6060/debug/pprof/goroutine` — All goroutines + stacks
- `http://localhost:6060/debug/pprof/mutex` — Lock contention
- `http://localhost:6060/debug/pprof/block` — Blocking operations (channels, syscalls)

### Enable mutex and block profiling (off by default)

```go
import "runtime"

func init() {
    runtime.SetMutexProfileFraction(1)  // 1 = sample every mutex event
    runtime.SetBlockProfileRate(1)       // 1 = sample every block event (nanoseconds)
}
```

Only enable these in dev/profile builds — they add overhead.

### Benchmark profiling (no HTTP server needed)

```bash
# CPU profile from benchmark
go test -bench=BenchmarkMyFunc -benchmem -cpuprofile=cpu.prof ./pkg -timeout=5m

# Memory profile from benchmark
go test -bench=BenchmarkMyFunc -benchmem -memprofile=mem.prof ./pkg -timeout=5m

# Execution trace (richer than pprof — shows goroutine scheduling)
go test -bench=BenchmarkMyFunc -trace=trace.out ./pkg -timeout=5m
go tool trace trace.out
```

---

## Step 2 — Collect Profiles

### From running HTTP server

```bash
# CPU (30 second sample — app must be under load)
curl -o cpu.prof "http://localhost:6060/debug/pprof/profile?seconds=30"

# Heap (snapshot)
curl -o heap.prof http://localhost:6060/debug/pprof/heap

# Goroutine dump (all goroutines with stacks)
curl -o goroutine.prof http://localhost:6060/debug/pprof/goroutine

# Mutex contention
curl -o mutex.prof http://localhost:6060/debug/pprof/mutex

# Block / channel contention
curl -o block.prof http://localhost:6060/debug/pprof/block
```

### From tests (no server)

```bash
# CPU profile for all tests in a package
go test -cpuprofile=cpu.prof ./pkg

# Memory profile for all tests
go test -memprofile=mem.prof ./pkg

# Specific test function
go test -run=TestHeavyOperation -cpuprofile=cpu.prof ./pkg
```

---

## Step 3 — Analyze Collapsed Stacks

### Generate collapsed stacks

```bash
# CPU collapsed stacks
go tool pprof -raw cpu.prof | awk '/^[^#]/{print}' > cpu.collapsed
# Or use the sample/total-based output:
go tool pprof -output=cpu.collapsed -text cpu.prof

# Better: use Brendan Gregg's stackcollapse-go (most compatible with flamegraph tools)
go tool pprof -raw -output=raw.txt cpu.prof
# Then collapse with: https://github.com/brendangregg/FlameGraph/blob/master/stackcollapse-go.pl
# stackcollapse-go.pl raw.txt > cpu.collapsed
```

### Quick text analysis (no external tools)

```bash
# Top functions by self-sample (CPU)
go tool pprof -top cpu.prof

# Top functions with cumulative cost shown
go tool pprof -top -cum cpu.prof

# Show top 20 with source
go tool pprof -top=20 cpu.prof
```

### awk extraction from collapsed stacks

Collapsed-stacks format is root-first, leaf-last (`root;caller;leaf N`) — the
leaf frame is the *last* `;`-separated field, not the first.

```bash
# Top leaf frames by self-sample count
awk '{n=$NF; sub(/ [0-9]+$/,"",n); split(n,a,";"); leaf=a[length(a)]; count[leaf]+=$NF} END{for(f in count) print count[f],f}' \
  cpu.collapsed | sort -rn | head -20

# Stacks in a specific package
grep "yourpackage" cpu.collapsed | sort -t' ' -k2 -rn | head -10

# Top full stacks (raw, sorted by count)
sort -t' ' -k2 -rn cpu.collapsed | head -20
```

### Percentage breakdown (bundled script)

```bash
python3 scripts/pct_breakdown.py cpu.collapsed --top 20
```

See `scripts/pct_breakdown.py` — leaf-frame self-time ranked by percentage of
total samples, tested in `scripts/tests/test_pct_breakdown.py`.

---

## Step 3a — Annotated Call Tree (LLM format)

The terse-but-context-preserving middle ground between collapsed stacks (all
call-path detail, but thousands of near-duplicate lines) and a flat top-N
table (compact, but loses which caller is responsible). Built with the
bundled `scripts/annotate_tree.py` directly from `go tool pprof -raw` —
no Perl/stackcollapse dependency, stdlib-only.

```bash
go tool pprof -raw cpu.prof > raw.txt
python3 scripts/annotate_tree.py raw.txt
```

Tune pruning/sensitivity for the profile size:

```bash
python3 scripts/annotate_tree.py raw.txt --min-pct 2 --hotspot-pct 8 --max-depth 10 --top-self 15
```

Example output (verified against a real CPU profile with a hot recursive
function, an allocation-heavy path, and a `strings.Builder` growth path):

```
Total samples: 8
Legend: [self% | cum%] function  (pruned below 1.0% cum, HOTSPOT = self% >= 5.0%)

├── [  0.0% |  87.5%] runtime.main
│   ├── [  0.0% |  50.0%] main.main
│   │   └── [  0.0% |  50.0%] main.cpuHeavy
│   │       └── [  0.0% |  50.0%] main.fib
│   ├── [ 25.0% |  25.0%] strings.(*Builder).copyCheck  ◀ HOTSPOT
│   └── [ 12.5% |  12.5%] main.allocHeavy  ◀ HOTSPOT
└── [  0.0% |  12.5%] runtime.systemstack
    └── ...

Top 10 by self-time (flat, across all call sites):
   50.0%  main.fib
   25.0%  strings.(*Builder).copyCheck
   12.5%  main.allocHeavy
```

`--min-pct` prunes any subtree below that cumulative % of total (keeps output
readable on real multi-thousand-sample profiles); `--hotspot-pct` controls
the self% threshold for the `◀ HOTSPOT` marker; `--top-self` adds a flat
leaderboard that catches hotspots split across many call sites (e.g. a shared
helper called from a dozen places, each individually below the tree's
pruning floor). Works on any profile type `-raw` supports (CPU, heap,
goroutine, mutex, block) — self/cum are computed from the sample-count
column, which pprof already normalizes per profile type.

Tested in `scripts/tests/test_annotate_tree.py` against a synthetic
`-raw`-format fixture (shared call-path merging, hotspot marking, pruning,
depth truncation, flat leaderboard).

---

## Step 4 — Flamegraph Visualization

### Interactive browser UI (recommended)

```bash
# CPU flamegraph — opens browser automatically
go tool pprof -http=:8081 cpu.prof

# Memory flamegraph
go tool pprof -http=:8081 heap.prof

# Goroutine flamegraph
go tool pprof -http=:8081 goroutine.prof
```

The browser UI shows: flamegraph, top, source, peek, disassembly tabs.

### SVG flamegraph (shareable)

```bash
# Install Brendan Gregg's tools once
git clone https://github.com/brendangregg/FlameGraph /opt/FlameGraph

# Generate SVG
go tool pprof -raw -output=raw.txt cpu.prof
/opt/FlameGraph/stackcollapse-go.pl raw.txt | /opt/FlameGraph/flamegraph.pl > flamegraph.svg
```

### Differential flamegraph (A/B comparison)

```bash
# Compare two profiles — shows regressions (red) and improvements (blue)
go tool pprof -http=:8081 -diff_base=baseline.prof current.prof
```

---

## Step 5 — Profile Types and When to Use

| Profile | Flag / Endpoint | Use when |
|---------|----------------|----------|
| **CPU** | `-cpuprofile` / `/profile?seconds=N` | High CPU, slow requests, inefficient loops |
| **Heap** | `-memprofile` / `/heap` | High memory, GC pressure, allocation churn |
| **Goroutine** | `/goroutine` | Goroutine leaks, deadlocks, stuck goroutines |
| **Mutex** | `/mutex` | Lock contention, slow shared state access |
| **Block** | `/block` | Channel blocking, syscall starvation |
| **Trace** | `-trace` / `/trace` | Goroutine scheduling, GC pauses, end-to-end latency |

---

> For fixing hotspots identified in the profile, apply the `golang-development` skill for idiomatic optimizations.

## Step 6 — Interpreting Results

### Hotspot patterns and fixes

| Pattern in top/flamegraph | Diagnosis | Fix |
|---------------------------|-----------|-----|
| `runtime.mallocgc` > 10% | Allocation churn (GC pressure) | Object pooling (`sync.Pool`), reuse slices |
| `runtime.gcBgMarkWorker` > 5% | GC running constantly | Reduce allocation rate; tune `GOGC` |
| `sync.(*Mutex).Lock` dominant | Lock contention | Reduce lock scope; use `sync.RWMutex`; shard |
| `syscall.Read` / `syscall.Write` | I/O bound | Buffered I/O (`bufio`); async I/O patterns |
| `encoding/json.Marshal` in hot path | Serialization overhead | `encoding/json` → `jsoniter` or `json.RawMessage` cache |
| `reflect.*` in hot path | Reflection overhead | Code-gen alternatives; avoid reflect in loops |
| `fmt.Sprintf` / `fmt.Fprintf` | String formatting cost | `strings.Builder`; pre-format static strings |
| `regexp.(*Regexp).Find` | Regex re-compilation | Compile once at package level (`var re = regexp.MustCompile(...)`) |
| `database/sql.(*DB).QueryContext` | DB query overhead | Connection pool tuning; query result caching |

### Filter to app-only frames

```bash
# Show only your package in pprof interactive
go tool pprof cpu.prof
(pprof) focus yourpackage/
(pprof) top

# Or from collapsed stacks
grep "github.com/yourorg/yourrepo" cpu.collapsed | sort -t' ' -k2 -rn | head -20
```

### Memory: inuse vs alloc

```bash
# Current live heap (what's consuming memory right now)
go tool pprof -inuse_space heap.prof

# Total allocations (what's driving GC pressure)
go tool pprof -alloc_space heap.prof

# Allocation count (how many objects, not bytes)
go tool pprof -alloc_objects heap.prof
```

---

## Step 7 — CI Integration

```yaml
# .github/workflows/profile.yml
jobs:
  profile:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with: { go-version: stable }

      - name: Run benchmark with CPU profile
        run: |
          go test -bench=BenchmarkCriticalPath -benchmem \
            -cpuprofile=cpu.prof -memprofile=mem.prof \
            -timeout=5m ./pkg/...

      - name: Generate collapsed stacks
        run: |
          go tool pprof -top=50 cpu.prof > cpu-top.txt
          go tool pprof -top=50 mem.prof > mem-top.txt

      - uses: actions/upload-artifact@v4
        with:
          name: profiles-${{ github.sha }}
          path: |
            cpu.prof
            mem.prof
            cpu-top.txt
            mem-top.txt
          retention-days: 30
```

**Store `.prof` files as CI artifacts** — they're binary but small (~1-5 MB), and `go tool pprof -diff_base` can compare them across commits.

---

## Step 8 — Execution Trace (Deeper Analysis)

pprof shows *where* time is spent. `go tool trace` shows *why* — goroutine scheduling, GC pauses, syscall latency.

```bash
# Collect trace from benchmark
go test -bench=BenchmarkHeavy -trace=trace.out ./pkg -timeout=5m

# Collect trace from running app (5 seconds)
curl -o trace.out http://localhost:6060/debug/pprof/trace?seconds=5

# Open interactive viewer
go tool trace trace.out
```

Trace viewer tabs:
- **View trace** — Timeline of all goroutines; zoom into pauses
- **Goroutine analysis** — Time blocked vs running per goroutine
- **Network blocking profile** — Network I/O waits
- **Synchronization blocking** — Mutex/channel wait time
- **Scheduler latency** — Time goroutines waited to be scheduled

---

## Quick Reference

| Goal | Command |
|------|---------|
| CPU profile (live app) | `curl -o cpu.prof "localhost:6060/debug/pprof/profile?seconds=30"` |
| Heap profile | `curl -o heap.prof localhost:6060/debug/pprof/heap` |
| CPU profile (benchmark) | `go test -bench=. -cpuprofile=cpu.prof ./pkg` |
| Top functions | `go tool pprof -top cpu.prof` |
| Interactive flamegraph | `go tool pprof -http=:8081 cpu.prof` |
| Diff two profiles | `go tool pprof -http=:8081 -diff_base=old.prof new.prof` |
| Execution trace | `go tool trace trace.out` |
| Goroutine dump | `curl localhost:6060/debug/pprof/goroutine?debug=2` |

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `golang-development` | Apply idiomatic Go fixes after identifying hotspots |
| `github-actions-debugging` | Debug CI failures in profiling or benchmark workflows |
| `infra-docker-build-test` | Profile a Go service running inside a container |

## Common Pitfalls

- **Profiling an idle app** — CPU profiles are useless without load; always profile under realistic traffic or benchmark load
- **Short CPU samples** — Use at least 10-30 seconds; short samples miss infrequent-but-slow paths
- **Forgetting mutex/block rates** — `SetMutexProfileFraction` and `SetBlockProfileRate` are off by default; set them before collecting those profiles
- **`-inuse_space` vs `-alloc_space`** — inuse shows live heap; alloc shows GC pressure; use alloc when diagnosing GC, inuse for OOM
- **`reflect.*` frames masking real callers** — use `-cum` flag in pprof top to see cumulative callers through reflection
- **Benchmarks without `-benchmem`** — always add `-benchmem` to see allocation counts alongside ns/op
- **GC noise in short benchmarks** — use `testing.B.ResetTimer()` after setup code to exclude initialization from measurement
