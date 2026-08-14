#!/usr/bin/env python3
"""Parse a Claude Code transcript JSONL file and report where context tokens went.

Schema notes (empirically verified against a real transcript, not the generic
`{content: ...}` shape assumed by meta-context-engineering's context_analyzer.py):

- Each line is one JSON object with a top-level "type": mode, permission-mode,
  file-history-snapshot, user, assistant, attachment, system, last-prompt,
  ai-title, queue-operation.
- "user" and "assistant" lines carry the actual conversation: message.content
  is either a plain string (user text) or a list of blocks. Block "type" is
  one of: text, thinking, tool_use, tool_result, image.
- "attachment" lines carry side-channel data (hook output, deferred-tool
  deltas, task notifications) that count against context but aren't part of
  the visible conversation.
- Token estimate uses len(text)//4, the same rough heuristic Claude Code's own
  /context command and the meta-context-engineering skill use.
"""
import argparse
import json
import sqlite3
import sys
from collections import defaultdict


def estimate_tokens(text):
    if not isinstance(text, str):
        text = json.dumps(text)
    return len(text) // 4


def block_text(block):
    if isinstance(block, str):
        return block
    if not isinstance(block, dict):
        return json.dumps(block)
    t = block.get("type")
    if t == "text":
        return block.get("text", "")
    if t == "thinking":
        return block.get("thinking", "")
    if t == "tool_use":
        return json.dumps(block.get("input", {}))
    if t == "tool_result":
        content = block.get("content", "")
        if isinstance(content, list):
            return "".join(block_text(c) for c in content)
        return content if isinstance(content, str) else json.dumps(content)
    if t == "image":
        return ""
    return json.dumps(block)


def load(path):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def analyze(path):
    by_type = defaultdict(int)
    by_tool = defaultdict(int)
    by_tool_calls = defaultdict(int)
    thinking_tokens = 0
    text_tokens = 0
    tool_use_tokens = 0
    tool_result_tokens = 0
    attachment_tokens = 0
    largest = []  # (tokens, label)
    n_user = n_assistant = 0
    first_ts = last_ts = None
    last_usage = None

    for entry in load(path):
        etype = entry.get("type")
        ts = entry.get("timestamp")
        if ts:
            first_ts = first_ts or ts
            last_ts = ts

        if etype == "attachment":
            size = estimate_tokens(entry.get("attachment", {}))
            attachment_tokens += size
            by_type["attachment"] += size
            continue

        if etype not in ("user", "assistant"):
            by_type[etype] += estimate_tokens(entry)
            continue

        if etype == "user":
            n_user += 1
        else:
            n_assistant += 1
            usage = entry.get("message", {}).get("usage")
            # Each assistant turn's usage reflects the *entire* API call's
            # input (full context so far, not just what's new this turn), so
            # the last one in the transcript is the actual final context
            # size — summing across turns would double-count.
            if isinstance(usage, dict):
                last_usage = usage

        content = entry.get("message", {}).get("content")
        if isinstance(content, str):
            size = estimate_tokens(content)
            text_tokens += size
            by_type[etype] += size
            largest.append((size, f"{etype} text @ {ts}"))
            continue

        if not isinstance(content, list):
            continue

        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            size = estimate_tokens(block_text(block))
            by_type[etype] += size

            if btype == "thinking":
                thinking_tokens += size
            elif btype == "text":
                text_tokens += size
                largest.append((size, f"{etype} text @ {ts}"))
            elif btype == "tool_use":
                name = block.get("name", "unknown")
                tool_use_tokens += size
                by_tool[name] += size
                by_tool_calls[name] += 1
                largest.append((size, f"tool_use:{name} @ {ts}"))
            elif btype == "tool_result":
                # tool_result blocks live in "user" lines but represent the
                # preceding tool's output, so attribute to a synthetic bucket
                # rather than double counting under "user".
                tool_result_tokens += size
                largest.append((size, f"tool_result @ {ts}"))

    largest.sort(reverse=True)
    total = sum(by_type.values())

    actual_total_tokens = None
    usage_breakdown = None
    if last_usage:
        usage_breakdown = {
            "input": last_usage.get("input_tokens", 0),
            "output": last_usage.get("output_tokens", 0),
            "cache_creation": last_usage.get("cache_creation_input_tokens", 0),
            "cache_read": last_usage.get("cache_read_input_tokens", 0),
        }
        actual_total_tokens = sum(usage_breakdown.values())

    return {
        "total_estimated_tokens": total,
        "actual_total_tokens": actual_total_tokens,
        "usage_breakdown": usage_breakdown,
        "by_type": dict(by_type),
        "breakdown": {
            "thinking": thinking_tokens,
            "text": text_tokens,
            "tool_use_inputs": tool_use_tokens,
            "tool_results": tool_result_tokens,
            "attachments": attachment_tokens,
        },
        "by_tool": dict(sorted(by_tool.items(), key=lambda kv: -kv[1])),
        "by_tool_calls": dict(by_tool_calls),
        "message_counts": {"user": n_user, "assistant": n_assistant},
        "time_range": {"first": first_ts, "last": last_ts},
        "largest_items": largest[:15],
    }


def recommend(report):
    recs = []
    # Percentages stay on the chars/4 heuristic total: actual_total_tokens is
    # the *current* context size (last turn's usage), while this breakdown is
    # cumulative across the whole transcript including content already
    # pruned/compacted out — the two aren't on the same basis.
    total = report["total_estimated_tokens"] or 1
    b = report["breakdown"]

    if b["tool_results"] / total > 0.35:
        recs.append(
            "Tool results are %.0f%% of tracked tokens — the biggest single lever. "
            "Prefer Grep/Read with offset+limit over full-file reads, and pipe "
            "large command output to a file instead of stdout." % (100 * b["tool_results"] / total)
        )
    if b["thinking"] / total > 0.15:
        recs.append(
            "Thinking blocks are %.0f%% of tracked tokens. These are pruned by "
            "Claude Code's own context editing on compaction, but a lower "
            "reasoning-effort setting reduces them proactively." % (100 * b["thinking"] / total)
        )
    if b["attachments"] / total > 0.10:
        recs.append(
            "Attachments (hook output, deferred-tool deltas, task notifications) "
            "are %.0f%% of tracked tokens. Check for hooks returning verbose "
            "stdout on every turn." % (100 * b["attachments"] / total)
        )
    top_tools = list(report["by_tool"].items())[:3]
    if top_tools:
        parts = ", ".join(f"{name} ({tok}t across {report['by_tool_calls'][name]} calls)" for name, tok in top_tools)
        recs.append(f"Heaviest tools by token cost: {parts}.")
    if not recs:
        recs.append("No single category dominates — context usage looks evenly spread.")
    return recs


def store_sqlite(report, db_path, session_id, trigger, transcript_path):
    """Append one row to the compactions table, matching cmdcrush/rtk's
    single-shared-WAL-db pattern (~/.claude/context-audit/trend.db)."""
    conn = sqlite3.connect(db_path, timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS compactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                trigger TEXT NOT NULL,
                transcript_path TEXT NOT NULL,
                total_estimated_tokens INTEGER NOT NULL,
                thinking_tokens INTEGER NOT NULL,
                text_tokens INTEGER NOT NULL,
                tool_use_tokens INTEGER NOT NULL,
                tool_result_tokens INTEGER NOT NULL,
                attachment_tokens INTEGER NOT NULL,
                top_tools TEXT NOT NULL,
                actual_total_tokens INTEGER
            )
            """
        )
        try:
            conn.execute("ALTER TABLE compactions ADD COLUMN actual_total_tokens INTEGER")
        except sqlite3.OperationalError:
            pass  # column already exists on a DB created before this field was added

        breakdown = report["breakdown"]
        top_tools = json.dumps(list(report["by_tool"].items())[:3])
        conn.execute(
            """
            INSERT INTO compactions (
                timestamp, session_id, trigger, transcript_path,
                total_estimated_tokens, thinking_tokens, text_tokens,
                tool_use_tokens, tool_result_tokens, attachment_tokens, top_tools,
                actual_total_tokens
            ) VALUES (datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                trigger,
                transcript_path,
                report["total_estimated_tokens"],
                breakdown.get("thinking", 0),
                breakdown.get("text", 0),
                breakdown.get("tool_use_inputs", 0),
                breakdown.get("tool_results", 0),
                breakdown.get("attachments", 0),
                top_tools,
                report.get("actual_total_tokens"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("transcript")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--sqlite", metavar="DB_PATH", help="also record this run to a compactions table in a SQLite trend db")
    parser.add_argument("--session-id", default="unknown")
    parser.add_argument("--trigger", default="manual")
    args = parser.parse_args()

    path = args.transcript
    as_json = args.as_json

    report = analyze(path)
    report["recommendations"] = recommend(report)

    if args.sqlite:
        store_sqlite(report, args.sqlite, args.session_id, args.trigger, path)

    if as_json:
        print(json.dumps(report, indent=2))
        return

    print(f"Transcript: {path}")
    print(f"Messages: {report['message_counts']['user']} user / {report['message_counts']['assistant']} assistant")
    print(f"Time range: {report['time_range']['first']} -> {report['time_range']['last']}")
    if report.get("actual_total_tokens") is not None:
        ub = report["usage_breakdown"]
        print(f"\nActual tokens (from usage, last assistant turn): {report['actual_total_tokens']}")
        print(f"  input={ub['input']} output={ub['output']} cache_creation={ub['cache_creation']} cache_read={ub['cache_read']}")
    else:
        print("\nActual tokens: unavailable (no assistant usage data in transcript)")
    print(f"Estimated tokens (chars/4 heuristic, category breakdown below): {report['total_estimated_tokens']}")
    print("\nBreakdown:")
    for k, v in report["breakdown"].items():
        print(f"  {k:20s} {v:>8d}")
    print("\nTop tools by token cost:")
    for name, tok in list(report["by_tool"].items())[:10]:
        print(f"  {name:30s} {tok:>8d}  ({report['by_tool_calls'][name]} calls)")
    print("\nLargest individual items:")
    for tok, label in report["largest_items"][:10]:
        print(f"  {tok:>8d}  {label}")
    print("\nRecommendations:")
    for r in report["recommendations"]:
        print(f"  - {r}")


if __name__ == "__main__":
    main()
