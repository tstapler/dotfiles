---
name: jvm-performance
description: Fix JVM/Kotlin performance bottlenecks identified via profiling. Covers concrete code changes for allocation pressure, GC tuning, lock contention, JIT blockers, and Kotlin-specific patterns. Use after jfr-profiling has identified the hotspot. Invoke when an engineer has a profile and needs to know what to change.
paths: "**/*.java,**/*.kt"
---

# JVM / Kotlin Performance Fix Playbook

**Prerequisite**: Use `/jfr-profiling` first to identify what's hot. This skill answers "now that I know the hotspot, what do I change?"

**Rule**: The smallest targeted change that removes the bottleneck. Don't touch cold paths.

---

## Quick Lookup: Stack Frame → Code Fix

Match what you see in the profile to a category, then open the linked reference for the concrete before/after code.

| Frame in collapsed stacks | Root cause | Reference |
|---|---|---|
| `HashMap.get` / boxing type in hot loop | Autoboxing on primitive map | [references/allocation-gc-pressure.md](references/allocation-gc-pressure.md) |
| `StringBuilder.<init>` in loop | String `+=` | [references/allocation-gc-pressure.md](references/allocation-gc-pressure.md) |
| `AppState.copy` / `data class.copy` | State copy in loop | [references/allocation-gc-pressure.md](references/allocation-gc-pressure.md) |
| `FunctionN.<init>` / `invoke` | Lambda allocating per call | [references/allocation-gc-pressure.md](references/allocation-gc-pressure.md) |
| `ArrayList.<init>` in filter/map chain | Intermediate collections | [references/allocation-gc-pressure.md](references/allocation-gc-pressure.md) |
| `G1YoungCollect` / `ZMarkStart` | GC pressure, allocation rate | [references/allocation-gc-pressure.md](references/allocation-gc-pressure.md) |
| `AQS.acquire` / `LockSupport.park` | Lock contention | [references/lock-contention.md](references/lock-contention.md) |
| Hot method despite few allocations, `deopt` in `-XX:+PrintCompilation` | JIT blocker (megamorphic call, oversized method, failed escape analysis) | [references/jit-blockers.md](references/jit-blockers.md) |
| Value class / sealed `when` / coroutine dispatch oddities | Kotlin-specific compilation behavior | [references/kotlin-specific-patterns.md](references/kotlin-specific-patterns.md) |
| `DriverManager.getConnection` / repeated `PreparedStatement.execute` | Missing connection pool or statement cache | [references/database-jdbc.md](references/database-jdbc.md) |
| GC log shows humongous allocations, concurrent mode failure, CodeCache/Metaspace exhaustion | GC configuration | [references/gc-configuration.md](references/gc-configuration.md) |

---

## Categories at a Glance

- **Allocation / GC pressure** — autoboxing, string concat in loops, `data class copy()`, lambda allocation, intermediate collections, pre-sizing, off-heap buffers. → [references/allocation-gc-pressure.md](references/allocation-gc-pressure.md)
- **Lock contention** — `ReentrantLock` vs `synchronized`, `StampedLock` optimistic reads, lock striping, coroutine actors, virtual-thread pinning by JDK version. → [references/lock-contention.md](references/lock-contention.md)
- **JIT blockers** — megamorphic call sites, methods too large to inline, escape-analysis failures. → [references/jit-blockers.md](references/jit-blockers.md)
- **Kotlin-specific patterns** — value classes and boxing rules, `trimIndent` cost, sealed-class `when` dispatch, `async`/`withContext` misuse, coroutine dispatcher selection. → [references/kotlin-specific-patterns.md](references/kotlin-specific-patterns.md)
- **Database / JDBC** — HikariCP configuration, batch inserts, read-only transaction hints. → [references/database-jdbc.md](references/database-jdbc.md)
- **GC configuration** — GC selection by workload, G1GC/ZGC production baselines, symptom-to-flag table. Only after allocation reduction isn't enough, and only after confirming with `jfrconv --gc` / `jstat -gcutil`. → [references/gc-configuration.md](references/gc-configuration.md)

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `jfr-profiling` | Collect JFR profiles and collapsed stacks to identify what's hot |
| `code-spring-boot` | Spring Boot-specific configuration and JPA/Hibernate tuning |
| `code-refactoring` | Structural refactors after eliminating the performance bottleneck |
| `code-debugging` | Investigate unexpected JVM crashes or OOM errors |
