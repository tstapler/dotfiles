# Phase 8 — Algorithm Patterns

## Map-Reduce

```rust
// Best for: independent per-item work, aggregation at end
let word_counts: HashMap<String, usize> = documents
    .par_iter()
    .flat_map_iter(|doc| doc.words())
    .fold(HashMap::new, |mut map, word| { *map.entry(word).or_insert(0) += 1; map })
    .reduce(HashMap::new, |mut a, b| {
        for (k, v) in b { *a.entry(k).or_insert(0) += v; }
        a
    });
```

## Pipeline Parallelism (stages in parallel, bounded backpressure)

```rust
use crossbeam::channel::bounded;
use std::thread;

// 3-stage pipeline: bounded channels = automatic backpressure
let (tx1, rx1) = bounded::<RawData>(128);
let (tx2, rx2) = bounded::<Processed>(128);

let reader = thread::spawn(move || {
    for item in source { tx1.send(item).unwrap(); }
    drop(tx1);  // signals end-of-stream
});
let transformer = thread::spawn(move || {
    for item in rx1.iter() { tx2.send(transform(item)).unwrap(); }
});
let writer = thread::spawn(move || {
    for item in rx2.iter() { write_output(item); }
});

reader.join().unwrap();
transformer.join().unwrap();
writer.join().unwrap();
```

## Work Queue / Task Stealing (custom scheduler)

```rust
use crossbeam::deque::{Injector, Stealer, Worker};

let global: Injector<Task> = Injector::new();
let workers: Vec<Worker<Task>> = (0..n_threads).map(|_| Worker::new_lifo()).collect();
let stealers: Vec<Stealer<Task>> = workers.iter().map(|w| w.stealer()).collect();

fn worker_thread(local: Worker<Task>, stealers: &[Stealer<Task>], global: &Injector<Task>) {
    loop {
        let task = local.pop()
            .or_else(|| global.steal_batch_and_pop(&local).success())
            .or_else(|| stealers.iter().map(|s| s.steal()).find_map(|s| s.success()));
        match task {
            Some(t) => execute(t),
            None => break,
        }
    }
}
```

## SPMD — MPI + Rayon Hybrid

```
mpirun -np N_NODES --bind-to socket ./mybinary
Each rank: rayon par_iter over its data partition (N_CPU_CORES threads)
Collective: allreduce for aggregation, barrier for synchronization
Result: N_NODES × N_CORES total parallelism
```

## Streaming / Chunked (data doesn't fit in RAM)

```rust
// Process 10GB array in 64MB chunks — RAM usage: O(chunk_size), not O(total)
let results: Vec<f64> = (0..total_items)
    .collect::<Vec<_>>()
    .par_chunks(chunk_size)
    .flat_map(|chunk| {
        let data = load_chunk_from_disk(chunk);
        data.par_iter().map(process).collect::<Vec<_>>()
    })
    .collect();
```

---

# Phase 9 — Profiling Parallel Programs

## Verify it's actually parallel

```bash
# Count threads during execution
watch -n 0.1 "cat /proc/$(pgrep mybinary)/status | grep Threads"

# htop: visually see per-core utilization — should see N cores at ~100%
htop
```

## Identify work imbalance (one core hot, others idle)

```bash
# Record all CPUs simultaneously
perf record -F 997 -a -g --call-graph=dwarf -- ./target/release/mybinary
perf report --sort=cpu,symbol --no-children | head -60
# If one CPU contributes > 50% of samples: work imbalance or serial bottleneck
```

## Memory bandwidth bound check

```bash
perf stat -e cache-misses,cache-references,instructions,cycles -- ./mybinary
# cache-miss rate > 5% → memory-bound → more threads won't help, fix data layout first
```

## tokio-console for async task profiling

```toml
console-subscriber = "0.4"
tokio = { version = "1", features = ["full", "tracing"] }
```

```bash
# Install and run
cargo install tokio-console
tokio-console
# Shows: per-task poll count, busy time, idle time, wake counts
# Look for: tasks stuck in "Idle" → blocked on lock or missing wakeup
```

## tracing for parallel observability

```toml
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }
```

```rust
use tracing::{info_span, instrument};

#[instrument(fields(items = data.len()))]
async fn process_batch(data: &[Item]) {
    data.par_iter().for_each(|item| {
        let _s = info_span!("process_item", id = item.id).entered();
        process(item);
    });
}
// RUST_LOG=info ./mybinary — see per-batch timings
```

---

# Phase 10 — Anti-Patterns and Fixes

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

## False sharing fix

```rust
use crossbeam::utils::CachePadded;

// Before: all counters on same cache line
let counters: Vec<u64> = vec![0u64; n_threads];

// After: each counter on its own 64-byte cache line
let counters: Vec<CachePadded<u64>> = (0..n_threads).map(|_| CachePadded::new(0u64)).collect();
```

## Mutex bottleneck fix with rayon fold

```rust
// Bad: global lock per item
let results = Mutex::new(Vec::new());
data.par_iter().for_each(|x| results.lock().unwrap().push(process(x)));

// Good: thread-local accumulation, merge once
let results: Vec<Output> = data
    .par_iter()
    .fold(Vec::new, |mut v, x| { v.push(process(x)); v })
    .reduce(Vec::new, |mut a, mut b| { a.append(&mut b); a });
```
