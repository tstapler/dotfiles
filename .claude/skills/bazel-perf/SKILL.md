---
name: bazel-perf
description: Find the slowest parts of a SteleKit Bazel build/test run and CI job, and know which fixes actually move the needle. Use when asked to speed up Bazel builds/tests, investigate why CI is slow, or find build hotspots — locally or from a GitHub Actions run.
---

# Bazel build/CI hotspot hunting

Bazel already tells you where time goes. Don't build custom instrumentation — read
its own trace profile and `INFO:` summary lines first.

## 1. Local: profile one build/test

```bash
bazel build //kmp:android_app --config=android --profile=/tmp/profile.json.gz
# or: bazel test //kmp:jvm_tests --profile=/tmp/profile.json.gz
```

`bazel analyze-profile` is gone as of Bazel 9.2.0 (this repo's version — no `.bazelversion`
pin, Bazelisk resolves latest) — `bazel help` doesn't list it. It was still documented as
of Bazel 7.4.0, so it was removed somewhere in 8.x/9.x, not just missing from an old
install; upgrading further will not bring it back. Use the JSON trace profile directly
instead — it's the modern, still-supported path and is actually more useful (interactive
timeline, not just text):

- **Perfetto UI (recommended):** open https://ui.perfetto.dev, drag in the `.json.gz`
  directly (no need to unzip) — flamegraph-style timeline, filterable by thread/action.
- **`chrome://tracing`:** same file, unzip first (`gunzip profile.json.gz`); Perfetto UI
  supersedes this but it still works.
- **jq, for a quick top-N without leaving the terminal** — pull the slowest individual
  actions (filter out phase/wrapper wrapper events like `Action.execute`,
  `Resources acquired`, `Worker #N working`, `buildTargets` to see real action names):

```bash
zcat /tmp/profile.json.gz | jq -r '
  .traceEvents[] | select(.dur != null) | "\(.dur/1000)ms \(.name)"
' | sort -rn | head -20
```

## 2. The single most useful number: elapsed vs. critical path

Every `bazel build`/`test` prints this line — it's the fastest hotspot signal there is:

```
INFO: Elapsed time: 1510.753s, Critical Path: 236.84s
```

- **Elapsed ≈ Critical Path** → the build is dependency-chain-bound. The only fix is
  shortening that chain (split a slow target, parallelize within it, cache it).
- **Elapsed ≫ Critical Path** (seen here: 6.4x) → most of the wall clock is
  *scheduling/spawn overhead*, not real work. Look at concurrency limits
  (`--local_resources`, `--jobs`) and whether actions run as persistent workers
  vs. spawning a fresh process each time (next section).

Check this for a CI run without downloading full logs:

```bash
gh run view <run-id> --log 2>/dev/null | grep -E "INFO: Elapsed time|Build completed"
```

## 3. Action-strategy breakdown (is this job action-count-bound?)

Bazel prints the execution strategy after each action line, e.g.
`; 3s disk-cache, remote-cache, processwrapper-sandbox`. Tally them:

```bash
gh run view <run-id> --log 2>/dev/null | grep "<job name>" \
  | grep -oP '; \d+s \K[a-z0-9, -]+(?=\.\.\.)' | sort | uniq -c | sort -rn
```

`processwrapper-sandbox`/`linux-sandbox` means a fresh process (often a fresh JVM) per
action — expensive when there are thousands of small actions (Android dexing/desugaring,
per-file C++ compiles). `worker`/`multiplex-worker` means a warm persistent process is
reused. A job dominated by sandbox strategy with a large elapsed/critical-path gap is the
textbook case for enabling persistent workers, not for adding more CPU/jobs.

**Tried and reverted here** (do not re-attempt without the memory math below):
`build:android --persistent_android_dex_desugar` and `--persistent_android_resource_processor`
(native `rules_android`/Bazel flags — `bazel help build | grep persistent`) shift Desugar/
DexBuilder/PackageAndroidResources from `processwrapper-sandbox` to `worker` mode — real, on
`//kmp:android_app` this was the majority of a 6.4x elapsed/critical-path gap. But it doesn't
fit this repo's 16GB GH runner and got reverted after 3 failed CI attempts.

**Why it broke, and why "local passed" didn't catch it.** A persistent worker stays
resident holding its JVM heap *between* actions instead of releasing it on exit like the
sandboxed process it replaces, and these actions' declared `resource_set` apparently
understates that footprint — so `--local_resources=memory=` doesn't stop enough concurrent
workers from spawning to blow past the runner's real RAM. Local verification on a
61GB/24-core dev box showed clean action-count shifts with zero swap and looked fully
safe — the box just has too much headroom to ever hit the ceiling. **Do the memory math
against the target runner's actual RAM, not just "run it and check for failures":** this
repo's own `.bazelrc` already documents these as `-Xmx3G` processes (the comment behind
`--local_resources=memory=9000`). Even `--worker_max_instances=<Mnemonic>=2` on all three
new-worker mnemonics is 6 workers × 3GB = 18GB from *just those three*, before the 6GB
Bazel-server cap, `KotlinCompile`'s own (pre-existing, already-persistent) worker, or OS
overhead — on a 16GB box that was never going to fit, and 3 rounds of CI (runs
33929109869, 33931054162, 33931907031) each took ~12-25 minutes to confirm it the hard
way. Multiply *(cap × mnemonics × per-worker -Xmx)* against the runner's total RAM minus
the Bazel server cap **before** picking a cap number, and mnemonic name matters
(`--worker_max_instances=<Mnemonic>=N`, `--worker_max_multiplex_instances=<Mnemonic>=N` —
find every mnemonic the flag actually touches with
`grep -oP 'bazel-workers/worker-\d+-\K\w+(?=\.log)'` on a failure log, not just the ones
you expect; missing one is exactly what caused attempt #2 here). **A local "no failures"
run is not sufficient proof for any worker/concurrency flag — push it and watch the actual
CI job, and don't declare success until that's green**, not just "didn't error locally."
Revisiting this needs either a larger-memory CI runner or verified real per-worker RSS
(not the tool's understated `resource_set`) measured on hardware matching the runner.

## 3b. One giant target on the critical path

The jq top-N (§1) surfaces this directly: if the single biggest action is a `KotlinCompile`
covering hundreds of files in one target (e.g. `//kmp/src/androidMain/kotlin:android_main
{ kt: 711 }` at 71s — measured here, ~half of a 138s critical path by itself), that's a
monolithic-module problem, not a scheduling or worker problem. A single Kotlin compilation
unit can't be parallelized internally and can't get a partial cache hit — touch one file
in it and the whole 711-file action reruns. §2's rule applies: this is dependency-chain-
bound, so persistent workers/more cores/cache tuning don't touch it. The fix is splitting
the module into smaller Bazel targets (by package, e.g. `:model`, `:repository`, `:db`,
`:ui` as separate `kt_jvm_library`/`kt_android_library` targets with explicit deps) so an
unrelated change only recompiles its own slice. Check for import cycles between the
candidate packages first (`grep -rl "import dev.stapler.stelekit.<pkgA>" <pkgB>/` both
ways) — a real cycle means those two packages can't be split apart without breaking one of
them out further.

## 4. Local build (correctness first, output is secondary signal)

`bazel build ... --config=remote-cache` prints cache-hit counts at the end
(`INFO: N processes: X action cache hit, Y disk cache hit, ...`). A cold run with
near-zero cache hits on a CI branch that should have a warm cache points at cache-key
churn or GitHub Actions cache eviction (~10GB/repo), not compute — check
`.github/workflows/bazel-ci.yml`'s `setup-bazel` cache config before touching build flags.

## What NOT to do

- Don't add `--jobs=N` blindly — GH standard runners are 4 vCPU; more `--jobs` than
  cores just adds queuing, it doesn't add throughput.
- Don't raise `--local_resources=memory=` without re-reading the OOM comment above it in
  `.bazelrc` (run 33803270917 — Bazel server got OOM-killed at higher concurrency).
- Don't chase the slowest single action mnemonic before checking elapsed-vs-critical-path
  — a build with a short critical path but a huge gap is a scheduling problem, and
  shaving one slow action won't fix it.
- Don't enable a persistent-worker flag and call it done after one clean local run — verify
  on the real CI runner's memory (§3's OOM story). A big dev box hides exactly this class
  of regression.
- Don't reach for `bazel analyze-profile` — it doesn't exist in this repo's Bazel version.
  Use the JSON trace profile (§1).
