---
name: rust-development
description: Hub skill for Rust development. Covers the full workflow from profiling → performance diagnosis → CPU/memory optimization → parallelism. Routes to the right specialist skill based on the symptom. Links all four Rust skills: rust-profiling, rust-perf-tuning, rust-memory-optimization, rust-parallel-processing.
paths: "**/*.rs"
metadata:
  type: feedback
---

# Rust Development Hub

This is a routing and overview skill. It maps symptoms to the right specialist skill and provides the overall Rust optimization workflow.

---

## Workflow: Measure → Diagnose → Fix → Verify

```
1. MEASURE        → rust-profiling
   Flamegraph, heaptrack, perf stat. Establish baseline numbers.
   Never skip. Never optimize without a number to beat.

2. DIAGNOSE       → rust-profiling + rust-perf-tuning + rust-memory-optimization
   Read the flamegraph. Is the hotspot:
   ├── CPU-bound, single-threaded? → rust-perf-tuning
   ├── Memory / allocation churn?  → rust-memory-optimization
   ├── CPU-bound but underutilized cores? → rust-parallel-processing
   └── I/O-bound? → tokio async patterns (rust-parallel-processing §2)

3. FIX            → specialist skill
   Apply the fix from the relevant specialist skill.
   Keep changes small — one variable at a time.

4. VERIFY         → rust-profiling
   Re-run the same benchmark/profiler. Confirm numbers improved.
   If not: revert, re-diagnose. Don't stack guesses.
```

---

## Skill Map: Which Skill for Which Symptom

| Symptom | Skill |
|---|---|
| "I need a flamegraph" | [[rust-profiling]] |
| "Find the CPU hotspot" | [[rust-profiling]] |
| "Benchmark before/after" | [[rust-profiling]] |
| "Hot loop is slow" | [[rust-perf-tuning]] |
| "HashMap is too slow" | [[rust-perf-tuning]] (FxHashMap) |
| "Enable LTO or PGO" | [[rust-perf-tuning]] |
| "High RSS / OOM" | [[rust-memory-optimization]] |
| "Allocation churn in heaptrack" | [[rust-memory-optimization]] |
| "Bounded ring buffer for telemetry" | [[rust-memory-optimization]] |
| "Custom allocator (mimalloc, jemalloc)" | [[rust-memory-optimization]] |
| "Memory leak" | [[rust-memory-optimization]] |
| "par_iter() / rayon" | [[rust-parallel-processing]] |
| "Async fan-out with tokio" | [[rust-parallel-processing]] |
| "GPU compute (wgpu, cudarc)" | [[rust-parallel-processing]] |
| "ML inference in Rust (candle)" | [[rust-parallel-processing]] |
| "Multi-machine (tonic, MPI, ractor)" | [[rust-parallel-processing]] |
| "SIMD / auto-vectorization" | [[rust-parallel-processing]] |

---

## Rust Specialist Skills

| Skill | Focus |
|---|---|
| [[rust-profiling]] | Flamegraphs (cargo-flamegraph, samply), heaptrack, perf, criterion. Collect data first — every other skill depends on this. |
| [[rust-perf-tuning]] | CPU throughput: data-oriented design, FxHashMap, LTO/PGO, SIMD baselines, bounds check elimination, hot-loop restructuring. |
| [[rust-memory-optimization]] | RSS reduction: compact types, custom allocators, arenas, bounded ring buffers, zero-copy (bytes, memmap2, zerocopy), leak detection (dhat, LeakSanitizer). |
| [[rust-parallel-processing]] | Scaling: rayon (data parallelism), tokio (async tasks), SIMD, GPU (wgpu/cudarc/candle), multi-machine (tonic/MPI/ractor/DataFusion). |

---

## Essential Cargo Config

```toml
# .cargo/config.toml — apply to all builds in this workspace
[build]
rustflags = ["-C", "target-cpu=native"]  # enables AVX2, SSE4.2 auto-vectorization

[profile.release]
lto = "thin"          # ~5-10% speedup from cross-crate inlining
codegen-units = 1     # single CGU → more inlining opportunities
opt-level = 3         # default for release

[profile.profiling]   # flamegraph-friendly: fast but readable symbols
inherits = "release"
debug = 1             # line tables only (small binary, readable stacks)
```

## Key Profiling Commands (quick reference)

```bash
# CPU flamegraph
cargo flamegraph --bin mybinary -- args
# or: samply record ./target/release/mybinary

# Heap profile
heaptrack ./target/release/mybinary
heaptrack_print heaptrack.mybinary.PID.zst | head -40

# Allocation benchmark
cargo bench -- --profile-time=5

# tokio async task visibility
cargo install tokio-console && tokio-console
```

## Dependency Version Hygiene

Check for outdated dependencies with:
```bash
cargo install cargo-outdated   # one-time install
cargo outdated                 # show all deps behind latest
cargo outdated --root-deps-only  # only direct deps (less noise)
```

When `cargo build` resolves a lower version than available, it prints:
```
Adding tokio-tungstenite v0.24.0 (available: v0.29.0)
```
**Always use the latest available version** — update Cargo.toml to the version shown in parentheses.

### Known breaking changes between major versions

| Crate | Old version | New version | Breaking change |
|---|---|---|---|
| `reqwest` | `0.12` | `0.13` | Feature `rustls-tls` renamed to `rustls` |
| `tokio-tungstenite` | `0.24` | `0.29` | `Message::Text(String)` → `Message::Text(Utf8Bytes)`, `Message::Binary(Vec<u8>)` → `Message::Binary(Bytes)` — both accept `.into()` from the old types |
| `chrono` | any | `0.4` | `local-offset` feature doesn't exist on older pinned versions; use `serde` feature instead and call `Local::now()` directly |

---

## Essential Crate Quick Reference

| Crate | Layer | Use for |
|---|---|---|
| `rayon` | CPU parallel | Data parallelism — par_iter(), join(), scope() |
| `tokio` | Async | I/O-bound + task fan-out, JoinSet, Semaphore |
| `wide` | SIMD | Manual AVX2 without nightly (f32x8, u8x32) |
| `crossbeam` | Concurrent | Bounded channels, deques, CachePadded |
| `wgpu` | GPU | Cross-platform compute (Vulkan/Metal/DX12) |
| `cudarc` | GPU | NVIDIA CUDA — maximum GPU performance |
| `candle` | GPU/ML | Pure-Rust inference, HuggingFace model weights |
| `tonic` | Network | gRPC — cross-language RPC |
| `tarpc` | Network | Rust-only RPC — simpler, no protobuf |
| `mpi` | HPC | Multi-machine numerical — allreduce, scatter |
| `ractor` | Distributed | Erlang-style actors — fault-tolerant stateful services |
| `datafusion` | Analytics | Distributed SQL over Parquet / Arrow |
| `compact_str` | Memory | Drop-in String replacement — inline ≤ 24B |
| `mimalloc` | Memory | Faster global allocator |
| `bumpalo` | Memory | Per-scope arena — O(1) alloc, O(1) free all |
| `dhat` | Memory | CI heap assertions — catch leaks at PR time |
| `criterion` | Bench | Statistical micro-benchmarks |
