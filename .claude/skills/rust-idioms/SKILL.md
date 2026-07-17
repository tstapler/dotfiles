---
name: rust-idioms
description: Idiomatic review for Rust — async/Tokio daemon design, ports-and-adapters trait boundaries, and thiserror/anyhow error handling. Use when reviewing or writing Rust code that defines async trait "ports" (dependency-inversion boundaries), runs a single-threaded Tokio daemon (current_thread runtime + LocalSet/spawn_local), or crosses a wire/domain type boundary. Covers async fn in traits vs async-trait, Rc/RefCell vs Arc/Mutex, tokio::select! cancel-safety, blocking calls in async context, thiserror-vs-anyhow error typing, wire/domain type separation, and common anti-patterns (clone in hot loops, overly generic port bounds). NOT for pure performance/profiling work (see rust-profiling, rust-perf-tuning, rust-memory-optimization, rust-parallel-processing) or unsafe/CLI/wasm-bindgen review (no dedicated skill yet — use the sdd:6-verify research-agent fallback for those).
paths: "**/*.rs"
metadata:
  type: feedback
---

# Rust Idioms — Async Daemons, Ports & Adapters, Error Handling

Review checklist for Rust code in native+wasm workspace daemons: async/Tokio runtime
usage, trait-based port design (hexagonal/ports-and-adapters), and error handling
conventions. Grade each finding **MUST FIX** or **SUGGEST**.

## When to Use This Skill

- Reviewing or writing async trait "ports" — dependency-inversion boundaries meant to be
  implemented by multiple adapters (real + test/mock)
- Reviewing a single-threaded async daemon (`current_thread` runtime, `LocalSet`/`spawn_local`)
- Reviewing error type design across a library/binary or port/adapter boundary
- Reviewing wire-format types (JSON/RPC/protocol) that cross into domain logic

Not a fit for: raw performance tuning (route to `rust-profiling`/`rust-perf-tuning`/
`rust-memory-optimization`/`rust-parallel-processing` via the `rust-development` hub),
`unsafe` soundness review, CLI (clap) design, or wasm-bindgen JS interop — these have no
dedicated skill yet; fall back to the research-agent path in `sdd:6-verify`.

## Checklist

### Async / Tokio

1. **[ASYNC] async fn in traits vs `#[async_trait]`** — MUST FIX if mixed inconsistently.
   Port traits should use native `async fn` in traits (stable since 1.75) or RPITIT, *unless*
   the trait must be used as `dyn Trait`. For dyn-compatible ports, either hand-write
   `Pin<Box<dyn Future<Output = T> + Send + '_>>` return types or keep `#[async_trait]` on
   that specific trait consistently — flag a trait that mixes both styles across its methods.

2. **[ASYNC] `Rc<RefCell<T>>` vs `Arc<Mutex<T>>`** — MUST FIX if mismatched with runtime.
   In a single-threaded daemon (`current_thread` runtime + `LocalSet`/`spawn_local`), shared
   state should be `Rc<RefCell<T>>`, not `Arc<Mutex<T>>` (unnecessary atomic/lock overhead).
   Conversely, flag `Rc`/`RefCell` anywhere a task might be `tokio::spawn`ed (not
   `spawn_local`) onto a multi-threaded runtime — `Rc`/`RefCell` are `!Send`/`!Sync` and this
   will fail to compile or, if wrapped unsafely, cause UB.

3. **[ASYNC] `tokio::select!` cancel-safety** — MUST FIX. Every branch's future must be
   cancel-safe (safe to drop mid-poll), or the future must be `pin!`-ed once and reused
   across loop iterations rather than recreated each `select!` call (recreating loses
   in-flight progress).

4. **[ASYNC] No blocking calls inside `async fn` bodies** — MUST FIX. Blocking I/O, CPU-bound
   loops, or blocking mutex acquisition inside an `async fn` starves the executor. Use
   `spawn_blocking` for blocking work, or `tokio::task::yield_now()` to yield between chunks
   of a long CPU-bound loop.

### Error Handling

5. **[ERROR] `thiserror` in ports, `anyhow` at the binary boundary** — MUST FIX if violated.
   Port/library trait `Result<T, E>` signatures should use a `thiserror`-derived typed enum.
   `anyhow::Error` may appear in binary/daemon-level aggregation code, but flag `anyhow`
   inside a port trait's error type — it erases the caller's ability to match on failure modes.

6. **[ERROR] No bare `String` or `Box<dyn Error>` error types in new code** — MUST FIX.
   Should be a `thiserror` enum with named variants.

7. **[ERROR] `.unwrap()` / `.expect()` scope** — MUST FIX outside these three contexts:
   tests, a proven-impossible invariant (with an `.expect("why this can't happen")` message
   explaining the invariant), or one-time startup code that runs before the serve loop begins.

8. **[ERROR] Error message style** — SUGGEST. Lowercase, no trailing punctuation (matches
   `std`/`thiserror` convention so messages compose cleanly when wrapped).

### Type Boundaries & Naming

9. **[NAMING] Wire types distinct from domain types** — MUST FIX if a wire/DTO type (JSON,
   RPC, protocol) leaks directly into a port trait signature. Convert at the adapter boundary
   via `From`/`TryFrom`; port traits should only ever see domain types.

10. **[STYLE] Newtype wrappers over raw primitives** crossing port boundaries (e.g. `UserId(u64)`
    not bare `u64`), with a complete `#[derive]` set (`Debug`, `Clone`, `PartialEq`, `Eq`,
    `Hash` as applicable) — SUGGEST.

### Style & Anti-Patterns

11. **[STYLE] Iterator chains over manual loops** with mutable accumulators, except where
    control flow is genuinely complex (early return, multiple break conditions) — SUGGEST.

12. **[ANTI-PATTERN] `.clone()` in hot loops** where `&T` or `Cow<'_, T>` would work —
    SUGGEST (MUST FIX if profiling data shows it's hot).

13. **[ANTI-PATTERN] Overly generic port trait bounds** (e.g. `T: Clone + Send + Sync + 'static`
    on a trait that doesn't need all of them) — a dependency-inversion smell that leaks
    adapter implementation constraints into the port. SUGGEST.

### Performance & Edition

14. **[PERF] Release profile tuning** — SUGGEST. Check `Cargo.toml` `[profile.release]` for
    `lto`/`codegen-units` tuning on daemon binaries; flag hot-path allocation churn (repeated
    `Vec`/`String` growth) without pre-sizing (`with_capacity`).

15. **[ANTI-PATTERN/ASYNC] Edition 2024 `unsafe_op_in_unsafe_fn`** — MUST FIX. This lint is
    default-on in edition 2024: explicit `unsafe { }` blocks are required even inside
    `unsafe fn` bodies — an `unsafe fn` body is no longer implicitly an unsafe block.

## Review Output Format

For each finding: `file:line`, severity (**MUST FIX** / **SUGGEST**), checklist item number,
and a concrete fix. Do not flag issues outside this checklist's scope (route
performance/unsafe/CLI/wasm findings to their respective skill or the research-agent fallback).

## Provenance

Derived from two independent `sdd:6-verify` research-fallback occurrences that converged on
the same idiom profile: 2026-06-22 (project `seneschal`, Rust+tokio+axum) and 2026-07-15
(project `stapler-mcp`, async/Tokio + ports-and-adapters + thiserror/anyhow). See
`~/.claude/logs/observations.md`.
