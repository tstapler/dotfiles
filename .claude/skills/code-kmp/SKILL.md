---
name: code-kmp
description: Idiomatic review for Kotlin Multiplatform (KMP) with Kotlin 2.x — expect/actual discipline, Swift boundary safety, ViewModel lifecycle, SQLDelight conventions
user-invocable: false
---

# KMP / Kotlin 2.2 Idiomatic Review

Apply this checklist when reviewing any diff containing `.kt` files in a KMP project (files in `commonMain`, `androidMain`, `iosMain`, `sharedLogic`, or `sharedUI` source sets).

## MUST FIX (block shipping if violated)

1. **[ERROR]** Do not throw raw exceptions from `suspend fun` exposed to iOS. Wrap in a `sealed class` result type before crossing the Kotlin → Swift boundary; Kotlin exceptions thrown from coroutines surface as untyped crashes in Swift.

2. **[ERROR]** Do not collect `StateFlow` directly in Swift via `collect {}`. Use `KMP-NativeCoroutines`, `SKIE`, or an explicit `iosMain` bridge with `DisposableHandle.dispose()` called from Swift `deinit`.

3. **[ANTI-PATTERN]** iOS ViewModel scope must be cancelled on dismiss. Every ViewModel must expose `fun clear()` that cancels its `SupervisorJob`. Swift callers must call `viewModel.clear()` from `deinit`. Without this, coroutines leak silently on iOS.

4. **[ANTI-PATTERN]** Do not use `expect class` for types that need fakes (repositories, helpers, services). Use `interface` in `commonMain` with `class Foo : Interface` in each platform source set. `expect class` blocks unit-testing with fakes.

5. **[ANTI-PATTERN]** `SqlDriver` must not be constructed directly in `commonMain`. Wrap all driver creation behind `interface DatabaseDriverFactory { fun createDriver(): SqlDriver }` with platform `actual` implementations.

6. **[NAMING]** Kotlin 2.2: `kotlinOptions {}` DSL is deprecated-to-error. Migrate all compiler flag configuration to `compilerOptions {}` inside `kotlin {}`. This breaks builds on Kotlin 2.2+.

7. **[STYLE]** Domain model `data class` instances in `commonMain` must not use `java.time.*`, `java.util.Date`, or any platform `Uri`. Use `kotlinx-datetime` (`Instant`, `LocalDate`) for all timestamp fields.

## SUGGEST (note and fix if <30 min; else track as follow-up)

8. **[ANTI-PATTERN]** Business logic must not leak into `actual` declarations. `actual` blocks are pure platform wiring (driver init, file paths, clock access). Logic that enters an `actual` block cannot be tested in `commonTest`.

9. **[NAMING]** `expect/actual` files: use identical file names across source sets (e.g., `TimeProvider.kt` in `commonMain`, `TimeProvider.android.kt` in `androidMain`). The compiler allows mismatched names but maintainers can't find `actual` implementations without searching.

10. **[STYLE]** ViewModels expose a single `StateFlow<UiState>` and a single `dispatch(action: Action)`. Use `SharedFlow<Event>(replay=0)` for one-shot navigation/snackbar events. Never expose `MutableStateFlow` or `MutableSharedFlow` from a ViewModel's public API.

11. **[PERF]** Use `SharingStarted.WhileSubscribed(5_000)` on `stateIn` calls, not `Eagerly`. This stops upstream producers after the last subscriber leaves, prevents wasted work on iOS when views are not collecting.

12. **[STYLE]** Every query in a SQLDelight `.sq` file must have a meaningful label (e.g., `selectUserById:`). Labels generate typed Kotlin functions. Unlabelled queries require raw `execute()` calls that lose compile-time safety.

13. **[STYLE]** Koin DSL (`module { single { } / factory { } }`) is preferred over a hand-rolled `AppContainer` when the DI graph exceeds ~7 nodes. Koin does not use reflection and is safe on Kotlin/Native.

14. **[STYLE]** Do not use the deprecated `context(Foo)` context receivers syntax (Kotlin 1.x experiment). It is being removed (KT-72994). Use explicit parameters or wait for the stable `context parameters` feature in Kotlin 2.2+.

15. **[PERF]** All `data class` fields used as map keys must implement stable `hashCode`/`equals`. KMP value classes (`@JvmInline`) give zero-cost wrappers on JVM but add a boxing step on Kotlin/Native — profile before adding to hot paths.
