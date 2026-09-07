# Allocation / GC Pressure

## What you see in the profile
- `GarbageCollector` / `G1YoungCollect` / `ZMarkStart` consuming > 5–10% of samples
- Allocation flame graph shows a specific call site allocating heavily
- `jfrconv --alloc` reveals repeated construction of the same type

## Autoboxing — `HashMap<String, Int>` in hot path
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

## String concatenation in loops
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

## `data class copy()` in a state update loop
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

## Lambda allocation in hot higher-order functions
```kotlin
// ❌ Each call site creates a Function1 instance
fun withRetry(block: () -> Unit) { /* ... */ }

// ✅ Caller's lambda body is copied to call site — zero allocation
inline fun withRetry(block: () -> Unit) { /* ... */ }
```
Use `noinline` when the lambda is stored or returned. Use `crossinline` when it's called from an inner non-inlined context (e.g., inside `Runnable`).

If on Kotlin 2.0+: non-capturing lambdas are already JVM-cached singletons via `invokedynamic` — only capturing lambdas need `inline`.

## Intermediate collection allocations in pipelines
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

## Pre-size collections when output size is known
```kotlin
// ❌ Backing array resizes O(log N) times
val results = buildList { addAll(source) }

// ✅ Pre-allocated; no resize copies
val results = buildList(capacity = source.size) { addAll(source) }

// ✅ For ArrayList directly
val list = ArrayList<Item>(source.size)
```

## Off-heap buffers to bypass GC entirely
Use for large, long-lived byte buffers (e.g., file cache, network buffer pool):
```kotlin
// Allocated off-heap — not visible to GC
val buffer = ByteBuffer.allocateDirect(4 * 1024 * 1024)

// ⚠️ Track lifecycle manually — no GC to free it
// ⚠️ Set limit: -XX:MaxDirectMemorySize=2g
```
