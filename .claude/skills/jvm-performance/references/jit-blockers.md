# JIT Blockers

## What you see in the profile
- A method that should be fast is unexpectedly hot despite few allocations
- Repeated `checkcast` / `instanceof` in bytecode
- `-XX:+PrintCompilation` shows `made not entrant` / `deopt` on the hot method

## Megamorphic call site — more than 2 implementations at one call site
```kotlin
// ❌ JIT cannot devirtualize if there are 3+ implementations
interface Transformer { fun transform(s: String): String }

// Dispatched as virtual call in tight loop — no inlining
for (item in items) result += transformers[i % 3].transform(item)

// ✅ Seal to 2 concrete types at the hot call site
// OR: specialize the loop for each type separately
// OR: use a direct function reference instead of interface
```

## Method too large to inline — split hot private methods
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

## Escape analysis failure — object unnecessarily heap-allocated
The JIT's escape analysis eliminates allocations for objects that don't escape the method. It fails when:
- The object is stored in a field or collection
- The object is passed to a virtual method the JIT can't resolve
- The method is too large

Diagnosis: allocation profiler shows your local data-carrier object in hot allocation sites.

Fix: keep it small, keep it local, keep the method small enough for C2 to analyze.
