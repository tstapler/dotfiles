# Research Plan: JVM Performance Optimization for Claude Skill

## Goal
Research Java/JVM performance optimization and tuning + Kotlin-specific tips to produce a Claude skill that helps engineers systematically identify and fix performance bottlenecks.

## Subtopics

### 1. Java/JVM Performance Fundamentals
**Search strategy**: Target JVM internals, GC tuning, memory models, profiling tools, JIT compilation, and common anti-patterns.
**Search cap**: 5 searches
**Trade-off axes**: Impact vs complexity, general vs workload-specific, free vs paid tooling, runtime vs compile-time
**Output file**: `findings-jvm-performance.md`

Covers:
- JVM startup and warmup behavior
- Garbage collector selection and tuning (G1, ZGC, Shenandoah, Serial, Parallel)
- Memory management: heap sizing, off-heap, object allocation patterns
- JIT compilation: C1/C2, escape analysis, inlining thresholds
- Thread and lock contention (synchronized, ReentrantLock, StampedLock, VarHandle)
- I/O and network: NIO, blocking vs non-blocking
- Profiling tools: JFR, async-profiler, JMH, VisualVM, YourKit
- JDBC / database: connection pools, batch updates, prepared statements
- Common anti-patterns: excessive boxing, string concatenation in loops, premature optimization

### 2. Kotlin-Specific Performance
**Search strategy**: Focus on Kotlin compiler optimizations, coroutine overhead, inline functions, sealed classes vs enums, and comparisons to equivalent Java patterns.
**Search cap**: 5 searches
**Trade-off axes**: Kotlin idiom vs performance, readability vs speed, coroutine overhead vs threading simplicity
**Output file**: `findings-kotlin-performance.md`

Covers:
- Inline functions and reified generics — when they matter
- Data classes and value classes (Valhalla-adjacent): boxing implications
- Sequences vs collections: lazy evaluation trade-offs
- Coroutines: structured concurrency overhead, dispatcher selection, continuation cost
- Lambda allocation: when Kotlin creates object instances vs inlines
- Extension functions: no overhead vs synthetic accessor overhead
- Sealed classes vs enums: pattern matching performance
- `buildList`/`buildMap`: avoiding intermediate copies
- `@JvmStatic`, `@JvmField`, `@JvmOverloads`: interop cost removal
- KMP considerations: expect/actual dispatch, WASM/JS specific constraints

## Synthesis
After both subagents complete, parent produces `synthesis.md` mapping findings to actionable skill content organized by:
1. Profiling workflow (how to diagnose before optimizing)
2. GC and memory playbook
3. Concurrency playbook
4. Kotlin idiom playbook
5. Measurement (JMH, JFR)
