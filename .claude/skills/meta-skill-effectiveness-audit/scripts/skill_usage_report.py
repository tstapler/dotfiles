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
import datetime
import glob
import json
import os
import re
import subprocess
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
                    sub = inp.get("subagent_type")
                    if not sub:
                        # The Agent tool's own default: omitting
                        # subagent_type runs the general-purpose agent —
                        # not missing data.
                        sub = "general-purpose" if name == "Agent" else "unknown"
                        if sub == "unknown":
                            warnings.append(
                                {
                                    "type": "unknown_subagent_type",
                                    "path": path,
                                    "line": line_no,
                                    "detail": f"tool_use {c.get('id')} ({name}) had "
                                    "no subagent_type in its input",
                                }
                            )
                    label = "agent:" + sub
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


def ledger_path():
    """XDG-cache location for the hardening ledger — not repo content, so it
    lives outside any git tree (see meta-persona-hardening's Step 6 handoff)."""
    xdg_cache = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
    return os.path.join(xdg_cache, "meta-skill-effectiveness-audit", "ledger.json")


def load_ledger():
    path = ledger_path()
    if not os.path.exists(path):
        return {}
    with open(path) as fh:
        return json.load(fh)


def save_ledger(ledger):
    path = ledger_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(ledger, fh, indent=2, sort_keys=True)


def git(*args, cwd):
    try:
        out = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
        )
        return out.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def git_commit_sha(path):
    """Commit SHA of the last commit touching this file — linkable/browsable,
    unlike a blob SHA (see CLAUDE.md's blob-vs-commit-SHA warning)."""
    abspath = os.path.abspath(path)
    return git("log", "-1", "--format=%H", "--", abspath, cwd=os.path.dirname(abspath))


def git_blob_hash(path):
    """Content hash of the file's current on-disk state — a local drift
    tripwire only, never surfaced as a link."""
    abspath = os.path.abspath(path)
    return git("hash-object", abspath, cwd=os.path.dirname(abspath))


def record_hardening(args, stats):
    if not (args.label and args.persona_file and args.incident):
        raise SystemExit(
            "--record-hardening requires --label, --persona-file, and --incident"
        )
    baseline = stats.get(args.label, {"count": 0, "tokens": 0})
    entry = {
        "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "persona_file": os.path.abspath(args.persona_file),
        "incident": args.incident,
        "commit_sha": git_commit_sha(args.persona_file),
        "blob_hash": git_blob_hash(args.persona_file),
        "baseline_count": baseline["count"],
        "baseline_tokens": baseline["tokens"],
        "baseline_avg": baseline["tokens"] // max(baseline["count"], 1),
    }
    ledger = load_ledger()
    ledger.setdefault(args.label, []).append(entry)
    save_ledger(ledger)
    print(f"Recorded hardening entry for {args.label} at {ledger_path()}")
    print(json.dumps(entry, indent=2))


def ledger_annotations(ledger, stats):
    """For each label with a ledger entry, compare its latest recorded
    baseline/blob-hash against current stats/on-disk state."""
    annotations = {}
    for label, entries in ledger.items():
        latest = entries[-1]
        current = stats.get(label, {"count": 0, "tokens": 0})
        current_avg = current["tokens"] // max(current["count"], 1)
        persona_file = latest["persona_file"]
        if os.path.exists(persona_file):
            current_blob = git_blob_hash(persona_file)
            drifted = current_blob is not None and current_blob != latest["blob_hash"]
        else:
            drifted = None  # file gone — can't compare, worth flagging distinctly
        annotations[label] = {
            "recorded_at": latest["recorded_at"],
            "persona_file": persona_file,
            "incident": latest["incident"],
            "commit_sha": latest["commit_sha"],
            "drifted": drifted,
            "baseline_avg": latest["baseline_avg"],
            "current_avg": current_avg,
            "avg_delta": current_avg - latest["baseline_avg"],
            "hardening_passes": len(entries),
        }
    return annotations


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--projects-dir", default=os.path.expanduser("~/.claude/projects")
    )
    ap.add_argument("--project", help="only this project slug (dir under projects-dir)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--min-count", type=int, default=1)
    ap.add_argument(
        "--record-hardening",
        action="store_true",
        help="record a ledger entry for a completed meta-persona-hardening pass "
        "instead of printing the usage report",
    )
    ap.add_argument("--label", help="attribution label the hardening targeted, e.g. agent:general-purpose")
    ap.add_argument("--persona-file", help="path to the persona/skill file that was hardened")
    ap.add_argument("--incident", help="the one/two-sentence Step 1 incident statement")
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

    if args.record_hardening:
        record_hardening(args, stats)
        return

    ledger = load_ledger()
    annotations = ledger_annotations(ledger, stats) if ledger else {}

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
                    "ledger": annotations,
                },
                indent=2,
            )
        )
        return

    print(f"{'label':<45} {'count':>6} {'total_tokens':>14} {'avg/invoke':>12}")
    for label, count, tokens, avg in rows:
        marker = ""
        if label in annotations:
            a = annotations[label]
            if a["drifted"] is None:
                marker = "  [ledger: persona file missing]"
            elif a["drifted"]:
                marker = "  [ledger: DRIFTED since hardening]"
            else:
                sign = "+" if a["avg_delta"] >= 0 else ""
                marker = f"  [ledger: {sign}{a['avg_delta']:,} avg/invoke vs baseline]"
        print(f"{label:<45} {count:>6} {tokens:>14,} {avg:>12,}{marker}")

    if annotations:
        print(f"\nHardening ledger ({ledger_path()}):")
        for label, a in annotations.items():
            print(f"  {label} — hardened {a['recorded_at']} ({a['hardening_passes']} pass(es))")
            print(f"    persona: {a['persona_file']}")
            if a["commit_sha"]:
                print(f"    commit:  {a['commit_sha']}")
            print(f"    incident: {a['incident']}")
            if a["drifted"] is None:
                print("    status: persona file no longer exists on disk")
            elif a["drifted"]:
                print("    status: persona file changed since hardening — re-verify the gate still holds")
            else:
                print(
                    f"    status: unchanged; avg/invoke {a['baseline_avg']:,} -> "
                    f"{a['current_avg']:,} ({a['avg_delta']:+,})"
                )

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
