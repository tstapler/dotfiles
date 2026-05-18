---
name: rust-perf-tuning
description: Diagnose Rust performance bottlenecks from profiling data and apply targeted optimizations. Covers the full cycle: measure → profile (see rust-profiling skill) → diagnose → fix → verify. Includes pattern-matched fixes for common flamegraph hotspots, allocation elimination, data layout, compiler settings, and parallelism tuning.
metadata:
  type: feedback
---

# Rust Performance Tuning

End-to-end workflow: baseline benchmark → profile → diagnose hotspot pattern → apply fix → verify improvement.

**Companion skill:** [[rust-profiling]] for collecting CPU flamegraphs, heaptrack reports, and collapsed stacks. This skill starts where that one ends — you have data, now fix it.

---

## Phase 0 — Prerequisites: Build Settings First

Before profiling or optimizing code, apply zero-effort compiler settings. These are free speedups.

```toml
# Cargo.toml (workspace or crate level)
[profile.release]
codegen-units = 1    # enables full inlining across the crate
lto = "thin"         # cross-crate inlining, fast links (use "fat" for max perf, slow links)
opt-level = 3        # default for release; try "s" for size if I-cache is a bottleneck
debug = 1            # line numbers for profiling (strip for shipping)
```

```bash
# Target-CPU: turns on AVX2/AVX-512 on native machine — free vectorization
export RUSTFLAGS="-C target-cpu=native"

# Alternative allocator — swap 5 lines, get 5-30% on allocation-heavy workloads
# Cargo.toml: [dependencies] mimalloc = { version = "0.1", default-features = false }
# main.rs:   #[global_allocator] static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;
```

Expected impact: **10–25% end-to-end speedup** with no code changes. Do this first, always.

---

> To collect the flamegraph and collapsed stacks needed for Phase 2 diagnosis, apply the `rust-profiling` skill.

## Phase 1 — Establish a Baseline

```bash
# Save named criterion baseline before any changes
cargo bench -p <crate> -- --save-baseline before

# Or time the binary directly (crude but fast)
time ./target/release/<binary> <args>

# perf stat for CPU-level counters (IPC, cache misses)
perf stat -- ./target/release/<binary> <args>
```

IPC interpretation from `perf stat`:
- IPC < 1.0 → memory-bound (cache misses dominating)
- IPC 1–2 → compute-bound, some stalls
- IPC > 3 → well-vectorized, CPU is the limit
- Cache misses > 5% → data layout problem

---

## Phase 2 — Diagnose from Flamegraph / Collapsed Stacks

Run `rust-profiling` skill to collect a flamegraph. Then pattern-match the hotspot:

### Pattern Table

| What you see in flamegraph | Diagnosis | Section |
|---|---|---|
| `alloc::alloc::alloc` / `jemalloc_sys::malloc` | Per-iteration allocation | §3 Allocations |
| `std::collections::hash_map` | HashMap overhead | §4 HashMap |
| `clone()` in hot path | Unnecessary copy | §3 Allocations |
| `fmt::Display` / `format!()` | String formatting overhead | §3 Allocations |
| `rayon::iter` overhead > work items | Parallel overhead > gain | §6 Rayon |
| `parking_lot::Mutex::lock` | Lock contention | §6 Rayon |
| `memcpy` / `memmove` dominant | Data movement | §5 Data Layout |
| `f32::sqrt` / `f64::sqrt` / trig in loop | Math-bound → SIMD candidate | §7 SIMD |
| `nalgebra::` slow with dynamic matrices | Dynamic allocation in linalg | §7 SIMD |
| Thin hot band across many frames | IPC < 1 → memory-bound → SoA | §5 Data Layout |
| `core::slice::index` / bounds check | Redundant bounds checking | §8 Unsafe Elision |
| `dyn Trait` vtable calls wide | Dynamic dispatch overhead | §9 Dispatch |

### Quick awk on collapsed stacks (from rust-profiling)

```bash
# Top leaf frames by self-sample count
awk '{split($0,a,";"); leaf=a[length(a)]; sub(/ [0-9]+$/,""); n=$NF; count[leaf]+=n}
     END{for(f in count) print count[f],f}' cpu.collapsed | sort -rn | head -20

# % of time in a specific module
grep "my_crate::" cpu.collapsed | awk '{sum+=$NF} END{print sum}' 
grep "" cpu.collapsed | awk '{sum+=$NF} END{print sum}'
# Divide for %

# Stacks that call a specific function (show callers)
grep "hot_function" cpu.collapsed | sed 's/;[^;]*$//' | sort | uniq -c | sort -rn | head -10
```

---

## Phase 3 — Fix: Eliminating Allocations

**Symptom:** `alloc`, `clone`, `format!`, `collect` in flamegraph hot path.

### Buffer reuse (most common fix)

```rust
// Before: allocates per iteration
for line in lines {
    let s = format!("prefix_{}", line);   // heap alloc every iter
    process(&s);
}

// After: reuse buffer
let mut buf = String::with_capacity(64);
for line in lines {
    buf.clear();
    write!(&mut buf, "prefix_{}", line).unwrap();  // zero alloc
    process(&buf);
}
```

### SmallVec for short-lived collections

```rust
// Before: Vec<_> always heap-allocates
let mut neighbors: Vec<u32> = Vec::new();

// After: inline storage for N ≤ 8, spills to heap only beyond
use smallvec::SmallVec;
let mut neighbors: SmallVec<[u32; 8]> = SmallVec::new();
```

### Vec::with_capacity to prevent reallocation

```rust
// Before: O(log n) reallocations
let mut v: Vec<_> = Vec::new();
for x in iter { v.push(x); }

// After: single allocation
let mut v = Vec::with_capacity(iter.size_hint().0);
for x in iter { v.push(x); }
// Or: iter.collect::<Vec<_>>() already calls size_hint — prefer collect when possible
```

### Avoid clone by restructuring ownership

```rust
// Before: clones the entire cloud to pass to two functions
fn process(cloud: PointCloud) {
    let filtered = filter(cloud.clone());
    let normals  = estimate(cloud.clone());
}

// After: take references
fn process(cloud: &PointCloud) {
    let filtered = filter(cloud);
    let normals  = estimate(cloud);
}
```

### Cow<'_, str> for conditionally-owned strings

```rust
// Before: always allocates
fn normalize(s: &str) -> String {
    if s.contains(' ') { s.replace(' ', "_") } else { s.to_owned() }
}

// After: borrows when no transformation needed
fn normalize(s: &str) -> Cow<'_, str> {
    if s.contains(' ') { Cow::Owned(s.replace(' ', "_")) } else { Cow::Borrowed(s) }
}
```

---

## Phase 4 — Fix: HashMap Replacement

**Symptom:** `std::collections::hash_map::HashMap` near top of flamegraph.

```rust
// Before: SipHash (DoS-resistant, ~3× slower for integer keys)
use std::collections::HashMap;
let mut map: HashMap<u32, u32> = HashMap::new();

// After option A: FxHashMap (rustc-hash) — fastest for integer/pointer keys
use rustc_hash::FxHashMap;
let mut map: FxHashMap<u32, u32> = FxHashMap::default();

// After option B: AHashMap — fastest for string keys (uses AES intrinsics)
use ahash::AHashMap;
let mut map: AHashMap<String, u32> = AHashMap::new();

// Type alias to make switching easy
type FastMap<K, V> = rustc_hash::FxHashMap<K, V>;
```

Expected speedup: **4–84%** over std HashMap (rustc's own benchmarks). Use std HashMap only when keys are user-controlled (HashDoS resistance required).

Pre-size to avoid rehashing:
```rust
let mut map = FxHashMap::with_capacity_and_hasher(expected_n, Default::default());
```

---

## Phase 5 — Fix: Data Layout (SoA over AoS)

**Symptom:** IPC < 1.0 in `perf stat`; `memcpy`/cache-miss dominated flamegraph; loop processes only a few fields of a large struct.

```rust
// Before: Array of Structs — each iteration loads the full struct into cache
struct Particle { x: f32, y: f32, z: f32, mass: f32, charge: f32, flags: u32 }
let particles: Vec<Particle> = ...;

// Hot loop touches only x, y, z → loads 24 bytes, uses 12, wastes 12
for p in &particles { p.x += dt * p.vx; }

// After: Struct of Arrays — x, y, z are contiguous → full cache lines used, auto-vectorizes
struct Particles { x: Vec<f32>, y: Vec<f32>, z: Vec<f32>, mass: Vec<f32>, charge: Vec<f32>, flags: Vec<u32> }

// Or use the soa-rs crate for auto-generated SoA:
// #[derive(soa_rs::Soa)] struct Particle { x: f32, y: f32, z: f32 }
// let particles = Particles::new();
```

Expected speedup: **2–4×** on vectorizable loops. The compiler auto-vectorizes SoA without any `unsafe` or SIMD intrinsics.

### False sharing fix (parallel code)

```rust
// Before: threads write adjacent fields → cache-line ping-pong
struct Counter { value: u64 }
let counters: Vec<Counter> = (0..n_threads).map(|_| Counter { value: 0 }).collect();

// After: pad each counter to its own cache line
use crossbeam::utils::CachePadded;
let counters: Vec<CachePadded<Counter>> = ...;
```

---

## Phase 6 — Fix: Rayon Parallelism

**Symptom:** Rayon overhead visible in flamegraph; `work_stealing` / `join` calls dominate; or parallelism isn't helping.

### When NOT to use rayon

```rust
// Rayon has ~2µs spawn overhead per unit of work.
// Use parallel only when: work_per_item > ~10µs OR n_items > ~10_000

// Before: parallel on tiny work
small_vec.par_iter().for_each(|x| cheap_op(x));  // slower than serial for small n

// After: serial threshold
if small_vec.len() > 10_000 {
    small_vec.par_iter().for_each(|x| expensive_op(x));
} else {
    small_vec.iter().for_each(|x| expensive_op(x));
}
```

### Reducing allocation inside par_iter

```rust
// Before: allocates a Vec per rayon thread
let results: Vec<Vec<u32>> = data.par_iter().map(|x| compute(x)).collect();
// Then flatten — double allocation

// After: rayon flat_map_iter + collect into single Vec
let results: Vec<u32> = data.par_iter()
    .flat_map_iter(|x| compute_iter(x))
    .collect();
```

### Thread-local buffers for per-iteration temporary data

```rust
use std::cell::RefCell;
thread_local! {
    static BUF: RefCell<Vec<u32>> = RefCell::new(Vec::with_capacity(1024));
}

data.par_iter().for_each(|x| {
    BUF.with(|buf| {
        let mut buf = buf.borrow_mut();
        buf.clear();
        compute_into(x, &mut buf);
        // buf reused across calls on same thread — zero alloc per iteration
    });
});
```

### Rayon pool sizing

```rust
// Default: uses all logical CPUs — may be wrong for I/O-heavy or NUMA workloads
rayon::ThreadPoolBuilder::new()
    .num_threads(num_cpus::get_physical())  // physical only, avoid HT overhead
    .build_global()
    .unwrap();
```

---

## Phase 7 — Fix: SIMD and Math

**Symptom:** `f32::sqrt`, trig, or nalgebra dynamic-matrix functions in hot path.

### Enable auto-vectorization first

Before writing SIMD, check if the compiler already vectorizes with `RUSTFLAGS="-C target-cpu=native"`. Inspect assembly:

```bash
cargo rustc --release -- --emit asm
grep -A 20 "my_function:" target/release/deps/*.s | grep -i "ymm\|zmm\|xmm"
# ymm = AVX (256-bit), zmm = AVX-512 (512-bit), xmm = SSE (128-bit)
```

### `wide` crate for portable SIMD (stable Rust)

```rust
use wide::f32x8;

// Before: scalar
let result: Vec<f32> = a.iter().zip(b.iter()).map(|(&x, &y)| x * y + c).collect();

// After: 8-wide SIMD — same semantics, ~8× throughput on AVX2
let result: Vec<f32> = a.chunks_exact(8).zip(b.chunks_exact(8))
    .flat_map(|(ax, bx)| {
        let va = f32x8::from(ax.try_into().unwrap());
        let vb = f32x8::from(bx.try_into().unwrap());
        (va * vb + f32x8::splat(c)).to_array()
    })
    .collect();
```

### nalgebra: prefer fixed-size over dynamic matrices

```rust
// Before: DMatrix allocates on heap
let m: nalgebra::DMatrix<f64> = DMatrix::zeros(3, 3);

// After: SMatrix is stack-allocated, no alloc, fully inlined
let m: nalgebra::SMatrix<f64, 3, 3> = SMatrix::zeros();
```

---

## Phase 8 — Fix: Bounds Check Elision

**Symptom:** `core::panicking::panic_bounds_check` or `slice::index` visible in flamegraph.

```rust
// Prefer iterators — compiler proves bounds automatically, no checks emitted
for (x, y) in a.iter().zip(b.iter()) { *x += *y; }

// split_at for validated index access
let (left, right) = slice.split_at(mid);  // single bounds check, then unchecked

// get_unchecked when you have proven the index is valid
// SAFETY: i < slice.len() ensured by the loop invariant above
let val = unsafe { *slice.get_unchecked(i) };
```

Note: `get_unchecked` is `unsafe`. Only use after proving the index is valid. Incorrect use causes UB.

---

## Phase 9 — Fix: Dispatch Overhead

**Symptom:** `dyn Trait` vtable calls spread across flamegraph; many call sites for the same trait method.

```rust
// Before: dyn dispatch — pointer chase + indirect call each iteration
fn process(items: &[Box<dyn Processor>]) {
    for item in items { item.process(); }  // vtable call per item
}

// After option A: enum dispatch — zero overhead, monomorphized
enum ProcessorKind { A(ProcessorA), B(ProcessorB) }
impl ProcessorKind {
    fn process(&self) { match self { Self::A(p) => p.process(), Self::B(p) => p.process() } }
}

// After option B: enum_dispatch crate (macro-generated enum from trait)
// #[enum_dispatch(Processor)] enum ProcessorKind { ProcessorA, ProcessorB }
```

Expected speedup: **2–10×** when the hot path is a tight loop over heterogeneous trait objects.

---

## Phase 10 — Verify the Fix

Always compare against the baseline, not against intuition:

```bash
# Criterion comparison
cargo bench -p <crate> -- --baseline before
# Look for: "Performance has improved by X%" in output

# Differential flamegraph (red=slower, blue=faster)
perf record -F 997 -g --call-graph=dwarf -- ./target/release/<binary> <args>
perf script | /opt/FlameGraph/stackcollapse-perf.pl > after.collapsed
/opt/FlameGraph/difffolded.pl before.collapsed after.collapsed | /opt/FlameGraph/flamegraph.pl > diff.svg
xdg-open diff.svg

# perf stat comparison
perf stat -- ./target/release/<binary> <args>  # compare IPC, cache-miss rate
```

**Minimum bar:** criterion must show statistically significant improvement (no overlap in confidence intervals). A 5% improvement that's within noise is not a confirmed fix.

---

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `rust-profiling` | Collect CPU flamegraphs, heaptrack reports, and collapsed stacks |
| `code-refactoring` | Structural refactors after eliminating the performance bottleneck |
| `code-debugging` | Systematic investigation when a perf fix introduces a correctness bug |
| `security-review` | Audit `unsafe` blocks introduced for bounds-check elision |

## Quick Reference: Fix by Symptom

| Symptom | First fix to try | Expected gain |
|---|---|---|
| `alloc` / `malloc` in hot path | Buffer reuse + `with_capacity` | 2–10× |
| `HashMap` near top | FxHashMap | 4–84% |
| IPC < 1.0 in perf stat | SoA data layout | 2–4× |
| Rayon overhead > work | Raise serial threshold or chunk size | 1.5–3× |
| `dyn Trait` wide in flamegraph | Enum dispatch | 2–10× |
| `f32::sqrt` / math dominant | `target-cpu=native` first, then `wide` | 2–8× |
| Build time / binary size bloat | `lto = "thin"`, `codegen-units = 4` | N/A |
| Slow cold start, not steady-state | PGO (`cargo-pgo`) | 10–20% |
| nalgebra slow | SMatrix instead of DMatrix | 2–5× |
| Clone in hot path | Borrow or Arc | 2–10× |
