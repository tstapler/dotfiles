# Phase 5 — Fix: Data Layout (SoA over AoS)

**Symptom:** IPC < 1.0 in `perf stat`; `memcpy`/cache-miss dominated flamegraph; loop processes only a few fields of a large struct.

```rust
// Before: Array of Structs — each iteration loads the full struct into cache
struct Particle { x: f32, y: f32, z: f32, mass: f32, charge: f32, flags: u32 }
let particles: Vec<Particle> = ...;

// Hot loop touches only x, y, z → loads 24 bytes, uses 12, wastes 12
for p in &particles { p.x += dt * p.vx; }

// After: Struct of Arrays — x, y, z are contiguous → full cache lines used, auto-vectorizes
struct Particles { x: Vec<f32>, y: Vec<f32>, z: Vec<f32>, mass: Vec<f32>, charge: Vec<f32>, flags: Vec<u32> }

// Or use the soa-rs crate for auto-generated SoA:
// #[derive(soa_rs::Soa)] struct Particle { x: f32, y: f32, z: f32 }
// let particles = Particles::new();
```

Expected speedup: **2–4×** on vectorizable loops. The compiler auto-vectorizes SoA without any `unsafe` or SIMD intrinsics.

## False sharing fix (parallel code)

```rust
// Before: threads write adjacent fields → cache-line ping-pong
struct Counter { value: u64 }
let counters: Vec<Counter> = (0..n_threads).map(|_| Counter { value: 0 }).collect();

// After: pad each counter to its own cache line
use crossbeam::utils::CachePadded;
let counters: Vec<CachePadded<Counter>> = ...;
```

---

# Phase 6 — Fix: Rayon Parallelism

**Symptom:** Rayon overhead visible in flamegraph; `work_stealing` / `join` calls dominate; or parallelism isn't helping.

## When NOT to use rayon

```rust
// Rayon has ~2µs spawn overhead per unit of work.
// Use parallel only when: work_per_item > ~10µs OR n_items > ~10_000

// Before: parallel on tiny work
small_vec.par_iter().for_each(|x| cheap_op(x));  // slower than serial for small n

// After: serial threshold
if small_vec.len() > 10_000 {
    small_vec.par_iter().for_each(|x| expensive_op(x));
} else {
    small_vec.iter().for_each(|x| expensive_op(x));
}
```

## Reducing allocation inside par_iter

```rust
// Before: allocates a Vec per rayon thread
let results: Vec<Vec<u32>> = data.par_iter().map(|x| compute(x)).collect();
// Then flatten — double allocation

// After: rayon flat_map_iter + collect into single Vec
let results: Vec<u32> = data.par_iter()
    .flat_map_iter(|x| compute_iter(x))
    .collect();
```

## Thread-local buffers for per-iteration temporary data

```rust
use std::cell::RefCell;
thread_local! {
    static BUF: RefCell<Vec<u32>> = RefCell::new(Vec::with_capacity(1024));
}

data.par_iter().for_each(|x| {
    BUF.with(|buf| {
        let mut buf = buf.borrow_mut();
        buf.clear();
        compute_into(x, &mut buf);
        // buf reused across calls on same thread — zero alloc per iteration
    });
});
```

## Rayon pool sizing

```rust
// Default: uses all logical CPUs — may be wrong for I/O-heavy or NUMA workloads
rayon::ThreadPoolBuilder::new()
    .num_threads(num_cpus::get_physical())  // physical only, avoid HT overhead
    .build_global()
    .unwrap();
```

---

# Phase 7 — Fix: SIMD and Math

**Symptom:** `f32::sqrt`, trig, or nalgebra dynamic-matrix functions in hot path.

## Enable auto-vectorization first

Before writing SIMD, check if the compiler already vectorizes with `RUSTFLAGS="-C target-cpu=native"`. Inspect assembly:

```bash
cargo rustc --release -- --emit asm
grep -A 20 "my_function:" target/release/deps/*.s | grep -i "ymm\|zmm\|xmm"
# ymm = AVX (256-bit), zmm = AVX-512 (512-bit), xmm = SSE (128-bit)
```

## `wide` crate for portable SIMD (stable Rust)

```rust
use wide::f32x8;

// Before: scalar
let result: Vec<f32> = a.iter().zip(b.iter()).map(|(&x, &y)| x * y + c).collect();

// After: 8-wide SIMD — same semantics, ~8× throughput on AVX2
let result: Vec<f32> = a.chunks_exact(8).zip(b.chunks_exact(8))
    .flat_map(|(ax, bx)| {
        let va = f32x8::from(ax.try_into().unwrap());
        let vb = f32x8::from(bx.try_into().unwrap());
        (va * vb + f32x8::splat(c)).to_array()
    })
    .collect();
```

## nalgebra: prefer fixed-size over dynamic matrices

```rust
// Before: DMatrix allocates on heap
let m: nalgebra::DMatrix<f64> = DMatrix::zeros(3, 3);

// After: SMatrix is stack-allocated, no alloc, fully inlined
let m: nalgebra::SMatrix<f64, 3, 3> = SMatrix::zeros();
```

---

# Phase 8 — Fix: Bounds Check Elision

**Symptom:** `core::panicking::panic_bounds_check` or `slice::index` visible in flamegraph.

```rust
// Prefer iterators — compiler proves bounds automatically, no checks emitted
for (x, y) in a.iter().zip(b.iter()) { *x += *y; }

// split_at for validated index access
let (left, right) = slice.split_at(mid);  // single bounds check, then unchecked

// get_unchecked when you have proven the index is valid
// SAFETY: i < slice.len() ensured by the loop invariant above
let val = unsafe { *slice.get_unchecked(i) };
```

Note: `get_unchecked` is `unsafe`. Only use after proving the index is valid. Incorrect use causes UB.

---

# Phase 9 — Fix: Dispatch Overhead

**Symptom:** `dyn Trait` vtable calls spread across flamegraph; many call sites for the same trait method.

```rust
// Before: dyn dispatch — pointer chase + indirect call each iteration
fn process(items: &[Box<dyn Processor>]) {
    for item in items { item.process(); }  // vtable call per item
}

// After option A: enum dispatch — zero overhead, monomorphized
enum ProcessorKind { A(ProcessorA), B(ProcessorB) }
impl ProcessorKind {
    fn process(&self) { match self { Self::A(p) => p.process(), Self::B(p) => p.process() } }
}

// After option B: enum_dispatch crate (macro-generated enum from trait)
// #[enum_dispatch(Processor)] enum ProcessorKind { ProcessorA, ProcessorB }
```

Expected speedup: **2–10×** when the hot path is a tight loop over heterogeneous trait objects.
