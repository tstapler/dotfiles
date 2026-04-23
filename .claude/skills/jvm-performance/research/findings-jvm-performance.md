# Findings: JVM Performance Optimization

## Summary

JVM performance optimization is a discipline that spans garbage collector selection, memory management, JIT compilation, concurrency, I/O, and tooling. The core principle is **measure first, tune second** — premature optimization without profiling data produces fragile, unreadable configurations that rarely address the actual bottleneck. For most server applications, the highest ROI changes are: correct heap sizing, appropriate GC selection, eliminating object allocation hot paths, and using HikariCP with proper pool sizing for database work.

---

## Options Surveyed

### Garbage Collectors

**Serial GC** (`-XX:+UseSerialGC`)
Single-threaded collection. Stop-the-world for both young and old generation. No parallelism, no concurrent marking.
- Use when: single-core environments, small heaps (<256 MB), CLI tools, microservices with sub-100ms latency budgets that can tolerate occasional full pauses.
- Avoid when: multi-core servers, heaps >512 MB, latency-sensitive services.

**Parallel GC** (`-XX:+UseParallelGC`, default pre-JDK 9)
Multi-threaded stop-the-world collections. Maximizes throughput by using all available CPU during GC.
- Use when: batch processing, offline analytics, throughput matters more than latency, JDK 8 compatibility required.
- Key flags: `-XX:ParallelGCThreads=N`, `-XX:MaxGCPauseMillis=200`, `-XX:GCTimeRatio=99`.
- Avoid when: applications require pause times <500ms.

**G1GC** (`-XX:+UseG1GC`, default JDK 9-20)
Divides heap into equal-sized regions (~1-32 MB each). Concurrent marking with short stop-the-world evacuation pauses. Aims to meet a configurable pause-time target.
- Use when: heaps 4 GB-64 GB, latency target 50-200ms, general-purpose server applications.
- Key flags:
  - `-XX:MaxGCPauseMillis=200` — soft pause target (default 200ms)
  - `-XX:G1HeapRegionSize=16m` — larger regions reduce region count overhead; tune if heap >32 GB
  - `-XX:G1NewSizePercent=20 -XX:G1MaxNewSizePercent=40` — bound young gen size
  - `-XX:G1ReservePercent=10` — emergency reserve to prevent promotion failure
  - `-XX:InitiatingHeapOccupancyPercent=45` — trigger concurrent marking earlier if fragmentation observed
  - `-XX:G1MixedGCLiveThresholdPercent=85` — exclude mostly-live regions from mixed GC

**ZGC** (`-XX:+UseZGC`, production-ready JDK 15+)
Concurrent garbage collector with sub-millisecond pause targets regardless of heap size. Uses colored pointers and load barriers. Pause times are constant even at terabyte-scale heaps.
- Use when: heaps from 8 MB to multi-TB, pause target <1ms, JDK 15+ available, latency-critical APIs (p99 requirements).
- Key flags:
  - `-XX:+UseZGC`
  - `-XX:ZCollectionInterval=5` — force periodic collection (seconds) to prevent memory pressure spikes
  - `-XX:ZAllocationSpikeTolerance=5` — multiplier for spike headroom
  - `-Xms` == `-Xmx` — recommended for ZGC to prevent resizing pauses
  - `-XX:SoftMaxHeapSize=<N>g` — ZGC tries to keep heap below this while still allowing growth
- Cost: ~15% higher CPU overhead vs G1 due to concurrent work; requires 1-3 extra CPU cores.

**Shenandoah** (`-XX:+UseShenandoahGC`, OpenJDK 12+, backported to JDK 8/11 in Red Hat builds)
Concurrent evacuation (unlike ZGC's relocation approach). Also targets sub-10ms pauses. Uses Brooks forwarding pointers.
- Use when: similar to ZGC, but preferred when Red Hat/Amazon Corretto builds are in use or JDK <15 is required.
- Key flags:
  - `-XX:ShenandoahGCMode=iu` — incremental-update mode (default, lower CPU than traversal)
  - `-XX:ShenandoahGCHeuristics=adaptive` — default; also `compact`, `static`, `aggressive`
  - `-XX:ShenandoahUnloadClassesFrequency=5` — class unloading interval

### JVM Flag Reference by Category

**Startup / heap sizing**
```
-Xms4g -Xmx4g           # Set initial and max heap equal — prevents resizing, predictable behavior
-XX:+AlwaysPreTouch      # Touch all heap pages at startup — eliminates page-fault latency spikes
-XX:MetaspaceSize=256m   # Initial metaspace commit
-XX:MaxMetaspaceSize=512m
-Xss512k                 # Thread stack size; reduce from 1MB default if spawning many threads
```

**GC logging (JDK 9+)**
```
-Xlog:gc*:file=/var/log/app/gc.log:time,uptime,level,tags:filecount=10,filesize=20m
```

**JDK 8 GC logging**
```
-verbose:gc
-XX:+PrintGCDetails
-XX:+PrintGCDateStamps
-Xloggc:/var/log/app/gc.log
-XX:+UseGCLogFileRotation
-XX:NumberOfGCLogFiles=10
-XX:GCLogFileSize=20m
```

**JIT / compilation**
```
-XX:+TieredCompilation                # Default on JDK 7+; ensure not disabled
-XX:CompileThreshold=10000            # Method invocations before C2 compilation
-XX:MaxInlineSize=35                  # Max bytecode size to inline unconditionally
-XX:FreqInlineSize=325                # Max bytecode size to inline hot methods
-XX:+OptimizeStringConcat             # Eliminates StringBuilder chaining overhead
-XX:+EliminateAllocations             # Scalar replacement via escape analysis
-XX:ReservedCodeCacheSize=256m        # Increase if JIT compilation stops (CodeCache full)
```

**Debugging / diagnostics**
```
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/var/dumps/
-XX:+PrintCompilation                 # Log JIT compilation events (high-volume, use in staging)
-XX:+UnlockDiagnosticVMOptions
-XX:+PrintInlining                    # Log inlining decisions
-XX:+LogCompilation                   # Emit XML compilation log (for JITWatch analysis)
```

**Virtual threads (JDK 21+)**
```
-Djdk.tracePinnedThreads=short        # Log when virtual threads pin to carrier threads
```

---

## Trade-off Matrix

| GC | Max Throughput | Max Latency | Memory Overhead | Tunability | Min JDK |
|----|---------------|-------------|-----------------|------------|---------|
| Serial | Low (single-threaded) | Very High (STW full GC) | Minimal | Low | 1.2 |
| Parallel | **Highest** | High (STW, parallel) | Low | Medium | 1.4 |
| G1GC | High | Medium (10-200ms typical) | Medium (region metadata) | **Highest** | 7 (default 9) |
| ZGC | Medium-High | **<1ms** (constant) | Medium-High (+15% CPU) | Medium | 11 (prod 15) |
| Shenandoah | Medium-High | <10ms typical | Medium (+10-12% CPU) | Medium | 12 (backport to 8/11) |

**Notes:**
- Throughput = total work done per unit time under sustained load
- Latency = worst-case pause duration (p99.9 stop-the-world)
- Memory overhead includes per-region/per-pointer metadata, not just live set
- G1GC "tunability" is highest because it has the most well-documented knobs; ZGC deliberately has fewer

---

## Risk and Failure Modes

### GC
- **G1 humongous allocation**: Objects >50% of region size bypass normal allocation and can trigger stop-the-world. Fix: increase `-XX:G1HeapRegionSize` or avoid large single allocations.
- **G1 promotion failure / concurrent mode failure**: Old gen fills before concurrent marking completes. Fix: lower `InitiatingHeapOccupancyPercent`, increase heap, or reduce allocation rate.
- **ZGC allocation stall**: Application pauses waiting for GC to free memory because allocation outpaces collection. Fix: increase `-XX:ZAllocationSpikeTolerance`, reduce allocation rate, or increase heap.
- **Shenandoah degenerated GC**: Falls back to stop-the-world when concurrent phase cannot keep up. Check `-Xlog:gc` for `Degenerated GC`.
- **Parallel GC OutOfMemoryError with fragmentation**: Heap is large but allocation fails due to fragmentation. Fix: switch to G1 or ZGC.

### JIT
- **CodeCache exhaustion**: JIT compilation stops, application reverts to interpreted mode — severe throughput drop. Symptoms: `CodeCache is full. Compiler has been disabled.` in logs. Fix: `-XX:ReservedCodeCacheSize=256m` or larger.
- **Deoptimization storms**: Loaded class hierarchy change invalidates compiled code; all affected methods re-compile. Common after classloader activity. Monitor with `-XX:+PrintCompilation`.
- **Megamorphic call sites**: JIT cannot devirtualize call sites with >2 receiver types; no inlining. Redesign to use final/sealed classes or dispatch manually.

### Memory
- **Off-heap leak**: `DirectByteBuffer` objects hold native memory; GC doesn't reclaim until the buffer object is collected. Use `-XX:MaxDirectMemorySize=<N>g` and monitor `java.nio:type=BufferPool,name=direct`.
- **Metaspace leak**: Classloader leak (common in hot-deploy containers, scripting engines). Monitor `jvm_memory_pool_bytes_used{pool="Metaspace"}`.
- **Humongous object fragmentation**: Large objects leave gaps in G1 regions that cannot be reused. Profile with `-Xlog:gc+heap=debug`.

### Threading
- **Virtual thread pinning**: Virtual threads using `synchronized` blocks or native frames pin the carrier thread, negating Loom's concurrency benefits. Replace with `ReentrantLock`, use `-Djdk.tracePinnedThreads=short`.
- **False sharing**: Multiple threads write to different fields in the same cache line (64 bytes). Use `@Contended` annotation (requires `-XX:-RestrictContended`) or pad structs manually.

---

## Migration and Adoption Cost

### Switching GC collectors
- Serial to G1GC: Low risk. Add flags, redeploy. Monitor GC logs for first 24h. Expect better latency, slightly lower peak throughput.
- G1GC to ZGC: Low-medium risk. Requires JDK 15+. Applications using large `synchronized` blocks may see pinning overhead (only relevant with virtual threads). Test under production-representative load for 1 week. Expect +15% CPU, dramatically lower p99 latency.
- G1GC to Shenandoah: Same as ZGC but available on older JDKs via Corretto/Adoptium builds.

### Migrating to virtual threads (JDK 21)
- Replace `Executors.newFixedThreadPool(N)` with `Executors.newVirtualThreadPerTaskExecutor()`.
- Replace `synchronized` critical sections with `ReentrantLock` if they wrap blocking I/O.
- High-risk: thread-local variables holding large objects (now held per-task, not per-carrier), `ThreadLocal` caches for expensive objects (now created per-virtual-thread with no pooling benefit).

### HikariCP migration
- Drop-in if using c3p0, DBCP, Tomcat pool. Align `maximumPoolSize` to `(CPU cores * 2) + effective_spindle_count` formula.

---

## Operational Concerns

### Heap sizing heuristics
- Set `-Xms` == `-Xmx` in production to prevent heap resizing pauses and OS memory over-commit.
- Target 50-70% heap occupancy under sustained load — headroom for burst allocation and GC to work without pressure.
- For containers: set `-Xmx` explicitly; do not rely on `UseContainerSupport` alone for critical services. `-XX:MaxRAMPercentage=75.0` is safer than `UseContainerSupport` default of 25%.
- For ZGC/Shenandoah: extra headroom (30-40% free) reduces concurrent collection pressure.

### GC log monitoring
- Parse logs with GCEasy (web tool) or `gc-log-visualizer` CLI.
- Key metrics: GC frequency, pause time distribution (p50/p99/p999), allocation rate (MB/s), promotion rate.
- Alert thresholds: >10% time in GC (Parallel), >1s pauses (G1), any `Degenerated GC` (Shenandoah).

### Container environments
- JDK 8u191+ and JDK 10+ respect cgroup memory limits via `-XX:+UseContainerSupport` (default on).
- Always set explicit `-Xmx`; container OOM kills are silent and harder to diagnose than JVM OOM.
- Set `--cpus` on container AND let JVM see it: `ParallelGCThreads`, `ConcGCThreads` auto-configure from visible CPU count.

---

## Prior Art and Lessons Learned

### Twitter / X Engineering
Migrated from CMS to G1GC across fleet, then to ZGC for latency-sensitive ad-serving paths. Key lesson: G1GC `MaxGCPauseMillis` is a *target*, not a guarantee — heap fragmentation can override it. ZGC eliminated the tail latency spikes but required 15-20% more memory headroom.

### Netflix
Extensively documented G1GC tuning for JVM services. Found that `InitiatingHeapOccupancyPercent=35` (vs default 45) reduced concurrent mode failures on write-heavy services. Published tooling (gc-advisor) for automated flag recommendation from GC logs.

### LinkedIn
Found that eliminating autoboxing in hot deserialization paths (using Eclipse Collections `IntLongHashMap` vs `HashMap<Integer, Long>`) reduced GC pressure by 30% on recommendation services.

### Disruptor (LMAX)
Demonstrated that lock-free ring buffers with mechanical sympathy (cache-line awareness, `@Contended`, avoiding false sharing) can achieve >6M transactions/sec on commodity hardware where `ConcurrentLinkedQueue` saturated at 200K/sec.

### Martin Thompson / Aeron project
Demonstrated that off-heap memory (`DirectByteBuffer`, unsafe memory access) avoids GC entirely for I/O buffers in low-latency messaging. Pattern: allocate off-heap once at startup, reuse slices, never allocate in steady state.

---

## Open Questions

1. ZGC generational mode (`-XX:+ZGenerational`, JDK 21 experimental, JDK 23 default) — how much throughput does it recover vs non-generational ZGC? [TRAINING_ONLY — verify with JDK 23 release notes]
2. Project Leyden (AOT compilation, JDK 24+) — does ahead-of-time compilation affect GC interaction and warm-up behavior in meaningful ways for long-lived servers? [TRAINING_ONLY — verify]
3. Virtual thread `ThreadLocal` behavior under high cardinality — what is the actual memory cost per virtual thread for `ThreadLocal` inheriting from parent at scale? Requires benchmarking with JMH.
4. Shenandoah vs ZGC for JDK 17 LTS on ARM64 (AWS Graviton) — latency characteristics may differ due to memory model differences. [TRAINING_ONLY — verify with production benchmarks]
5. HikariCP connection pool sizing for read replicas behind a proxy (PgBouncer) — pool-on-pool dynamics and statement caching invalidation.

---

## Recommendation

### Profiling-First Workflow

1. **Establish baseline metrics** before changing anything.
   - Enable JFR: `java -XX:StartFlightRecording=duration=60s,filename=baseline.jfr -jar app.jar`
   - Or attach to running process: `jcmd <pid> JFR.start duration=120s settings=profile filename=app.jfr`
   - Capture under representative production load (or load test that matches p95 traffic).

2. **Identify the actual bottleneck** — GC, CPU, allocation, contention, or I/O.
   - GC-bound: `jstat -gcutil <pid> 1000` — look for >5% time in GC columns (YGC, FGC).
   - Allocation-bound: async-profiler allocation profiling: `./profiler.sh -e alloc -d 30 -f alloc.html <pid>`
   - CPU-bound / lock contention: async-profiler CPU: `./profiler.sh -e cpu -d 30 -f cpu.html <pid>`
   - I/O-bound: JFR socket/file I/O events, or `pidstat -d 1`.

3. **Analyze with the right tool for the symptom.**
   - GC: GCEasy or `jstat`, look at GC frequency and pause distributions.
   - Hot methods / allocation sites: async-profiler flame graph — focus on widest frames.
   - Lock contention: async-profiler with `-e lock`, or JFR `JavaMonitorWait` events.
   - JIT issues: `-XX:+PrintCompilation` output, JITWatch for inlining decisions.

4. **Make one change at a time.** Re-baseline after each change. Revert if no improvement.

5. **Validate under load** — microbenchmarks with JMH for micro-optimizations, load tests for GC/pool changes.

### Top 5 Highest-Impact JVM Flags for Typical Server Application

```bash
# 1. Equal heap bounds — eliminate resize pauses, prevent OS overcommit surprises
-Xms4g -Xmx4g

# 2. Pre-touch heap pages at startup — eliminate page-fault latency spikes under first load
-XX:+AlwaysPreTouch

# 3. Select appropriate GC — G1GC is the right default for most services; ZGC if p99 latency matters
-XX:+UseG1GC -XX:MaxGCPauseMillis=100
# Or for latency-critical JDK 15+:
# -XX:+UseZGC

# 4. Structured GC logging — visibility is required before tuning
-Xlog:gc*:file=/var/log/app/gc.log:time,uptime,level,tags:filecount=10,filesize=20m

# 5. OOM heap dump — never lose the evidence when it matters most
-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/var/dumps/
```

### Additional High-Impact Non-Flag Changes (by category)

**GC pressure reduction (often more impactful than GC tuning):**
- Eliminate autoboxing in hot paths: use `int[]` instead of `List<Integer>`, primitive collections (Eclipse Collections, Koloboke).
- Pool expensive objects (parsers, formatters, connections) — only if profiler shows allocation is the bottleneck.
- Avoid string concatenation in loops — use `StringBuilder` or string templates.
- Prefer `byte[]` / `ByteBuffer` for I/O intermediates over repeated `String` construction.

**Threading:**
- JDK 21+: use virtual threads for blocking I/O tasks (`Executors.newVirtualThreadPerTaskExecutor()`).
- Replace contended `synchronized` with `ReentrantLock` or `StampedLock` where read-heavy.
- Use `VarHandle` for single-field CAS operations instead of `AtomicReference` wrapper objects.

**Database:**
- HikariCP pool size: `(CPU_cores * 2) + 1` for OLTP; never >50 without benchmarking.
- Enable prepared statement caching: HikariCP sets this via `cachePrepStmts=true` in `dataSourceProperties`.
- Batch inserts: `addBatch()` / `executeBatch()` — 10-100x throughput improvement for bulk writes.
- Use `@Transactional(readOnly = true)` for read-only operations — signals driver to skip journal entries on some DBs, enables read-replica routing.

---

## Detailed Section Notes

### GC Tuning — Key Flags Quick Reference

```bash
# G1GC production baseline
java \
  -Xms8g -Xmx8g \
  -XX:+UseG1GC \
  -XX:MaxGCPauseMillis=100 \
  -XX:G1HeapRegionSize=16m \
  -XX:G1NewSizePercent=20 \
  -XX:G1MaxNewSizePercent=40 \
  -XX:InitiatingHeapOccupancyPercent=35 \
  -XX:G1ReservePercent=15 \
  -XX:+AlwaysPreTouch \
  -XX:+HeapDumpOnOutOfMemoryError \
  -XX:HeapDumpPath=/var/dumps/ \
  -Xlog:gc*:file=/var/log/gc.log:time,uptime:filecount=10,filesize=20m \
  -jar app.jar

# ZGC production baseline (JDK 17+)
java \
  -Xms16g -Xmx16g \
  -XX:+UseZGC \
  -XX:ZCollectionInterval=10 \
  -XX:+AlwaysPreTouch \
  -XX:SoftMaxHeapSize=14g \
  -XX:+HeapDumpOnOutOfMemoryError \
  -Xlog:gc*:file=/var/log/gc.log:time,uptime:filecount=10,filesize=20m \
  -jar app.jar
```

### Memory Management

**Heap sizing heuristics:**
- Live set = minimum heap needed. Measure with G1GC: look for `Heap used after GC` in GC logs immediately after full GC. Target live set * 2.5-3x for normal services.
- For ZGC: live set * 4x due to concurrent relocation requiring extra headroom.

**Object allocation patterns:**
- Short-lived objects (<1 young GC cycle): nearly free in generational GC — allocation is a pointer bump, collection is "free" in a young GC if objects don't survive.
- Long-lived objects: allocate once and reuse (e.g., connection pools, parser instances). Avoid re-creating these in request handlers.
- Large objects (>50% G1 region size): go directly to old gen as "humongous objects" — avoid or pre-allocate.

**Off-heap memory:**
```java
// Allocate off-heap buffer (not counted in -Xmx)
ByteBuffer direct = ByteBuffer.allocateDirect(1024 * 1024);
// JDK 9+ Cleaner for explicit release
import java.lang.ref.Cleaner;
Cleaner cleaner = Cleaner.create();
cleaner.register(myObject, () -> { /* release native resource */ });
```

**Escape analysis / scalar replacement:**
The JIT eliminates allocations entirely when it proves an object does not escape the method. Enabled by default:
```
-XX:+DoEscapeAnalysis
-XX:+EliminateAllocations
```
Defeats: storing object in a field, passing to a method the JIT cannot inline, putting in a collection.

### JIT Compilation

**Tiered compilation pipeline:**
- Tier 0: Interpreter
- Tier 1: C1 (no profiling) — simple compilation, fast startup
- Tier 2: C1 (limited profiling)
- Tier 3: C1 (full profiling) — instruments call/branch counts
- Tier 4: C2 — heavy optimization using profile data: inlining, loop unrolling, devirtualization, vectorization

**OSR (On-Stack Replacement):** Replaces an executing interpreted method with compiled code mid-execution (while in a loop). Enables JIT to kick in for long-running loops. OSR entry points are compiled separately from normal entry points.

**Inlining:** Most impactful JIT optimization — eliminates call overhead and enables downstream optimizations (constant folding, dead-code elimination).
- `MaxInlineSize=35`: unconditional limit (bytecodes). Increase with care — too large causes CodeCache pressure.
- `FreqInlineSize=325`: inlining budget for "hot" methods (called frequently). JIT may exceed `MaxInlineSize` if method is hot enough.
- To check inlining decisions: `-XX:+PrintInlining -XX:+UnlockDiagnosticVMOptions` or JITWatch.

**Loop unrolling:** JIT unrolls tight loops automatically. Manual hint: ensure loop body is simple and inlineable, avoid virtual calls inside loops.

### Thread / Lock Contention

**Lock comparison:**

| Mechanism | Read Throughput | Write Throughput | Reentrancy | Condition Support | Best For |
|---|---|---|---|---|---|
| `synchronized` | Medium | Medium | Yes | Yes (Object.wait) | Simple critical sections |
| `ReentrantLock` | Medium | Medium | Yes | Yes (Condition) | Timed tryLock, interruptible wait |
| `ReentrantReadWriteLock` | High | Low | Yes | Yes | Read-heavy, rare writes |
| `StampedLock` | **Highest** | Medium | No | No | Read-dominant, optimistic reads |
| `VarHandle` CAS | N/A | **Highest** | No | No | Single-field atomic updates |

**Lock striping pattern:**
```java
// Instead of one lock for a Map<K,V>:
private final Lock[] stripes = new Lock[16];
// Use: stripes[key.hashCode() & 15].lock()
// Reduces contention by 16x at cost of 16 lock objects
```

**StampedLock optimistic read:**
```java
StampedLock lock = new StampedLock();
long stamp = lock.tryOptimisticRead();
int x = this.x; int y = this.y;
if (!lock.validate(stamp)) {
    stamp = lock.readLock();
    try { x = this.x; y = this.y; }
    finally { lock.unlockRead(stamp); }
}
```

**Virtual threads (JDK 21):**
```java
// Create executor with one virtual thread per task
ExecutorService vte = Executors.newVirtualThreadPerTaskExecutor();

// Pinning -- avoid synchronized around I/O:
// BAD (pins carrier thread):
synchronized (lock) { socket.read(buffer); }
// GOOD:
lock.lock(); try { socket.read(buffer); } finally { lock.unlock(); }
```

**ForkJoinPool:** Use for divide-and-conquer workloads. `commonPool()` is shared; create a dedicated pool for CPU-intensive tasks to avoid starving other users of the common pool.

### I/O Optimization

**NIO Channel read:**
```java
// Non-blocking NIO -- multiplexed via Selector
Selector selector = Selector.open();
SocketChannel channel = SocketChannel.open();
channel.configureBlocking(false);
channel.register(selector, SelectionKey.OP_READ);

// Zero-copy sendfile (Linux kernel optimization)
FileChannel src = FileChannel.open(path);
SocketChannel dest = socketChannel;
src.transferTo(0, src.size(), dest); // avoids user-space copy
```

**Direct vs heap ByteBuffer:**
- `ByteBuffer.allocateDirect()`: off-heap, no GC pressure, faster I/O (no copy from heap to native), but slower allocation and JVM-managed cleanup.
- `ByteBuffer.allocate()`: on-heap, GC-managed, faster per-allocation, extra copy on I/O.
- Rule: use direct buffers for long-lived I/O buffers pooled at startup; use heap buffers for short-lived processing.

**Buffer pooling pattern:**
```java
Deque<ByteBuffer> pool = new ArrayDeque<>();

ByteBuffer acquire(int size) {
    ByteBuffer buf = pool.pollFirst();
    if (buf == null || buf.capacity() < size) {
        buf = ByteBuffer.allocateDirect(size);
    }
    buf.clear();
    return buf;
}

void release(ByteBuffer buf) { pool.addFirst(buf); }
```

### Profiling Tools

**JFR (Java Flight Recorder)** — preferred for production profiling
- Low overhead (~1-3% CPU) — safe for production.
- Captures: GC events, JIT compilation, thread sleep/wait, socket I/O, file I/O, lock contention, CPU samples.
```bash
# Start with app
java -XX:StartFlightRecording=duration=60s,settings=profile,filename=app.jfr -jar app.jar

# Attach to running JVM
jcmd <pid> JFR.start duration=120s settings=profile filename=app.jfr

# Stop and dump
jcmd <pid> JFR.stop name=1 filename=app.jfr

# Analyze: JDK Mission Control
jmc   # GUI tool -- open .jfr file
```

**async-profiler** — best for CPU/allocation flame graphs
- Works via `AsyncGetCallTrace` — no safepoint bias (unlike JFR CPU sampling before JDK 16).
- Available at: https://github.com/jvm-profiling-tools/async-profiler
```bash
# CPU flame graph
./profiler.sh -e cpu -d 30 -f cpu.html <pid>

# Allocation flame graph
./profiler.sh -e alloc -d 30 -f alloc.html <pid>

# Lock contention
./profiler.sh -e lock -d 30 -f lock.html <pid>

# Wall-clock (includes blocked time -- best for latency analysis)
./profiler.sh -e wall -d 30 -t -f wall.html <pid>
```

**Reading flame graphs:**
- Width = time/samples (wider = more time spent there)
- Stack grows upward (top frame = where CPU was)
- Start at wide base frames to identify hot call paths
- Look for unexpected depth (deep recursion = stack allocation pressure)
- Look for `GC` frames — indicates GC overhead

**JMH (Java Microbenchmark Harness)** — the only correct way to benchmark JVM code
```kotlin
// Gradle dependency
testImplementation("org.openjdk.jmh:jmh-core:1.37")
annotationProcessor("org.openjdk.jmh:jmh-generator-annprocess:1.37")
```
```java
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.NANOSECONDS)
@Warmup(iterations = 5, time = 1)
@Measurement(iterations = 10, time = 1)
@Fork(1)
@State(Scope.Benchmark)
public class MyBenchmark {
    @Benchmark
    public int myMethod() { return hotPath(); }
}
// Run: java -jar benchmarks.jar -prof gc  (includes GC overhead in output)
```

**`jstat`** — quick GC health check without JFR overhead
```bash
jstat -gcutil <pid> 1000 60  # print every 1s for 60 iterations
# Columns: S0 S1 E O M CCS YGC YGCT FGC FGCT CGC CGCT GCT
# O (old gen %) creeping toward 100% = promotion pressure
# FGC count increasing = investigate
```

**VisualVM / JConsole** — useful for quick MBean inspection and heap histogram; not suitable for production profiling (higher overhead than JFR).

**YourKit** — commercial, excellent for memory leak detection and thread analysis; particularly good at tracking object retention paths.

### Common Anti-Patterns

**Autoboxing in hot paths:**
```java
// BAD -- allocates Long objects on every insert
Map<String, Long> counts = new HashMap<>();
counts.merge(key, 1L, Long::sum);

// GOOD -- Eclipse Collections
MutableObjectLongMap<String> counts = ObjectLongHashMap.newMap();
counts.addToValue(key, 1L); // no allocation
```

**String concatenation in loops:**
```java
// BAD -- O(n^2) -- each += creates new String object
String result = "";
for (String item : items) result += item + ",";

// GOOD
StringBuilder sb = new StringBuilder(items.size() * 20);
for (String item : items) sb.append(item).append(',');
String result = sb.toString();
```

**Excessive `HashMap` for primitive keys:**
```java
// BAD -- boxing overhead
Map<Integer, String> map = new HashMap<>();

// GOOD -- Eclipse Collections
IntObjectHashMap<String> map = new IntObjectHashMap<>();
```

**Collections.sort() on large arrays vs Arrays.sort():**
- `Collections.sort()` copies to array internally — extra allocation.
- `Arrays.sort()` works in-place on primitive arrays using dual-pivot quicksort (timsort for objects).
- For primitives: always use `Arrays.sort(int[])` — cannot box, cannot GC.

**`String.format()` in logging hot paths:**
```java
// BAD -- always creates formatted string even if log level disabled
logger.debug(String.format("User %s logged in at %s", user, time));

// GOOD -- lazy evaluation
logger.debug("User {} logged in at {}", user, time); // SLF4J parameterized logging
```

**Repeated `Class.forName()` / reflection:**
- Cache `Method` / `Field` references in static fields; `setAccessible(true)` once at startup.

### Database / JDBC

**HikariCP configuration:**
```properties
# Pool sizing: formula = (core_count * 2) + effective_spindle_count
# For 4-core machine with SSD: (4 * 2) + 1 = 9
maximumPoolSize=10
minimumIdle=5   # set equal to maximumPoolSize in steady-state services
connectionTimeout=30000   # 30s -- fail fast rather than queue
idleTimeout=600000        # 10 min -- recycle idle connections
maxLifetime=1800000       # 30 min -- force recycle before DB-side timeout
keepaliveTime=300000      # 5 min -- prevent firewall from closing idle connections
```

**Prepared statement caching (PostgreSQL JDBC example):**
```properties
dataSource.cachePrepStmts=true
dataSource.prepStmtCacheSize=250
dataSource.prepStmtCacheSqlLimit=2048
dataSource.useServerPrepStmts=true
```

**Batch insert pattern:**
```java
PreparedStatement ps = conn.prepareStatement("INSERT INTO t (a,b) VALUES (?,?)");
for (Row row : rows) {
    ps.setString(1, row.a);
    ps.setLong(2, row.b);
    ps.addBatch();
    if (++count % 1000 == 0) ps.executeBatch(); // flush every 1000
}
ps.executeBatch(); // flush remainder
```

**N+1 query avoidance:**
- Identify with: query count logging (`p6spy`, Hibernate `show_sql`), or slow-query log.
- Fix with: JOIN FETCH (JPA), DataLoader pattern (GraphQL), or explicit batch loading.
- In Spring Data JPA: `@EntityGraph` to force eager fetch, or `@Query("SELECT p FROM Page p JOIN FETCH p.blocks")`.

**Read-only transaction hint:**
```java
@Transactional(readOnly = true)  // Spring -- signals driver to skip transaction journal on some DBs
public List<Page> getPages() { ... }
```

---

## Pending Web Searches

The following claims are based on training data (cutoff August 2025) and should be verified:

1. **ZGC generational mode in JDK 23** — `[TRAINING_ONLY]` verify that `-XX:+ZGenerational` is the default in JDK 23 and review its throughput recovery benchmarks vs non-generational ZGC.

2. **Project Leyden / AOT compilation** — `[TRAINING_ONLY]` verify JDK version availability and whether it affects steady-state performance (not just startup).

3. **async-profiler 3.x API changes** — `[TRAINING_ONLY]` verify current syntax for `profiler.sh` vs `asprof` binary in async-profiler v3.

4. **HikariCP latest recommended version** — `[TRAINING_ONLY]` verify current stable release and any configuration changes in recent versions.

5. **Virtual thread ThreadLocal pinning behavior** — `[TRAINING_ONLY]` verify whether JDK 21+ has addressed ThreadLocal pinning and what the current recommended pattern is for ThreadLocal caches with virtual threads.

6. **JFR in JDK 21 safepoint-bias fix** — `[TRAINING_ONLY]` verify whether JDK 21 JFR CPU sampling is fully safepoint-bias free or whether async-profiler still has an advantage.
