#!/usr/bin/env python3
"""Percentage breakdown of leaf-frame self-time from collapsed stacks.

Usage:
    go tool pprof -raw -output=raw.txt cpu.prof
    stackcollapse-go.pl raw.txt > cpu.collapsed   # or your collapse step of choice
    python3 pct_breakdown.py cpu.collapsed [--top 20]

Collapsed-stacks format: one line per unique call stack, "root;caller;leaf N"
(semicolon-joined stack, root-first/leaf-last, trailing sample count -- the
Brendan Gregg / stackcollapse-go.pl convention). This ranks by leaf frame
(where the sample actually landed), not by any single ancestor -- use
annotate_tree.py instead when you need call-path context.
"""
import argparse
import sys
from collections import defaultdict


def compute_breakdown(lines, top: int = 20) -> list[tuple[float, int, str]]:
    """Returns [(pct, count, leaf_frame), ...] sorted by count descending,
    limited to `top` entries. Raises ValueError if no samples are found."""
    total = 0
    by_leaf: dict[str, int] = defaultdict(int)
    for line in lines:
        line = line.strip()
        if not line:
            continue
        stack, _, count_str = line.rpartition(" ")
        count = int(count_str)
        total += count
        leaf = stack.split(";")[-1]
        by_leaf[leaf] += count

    if total == 0:
        raise ValueError("No samples found in input.")

    ranked = sorted((-v, k) for k, v in by_leaf.items())[:top]
    return [(100 * -count / total, -count, frame) for count, frame in ranked]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("collapsed_file", help="Collapsed-stacks file ('-' for stdin)")
    ap.add_argument("--top", type=int, default=20, help="Number of leaf frames to show (default: 20)")
    args = ap.parse_args()

    lines = sys.stdin.readlines() if args.collapsed_file == "-" else open(
        args.collapsed_file, encoding="utf-8"
    ).readlines()

    try:
        rows = compute_breakdown(lines, args.top)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    for pct, count, frame in rows:
        print(f"{pct:5.1f}%  {count:6d}  {frame}")


if __name__ == "__main__":
    main()
