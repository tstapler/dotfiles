---
name: rust-profiling
description: Profile Rust binaries and benchmarks using cargo-flamegraph, samply, perf, and heaptrack. Covers CPU flamegraphs, collapsed stacks for LLM analysis, memory profiling, criterion benchmark profiling, and interactive Firefox Profiler UI.
paths: "**/*.rs"
---

# Rust Profiling

End-to-end workflow: build with debug info → collect profile → collapsed stacks (primary analysis format) → flamegraph (visualization).

**Companion skills:** [[rust-perf-tuning]] for applying CPU fixes after profiling. [[rust-memory-optimization]] for heap/allocation fixes. [[rust-parallel-processing]] for parallelism. [[rust-development]] for the full workflow map.

## Format Strategy

| Format | Best for | Tool |
|--------|----------|------|
| **Collapsed stacks** | LLM analysis, awk parsing, diffs | `perf script \| stackcollapse-perf.pl` |
| SVG flamegraph | Shareable, self-contained | `cargo flamegraph` |
| Firefox Profiler | Interactive human exploration | `samply record` |
| Criterion HTML | Benchmark regression tracking | `cargo bench` |
| heaptrack | Memory allocations + live heap | `heaptrack ./binary` |

**Use collapsed stacks for LLM analysis.** Format: `frame1;frame2;leaf N` — same as Go's pprof collapsed format.

---

## Prerequisites

```bash
# cargo-flamegraph (wraps perf/dtrace)
cargo install flamegraph

# samply — Mozilla's profiler, Firefox Profiler UI
cargo install samply

# Linux perf (Manjaro/Arch)
sudo pacman -S perf

# heaptrack (Arch/Manjaro)
sudo pacman -S heaptrack

# Brendan Gregg FlameGraph scripts (collapse + render)
git clone https://github.com/brendangregg/FlameGraph /opt/FlameGraph
# Add to PATH or use full path below
```

### Required: debug info in release builds

Add to `Cargo.toml` (workspace or per-crate):

```toml
[profile.release]
debug = 1          # line numbers only (minimal overhead) — use for profiling
# debug = true     # full DWARF — use when you need source view in samply
```

Without this, flamegraphs show only symbol names with no source locations.

---

## Collecting a Profile (Steps 1, 2, 4, 5, 6, 8)

- **Step 1 — CPU profile a binary:** `cargo flamegraph --bin <bin> -- <args>` (simplest), `samply record` (interactive Firefox Profiler UI), or `perf record -F 997 -g --call-graph=dwarf` directly.
- **Step 2 — CPU profile a criterion benchmark:** same three tools, pointed at `--bench <name>` or the compiled bench binary in `target/release/deps/`.
- **Step 4 — Memory profiling:** `heaptrack ./binary` for peak heap / leaked / top-allocators / temporary-allocations breakdown; `valgrind --tool=dhat` for a slower, more detailed alternative.
- **Step 5 — Differential flamegraph (A/B):** capture `before.collapsed` and `after.collapsed` with perf, then `difffolded.pl before after | flamegraph.pl > diff.svg` (red = regression, blue = improvement).
- **Step 6 — Criterion regression tracking:** `cargo bench -- --save-baseline before`, then `--baseline before` after changes; HTML report at `target/criterion/report/index.html` (not stored in git).
- **Step 8 — perf quick reference:** one-shot record+report, time-limited system-wide recording, attaching to a running PID, and `perf stat` for low-overhead counts.

Full commands for all of the above: [Collection Commands](references/collection-commands.md).

---

## Step 3 — Analyze Collapsed Stacks

Generate with `perf script | stackcollapse-perf.pl > cpu.collapsed`. From there, `awk` extracts top leaf frames by self-sample count or filters to stacks touching a specific function/crate; a short Python script gives a percentage breakdown per leaf frame. Full commands and the Python script: [Collapsed Stack Analysis](references/collapsed-stack-analysis.md).

---

> For applying targeted fixes to hotspots found in the flamegraph, apply the `rust-perf-tuning` skill.

## Step 7 — Hotspot Patterns and Fixes

| Pattern in flamegraph | Diagnosis | Fix |
|-----------------------|-----------|-----|
| `alloc::vec::Vec::push` dominant | Reallocation churn | `Vec::with_capacity(n)` upfront |
| `std::collections::HashMap` in hot loop | Hash overhead | `FxHashMap` / `rustc-hash` for integer keys |
| `clone()` in hot path | Unnecessary copies | Borrow instead; `Arc` for shared read |
| `fmt::Display` / `format!()` in loop | String formatting | Pre-format outside loop; use `write!` |
| `rayon::iter::*` overhead > work | Parallel overhead exceeds gain | Raise chunk size; use serial for small N |
| `parking_lot::Mutex::lock` | Lock contention | Reduce scope; use `RwLock` for readers; shard |
| `memcpy` / `memmove` dominant | Data movement | Process in-place; use slices not owned Vec |
| `f64::sqrt` / `f32::sqrt` dominant | Math bound | Check if needed every iteration; batch SIMD |
| `nalgebra::*` slow | Linear algebra allocation | Use stack-allocated `nalgebra::SMatrix` |
| `bytemuck::cast_slice` in loop | Re-casting repeatedly | Cast once outside loop |

Rust-specific monomorphization-bloat check (`nm --demangle`, `cargo bloat`) is in [Collapsed Stack Analysis](references/collapsed-stack-analysis.md).

---

## Quick Reference

| Goal | Command |
|------|---------|
| CPU flamegraph (binary) | `cargo flamegraph --bin proextract -- <args>` |
| CPU flamegraph (bench) | `cargo flamegraph --bench bpa_bench -- --bench <name>` |
| Interactive profiler | `samply record ./target/release/proextract <args>` |
| Collapsed stacks | `perf record -g ... && perf script \| stackcollapse-perf.pl > out.collapsed` |
| Diff two profiles | `/opt/FlameGraph/difffolded.pl before.collapsed after.collapsed \| flamegraph.pl > diff.svg` |
| Heap allocations | `heaptrack ./target/release/proextract <args>` |
| Bench regression | `cargo bench -- --baseline before` |
| Binary size breakdown | `cargo bloat --release --crates` |

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `rust-perf-tuning` | Apply targeted optimizations once hotspots are identified |
| `code-debugging` | Investigate correctness bugs uncovered while profiling |
| `github-actions-debugging` | Debug CI failures in benchmark or profiling jobs |

## Common Pitfalls

- **Missing debug symbols** — profile shows `[unknown]` frames. Add `debug = 1` to `[profile.release]`.
- **Inlined frames hidden** — `debug = 1` keeps symbols but may not preserve inlined frames; use `debug = true` for full detail at cost of slower link.
- **perf not finding kernel symbols** — run `echo 0 | sudo tee /proc/sys/kernel/perf_event_paranoid` or run perf as root.
- **`--call-graph=dwarf` vs `fp`** — DWARF is required when frame pointers are omitted (default for Rust); `fp` is faster but unreliable without `-C force-frame-pointers=yes`.
- **Profiling debug build** — always profile `--release`; debug builds are dominated by bounds checks and unoptimized code.
- **Short samples** — Run for at least 10–30 seconds under representative load; short profiles miss infrequent-but-slow paths.
- **Criterion warmup in flamegraph** — cargo-flamegraph profiles include the Criterion warmup phase. Pass `-- --bench --warm-up-time 0` to minimize warmup in the profile.
- **ASLR jitter in collapsed stacks** — addresses vary per run; collapsed stacks use symbol names so this is fine.
