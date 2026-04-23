# Research Synthesis: JVM/Kotlin Performance Optimization

## Decision Required
What guidance should a Claude skill provide engineers to systematically diagnose and fix JVM/Kotlin performance bottlenecks?

## Context
Engineers working on JVM-based Kotlin applications (server, Android, KMP) face performance issues stemming from GC pressure, lock contention, coroutine overhead, and Kotlin-specific allocation patterns. The skill should guide a profiling-first approach, then provide a targeted playbook organized by problem class.

## Options Considered
| Option | Summary | Key Trade-off |
|--------|---------|---------------|
| GC: G1GC | Default JDK 9+, balanced throughput/latency | ~100ms pauses; tunable with `-XX:MaxGCPauseMillis` |
| GC: ZGC | Sub-millisecond pauses, generational since JDK 23 default | Slightly higher memory overhead |
| GC: Shenandoah | Similar to ZGC, generational GA in Java 25 | Less JVM-vendor support |
| GC: Parallel | Max throughput, STW pauses | Not suitable for latency-sensitive workloads |
| Kotlin: eager collections | Simple, idiomatic | Intermediate list allocations at each step |
| Kotlin: sequences | Lazy, short-circuits | Overhead for small N; terminal op required |
| Kotlin: value classes | Zero allocation for non-nullable | Boxes on nullable/generic use |
| Kotlin: inline functions | Eliminates lambda heap allocation | Bytecode size grows at call sites |
| JVM: virtual threads (Loom) | M:N scheduling, massive concurrency | Synchronized pinning fixed in JDK 24 (JEP 491) |

## Dominant Trade-off
**Measurement vs intuition**: JVM performance is counter-intuitive because the JIT, GC, and escape analysis frequently eliminate the costs developers optimize for. The dominant tension is: optimize based on profiling data vs optimize based on source-level heuristics. This skill lands firmly on the profiling-first side.

## Verified Facts (from web searches, April 2026)

### ZGC
- JDK 21: generational opt-in (`-XX:+UseZGC -XX:+ZGenerational`)
- JDK 23: generational is default (JEP 474)
- JDK 24+: non-generational ZGC removed — if on ZGC, you are already on generational
- ~10% throughput improvement over single-gen ZGC

### Virtual Threads / Loom
- JDK 21–23: `synchronized` blocks pin carrier threads
- JDK 24+ (JEP 491): synchronized no longer pins — use freely
- `ScopedValue` replaces `ThreadLocal` for virtual threads — finalized JDK 24 (JEP 487)

### Kotlin `-Xlambdas=indy`
- Kotlin 2.0+: `invokedynamic` is the **default** for lambda generation
- Applies to both Kotlin functional types (Function0/1/...) AND SAM conversions
- Reported 60% reduction in class file count in real projects
- If on Kotlin 2.0+, no explicit flag needed

### K2 `when` sealed class dispatch
- Kotlin 2.2.20+: `when` with type checks compiles to `invokedynamic` (equivalent to Java switch)
- Conditions: all branches are `is`/null checks, no guards, 2+ branches, same subject
- Eliminates O(N) `instanceof` chain — meaningful for large sealed hierarchies

### `withContext` same-dispatcher optimization
- Built into kotlinx.coroutines: if contexts are identical, no new coroutine is created and no thread switch occurs
- If dispatcher is same instance: skip dispatch
- Default + IO share thread pool — switching between them often reuses the same thread

### Project Valhalla
- Early-access build as of March 2026
- Kotlin `@JvmInline` was designed with Valhalla in mind — non-annotated value classes reserved for Valhalla primitive class backing
- When Valhalla ships: multi-field value classes, nullable without boxing

## Recommendation

**Choose**: Profiling-first workflow → targeted fix from the playbook

**Because**: JVM escape analysis already eliminates many source-level allocation concerns; the GC handles short-lived objects cheaply on modern collectors; JIT inlining and devirtualization optimize many call patterns. Optimizing before profiling wastes effort on non-bottlenecks.

**Accept these costs**: The profiling-first approach requires tooling setup (JFR, async-profiler, JMH) before any optimization is visible.

**Reject these alternatives**:
- Blanket "always use sequences": rejected because sequences are slower than eager collections for small N or single-step pipelines
- Blanket "avoid all synchronized": rejected because JDK 24+ removes the virtual thread pinning concern; synchronized is fine again

## Open Questions Before Committing
None — all major [TRAINING_ONLY] claims verified via web search.

## Sources
- findings-jvm-performance.md
- findings-kotlin-performance.md
- [JEP 474: Generational ZGC by Default](https://www.infoq.com/news/2024/05/java-zgc-update/)
- [JEP 491: Synchronize Virtual Threads without Pinning](https://microservicesinsider.substack.com/p/java-is-now-unstoppable-pinning-in)
- [Kotlin 2.0 invokedynamic default](https://kotlinlang.org/docs/whatsnew20.html)
- [Kotlin 2.2.20 when-expression invokedynamic](https://kotlinlang.org/docs/whatsnew2220.html)
- [Kotlin value classes & Valhalla](https://github.com/Kotlin/KEEP/blob/master/notes/value-classes.md)
