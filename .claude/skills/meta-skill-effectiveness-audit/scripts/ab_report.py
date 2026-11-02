#!/usr/bin/env python3
"""Summarize results.jsonl from ab_runner.py: per-arm means and a bootstrap CI on the difference.

    ab_report.py RESULTS.jsonl [--base A] [--other B]

With only a handful of runs per arm the CI is wide; that is the honest answer, not a bug.
Cost per success divides an arm's total spend by its successes, so failed runs count against it.
"""
import argparse
import json
from collections import defaultdict

import numpy as np

METRICS = ["cost_usd", "turns", "duration_s", "blockers_found", "blockers_fixed", "gaps_found",
           "triad_invocations", "review_rounds", "subagents", "repair_agents", "plan_lines", "ux_lines"]
BOOTSTRAP_RESAMPLES = 10000


def value(rec, key):
    if key in rec:
        return rec[key]
    return (rec.get("score") or {}).get(key)


def boot_diff(a, b, rng):
    """95% percentile-bootstrap CI for mean(b) - mean(a), resampling runs within each arm."""
    a, b = np.array(a, float), np.array(b, float)
    diffs = [rng.choice(b, len(b)).mean() - rng.choice(a, len(a)).mean() for _ in range(BOOTSTRAP_RESAMPLES)]
    return np.percentile(diffs, [2.5, 97.5])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--base")
    ap.add_argument("--other")
    args = ap.parse_args()
    arms = defaultdict(list)
    with open(args.results) as fh:
        for line in fh:
            rec = json.loads(line)
            arms[rec["arm"]].append(rec)
    names = sorted(arms)
    base = args.base or names[0]
    other = args.other or names[-1]
    rng = np.random.default_rng(1)
    print(f"{base}: n={len(arms[base])}   {other}: n={len(arms[other])}   (difference = {other} - {base})\n")
    print(f"{'metric':<20}{base:>12}{other:>12}{'diff':>10}   95% CI")
    for m in METRICS:
        a = [value(r, m) for r in arms[base] if value(r, m) is not None]
        b = [value(r, m) for r in arms[other] if value(r, m) is not None]
        if len(a) < 2 or len(b) < 2:
            continue
        lo, hi = boot_diff(a, b, rng)
        print(f"{m:<20}{np.mean(a):>12.2f}{np.mean(b):>12.2f}{np.mean(b) - np.mean(a):>10.2f}   [{lo:.2f}, {hi:.2f}]")
    print()
    for name in (base, other):
        runs = arms[name]
        ok = sum(1 for r in runs if (r.get("score") or {}).get("success"))
        total = sum(r.get("cost_usd") or 0 for r in runs)
        cps = f"${total / ok:.2f}" if ok else "n/a (no successes)"
        print(f"{name}: {ok}/{len(runs)} successes, total ${total:.2f}, cost per success {cps}")


if __name__ == "__main__":
    main()
