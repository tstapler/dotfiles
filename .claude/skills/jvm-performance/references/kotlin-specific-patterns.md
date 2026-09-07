# Kotlin-Specific Patterns

## Value classes — zero-cost domain typing
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

## `trimIndent` at initialization, not per-call
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

## `when` on sealed classes — Kotlin 2.2.20+ generates efficient dispatch
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

## `async/await` without concurrency — use `withContext` instead
```kotlin
// ❌ Allocates a Deferred channel for no benefit
val result = async { compute() }.await()

// ✅ Same semantics, cheaper
val result = withContext(Dispatchers.Default) { compute() }
```
Use `async` only when launching work that runs concurrently with the calling coroutine.

## `withContext` same-dispatcher round-trips in loops
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

## Coroutine dispatcher selection
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

## Non-capturing lambda — confirm it's a singleton (Kotlin 2.0+)
```kotlin
// Kotlin 2.0+: invokedynamic by default — non-capturing lambdas are JVM-cached singletons
list.map { it * 2 }      // singleton — no allocation
list.map { it * mult }   // captures mult — allocates per call

// Kotlin < 2.0: add to build.gradle.kts to get the same behavior
kotlin { compilerOptions { freeCompilerArgs.add("-Xlambdas=indy") } }
```
