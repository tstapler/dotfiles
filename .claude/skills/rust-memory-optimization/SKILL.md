---
name: rust-memory-optimization
description: Reduce Rust memory usage, eliminate allocation churn, size types precisely, apply custom allocators and arenas, build bounded telemetry buffers, and detect leaks. Covers the full cycle: measure → diagnose → fix → verify. Companion to rust-profiling (CPU flamegraphs) and rust-perf-tuning (CPU throughput).
paths: "**/*.rs"
metadata:
  type: feedback
---

# Rust Memory Optimization

End-to-end workflow: measure RSS / heap profile → diagnose pattern → apply fix → assert in CI.

**Companion skills:** [[rust-profiling]] for heaptrack collection and collapsed stacks. [[rust-perf-tuning]] for CPU throughput fixes after memory is addressed. [[rust-parallel-processing]] for parallelism patterns that can amplify or reduce allocation pressure. [[rust-development]] for the full workflow map.

---

## Phase 0 — Measure First

Never optimize by intuition. Pick the tool that matches your observable symptom.

| Symptom | Tool | Cost |
|---|---|---|
| High peak RSS / OOM | heaptrack, Massif | 5–20× slowdown |
| Allocation churn (GC pressure) | heaptrack "temporary allocations" | 5–20× slowdown |
| Leak suspect | dhat (in-process), cargo-valgrind | 10–100× slowdown |
| CI regression gate | `dhat` crate with assertions | compile-time flag |
| Long-running server heap growth | tikv-jemallocator profiling | ~10–30% overhead |
| Quick coarse check | `/proc/self/status` RSS | zero overhead |

For heaptrack commands, dhat CI setup, `/proc` RSS checks, and Valgrind DHAT, see [Measurement Tooling](references/measurement-tooling.md).

---

## Phase 1 — Type Size Optimization

**#1 impact:** `NonZero*` niche — `Option<NonZeroU32>` = 4 bytes, not 8.

Audit sizes with a `const _: () = assert!(size_of::<T>() <= N)` guard in CI and `cargo bloat`. Other high-value fixes: box large enum variants so small variants don't pay their padding cost, pack boolean flags with `bitflags`, order `#[repr(C)]` fields largest-alignment-first, and use `u32`/`u8` indices instead of `usize` for bounded counts.

## Phase 2 — Compact String and Collection Types

**#1 impact:** `CompactString` — strings ≤ 24 bytes stored inline, zero heap allocation.

`compact_str` and `smol_str` avoid heap allocation for short strings; `arrayvec`/`tinyvec` avoid it for small fixed-or-bounded collections; a hand-rolled string pool turns N allocations into one.

For full code examples of both phases, see [Type Sizing and Collections](references/type-sizing-and-collections.md).

---

## Phase 3 — Allocator Swap

**#1 impact:** `mimalloc` — 5–30% allocation throughput improvement, 5 lines of code.

Swap the global allocator for `mimalloc` (general-purpose, all platforms) or `tikv-jemallocator` (long-running servers, supports heap profiling). Always benchmark — it's a global change and can regress the wrong workload.

## Phase 4 — Arenas, Pools, and Scoped Allocation

**When pools beat malloc:** allocation rate > ~10,000/s for same-sized objects (check heaptrack "temporary allocations").

`bumpalo` gives O(1) bulk cleanup for a scope of intermediates; `typed_arena` supports `Drop`; `slotmap` gives pool-like O(1) insert/remove with use-after-free protection; a thread-local `Vec<Vec<u8>>` pool needs no crate at all.

## Phase 5 — Zero-Copy Patterns

**#1 impact:** `bytes::Bytes` — share a buffer across tasks without copying.

`bytes::Bytes` slices are O(1) refcount bumps; `memmap2` avoids upfront allocation for large files (> 64MB); `zerocopy` transmutes `#[repr(C)]` byte slices to typed structs with no memcpy.

For full code examples of allocators, arenas, and zero-copy patterns, see [Allocators and Memory Regions](references/allocators-and-memory-regions.md).

---

## Phase 6 — Reference Counting Optimization

**#1 impact:** Borrow instead of `Arc::clone` inside loops — one clone, not N.

Prefer `Rc<T>` over `Arc<T>` for single-threaded data (no atomic overhead). Inside hot loops, borrow the `Arc` once outside the loop rather than cloning per-iteration — each `Arc::clone`/`drop` is an atomic op that thrashes the refcount cache line under contention. `triomphe::Arc` drops the weak count when `downgrade()` is never used; `arc-swap` gives lock-free hot-swappable shared state, beating `RwLock<Arc<T>>` for many concurrent readers.

## Phase 7 — Bounded Telemetry Buffers

**#1 impact:** `ArrayQueue` — lock-free MPMC ring buffer, allocated once at startup.

Size the ring buffer from your item's compact-type footprint (e.g., a `SmolStr`+`CompactString` span ≈ 256B) times the capacity needed to cover your overflow window. `crossbeam::ArrayQueue` for MPMC, `ringbuf` for SPSC (faster when producer/consumer are separate threads). Always pair a drop strategy (drop-newest, drop-oldest, or block) with an `AtomicU64` dropped-count exposed in exports.

## Phase 8 — Leak Detection

**#1 impact:** `dhat` CI assertions — catch leaks at PR time, not in production.

`dhat`'s in-process `HeapStats` assertions run on stable Rust and are CI-friendly; LeakSanitizer/AddressSanitizer (nightly) and `cargo-valgrind` (stable, slowest) catch what dhat misses. No automated tool detects `Arc` cycles — prevent them with arena indices or `Weak` back-references, and audit `Box::leak` usage in CI.

For full code examples of refcounting, ring buffers, and leak detection, see [Refcounting and Telemetry Buffers](references/refcounting-and-telemetry-buffers.md).

---

## Phase 9 — Verify the Fix

Always compare numbers, not intuition:

```bash
# Before fix — capture baseline RSS after operation:
./target/release/mybinary --scenario load-8k-pages
# Record VmRSS from /proc or heaptrack peak

# After fix — compare:
heaptrack ./target/release/mybinary --scenario load-8k-pages
heaptrack_print heaptrack.*.zst | grep "peak heap"

# Criterion memory benchmark (dhat integration):
cargo bench --features dhat-heap -- --bench memory_bench
```

**Minimum bar:** heaptrack peak must decrease. For allocation elimination, `dhat::HeapStats::total_blocks` must decrease. RSS reduction ≥ 1 page (4KB) — smaller changes are within OS noise.

---

## Quick Reference: Fix by Symptom

| Symptom in heaptrack | Diagnosis | Fix | Expected savings |
|---|---|---|---|
| High "temporary allocations" for String | Repeated short string alloc | `CompactString` / `SmolStr` | 0–∞ allocs depending on length |
| High "temporary allocations" for Vec | Vec built and dropped in loop | `ArrayVec` or buffer reuse | O(N) allocs → O(1) |
| Large "peak heap", enum type dominant | Large enum variant padds all | Box the large variant | N× depending on ratio |
| `Arc::clone` in heaptrack hot path | Clone storm | Borrow instead, clone once | N-1 atomic ops per loop |
| "leaked" bytes in heaptrack | True leak | Arc cycle check, `Box::leak` audit | All leaked bytes |
| `Vec<String>` dominant | N heap allocs for N strings | String pool or `SmolStr` | N allocs → 1 |
| Ring buffer allocates per item | No pre-allocated ring | `ArrayQueue` / `ringbuf` | N allocs → 0 |
| Option<T> larger than T | Missing niche optimization | Wrap inner in `NonZeroU32` etc. | 4–8 bytes per instance |

## Crate Quick Reference

| Crate | Use for | Size overhead |
|---|---|---|
| `compact_str` | Drop-in `String` replacement | 24B inline stack |
| `smol_str` | Immutable O(1)-clone strings | 24B + optional Arc |
| `arrayvec` | Fixed-cap stack arrays/strings | Stack only |
| `tinyvec` | SmallVec without unsafe | Stack + heap spill |
| `bytes` | Zero-copy shared buffers | Arc per allocation |
| `bumpalo` | Per-scope arena | One arena block |
| `typed_arena` | Homogeneous arena with Drop | One arena block |
| `slotmap` | Pool-like O(1) insert/remove | 1 Vec |
| `triomphe` | Arc without weak count | Saves 8B per allocation |
| `arc-swap` | Lock-free config hot-swap | One ArcSwap per slot |
| `crossbeam::ArrayQueue` | Bounded MPMC ring buffer | N × sizeof(T) once |
| `ringbuf` | Bounded SPSC ring buffer | N × sizeof(T) once |
| `bitflags` | Flag types | 1–4 bytes |
| `memmap2` | Zero-copy file reads | OS pages only |
| `zerocopy` | Transmute bytes to structs | Zero |
| `mimalloc` | Faster global allocator | ≈0 |
| `tikv-jemallocator` | Server allocator + profiling | ≈0 |
| `dhat` | CI heap assertions | Test-only |

---

## Common Mistakes

From *The Rust Performance Book* and Jon Gjengset's *Rust for Rustaceans*:

1. **`String` for short-lived or repeated identifiers** — use `CompactString` or `&str`
2. **`format!()` in hot paths** — allocates; use `write!` into a pre-allocated buffer
3. **`Arc::clone` per iteration** — borrow for the loop's duration, clone once outside
4. **Large enum variant without boxing** — all variants pay the largest variant's cost
5. **`Arc<Mutex<T>>` everywhere** — signals misunderstood ownership; restructure to channels or arena indices
6. **Profiling debug builds** — always profile `--release`; debug is dominated by bounds checks
7. **No size guard in CI** — `const _: () = assert!(size_of::<HotType>() <= N)` catches regressions at compile time
8. **Not counting dropped spans** — add `AtomicU64` dropped counter alongside every ring buffer; include in exports

---

## Related Skills

| Skill | When to apply |
|---|---|
| [[rust-profiling]] | Collect heaptrack reports, CPU flamegraphs, collapsed stacks |
| [[rust-perf-tuning]] | Fix CPU throughput bottlenecks found after memory is addressed |
| [[code-refactoring]] | Structural refactors after type sizes and allocators are settled |
