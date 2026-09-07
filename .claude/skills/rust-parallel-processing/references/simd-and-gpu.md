# Phase 3 — CPU SIMD

**#1 impact:** Enable `target-cpu=native` first — the compiler auto-vectorizes more than most people expect.

## Step 1: Check auto-vectorization

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

## Step 2: Manual SIMD with `wide` (stable, AVX2)

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

## When NOT to use manual SIMD

| Situation | Why | Fix |
|---|---|---|
| Auto-vectorized already | Manual SIMD won't help | Verify with `--emit asm` first |
| Branch-heavy code | SIMD requires branch-free math | Restructure to branchless |
| Non-contiguous memory | Gather/scatter patterns are slow | Reorder data to SoA layout first |
| Shipping to diverse CPUs | AVX2 not on old hardware | Use `wide`'s safe abstractions or runtime detection |

---

# Phase 4 — GPU Compute

**Rule of thumb before using GPU:**
- > 1M arithmetic operations per kernel launch
- Data already on GPU or transfer amortized over many launches
- Arithmetic intensity > ~10 ops/byte (otherwise bandwidth-bound)
- Latency is NOT the primary constraint (GPU launch overhead: 5–50µs)

**PCIe 4.0 x16 budget:** ~32 GB/s bidirectional. For 1M f32 (4 MB): transfer ≈ 125µs. GPU wins only when `compute_time >> transfer_time`. For batches < 64KB: CPU is almost always faster.

## wgpu 0.20 — cross-platform compute (Vulkan/Metal/DX12/WebGPU)

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

## cudarc 0.12 — NVIDIA CUDA (maximum performance)

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

# Phase 5 — GPU ML/Tensor Acceleration

**Decision:** use Python subprocess unless you need Rust-native inference (latency, deployment constraints, or embedding into a Rust service).

## candle (HuggingFace) — pure-Rust inference

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

## tch-rs — LibTorch bindings

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

## burn 0.14 — training + inference, multiple backends

```toml
burn = { version = "0.14", features = ["wgpu"] }  # or "cuda", "tch", "ndarray"
```

Backend is a compile-time type parameter — swap `Wgpu` for `Cuda` without code changes. Best for: new Rust ML projects, training on non-NVIDIA hardware via wgpu.
