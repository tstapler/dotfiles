#!/usr/bin/env python3
"""Resolve [N] citations in NotebookLM answers to Logseq-compatible footnotes.

Adapted from ArtemXTech/personal-os-skills for Logseq (~/PageName.md structure).
Unlike the Obsidian version, this uses footnote-style citations instead of
[[Page#^anchor]] block references, since Logseq uses ((block-uuid)) not ^anchors.

Usage:
  python3 resolve_citations.py --qa /tmp/nlm-answer.json --sources /tmp/nlm-sources.json
  python3 resolve_citations.py --qa /tmp/nlm-answer.json --sources /tmp/nlm-sources.json \
    --output /tmp/nlm-resolved.md --title "My Q&A"
"""
import argparse
import json
import re
import sys
from pathlib import Path


def load_sources(sources_file):
    with open(sources_file) as f:
        data = json.load(f)
    # nlm format: flat list [{id, title, type, url}]
    # old format: {sources: [{id, title, ...}]}
    sources = data if isinstance(data, list) else data.get("sources", [])
    return {s["id"]: s for s in sources if s.get("title") and len(s["title"].strip()) >= 3}


def load_qa(qa_file):
    with open(qa_file) as f:
        data = json.load(f)
    # nlm format: {value: {answer, references: [{source_id, citation_number, cited_text}]}}
    value = data.get("value", data)
    answer = value.get("answer", "")
    references = value.get("references", [])
    return answer, references


def build_citation_map(references, source_map):
    """Map citation number -> source title and cited text excerpt."""
    citations = {}
    for ref in references:
        num = ref.get("citation_number")
        source_id = ref.get("source_id", "")
        cited_text = ref.get("cited_text", "").strip()
        source = source_map.get(source_id, {})
        title = source.get("title", "Unknown Source").strip()
        url = source.get("url", "")
        if num is not None:
            citations[num] = {"title": title, "cited_text": cited_text, "url": url, "source_id": source_id}
    return citations


def handle_cross_source_citations(answer, references, source_map):
    """
    When all references share the same source_id (cross-source synthesis),
    try to match *"episode title"* markers in the answer to source titles.
    """
    if not references:
        return {}
    source_ids = {r.get("source_id") for r in references}
    if len(source_ids) > 1:
        return {}  # Multiple distinct sources — no remapping needed

    # All refs point to same source_id — try fuzzy title matching
    episode_pattern = re.compile(r'\*"([^"]+)"\*')
    episode_mentions = episode_pattern.findall(answer)
    if not episode_mentions:
        return {}

    remap = {}
    titles_by_id = {sid: s["title"] for sid, s in source_map.items()}

    for mention in episode_mentions:
        best_id, best_score = None, 0
        mention_lower = mention.lower()
        for sid, title in titles_by_id.items():
            # Simple overlap scoring
            words_mention = set(mention_lower.split())
            words_title = set(title.lower().split())
            score = len(words_mention & words_title) / max(len(words_mention), 1)
            if score > best_score and score > 0.4:
                best_score, best_id = score, sid
        if best_id:
            remap[mention] = source_map[best_id]["title"]

    return remap


def format_output(answer, citation_map, title=None):
    """Format answer with Logseq footnote-style citations."""
    lines = []

    if title:
        lines.append(f"# {title}\n")

    # Answer body — keep [N] markers inline
    lines.append(answer.strip())
    lines.append("")

    if not citation_map:
        return "\n".join(lines)

    # Footnotes section
    lines.append("---")
    lines.append("## Sources")
    lines.append("")

    for num in sorted(citation_map.keys()):
        info = citation_map[num]
        title_link = f"[[{info['title']}]]" if info["title"] != "Unknown Source" else info["title"]
        excerpt = info["cited_text"][:150].replace("\n", " ").strip()
        if len(info["cited_text"]) > 150:
            excerpt += "…"

        if info.get("url"):
            line = f"[{num}] {title_link} ([source]({info['url']}))"
        else:
            line = f"[{num}] {title_link}"

        if excerpt:
            line += f'\n    > "{excerpt}"'

        lines.append(line)
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Resolve NLM citations to Logseq footnotes")
    parser.add_argument("--qa", required=True, help="nlm query output JSON file")
    parser.add_argument("--sources", required=True, help="nlm source list JSON file")
    parser.add_argument("--output", help="Output markdown file (default: stdout)")
    parser.add_argument("--title", help="Title for the output page")
    args = parser.parse_args()

    source_map = load_sources(args.sources)
    answer, references = load_qa(args.qa)

    citation_map = build_citation_map(references, source_map)

    if not citation_map and references:
        print("Warning: cross-source synthesis detected — attempting title remapping", file=sys.stderr)
        handle_cross_source_citations(answer, references, source_map)

    output = format_output(answer, citation_map, title=args.title)

    if args.output:
        Path(args.output).write_text(output)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
