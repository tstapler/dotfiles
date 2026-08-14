#!/usr/bin/env python3
"""Aggregate Claude Code token usage per project/session from local transcripts.

Reads ~/.claude/projects/**/*.jsonl (every Claude Code session on this
machine), sums token usage by project and model over a trailing window, and
applies Anthropic list pricing to estimate $ spend. Useful for a per-project
breakdown when your org's own usage dashboard only reports an aggregate total.

Pricing is Anthropic first-party list price, not necessarily what you're
actually billed (enterprise/negotiated rates may differ) -- treat $ figures
here as an estimate for relative comparison across projects, not a
reconciled invoice.
"""

import argparse
import glob
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone

CLAUDE_PROJECTS_DIR = os.path.expanduser("~/.claude/projects")

# Anthropic list pricing, $ per 1M tokens: (input, output).
# Sonnet 5 intro pricing runs through 2026-08-31; after that it reverts to
# $3/$15. Source: claude-api skill, cached 2026-06-24.
PRICING = {
    "claude-sonnet-5": (2.00, 10.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-fable-5": (10.00, 50.00),
}

# Cache write/read cost as a multiplier of the model's own input rate.
# Source: claude-api skill's prompt-caching reference.
CACHE_WRITE_5M_MULT = 1.25
CACHE_WRITE_1H_MULT = 2.0
CACHE_READ_MULT = 0.1

# Worktree dir names under ~/.stapler-squad/workspaces/*/worktrees/ don't
# consistently prefix or suffix the project slug (e.g. "pr-479-compute-nop"
# vs "corp-compute-nop-pr-479"), so collapse them by substring match against
# slugs seen in this user's real (non-worktree) repo checkouts instead of
# trying to parse a naming convention that doesn't exist.
KNOWN_PROJECT_SLUGS = [
    "stapler-squad",
    "docspan",
    "stelekit",
    "design-docs",
    "compute-nop",
    "tn-titus-kube-config",
    "tn-titus-static-infra-tf",
    "traffic-capacitron",
    "traffic-reservations",
    "tn-compute-runbooks",
    "consolette",
    "stapler-mcp",
    "kibitzer",
    "ngp-skills",
    "aimee-dash",
    "aimee",
    "dotfiles",
]


# Canonical repo-root patterns. A session's cwd can be any subdirectory of a
# checkout (not just its root), so match on the root and drop everything
# after it -- matching on basename alone mislabels e.g.
# ~/ws/ngp-skills/plugins/.../skills/slack-interactions as project
# "slack-interactions" instead of rolling it up into "ngp-skills".
REPO_ROOT_PATTERNS = [
    re.compile(r"/\.stapler-squad/repos/[^/]+/[^/]+/([^/]+)"),
    re.compile(r"/code/[^/]+/[^/]+/([^/]+)"),
    re.compile(r"/ws/([^/]+)"),
    re.compile(r"/Documents/([^/]+)"),
]


def project_label(cwd):
    if not cwd:
        return "(unknown)"
    m = re.search(r"/\.stapler-squad/workspaces/[^/]+/worktrees/([^/]+)", cwd)
    if m:
        name = re.sub(r"_[0-9a-f]{10,}$", "", m.group(1))
        candidates = [s for s in KNOWN_PROJECT_SLUGS if s in name]
        if candidates:
            return "stapler-squad: " + max(candidates, key=len)
        if name.startswith("triage-"):
            return "stapler-squad: triage"
        return "stapler-squad: " + name + " (uncategorized)"
    if "/.aimee/workspace" in cwd:
        return "aimee (ops/journal)"
    if re.search(r"/dotfiles(/|$)", cwd):
        return "dotfiles"
    for pattern in REPO_ROOT_PATTERNS:
        m = pattern.search(cwd)
        if m:
            return m.group(1)
    if cwd.rstrip("/") == "/Users/tstapler":
        return "(home dir, no project)"
    return os.path.basename(cwd.rstrip("/"))


def load_usage(days):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    # project -> model -> token-type -> count
    agg = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    files = glob.glob(os.path.join(CLAUDE_PROJECTS_DIR, "**", "*.jsonl"), recursive=True)
    for path in files:
        try:
            with open(path, errors="ignore") as f:
                for line in f:
                    if '"type":"assistant"' not in line and '"type": "assistant"' not in line:
                        continue
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    if d.get("type") != "assistant":
                        continue
                    msg = d.get("message") or {}
                    model = msg.get("model")
                    usage = msg.get("usage")
                    if not usage or not model or model == "<synthetic>":
                        continue
                    ts = d.get("timestamp")
                    if not ts:
                        continue
                    try:
                        t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except Exception:
                        continue
                    if t < cutoff:
                        continue
                    label = project_label(d.get("cwd"))
                    bucket = agg[label][model]
                    bucket["input"] += usage.get("input_tokens", 0)
                    bucket["output"] += usage.get("output_tokens", 0)
                    cc = usage.get("cache_creation") or {}
                    bucket["cache_write_1h"] += cc.get("ephemeral_1h_input_tokens", 0)
                    bucket["cache_write_5m"] += cc.get("ephemeral_5m_input_tokens", 0)
                    bucket["cache_read"] += usage.get("cache_read_input_tokens", 0)
        except Exception:
            continue
    return agg


def estimate_cost(model, tok):
    rates = PRICING.get(model)
    if not rates:
        return None
    in_rate, out_rate = rates
    cost = tok["input"] / 1e6 * in_rate
    cost += tok["output"] / 1e6 * out_rate
    cost += tok["cache_write_1h"] / 1e6 * in_rate * CACHE_WRITE_1H_MULT
    cost += tok["cache_write_5m"] / 1e6 * in_rate * CACHE_WRITE_5M_MULT
    cost += tok["cache_read"] / 1e6 * in_rate * CACHE_READ_MULT
    return cost


def total_tokens(tok):
    return (
        tok["input"] + tok["output"] + tok["cache_write_1h"] + tok["cache_write_5m"] + tok["cache_read"]
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=28, help="trailing window in days (default 28, matches go/aipi)")
    ap.add_argument("--top", type=int, default=20, help="max projects to show (default 20)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a text report")
    ap.add_argument("--details", help="print per-model/token-type cost breakdown for one project label")
    args = ap.parse_args()

    agg = load_usage(args.days)

    if args.details:
        models = agg.get(args.details)
        if not models:
            print(f"no data for project label {args.details!r}")
            return
        for model, tok in models.items():
            rates = PRICING.get(model)
            print(f"model={model} rates={rates}")
            for k, v in tok.items():
                rate = 0.0
                if rates:
                    in_rate = rates[0]
                    if k == "input":
                        rate = in_rate
                    elif k == "output":
                        rate = rates[1]
                    elif k == "cache_write_1h":
                        rate = in_rate * CACHE_WRITE_1H_MULT
                    elif k == "cache_write_5m":
                        rate = in_rate * CACHE_WRITE_5M_MULT
                    elif k == "cache_read":
                        rate = in_rate * CACHE_READ_MULT
                print(f"  {k:<16} {v:>14,} tokens  ${v / 1e6 * rate:>10,.2f}")
        return

    rows = []
    unpriced_models = set()
    for label, models in agg.items():
        proj_cost = 0.0
        proj_tokens = 0
        proj_models = {}
        for model, tok in models.items():
            cost = estimate_cost(model, tok)
            if cost is None:
                unpriced_models.add(model)
                cost = 0.0
            proj_cost += cost
            proj_tokens += total_tokens(tok)
            proj_models[model] = {"tokens": total_tokens(tok), "cost": cost}
        rows.append({"project": label, "cost": proj_cost, "tokens": proj_tokens, "models": proj_models})

    rows.sort(key=lambda r: r["cost"], reverse=True)
    grand_cost = sum(r["cost"] for r in rows)
    grand_tokens = sum(r["tokens"] for r in rows)

    if args.json:
        print(json.dumps({"days": args.days, "total_cost": grand_cost, "total_tokens": grand_tokens, "projects": rows}, indent=2))
        return

    print(f"Token spend estimate, last {args.days} days ({len(rows)} projects, {grand_tokens:,} tokens)")
    print(f"Estimated total: ${grand_cost:,.2f} (Anthropic list price, not a reconciled bill)")
    if unpriced_models:
        print(f"Unpriced models seen (excluded from $ but counted in tokens if 0): {sorted(unpriced_models)}")
    print()
    print(f"{'Project':<45} {'Est $':>10} {'Tokens':>14} {'% of total':>10}")
    print("-" * 82)
    for r in rows[: args.top]:
        pct = (r["cost"] / grand_cost * 100) if grand_cost else 0
        print(f"{r['project']:<45} {r['cost']:>10,.2f} {r['tokens']:>14,} {pct:>9.1f}%")
    if len(rows) > args.top:
        rest_cost = sum(r["cost"] for r in rows[args.top :])
        rest_tokens = sum(r["tokens"] for r in rows[args.top :])
        print(f"{'... ' + str(len(rows) - args.top) + ' more projects':<45} {rest_cost:>10,.2f} {rest_tokens:>14,}")


if __name__ == "__main__":
    main()
