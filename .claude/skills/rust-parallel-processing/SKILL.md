---
name: rust-parallel-processing
description: Exploit CPU, GPU, and multi-machine parallelism in Rust. Covers rayon (data parallelism), tokio (task/async parallelism), SIMD (auto-vectorization + wide crate), wgpu/cudarc/candle (GPU compute and ML), tonic/tarpc/quinn (multi-machine RPC), MPI/ractor/DataFusion (HPC and distributed), algorithm patterns (map-reduce, pipeline, work-stealing, SPMD), profiling parallel programs, and common anti-patterns. Companion to rust-profiling (collect data first) and rust-perf-tuning (single-core fixes).
paths: "**/*.rs"
metadata:
  type: feedback
---

# Rust Parallel Processing

End-to-end workflow: identify bottleneck → choose the right layer → implement → verify scaling.

**Companion skills:** [[rust-profiling]] to measure serial fraction and hotspots first. [[rust-perf-tuning]] for single-core CPU optimizations (caches, allocations, SIMD) that multiply with parallelism. [[rust-memory-optimization]] when parallel work amplifies allocation pressure. [[rust-development]] for the full Rust development workflow.

---

## Phase 0 — Decision Tree: Which Layer Do You Need?

Before writing code, identify your bottleneck:

```
Is the work CPU-bound or I/O-bound?
├── I/O-bound → tokio async tasks (§2). Parallelism won't help.
└── CPU-bound
    ├── Data fits in one machine?
    │   ├── Data is numeric/homogeneous arrays? → SIMD first (§3), then rayon (§1)
    │   ├── Independent tasks (embarrassingly parallel)? → rayon par_iter (§1)
    │   ├── Tasks have async dependencies? → tokio JoinSet + spawn_blocking (§2)
    │   └── N > ~1M ops AND arithmetic intensity > 10 ops/byte? → GPU (§4)
    └── Data doesn't fit one machine or latency budget requires fan-out?
        ├── Tightly coupled, numerical, HPC cluster? → MPI (§7)
        ├── Stateful event-driven services? → actors via ractor (§7)
        └── Data pipeline / SQL-style? → DataFusion + Ballista (§7)
```

**Amdahl's Law sanity check before starting:**
```
Max speedup = 1 / (serial_fraction + parallel_fraction / N_cores)
10% serial code → max 10× speedup on infinite cores
5% serial code → max 20× speedup
```
Profile serial fraction first with [[rust-profiling]]. If it's > 20%, fix that before adding parallelism.

---

## Phase 1 — CPU Data Parallelism: Rayon

**#1 impact:** `par_iter()` on an existing `Vec` — near-zero code change, near-linear speedup for CPU-bound work with items > ~10µs each.

Core API: `par_iter().map().sum()/.collect()`, `par_chunks` for cache-friendly contiguous work, `fold`+`reduce` for per-thread accumulation without shared state, `rayon::join` for divide-and-conquer, `rayon::scope` for structured parallel tasks, and thread-local buffers to avoid per-item allocation. Rayon's Chase-Lev work-stealing deque load-balances irregular workloads automatically.

**Skip rayon when:** work is I/O-bound, items are < ~10µs, total items < ~10k, you're already inside an async executor (use `spawn_blocking` instead), or you'd otherwise share a `Mutex<Vec<T>>` per item (use `fold`/`reduce` instead).

## Phase 2 — CPU Task Parallelism: Tokio Async

**#1 impact:** `JoinSet` for bounded fan-out of independent async tasks.

`spawn` for async tasks, `spawn_blocking` for CPU-bound/sync work so it doesn't block the executor, `spawn_local` for non-`Send` types. `JoinSet` is the safe default for concurrent fan-out (auto-cancels on drop); `FuturesUnordered` is faster for hot paths. Bound concurrency with `tokio::sync::Semaphore`. Bridge rayon work into async via `spawn_blocking`.

For full rayon and tokio code examples, see [Rayon and Tokio](references/rayon-and-tokio.md).

---

## Phase 3 — CPU SIMD

**#1 impact:** Enable `target-cpu=native` first — the compiler auto-vectorizes more than most people expect. Check with `--emit asm` before reaching for manual SIMD; only add `wide::f32x8`/`u8x32` if the compiler didn't already vectorize the loop.

## Phase 4 — GPU Compute

**Rule of thumb:** only worth it above ~1M ops per kernel launch, arithmetic intensity > ~10 ops/byte, and when launch/transfer overhead (5–50µs, ~125µs for 4MB over PCIe 4.0) is amortized. Below ~64KB, CPU wins. `wgpu` for cross-platform (Vulkan/Metal/DX12/WebGPU, no NVIDIA required); `cudarc` for NVIDIA-only maximum performance.

## Phase 5 — GPU ML/Tensor Acceleration

Default to a Python subprocess unless you need Rust-native inference. `candle` (HuggingFace, pure Rust) for inference without a Python dependency or for WASM targets; `tch-rs` for LibTorch bindings; `burn` when the backend (wgpu/cuda/tch/ndarray) needs to be a compile-time swap.

For full SIMD and GPU code examples, see [SIMD and GPU](references/simd-and-gpu.md).

---

## Phase 6 — Multi-Machine: Message Passing

`tonic` (gRPC) for cross-language, schema-first, production-grade RPC; `tarpc` for simpler Rust-only RPC without protobuf; `quinn` (QUIC) when head-of-line blocking or 0-RTT reconnection matters; ZeroMQ push/pull for HPC scatter-gather pipelines.

## Phase 7 — Multi-Machine: Distributed Compute

`mpi` (+ rayon hybrid) for tightly coupled numerical HPC with collective ops (allreduce, scatter/gather) — standard pattern is `mpirun -np N_NODES` with each rank running rayon across its cores. `ractor` for Erlang-style stateful actors with fault isolation. `datafusion` (+ `ballista` for the distributed scheduler) for SQL-style distributed analytics.

For full RPC and distributed-compute code examples, see [Distributed Computing](references/distributed-computing.md).

---

## Phase 8 — Algorithm Patterns

Map-reduce (`fold`+`reduce` to a `HashMap`), pipeline parallelism (bounded `crossbeam::channel` stages for automatic backpressure), work-stealing queues (`crossbeam::deque::Injector`/`Worker`/`Stealer` for a custom scheduler), SPMD (MPI+rayon hybrid), and chunked streaming (`par_chunks` over data loaded incrementally, so RAM usage is O(chunk) not O(total)).

## Phase 9 — Profiling Parallel Programs

Verify actual parallelism with `htop`/`/proc/.../status` thread counts. Find work imbalance with `perf record -a -g` sorted by CPU. Check memory-bandwidth-bound work with `perf stat -e cache-misses,cache-references`. Use `tokio-console` for async task stalls and `tracing` spans for per-batch timing.

For full algorithm-pattern and profiling code examples, see [Algorithm Patterns and Anti-Patterns](references/algorithm-patterns-and-antipatterns.md) (also covers Phase 10 below).

## Phase 10 — Anti-Patterns and Fixes

| Anti-pattern | Why it fails | Fix |
|---|---|---|
| `Mutex<Vec<T>>` per rayon item | Every item acquires global lock → serial | `fold` into thread-local vecs, `reduce` to merge |
| Rayon inside `tokio::spawn` | Blocks async executor thread pool | `tokio::task::spawn_blocking(|| rayon_work())` |
| GPU kernel on < 64KB data | Transfer overhead > compute savings | CPU with SIMD; only GPU for > ~1M ops |
| `Arc<Mutex<T>>` for shared counter | Cache-line bouncing at high frequency | `std::sync::atomic::AtomicU64::fetch_add` |
| `par_iter` on < 1k items | Spawn overhead > work | `if n > 10_000 { par_iter() } else { iter() }` |
| False sharing in parallel writes | Adjacent cache lines ping-pong between CPUs | `crossbeam::utils::CachePadded` per slot |
| NUMA cross-socket memory access | 2–3× latency vs. local socket | `numactl --cpubind=0 --membind=0` per rank |
| MPI for simple fan-out | Heavyweight, hard to debug | Use `tonic` + `tokio` for service fan-out |
| Unbounded channel in pipeline | Producer outruns consumer → OOM | `crossbeam::channel::bounded(N)` |
| Spawning 1 tokio task per item | Task scheduling overhead | Batch items: N tasks where N = core count |

Full fix code (false sharing padding, mutex-to-fold rewrite) is in the reference above.

---

## Quick Reference: Tool by Goal

| Goal | Primary tool | Notes |
|---|---|---|
| Parallelize a `for` loop | `rayon::par_iter()` | N_cores × (serial fraction limit) |
| Recursive divide-and-conquer | `rayon::join()` | Near-linear to tree depth |
| Per-thread temp buffers | `thread_local! + RefCell<Vec>` | Eliminates N-1 allocations |
| Async fan-out of N tasks | `tokio::task::JoinSet` | Bounded by I/O latency |
| Limit concurrent tasks | `tokio::sync::Semaphore` | Prevents OOM / thundering herd |
| CPU-bound work from async | `spawn_blocking(|| rayon_work())` | Unblocks async executor |
| 8-wide float math | `wide::f32x8` or auto-vectorize | Up to 8× throughput |
| Matrix/tensor ops on GPU | `candle` or `tch-rs` | 10–1000× vs. CPU |
| Custom GPU kernel | `wgpu` (cross-GPU) / `cudarc` (NVIDIA) | Workload-dependent |
| Multi-service RPC | `tonic` (cross-lang) / `tarpc` (Rust) | Network latency bound |
| HPC cluster numerical | `mpi` + `rayon` hybrid | N_nodes × N_cores |
| Fault-tolerant stateful actors | `ractor` | Event-driven concurrency |
| Distributed SQL/analytics | `datafusion` + `ballista` | Partition-count linear |
| Pipeline with backpressure | `crossbeam::channel::bounded` | CPU-bound stages |
| Detect work imbalance | `perf record -a` + `htop` | Diagnostic |
| Debug async task stalls | `tokio-console` | Diagnostic |

---

## Related Skills

| Skill | When to use it instead or alongside |
|---|---|
| [[rust-profiling]] | **Always run first** — measure serial fraction and hotspots before adding parallelism |
| [[rust-perf-tuning]] | Single-core CPU optimizations (caches, allocations, SIMD baselines) that compound with parallelism |
| [[rust-memory-optimization]] | When parallel work amplifies allocation pressure or causes OOM under concurrent load |
| [[rust-development]] | Hub skill — links all Rust skills and provides workflow overview |
