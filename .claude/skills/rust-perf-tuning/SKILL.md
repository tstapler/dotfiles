---
name: rust-perf-tuning
description: Diagnose Rust performance bottlenecks from profiling data and apply targeted optimizations. Covers the full cycle: measure → profile (see rust-profiling skill) → diagnose → fix → verify. Includes pattern-matched fixes for common flamegraph hotspots, allocation elimination, data layout, compiler settings, and parallelism tuning.
paths: "**/*.rs"
metadata:
  type: feedback
---

# Rust Performance Tuning

End-to-end workflow: baseline benchmark → profile → diagnose hotspot pattern → apply fix → verify improvement.

**Companion skills:** [[rust-profiling]] for collecting CPU flamegraphs, heaptrack reports, and collapsed stacks. This skill starts where that one ends — you have data, now fix it. [[rust-memory-optimization]] for heap/allocation-specific fixes. [[rust-parallel-processing]] for adding parallelism once single-core is tuned. [[rust-development]] for the full workflow map.

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

| What you see in flamegraph | Diagnosis | Fix section |
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

Fixes for §3 and §4 (allocations, HashMap) are in [Allocation and HashMap Fixes](references/allocation-and-hashmap-fixes.md). Fixes for §5–§9 (data layout, rayon, SIMD, bounds checks, dispatch) are in [Layout, SIMD, and Dispatch Fixes](references/layout-simd-dispatch-fixes.md).

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

Buffer reuse (`String::with_capacity` + `write!` instead of `format!` per iteration) is the most common fix. Also: `SmallVec` for short-lived collections, `Vec::with_capacity`/`collect` to avoid reallocation, borrowing instead of `clone()`, and `Cow<'_, str>` for conditionally-owned strings.

## Phase 4 — Fix: HashMap Replacement

**Symptom:** `std::collections::hash_map::HashMap` near top of flamegraph.

Swap std `HashMap` (SipHash, DoS-resistant but slow) for `rustc_hash::FxHashMap` (fastest for integer/pointer keys) or `ahash::AHashMap` (fastest for string keys). Expected speedup: **4–84%**. Keep std `HashMap` only when keys are user-controlled and HashDoS resistance matters. Pre-size with `with_capacity_and_hasher` to avoid rehashing.

Full code for both fixes: [Allocation and HashMap Fixes](references/allocation-and-hashmap-fixes.md).

---

## Phase 5 — Fix: Data Layout (SoA over AoS)

**Symptom:** IPC < 1.0 in `perf stat`; `memcpy`/cache-miss dominated flamegraph; loop touches only a few fields of a large struct.

Convert Array-of-Structs to Struct-of-Arrays so a hot loop only pulls in the fields it touches — full cache lines used, auto-vectorizes without `unsafe`. Expected speedup: **2–4×**. In parallel code, pad per-thread counters with `crossbeam::utils::CachePadded` to stop cache-line ping-pong (false sharing).

## Phase 6 — Fix: Rayon Parallelism

**Symptom:** Rayon overhead visible in flamegraph; parallelism isn't helping.

Rayon has ~2µs spawn overhead per unit of work — raise the serial threshold (`if n > 10_000`) when items or counts are small. Use `flat_map_iter` instead of `map().collect()` + flatten to avoid a double allocation. Use `thread_local!` buffers to eliminate per-iteration allocation. Size the pool to physical cores with `ThreadPoolBuilder`.

## Phase 7 — Fix: SIMD and Math

**Symptom:** `f32::sqrt`, trig, or nalgebra dynamic-matrix functions in hot path.

Check auto-vectorization first with `RUSTFLAGS="-C target-cpu=native"` and `--emit asm` before hand-writing SIMD. `wide::f32x8` gives ~8× throughput on AVX2 when the compiler didn't already vectorize. Prefer `nalgebra::SMatrix` (stack-allocated) over `DMatrix` (heap-allocated) for small fixed-size linear algebra.

## Phase 8 — Fix: Bounds Check Elision

**Symptom:** `core::panicking::panic_bounds_check` or `slice::index` visible in flamegraph.

Prefer iterators (`zip`, `iter()`) — the compiler proves bounds automatically. `split_at` does one bounds check then unchecked access. `get_unchecked` is `unsafe` and only safe after proving the index is valid in a comment at the call site.

## Phase 9 — Fix: Dispatch Overhead

**Symptom:** `dyn Trait` vtable calls spread across flamegraph.

Replace `Box<dyn Trait>` with enum dispatch (hand-written `match`, or the `enum_dispatch` macro) for zero-overhead monomorphized calls. Expected speedup: **2–10×** for tight loops over heterogeneous trait objects.

Full code for Phases 5–9: [Layout, SIMD, and Dispatch Fixes](references/layout-simd-dispatch-fixes.md).

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
