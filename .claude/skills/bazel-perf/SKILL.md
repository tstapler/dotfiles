---
name: bazel-perf
description: Find the slowest parts of a Bazel build or test run, locally or in CI, and know which fixes move the needle. Use when asked to speed up Bazel builds/tests, investigate why CI is slow, or find build hotspots. Repo-specific history lives in that repo's own skill (e.g. stelekit-bazel-perf).
---

# Bazel build/CI hotspot hunting

Bazel already tells you where time goes. Read its own trace profile and `INFO:` summary lines before building custom instrumentation.

## 1. Profile one build or test run

```bash
bazel build //some:target --profile=/tmp/profile.json.gz --experimental_profile_include_target_label
# or: bazel test //... --profile=/tmp/profile.json.gz
```

`bazel analyze-profile` was removed in Bazel 9 (still documented in 7.x); upgrading will not bring it back. Use the JSON trace profile:

- **Perfetto UI (recommended):** open https://ui.perfetto.dev and drag in the `.json.gz` (no unzip). Filter by thread or action.
- **`chrome://tracing`:** same file, gunzip first.
- **Terminal top-N with jq** (filter wrapper events such as `Action.execute`, `Resources acquired`, `Worker #N working`, `buildTargets` to see real action names):

```bash
zcat /tmp/profile.json.gz | jq -r '.traceEvents[] | select(.dur != null) | "\(.dur/1000)ms \(.name)"' | sort -rn | head -20
```

In CI the profile file is only readable if the CI system exports it; otherwise print a summary into the log (a small script over `traceEvents`: `build phase marker`, `critical path component` and action categories).

## 2. Elapsed vs. critical path

Every `bazel build`/`test` prints `INFO: Elapsed time: 1510s, Critical Path: 236s`.

- **Elapsed close to Critical Path:** dependency-chain-bound. Shorten the chain: split a slow target, parallelize within it, cache it.
- **Elapsed much larger than Critical Path:** scheduling or spawn overhead. Check `--jobs`, `--local_resources`, and whether actions run as persistent workers or fresh processes (section 3).

From a CI log: `grep -E "INFO: Elapsed time|Build completed"`.

## 3. Execution strategy breakdown

Action lines end with the strategy, e.g. `; 3s disk-cache, remote-cache, processwrapper-sandbox`. Tally them from the log. `processwrapper-sandbox`/`linux-sandbox` means a fresh process (often a fresh JVM) per action, which hurts with thousands of small actions. `worker`/`multiplex-worker` reuses a warm process. A job dominated by sandbox strategy with a large elapsed/critical-path gap is the textbook case for persistent workers, not for more CPU.

**Persistent workers hold their heap between actions** and a rule's declared `resource_set` often understates that, so `--local_resources=memory=` may not stop enough concurrent workers from blowing past real RAM. A big dev box hides this. Before enabling any worker or concurrency flag, compute *(instance cap x worker mnemonics x per-worker -Xmx)* against the CI runner's RAM minus the Bazel server's own cap. Find every mnemonic a flag touches from the worker logs (`bazel-workers/worker-N-<Mnemonic>.log`), not just the expected ones. A clean local run is not proof; watch the real CI job.

## 4. One giant target on the critical path

If the biggest action is a single compile of hundreds of files, it is a monolithic-module problem. It cannot be parallelized internally and gets no partial cache hit: touching one file reruns all of it. Workers, cores and cache tuning will not help; split the module into smaller targets. Check for import cycles between candidate packages first.

## 5. Where test time goes

Bazel's profile stops at the whole test target. For per-test-function times:

- rules_go: pass `--test_env=GO_TEST_WRAP_TESTV=1`; each `bazel-testlogs/<pkg>/<target>/test.xml` (and `shard_N_of_M/test.xml`) then carries `<testcase time=...>`. Without it `test.xml` has no testcases.
- Rank them with a short script over `testcase` elements; list top-level tests apart from subtests, since a parent's time includes its subtests.
- Shard a long-pole target (`shard_count = N`) only after confirming its tests are independent; a test that assumes it runs the whole package (call-proof or coverage gates) must detect `TEST_TOTAL_SHARDS>1`.
- Changing `--test_env` changes the test action key once, so the first run after the change is uncached.

## 6. Cache hits

`INFO: N processes: X action cache hit, Y disk cache hit, ...` prints at the end. A cold run with near-zero hits where the cache should be warm points at cache-key churn or cache eviction/host affinity, not compute. Check the CI cache configuration before touching build flags.

## What NOT to do

- Don't add `--jobs=N` blindly; more jobs than cores only adds queuing.
- Don't raise `--local_resources=memory=` without reading why it was set (usually an OOM kill).
- Don't chase the slowest single action before checking elapsed vs. critical path.
- Don't enable a persistent-worker flag after one clean local run (section 3).
- Don't reach for `bazel analyze-profile` on Bazel 9 (section 1).
