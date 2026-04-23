---
name: jfr-profiling
description: Profile Java/Kotlin processes using JFR (Java Flight Recorder). Covers Gradle task setup, CI integration, collapsed-stacks output for LLM analysis, flamegraph visualization, and bottleneck identification patterns.
---

# JFR Profiling for Java/Kotlin Projects

End-to-end workflow: Gradle task → JFR → collapsed stacks (primary analysis format) → flamegraph (visualization).

## Format Strategy

| Format | Size vs JFR | Best for | Command |
|--------|-------------|----------|---------|
| **Collapsed stacks** | ~1-2% | LLM analysis, CI diffs, awk parsing | `jfrconv -o collapsed` |
| HTML flamegraph | ~5-10% | Interactive human exploration | `jfrconv` (default) |
| Differential flamegraph | ~5-10% | A/B comparison | `jfrconv --diff` |
| Raw JFR | 100% | Archive, future re-analysis | — |

**Use collapsed stacks for LLM analysis.** Format: `frame1;frame2;leaf N` — one line per unique call stack, count at end. No decoder needed.

---

## Step 1 — Gradle Task Setup

```kotlin
// build.gradle.kts
tasks.register<Test>("jvmTestProfile") {
    description = "Run benchmark under JFR"
    group = "verification"
    testClassesDirs = sourceSets["jvmTest"].output.classesDirs
    classpath = sourceSets["jvmTest"].runtimeClasspath
    filter { includeTestsMatching("*.GraphLoadTimingTest") }

    val jfrFile = layout.buildDirectory.file("reports/graph-load.jfr").get().asFile
    jvmArgs(
        "-XX:+FlightRecorder",
        "-XX:StartFlightRecording=filename=${jfrFile.absolutePath},settings=profile,dumponexit=true",
    )
    outputs.upToDateWhen { false }

    doLast {
        val collapsedFile = jfrFile.resolveSibling("graph-load.collapsed")
        val htmlFile = jfrFile.resolveSibling("flamegraph.html")
        // Auto-convert if jfrconv is on PATH
        val jfrconvPath = listOf("jfrconv", "/opt/homebrew/bin/jfrconv")
            .firstOrNull { cmd -> runCatching { ProcessBuilder("which", cmd).start().waitFor() == 0 }.getOrDefault(false) }
        if (jfrconvPath != null) {
            exec { commandLine(jfrconvPath, "--cpu", "-o", "collapsed", "$jfrFile", "$collapsedFile"); isIgnoreExitValue = true }
            exec { commandLine(jfrconvPath, "--cpu", "$jfrFile", "$htmlFile"); isIgnoreExitValue = true }
            println("Collapsed stacks: $collapsedFile")
        } else {
            println("Install async-profiler: brew install async-profiler")
        }
    }
}
```

Key flags:
- `settings=profile` — enables CPU sampling (vs `settings=default` which is minimal)
- `dumponexit=true` — writes the JFR on normal JVM exit, including test runner exit
- `outputs.upToDateWhen { false }` — Gradle must always re-run profiling tasks

---

## Step 2 — Install jfrconv

```bash
# macOS
brew install async-profiler

# Linux — download from https://github.com/async-profiler/async-profiler/releases
# then: export PATH="$HOME/async-profiler/bin:$PATH"
```

Manual conversion after a run:

```bash
# Collapsed stacks (primary — use this for analysis)
jfrconv --cpu -o collapsed graph-load.jfr graph-load.collapsed

# HTML flamegraph (visualization)
jfrconv --cpu graph-load.jfr flamegraph.html

# Allocation profile (heap pressure)
jfrconv --alloc -o collapsed graph-load.jfr alloc.collapsed

# Lock contention (thread starvation)
jfrconv --lock -o collapsed graph-load.jfr lock.collapsed
```

**Filtering frames:** `jfrconv` supports `--exclude REGEX` and `--include REGEX` at conversion time if you want to narrow the output. Avoid hardcoding library names (e.g. `kryo`) since those may be app dependencies you want to see. Use `--include "dev\.yourpackage"` to show only your code when you know exactly what you're looking for.

---

## Step 3 — Analyze Collapsed Stacks

### Read it directly

Collapsed stacks are plain text — read with the `Read` tool. Each line is:
```
pkg/ClassName.method;pkg/Caller.method;pkg/Root.method 1247
```
Count is the last token. Root of call tree is rightmost frame; leaf (hottest) is leftmost.

### Extract top frames (awk — no Python needed)

```bash
# Top leaf frames by self-sample count
awk '{n=$NF; sub(/ [0-9]+$/,"",n); split(n,a,";"); leaf=a[1]; count[leaf]+=$NF} END{for(f in count) print count[f],f}' \
  build/reports/graph-load.collapsed | sort -rn | head -20

# Top full stacks (raw, sorted by count)
sort -t' ' -k2 -rn build/reports/graph-load.collapsed | head -20

# Stacks containing a specific class (drill into a subsystem)
grep "GraphLoader" build/reports/graph-load.collapsed | sort -t' ' -k2 -rn | head -10
```

### Minimal Python alternative (when you need total-sample percentages)

```python
from collections import defaultdict
import sys

lines = open(sys.argv[1]).readlines()
total = sum(int(l.rsplit(" ", 1)[1]) for l in lines if l.strip())
by_leaf = defaultdict(int)
for line in lines:
    stack, _, count = line.strip().rpartition(" ")
    leaf = stack.split(";")[0]
    by_leaf[leaf] += int(count)

for count, frame in sorted((-v, k) for k, v in by_leaf.items())[:20]:
    print(f"{100*-count/total:5.1f}%  {-count:6d}  {frame}")
```

---

## Step 4 — CI Integration

```yaml
# .github/workflows/profile.yml
jobs:
  profile:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with: { distribution: temurin, java-version: 17 }

      - name: Install async-profiler
        run: |
          wget -q https://github.com/async-profiler/async-profiler/releases/latest/download/async-profiler-linux-x64.tar.gz
          tar xf async-profiler-linux-x64.tar.gz
          echo "$PWD/async-profiler/bin" >> $GITHUB_PATH

      - run: ./gradlew jvmTestProfile --rerun-tasks

      - uses: actions/upload-artifact@v4
        with:
          name: profiling-${{ github.sha }}
          path: |
            kmp/build/reports/graph-load.collapsed
            kmp/build/reports/flamegraph.html
          retention-days: 30
```

**Store collapsed stacks as the primary CI artifact** — they're text, ~10-50 KB, and diffable between commits.

---

## Step 5 — A/B Comparison

```bash
# Download artifacts for two commits
# (GitHub CLI: gh run download <run-id> --name profiling-<sha>)

# Text diff — shows which stacks gained/lost samples
diff baseline.collapsed current.collapsed

# Differential flamegraph (red=regression, blue=improvement)
jfrconv --diff baseline.jfr current.jfr diff-flamegraph.html
# Or from collapsed stacks via Brendan Gregg's tools:
# difffolded.pl baseline.collapsed current.collapsed | flamegraph.pl > diff.svg
```

---

## Step 6 — Interpreting Results

### Hotspot patterns and fixes

| Pattern in collapsed stacks | Diagnosis | Fix |
|-----------------------------|-----------|-----|
| `JDBC.connect;DriverManager.getConnection` in hot path | New connection per transaction | Connection pool (HikariCP) or persistent connection |
| `transaction;newTransaction` dominant (>15%) | Too many small transactions | Batch N operations into one `transaction {}` |
| `GarbageCollector` or `G1Young` > 10% | Heap pressure / allocation churn | Object pooling; reduce per-loop allocations |
| `AbstractQueuedSynchronizer.acquire` | Lock contention | Actor pattern; reduce lock scope |
| `KotlinJsonDecoder` / `ObjectInputStream` | Serialization on hot path | Lazy parse; cache deserialized objects |
| `EPoll.wait` / `Kryo` | Gradle test infra (IPC/sockets) | Ignore — filter your package namespace |

### Filter to app-only frames

```bash
# Exclude JDK/Gradle infrastructure; show only your packages
grep "dev\.stapler\|dev\.logseq" build/reports/graph-load.collapsed | \
  sort -t' ' -k2 -rn | head -30
```

Sample count in infra threads (EPoll, Kryo, JUnit engine) is expected. If they're < 5% of total samples, ignore them entirely.

---

## Quick Reference

| Goal | Command |
|------|---------|
| Run benchmark | `./gradlew jvmTestProfile` |
| Collapsed stacks | `jfrconv --cpu -o collapsed graph-load.jfr graph-load.collapsed` |
| HTML flamegraph | `jfrconv --cpu graph-load.jfr flamegraph.html` |
| Alloc profile | `jfrconv --alloc -o collapsed graph-load.jfr alloc.collapsed` |
| Lock profile | `jfrconv --lock -o collapsed graph-load.jfr lock.collapsed` |
| Top leaf frames | `awk '...' graph-load.collapsed \| sort -rn \| head -20` (see Step 3) |
| A/B diff | `jfrconv --diff before.jfr after.jfr diff.html` |

## Common Pitfalls

- **`settings=default`** — CPU sampling is off by default; always use `settings=profile`
- **Forgetting `--rerun-tasks` in CI** — Gradle caches the task result; profiling is always stale
- **Reading EPoll/Kryo as app code** — these are Gradle test-infra threads; filter by your package
- **Using HTML for LLM analysis** — the cpool encoding requires a decoder; use collapsed stacks instead
- **p50 only** — always collect p50 + p95 + p99; tail latency reveals starvation
