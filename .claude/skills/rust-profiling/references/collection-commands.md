# Step 1 — CPU Profile a Binary

## cargo flamegraph (simplest)

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

## samply (interactive Firefox Profiler UI)

```bash
# Record then auto-open browser
samply record ./target/release/proextract pipeline \
  --scan-dir /path/to/scan --output-dir /tmp/out

# Explicit frequency
samply record --rate 4000 ./target/release/proextract bpa --input cloud.ply
```

## perf directly (Linux)

```bash
# Record
perf record -F 997 -g --call-graph=dwarf -- ./target/release/proextract bpa --input cloud.ply

# Quick text summary
perf report --stdio --no-children | head -60

# Collapsed stacks (for LLM analysis or custom flamegraph)
perf script | /opt/FlameGraph/stackcollapse-perf.pl > cpu.collapsed
```

---

# Step 2 — CPU Profile a Criterion Benchmark

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

# Step 4 — Memory Profiling with heaptrack

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

## DHAT (Valgrind heap profiler — slower but more detailed)

```bash
valgrind --tool=dhat --dhat-out-file=dhat.out \
  ./target/release/proextract bpa --input small_cloud.ply
# Opens at: https://nnethercote.github.io/dh_view/dh_view.html
# Upload dhat.out to view
```

---

# Step 5 — Differential Flamegraph (A/B comparison)

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

# Step 6 — Criterion Benchmark Regression Tracking

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

# Step 8 — Linux perf Quick Reference

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
