---
description: Checklist of techniques and tools for preventing flaky tests while keeping them fast and parallel. Use when a test failed intermittently, when writing or reviewing async/UI/IO tests, or before a release gate fails on a "passes locally" test.
---

# Prevent Test Flakes

Goal: tests that are deterministic **and** stay fast and parallel. Never "fix" a flake with retries, longer sleeps, `@Ignore`, or serial execution; those trade speed for hidden risk.

## 1. Triage a flake (root cause first)

1. Get the exact failure: stack trace, test name, which phase (body vs `@After`/`@Before`). Download the CI report/artifact if the log is truncated.
2. State a root-cause hypothesis ("fails because X"), then confirm it: reproduce under stress (loop the class N times, `--rerun-tasks`, run with other classes, fewer CPUs) or read the library source for the exact exception text.
3. If it cannot be reproduced, say so; label the fix INFERRED, and harden the whole class of cause (section 2), not just the one test.
4. A single re-run is a retry, not a fix. Report it as such.

## 2. Hardening checklist

**Time**
- No `Thread.sleep`/`delay` to wait for something. Wait on a completion signal: `StateFlow.first { predicate }`, `CompletableDeferred`, `CountDownLatch`, `awaitIdle()`/`waitForIdle()`.
- Coroutines: `runTest` + virtual time and an injected `TestDispatcher`/scope; never real clocks for logic under test. If real time is unavoidable (timeouts of an external system), use a generous timeout bound only as a hang guard, never as the assertion.
- Inject clocks, random seeds, and UUID generators.

**Concurrency and lifecycle (the most common cause of teardown flakes)**
- Everything a test starts must be stopped before teardown: cancel ViewModel/service scopes, close DB drivers, stop watchers, shut down executors. Track created objects in a list and release them in `@After`.
- Order teardown: stop producers/consumers -> drain the dispatcher (`runBlocking(thread) {}`) -> reset global state (`Dispatchers.resetMain()`) -> close threads.
- `Dispatchers.setMain`/`resetMain` throws "Dispatchers.Main is used concurrently with setting it" if any coroutine still reads Main. Never reset Main with live coroutines.
- Prefer injecting scopes/dispatchers over touching process-global ones (`Dispatchers.Main`, `Locale.setDefault`, system properties, `user.home`).

**Isolation (what lets tests run in parallel)**
- Unique temp dirs/ports/DB names per test (`TemporaryFolder`, UUID suffixes, port 0). No shared fixed paths like `/tmp/x`.
- No static/singleton mutable state shared across tests; reset or avoid it.
- No ordering dependence: each test builds its own fixtures. Run the class in random/reverse order to prove it.
- Fakes over real network/clock/filesystem: use in-memory repos and stub file systems. Tests gated on the network (`assumeTrue(isOnline)`) silently never run in CI; make them offline-capable or stub the dependency.

**Assertions**
- Assert on outcomes the system signals, not intermediate timing. Order-insensitive comparison for sets/maps/concurrent results.
- No dependence on wall-clock formatting, locale, timezone, hash/iteration order, or filesystem listing order.

**UI/Robolectric/Compose**
- Use the framework's idling mechanisms (`composeRule.waitForIdle()`, `awaitIdle`) rather than sleeps; route Main to a test-owned thread and block on state, not the clock.
- Prefer headless Robolectric (`androidUnitTest`) over real-display tests.

## 3. Tools

- Stress locally: `for i in 1..N; ./gradlew <task> --tests <Class> --rerun-tasks` (Gradle) or `bazel test --runs_per_test=20 --test_output=errors`.
- Constrain CPUs (`taskset -c 0`) or run under load to widen race windows.
- Kotlin: `kotlinx-coroutines-test` (`runTest`, `StandardTestDispatcher`, `advanceUntilIdle`), `Turbine` for Flow assertions, `kotest-property` for input-space coverage.
- JVM: `-Djava.util.concurrent.ForkJoinPool.common.parallelism=1` to expose hidden thread assumptions; Robolectric `LooperMode.PAUSED`.
- CI: keep failing-test reports as artifacts so a flake is diagnosable from one run; track repeat offenders by test name.
- Parallelism: keep `maxParallelForks`/Bazel sharding on; fix shared state rather than serializing. Serialize only per-build-dir Gradle invocations.

## 4. Verify the fix

- Loop the affected class (>= 10x, plus once with the whole module) and show the pass counts.
- Confirm the fix targets the cause: the teardown/lifecycle/time/isolation item it maps to above.
- Record the cause in the commit body in one or two sentences; no investigation narrative.

## Reference fix (SteleKit)

`CaptureShareReviewTest` failed in the release safety gate with `IllegalStateException` from `@After` (`resetMain`), cause `TestMainDispatcher`. ViewModel coroutines still read `Dispatchers.Main` while teardown reset it. Fix: track ViewModels, cancel their `viewModelScope`, drain the Main thread, then `resetMain()`.
