---
description: Detect dead/unused code (imports, private members, and whole-project-unreachable declarations) with language-specific tooling and a false-positive checklist before deleting anything
---

# Find Dead Code

I'll help you find genuinely unused code in $1 (or the current directory if not specified). No single tool catches everything — lexical/AST tools (fast, per-file) miss cross-file reachability, and whole-program tools (slow, need setup) can false-positive on reflection, DI, and serialization. I'll layer both and flag anything that needs manual verification before deletion.

## Kotlin / Java

### 1. Lexical analysis — Detekt (fast, per-file, safe first pass)

If the project already runs Detekt, its built-in rules catch unused imports and unused private members without any new tooling:

```yaml
# detekt.yml
style:
  UnusedImports:
    active: true
  UnusedPrivateMember:
    active: true
  UnusedPrivateProperty:
    active: true
  UnusedParameter:
    active: true
```

```bash
./gradlew :module:detekt --no-daemon
# or, if migrated to Bazel (see ADR for rules_detekt-based projects):
bazel test //module:detekt
```

These are structurally low-risk: `UnusedImports` is nearly zero-false-positive (an unused import is unused, full stop). `UnusedPrivateMember`/`UnusedPrivateProperty` only flag `private` declarations, so there's no cross-file ambiguity — but check for two things before trusting a clean run:
- **Kotlin Multiplatform `expect`/`actual`**: older Detekt versions have had false positives flagging `expect` declaration parameters as unused (they're implemented in `actual`, not the `expect` body). Confirm your Detekt version isn't affected, or scope `ignoreAnnotated`/allowlist accordingly.
- **If these rules are already in the config but `active: false`**: check git history/comments for *why* — if there's no documented reason, that's itself a signal worth flagging, not assuming it's intentional.

This layer will NOT find unused `public` or `internal` top-level functions/classes — Detekt reasons per-file, not across the whole compiled module, so anything not `private` looks "used" to it even if nothing calls it anywhere.

### 2. Whole-program reachability — IntelliJ IDEA headless inspection (the actual gold standard for Kotlin)

For unused `public`/`internal` declarations — the bigger, harder class of dead code — IntelliJ's "Unused declaration" inspection is the most trustworthy tool because it uses full symbol resolution across the whole multi-module/multiplatform project (Detekt and other AST-only linters cannot do this correctly for Kotlin, especially with `expect`/`actual`).

```bash
# Headless CLI (IntelliJ IDEA 2024.1+; requires a full IDE install, not just the CLI):
idea inspect /path/to/project /path/to/inspection-profile.xml /path/to/output --format json

# Or via Android Studio for Android-heavy Kotlin projects:
studio inspect /path/to/project /path/to/inspection-profile.xml /path/to/output
```

Build the inspection profile with only "Unused declaration" (and optionally "Unused symbol") enabled, scope "Whole Project" — enabling the full default profile makes the run slow and floods output with unrelated style findings. This requires the project to fully index first (can take a while on a large codebase) — run it as an occasional deep audit, not on every CI run; it's too slow/heavy for that.

Note: **UCDetector** (a well-known "unused code" Java tool) is Eclipse-only — skip it entirely on an IntelliJ/Android Studio project; the built-in inspection above supersedes it and understands Kotlin, which UCDetector doesn't.

### 3. Runtime reachability — Scavenger / Codekvast (eliminates reflection/DI false positives entirely)

Static analysis (layers 1-2) can't see through reflection, DI containers, or `ServiceLoader` — a method invoked only via `Class.forName` or a Dagger/Hilt binding looks "unused" to any static tool. Runtime instrumentation sidesteps this by attaching a Java agent that records which methods actually get invoked during real usage (staging or production), over a representative time window — anything with zero invocations after that window is *truly* dead, regardless of how it's theoretically reachable.

- **[Scavenger](https://github.com/naver/scavenger)** (Naver) — the actively-maintained successor to Codekvast; supports any JVM-based language, no code changes required, clearer UI for reviewing results.
- **[Codekvast](https://github.com/crispab/codekvast)** — the original; still usable but less actively developed than Scavenger.

This is the most accurate signal available (it measures actual behavior, not inferred reachability) but requires running the instrumented build somewhere real for long enough to cover representative usage — most useful for confirming a static-analysis finding (from layer 1 or 2) is safe to delete, not as a first-pass scan on its own.

### 4. Reachability from real entry points — R8/ProGuard usage reports (Android)

If the project already ships an Android release build via R8 (most do), the shrinker's own usage report is a free, real reachability graph rooted at actual entry points (`Activity`, `Application`, manifest components, etc.) — closer to ground truth than any static heuristic:

```bash
./gradlew :androidApp:assembleRelease
cat androidApp/build/outputs/mapping/release/usage.txt   # classes/methods R8 determined unreachable and stripped
cat androidApp/build/outputs/mapping/release/seeds.txt    # entry points R8 kept as roots
```

Caveat: this only reflects the Android target's reachability graph. A KMP `commonMain` function unused on Android but still called from `jvmMain`/`iosMain`/`jsMain` will show as "removed" here — cross-check against other targets before trusting a `usage.txt` entry as truly dead.

### 5. Unused Gradle dependencies (a different but related problem)

Not the same as unused *code*, but usually asked alongside it: [`com.autonomousapps.dependency-analysis`](https://github.com/autonomousapps/dependency-analysis-android-gradle-plugin) finds declared dependencies nothing actually imports, and the inverse (used-but-undeclared transitive dependencies).

```bash
./gradlew buildHealth
```

## False-positive checklist — verify each finding before deleting

Automated tools cannot see:
- **Reflection / dependency injection** (`Class.forName`, Dagger/Hilt/Koin bindings, ServiceLoader `META-INF/services` entries) — a class instantiated only by name or DI graph looks unreferenced to static analysis.
- **Serialization** — a `@Serializable` data class property that's never read in Kotlin code but is required for JSON/DB schema round-tripping.
- **KMP `expect`/`actual`** — an `expect` declaration's only "caller" is the compiler matching it to `actual` implementations per target; don't delete one side without checking all target source sets.
- **Compose `@Preview` functions** — intentionally never called by app code; used only by tooling.
- **Public library API** — if this module is published/consumed externally, "unused within this repo" ≠ "unused" for external consumers. Check for an `api`/binary-compatibility-validator surface before removing.
- **Test-only helpers** — a production-code function only called from test source sets is still "used," just not from `main`.
- **JNI / native entry points** — functions called from native code via a fixed signature, invisible to any JVM-side static analysis.

When in doubt, grep for the exact identifier across the whole repo (not just the module) before deleting — a whole-program tool's "unused" verdict is a strong signal, not a guarantee.

## Additional Languages

- **JavaScript/TypeScript**: `ts-prune` (unused exports) or `knip` (the more actively maintained, broader successor — covers unused exports, files, and dependencies in one pass) — `npx knip`.
- **Go**: `deadcode` (`golang.org/x/tools/cmd/deadcode`) for whole-program reachability from `main`; `unused` (part of `staticcheck`) for a faster per-package pass.
- **Python**: `vulture` — AST-based, flags unused functions/classes/imports/variables with a confidence score.
- **Rust**: the compiler's own `dead_code` lint (`#[warn(dead_code)]`, on by default) is usually sufficient; `cargo udeps` for unused dependencies specifically.
- **C#**: Roslyn analyzers (`IDE0051`/`IDE0052` unused private member/field) built into the SDK; ReSharper's "Unused symbol" for whole-solution analysis.

Let me analyze your codebase using the layers above and report concrete, verified findings — flagging anything ambiguous for your review rather than assuming it's safe to delete.
