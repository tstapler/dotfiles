# Phase 1 — CPU Data Parallelism: Rayon

**#1 impact:** `par_iter()` on an existing `Vec` — near-zero code change, near-linear speedup for CPU-bound work with items > ~10µs each.

```toml
rayon = "1.10"
```

## Core API

```rust
use rayon::prelude::*;

// Basic data parallelism — replaces .iter()
let sum: f64 = data.par_iter().map(|x| expensive_compute(x)).sum();

// Parallel map → collect (preserves order)
let results: Vec<Output> = data.par_iter().map(|x| process(x)).collect();

// par_chunks: bounded parallelism over large arrays
// Gives each thread a contiguous chunk — better cache behavior than par_iter on small items
let results: Vec<f64> = data
    .par_chunks(1024)
    .flat_map(|chunk| chunk.iter().map(|x| compute(x)))
    .collect();

// fold + reduce: per-thread accumulation, then merge — avoids shared state entirely
let total: u64 = data
    .par_iter()
    .fold(|| 0u64, |acc, x| acc + x.count())  // each thread has its own accumulator
    .reduce(|| 0u64, |a, b| a + b);            // merge thread results

// flat_map_iter: parallel outer, serial inner — avoids rayon overhead for inner iterations
let expanded: Vec<Item> = pages
    .par_iter()
    .flat_map_iter(|page| page.items.iter().cloned())
    .collect();
```

## Thread pool sizing

```rust
use rayon::ThreadPoolBuilder;

// For compute-bound: physical CPUs only (avoid hyperthreading overhead)
let pool = ThreadPoolBuilder::new()
    .num_threads(num_cpus::get_physical())  // crate: num_cpus = "1.16"
    .build()
    .unwrap();

pool.install(|| {
    data.par_iter().for_each(|x| process(x));
});

// Runtime override: RAYON_NUM_THREADS=8 ./mybinary
```

## Work-stealing internals (why it matters)

Rayon uses a Chase-Lev double-ended work-stealing deque per thread. Each thread pushes to its own deque's back; idle threads steal from the fronts of others. Result: automatic load balancing even when items have variable cost — no manual chunking needed. This is why rayon outperforms hand-rolled thread pools for irregular workloads.

## Divide and conquer with `rayon::join`

```rust
// Parallel merge sort
fn parallel_sort(data: &mut [i64]) {
    if data.len() <= 4096 {
        data.sort_unstable();  // serial base case
        return;
    }
    let mid = data.len() / 2;
    let (left, right) = data.split_at_mut(mid);
    rayon::join(
        || parallel_sort(left),
        || parallel_sort(right),
    );
    // merge left + right (serial)
}

// Tree traversal
fn sum_tree(node: &Node) -> u64 {
    if node.children.is_empty() { return node.value; }
    let (left_sum, right_sum) = rayon::join(
        || sum_tree(&node.children[0]),
        || node.children[1..].iter().map(sum_tree).sum::<u64>(),
    );
    node.value + left_sum + right_sum
}
```

## Per-thread temporary state without allocation

```rust
use std::cell::RefCell;

thread_local! {
    static BUF: RefCell<Vec<u8>> = RefCell::new(Vec::with_capacity(4096));
}

data.par_iter().for_each(|item| {
    BUF.with(|buf| {
        let mut buf = buf.borrow_mut();
        buf.clear();
        serialize_into(item, &mut *buf);
        write_to_output(&buf);
    });
});
// Each rayon worker thread reuses its own Vec — zero allocation per item
```

## Structured parallelism with `scope`

```rust
rayon::scope(|s| {
    s.spawn(|_| task_a());  // runs in parallel
    s.spawn(|_| task_b());  // runs in parallel
    task_c();               // runs while a and b run
});
// All tasks done here — implicit barrier
```

## `IndexedParallelIterator` vs `ParallelIterator`

- `IndexedParallelIterator`: knows its length, supports `zip`, `enumerate`, `chunks`. Implemented by `Vec`, arrays, ranges.
- `ParallelIterator`: streaming, no length. `BTreeMap`, `HashSet`, channels use this.
- `par_bridge()`: converts any `Iterator` to a `ParallelIterator` (uses a mutex internally — not zero-cost).

```rust
// Zip two parallel iterators (requires IndexedParallelIterator on both)
let dot: f64 = a.par_iter()
    .zip(b.par_iter())
    .map(|(x, y)| x * y)
    .sum();
```

## When NOT to use rayon

| Situation | Why rayon hurts | Fix |
|---|---|---|
| I/O-bound work | Threads block, executor starves | tokio async |
| Items < ~10µs of work | Spawn overhead (2µs) > gain | Serial iterator |
| < ~10k items total | Parallel overhead > serial | `if n > 10_000 { par } else { serial }` |
| Inside async executor | Blocks async worker thread | `spawn_blocking(|| rayon_work())` |
| Shared `Mutex<Vec<T>>` per item | Lock contention serializes everything | `fold` into thread-local then merge |

---

# Phase 2 — CPU Task Parallelism: Tokio Async

**#1 impact:** `JoinSet` for bounded fan-out of independent async tasks.

```toml
tokio = { version = "1", features = ["full"] }
```

## spawn variants — when to use each

```rust
// spawn: async task, runs on tokio worker thread pool
let handle = tokio::task::spawn(async move { fetch_page(url).await });

// spawn_blocking: sync/CPU-bound work on a dedicated blocking thread pool
let result = tokio::task::spawn_blocking(|| {
    heavy_cpu_work()  // doesn't block async executor
}).await?;

// spawn_local: runs on the CURRENT thread only (not Send required)
tokio::task::spawn_local(async { use_rc_type().await });
```

## JoinSet — bounded concurrent task fan-out

```rust
use tokio::task::JoinSet;

let mut set: JoinSet<Result<Output, Error>> = JoinSet::new();

for item in items {
    // Limit concurrency: drain when full
    if set.len() >= 16 {
        set.join_next().await;  // wait for one to finish
    }
    set.spawn(async move { process(item).await });
}

while let Some(result) = set.join_next().await {
    match result? {
        Ok(output) => handle(output),
        Err(e) => log_error(e),
    }
}
```

## FuturesUnordered vs JoinSet

- `FuturesUnordered` (from `futures` crate): faster for hot paths (no allocation per future), output order is completion order.
- `JoinSet`: safer (auto-cancels on drop), easier API, integrates with tokio's abort handles. Use for most production code.

```rust
use futures::stream::{FuturesUnordered, StreamExt};

let mut futs: FuturesUnordered<_> = urls.iter()
    .map(|url| fetch(url))
    .collect();

while let Some(result) = futs.next().await {
    process(result?);
}
```

## Semaphore for bounding concurrency

```rust
use tokio::sync::Semaphore;
use std::sync::Arc;

let sem = Arc::new(Semaphore::new(8));  // max 8 concurrent

let handles: Vec<_> = items.iter().map(|item| {
    let sem = sem.clone();
    tokio::spawn(async move {
        let _permit = sem.acquire().await.unwrap();  // blocks until slot available
        do_work(item).await
    })
}).collect();
```

## Rayon from Tokio — bridging sync and async

```rust
// Offload rayon work to blocking thread pool, get result back in async
async fn parallel_process(data: Vec<Input>) -> Vec<Output> {
    tokio::task::spawn_blocking(move || {
        data.par_iter().map(|x| cpu_heavy(x)).collect()
    }).await.expect("rayon task panicked")
}
```

## Producer-consumer pipeline

```rust
use async_channel::{bounded, Receiver, Sender};  // crate: async-channel = "2"

async fn pipeline(input: Vec<Item>) {
    let (tx, rx): (Sender<Processed>, Receiver<Processed>) = bounded(128);

    let producer = tokio::spawn(async move {
        for item in input {
            tx.send(stage1(item).await).await.unwrap();
        }
    });

    let consumer = tokio::spawn(async move {
        while let Ok(item) = rx.recv().await {
            stage2(item).await;
        }
    });

    let _ = tokio::join!(producer, consumer);
}
```
