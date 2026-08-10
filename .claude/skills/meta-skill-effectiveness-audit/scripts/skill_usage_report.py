#!/usr/bin/env python3
"""Aggregate skill/agent/command invocation counts and attributed token cost
from Claude Code session transcripts (~/.claude/projects/*/*.jsonl).

Usage:
    skill_usage_report.py [--projects-dir DIR] [--project SLUG] [--json] [--min-count N]

Attribution uses three ground-truth signals instead of forward windowing:

- Skill turns: the harness stamps each assistant message with
  `attributionSkill` while a skill is active (set by an explicit Skill tool
  call or by a slash command that maps to a skill). Turns are attributed to
  `skill:<name>` directly from that field — no invoke-to-invoke windowing,
  so there's no way for a skill's cost to bleed into unrelated later work.
- Agent/Task turns: an Agent/Task tool_use's paired tool_result carries
  `toolUseResult.totalTokens`, the subagent's own self-reported total cost.
  That lump sum is attributed to `agent:<subagent_type>` directly, decoupled
  from whatever the parent transcript does afterward (subagent-internal
  turns never appear in the parent file at all).
- Everything else (plain slash commands with no backing skill, and any
  turn before the first invocation) falls back to windowing by
  `<command-name>` tag, since there's no ground-truth close signal for
  those — this window closes as soon as `attributionSkill` turns on, which
  covers most practical cases.
"""
import argparse
import glob
import json
import os
import re
from collections import defaultdict

COMMAND_RE = re.compile(r"<command-name>([^<]+)</command-name>")
SUBAGENT_TOKENS_RE = re.compile(r"subagent_tokens:\s*(\d+)")
TASK_NOTIFICATION_RE = re.compile(
    r"<tool-use-id>([^<]+)</tool-use-id>.*<usage>\s*<subagent_tokens>(\d+)</subagent_tokens>",
    re.DOTALL,
)


def task_notification_text(d):
    """Return the raw <task-notification> string for this event, if it is one.

    Only the two structural shapes the harness actually emits qualify — a
    top-level queue-operation event, or a "user"-type event whose message
    content is a bare string (the harness's duplicate delivery of the same
    notification). Anything else — assistant prose, system-reminders, tool
    output — that merely quotes notification-shaped text must not match.
    """
    if d.get("type") == "queue-operation":
        content = d.get("content")
        if isinstance(content, str) and content.startswith("<task-notification>"):
            return content
    elif d.get("type") == "user":
        content = d.get("message", {}).get("content")
        if isinstance(content, str) and content.startswith("<task-notification>"):
            return content
    return None


def agent_result_tokens(result_event):
    """Extract a subagent's self-reported total token cost from its tool_result."""
    tur = result_event.get("toolUseResult")
    if isinstance(tur, dict) and isinstance(tur.get("totalTokens"), (int, float)):
        return tur["totalTokens"]

    content = result_event.get("message", {}).get("content")
    text_chunks = []
    if isinstance(content, str):
        text_chunks.append(content)
    elif isinstance(content, list):
        for c in content:
            if isinstance(c, dict):
                if isinstance(c.get("content"), str):
                    text_chunks.append(c["content"])
                elif isinstance(c.get("text"), str):
                    text_chunks.append(c["text"])
    for chunk in text_chunks:
        m = SUBAGENT_TOKENS_RE.search(chunk)
        if m:
            return int(m.group(1))
    return 0


def attribute(path, stats, warnings):
    seen_msg_ids = set()
    pending_agents = {}  # tool_use_id -> "agent:<subagent_type>"
    current_command = "unattributed"
    prev_attribution_skill = None

    with open(path, errors="replace") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except ValueError as e:
                warnings.append(
                    {
                        "type": "parse_error",
                        "path": path,
                        "line": line_no,
                        "detail": str(e),
                    }
                )
                continue

            if pending_agents:
                notification = task_notification_text(d)
                if notification is not None:
                    m = TASK_NOTIFICATION_RE.search(notification)
                    if m:
                        label = pending_agents.pop(m.group(1), None)
                        if label is not None:
                            stats[label]["tokens"] += int(m.group(2))

            if d.get("type") == "user":
                text = d.get("message", {}).get("content")
                if isinstance(text, str):
                    m = COMMAND_RE.search(text)
                    if m:
                        current_command = "/" + m.group(1).lstrip("/")
                        stats[current_command]["count"] += 1

                tur = d.get("toolUseResult")
                if isinstance(tur, dict) and tur.get("isAsync"):
                    # Initial launch acknowledgment, not the real result —
                    # its cost arrives later via a <task-notification>.
                    continue

                content = d.get("message", {}).get("content")
                if isinstance(content, list):
                    for c in content:
                        if not isinstance(c, dict) or c.get("type") != "tool_result":
                            continue
                        label = pending_agents.pop(c.get("tool_use_id"), None)
                        if label is not None:
                            result_tokens = agent_result_tokens(d)
                            if result_tokens == 0:
                                warnings.append(
                                    {
                                        "type": "zero_token_agent_result",
                                        "path": path,
                                        "line": line_no,
                                        "detail": f"{label} tool_result at "
                                        f"{c.get('tool_use_id')} carried no "
                                        "extractable token count",
                                    }
                                )
                            stats[label]["tokens"] += result_tokens
                continue

            if d.get("type") != "assistant":
                continue
            msg = d.get("message", {})
            content = msg.get("content", [])
            for c in content:
                if not isinstance(c, dict) or c.get("type") != "tool_use":
                    continue
                name = c.get("name")
                inp = c.get("input", {}) or {}
                if name in ("Agent", "Task"):
                    sub = inp.get("subagent_type") or "unknown"
                    label = "agent:" + sub
                    if sub == "unknown":
                        warnings.append(
                            {
                                "type": "unknown_subagent_type",
                                "path": path,
                                "line": line_no,
                                "detail": f"tool_use {c.get('id')} had no "
                                "subagent_type in its input",
                            }
                        )
                    stats[label]["count"] += 1
                    if c.get("id"):
                        pending_agents[c["id"]] = label

            attribution_skill = d.get("attributionSkill")
            if attribution_skill and attribution_skill != prev_attribution_skill:
                stats["skill:" + attribution_skill]["count"] += 1
            prev_attribution_skill = attribution_skill
            label = "skill:" + attribution_skill if attribution_skill else current_command

            msg_id = msg.get("id")
            if not msg_id or msg_id in seen_msg_ids:
                continue
            seen_msg_ids.add(msg_id)
            usage = msg.get("usage") or {}
            tokens = usage.get("output_tokens", 0) + usage.get(
                "cache_creation_input_tokens", 0
            )
            stats[label]["tokens"] += tokens

    for tool_use_id, label in pending_agents.items():
        warnings.append(
            {
                "type": "unresolved_async_agent",
                "path": path,
                "line": None,
                "detail": f"{label} ({tool_use_id}) never got a matching "
                "tool_result or task-notification — likely a background "
                "agent still running (or killed) when the transcript ends; "
                "its cost is missing, not zero",
            }
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--projects-dir", default=os.path.expanduser("~/.claude/projects")
    )
    ap.add_argument("--project", help="only this project slug (dir under projects-dir)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--min-count", type=int, default=1)
    args = ap.parse_args()

    root = args.projects_dir
    if args.project:
        pattern = os.path.join(root, args.project, "*.jsonl")
    else:
        pattern = os.path.join(root, "*", "*.jsonl")

    stats = defaultdict(lambda: {"count": 0, "tokens": 0})
    warnings = []
    for path in glob.glob(pattern):
        attribute(path, stats, warnings)

    rows = [
        (label, v["count"], v["tokens"], v["tokens"] // max(v["count"], 1))
        for label, v in stats.items()
        if v["count"] >= args.min_count
    ]
    rows.sort(key=lambda r: r[2], reverse=True)

    if args.json:
        print(
            json.dumps(
                {
                    "rows": [
                        {"label": l, "count": c, "total_tokens": t, "avg_tokens": a}
                        for l, c, t, a in rows
                    ],
                    "warnings": warnings,
                },
                indent=2,
            )
        )
        return

    print(f"{'label':<45} {'count':>6} {'total_tokens':>14} {'avg/invoke':>12}")
    for label, count, tokens, avg in rows:
        print(f"{label:<45} {count:>6} {tokens:>14,} {avg:>12,}")

    if warnings:
        by_type = defaultdict(list)
        for w in warnings:
            by_type[w["type"]].append(w)
        print(f"\n{len(warnings)} warning(s):")
        for wtype, items in sorted(by_type.items(), key=lambda kv: -len(kv[1])):
            print(f"  {wtype} ({len(items)}):")
            for w in items[:5]:
                loc = f"{w['path']}:{w['line']}" if w.get("line") else w["path"]
                print(f"    {loc} — {w['detail']}")
            if len(items) > 5:
                print(f"    ... and {len(items) - 5} more")


if __name__ == "__main__":
    main()
