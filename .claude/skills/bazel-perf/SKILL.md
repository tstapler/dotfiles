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
bazel analyze-profile /tmp/profile.json.gz          # phase breakdown, critical path
```

For per-action detail, load `/tmp/profile.json.gz` at `chrome://tracing` (unzip first),
or pull the slowest individual actions with jq:

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

Known win already applied here: `build:android --persistent_android_dex_desugar` and
`--persistent_android_resource_processor` in `.bazelrc` (native `rules_android`/Bazel
flags — `bazel help build | grep persistent`). Verified locally: shifted 466/809 actions
from `processwrapper-sandbox` to `worker` on `//kmp:android_app` with no failures.

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
