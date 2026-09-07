# Phase 1 — Type Size Optimization

**#1 impact:** `NonZero*` niche — `Option<NonZeroU32>` = 4 bytes, not 8.

## Audit type sizes in CI

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

## NonZero niche optimization

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

## Enum variant size disparity — box the large variant

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

## Bitfield packing (flags)

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

## Struct field ordering for `#[repr(C)]`

For `#[repr(Rust)]` (the default) the compiler already minimizes padding — verify with `size_of!`. Only applies to `#[repr(C)]`:

```rust
// Bad #[repr(C)]: bool(1) + 7pad + u64(8) + bool(1) + 7pad = 24 bytes
#[repr(C)] struct Bad { a: bool, b: u64, c: bool }

// Good #[repr(C)]: u64(8) + bool(1) + bool(1) + 6pad = 16 bytes
#[repr(C)] struct Good { b: u64, a: bool, c: bool }
// Rule: largest alignment first (u64, u32, u16, u8/bool)
```

## Small integer types for bounded counts

```rust
// Before: Vec<usize> — 8 bytes per index
struct Node { children: Vec<usize> }

// After (bounded ≤ 65535): 4 bytes per index
struct Node { children: Vec<u32> }

// Or (bounded ≤ 255): 1 byte per index — 8× smaller
struct Node { children: Vec<u8> }
```

---

# Phase 2 — Compact String and Collection Types

**#1 impact:** `CompactString` — strings ≤ 24 bytes stored inline, zero heap allocation.

## compact_str 0.8 — drop-in String replacement

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

## smol_str 0.3 — immutable, O(1) clone

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

## arrayvec 0.7 — fixed-capacity stack arrays

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

## tinyvec 1.8 — safe SmallVec

```toml
tinyvec = { version = "1.8", features = ["alloc"] }
```

```rust
use tinyvec::TinyVec;
let mut v: TinyVec<[u32; 4]> = TinyVec::new();
for i in 0..8 { v.push(i); }  // spills to heap at 5th push, keeps working
// 100% safe Rust — no unsafe internals (unlike SmallVec)
```

## String pool — N strings, 1 allocation

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
