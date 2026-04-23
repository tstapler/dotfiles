# Findings: Kotlin Performance Optimization

## Summary

Kotlin compiles to JVM bytecode (or JS/WASM/Native), and most performance concerns reduce to: boxing overhead, lambda allocation, coroutine machinery cost, and collection traversal strategy. Unlike Java, Kotlin's abstraction mechanisms (inline functions, value classes, sequences) are designed to let you write expressive code without paying allocation penalties — but only when used correctly. The wrong choice at each abstraction boundary can silently introduce object churn that defeats the JIT.

---

## Options Surveyed

### 1. Inline Functions and Reified Generics

**What `inline` does to bytecode**: The compiler copies the entire function body — including any lambda parameters — to every call site. No `Function0`/`Function1` anonymous class is created; the lambda body is emitted inline.

```kotlin
inline fun <T> measure(block: () -> T): T {
    val start = System.nanoTime()
    val result = block()
    println(System.nanoTime() - start)
    return result
}
```

Without `inline`, `block` becomes a `Function0<T>` heap allocation at every call site. With `inline`, the lambda body is copied verbatim — zero allocation.

**Reified generics**: Normal generic functions erase type parameters to `Object` at the JVM level. `inline` + `reified` avoids erasure at the call site by emitting a concrete type token:

```kotlin
inline fun <reified T> instanceOf(value: Any): Boolean = value is T
// Compiles to: value instanceof T (concrete class, not erased)
```

**When it helps**:
- Higher-order functions called in tight loops (forEach, filter, map, let, run, also, apply, with)
- Type-safe builder DSLs
- Any function whose only purpose is to call a lambda

**When it hurts**:
- Large function bodies: code is duplicated at every call site, bloating bytecode. The JIT may refuse to compile oversized methods.
- Public API: inline functions cannot reference private/internal members
- Recursive functions: cannot be inlined

**`noinline`**: Marks a lambda parameter that should NOT be inlined — needed when the lambda is stored, passed to another function, or returned:

```kotlin
inline fun run(noinline stored: () -> Unit, executed: () -> Unit) {
    registry.add(stored)  // must be a real Function0 object
    executed()            // inlined
}
```

**`crossinline`**: Marks a lambda that is inlined but will be called from a non-inlined context. Prevents non-local returns:

```kotlin
inline fun runLater(crossinline block: () -> Unit) {
    Handler(Looper.getMainLooper()).post { block() }
}
```

---

### 2. Value Classes and Data Classes

**`@JvmInline value class`**: A single-property wrapper. The compiler attempts to eliminate the wrapper entirely, passing the underlying type directly on the JVM stack.

```kotlin
@JvmInline value class UserId(val raw: String)

fun process(id: UserId) { ... }
// JVM bytecode: process(String raw) — no UserId object created
```

**Boxing rules** (when the compiler MUST box):
- The value is used as a nullable type: `UserId?` forces boxing
- The value is stored in a collection: `List<UserId>` erases to `List<Object>` — boxed
- The value is passed to a generic function
- The value class implements an interface and is used via that interface

**When the compiler can unbox**:
- Non-nullable value class parameter to a non-generic function
- Local variable of value class type
- Return type of a non-generic function

**Limitations** [TRAINING_ONLY — verify exact Valhalla timeline]:
- Only one backing field (pre-Project Valhalla)
- No nullable without boxing overhead
- Cannot inherit from classes

**Data class `copy()` overhead**: `copy()` allocates a new instance for every call. In hot state-update loops, prefer manual construction:

```kotlin
// Allocates on every iteration
state = state.copy(count = state.count + 1)
// Prefer: State(state.count + 1, state.name, state.flag)
```

---

### 3. Sequences vs Collections

Kotlin's eager operations (`.filter`, `.map`, `.flatMap`) create intermediate `List` instances at each step. `.asSequence()` introduces a lazy pipeline.

```kotlin
// Eager: creates 3 intermediate lists
list.filter { it > 0 }.map { it * 2 }.take(10)

// Lazy: no intermediate lists, short-circuits at 10 elements
list.asSequence().filter { it > 0 }.map { it * 2 }.take(10).toList()
```

**When lazy wins**:
- Dataset > ~500–1000 elements
- Pipeline has multiple filter/map steps
- Terminal operation takes fewer elements than the full collection (`.first()`, `.take(n)`)

**When lazy loses**:
- Small collections (< ~100 elements): `Sequence` wraps each element in an `Iterator` state machine — overhead exceeds savings
- Single-step pipelines: `list.map { ... }` is as fast as the sequence equivalent
- Terminal operation is `.toList()` over the full dataset

---

### 4. Coroutines Overhead

**Suspension point cost**: Each `suspend` function is compiled into a state machine. At every `suspend` point, a continuation (heap-allocated, capturing local variables and resume index) is saved. Cost: one object allocation per suspension, plus context switch if a dispatcher is involved.

**`withContext` dispatch overhead**: `withContext` checks if a dispatcher switch is needed. Kotlin optimizes this to skip dispatch when already on the target dispatcher [TRAINING_ONLY — verify exact version]. Avoid `withContext(sameDispatcher)` in hot loops.

**`async/await` vs `launch`**:
- `launch`: fire and forget, returns `Job`. Slightly cheaper — no result channel.
- `async`: returns `Deferred<T>`. Use only when you need the result or want parallel fan-out.
- `async { ... }.await()` without concurrency is equivalent to `withContext` with one extra allocation.

**`StateFlow` vs `SharedFlow`**:
- `StateFlow`: always has a value, conflates — only the latest value emitted. Ideal for UI state.
- `SharedFlow`: configurable replay, no conflation. Ideal for events.

**`Dispatchers.IO` vs `Dispatchers.Default`**:
- `Default`: bounded to `max(2, CPU count)` threads. For CPU-bound work.
- `IO`: unbounded pool (up to 64 + CPU count threads). For blocking I/O.

**Coroutine dispatcher mapping per platform**:

| Platform | DB Dispatcher | Rationale |
|---|---|---|
| JVM | `Dispatchers.IO` | Pooled JDBC driver, N connections |
| Android | `Dispatchers.IO` | Native SQLite pool |
| iOS | `Dispatchers.Default` | GCD handles threading |
| WASM/JS | `Dispatchers.Default` | Single-threaded runtime |

---

### 5. Lambda Allocation

Kotlin lambdas that capture variables become anonymous class instances. Lambdas that do NOT capture anything are singletons.

```kotlin
val multiplier = 2
list.map { it * multiplier }  // captures — allocates on every call
list.map { it * 2 }           // no capture — singleton, zero allocation
```

**Method references**: `::method` compiles to a singleton `KFunction` reference when non-capturing. `instance::method` captures `instance` — still allocates.

**SAM conversions**: When a Kotlin lambda is passed to a Java Single Abstract Method interface, each call site creates a new object unless the lambda captures nothing. With `-Xlambdas=indy`, non-capturing SAMs are cached as JVM singletons.

---

### 6. Sealed Classes vs Enums

**Enums**: `when` over an enum compiles to a `tableswitch` JVM instruction — O(1) dispatch.

**Sealed classes**: `when` over a sealed type compiles to sequential `instanceof` checks — O(N) without compiler optimization [TRAINING_ONLY — verify K2 improvements].

**Memory layout**:
- Enum: pre-allocated static field — zero allocation on use
- Sealed class with data: allocates on each construction

Use enums for fixed, valueless variants. Use sealed classes when variants carry different data payloads.

---

### 7. Collection Builders

`buildList`, `buildMap`, `buildSet` (Kotlin 1.6+) avoid creating a temporary mutable collection that is then converted to immutable.

```kotlin
// Old: creates ArrayList, converts to immutable List
val items = mutableListOf<Item>().apply { add(a); add(b) }.toList()

// Builder: single ArrayList, wrapped as immutable view
val items = buildList { add(a); add(b) }
```

**Sizing**: `buildList(capacity = n) { ... }` pre-allocates the backing array — eliminates all resize copies.

---

### 8. JVM Interop Annotations

**`@JvmStatic`**: Without this, companion object members require a synthetic accessor from Java. In Kotlin-to-Kotlin calls, no difference.

```kotlin
class Foo {
    companion object {
        fun create(): Foo = Foo()              // Java: Foo.Companion.create()
        @JvmStatic fun create2(): Foo = Foo() // Java: Foo.create2() — direct
    }
}
```

**`@JvmField`**: Exposes a property as a plain JVM field with no getter/setter overhead.

**`@JvmOverloads`**: Generates N overloaded methods for a function with N default parameters. Cost: N extra methods in bytecode, N−1 extra invocations per call. Only use when Java callers need to omit trailing parameters.

---

### 9. String Operations

```kotlin
// Template in loop — O(N²) string copying
var result = ""
for (i in 0..10000) result += "item$i"

// StringBuilder — O(N) amortized
val sb = StringBuilder()
for (i in 0..10000) sb.append("item").append(i)
val result = sb.toString()
```

Single-expression string templates compile to `StringBuilder` automatically — fine. Concatenation across multiple statements in a loop is not.

**`trimIndent`**: Called at runtime, not folded at compile time in general [TRAINING_ONLY — verify K2]. Precompute at class initialization in hot paths.

**`String.format` vs template**: `String.format` uses `java.util.Formatter` — regex parsing plus vararg boxing. String templates are `StringBuilder` operations — faster and cheaper.

---

### 10. Kotlin Multiplatform (KMP) Specifics

**expect/actual dispatch**: Resolves at compile time — no runtime dispatch overhead.

**JS/WASM single-threaded constraints**:
- No `Dispatchers.IO` on JS/WASM — all I/O must be non-blocking
- `Dispatchers.Default` is single-threaded on JS; no parallelism
- `Mutex` and `Channel` work; `synchronized {}` does not exist on JS

**KMP collection performance**: `kotlin.collections` has separate implementations per platform. Profile platform-specifically.

---

### 11. Compiler Flags

**`-Xlambdas=indy`** (Kotlin 1.9+ / K2): Emits `invokedynamic` for lambda creation. Non-capturing lambdas become true singletons via JVM bootstrap cache. Reduces class file count, improves startup time, eliminates per-call-site allocation for non-capturing lambdas.

```kotlin
// build.gradle.kts
kotlin {
    compilerOptions {
        freeCompilerArgs.add("-Xlambdas=indy")
    }
}
```

**K2 compiler improvements** (Kotlin 2.x) [TRAINING_ONLY — verify full list]:
- Smarter inlining decisions
- Better constant folding
- Improved smart casts reducing redundant null checks
- Better dead code elimination

---

### 12. Profiling Kotlin Code

**Reading Kotlin bytecode**:

IntelliJ IDEA: `Tools → Kotlin → Show Kotlin Bytecode → Decompile`

Command line:
```bash
kotlinc Foo.kt -include-runtime -d out.jar
javap -c -p out/FooKt.class
```

Look for:
- `NEW` + `INVOKESPECIAL <init>` — object allocation
- `INVOKEVIRTUAL` vs `INVOKESTATIC` — virtual vs static dispatch
- `INVOKEDYNAMIC` — lambda via LambdaMetafactory (good with `indy`)
- Repeated `CHECKCAST` — generic type erasure workarounds

**JMH from Kotlin** via `kotlinx-benchmark`:

```kotlin
// build.gradle.kts
plugins { id("org.jetbrains.kotlinx.benchmark") version "0.4.x" }
benchmark { targets { register("jvm") } }
```

```kotlin
@State(Scope.Benchmark)
class CollectionBench {
    private val data = List(10_000) { it }

    @Benchmark
    fun eagerChain(bh: Blackhole) {
        bh.consume(data.filter { it % 2 == 0 }.map { it * 3 }.take(100))
    }

    @Benchmark
    fun lazyChain(bh: Blackhole) {
        bh.consume(data.asSequence().filter { it % 2 == 0 }.map { it * 3 }.take(100).toList())
    }
}
```

---

## Trade-off Matrix

| Idiom A | Idiom B | Readability | Allocation Cost | Throughput | Complexity |
|---|---|---|---|---|---|
| Eager collections | Sequences | A wins (simpler) | B wins (less intermediate) | B wins for large N + early termination | B adds pipeline setup cost |
| Data class | Value class | A wins (more features) | B wins (unboxed on JVM stack) | B wins in hot paths | B has more restrictions |
| `inline` HOF | Regular HOF | Tied | A wins (zero lambda alloc) | A wins (no virtual dispatch) | A increases bytecode size |
| `Dispatchers.IO` coroutine | Thread (blocking) | A wins | A wins (continuation vs Thread stack) | Tied for I/O-bound | B requires explicit lifecycle |
| `async/await` (concurrent) | Sequential `suspend` | Tied | B wins (no Deferred channel) | A wins (parallel fan-out) | A requires scope management |
| `StateFlow` | `SharedFlow` | A wins (simpler) | A wins (one slot) | A wins (conflation) | B needed for event semantics |
| Enum | Sealed class | Tied | A wins (pre-allocated) | A wins (tableswitch) | B needed for variant data |
| `buildList` | `mutableListOf + toList` | A wins | A wins (one allocation) | A wins | Tied |

---

## Risk and Failure Modes

1. **Over-inlining**: Large inlined functions inflate bytecode past JIT method-size limits, causing the optimizer to fall back to interpreted mode.
2. **Value class nullable boxing**: `UserId?` negates all value class benefits silently.
3. **Sequence terminal operation forgotten**: `list.asSequence().filter { ... }` without `.toList()` is a silent no-op.
4. **`withContext` on same dispatcher**: Spurious dispatcher round-trips in hot code.
5. **`async` without `await`**: Deferred exceptions are silently swallowed until `.await()` is called.
6. **`trimIndent` in hot path**: Appears safe, but involves regex and character scanning at runtime.
7. **SAM conversion allocation without `indy`**: Capturing SAM conversions create a new object per call — invisible in Kotlin source.

---

## Migration and Adoption Cost

| Change | Effort | Risk | Measurable Gain |
|---|---|---|---|
| Add `-Xlambdas=indy` to compiler flags | Low (1 line) | Low (JVM 8+) | Startup time, allocation reduction |
| Wrap primitive IDs in `@JvmInline value class` | Medium (type propagation) | Medium (boxing rules) | Zero-cost abstraction, type safety |
| Replace hot `data class copy()` | Low | Low | Allocation reduction in hot paths |
| Add `buildList(capacity)` | Low | None | Minor allocation/copy reduction |
| Convert large-dataset filter+map to sequences | Low | Low | Throughput on N > 500 |
| Switch `async { }.await()` to `withContext` | Low | Low | One fewer Deferred allocation |
| Add `@JvmStatic`/`@JvmField` to companions | Low | None | Java interop only |
| Add `kotlinx-benchmark` | Medium | Low | Enables measurement before optimizing |

---

## Operational Concerns

- **K2 compiler**: Migration may change inlining and smart cast behavior. Benchmark before/after.
- **Coroutine debugger overhead**: `kotlinx-coroutines-debug` adds instrumentation. Disable in production.
- **`StateFlow` and equality**: Uses `equals()` to suppress duplicate emissions. Override `equals` carefully for large state objects.
- **Kotlin/Native (iOS) memory model**: New MM since 1.7.20. Ensure coroutine scopes are not leaked across thread boundaries.

---

## Prior Art and Lessons Learned

- **JetBrains IntelliJ codebase**: Heavy use of `@JvmField` and `@JvmStatic`; explicit `ArrayList` pre-sizing in parser hot paths. 5–15% throughput gains from eliminating getter overhead in inner loops.
- **Android Jetpack Compose**: Uses `@Stable`/`@Immutable` as recomposition-scope hints. Value classes shine in `remember` blocks where structural equality via `equals()` is used.
- **Ktor**: `withContext` same-dispatcher optimization upstreamed to kotlinx.coroutines.
- **kotlinx.serialization**: Uses `@JvmInline value class` for descriptor handles to avoid boxing in the serialization core.
- **Square (OkHttp Kotlin migration)**: `String` concatenation in logging code was a significant allocation source; moved to lazy lambdas (`() -> String`) passed to loggers to avoid construction when logging is disabled.

---

## Open Questions

- [ ] Does K2 generate `tableswitch` for `when` on sealed classes? [TRAINING_ONLY — verify]
- [ ] Exact Kotlin version where `withContext` avoids same-dispatcher dispatch. Is it guaranteed? [TRAINING_ONLY — verify]
- [ ] Does `-Xlambdas=indy` apply to Kotlin functional types (`Function0`, `Function1`) or only SAM conversions? [TRAINING_ONLY — verify]
- [ ] `trimIndent` — does K2 fold it at compile time for const-equivalent literals? [TRAINING_ONLY — verify]
- [ ] What is the actual allocation size of a Kotlin continuation object? [TRAINING_ONLY — verify]

---

## Recommendation

Top 8 Kotlin-specific performance patterns, ordered by impact:

1. **Enable `-Xlambdas=indy`** — One compiler flag. Non-capturing lambdas become JVM-cached singletons. Zero source changes, measurable improvement in allocation rate and startup time.
2. **Inline higher-order functions in hot paths** — Eliminates `Function1` heap allocations at call sites.
3. **Use `asSequence()` for multi-step pipelines on large collections** — Break-even typically around N=100–500 depending on operation count.
4. **Replace hot `data class copy()` with explicit construction** — In state update loops (ViewModel reducers, coroutine actors).
5. **Wrap domain identifiers in `@JvmInline value class`** — Zero runtime cost for non-nullable, non-generic usage. Prevents type confusion bugs.
6. **Avoid `async { ... }.await()` without concurrent work** — Use `withContext` instead.
7. **Pre-size collection builders** — `buildList(capacity = knownSize)` avoids array resize-and-copy.
8. **Profile with `kotlinx-benchmark` before optimizing** — The JIT's escape analysis may already be eliminating allocations you're manually working around.

---

## Pending Web Searches

1. `site:kotlinlang.org -Xlambdas=indy invokedynamic lambda` — exact semantics for Kotlin functional types vs SAM
2. `kotlin k2 compiler when sealed class tableswitch bytecode 2024` — K2 `when` dispatch improvement
3. `kotlinx.coroutines withContext same dispatcher optimization skip` — version and guarantee level
4. `kotlin k2 trimIndent constant folding compile time` — compile-time folding status
5. `kotlin coroutine continuation object size heap allocation bytes` — actual continuation size
6. `kotlin value class nullable boxing jvm valhalla 2024 2025` — Project Valhalla timeline
