#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
Build and analyze the citation graph from stored papers.

Usage:
  uv run build_graph.py build           # Rebuild graph.json from papers/
  uv run build_graph.py stats           # Graph statistics
  uv run build_graph.py top --n 20      # Top papers by in-corpus citation count
  uv run build_graph.py clusters        # Find paper clusters / sub-topics
  uv run build_graph.py path <id1> <id2>  # Find citation path between papers
  uv run build_graph.py neighbors <id>  # Papers that cite or are cited by <id>

Environment:
  LITERATURE_DIR  Storage directory (default: ~/Documents/personal-wiki/literature/)
"""

import argparse
import json
import os
import sys
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Optional


LITERATURE_DIR = Path(os.environ.get(
    "LITERATURE_DIR",
    Path.home() / "Documents/personal-wiki/literature"
))


def load_all_papers() -> dict[str, dict]:
    papers_dir = LITERATURE_DIR / "papers"
    if not papers_dir.exists():
        return {}
    papers = {}
    for f in papers_dir.glob("*.json"):
        try:
            p = json.loads(f.read_text())
            papers[p["id"]] = p
        except Exception:
            pass
    return papers


def load_graph() -> dict:
    graph_path = LITERATURE_DIR / "graph.json"
    if graph_path.exists():
        return json.loads(graph_path.read_text())
    return {"edges": [], "paper_count": 0, "edge_count": 0}


def build_adjacency(papers: dict[str, dict]) -> tuple[dict, dict]:
    """Build outgoing (references) and incoming (cited_by) adjacency lists.

    Matches references by arXiv ID (primary) and by canonical OpenAlex ID (_oa_ref_ids)
    so that edges are captured even when published-paper DOIs don't carry arXiv links.
    """
    out_edges: dict[str, list[str]] = defaultdict(list)
    in_edges: dict[str, list[str]] = defaultdict(list)
    corpus_ids = set(papers.keys())
    # Build OA canonical ID → paper_id reverse map
    oa_to_paper: dict[str, str] = {}
    for pid, paper in papers.items():
        oa_id = paper.get("oa_id", "")
        if oa_id:
            oa_to_paper[oa_id] = pid

    for pid, paper in papers.items():
        # Match arXiv-resolved references
        seen: set[str] = set()
        for ref in paper.get("references", []):
            if ref in corpus_ids and ref not in seen:
                out_edges[pid].append(ref)
                in_edges[ref].append(pid)
                seen.add(ref)
        # Match raw OA reference IDs against canonical OA IDs of corpus papers
        for oa_ref_id in paper.get("_oa_ref_ids", []):
            tgt = oa_to_paper.get(oa_ref_id)
            if tgt and tgt != pid and tgt not in seen:
                out_edges[pid].append(tgt)
                in_edges[tgt].append(pid)
                seen.add(tgt)
    return dict(out_edges), dict(in_edges)


def cmd_build(args: argparse.Namespace) -> None:
    papers = load_all_papers()
    if not papers:
        print("No papers found. Run: fetch_papers.py search <query>")
        return

    out_edges, in_edges = build_adjacency(papers)

    edges = []
    for src, targets in out_edges.items():
        for tgt in targets:
            edges.append({"from": src, "to": tgt})

    # Update cited_by in each paper file
    for pid, citers in in_edges.items():
        if pid in papers:
            papers[pid]["cited_by"] = citers
            path = LITERATURE_DIR / "papers" / f"{pid.replace('arxiv:', '').replace('.', '_')}.json"
            if path.exists():
                path.write_text(json.dumps(papers[pid], indent=2, ensure_ascii=False))

    graph = {
        "built_at": datetime.now().isoformat(),
        "paper_count": len(papers),
        "edge_count": len(edges),
        "edges": edges,
    }
    graph_path = LITERATURE_DIR / "graph.json"
    graph_path.write_text(json.dumps(graph, indent=2, ensure_ascii=False))
    print(f"Graph built: {len(papers)} papers, {len(edges)} in-corpus citation edges")
    print(f"Saved to: {graph_path}")


def cmd_stats(args: argparse.Namespace) -> None:
    papers = load_all_papers()
    graph = load_graph()
    if not papers:
        print("No papers stored.")
        return

    _, in_edges = build_adjacency(papers)
    years = [p.get("year") for p in papers.values() if p.get("year")]
    venues = defaultdict(int)
    for p in papers.values():
        if p.get("venue"):
            venues[p["venue"]] += 1

    in_degrees = {pid: len(citers) for pid, citers in in_edges.items()}
    avg_in = sum(in_degrees.values()) / len(in_degrees) if in_degrees else 0

    print(f"=== Citation Graph Statistics ===")
    print(f"Papers:          {len(papers)}")
    print(f"In-corpus edges: {graph.get('edge_count', 0)}")
    print(f"Avg in-degree:   {avg_in:.1f}")
    print(f"Year range:      {min(years) if years else '?'} – {max(years) if years else '?'}")
    if venues:
        print(f"\nTop venues:")
        for venue, count in sorted(venues.items(), key=lambda x: -x[1])[:8]:
            print(f"  {count:3d}  {venue[:60]}")


def cmd_top(args: argparse.Namespace) -> None:
    papers = load_all_papers()
    if not papers:
        print("No papers stored.")
        return

    _, in_edges = build_adjacency(papers)
    in_degrees = {pid: len(citers) for pid, citers in in_edges.items()}

    # Rank: in-corpus citations first, break ties with total S2 citation count
    ranked = sorted(
        papers.items(),
        key=lambda x: (in_degrees.get(x[0], 0), x[1].get("citation_count", 0)),
        reverse=True
    )

    print(f"{'In-corp':<8} {'S2-total':<10} {'Year':<6} {'ID':<22} Title")
    print("-" * 100)
    for pid, paper in ranked[:args.n]:
        in_c = in_degrees.get(pid, 0)
        s2_c = paper.get("citation_count", 0)
        year = paper.get("year") or "????"
        title = paper.get("title", "")[:55]
        short_id = pid.replace("arxiv:", "")
        print(f"{in_c:<8} {s2_c:<10} {year:<6} {short_id:<22} {title}")


def cmd_clusters(args: argparse.Namespace) -> None:
    """Find weakly connected components as a proxy for topic clusters."""
    papers = load_all_papers()
    if not papers:
        print("No papers stored.")
        return

    out_edges, in_edges = build_adjacency(papers)
    all_ids = set(papers.keys())

    # Union-Find for connected components (undirected)
    parent = {pid: pid for pid in all_ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        parent[find(a)] = find(b)

    for src, targets in out_edges.items():
        for tgt in targets:
            union(src, tgt)

    clusters: dict[str, list[str]] = defaultdict(list)
    for pid in all_ids:
        clusters[find(pid)].append(pid)

    sorted_clusters = sorted(clusters.values(), key=len, reverse=True)
    print(f"Found {len(sorted_clusters)} clusters:")
    for i, cluster in enumerate(sorted_clusters[:10]):
        # Representative paper = highest in-corpus citation count in cluster
        _, in_edges_local = build_adjacency({pid: papers[pid] for pid in cluster})
        best = max(cluster, key=lambda p: len(in_edges_local.get(p, [])))
        print(f"\nCluster {i+1} ({len(cluster)} papers) — anchor: {papers[best]['title'][:60]}")
        for pid in sorted(cluster, key=lambda p: len(in_edges_local.get(p, [])), reverse=True)[:5]:
            print(f"  - [{papers[pid].get('year','')}] {papers[pid]['title'][:70]}")


def bfs_path(start: str, end: str, out_edges: dict) -> Optional[list[str]]:
    if start == end:
        return [start]
    visited = {start}
    queue = deque([[start]])
    while queue:
        path = queue.popleft()
        node = path[-1]
        for neighbor in out_edges.get(node, []):
            if neighbor == end:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])
    return None


def cmd_path(args: argparse.Namespace) -> None:
    papers = load_all_papers()
    out_edges, _ = build_adjacency(papers)
    from_id = f"arxiv:{args.from_id}" if not args.from_id.startswith("arxiv:") else args.from_id
    to_id = f"arxiv:{args.to_id}" if not args.to_id.startswith("arxiv:") else args.to_id

    path = bfs_path(from_id, to_id, out_edges)
    if path:
        print(f"Citation path ({len(path)-1} hops):")
        for pid in path:
            p = papers.get(pid, {})
            print(f"  → [{p.get('year','')}] {p.get('title', pid)[:70]}")
    else:
        print(f"No directed citation path found from {from_id} to {to_id}")


def cmd_neighbors(args: argparse.Namespace) -> None:
    papers = load_all_papers()
    pid = f"arxiv:{args.paper_id}" if not args.paper_id.startswith("arxiv:") else args.paper_id
    out_edges, in_edges = build_adjacency(papers)

    refs = out_edges.get(pid, [])
    citers = in_edges.get(pid, [])

    paper = papers.get(pid, {})
    print(f"Paper: {paper.get('title', pid)}")
    print(f"\nCites ({len(refs)} in corpus):")
    for r in refs:
        p = papers.get(r, {})
        print(f"  → [{p.get('year','')}] {p.get('title', r)[:70]}")
    print(f"\nCited by ({len(citers)} in corpus):")
    for c in citers:
        p = papers.get(c, {})
        print(f"  ← [{p.get('year','')}] {p.get('title', c)[:70]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze literature citation graph")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("build", help="Rebuild graph.json from stored papers").set_defaults(func=cmd_build)
    sub.add_parser("stats", help="Show graph statistics").set_defaults(func=cmd_stats)

    p_top = sub.add_parser("top", help="Top papers by in-corpus citations")
    p_top.add_argument("--n", type=int, default=20)
    p_top.set_defaults(func=cmd_top)

    sub.add_parser("clusters", help="Find topic clusters").set_defaults(func=cmd_clusters)

    p_path = sub.add_parser("path", help="Find citation path between papers")
    p_path.add_argument("from_id")
    p_path.add_argument("to_id")
    p_path.set_defaults(func=cmd_path)

    p_nb = sub.add_parser("neighbors", help="Show papers that cite or are cited by a paper")
    p_nb.add_argument("paper_id")
    p_nb.set_defaults(func=cmd_neighbors)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
