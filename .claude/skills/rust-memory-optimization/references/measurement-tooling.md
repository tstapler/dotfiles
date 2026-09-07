# Phase 0 — Measurement Tooling

Never optimize by intuition. Pick the tool that matches your observable symptom.

| Symptom | Tool | Cost |
|---|---|---|
| High peak RSS / OOM | heaptrack, Massif | 5–20× slowdown |
| Allocation churn (GC pressure) | heaptrack "temporary allocations" | 5–20× slowdown |
| Leak suspect | dhat (in-process), cargo-valgrind | 10–100× slowdown |
| CI regression gate | `dhat` crate with assertions | compile-time flag |
| Long-running server heap growth | tikv-jemallocator profiling | ~10–30% overhead |
| Quick coarse check | `/proc/self/status` RSS | zero overhead |

## heaptrack (best overall)

```bash
# Arch/Manjaro
sudo pacman -S heaptrack

heaptrack ./target/release/mybinary args
heaptrack_print heaptrack.mybinary.PID.zst | head -80
heaptrack_gui heaptrack.mybinary.PID.zst    # GUI
```

Output sections to focus on:
- **Peak heap** — maximum live bytes (RSS footprint)
- **Temporary allocations** — allocated and freed within the same call stack (allocation churn, the GC-pressure equivalent)
- **Top allocators** — call stacks by total bytes (where your heap comes from)
- **Leaked** — allocations never freed

Gotcha: misses mmap-based allocations (jemalloc, mimalloc use mmap). Add `--track-mmap` if using a custom allocator.

## dhat crate — in-process CI assertions

```toml
# Cargo.toml — gate behind a feature flag so it doesn't conflict with mimalloc/jemalloc
[features]
dhat-heap = ["dhat"]
[dependencies]
dhat = { version = "0.3", optional = true }
```

```rust
#[cfg(feature = "dhat-heap")]
#[global_allocator]
static ALLOC: dhat::Alloc = dhat::Alloc;

// Zero-allocation assertion in CI:
#[test]
#[cfg(feature = "dhat-heap")]
fn span_emission_does_not_allocate() {
    let _profiler = dhat::Profiler::builder().testing().build();
    emit_span("db.saveBlocks", &attrs);
    let stats = dhat::HeapStats::get();
    dhat::assert_eq!(stats.total_blocks, 0, "span emission must be zero-alloc");
}
```

## /proc RSS (zero-overhead coarse check)

```rust
fn rss_kb() -> u64 {
    std::fs::read_to_string("/proc/self/status").ok()
        .and_then(|s| s.lines()
            .find(|l| l.starts_with("VmRSS:"))
            .and_then(|l| l.split_whitespace().nth(1))
            .and_then(|s| s.parse().ok()))
        .unwrap_or(0)
}
// Granularity: 4KB (OS page). Useless for allocations < 4KB.
// Use for graph-scale regression detection: before vs after load.
```

## Valgrind DHAT (external, detailed)

```bash
valgrind --tool=dhat ./target/release/mybinary args
# Upload dhat.out.PID → https://nnethercote.github.io/dh_view/dh_view.html
# Key insight: "Total bytes" >> "Max bytes live" = churn problem, not footprint problem
```
