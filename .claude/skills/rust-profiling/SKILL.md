---
name: rust-profiling
description: Profile Rust binaries and benchmarks using cargo-flamegraph, samply, perf, and heaptrack. Covers CPU flamegraphs, collapsed stacks for LLM analysis, memory profiling, criterion benchmark profiling, and interactive Firefox Profiler UI.
---

# Rust Profiling

End-to-end workflow: build with debug info → collect profile → collapsed stacks (primary analysis format) → flamegraph (visualization).

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

## Step 1 — CPU Profile a Binary

### cargo flamegraph (simplest)

```bash
# Profile a binary — runs it under perf/dtrace automatically
cargo flamegraph --bin proextract -- pipeline --scan-dir /path/to/scan --output-dir /tmp/out

# Profile a specific subcommand
cargo flamegraph --bin proextract -- bpa --input cloud.ply --output mesh.ply

# Increase frequency for short runs (default: 997 Hz; higher = more detail, more overhead)
cargo flamegraph --freq 4000 --bin proextract -- bpa --input cloud.ply

# Output goes to flamegraph.svg in current directory
xdg-open flamegraph.svg
```

### samply (interactive Firefox Profiler UI)

```bash
# Record then auto-open browser
samply record ./target/release/proextract pipeline \
  --scan-dir /path/to/scan --output-dir /tmp/out

# Explicit frequency
samply record --rate 4000 ./target/release/proextract bpa --input cloud.ply
```

### perf directly (Linux)

```bash
# Record
perf record -F 997 -g --call-graph=dwarf -- ./target/release/proextract bpa --input cloud.ply

# Quick text summary
perf report --stdio --no-children | head -60

# Collapsed stacks (for LLM analysis or custom flamegraph)
perf script | /opt/FlameGraph/stackcollapse-perf.pl > cpu.collapsed
```

---

## Step 2 — CPU Profile a Criterion Benchmark

```bash
# Flamegraph from benchmark (binary already has --bench harness)
cargo flamegraph --bench bpa_bench -- --bench ball_pivot/sphere/5000

# Profile all benchmarks in a group
cargo flamegraph --bench bpa_bench -- --bench "ball_pivot"

# samply on a benchmark
samply record ./target/release/deps/bpa_bench-* --bench "ball_pivot/sphere/5000"
# Find the binary name with: ls target/release/deps/bpa_bench-*

# perf on a criterion benchmark
perf record -F 997 -g --call-graph=dwarf \
  ./target/release/deps/bpa_bench-* --bench "ball_pivot/sphere/5000"
perf script | /opt/FlameGraph/stackcollapse-perf.pl > bench.collapsed
```

---

## Step 3 — Analyze Collapsed Stacks

### Generate collapsed stacks

```bash
# From perf recording
perf script | /opt/FlameGraph/stackcollapse-perf.pl --kernel > cpu.collapsed

# Render SVG from collapsed stacks (same as cargo flamegraph, more control)
/opt/FlameGraph/flamegraph.pl --title "proextract BPA" cpu.collapsed > flamegraph.svg
```

### awk extraction from collapsed stacks

```bash
# Top leaf frames by self-sample count
awk '{n=$NF; sub(/ [0-9]+$/,""); split($0,a,";"); leaf=a[length(a)]; count[leaf]+=$NF}
     END{for(f in count) print count[f],f}' \
  cpu.collapsed | sort -rn | head -20

# Stacks touching a specific function
grep "bpa::pivot_step" cpu.collapsed | sort -t' ' -k2 -rn | head -10

# Filter to your crate only (remove stdlib + runtime noise)
grep "proextract" cpu.collapsed | sort -t' ' -k2 -rn | head -30
```

### Python percentage breakdown

```python
from collections import defaultdict
import sys

lines = [l.strip() for l in open(sys.argv[1]) if l.strip()]
total = sum(int(l.rsplit(" ", 1)[1]) for l in lines)
by_leaf = defaultdict(int)
for line in lines:
    stack, _, count = line.rpartition(" ")
    leaf = stack.split(";")[-1]
    by_leaf[leaf] += int(count)

for count, frame in sorted((-v, k) for k, v in by_leaf.items())[:20]:
    print(f"{100*-count/total:5.1f}%  {-count:6d}  {frame}")
```

```bash
python3 analyze.py cpu.collapsed
```

---

## Step 4 — Memory Profiling with heaptrack

```bash
# Record heap allocations
heaptrack ./target/release/proextract bpa --input cloud.ply

# heaptrack writes heaptrack.<binary>.<pid>.zst
# Open GUI
heaptrack_gui heaptrack.proextract.12345.zst

# Or print text summary
heaptrack_print heaptrack.proextract.12345.zst | head -80
```

heaptrack output sections:
- **Peak heap** — maximum live memory
- **Leaked** — allocations never freed
- **Top allocators** — call stacks with highest total bytes allocated
- **Temporary allocations** — allocated and freed within same call stack (GC pressure equivalent)

### DHAT (Valgrind heap profiler — slower but more detailed)

```bash
valgrind --tool=dhat --dhat-out-file=dhat.out \
  ./target/release/proextract bpa --input small_cloud.ply
# Opens at: https://nnethercote.github.io/dh_view/dh_view.html
# Upload dhat.out to view
```

---

## Step 5 — Differential Flamegraph (A/B comparison)

```bash
# Baseline — save as before.collapsed
perf record -F 997 -g --call-graph=dwarf -- ./target/release/proextract bpa --input cloud.ply
perf script | /opt/FlameGraph/stackcollapse-perf.pl > before.collapsed

# After code change — save as after.collapsed
perf script | /opt/FlameGraph/stackcollapse-perf.pl > after.collapsed

# Differential flamegraph (red = regression, blue = improvement)
/opt/FlameGraph/difffolded.pl before.collapsed after.collapsed | /opt/FlameGraph/flamegraph.pl > diff.svg
xdg-open diff.svg
```

---

## Step 6 — Criterion Benchmark Regression Tracking

```bash
# Save a named baseline before changes
cargo bench -p proextract-pipeline -- --save-baseline before

# After changes — compare
cargo bench -p proextract-pipeline -- --baseline before

# Open HTML report
xdg-open target/criterion/report/index.html
```

Criterion reports: mean, stddev, outliers, and regression/improvement vs baseline. Stored in `target/criterion/` — **not in git by default**.

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

### Rust-specific: check for monomorphization bloat

```bash
# Symbols in the binary — large count of similar names = monomorphization
nm --demangle target/release/proextract | grep -c "fn "
cargo bloat --release --crates    # shows which crates dominate binary size
cargo bloat --release -n 30       # top 30 functions by size
```

---

## Step 8 — Linux perf Quick Reference

```bash
# One-shot: record + report
perf record -F 997 -g --call-graph=dwarf -- <cmd> && perf report --stdio --no-children | head -40

# Record with time limit (useful for long-running processes)
perf record -F 997 -g --call-graph=dwarf -a -- sleep 10  # system-wide for 10s

# Attach to running process
perf record -F 997 -g --call-graph=dwarf -p <PID> -- sleep 10

# Stat (counts, not stacks — low overhead)
perf stat -- ./target/release/proextract bpa --input cloud.ply
```

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
