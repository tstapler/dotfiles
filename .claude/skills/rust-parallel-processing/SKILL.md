---
name: rust-parallel-processing
description: Exploit CPU, GPU, and multi-machine parallelism in Rust. Covers rayon (data parallelism), tokio (task/async parallelism), SIMD (auto-vectorization + wide crate), wgpu/cudarc/candle (GPU compute and ML), tonic/tarpc/quinn (multi-machine RPC), MPI/ractor/DataFusion (HPC and distributed), algorithm patterns (map-reduce, pipeline, work-stealing, SPMD), profiling parallel programs, and common anti-patterns. Companion to rust-profiling (collect data first) and rust-perf-tuning (single-core fixes).
paths: "**/*.rs"
metadata:
  type: feedback
---

# Rust Parallel Processing

End-to-end workflow: identify bottleneck → choose the right layer → implement → verify scaling.

**Companion skills:** [[rust-profiling]] to measure serial fraction and hotspots first. [[rust-perf-tuning]] for single-core CPU optimizations (caches, allocations, SIMD) that multiply with parallelism. [[rust-memory-optimization]] when parallel work amplifies allocation pressure. [[rust-development]] for the full Rust development workflow.

---

## Phase 0 — Decision Tree: Which Layer Do You Need?

Before writing code, identify your bottleneck:

```
Is the work CPU-bound or I/O-bound?
├── I/O-bound → tokio async tasks (§2). Parallelism won't help.
└── CPU-bound
    ├── Data fits in one machine?
    │   ├── Data is numeric/homogeneous arrays? → SIMD first (§3), then rayon (§1)
    │   ├── Independent tasks (embarrassingly parallel)? → rayon par_iter (§1)
    │   ├── Tasks have async dependencies? → tokio JoinSet + spawn_blocking (§2)
    │   └── N > ~1M ops AND arithmetic intensity > 10 ops/byte? → GPU (§4)
    └── Data doesn't fit one machine or latency budget requires fan-out?
        ├── Tightly coupled, numerical, HPC cluster? → MPI (§7)
        ├── Stateful event-driven services? → actors via ractor (§7)
        └── Data pipeline / SQL-style? → DataFusion + Ballista (§7)
```

**Amdahl's Law sanity check before starting:**
```
Max speedup = 1 / (serial_fraction + parallel_fraction / N_cores)
10% serial code → max 10× speedup on infinite cores
5% serial code → max 20× speedup
```
Profile serial fraction first with [[rust-profiling]]. If it's > 20%, fix that before adding parallelism.

---

## Phase 1 — CPU Data Parallelism: Rayon

**#1 impact:** `par_iter()` on an existing `Vec` — near-zero code change, near-linear speedup for CPU-bound work with items > ~10µs each.

```toml
rayon = "1.10"
```

### Core API

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

### Thread pool sizing

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

### Work-stealing internals (why it matters)

Rayon uses a Chase-Lev double-ended work-stealing deque per thread. Each thread pushes to its own deque's back; idle threads steal from the fronts of others. Result: automatic load balancing even when items have variable cost — no manual chunking needed. This is why rayon outperforms hand-rolled thread pools for irregular workloads.

### Divide and conquer with `rayon::join`

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

### Per-thread temporary state without allocation

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

### Structured parallelism with `scope`

```rust
rayon::scope(|s| {
    s.spawn(|_| task_a());  // runs in parallel
    s.spawn(|_| task_b());  // runs in parallel
    task_c();               // runs while a and b run
});
// All tasks done here — implicit barrier
```

### `IndexedParallelIterator` vs `ParallelIterator`

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

### When NOT to use rayon

| Situation | Why rayon hurts | Fix |
|---|---|---|
| I/O-bound work | Threads block, executor starves | tokio async |
| Items < ~10µs of work | Spawn overhead (2µs) > gain | Serial iterator |
| < ~10k items total | Parallel overhead > serial | `if n > 10_000 { par } else { serial }` |
| Inside async executor | Blocks async worker thread | `spawn_blocking(|| rayon_work())` |
| Shared `Mutex<Vec<T>>` per item | Lock contention serializes everything | `fold` into thread-local then merge |

---

## Phase 2 — CPU Task Parallelism: Tokio Async

**#1 impact:** `JoinSet` for bounded fan-out of independent async tasks.

```toml
tokio = { version = "1", features = ["full"] }
```

### spawn variants — when to use each

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

### JoinSet — bounded concurrent task fan-out

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

### FuturesUnordered vs JoinSet

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

### Semaphore for bounding concurrency

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

### Rayon from Tokio — bridging sync and async

```rust
// Offload rayon work to blocking thread pool, get result back in async
async fn parallel_process(data: Vec<Input>) -> Vec<Output> {
    tokio::task::spawn_blocking(move || {
        data.par_iter().map(|x| cpu_heavy(x)).collect()
    }).await.expect("rayon task panicked")
}
```

### Producer-consumer pipeline

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

---

## Phase 3 — CPU SIMD

**#1 impact:** Enable `target-cpu=native` first — the compiler auto-vectorizes more than most people expect.

### Step 1: Check auto-vectorization

```bash
RUSTFLAGS="-C target-cpu=native" cargo rustc --release -- --emit asm
grep -A 5 "my_hot_loop:" target/release/deps/*.s | grep -i "ymm\|zmm\|xmm"
# ymm = AVX2 (256-bit, 8× f32), zmm = AVX-512 (512-bit, 16× f32)
# If you see these: the compiler already vectorized — don't add manual SIMD
```

Add permanently to `.cargo/config.toml`:
```toml
[build]
rustflags = ["-C", "target-cpu=native"]
```

### Step 2: Manual SIMD with `wide` (stable, AVX2)

```toml
wide = "0.7"
```

```rust
use wide::f32x8;

// 8-wide SIMD dot product — ~8× throughput on AVX2
fn dot_product_simd(a: &[f32], b: &[f32]) -> f32 {
    let mut acc = f32x8::ZERO;
    let chunks = a.len() / 8;
    for i in 0..chunks {
        let va = f32x8::from(&a[i*8..(i+1)*8]);
        let vb = f32x8::from(&b[i*8..(i+1)*8]);
        acc += va * vb;
    }
    let mut sum: f32 = acc.reduce_add();
    for i in (chunks * 8)..a.len() { sum += a[i] * b[i]; }
    sum
}

// u8x32 for byte scanning (e.g., find newlines in bulk)
use wide::u8x32;
fn count_newlines(data: &[u8]) -> usize {
    let nl = u8x32::splat(b'\n');
    let mut count = 0usize;
    let chunks = data.len() / 32;
    for i in 0..chunks {
        let v = u8x32::from(&data[i*32..(i+1)*32]);
        count += (v.cmp_eq(nl).move_mask().count_ones()) as usize;
    }
    for &b in &data[chunks*32..] { if b == b'\n' { count += 1; } }
    count
}
```

### When NOT to use manual SIMD

| Situation | Why | Fix |
|---|---|---|
| Auto-vectorized already | Manual SIMD won't help | Verify with `--emit asm` first |
| Branch-heavy code | SIMD requires branch-free math | Restructure to branchless |
| Non-contiguous memory | Gather/scatter patterns are slow | Reorder data to SoA layout first |
| Shipping to diverse CPUs | AVX2 not on old hardware | Use `wide`'s safe abstractions or runtime detection |

---

## Phase 4 — GPU Compute

**Rule of thumb before using GPU:**
- > 1M arithmetic operations per kernel launch
- Data already on GPU or transfer amortized over many launches
- Arithmetic intensity > ~10 ops/byte (otherwise bandwidth-bound)
- Latency is NOT the primary constraint (GPU launch overhead: 5–50µs)

**PCIe 4.0 x16 budget:** ~32 GB/s bidirectional. For 1M f32 (4 MB): transfer ≈ 125µs. GPU wins only when `compute_time >> transfer_time`. For batches < 64KB: CPU is almost always faster.

### wgpu 0.20 — cross-platform compute (Vulkan/Metal/DX12/WebGPU)

Best for: cross-platform, desktop + web, general compute. No NVIDIA required.

```toml
wgpu = "0.20"
```

```wgsl
// WGSL compute shader (element-wise square)
@group(0) @binding(0) var<storage, read> input: array<f32>;
@group(0) @binding(1) var<storage, read_write> output: array<f32>;

@compute @workgroup_size(256)
fn main(@builtin(global_invocation_id) id: vec3<u32>) {
    let i = id.x;
    if i < arrayLength(&input) {
        output[i] = input[i] * input[i];
    }
}
```

```rust
async fn gpu_square(data: &[f32]) -> Vec<f32> {
    let instance = wgpu::Instance::default();
    let adapter = instance.request_adapter(&Default::default()).await.unwrap();
    let (device, queue) = adapter.request_device(&Default::default(), None).await.unwrap();

    let input_buf = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: None,
        contents: bytemuck::cast_slice(data),
        usage: wgpu::BufferUsages::STORAGE,
    });
    let output_buf = device.create_buffer(&wgpu::BufferDescriptor {
        label: None,
        size: (data.len() * 4) as u64,
        usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC,
        mapped_at_creation: false,
    });
    // dispatch_workgroups((data.len() + 255) / 256, 1, 1)
    // then readback via staging buffer
    todo!("see wgpu compute examples for full pipeline setup")
}
```

### cudarc 0.12 — NVIDIA CUDA (maximum performance)

Best for: NVIDIA-only deployments, ML kernels, existing CUDA ecosystem.

```toml
cudarc = { version = "0.12", features = ["cuda-12050"] }
```

```rust
use cudarc::driver::*;

fn cuda_square(data: &[f32]) -> Vec<f32> {
    let dev = CudaDevice::new(0).unwrap();
    let d_input: CudaSlice<f32> = dev.htod_copy(data.to_vec()).unwrap();
    let mut d_output: CudaSlice<f32> = unsafe { dev.alloc(data.len()).unwrap() };

    dev.load_ptx(Ptx::from_file("square.ptx"), "square", &["square_kernel"]).unwrap();
    let f = dev.get_func("square", "square_kernel").unwrap();

    let n = data.len();
    let cfg = LaunchConfig { grid_dim: ((n + 255) / 256) as u32, block_dim: 256, shared_mem_bytes: 0 };
    unsafe { f.launch(cfg, (&d_input, &mut d_output, n as u32)) }.unwrap();
    dev.dtoh_sync_copy(&d_output).unwrap()
}

// Async streams for overlapping compute + transfer
let stream = dev.fork_default_stream().unwrap();
dev.htod_copy_into(data, &mut d_input, &stream).unwrap();
unsafe { f.launch_on_stream(&stream, cfg, args) }.unwrap();
```

---

## Phase 5 — GPU ML/Tensor Acceleration

**Decision:** use Python subprocess unless you need Rust-native inference (latency, deployment constraints, or embedding into a Rust service).

### candle (HuggingFace) — pure-Rust inference

```toml
candle-core = { version = "0.7", features = ["cuda"] }
candle-nn = "0.7"
candle-transformers = "0.7"
```

```rust
use candle_core::{Device, Tensor};

let device = Device::new_cuda(0)?;  // or Device::Cpu
let a = Tensor::rand(0f32, 1f32, (1024, 1024), &device)?;
let b = Tensor::rand(0f32, 1f32, (1024, 1024), &device)?;
let c = a.matmul(&b)?;

// Load HuggingFace safetensors weights
use candle_core::safetensors::load;
let weights = load("model.safetensors", &device)?;
```

When to use: Rust-native inference, no Python dependency, WASM targets. When NOT: training (use PyTorch), prototyping (Python is faster to iterate).

### tch-rs — LibTorch bindings

```toml
tch = "0.17"  # requires LibTorch at LIBTORCH env var
```

```rust
use tch::{Tensor, Device, Kind};

let device = Device::Cuda(0);
let t = Tensor::randn(&[1024, 1024], (Kind::Float, device));
let result = t.matmul(&t.transpose(0, 1));

// Load a traced PyTorch model
let model = tch::CModule::load("model.pt")?;
let output = model.forward_ts(&[input])?;
```

### burn 0.14 — training + inference, multiple backends

```toml
burn = { version = "0.14", features = ["wgpu"] }  # or "cuda", "tch", "ndarray"
```

Backend is a compile-time type parameter — swap `Wgpu` for `Cuda` without code changes. Best for: new Rust ML projects, training on non-NVIDIA hardware via wgpu.

---

## Phase 6 — Multi-Machine: Message Passing

### tonic (gRPC) — cross-language, production-grade

Best for: heterogeneous services (Rust + Python + Go), schema-first API contracts, bidirectional streaming.

```toml
tonic = "0.12"
prost = "0.13"
tokio = { version = "1", features = ["full"] }
```

```protobuf
service ComputeService {
  rpc Process (ProcessRequest) returns (ProcessResponse);
  rpc StreamResults (ProcessRequest) returns (stream ProcessResponse);
}
```

```rust
// Server
#[tonic::async_trait]
impl ComputeService for MyService {
    async fn process(&self, req: Request<ProcessRequest>) -> Result<Response<ProcessResponse>, Status> {
        let result = rayon_compute(req.into_inner().data);
        Ok(Response::new(ProcessResponse { result }))
    }
}

// Client
let mut client = ComputeServiceClient::connect("http://worker:50051").await?;
let response = client.process(ProcessRequest { data: input }).await?;
```

### tarpc — Rust-native RPC (simpler, no protobuf)

```toml
tarpc = { version = "0.34", features = ["full"] }
```

```rust
#[tarpc::service]
trait WorldService {
    async fn hello(name: String) -> String;
}
// Implementation + server/client boilerplate is macro-generated
```

Use tarpc for Rust-only + simpler setup; tonic for cross-language or existing protobuf schemas.

### quinn (QUIC) — low-latency, multiplexed

```toml
quinn = "0.11"
```

QUIC advantages over TCP+gRPC: no head-of-line blocking across streams, 0-RTT reconnection, built-in TLS. Use when: many small parallel messages, latency-sensitive, mobile/unreliable networks.

### ZeroMQ patterns for HPC pipelines

```toml
zmq = "0.10"  # requires libzmq system package
```

```rust
// Push/pull scatter-gather across workers
let pusher = context.socket(zmq::PUSH)?;
pusher.bind("tcp://*:5555")?;
for item in work_items { pusher.send(&serialize(item), 0)?; }
```

---

## Phase 7 — Multi-Machine: Distributed Compute

### MPI — tightly coupled HPC

Best for: numerical simulation, linear algebra, collective ops (allreduce for gradient aggregation, scatter/gather for domain decomposition).

```toml
mpi = "0.8"  # requires OpenMPI or MPICH installed
```

```rust
use mpi::traits::*;

fn main() {
    let universe = mpi::initialize().unwrap();
    let world = universe.world();
    let rank = world.rank();
    let size = world.size();

    // Partition data across ranks
    let chunk_size = total_data.len() / size as usize;
    let local_data = &total_data[rank as usize * chunk_size..];

    let local_result: f64 = local_data.par_iter().map(compute).sum();

    let mut global_result = 0.0f64;
    world.process_at_rank(0).reduce_into_root(
        &local_result, &mut global_result, mpi::collective::SystemOperation::sum()
    );
}
```

**Hybrid MPI+Rayon** (standard for HPC clusters):
```
Launch: mpirun -np N_NODES --bind-to socket ./mybinary
Each rank: processes its data partition with rayon (N_CPU_CORES threads)
Result: N_NODES × N_CORES total parallelism
```

### ractor — Erlang-style actors

```toml
ractor = "0.14"
```

```rust
use ractor::{Actor, ActorRef};

struct WorkerActor;

#[async_trait::async_trait]
impl Actor for WorkerActor {
    type Msg = WorkMessage;
    type State = WorkerState;
    type Arguments = ();

    async fn pre_start(&self, _: ActorRef<Self::Msg>, _: ()) -> Result<Self::State, ActorProcessingErr> {
        Ok(WorkerState::new())
    }

    async fn handle(&self, _: ActorRef<Self::Msg>, msg: Self::Msg, state: &mut Self::State) -> Result<(), ActorProcessingErr> {
        match msg {
            WorkMessage::Process(data, reply) => { reply.send(compute(data))?; }
        }
        Ok(())
    }
}
```

When to use: stateful microservices, event-driven pipelines, systems needing fault isolation per actor.

### DataFusion + Ballista — distributed SQL/analytics

```toml
datafusion = "40"
# ballista for distributed: ballista = "0.12"
```

```rust
use datafusion::prelude::*;

let ctx = SessionContext::new();
ctx.register_parquet("spans", "s3://bucket/spans/*.parquet", Default::default()).await?;

let df = ctx.sql("SELECT operation, AVG(duration_ms) FROM spans GROUP BY operation").await?;
df.show().await?;
```

Ballista adds a remote scheduler + executor cluster for multi-machine DataFusion.

---

## Phase 8 — Algorithm Patterns

### Map-Reduce

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

### Pipeline Parallelism (stages in parallel, bounded backpressure)

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

### Work Queue / Task Stealing (custom scheduler)

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

### SPMD — MPI + Rayon Hybrid

```
mpirun -np N_NODES --bind-to socket ./mybinary
Each rank: rayon par_iter over its data partition (N_CPU_CORES threads)
Collective: allreduce for aggregation, barrier for synchronization
Result: N_NODES × N_CORES total parallelism
```

### Streaming / Chunked (data doesn't fit in RAM)

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

## Phase 9 — Profiling Parallel Programs

### Verify it's actually parallel

```bash
# Count threads during execution
watch -n 0.1 "cat /proc/$(pgrep mybinary)/status | grep Threads"

# htop: visually see per-core utilization — should see N cores at ~100%
htop
```

### Identify work imbalance (one core hot, others idle)

```bash
# Record all CPUs simultaneously
perf record -F 997 -a -g --call-graph=dwarf -- ./target/release/mybinary
perf report --sort=cpu,symbol --no-children | head -60
# If one CPU contributes > 50% of samples: work imbalance or serial bottleneck
```

### Memory bandwidth bound check

```bash
perf stat -e cache-misses,cache-references,instructions,cycles -- ./mybinary
# cache-miss rate > 5% → memory-bound → more threads won't help, fix data layout first
```

### tokio-console for async task profiling

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

### tracing for parallel observability

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

## Phase 10 — Anti-Patterns and Fixes

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

### False sharing fix

```rust
use crossbeam::utils::CachePadded;

// Before: all counters on same cache line
let counters: Vec<u64> = vec![0u64; n_threads];

// After: each counter on its own 64-byte cache line
let counters: Vec<CachePadded<u64>> = (0..n_threads).map(|_| CachePadded::new(0u64)).collect();
```

### Mutex bottleneck fix with rayon fold

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

---

## Quick Reference: Tool by Goal

| Goal | Primary tool | Notes |
|---|---|---|
| Parallelize a `for` loop | `rayon::par_iter()` | N_cores × (serial fraction limit) |
| Recursive divide-and-conquer | `rayon::join()` | Near-linear to tree depth |
| Per-thread temp buffers | `thread_local! + RefCell<Vec>` | Eliminates N-1 allocations |
| Async fan-out of N tasks | `tokio::task::JoinSet` | Bounded by I/O latency |
| Limit concurrent tasks | `tokio::sync::Semaphore` | Prevents OOM / thundering herd |
| CPU-bound work from async | `spawn_blocking(|| rayon_work())` | Unblocks async executor |
| 8-wide float math | `wide::f32x8` or auto-vectorize | Up to 8× throughput |
| Matrix/tensor ops on GPU | `candle` or `tch-rs` | 10–1000× vs. CPU |
| Custom GPU kernel | `wgpu` (cross-GPU) / `cudarc` (NVIDIA) | Workload-dependent |
| Multi-service RPC | `tonic` (cross-lang) / `tarpc` (Rust) | Network latency bound |
| HPC cluster numerical | `mpi` + `rayon` hybrid | N_nodes × N_cores |
| Fault-tolerant stateful actors | `ractor` | Event-driven concurrency |
| Distributed SQL/analytics | `datafusion` + `ballista` | Partition-count linear |
| Pipeline with backpressure | `crossbeam::channel::bounded` | CPU-bound stages |
| Detect work imbalance | `perf record -a` + `htop` | Diagnostic |
| Debug async task stalls | `tokio-console` | Diagnostic |

---

## Related Skills

| Skill | When to use it instead or alongside |
|---|---|
| [[rust-profiling]] | **Always run first** — measure serial fraction and hotspots before adding parallelism |
| [[rust-perf-tuning]] | Single-core CPU optimizations (caches, allocations, SIMD baselines) that compound with parallelism |
| [[rust-memory-optimization]] | When parallel work amplifies allocation pressure or causes OOM under concurrent load |
| [[rust-development]] | Hub skill — links all Rust skills and provides workflow overview |
