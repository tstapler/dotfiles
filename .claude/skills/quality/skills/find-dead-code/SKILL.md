---
description: Detect dead/unused code (imports, private members, and whole-project-unreachable declarations) with language-specific tooling and a false-positive checklist before deleting anything
---

# Find Dead Code

I'll help you find genuinely unused code in $1 (or the current directory if not specified). No single tool catches everything — lexical/AST tools (fast, per-file) miss cross-file reachability, and whole-program tools (slow, need setup) can false-positive on reflection, DI, and serialization. I layer three tiers regardless of language, then apply a false-positive checklist before anything gets deleted.

## The three tiers (language-agnostic)

1. **Lexical/AST, per-file** — fast, safe, catches unused imports and unused private/unexported members. Zero setup, near-zero false positives (an unused import is unused, full stop). Run this first, always.
2. **Whole-program reachability** — traces from real entry points (`main`, exported package API, app entry) across the whole build graph. Catches unused *exported* declarations that per-file tools can't see, but needs the project to actually build/compile first.
3. **Runtime verification** — instruments a real running instance and records what's actually invoked. The only tier immune to reflection/DI/dynamic-dispatch false positives, but requires representative real usage over time — use it to confirm a static finding, not as a first pass.

Pick tools per language below; run tier 1 on everything, tier 2 where the project builds cleanly, tier 3 only when a finding is contested or high-stakes.

## Scaling to a large scan: delegate the mechanical pass to Haiku

Running a tool and checking each raw finding against the false-positive checklist above (does this symbol match a reflection/DI/serialization/test-only pattern?) is mechanical, not judgment — a good fit for cheap agents once the finding count or directory count gets large (more than a handful of packages/modules, or more raw findings than fit in one context comfortably).

Fan out per package/directory in one message, following this repo's existing pattern (`code:is-it-ready`):

```
Agent(subagent_type: "general-purpose", model: "haiku",
  prompt: "Run <tier-1 command> in <dir>. For each raw finding, check it against
           this false-positive list: [paste the checklist]. Return only file:line,
           symbol, tool, and verdict (likely-dead / needs-review) — no prose.")
```

Launch all package/directory agents in a single message so they run in parallel. Keep the orchestrating model (you) for what Haiku shouldn't decide alone: reconciling duplicate findings across slices, making the final delete/keep call on anything flagged "needs-review," and any tier-3 runtime-verification judgment call. Skip the fan-out entirely for a small scan (one package, a few files) — spawning agents for a five-file grep is pure overhead.

## Go

```bash
staticcheck ./...              # tier 1: unused funcs/vars/consts per-package (U1000)
go vet ./...
deadcode ./...                 # tier 2: golang.org/x/tools/cmd/deadcode — whole-program reachability from main
```

`deadcode` needs `go build` to succeed first and only traces from actual `main` packages — a library module with no `main` gets no meaningful graph from it; rely on `staticcheck`'s per-package `U1000` there instead. Both miss anything reached only via reflection or an `interface{}` type-switch dispatch table.

## TypeScript / JavaScript

```bash
npx knip                       # tiers 1+2 in one pass: unused exports, files, and dependencies
npx ts-prune                   # narrower alternative: unused exports only
```

`knip` is the more actively maintained, broader tool — prefer it. Both need a working `tsconfig.json`/entry-point config to trace exports correctly; an unconfigured monorepo package will produce noisy false positives until its entry points are declared.

## Python

```bash
vulture .                      # tier 1: AST-based, flags unused functions/classes/imports/vars with a confidence score
```

Lower the confidence threshold cautiously — `vulture`'s low-confidence findings are dominated by dynamically-dispatched code (Django views, pytest fixtures, `__init__.py` re-exports).

## Rust

```bash
cargo build                    # tier 1: rustc's own dead_code lint is on by default, no extra tool needed
cargo udeps                    # unused *dependencies*, not code — a different but related check
```

## Shell / Ansible

No dedicated dead-*code* tool — `shellcheck` (already run via `make ready` in dotfiles) flags unused variables (`SC2034`) as a byproduct, but nothing here traces cross-file reachability of a whole function/role. Treat unused-role or unused-script detection as a manual grep-for-callers pass, not an automated tier.

## Kotlin / Java

### 1. Lexical analysis — Detekt

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
```

Two things to check before trusting a clean run:
- **Kotlin Multiplatform `expect`/`actual`**: older Detekt versions have false-positived on `expect` declaration parameters (implemented in `actual`, not the `expect` body) — confirm your version isn't affected.
- **If these rules exist but are `active: false`** with no documented reason, that's itself a finding worth flagging.

This will NOT find unused `public`/`internal` declarations — Detekt reasons per-file, not across the compiled module.

### 2. Whole-program reachability — IntelliJ IDEA headless inspection

```bash
idea inspect /path/to/project /path/to/inspection-profile.xml /path/to/output --format json
```

Build a profile with only "Unused declaration" enabled, scope "Whole Project" — the full default profile is slow and noisy. Requires full project indexing first; run as an occasional deep audit, not on every CI run. (Skip UCDetector — it's Eclipse-only and superseded by this for IntelliJ/Android Studio projects.)

### 3. Runtime reachability — Scavenger / Codekvast

Attaches a Java agent that records which methods are actually invoked in a real running instance (staging/production) over a representative window. The only tier that sees through reflection, DI containers, and `ServiceLoader` bindings. [Scavenger](https://github.com/naver/scavenger) is the actively-maintained successor to [Codekvast](https://github.com/crispab/codekvast); prefer it. Use to confirm a static finding, not as a first pass.

### 4. Android-specific: R8/ProGuard usage reports

```bash
./gradlew :androidApp:assembleRelease
cat androidApp/build/outputs/mapping/release/usage.txt   # what R8 determined unreachable and stripped
cat androidApp/build/outputs/mapping/release/seeds.txt    # entry points R8 kept as roots
```

Free, real reachability graph rooted at actual entry points — but reflects only the Android target's graph. A KMP `commonMain` function unused on Android but called from `jvmMain`/`iosMain`/`jsMain` will show as "removed" here; cross-check other targets.

### 5. Unused Gradle dependencies

```bash
./gradlew buildHealth   # com.autonomousapps.dependency-analysis
```

Not unused *code*, but usually asked alongside it — finds declared-but-unimported dependencies and used-but-undeclared transitive ones.

## C#

Roslyn analyzers (`IDE0051`/`IDE0052`, built into the SDK) for unused private members/fields; ReSharper's "Unused symbol" inspection for whole-solution analysis.

## False-positive checklist — verify each finding before deleting

Automated tools, in every language above, cannot see:
- **Reflection / dependency injection** (`Class.forName`, Dagger/Hilt/Koin, `ServiceLoader`, Python's dynamic `getattr`/plugin registries, Go `interface{}` dispatch) — a symbol instantiated only by name or DI graph looks unreferenced to static analysis.
- **Serialization** — a struct/data-class field never read in application code but required for JSON/DB schema round-tripping.
- **KMP `expect`/`actual`** — an `expect` declaration's only "caller" is the compiler matching it to `actual` per target; don't delete one side without checking all target source sets.
- **Framework entry points** — Compose `@Preview`, pytest fixtures, Django views/urls, CLI `cobra.Command` registrations — invoked by a framework, not by a visible call site.
- **Public library API** — "unused within this repo" ≠ "unused" for external consumers if this module is published. Check for an API/binary-compatibility surface before removing.
- **Test-only helpers** — a production function only called from test code is still "used," just not from `main`.
- **CGo / JNI / native entry points** — functions called from native code via a fixed signature, invisible to any static analysis in the managed language.

When in doubt, grep for the exact identifier across the whole repo (not just the module) before deleting — a whole-program tool's "unused" verdict is a strong signal, not a guarantee.

## Running this regularly

For a one-off audit, run the tiers above directly. To make this a recurring, low-effort check across repos (the actual long-term goal) rather than something invoked ad hoc, this is tracked as an untested check idea in kibitzer's `docs/check-ideas.md` (`~/code/github.com/tstapler/kibitzer`) — kibitzer already wraps per-language static tools behind one MCP interface (`list_checks`/`run_checks`), so a `dead-code` check there would let this run on the same cadence as its other checks instead of being re-invoked by hand per repo.

Let me analyze your codebase using the layers above and report concrete, verified findings — flagging anything ambiguous for your review rather than assuming it's safe to delete.
