#!/usr/bin/env python3
"""Where does a Go test run's time go? Histogram + Pareto + Amdahl, from real measurements.

Inputs (collect with scripts/collect.sh, or by hand — see SKILL.md Step 0):
  --json   FILE   `go test -json` output for ONE package (required)
  --cpu    FILE   `-cpuprofile` file (optional; enables the cost-class breakdown)
  --bin    FILE   the test binary from `go test -o` (needed to symbolize --cpu)
  --time   FILE   `/usr/bin/time -l -o FILE go test ...` output (optional; macOS format;
                  adds subprocess CPU and utilization)
  --rules  FILE   JSON {"class name": ["substring", ...]} overriding the default classes
  --cores  N      logical cores the run had (default: this machine)

Reads three different questions off one run — keep them separate:
  1. Test-duration histogram + Pareto: which *tests* matter.            (from --json)
  2. Serial fraction (Amdahl on parallelism): can more cores help?       (from --json)
  3. CPU cost classes (Amdahl on cost): which *work* matters.            (from --cpu)

Caveat that bites: per-test durations from a run where many tests execute at once are
inflated by contention. Treat them as relative weights, not as what each test costs alone.
"""
import argparse
import collections
import json
import math
import os
import re
import subprocess
import sys

BAR = 28

# Priority order: the first class with a marker anywhere in the sample's stack wins, so list
# specific, avoidable costs before generic ones. Markers are substrings of function names.
DEFAULT_RULES = collections.OrderedDict(
    [
        ("ent schema migration", ["schema.(*Atlas)", "migrate.(*Schema)", ".Schema.Create"]),
        ("test storage setup (non-migration)", ["NewTestEntRepository", "newSeededEntRepository", "NewEntRepository"]),
        ("go-git", ["go-git/go-git"]),
        ("subprocess exec", ["os/exec.", "os.StartProcess", "syscall.forkExec", "safeexec."]),
        ("tmux", ["session/tmux."]),
        ("sqlite queries", ["modernc.org/sqlite"]),
        ("ent ORM", ["entgo.io/ent", "session/ent."]),
        ("protobuf / connect / json", ["google.golang.org/protobuf", "connectrpc.com", "encoding/json"]),
        ("network / http", ["net/http.", "net.(*"]),
        ("regexp", ["regexp."]),
    ]
)
# Leaf-only classes (the runtime is the leaf of the stack, not an ancestor).
GC_LEAF = re.compile(r"runtime\.(gcBgMarkWorker|gcDrain|scanobject|scanblock|greyobject|markroot|mallocgc|memclr|bgsweep|sweep)")
RACE_LEAF = re.compile(r"(__tsan|racecall|runtime\.race|racefunc|raceread|racewrite|tsan)")
SCHED_LEAF = re.compile(r"runtime\.(findRunnable|schedule|park_m|mcall|futex|usleep|notesleep|gopark|netpoll|kevent|pthread_cond|semasleep)")


def fmt_s(x):
    return f"{x:,.1f}s" if x >= 1 else f"{x * 1000:,.0f}ms"


def bar(frac):
    n = int(round(frac * BAR))
    return "█" * n + "·" * (BAR - n)


def amdahl(p, s):
    """Overall speedup when fraction p of the time gets s times faster (s=inf removes it)."""
    return 1.0 / ((1.0 - p) + (0.0 if math.isinf(s) else p / s))


# ---------------------------------------------------------------------------- go test -json
def read_json(path):
    tests, parallel, pkgs = {}, set(), {}
    for line in open(path, errors="replace"):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        t, a = e.get("Test"), e.get("Action")
        if t and "/" not in t:
            if a == "pause":
                parallel.add(t)
            elif a in ("pass", "fail"):
                tests[t] = (e.get("Elapsed", 0.0), a)
        elif not t and a in ("pass", "fail"):
            pkgs[e.get("Package", "?")] = (e.get("Elapsed", 0.0), a)
    return tests, parallel, pkgs


def section_tests(tests, parallel, pkgs, cores):
    wall = max((v[0] for v in pkgs.values()), default=0.0)
    total = sum(d for d, _ in tests.values())
    print("## 1. Test-duration histogram\n")
    print(f"- package wall: **{fmt_s(wall)}**   top-level tests: **{len(tests)}**   "
          f"sum of test durations: **{fmt_s(total)}**   parallel tests: **{len(parallel)}**\n")
    buckets = [(0, 0.01), (0.01, 0.1), (0.1, 1), (1, 5), (5, 20), (20, float("inf"))]
    names = ["<10ms", "10–100ms", "0.1–1s", "1–5s", "5–20s", "≥20s"]
    print("| bucket | tests | total time | share of test time | |")
    print("|---|---:|---:|---:|---|")
    for (lo, hi), name in zip(buckets, names):
        sel = [d for d, _ in tests.values() if lo <= d < hi]
        s = sum(sel)
        frac = s / total if total else 0
        print(f"| {name} | {len(sel)} | {fmt_s(s)} | {frac:5.1%} | `{bar(frac)}` |")
    print("\n### Pareto — how concentrated is it?\n")
    ranked = sorted(((d, n) for n, (d, _) in tests.items()), reverse=True)
    acc = 0.0
    marks = {1, 5, 10, 20, 50, 100}
    print("| top N tests | cumulative share of test time |")
    print("|---:|---:|")
    for i, (d, _) in enumerate(ranked, 1):
        acc += d
        if i in marks:
            print(f"| {i} | {acc / total:5.1%} |")
    print("\n| slowest | duration | parallel? |")
    print("|---|---:|---|")
    for d, n in ranked[:8]:
        print(f"| `{n[:70]}` | {fmt_s(d)} | {'yes' if n in parallel else 'no'} |")

    print("\n## 2. Serial fraction — can more cores help? (Amdahl on parallelism)\n")
    serial = sum(d for n, (d, _) in tests.items() if n not in parallel)
    par_work = total - serial
    # serial top-level tests run one after another, so they add to wall 1:1.
    s_frac = serial / wall if wall else 0
    print(f"- serial top-level tests: **{fmt_s(serial)}** = **{s_frac:.0%} of wall** "
          f"(these cannot overlap each other)")
    print(f"- parallel tests: **{fmt_s(par_work)}** of work (durations inflated by contention)")
    left = max(wall - serial, 0.0)
    if left > 0:
        print(f"- wall not explained by serial tests: {fmt_s(left)} → effective parallelism of the "
              f"parallel phase ≈ **{par_work / left:.1f}×** (runner has {cores} cores)")
    if s_frac > 0:
        print(f"- **ceiling from parallelism alone: {1 / s_frac:.1f}× faster** even with infinite cores, "
              f"until the serial tests themselves shrink or go parallel")
    print()
    return wall, total


# ------------------------------------------------------------------------------ cpu profile
def read_raw(cpu, binpath):
    cmd = ["go", "tool", "pprof", "-raw"] + ([binpath] if binpath else []) + [cpu]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    funcs, loc_open, samples, mode = {}, None, [], None
    for line in out.splitlines():
        if line.startswith("Samples:"):
            mode = "samples"
            continue
        if line.startswith("Locations"):
            mode = "loc"
            continue
        if line.startswith("Mappings"):
            mode = None
            continue
        if mode == "samples":
            m = re.match(r"\s*(\d+)\s+(\d+):\s*([\d ]+)$", line)
            if m:
                samples.append((int(m.group(2)), [int(x) for x in m.group(3).split()]))
        elif mode == "loc":
            m = re.match(r"\s*(\d+):\s+0x[0-9a-f]+\s+M=\d+\s+(\S+)", line)
            if m:
                loc_open = int(m.group(1))
                funcs[loc_open] = [m.group(2)]
            elif loc_open is not None:
                m = re.match(r"\s+(\S+)\s+\S+:\d+\s+s=\d+", line)
                if m:
                    funcs[loc_open].append(m.group(1))
    return funcs, samples


def classify(stack_funcs, rules):
    leaf = stack_funcs[0] if stack_funcs else ""
    if GC_LEAF.search(leaf):
        return "GC / allocation"
    if RACE_LEAF.search(leaf):
        return "race-detector runtime"
    if SCHED_LEAF.search(leaf):
        return "scheduler / idle"
    for cls, marks in rules.items():
        for f in stack_funcs:
            if any(m in f for m in marks):
                return cls
    return "other (test + app code)"


def section_cpu(cpu, binpath, wall, rules, cores, time_file):
    funcs, samples = read_raw(cpu, binpath)
    if not samples:
        print("## 3. CPU cost classes\n\n_no samples in the profile (run too short, or symbolization failed)_\n")
        return
    by_cls = collections.Counter()
    leaf_in_cls = collections.defaultdict(collections.Counter)
    for ns, locs in samples:
        stack = [f for l in locs for f in funcs.get(l, [])]
        cls = classify(stack, rules)
        by_cls[cls] += ns
        leaf_in_cls[cls][stack[0] if stack else "?"] += ns
    total_ns = sum(by_cls.values())
    cpu_s = total_ns / 1e9
    print("## 3. CPU cost classes (Amdahl on cost)\n")
    util = cpu_s / (wall * cores) if wall else 0
    print(f"- profiled CPU in the test process: **{fmt_s(cpu_s)}** over **{fmt_s(wall)}** wall "
          f"→ **{cpu_s / wall:.1f} cores busy on average** of {cores} "
          f"(**{util:.0%} utilization**)")
    if util < 0.35:
        print("- utilization is low: wall time is dominated by **waiting / serial work**, not CPU. "
              "Cutting a CPU class helps less than its share suggests; look at section 2 first.")
    if time_file and os.path.exists(time_file):
        m = re.search(r"([\d.]+)\s+real\s+([\d.]+)\s+user\s+([\d.]+)\s+sys", open(time_file).read())
        if m:
            tot = float(m.group(2)) + float(m.group(3))
            print(f"- whole process tree CPU (`/usr/bin/time`): user+sys **{fmt_s(tot)}** — "
                  f"the part not in the profile (**{fmt_s(max(tot - cpu_s, 0))}**) is child processes "
                  f"and the `go` tool's own compile/link")
    print("\n| class | CPU | share | | top leaf function |")
    print("|---|---:|---:|---|---|")
    ranked = by_cls.most_common()
    for cls, ns in ranked:
        frac = ns / total_ns
        top = leaf_in_cls[cls].most_common(1)[0][0][:48]
        print(f"| {cls} | {fmt_s(ns / 1e9)} | {frac:5.1%} | `{bar(frac)}` | `{top}` |")

    print("\n### Amdahl — best-case whole-run speedup if a class gets faster\n")
    print("Assumes wall time scales with CPU time. Multiply by the CPU-boundness caveat above.\n")
    print("| class | share p | 2× faster | 10× faster | eliminated |")
    print("|---|---:|---:|---:|---:|")
    for cls, ns in ranked:
        p = ns / total_ns
        if p < 0.02 or cls.startswith(("scheduler", "other")):
            continue
        print(f"| {cls} | {p:5.1%} | {amdahl(p, 2):.2f}× | {amdahl(p, 10):.2f}× | {amdahl(p, float('inf')):.2f}× |")
    print("\nA class worth attacking has a large share **and** a fix that removes it (large s). "
          "If the best single row is under ~1.3×, only an architectural change that touches several "
          "classes at once (or the serial fraction in section 2) will move the number.\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", required=True)
    ap.add_argument("--cpu")
    ap.add_argument("--bin")
    ap.add_argument("--time")
    ap.add_argument("--rules")
    ap.add_argument("--cores", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    rules = DEFAULT_RULES
    if a.rules:
        rules = collections.OrderedDict(json.load(open(a.rules)))
    print(f"# Test time breakdown{': ' + a.title if a.title else ''}\n")
    tests, parallel, pkgs = read_json(a.json)
    if not tests:
        sys.exit("no top-level tests found in --json (was it `go test -json` for one package?)")
    wall, _ = section_tests(tests, parallel, pkgs, a.cores)
    if a.cpu:
        section_cpu(a.cpu, a.bin, wall, rules, a.cores, a.time)


if __name__ == "__main__":
    main()
