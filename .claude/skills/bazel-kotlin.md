# Bazel + Kotlin JVM Configuration (Bazel 9.x / Bzlmod)

## When to use this skill

Use this when configuring, debugging, or extending a Bazel build for a Kotlin JVM project:
- Setting up `MODULE.bazel` from scratch
- Adding or updating `rules_kotlin`, `rules_jvm_external`, or Gazelle
- Registering Kotlin toolchains
- Managing the Maven lockfile (`maven_install.json`)
- Generating BUILD files with Gazelle

---

## Canonical versions (April 2026)

| Component | Version | Notes |
|---|---|---|
| Bazel | **9.1.0** | Current LTS. Pin in `.bazelversion`. |
| rules_kotlin | **2.3.20** | Bundles Kotlin 2.3.20. Requires Bazel 9. |
| rules_jvm_external | **7.0** | Requires Bazel 7.7.1+/8.6.0+/9.x, Java 11+. |
| gazelle | **0.50.0** | Core Gazelle (Go + proto native). |
| contrib_rules_jvm | **0.32.0** | Gazelle extension for Java/Kotlin BUILD generation. |
| Bazelisk | **1.28.1** | Reads `.bazelversion`; use instead of installing Bazel directly. |

---

## Breaking changes to watch for

**Bazel 9 (current)**
- WORKSPACE is **completely removed** — no `--enable_workspace` flag exists. Pure Bzlmod only.
- `java_library`, `java_binary` must be loaded from `@rules_java` explicitly (no longer built-in).
- `native.register_toolchains()` is not callable from inside module extensions — use `register_toolchains()` in MODULE.bazel.

**rules_kotlin 2.2+**
- Dropped support for Kotlin < 2.2 and Java 8.
- Dropped `kotlin-preloader`.

**rules_jvm_external 7.0**
- Lock file format changed — must repin after upgrading: `REPIN=1 bazel run @maven//:pin`.
- WORKSPACE-based setup removed entirely.

---

## Correct MODULE.bazel pattern

```starlark
module(
    name = "my_project",
    version = "0.1.0",
)

bazel_dep(name = "rules_kotlin",       version = "2.3.20")
bazel_dep(name = "rules_jvm_external", version = "7.0")
bazel_dep(name = "gazelle",            version = "0.50.0")      # optional
bazel_dep(name = "contrib_rules_jvm",  version = "0.32.0")      # optional, Gazelle JVM extension

# Expose Kotlin compiler repos into this module's repo mapping (required for Bzlmod)
rules_kotlin_extensions = use_extension(
    "@rules_kotlin//src/main/starlark/core/repositories:bzlmod_setup.bzl",
    "rules_kotlin_extensions",
)
use_repo(
    rules_kotlin_extensions,
    "com_github_jetbrains_kotlin",
    "com_github_google_ksp",
    "com_github_pinterest_ktlint",
)

# To pin a specific Kotlin compiler version (optional — omit to use bundled 2.3.20):
# rules_kotlin_extensions.kotlinc_version(
#     version = "2.1.21",
#     sha256 = "<sha256 of kotlin-compiler-2.1.21.zip>",
# )

# Maven dependency management
maven = use_extension("@rules_jvm_external//:extensions.bzl", "maven")
maven.install(
    artifacts = [
        "group:artifact:version",
        # ...
    ],
    lock_file = "//:maven_install.json",   # commit this file
    repositories = ["https://repo1.maven.org/maven2"],
)
use_repo(maven, "maven")

# Register the toolchain defined in BUILD.bazel
register_toolchains("//:kotlin_toolchain")
```

---

## Correct BUILD.bazel toolchain definition

```starlark
load("@rules_kotlin//kotlin:core.bzl", "define_kt_toolchain")
load("@rules_kotlin//kotlin:jvm.bzl", "kt_jvm_binary", "kt_jvm_library", "kt_jvm_test")

# Language/JVM target settings — separate from the compiler version
define_kt_toolchain(
    name = "kotlin_toolchain",
    api_version      = "2.3",   # "1.9" | "2.0" | "2.1" | "2.2" | "2.3"
    language_version = "2.3",
    jvm_target       = "21",    # "1.8" through "25"
)
```

**Split library from binary** so tests can depend on app code without the main class:

```starlark
kt_jvm_library(
    name = "my_lib",
    srcs = glob(["src/main/kotlin/**/*.kt"]),
    resources = glob(["src/main/resources/**"]),
    deps = ["@maven//:..."],
)

# `bazel build //:my_app_deploy.jar` produces the fat JAR
kt_jvm_binary(
    name = "my_app",
    main_class = "com.example.ApplicationKt",
    runtime_deps = [":my_lib"],
)

kt_jvm_test(
    name = "all_tests",
    srcs = glob(["src/test/kotlin/**/*.kt"]),
    deps = [":my_lib", "@maven//:..."],
)
```

---

## Gazelle BUILD file generation

Add to `MODULE.bazel`:
```starlark
bazel_dep(name = "gazelle",           version = "0.50.0")
bazel_dep(name = "contrib_rules_jvm", version = "0.32.0")
```

Add to root `BUILD.bazel`:
```starlark
load("@bazel_gazelle//:def.bzl", "DEFAULT_LANGUAGES", "gazelle", "gazelle_binary")

# gazelle:prefix com.example.myapp
# gazelle:java_maven_install_file maven_install.json
# gazelle:java_maven_repository_name maven
# gazelle:jvm_kotlin_enabled true
# gazelle:java_module_granularity package

gazelle(name = "gazelle", gazelle = ":gazelle_bin")

gazelle_binary(
    name = "gazelle_bin",
    languages = DEFAULT_LANGUAGES + ["@contrib_rules_jvm//java/gazelle"],
)
```

Run: `bazel run //:gazelle`

**Known Gazelle/Kotlin limitations:**
- No `kt_jvm_test` generation — test files get `kt_jvm_library` inside a `java_test_suite`.
- `rules_kotlin` must be in the module graph when `jvm_kotlin_enabled = true`.

---

## Maven lockfile workflow

```bash
# First time — generate maven_install.json
bazel run @maven//:pin

# After adding/changing artifacts in MODULE.bazel
REPIN=1 bazel run @maven//:pin

# Verify exact label names for deps (useful when BUILD labels don't match)
bazel query @maven//:all
```

Commit `maven_install.json`. Never `.gitignore` it.

---

## Label naming for @maven deps

`group.id:artifact-name` → dots and dashes become underscores, all lowercase:

| Maven coordinate | Bazel label |
|---|---|
| `io.ktor:ktor-server-cio-jvm` | `@maven//:io_ktor_ktor_server_cio_jvm` |
| `com.zaxxer:HikariCP` | `@maven//:com_zaxxer_hikaricp` |
| `io.insert-koin:koin-ktor` | `@maven//:io_insert_koin_koin_ktor` |
| `org.postgresql:postgresql` | `@maven//:org_postgresql_postgresql` |

When in doubt: `bazel query @maven//:all | sort`

---

## Common wrong patterns

| Wrong | Correct |
|---|---|
| `kotlin_toolchain.configure(version = "...")` | Use `define_kt_toolchain` in BUILD.bazel |
| `WORKSPACE` file | Deleted in Bazel 9; use MODULE.bazel only |
| `native.register_toolchains()` in an extension | `register_toolchains()` in MODULE.bazel |
| No `use_repo(rules_kotlin_extensions, ...)` | Required even if not overriding Kotlin version |
| Missing `lock_file` in `maven.install` | Add `lock_file = "//:maven_install.json"` and run `bazel run @maven//:pin` |

---

## .bazelversion

```
9.1.0
```

Bazelisk reads this file and downloads the correct Bazel binary automatically.

---

## .bazelrc

```
build --java_language_version=21
build --tool_java_language_version=21
build --java_runtime_version=remotejdk_21
build --keep_going=false

test --test_output=errors
test --test_verbose_timeout_warnings

build:ci --noshow_progress
build:ci --verbose_failures
test:ci --test_output=all
```

---

## CI (GitHub Actions)

```yaml
- uses: bazelbuild/setup-bazelisk@v3

- uses: actions/cache@v4
  with:
    path: ~/.cache/bazel
    key: ${{ runner.os }}-bazel-${{ hashFiles('MODULE.bazel', 'BUILD.bazel') }}

- run: bazel build --config=ci //:my_app_deploy.jar
- run: bazel test --config=ci //...
```
