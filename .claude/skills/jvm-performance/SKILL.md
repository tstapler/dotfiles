---
name: jvm-performance
description: Fix JVM/Kotlin performance bottlenecks identified via profiling. Covers concrete code changes for allocation pressure, GC tuning, lock contention, JIT blockers, and Kotlin-specific patterns. Use after jfr-profiling has identified the hotspot. Invoke when an engineer has a profile and needs to know what to change.
---

# JVM / Kotlin Performance Fix Playbook

**Prerequisite**: Use `/jfr-profiling` first to identify what's hot. This skill answers "now that I know the hotspot, what do I change?"

**Rule**: The smallest targeted change that removes the bottleneck. Don't touch cold paths.

---

## Allocation / GC Pressure

### What you see in the profile
- `GarbageCollector` / `G1YoungCollect` / `ZMarkStart` consuming > 5–10% of samples
- Allocation flame graph shows a specific call site allocating heavily
- `jfrconv --alloc` reveals repeated construction of the same type

### Autoboxing — `HashMap<String, Int>` in hot path
```kotlin
// ❌ Boxes every Int read and write
val counts = HashMap<String, Int>()
counts["key"] = counts.getOrDefault("key", 0) + 1

// ✅ Primitive map — zero boxing
// Eclipse Collections
val counts = MutableObjectIntMap<String>()
counts.addToValue("key", 1)

// Agrona (lower-level, faster)
val counts = Object2IntHashMap<String>(16, 0.6f, 0)
counts.merge("key", 1, Int::plus)
```

### String concatenation in loops
```kotlin
// ❌ O(N²) — each += copies the entire string
var result = ""
for (item in items) result += item.name + ","

// ✅ O(N) amortized
val sb = StringBuilder(items.size * 16)  // pre-size estimate
for (item in items) sb.append(item.name).append(',')
val result = sb.toString()
```
Single-expression templates (`"Hello $name"`) already compile to `StringBuilder` — only loops are a problem.

### `data class copy()` in a state update loop
```kotlin
// ❌ Allocates a new object on every state transition
fun reducer(state: AppState, event: Event): AppState = when (event) {
    is Increment -> state.copy(count = state.count + 1)
    is Reset     -> state.copy(count = 0, name = "")
}

// ✅ Direct construction — same result, no copy machinery
fun reducer(state: AppState, event: Event): AppState = when (event) {
    is Increment -> AppState(state.count + 1, state.name, state.flag)
    is Reset     -> AppState(0, "", state.flag)
}
```

### Lambda allocation in hot higher-order functions
```kotlin
// ❌ Each call site creates a Function1 instance
fun withRetry(block: () -> Unit) { /* ... */ }

// ✅ Caller's lambda body is copied to call site — zero allocation
inline fun withRetry(block: () -> Unit) { /* ... */ }
```
Use `noinline` when the lambda is stored or returned. Use `crossinline` when it's called from an inner non-inlined context (e.g., inside `Runnable`).

If on Kotlin 2.0+: non-capturing lambdas are already JVM-cached singletons via `invokedynamic` — only capturing lambdas need `inline`.

### Intermediate collection allocations in pipelines
```kotlin
// ❌ Allocates 3 intermediate Lists for 10k elements
items.filter { it.active }
     .map { it.value }
     .take(10)

// ✅ No intermediate lists; short-circuits after 10 matches
items.asSequence()
     .filter { it.active }
     .map { it.value }
     .take(10)
     .toList()
```
Break-even: ~100–500 elements. For a single operation (`list.map { ... }`), sequences add overhead — don't convert.

### Pre-size collections when output size is known
```kotlin
// ❌ Backing array resizes O(log N) times
val results = buildList { addAll(source) }

// ✅ Pre-allocated; no resize copies
val results = buildList(capacity = source.size) { addAll(source) }

// ✅ For ArrayList directly
val list = ArrayList<Item>(source.size)
```

### Off-heap buffers to bypass GC entirely
Use for large, long-lived byte buffers (e.g., file cache, network buffer pool):
```kotlin
// Allocated off-heap — not visible to GC
val buffer = ByteBuffer.allocateDirect(4 * 1024 * 1024)

// ⚠️ Track lifecycle manually — no GC to free it
// ⚠️ Set limit: -XX:MaxDirectMemorySize=2g
```

---

## Lock Contention

### What you see in the profile
- `AbstractQueuedSynchronizer.acquire` / `LockSupport.park` prominent in lock profile
- `jfrconv --lock` shows a specific lock dominating wait time
- Throughput drops sharply as thread count increases

### Replace `synchronized` with `ReentrantLock` for try-lock / interruptible patterns
```kotlin
// ❌ synchronized — no timeout, no interruptibility
@Synchronized
fun update(value: Int) { state = compute(value) }

// ✅ ReentrantLock with timeout — caller can give up
private val lock = ReentrantLock()

fun update(value: Int): Boolean {
    if (!lock.tryLock(100, TimeUnit.MILLISECONDS)) return false
    return try { state = compute(value); true }
    finally { lock.unlock() }
}
```

### StampedLock for read-heavy shared state
```kotlin
private val lock = StampedLock()
private var cachedValue = 0

// Optimistic read — no lock acquired, no contention
fun read(): Int {
    val stamp = lock.tryOptimisticRead()
    val value = cachedValue
    if (lock.validate(stamp)) return value          // fast path: no write occurred
    val readStamp = lock.readLock()                 // fallback: full read lock
    return try { cachedValue } finally { lock.unlockRead(readStamp) }
}

fun write(v: Int) {
    val stamp = lock.writeLock()
    try { cachedValue = v } finally { lock.unlockWrite(stamp) }
}
```

### Lock striping — reduce contention on shared maps
```kotlin
// ❌ One lock for all keys — every thread serializes
class Cache<K, V> {
    @Synchronized fun get(key: K): V? = map[key]
}

// ✅ 16 independent locks — ~16x less contention
class StripedCache<K, V>(stripes: Int = 16) {
    private val locks = Array(stripes) { ReentrantLock() }
    private val maps  = Array(stripes) { HashMap<K, V>() }
    private fun idx(key: K) = key.hashCode().and(0x7FFFFFFF) % stripes

    fun get(key: K): V? {
        val i = idx(key); locks[i].lock()
        return try { maps[i][key] } finally { locks[i].unlock() }
    }
    fun put(key: K, value: V) {
        val i = idx(key); locks[i].lock()
        try { maps[i][key] = value } finally { locks[i].unlock() }
    }
}
```

### Replace synchronized shared state with coroutine actor
For Kotlin code where multiple coroutines update shared state:
```kotlin
// ❌ Mutex around every state access
private val mutex = Mutex()
private var count = 0
suspend fun increment() = mutex.withLock { count++ }

// ✅ Actor owns the state — no shared mutable state, no locks
sealed interface CounterMsg
data object Increment : CounterMsg
class GetValue(val reply: CompletableDeferred<Int>) : CounterMsg

class Counter(scope: CoroutineScope) {
    private val channel = scope.actor<CounterMsg> {
        var count = 0
        for (msg in channel) when (msg) {
            Increment -> count++
            is GetValue -> msg.reply.complete(count)
        }
    }
    suspend fun increment() = channel.send(Increment)
    suspend fun value(): Int = CompletableDeferred<Int>().also { channel.send(GetValue(it)) }.await()
}
```

### Virtual thread + synchronized (JDK version matters)
```kotlin
// JDK 21–23: synchronized around blocking I/O pins the carrier thread
// → Replace with ReentrantLock if using virtual threads

// JDK 24+: synchronized is fixed (JEP 491) — pinning removed
// → No change needed
```

---

## JIT Blockers

### What you see in the profile
- A method that should be fast is unexpectedly hot despite few allocations
- Repeated `checkcast` / `instanceof` in bytecode
- `-XX:+PrintCompilation` shows `made not entrant` / `deopt` on the hot method

### Megamorphic call site — more than 2 implementations at one call site
```kotlin
// ❌ JIT cannot devirtualize if there are 3+ implementations
interface Transformer { fun transform(s: String): String }

// Dispatched as virtual call in tight loop — no inlining
for (item in items) result += transformers[i % 3].transform(item)

// ✅ Seal to 2 concrete types at the hot call site
// OR: specialize the loop for each type separately
// OR: use a direct function reference instead of interface
```

### Method too large to inline — split hot private methods
The JIT will not inline methods > 325 bytecodes (default). If a hot helper is large, the call overhead dominates:
```kotlin
// ❌ One large private method — JIT won't inline it
private fun processBlock(block: Block): Result { /* 400+ lines of logic */ }

// ✅ Split: small hot path inlined, cold path remains large
private fun processBlock(block: Block): Result {
    if (block.type == SIMPLE) return processSimple(block)  // inlined
    return processComplex(block)                            // not inlined, OK — cold path
}
private fun processSimple(block: Block): Result { /* 30 lines */ }
private fun processComplex(block: Block): Result { /* 380 lines */ }
```

### Escape analysis failure — object unnecessarily heap-allocated
The JIT's escape analysis eliminates allocations for objects that don't escape the method. It fails when:
- The object is stored in a field or collection
- The object is passed to a virtual method the JIT can't resolve
- The method is too large

Diagnosis: allocation profiler shows your local data-carrier object in hot allocation sites.

Fix: keep it small, keep it local, keep the method small enough for C2 to analyze.

---

## Kotlin-Specific Patterns

### Value classes — zero-cost domain typing
```kotlin
// ❌ Type confusion possible; String allocates anyway
fun loadPage(id: String): Page

// ✅ Compiler-enforced typing; no allocation for non-nullable non-generic use
@JvmInline value class PageId(val raw: String)
fun loadPage(id: PageId): Page
```

**Boxing rules** — value class IS boxed when:
- `PageId?` (nullable) — prefer non-nullable in APIs
- `List<PageId>` — erases to `List<Object>`
- Passed to `fun <T> process(id: T)` — generic parameter

**Valhalla note**: The `@JvmInline` annotation reserves non-annotated value classes for future Project Valhalla primitive class backing (multi-field, nullable without boxing). Ongoing as of early 2026.

### `trimIndent` at initialization, not per-call
```kotlin
// ❌ Regex + character scan on every invocation
fun buildQuery(id: String) = """
    SELECT * FROM pages
    WHERE id = '$id'
""".trimIndent()

// ✅ Template with pre-trimmed prefix
private val QUERY_PREFIX = """
    SELECT * FROM pages
    WHERE id = '
""".trimIndent()
```
Or use parameterized prepared statements (which also avoids SQL injection).

### `when` on sealed classes — Kotlin 2.2.20+ generates efficient dispatch
```kotlin
// Kotlin 2.2.20+: compiles to invokedynamic (Java switch equivalent) when:
//   • all branches are `is` or null checks
//   • no guard conditions  
//   • same subject throughout
//   • 2+ branches
when (event) {
    is LoadEvent   -> handleLoad(event)
    is SaveEvent   -> handleSave(event)
    is DeleteEvent -> handleDelete(event)
}
// Older Kotlin / conditions not met → sequential instanceof checks (O(N))
// Fix for older Kotlin: use enum for valueless variants (compiles to tableswitch)
```

### `async/await` without concurrency — use `withContext` instead
```kotlin
// ❌ Allocates a Deferred channel for no benefit
val result = async { compute() }.await()

// ✅ Same semantics, cheaper
val result = withContext(Dispatchers.Default) { compute() }
```
Use `async` only when launching work that runs concurrently with the calling coroutine.

### `withContext` same-dispatcher round-trips in loops
```kotlin
// ❌ Dispatches N times — each withContext checks for context switch
for (id in ids) {
    withContext(Dispatchers.IO) { db.load(id) }  // dispatch overhead per iteration
}

// ✅ One dispatch, N operations
withContext(Dispatchers.IO) {
    for (id in ids) db.load(id)
}
```
Same-dispatcher `withContext` skips thread switching (built-in optimization), but still has coroutine bookkeeping overhead — avoid in tight loops.

### Coroutine dispatcher selection
```kotlin
// ✅ CPU-bound: bounded pool (max(2, CPU count) threads)
withContext(Dispatchers.Default) { parseDocument(text) }

// ✅ Blocking I/O: unbounded pool (keeps CPU cores free)
withContext(Dispatchers.IO) { file.readText() }

// ✅ KMP — use platform abstraction, never hardcode
expect val DB: CoroutineDispatcher
// JVM/Android actual: Dispatchers.IO
// iOS/WASM actual: Dispatchers.Default
```

### Non-capturing lambda — confirm it's a singleton (Kotlin 2.0+)
```kotlin
// Kotlin 2.0+: invokedynamic by default — non-capturing lambdas are JVM-cached singletons
list.map { it * 2 }      // singleton — no allocation
list.map { it * mult }   // captures mult — allocates per call

// Kotlin < 2.0: add to build.gradle.kts to get the same behavior
kotlin { compilerOptions { freeCompilerArgs.add("-Xlambdas=indy") } }
```

---

## Database / JDBC

### What you see in the profile
- `DriverManager.getConnection` or `HikariPool.getConnection` in hot path → no pool / pool exhausted
- `PreparedStatement.execute` compiling SQL on every call → no statement cache
- N×M individual inserts for a batch operation → missing `executeBatch()`

### HikariCP minimum correct configuration
```kotlin
HikariConfig().apply {
    jdbcUrl = "jdbc:postgresql://host/db"
    // CPU * 2 + 1 for I/O-bound workloads (Hikari recommendation)
    maximumPoolSize = 2 * Runtime.getRuntime().availableProcessors() + 1
    minimumIdle = maximumPoolSize   // pre-warm all connections; no ramp-up delay
    connectionTimeout = 30_000
    maxLifetime = 1_800_000         // recycle before DB server drops the connection
    cachePrepStmts = true
    prepStmtCacheSize = 250
    prepStmtCacheSqlLimit = 2048
}
```

### Batch inserts — order-of-magnitude faster than row-by-row
```kotlin
// ❌ N round-trips
for (item in items) db.insert(item)

// ✅ 1 round-trip
connection.prepareStatement("INSERT INTO items (id, name) VALUES (?, ?)").use { stmt ->
    for (item in items) {
        stmt.setInt(1, item.id)
        stmt.setString(2, item.name)
        stmt.addBatch()
    }
    stmt.executeBatch()
}
```

### Read-only transaction hint
```kotlin
connection.isReadOnly = true  // skip undo log writes, may use read-replica
```

---

## GC Configuration

When allocation reduction is not enough, tune the GC. Run `jfrconv --gc` (or check `jstat -gcutil`) to confirm GC is the problem before touching flags.

### GC selection

| Workload | GC | Minimum flags |
|---|---|---|
| General server app | G1GC (default JDK 9+) | `-Xms=Xmx -XX:MaxGCPauseMillis=200` |
| Latency-sensitive (< 1ms pauses) | ZGC | `-XX:+UseZGC` (JDK 23+ gen by default) |
| Max throughput, pauses acceptable | Parallel GC | `-XX:+UseParallelGC` |
| Batch / single-core container | Serial GC | `-XX:+UseSerialGC` |

### G1GC production baseline
```bash
-XX:+UseG1GC
-Xms4g -Xmx4g                     # fix heap — eliminate resize pauses
-XX:MaxGCPauseMillis=200          # target (not guaranteed)
-XX:G1HeapRegionSize=16m          # increase if > 50% of regions are "humongous"
-XX:G1NewSizePercent=20
-XX:G1MaxNewSizePercent=40
-Xlog:gc*:file=gc.log:time,uptime # always log
```

### ZGC production baseline (JDK 21+)
```bash
-XX:+UseZGC                        # generational by default JDK 23+; add -XX:+ZGenerational on JDK 21
-Xms4g -Xmx4g
-XX:SoftMaxHeapSize=3500m          # leave headroom for concurrent marking
-Xlog:gc*:file=gc.log:time,uptime
```

### Common GC symptoms and fixes

| GC log symptom | Cause | Fix |
|---|---|---|
| Frequent young GCs | High allocation rate | Profile alloc hotspots; apply patterns above |
| G1 "humongous allocation" | Object > 50% region size | Increase `-XX:G1HeapRegionSize` or reduce object |
| `Concurrent Mode Failure` | GC falling behind allocation | Increase heap; reduce allocation rate |
| `CodeCache is full` | JIT cache exhausted | `-XX:ReservedCodeCacheSize=512m` |
| Metaspace OOM | Class loader leak / many dynamic classes | `-XX:MaxMetaspaceSize=512m`; fix leak |
| Full GC on startup only | Small initial heap forces resize | Set `-Xms` == `-Xmx` |

---

## Quick Lookup: Stack Frame → Code Fix

| Frame in collapsed stacks | Root cause | Fix section |
|---|---|---|
| `HashMap.get` / boxing type in hot loop | Autoboxing on primitive map | [Autoboxing](#autoboxing) |
| `StringBuilder.<init>` in loop | String `+=` | [String concat](#string-concatenation) |
| `AppState.copy` / `data class.copy` | State copy in loop | [data class copy](#data-class-copy) |
| `FunctionN.<init>` / `invoke` | Lambda allocating per call | [Lambda allocation](#lambda-allocation) |
| `ArrayList.<init>` in filter/map chain | Intermediate collections | [Sequences](#intermediate-collection-allocations) |
| `AQS.acquire` / `LockSupport.park` | Lock contention | [Lock contention](#lock-contention) |
| `G1YoungCollect` / `ZMarkStart` | GC pressure | [Allocation patterns](#allocation--gc-pressure) |
| `DriverManager.getConnection` | Missing connection pool | [HikariCP](#hikaricp-minimum-correct-configuration) |
| `PreparedStatement.execute` (repeated SQL text) | No statement cache | [HikariCP config](#hikaricp-minimum-correct-configuration) |
| `withContext` inside a loop | Per-iteration dispatch | [withContext loops](#withcontext-same-dispatcher-round-trips-in-loops) |
