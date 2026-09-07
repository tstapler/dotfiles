# Phase 3 — Fix: Eliminating Allocations

**Symptom:** `alloc`, `clone`, `format!`, `collect` in flamegraph hot path.

## Buffer reuse (most common fix)

```rust
// Before: allocates per iteration
for line in lines {
    let s = format!("prefix_{}", line);   // heap alloc every iter
    process(&s);
}

// After: reuse buffer
let mut buf = String::with_capacity(64);
for line in lines {
    buf.clear();
    write!(&mut buf, "prefix_{}", line).unwrap();  // zero alloc
    process(&buf);
}
```

## SmallVec for short-lived collections

```rust
// Before: Vec<_> always heap-allocates
let mut neighbors: Vec<u32> = Vec::new();

// After: inline storage for N ≤ 8, spills to heap only beyond
use smallvec::SmallVec;
let mut neighbors: SmallVec<[u32; 8]> = SmallVec::new();
```

## Vec::with_capacity to prevent reallocation

```rust
// Before: O(log n) reallocations
let mut v: Vec<_> = Vec::new();
for x in iter { v.push(x); }

// After: single allocation
let mut v = Vec::with_capacity(iter.size_hint().0);
for x in iter { v.push(x); }
// Or: iter.collect::<Vec<_>>() already calls size_hint — prefer collect when possible
```

## Avoid clone by restructuring ownership

```rust
// Before: clones the entire cloud to pass to two functions
fn process(cloud: PointCloud) {
    let filtered = filter(cloud.clone());
    let normals  = estimate(cloud.clone());
}

// After: take references
fn process(cloud: &PointCloud) {
    let filtered = filter(cloud);
    let normals  = estimate(cloud);
}
```

## Cow<'_, str> for conditionally-owned strings

```rust
// Before: always allocates
fn normalize(s: &str) -> String {
    if s.contains(' ') { s.replace(' ', "_") } else { s.to_owned() }
}

// After: borrows when no transformation needed
fn normalize(s: &str) -> Cow<'_, str> {
    if s.contains(' ') { Cow::Owned(s.replace(' ', "_")) } else { Cow::Borrowed(s) }
}
```

---

# Phase 4 — Fix: HashMap Replacement

**Symptom:** `std::collections::hash_map::HashMap` near top of flamegraph.

```rust
// Before: SipHash (DoS-resistant, ~3× slower for integer keys)
use std::collections::HashMap;
let mut map: HashMap<u32, u32> = HashMap::new();

// After option A: FxHashMap (rustc-hash) — fastest for integer/pointer keys
use rustc_hash::FxHashMap;
let mut map: FxHashMap<u32, u32> = FxHashMap::default();

// After option B: AHashMap — fastest for string keys (uses AES intrinsics)
use ahash::AHashMap;
let mut map: AHashMap<String, u32> = AHashMap::new();

// Type alias to make switching easy
type FastMap<K, V> = rustc_hash::FxHashMap<K, V>;
```

Expected speedup: **4–84%** over std HashMap (rustc's own benchmarks). Use std HashMap only when keys are user-controlled (HashDoS resistance required).

Pre-size to avoid rehashing:
```rust
let mut map = FxHashMap::with_capacity_and_hasher(expected_n, Default::default());
```
