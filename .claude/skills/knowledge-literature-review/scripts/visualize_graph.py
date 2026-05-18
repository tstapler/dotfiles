#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
Generate citation graph visualizations.

Usage:
  uv run visualize_graph.py html [--top N] > /tmp/graph.html
  uv run visualize_graph.py dot [--top N] > /tmp/graph.dot
  uv run visualize_graph.py gephi [--top N] > /tmp/graph.gexf

Then view:
  open /tmp/graph.html               # Interactive D3.js in browser
  dot -Tsvg /tmp/graph.dot > g.svg   # Render with Graphviz (brew install graphviz)
  # Import graph.gexf into Gephi for advanced analysis

Environment:
  LITERATURE_DIR  Storage directory (default: ~/Documents/personal-wiki/literature/)
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path


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


def get_top_papers(papers: dict, n: int) -> set[str]:
    """Return IDs of top N papers by in-corpus citation count."""
    in_degrees: dict[str, int] = defaultdict(int)
    corpus = set(papers.keys())
    for pid, paper in papers.items():
        for ref in paper.get("references", []):
            if ref in corpus:
                in_degrees[ref] += 1
    ranked = sorted(papers.keys(), key=lambda p: (in_degrees.get(p, 0), papers[p].get("citation_count", 0)), reverse=True)
    return set(ranked[:n])


def build_subgraph(papers: dict, allowed: set[str]) -> list[dict]:
    edges = []
    for pid in allowed:
        for ref in papers[pid].get("references", []):
            if ref in allowed:
                edges.append({"from": pid, "to": ref})
    return edges


def short_title(title: str, max_len: int = 40) -> str:
    return title[:max_len] + "…" if len(title) > max_len else title


def cmd_html(args: argparse.Namespace) -> None:
    papers = load_all_papers()
    if not papers:
        print("No papers stored.", file=sys.stderr)
        sys.exit(1)

    allowed = get_top_papers(papers, args.top) if args.top < len(papers) else set(papers.keys())
    edges = build_subgraph(papers, allowed)

    nodes = []
    in_degrees: dict[str, int] = defaultdict(int)
    for e in edges:
        in_degrees[e["to"]] += 1

    for pid in allowed:
        p = papers[pid]
        nodes.append({
            "id": pid,
            "label": short_title(p.get("title", pid)),
            "title": p.get("title", ""),
            "year": p.get("year"),
            "venue": p.get("venue", ""),
            "url": p.get("url", ""),
            "citation_count": p.get("citation_count", 0),
            "in_degree": in_degrees.get(pid, 0),
            "size": max(5, min(30, 5 + in_degrees.get(pid, 0) * 3)),
        })

    graph_data = json.dumps({"nodes": nodes, "edges": edges})

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Literature Citation Graph ({len(nodes)} papers)</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  body {{ margin: 0; background: #1a1a2e; color: #eee; font-family: sans-serif; }}
  #info {{ position: fixed; top: 10px; right: 10px; width: 300px; background: rgba(0,0,0,0.8);
           padding: 12px; border-radius: 8px; font-size: 13px; display: none; }}
  #info a {{ color: #7eb8f7; }}
  #stats {{ position: fixed; top: 10px; left: 10px; background: rgba(0,0,0,0.6);
            padding: 8px 12px; border-radius: 6px; font-size: 12px; }}
  svg {{ width: 100vw; height: 100vh; }}
  .link {{ stroke: #444; stroke-opacity: 0.4; }}
  .node circle {{ cursor: pointer; stroke-width: 1.5; }}
  .node text {{ font-size: 10px; fill: #ccc; pointer-events: none; }}
</style>
</head>
<body>
<div id="stats">Papers: {len(nodes)} | Edges: {len(edges)}</div>
<div id="info"></div>
<svg></svg>
<script>
const data = {graph_data};
const svg = d3.select("svg");
const w = window.innerWidth, h = window.innerHeight;
const g = svg.append("g");
svg.call(d3.zoom().on("zoom", e => g.attr("transform", e.transform)));

const colorScale = d3.scaleSequential(d3.interpolateCool)
  .domain([d3.min(data.nodes, d => d.year || 2000), d3.max(data.nodes, d => d.year || 2024)]);

const sim = d3.forceSimulation(data.nodes)
  .force("link", d3.forceLink(data.edges).id(d => d.id).distance(80))
  .force("charge", d3.forceManyBody().strength(-200))
  .force("center", d3.forceCenter(w/2, h/2))
  .force("collision", d3.forceCollide(d => d.size + 4));

const link = g.append("g").selectAll("line").data(data.edges).join("line").attr("class","link");

const node = g.append("g").selectAll("g").data(data.nodes).join("g").attr("class","node")
  .call(d3.drag()
    .on("start", (e,d) => {{ if (!e.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; }})
    .on("drag", (e,d) => {{ d.fx=e.x; d.fy=e.y; }})
    .on("end", (e,d) => {{ if (!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }}));

node.append("circle")
  .attr("r", d => d.size)
  .attr("fill", d => colorScale(d.year || 2015))
  .attr("stroke", d => d.in_degree > 2 ? "#fff" : "#555")
  .on("click", (e, d) => {{
    const info = document.getElementById("info");
    info.style.display = "block";
    info.innerHTML = `<b>${{d.title}}</b><br>Year: ${{d.year}} | Venue: ${{d.venue || "?"}}<br>
      In-corpus cites: ${{d.in_degree}} | Total cites: ${{d.citation_count}}<br>
      <a href="${{d.url}}" target="_blank">arXiv ↗</a>`;
  }});

node.filter(d => d.in_degree > 1).append("text")
  .attr("dx", d => d.size + 2).attr("dy", 4)
  .text(d => d.label);

sim.on("tick", () => {{
  link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  node.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
}});
</script>
</body>
</html>"""
    print(html)


def cmd_dot(args: argparse.Namespace) -> None:
    papers = load_all_papers()
    if not papers:
        print("No papers stored.", file=sys.stderr)
        sys.exit(1)

    allowed = get_top_papers(papers, args.top) if args.top < len(papers) else set(papers.keys())
    edges = build_subgraph(papers, allowed)
    in_degrees: dict[str, int] = defaultdict(int)
    for e in edges:
        in_degrees[e["to"]] += 1

    lines = ["digraph literature {", "  rankdir=LR;", "  node [shape=box fontsize=10];"]
    for pid in allowed:
        p = papers[pid]
        label = short_title(p.get("title", pid), 35).replace('"', "'")
        year = p.get("year", "")
        size = max(0.3, min(2.0, 0.3 + in_degrees.get(pid, 0) * 0.2))
        lines.append(f'  "{pid}" [label="{label}\\n[{year}]" width={size:.1f} URL="{p.get("url","")}"];')
    for e in edges:
        lines.append(f'  "{e["from"]}" -> "{e["to"]}";')
    lines.append("}")
    print("\n".join(lines))


def cmd_gephi(args: argparse.Namespace) -> None:
    papers = load_all_papers()
    if not papers:
        print("No papers stored.", file=sys.stderr)
        sys.exit(1)

    allowed = get_top_papers(papers, args.top) if args.top < len(papers) else set(papers.keys())
    edges = build_subgraph(papers, allowed)

    id_map = {pid: str(i) for i, pid in enumerate(allowed)}
    nodes_xml = "\n".join(
        f'      <node id="{id_map[pid]}" label="{papers[pid].get("title","")[:60].replace(chr(34), chr(39))}">'
        f'<attvalues><attvalue for="0" value="{papers[pid].get("year","")}"/>'
        f'<attvalue for="1" value="{papers[pid].get("citation_count",0)}"/></attvalues></node>'
        for pid in allowed
    )
    edges_xml = "\n".join(
        f'      <edge id="{i}" source="{id_map[e["from"]]}" target="{id_map[e["to"]]}"/>'
        for i, e in enumerate(edges)
    )
    print(f"""<?xml version="1.0" encoding="UTF-8"?>
<gexf xmlns="http://gexf.net/1.3">
  <graph defaultedgetype="directed">
    <attributes class="node">
      <attribute id="0" title="year" type="integer"/>
      <attribute id="1" title="citation_count" type="integer"/>
    </attributes>
    <nodes>
{nodes_xml}
    </nodes>
    <edges>
{edges_xml}
    </edges>
  </graph>
</gexf>""")


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize literature citation graph")
    parser.add_argument("format", choices=["html", "dot", "gephi"])
    parser.add_argument("--top", type=int, default=100, help="Limit to top N papers (default: 100)")
    args = parser.parse_args()
    {"html": cmd_html, "dot": cmd_dot, "gephi": cmd_gephi}[args.format](args)


if __name__ == "__main__":
    main()
