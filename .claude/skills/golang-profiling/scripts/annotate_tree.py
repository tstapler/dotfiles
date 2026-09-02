#!/usr/bin/env python3
"""Build a terse, indented call tree with self%/cum% annotations from
`go tool pprof -raw` output.

This is the middle ground between a flat top-N table (loses which caller is
responsible) and full collapsed stacks (keeps every call path, but as
thousands of near-duplicate lines that burn tokens without adding much signal
for an LLM deciding what to fix). Recursive call chains collapse naturally
because siblings are merged by function name at each depth, and low-weight
subtrees are pruned so the output stays readable even on multi-thousand-
sample profiles.

Usage:
    go tool pprof -raw cpu.prof > raw.txt
    python3 annotate_tree.py raw.txt
    python3 annotate_tree.py raw.txt --min-pct 2 --hotspot-pct 8 --max-depth 10

No third-party dependencies -- stdlib only, so it runs anywhere `python3` does.
"""
import argparse
import re
import sys
from collections import defaultdict

SAMPLE_RE = re.compile(r"^\s*(\d+)\s+\d+:\s*([\d ]+)\s*$")
LOCATION_RE = re.compile(r"^\s*(\d+):\s+0x[0-9a-fA-F]+\s+M=\d+\s+(\S+)")


def parse_raw(text: str):
    """Returns (samples, locations): samples is [(count, [location_id, ...])]
    with location ids ordered leaf-first (as pprof -raw emits them);
    locations maps location id -> function name."""
    samples = []
    locations = {}
    section = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "Samples:":
            section = "samples-header"
            continue
        if stripped == "Locations":
            section = "locations"
            continue
        if stripped in ("Mappings", "Comments"):
            section = None
            continue
        if section == "samples-header":
            section = "samples"  # this line is the "samples/count value/unit" header
            continue
        if section == "samples":
            m = SAMPLE_RE.match(line)
            if m:
                count = int(m.group(1))
                ids = [int(x) for x in m.group(2).split()]
                samples.append((count, ids))
        elif section == "locations":
            m = LOCATION_RE.match(line)
            if m:
                locations[int(m.group(1))] = m.group(2)
    return samples, locations


class Node:
    __slots__ = ("name", "self_count", "cum_count", "children")

    def __init__(self, name: str):
        self.name = name
        self.self_count = 0
        self.cum_count = 0
        self.children: dict[str, "Node"] = {}


def build_tree(samples, locations) -> tuple[Node, int]:
    root = Node("(root)")
    total = 0
    for count, ids in samples:
        total += count
        # ids are leaf-first; walk root-first to build the tree top-down.
        path = [locations.get(i, f"?{i}") for i in reversed(ids)]
        node = root
        node.cum_count += count
        for name in path:
            child = node.children.get(name)
            if child is None:
                child = Node(name)
                node.children[name] = child
            child.cum_count += count
            node = child
        node.self_count += count
    return root, total


def render(node: Node, total: int, min_pct: float, hotspot_pct: float, max_depth: int,
           depth: int = 0, prefix: str = "") -> list[str]:
    lines = []
    visible = [c for c in node.children.values() if 100 * c.cum_count / total >= min_pct]
    visible.sort(key=lambda n: -n.cum_count)
    for i, child in enumerate(visible):
        last = i == len(visible) - 1
        cum_pct = 100 * child.cum_count / total
        self_pct = 100 * child.self_count / total
        connector = "└── " if last else "├── "
        marker = "  ◀ HOTSPOT" if self_pct >= hotspot_pct else ""
        lines.append(f"{prefix}{connector}[{self_pct:5.1f}% | {cum_pct:5.1f}%] {child.name}{marker}")
        if depth + 1 < max_depth:
            ext = "    " if last else "│   "
            lines.extend(render(child, total, min_pct, hotspot_pct, max_depth, depth + 1, prefix + ext))
    return lines


def top_self(root: Node, total: int, n: int) -> list[tuple[float, str]]:
    """Flat self-time leaderboard, independent of call-tree position --
    catches hotspots that are individually small per call site but add up
    across many callers (e.g. a helper called from a dozen places)."""
    totals: dict[str, int] = defaultdict(int)

    def walk(node: Node):
        if node.self_count:
            totals[node.name] += node.self_count
        for c in node.children.values():
            walk(c)

    walk(root)
    ranked = sorted(totals.items(), key=lambda kv: -kv[1])[:n]
    return [(100 * count / total, name) for name, count in ranked]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw_file", help="Output of `go tool pprof -raw <profile>` ('-' for stdin)")
    ap.add_argument("--min-pct", type=float, default=1.0,
                     help="Prune subtrees below this cum%% of total (default: 1.0)")
    ap.add_argument("--hotspot-pct", type=float, default=5.0,
                     help="Mark nodes with self%% >= this as HOTSPOT (default: 5.0)")
    ap.add_argument("--max-depth", type=int, default=15, help="Max tree depth to render (default: 15)")
    ap.add_argument("--top-self", type=int, default=10,
                     help="Also print a flat top-N self-time leaderboard (default: 10, 0 to disable)")
    args = ap.parse_args()

    text = sys.stdin.read() if args.raw_file == "-" else open(args.raw_file, encoding="utf-8").read()
    samples, locations = parse_raw(text)
    if not samples:
        print("No samples parsed -- is this the output of `go tool pprof -raw`?", file=sys.stderr)
        sys.exit(1)

    root, total = build_tree(samples, locations)

    print(f"Total samples: {total}")
    print(f"Legend: [self% | cum%] function  (pruned below {args.min_pct}% cum, "
          f"HOTSPOT = self% >= {args.hotspot_pct}%)\n")
    print("\n".join(render(root, total, args.min_pct, args.hotspot_pct, args.max_depth)))

    if args.top_self > 0:
        print(f"\nTop {args.top_self} by self-time (flat, across all call sites):")
        for pct, name in top_self(root, total, args.top_self):
            print(f"  {pct:5.1f}%  {name}")


if __name__ == "__main__":
    main()
