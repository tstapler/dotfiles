# Phase 3 — Allocator Swap

**#1 impact:** `mimalloc` — 5–30% allocation throughput improvement, 5 lines of code.

## mimalloc (fastest general-purpose)

```toml
mimalloc = { version = "0.1", default-features = false }
```

```rust
#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;
```

Expected: 5–30% allocation throughput improvement (benchmarks vary by workload). Thread-local caches reduce contention. Works on all platforms.

## tikv-jemallocator (long-running servers, profiling support)

```toml
tikv-jemallocator = "0.6"
```

```rust
#[global_allocator]
static ALLOC: tikv_jemallocator::Jemalloc = tikv_jemallocator::Jemalloc;
```

Better than mimalloc for: long-running servers, high thread count, fragmentation-sensitive workloads. Supports heap profiling (see `measurement-tooling.md`). When NOT to switch: single-threaded, WASM, embedded targets.

**Always benchmark before shipping.** Switching allocators is global and the wrong choice for a given workload can regress performance.

---

# Phase 4 — Arenas, Pools, and Scoped Allocation

**When pools beat malloc:** allocation rate > ~10,000/s for same-sized objects. Check heaptrack "temporary allocations" — high count = pool candidate.

## bumpalo 3.x — per-scope arena (fastest allocator pattern)

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

## typed_arena 2.0 — homogeneous, supports Drop

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

## slotmap 1.0 — pool-like O(1) insert/remove

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

## Thread-local pool (zero-overhead, no crate)

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

# Phase 5 — Zero-Copy Patterns

**#1 impact:** `bytes::Bytes` — share a gzip output buffer across tasks without copying.

## bytes 1.x — shared immutable buffer slices

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

## memmap2 0.9 — memory-mapped files

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

## zerocopy 0.8 — transmute byte slices to typed structs

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
