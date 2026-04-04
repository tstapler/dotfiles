---
name: bazel-version-upgrades
description: Guidance for migrating Bazel projects to newer versions, specifically
  Bazel 9+. Use when encountering 'name not defined' errors for core rules like sh_binary,
  cc_binary, or when migrating from WORKSPACE to Bzlmod.
---

# Bazel Version Upgrades (Focus: Bazel 9)

Bazel 9 introduces significant changes, primarily the complete removal of `WORKSPACE` support and the "Starlarkification" of core rules.

## Key Migration Patterns for Bazel 9

### 1. Core Rules are no longer Built-in
Rules like `sh_binary`, `cc_binary`, `java_binary`, etc., are no longer globally available. They must be loaded from external repositories.

**Symptoms:**
- `name 'sh_binary' is not defined`
- `name 'cc_library' is not defined`

**Fix:**
1. Add the corresponding `bazel_dep` to `MODULE.bazel`.
2. Add a `load()` statement to the top of the `BUILD` file.

| Rule Type | Repository | Load Statement |
|-----------|------------|----------------|
| `sh_*` | `rules_shell` | `load("@rules_shell//shell:sh_binary.bzl", "sh_binary")` |
| `cc_*` | `rules_cc` | `load("@rules_cc//cc:defs.bzl", "cc_binary", "cc_library")` |
| `java_*` | `rules_java" | `load("@rules_java//java:defs.bzl", "java_binary", "java_library")` |
| `py_*` | `rules_python` | `load("@rules_python//python:py_binary.bzl", "py_binary")` |
| `proto_*` | `rules_proto` | `load("@rules_proto//proto:defs.bzl", "proto_library")` |

### 2. MODULE.bazel is Mandatory
Bazel 9 does not support `WORKSPACE`. All dependencies must be in `MODULE.bazel`.

**Pattern:**
```python
bazel_dep(name = "rules_shell", version = "0.6.1")
bazel_dep(name = "rules_cc", version = "0.0.17")
```

### 3. Repository Mapping
If a tool like `gazelle` or `rules_rust` expects a repository to be visible, ensure it is added to `MODULE.bazel`. Bazel 9 is stricter about "strict dependency tracking" for modules.

## Troubleshooting
- **Version Mismatches**: If you see a warning about a version mismatch (e.g., requested 0.4.0 but got 0.6.1), update your `MODULE.bazel` to match the resolved version to avoid non-deterministic builds.
- **Missing Rules**: If `sh_binary` is still missing after loading, check if it's being shadowed by a local macro or another `load` statement.