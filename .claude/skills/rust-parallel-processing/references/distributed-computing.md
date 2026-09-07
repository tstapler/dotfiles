# Phase 6 — Multi-Machine: Message Passing

## tonic (gRPC) — cross-language, production-grade

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

## tarpc — Rust-native RPC (simpler, no protobuf)

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

## quinn (QUIC) — low-latency, multiplexed

```toml
quinn = "0.11"
```

QUIC advantages over TCP+gRPC: no head-of-line blocking across streams, 0-RTT reconnection, built-in TLS. Use when: many small parallel messages, latency-sensitive, mobile/unreliable networks.

## ZeroMQ patterns for HPC pipelines

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

# Phase 7 — Multi-Machine: Distributed Compute

## MPI — tightly coupled HPC

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

## ractor — Erlang-style actors

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

## DataFusion + Ballista — distributed SQL/analytics

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
