---
name: bazel-github-actions-ci
description: Use when setting up or reviewing Bazel CI on GitHub Actions. Covers
  setup-bazel caching strategy, per-job disk-cache isolation, Compose Desktop X11
  support, KMP test aggregation, and security hardening. Based on SteleKit migration.
---

# Bazel CI on GitHub Actions

Battle-tested patterns from migrating a Kotlin Multiplatform project to Bazel CI.
Replaces the outdated `bazelbuild/setup-bazelisk + actions/cache` approach.

---

## Core: use `bazel-contrib/setup-bazel` — not manual caching

`setup-bazel@0.19.0` replaces both `bazelbuild/setup-bazelisk` and manual
`actions/cache` for Bazel caches. It manages three orthogonal caches:

| Input | What it caches | Notes |
|---|---|---|
| `disk-cache: <name>` | Compiled build outputs (action result cache) | Isolate per job |
| `repository-cache: true` | Downloaded Maven/artifact files (CAS store) | Share across jobs |
| `external-cache: true` | Processed external repos (Compose Desktop, AndroidX) | Share across jobs |
| `cache-save: <bool>` | Whether to write the cache back | PRs read, pushes write |

```yaml
- name: Set up Bazel
  uses: bazel-contrib/setup-bazel@0.19.0
  with:
    bazelisk-version: "1.x"
    disk-cache: jvm              # unique per job — prevents cross-job collisions
    repository-cache: true       # shared across all jobs (keyed by MODULE.bazel)
    external-cache: true         # Compose Desktop etc. are large; cache separately
    cache-save: ${{ github.event_name != 'pull_request' }}
```

**Why `cache-save: ${{ github.event_name != 'pull_request' }}`**: PRs read the cache
seeded by the main branch but never write back. This prevents a poisoned PR from
corrupting the shared cache. Pushes to main write a fresh cache for the next PR.

**Why per-job `disk-cache`**: JVM and Android compiled outputs are incompatible.
Sharing a disk cache between jobs that build different targets causes cache misses and
occasional corruption. Use distinct names: `jvm`, `android`, `android-tests`, `web`.

**`repository-cache` and `external-cache` are complementary, not redundant**:
- `repository-cache` = `~/.cache/bazel/cache/repos` — raw downloaded files (content-addressed)
- `external-cache` = processed external repo directories (e.g. `external/rules_jvm_external~maven/`)
Both are useful; enabling both is correct.

---

## Security baseline

Always add `permissions: contents: read` at the workflow level. Without it, the default
`GITHUB_TOKEN` has write access to contents, packages, and deployments — far more than
a test workflow needs.

```yaml
name: Bazel CI

on:
  push:
    branches: [main]
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]

permissions:
  contents: read     # minimum required to checkout code

concurrency:
  group: bazel-ci-${{ github.ref }}
  cancel-in-progress: true
```

---

## Skipping draft PRs

```yaml
jobs:
  bazel-jvm:
    if: github.event.pull_request.draft == false
```

**This is safe for both `push` and `pull_request` events.** On `push` events,
`github.event.pull_request` is `null`, so `github.event.pull_request.draft` is `null`.
GitHub Actions coerces `null` to `0` and `false` to `0` for `==`, so `null == false`
evaluates to `true` — the job runs. No special handling needed for push vs PR.

---

## JDK: JVM jobs don't need `setup-java`

Bazel downloads its own JDK toolchain via `--java_runtime_version=21` (from
`rules_java`). JVM/desktop jobs do **not** need `actions/setup-java`.

Android jobs **do** need `setup-java` because the Android SDK host tools (aapt2,
d8, etc.) run outside Bazel's hermetic environment and require a system JDK on `PATH`.

```yaml
# JVM job — NO setup-java needed (Bazel downloads the JDK itself)
bazel-jvm:
  steps:
    - uses: actions/checkout@v4
    - uses: bazel-contrib/setup-bazel@0.19.0
      with: { disk-cache: jvm, ... }
    - run: bazel test //kmp:jvm_tests

# Android job — setup-java IS needed for host tools
bazel-android:
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-java@v4
      with: { java-version: "21", distribution: temurin }
    - uses: android-actions/setup-android@v3
    - uses: bazel-contrib/setup-bazel@0.19.0
      with: { disk-cache: android, ... }
    - run: bazel build //kmp:android_app --config=android
```

---

## Compose Desktop / X11 on Linux CI

Compose Desktop tests open real windows and require an X display. The Bazel sandbox
creates an isolated mount namespace that excludes `/tmp/.X11-unix` by default, so even
with `DISPLAY` set, the X socket is unreachable.

### .bazelrc

```
# Mount the X11 socket directory into every test sandbox (Linux only).
# Locally: uses whatever X server is running.
# CI: xvfb-run creates the socket before Bazel runs.
test --sandbox_add_mount_pair=/tmp/.X11-unix
```

### BUILD.bazel test target

```python
kt_jvm_test(
    name = "jvm_tests",
    ...
    jvm_flags = [
        "-Djava.awt.headless=false",          # Compose Desktop requires headless=false
        "--add-opens=java.base/java.lang=ALL-UNNAMED",
    ],
    env = {
        "LIBGL_ALWAYS_SOFTWARE": "1",         # software OpenGL — no GPU needed on CI
    },
    env_inherit = ["DISPLAY"],                # required with --incompatible_strict_action_env
    tags = ["requires-display"],
)
```

### CI workflow step

```yaml
- name: Install Xvfb
  run: |
    sudo apt-get install -y --no-install-recommends xvfb
    # Create the directory before Bazel validates the sandbox mount source.
    # xvfb-run creates the socket, but Bazel checks the directory at startup.
    mkdir -p /tmp/.X11-unix

- name: Run JVM tests
  run: |
    xvfb-run --auto-servernum bazel test //kmp:jvm_tests \
      --test_output=summary
```

**Why `mkdir -p /tmp/.X11-unix` before the test command**: Bazel validates
`--sandbox_add_mount_pair` mount sources at startup. If the directory doesn't exist,
Bazel refuses to start the test. `xvfb-run` creates the socket inside the directory
but the directory itself must pre-exist.

---

## Test aggregation: `test_suite` not `alias`

`alias()` does not forward the test provider — `bazel test //kmp:jvm_tests` will silently
build without running any tests if `jvm_tests` is an `alias`.

```python
# kmp/BUILD.bazel — CORRECT
test_suite(
    name = "jvm_tests",
    tests = ["//kmp/src/jvmTest/kotlin:jvm_tests"],
)

# WRONG — test provider is not forwarded
alias(
    name = "jvm_tests",
    actual = "//kmp/src/jvmTest/kotlin:jvm_tests",
)
```

---

## JUnit4 Suite aggregator (Bazel's `test_class` requirement)

Bazel's `kt_jvm_test` runner needs a real JUnit4 class as `test_class`. Kotlin test
with `@RunWith(Suite.class)` is the correct aggregator pattern.

```kotlin
@RunWith(Suite::class)
@Suite.SuiteClasses(
    FooTest::class,
    BarTest::class,
    // ... all test classes in the source set
)
class AllJvmTests
```

```python
kt_jvm_test(
    name = "jvm_tests",
    srcs = glob(["**/*.kt"]),
    test_class = "dev.stapler.stelekit.AllJvmTests",
    ...
)
```

Note: if screenshot tests use Roborazzi (no Bazel integration), exclude them:
```python
srcs = glob(
    ["**/*.kt"],
    exclude = ["**/*Screenshot*.kt", "**/screenshots/**"],
),
```

---

## `associates` vs `deps` for `internal` visibility

To access `internal` declarations from another module, use `associates`, not `deps`.
A target listed in `associates` **must not** also appear in `deps` — this is a rules_kotlin
constraint.

```python
kt_jvm_test(
    name = "business_tests",
    associates = ["//kmp/src/commonMain/kotlin:common_main_lib"],  # grants internal access
    deps = [
        # common_main_lib must NOT appear here too
        "@maven//:org_jetbrains_kotlin_kotlin_test_junit",
    ],
)
```

---

## JAR-safe test fixture extraction

Bazel packs `resources` into JARs. `File(url.toURI())` throws on `jar:` URIs.
Use `ClassLoader.getResource()` and extract to a temp dir with atomic rename:

```kotlin
fun getClasspathDirectory(loader: ClassLoader, resourceName: String): File {
    val url = loader.getResource(resourceName) ?: error("$resourceName not found")
    if (url.protocol == "file") return File(url.toURI())    // IDE / file:// path — no extraction needed
    val dest = File(
        System.getenv("TEST_TMPDIR") ?: System.getProperty("java.io.tmpdir"),
        resourceName.replace('/', '_'),
    )
    synchronized(extractionLock) {
        if (!dest.exists()) {
            val tmp = File(dest.parent, dest.name + ".tmp")
            tmp.deleteRecursively(); tmp.mkdirs()
            try {
                val conn = url.openConnection() as JarURLConnection
                conn.jarFile.use { jar ->
                    val prefix = conn.entryName + "/"
                    jar.entries().asSequence()
                        .filter { !it.isDirectory && it.name.startsWith(prefix) }
                        .forEach { entry ->
                            val target = File(tmp, entry.name.removePrefix(prefix))
                            target.parentFile?.mkdirs()
                            jar.getInputStream(entry).use { it.copyTo(target.outputStream()) }
                        }
                }
                tmp.renameTo(dest)              // atomic: dest appears fully-written or not at all
            } catch (e: Exception) {
                tmp.deleteRecursively(); throw e // clean up partial extractions
            }
        }
    }
    return dest
}
private val extractionLock = Any()
```

Use `TEST_TMPDIR` (Bazel's designated temp dir for tests) over `java.io.tmpdir` — Bazel
cleans it between runs. Do **not** use `user.home` — Bazel's sandbox blocks writes there.

---

## Sandbox restrictions: `user.home` writes fail

Inside the Bazel sandbox, the home directory (`$HOME`) is inaccessible for writes.
Replace `System.getProperty("user.home")` with `System.getProperty("java.io.tmpdir")`
or `System.getenv("TEST_TMPDIR")` in any test that creates temporary files.

---

## KMP: patching `rules_kotlin` for `common_srcs`

Kotlin Multiplatform requires `-Xcommon-sources` for expect/actual compilation.
`rules_kotlin` doesn't support this natively — patch it via `single_version_override`:

```starlark
# MODULE.bazel
single_version_override(
    module_name = "rules_kotlin",
    version = "2.3.20",
    patches = ["//third_party/patches:rules_kotlin_kmp.patch"],
    patch_strip = 1,
)
```

The patch adds a `common_srcs` attribute to `kt_jvm_library` and passes
`-Xcommon-sources=$(common_srcs)` to kotlinc. Maintain the patch in
`third_party/patches/rules_kotlin_kmp.patch`. When upgrading rules_kotlin,
re-apply and re-test.

---

## Gradle-delegating genrule (for WASM/JS)

When a Bazel target must delegate to Gradle (e.g., WASM until rules_kotlin#567 lands),
preserve Gradle's incremental cache with a separate `actions/cache` step keyed on
relevant Gradle files plus `${{ github.sha }}` (so each push seeds a fresh cache from
the previous run):

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.gradle
    key: gradle-web-${{ runner.os }}-${{ hashFiles('build.gradle.kts', 'gradle.properties') }}-${{ github.sha }}
    restore-keys: |
      gradle-web-${{ runner.os }}-${{ hashFiles('build.gradle.kts', 'gradle.properties') }}-
      gradle-web-${{ runner.os }}-
```

---

## Artifact uploads: gate on push

CI artifacts on PRs add noise and consume storage quota without benefit. Gate uploads
on `github.event_name == 'push'`:

```yaml
- name: Upload web bundle
  if: github.event_name == 'push'
  uses: actions/upload-artifact@v4
  with:
    name: web-dist
    path: bazel-bin/kmp/web_dist.tar.gz
    retention-days: 7
```

---

## Local disk cache for developers

Document in `.bazelrc.user.example` (not committed):

```
# Persists build results between sessions and workspace switches.
# build --disk_cache=~/.cache/bazel-disk-cache
```

Grows unboundedly — users must manually prune with `bazel clean --expunge` or `rm -rf`.

---

## Anti-patterns

| Wrong | Correct |
|---|---|
| `bazelbuild/setup-bazelisk` + `actions/cache` for Bazel | `bazel-contrib/setup-bazel@0.19.0` |
| Single shared `disk-cache` across all jobs | One `disk-cache` name per job |
| `alias()` for test aggregation | `test_suite()` |
| `target` in both `associates` and `deps` | `associates` only — no `deps` duplication |
| `File(url.toURI())` for classpath resources | Extract via `JarURLConnection` |
| `System.getProperty("user.home")` in tests | `TEST_TMPDIR` or `java.io.tmpdir` |
| `sudo apt-get install -y <pkg>` | `sudo apt-get install -y --no-install-recommends <pkg>` |
| Uploading artifacts on every event | Gate with `if: github.event_name == 'push'` |
| No `permissions:` block in workflow | `permissions: contents: read` at minimum |
