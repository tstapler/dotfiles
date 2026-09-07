# Phase 6 — Reference Counting Optimization

**#1 impact:** Borrow instead of `Arc::clone` inside loops — one clone, not N.

## Arc vs Rc

- `Rc<T>`: single-threaded, no atomic ops, zero synchronization overhead. Always prefer over `Arc` for types that never cross thread boundaries.
- `Arc<T>`: each `clone` and `drop` is an atomic `fetch_add`/`fetch_sub`. Under heavy multi-threaded access the refcount cache line bounces.

```rust
// Bad: N Arc::clone per loop — refcount cache line thrashes
fn worker(config: Arc<Config>, items: &[Item]) {
    for item in items { process(config.clone(), item); }
}

// Good: borrow for the loop, clone once
fn worker(config: Arc<Config>, items: &[Item]) {
    let cfg: &Config = &*config;
    for item in items { process(cfg, item); }
}
```

## triomphe::Arc — no weak count

```toml
triomphe = "0.1"
```

```rust
use triomphe::Arc;
// Drop-in for std::sync::Arc when Weak is never used
// Saves: 1 usize per allocation (the weak refcount field)
// Faster clone/drop: one fewer atomic op
// Use when: no Arc::downgrade() calls anywhere for this type
```

## arc-swap 1.7 — lock-free hot-swappable shared state

```toml
arc-swap = "1.7"
```

```rust
use arc_swap::ArcSwap;
use std::sync::OnceLock;

static CONFIG: OnceLock<ArcSwap<Config>> = OnceLock::new();

fn reload(new: Config) { CONFIG.get().unwrap().store(Arc::new(new)); }
fn read() -> arc_swap::Guard<Arc<Config>> { CONFIG.get().unwrap().load() }
// read() is lock-free via epoch-based reclamation
// Better read throughput than RwLock<Arc<Config>> under many concurrent readers
```

---

# Phase 7 — Bounded Telemetry Buffers

**#1 impact:** `ArrayQueue` — lock-free MPMC ring buffer, allocated once at startup.

## Sizing a telemetry ring buffer

```
Compact Span estimate (using SmolStr + CompactString):
  name:       SmolStr     (24B inline)
  trace_id:   [u8; 16]   (16B)
  timestamps: 2 × i64    (16B)
  status:     u8          (1B)
  4 attrs:    4 × (SmolStr + CompactString) ≈ 4 × 48B = 192B
  Total: ~249B → round to 256B

At 1024 capacity: 1024 × 256B = 256KB ring buffer
At 100 spans/min: covers 10+ minutes before overflow
```

## crossbeam ArrayQueue (lock-free MPMC)

```toml
crossbeam = "0.8"
```

```rust
use crossbeam::queue::ArrayQueue;
use std::sync::atomic::{AtomicU64, Ordering};

static DROPPED: AtomicU64 = AtomicU64::new(0);

// Allocated once at startup, never re-allocates
let ring: ArrayQueue<Span> = ArrayQueue::new(1024);

// Producer — drop-newest on overflow (telemetry default):
fn emit(span: Span) {
    if ring.push(span).is_err() {
        DROPPED.fetch_add(1, Ordering::Relaxed);
    }
}

// Include in export report so overflow is visible:
report.dropped_spans = DROPPED.load(Ordering::Relaxed);

// Drain loop:
while let Some(span) = ring.pop() { batch.push(span); }
```

## ringbuf 0.4 (SPSC, zero-overhead)

```toml
ringbuf = "0.4"
```

```rust
use ringbuf::{HeapRb, traits::*};

// Single-producer, single-consumer — faster than ArrayQueue when P and C are separate threads
let rb = HeapRb::<Span>::new(1024);
let (mut prod, mut cons) = rb.split();

// Fully static (no heap at all — only feasible with const capacity):
use ringbuf::StaticRb;
static RB: StaticRb<u32, 256> = StaticRb::new();
```

## Backpressure strategy table

| Strategy | Code | Use case |
|---|---|---|
| Drop newest (push fails) | `ring.push(s).ok()` | Always-on low-priority telemetry |
| Drop oldest | `ring.force_push(s)` (ringbuf) | Event ordering matters more than recency |
| Block sender | `channel::bounded(N)` + `send().await` | Critical traces — latency acceptable |
| Count drops | `DROPPED.fetch_add(1, Relaxed)` | Always add alongside any drop strategy |

---

# Phase 8 — Leak Detection

**#1 impact:** `dhat` CI assertions — catch leaks at PR time, not in production.

## dhat in-process assertions (stable Rust, CI-friendly)

```rust
#[test]
#[cfg(feature = "dhat-heap")]
fn telemetry_writer_does_not_leak() {
    let _p = dhat::Profiler::builder().testing().build();
    {
        let writer = HistogramWriter::new_for_test();
        writer.record("op", 50);
        writer.flush_sync();
    }  // all objects dropped
    let stats = dhat::HeapStats::get();
    assert_eq!(stats.curr_bytes, 0, "leaked {} bytes after drop", stats.curr_bytes);
}
```

## LeakSanitizer (nightly, fast)

```bash
RUSTFLAGS="-Z sanitizer=leak" \
  cargo +nightly test --target x86_64-unknown-linux-gnu 2>&1 | grep "SUMMARY\|leaked"
```

## AddressSanitizer (nightly, catches use-after-free too)

```bash
RUSTFLAGS="-Z sanitizer=address" \
  cargo +nightly test --target x86_64-unknown-linux-gnu
```

## cargo-valgrind (stable, slowest)

```bash
cargo install cargo-valgrind
cargo valgrind test
```

## Arc cycle detection

No automatic tool exists. Prevention patterns:

```rust
// Pattern 1: use arena indices instead of Arc back-references
struct Graph { nodes: SlotMap<NodeKey, Node> }
struct Node { children: Vec<NodeKey> }  // indices, no reference cycles possible

// Pattern 2: Weak for genuine back-references
struct Parent { children: Vec<Arc<Child>> }
struct Child { parent: std::sync::Weak<Parent> }  // Weak breaks the cycle

// Pattern 3: CI audit — if no Weak is used, cycles are impossible
// grep -rn "Arc::new" src/ | grep -v "Weak" — flag for manual review
```

## Static vs true leaks

```rust
// Intentional static: document with a comment
static DB: OnceLock<Database> = OnceLock::new();  // freed at process exit — not a leak

// Box::leak: intentional infinite lifetime — add to CI grep
let config: &'static Config = Box::leak(Box::new(load_config()));
// CI: grep -rn "Box::leak" src/ — should be zero or justified

// True leaks: Arc cycles, append-only caches without eviction, sender dropped but receiver running
```
