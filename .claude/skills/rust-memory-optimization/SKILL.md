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

### heaptrack (best overall)

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

### dhat crate — in-process CI assertions

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

### /proc RSS (zero-overhead coarse check)

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

### Valgrind DHAT (external, detailed)

```bash
valgrind --tool=dhat ./target/release/mybinary args
# Upload dhat.out.PID → https://nnethercote.github.io/dh_view/dh_view.html
# Key insight: "Total bytes" >> "Max bytes live" = churn problem, not footprint problem
```

---

## Phase 1 — Type Size Optimization

**#1 impact:** `NonZero*` niche — `Option<NonZeroU32>` = 4 bytes, not 8.

### Audit type sizes in CI

```rust
// Add to lib.rs or a test — breaks build on accidental struct bloat:
const _: () = assert!(
    std::mem::size_of::<Span>() <= 128,
    "Span exceeded 128B — new fields must be boxed or use compact types"
);

// Inspect at runtime:
dbg!(std::mem::size_of::<MyEnum>());
dbg!(std::mem::size_of::<Option<MyStruct>>());
```

```bash
cargo install cargo-bloat
cargo bloat --release --crates       # per-crate binary contribution
cargo bloat --release -n 50          # top 50 functions by size
```

### NonZero niche optimization

```rust
use std::num::NonZeroU32;

// Before: 8 bytes — u32 (4B) + discriminant (4B)
enum Bad { None, Some(u32) }

// After: 4 bytes — zero is the None niche, no discriminant
type Good = Option<NonZeroU32>;

// Apply to IDs and handles that are never 0:
#[derive(Copy, Clone, PartialEq, Eq, Hash)]
struct NodeId(NonZeroU32);
// Option<NodeId> = 4 bytes. Box<T>, &T, Arc<T> already have a null niche.
```

### Enum variant size disparity — box the large variant

```rust
// Bad: ALL variants padded to the largest — wastes memory for Tiny variants
enum Event {
    Tiny(u8),                // wants 1 byte
    Huge([u8; 4096]),        // ALL variants become 4097 bytes
}

// Good: box the large variant — all variants = pointer size (8 bytes)
enum Event {
    Tiny(u8),
    Huge(Box<[u8; 4096]>),  // heap-allocated; enum is 16 bytes
}
```

### Bitfield packing (flags)

```toml
bitflags = "2.6"
```

```rust
use bitflags::bitflags;
bitflags! {
    #[derive(Clone, Copy)]
    struct SpanFlags: u8 {   // 1 byte for 8 flags vs 8 × bool = 8 bytes
        const IS_ERROR   = 0b00000001;
        const IS_SAMPLED = 0b00000010;
        const HAS_PARENT = 0b00000100;
    }
}
```

### Struct field ordering for `#[repr(C)]`

For `#[repr(Rust)]` (the default) the compiler already minimizes padding — verify with `size_of!`. Only applies to `#[repr(C)]`:

```rust
// Bad #[repr(C)]: bool(1) + 7pad + u64(8) + bool(1) + 7pad = 24 bytes
#[repr(C)] struct Bad { a: bool, b: u64, c: bool }

// Good #[repr(C)]: u64(8) + bool(1) + bool(1) + 6pad = 16 bytes
#[repr(C)] struct Good { b: u64, a: bool, c: bool }
// Rule: largest alignment first (u64, u32, u16, u8/bool)
```

### Small integer types for bounded counts

```rust
// Before: Vec<usize> — 8 bytes per index
struct Node { children: Vec<usize> }

// After (bounded ≤ 65535): 4 bytes per index
struct Node { children: Vec<u32> }

// Or (bounded ≤ 255): 1 byte per index — 8× smaller
struct Node { children: Vec<u8> }
```

---

## Phase 2 — Compact String and Collection Types

**#1 impact:** `CompactString` — strings ≤ 24 bytes stored inline, zero heap allocation.

### compact_str 0.8 — drop-in String replacement

```toml
compact_str = "0.8"
```

```rust
use compact_str::CompactString;
// Strings ≤ 24 bytes: inline, zero heap. Longer: heap-backed.
let op: CompactString = "db.saveBlocks".into();   // inline, 0 alloc (13 bytes)
let long: CompactString = very_long_string.into(); // heap if > 24 bytes

// Most span names, SQL table names, operation keys ≤ 24 bytes → zero allocation
```

### smol_str 0.3 — immutable, O(1) clone

```toml
smol_str = "0.3"
```

```rust
use smol_str::SmolStr;
// Inline ≤ 22 bytes; Arc-backed for longer (clone = O(1) refcount bump, no memcpy)
// Immutable — no push_str. Best for: span names cloned across many consumers.
let op: SmolStr = "parseAndSavePage".into();
let op2 = op.clone();  // O(1) — no memcpy for strings of any length
```

### arrayvec 0.7 — fixed-capacity stack arrays

```toml
arrayvec = "0.7"
```

```rust
use arrayvec::{ArrayVec, ArrayString};
use std::fmt::Write;

// Never heap-allocates. Panics on push past capacity.
let mut attrs: ArrayVec<(&str, &str), 8> = ArrayVec::new();
attrs.push(("db.table", "pages"));   // stack-only
attrs.push(("span.id", "abc123"));

// Stack-allocated string:
let mut buf: ArrayString<64> = ArrayString::new();
write!(buf, "span_{}", id).unwrap();  // no heap
```

When NOT to use: max capacity is unknown or variable — use `SmallVec` or `Vec`.

### tinyvec 1.8 — safe SmallVec

```toml
tinyvec = { version = "1.8", features = ["alloc"] }
```

```rust
use tinyvec::TinyVec;
let mut v: TinyVec<[u32; 4]> = TinyVec::new();
for i in 0..8 { v.push(i); }  // spills to heap at 5th push, keeps working
// 100% safe Rust — no unsafe internals (unlike SmallVec)
```

### String pool — N strings, 1 allocation

```rust
// Instead of Vec<String> — N separate heap allocations:
struct StringPool { data: String, spans: Vec<std::ops::Range<usize>> }

impl StringPool {
    fn intern(&mut self, s: &str) -> usize {
        let start = self.data.len();
        self.data.push_str(s);
        self.spans.push(start..self.data.len());
        self.spans.len() - 1
    }
    fn get(&self, idx: usize) -> &str { &self.data[self.spans[idx].clone()] }
}
// N spans' attribute values → 1 amortized allocation
```

---

## Phase 3 — Allocator Swap

**#1 impact:** `mimalloc` — 5–30% allocation throughput improvement, 5 lines of code.

### mimalloc (fastest general-purpose)

```toml
mimalloc = { version = "0.1", default-features = false }
```

```rust
#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;
```

Expected: 5–30% allocation throughput improvement (benchmarks vary by workload). Thread-local caches reduce contention. Works on all platforms.

### tikv-jemallocator (long-running servers, profiling support)

```toml
tikv-jemallocator = "0.6"
```

```rust
#[global_allocator]
static ALLOC: tikv_jemallocator::Jemalloc = tikv_jemallocator::Jemalloc;
```

Better than mimalloc for: long-running servers, high thread count, fragmentation-sensitive workloads. Supports heap profiling (see Phase 0). When NOT to switch: single-threaded, WASM, embedded targets.

**Always benchmark before shipping.** Switching allocators is global and the wrong choice for a given workload can regress performance.

---

## Phase 4 — Arenas, Pools, and Scoped Allocation

**When pools beat malloc:** allocation rate > ~10,000/s for same-sized objects. Check heaptrack "temporary allocations" — high count = pool candidate.

### bumpalo 3.x — per-scope arena (fastest allocator pattern)

```toml
bumpalo = "3.16"
```

```rust
use bumpalo::Bump;

// All intermediate allocations from one arena; freed in O(1) when bump drops
fn process_export() -> Vec<u8> {
    let bump = Bump::new();
    let spans: &[Span] = bump.alloc_slice_copy(&raw_spans);
    let json: &str = bump.alloc_str(&serialized);
    // JSON bytes copied out before bump drops
    json.as_bytes().to_vec()
}  // ← O(1) cleanup of ALL intermediates

// For types with Drop: use bumpalo's Box
let node: bumpalo::boxed::Box<'_, MyDrop> = bumpalo::boxed::Box::new_in(MyDrop, &bump);
```

When NOT to use: items need individual freeing; lifetimes differ across bump items.

### typed_arena 2.0 — homogeneous, supports Drop

```toml
typed_arena = "2.0"
```

```rust
use typed_arena::Arena;

let arena: Arena<AstNode> = Arena::new();
let node: &mut AstNode = arena.alloc(AstNode::new());
// arena calls Drop on items in insertion order when it drops
// Cannot free individual items
```

### slotmap 1.0 — pool-like O(1) insert/remove

```toml
slotmap = "1.0"
```

```rust
use slotmap::{SlotMap, DefaultKey};

let mut pool: SlotMap<DefaultKey, Span> = SlotMap::new();
let k = pool.insert(span);          // O(1), generational key
pool.remove(k);                     // slot recycled
let bad = pool[k];                  // panics: generation mismatch (use-after-free protection)
// Contiguous Vec-like storage → cache-friendly iteration
```

### Thread-local pool (zero-overhead, no crate)

```rust
use std::cell::RefCell;

thread_local! {
    static BUF_POOL: RefCell<Vec<Vec<u8>>> = RefCell::new(Vec::new());
}

fn acquire_buf() -> Vec<u8> {
    BUF_POOL.with(|p| p.borrow_mut().pop().unwrap_or_else(|| Vec::with_capacity(4096)))
}

fn release_buf(mut v: Vec<u8>) {
    v.clear();  // keep capacity for reuse
    BUF_POOL.with(|p| {
        if p.borrow().len() < 16 { p.borrow_mut().push(v); }  // cap pool size
    });
}

// Usage pattern:
let buf = acquire_buf();
fill(&mut buf, data);
process(&buf);
release_buf(buf);
```

When NOT to use: varying-size buffers (capacity mismatch forces re-allocation anyway).

---

## Phase 5 — Zero-Copy Patterns

**#1 impact:** `bytes::Bytes` — share a gzip output buffer across tasks without copying.

### bytes 1.x — shared immutable buffer slices

```toml
bytes = "1.9"
```

```rust
use bytes::{Bytes, BytesMut};

// Write once, read many — zero-copy slicing:
let body = Bytes::from(compressed_report);  // one allocation
let header = body.slice(0..32);            // O(1), ref-count bump, no memcpy
let payload = body.slice(32..);           // O(1), ref-count bump, no memcpy

// Staging buffer → shared immutable:
let mut buf = BytesMut::with_capacity(4096);
buf.extend_from_slice(b"json content");
let frozen: Bytes = buf.freeze();  // O(1), now shareable across threads
```

Wrong for: payloads < 64 bytes (Arc overhead dominates cost). Best for: gzip output, network buffers, file content read once and shared across tasks.

### memmap2 0.9 — memory-mapped files

```toml
memmap2 = "0.9"
```

```rust
use memmap2::Mmap;
let file = std::fs::File::open("large_export.json.gz")?;
let mmap = unsafe { Mmap::map(&file)? };
// OS reads pages on demand — no upfront heap allocation
let reader = flate2::read::GzDecoder::new(&mmap[..]);
```

When to use: files > 64MB, partial reads. Wrong for: files < 1MB (mmap setup overhead > memcpy), network filesystems.

### zerocopy 0.8 — transmute byte slices to typed structs

```toml
zerocopy = { version = "0.8", features = ["derive"] }
```

```rust
use zerocopy::{FromBytes, IntoBytes, Immutable};

#[derive(FromBytes, IntoBytes, Immutable)]
#[repr(C)]
struct PerfHeader { magic: [u8; 4], version: u32, span_count: u32 }

// Zero-copy parse — no allocation, no memcpy:
let header: &PerfHeader = PerfHeader::ref_from_bytes(&mmap[0..12]).unwrap();
```

Requires `#[repr(C)]`. Use `zerocopy::U32<LittleEndian>` for cross-platform endianness.

---

## Phase 6 — Reference Counting Optimization

**#1 impact:** Borrow instead of `Arc::clone` inside loops — one clone, not N.

### Arc vs Rc

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

### triomphe::Arc — no weak count

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

### arc-swap 1.7 — lock-free hot-swappable shared state

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

## Phase 7 — Bounded Telemetry Buffers

**#1 impact:** `ArrayQueue` — lock-free MPMC ring buffer, allocated once at startup.

### Sizing a telemetry ring buffer

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

### crossbeam ArrayQueue (lock-free MPMC)

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

### ringbuf 0.4 (SPSC, zero-overhead)

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

### Backpressure strategy table

| Strategy | Code | Use case |
|---|---|---|
| Drop newest (push fails) | `ring.push(s).ok()` | Always-on low-priority telemetry |
| Drop oldest | `ring.force_push(s)` (ringbuf) | Event ordering matters more than recency |
| Block sender | `channel::bounded(N)` + `send().await` | Critical traces — latency acceptable |
| Count drops | `DROPPED.fetch_add(1, Relaxed)` | Always add alongside any drop strategy |

---

## Phase 8 — Leak Detection

**#1 impact:** `dhat` CI assertions — catch leaks at PR time, not in production.

### dhat in-process assertions (stable Rust, CI-friendly)

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

### LeakSanitizer (nightly, fast)

```bash
RUSTFLAGS="-Z sanitizer=leak" \
  cargo +nightly test --target x86_64-unknown-linux-gnu 2>&1 | grep "SUMMARY\|leaked"
```

### AddressSanitizer (nightly, catches use-after-free too)

```bash
RUSTFLAGS="-Z sanitizer=address" \
  cargo +nightly test --target x86_64-unknown-linux-gnu
```

### cargo-valgrind (stable, slowest)

```bash
cargo install cargo-valgrind
cargo valgrind test
```

### Arc cycle detection

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

### Static vs true leaks

```rust
// Intentional static: document with a comment
static DB: OnceLock<Database> = OnceLock::new();  // freed at process exit — not a leak

// Box::leak: intentional infinite lifetime — add to CI grep
let config: &'static Config = Box::leak(Box::new(load_config()));
// CI: grep -rn "Box::leak" src/ — should be zero or justified

// True leaks: Arc cycles, append-only caches without eviction, sender dropped but receiver running
```

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
