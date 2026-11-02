#!/usr/bin/env python3
"""Per-phase token, cache, cost and wall-clock report for Claude Code sessions.

Unlike skill_usage_report.py (output + cache-creation tokens only, subagents as
a lump sum), this reads the per-turn usage in each subagent's own transcript
(<session>/subagents/agent-*.jsonl), so it sees every bucket including cache
reads, plus timestamps for wall-clock and parallelism.

Usage:
    phase_cost_report.py [SESSION.jsonl ...] [--prefix sdd:] [--json]
    (no sessions given: discover sessions under ~/.claude/projects that mention --prefix)

Phase label of a turn = its own `attributionSkill`, else the label of the turn
that spawned its subagent, else (main thread) the last skill seen since the most
recent human prompt (a skill window ends at the next human prompt). Labels
reached by inheritance are reported as an `inherited` share so you can judge
how much to trust a row.

$ cost uses per-model rates fitted by least squares to the `cost-state`
events (actual billed totals per model) across the sessions given, so no price
is hard-coded. The calibration section shows how well bucket sums reproduce
those billed totals; trust cost columns only when the residual is small.
"""
import argparse
import datetime
import glob
import json
import mmap
import os
from collections import defaultdict

import re

import numpy as np

# /sdd:full runs a phase by Reading its file, so attributionSkill never marks the switch.
PHASE_READ_RE = re.compile(r"sdd/(?:skills/)?(\d-[a-z]+|full|quick|fix-bug|fix-hotspot)(?:/SKILL)?\.md$")

BUCKETS = ("input", "cache_read", "cache_write", "output")


IDLE_CAP_S = 300  # sessions get resumed hours later; don't count idle gaps as work


def active_seconds(spans):
    """Union of [t0, t1] spans, with gaps over IDLE_CAP_S contributing nothing."""
    total, end = 0.0, None
    for t0, t1 in sorted(spans):
        if end is None:
            total += t1 - t0
        elif t0 > end:
            total += min(t0 - end, IDLE_CAP_S) + (t1 - t0)
        elif t1 > end:
            total += t1 - end
        end = t1 if end is None else max(end, t1)
    return total


def parse_ts(s):
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def read_events(path):
    """Yield assistant events and the last cost-state event, skipping blob lines."""
    cost_state = None
    with open(path, "rb") as fh:
        for raw in fh:
            if b'"type":"assistant"' in raw:
                try:
                    d = json.loads(raw)
                except ValueError:
                    continue
                if d.get("type") == "assistant":
                    yield d
            elif b'"role":"user","content":"' in raw and b'"kind":"human"' in raw:
                try:
                    d = json.loads(raw)
                except ValueError:
                    continue
                origin = d.get("origin")
                if d.get("type") == "user" and isinstance(origin, dict) and origin.get("kind") == "human":
                    yield {"type": "human-prompt"}
            elif b'"type":"cost-state"' in raw:
                try:
                    cost_state = json.loads(raw)
                except ValueError:
                    pass
    if cost_state is not None:
        yield cost_state


def usage_buckets(msg):
    u = msg.get("usage") or {}
    return {
        "input": u.get("input_tokens", 0),
        "cache_read": u.get("cache_read_input_tokens", 0),
        "cache_write": u.get("cache_creation_input_tokens", 0),
        "output": u.get("output_tokens", 0),
    }


class Turn:
    __slots__ = ("model", "buckets", "t0", "t1", "label", "agent_file", "inherited", "raw")

    def __init__(self, model, buckets, ts, label, agent_file, inherited):
        self.model, self.buckets = model, dict(buckets)
        self.t0 = self.t1 = ts
        self.label, self.agent_file, self.inherited = label, agent_file, inherited
        self.raw = None

    def merge(self, buckets, ts):
        # Streaming writes one line per content block with the same message id;
        # the largest value seen per bucket is the final usage.
        for k, v in buckets.items():
            self.buckets[k] = max(self.buckets[k], v)
        self.t0, self.t1 = min(self.t0, ts), max(self.t1, ts)


def load_file(path, agent_file, spawn_label, spawns, turns, by_msg):
    """Parse one transcript. spawns maps Agent tool_use id -> label of emitting turn."""
    last_skill = None
    cost_state = None
    for d in read_events(path):
        if d.get("type") == "cost-state":
            cost_state = d
            continue
        if d.get("type") == "human-prompt":
            if agent_file is None:  # a subagent's one prompt is its brief, not a window end
                last_skill = None
            continue
        msg = d.get("message", {})
        mid = msg.get("id")
        if not mid or not d.get("timestamp"):
            continue
        ts = parse_ts(d["timestamp"])
        buckets = usage_buckets(msg)
        key = (agent_file, mid)
        existing = by_msg.get(key)
        if existing:
            existing.merge(buckets, ts)
            label = existing.label
        else:
            own = d.get("attributionSkill")
            if own:
                label, inherited = own, False
                last_skill = own
            elif last_skill:
                label, inherited = last_skill, True
            elif agent_file is not None and spawn_label:
                label, inherited = spawn_label, True
            else:
                label, inherited = "(none)", False
            t = Turn(msg.get("model", "?"), buckets, ts, label, agent_file, inherited)
            by_msg[key] = t
            turns.append(t)
        for c in msg.get("content") or []:
            if not (isinstance(c, dict) and c.get("type") == "tool_use"):
                continue
            if c.get("name") in ("Agent", "Task"):
                spawns[c["id"]] = label
            elif c.get("name") == "Skill" and (c.get("input") or {}).get("skill"):
                last_skill = c["input"]["skill"]
            elif c.get("name") == "Read":
                m = PHASE_READ_RE.search((c.get("input") or {}).get("file_path", ""))
                if m:
                    last_skill = "sdd:" + m.group(1)
    return cost_state


def load_session(path):
    turns, by_msg, spawns = [], {}, {}
    cost_state = load_file(path, None, None, spawns, turns, by_msg)
    sub_dir = path[: -len(".jsonl")] + "/subagents"
    files = sorted(glob.glob(os.path.join(sub_dir, "agent-*.jsonl")))
    metas = {}
    for f in files:
        try:
            with open(f[: -len(".jsonl")] + ".meta.json") as fh:
                metas[f] = json.load(fh)
        except (OSError, ValueError):
            metas[f] = {}
    # Subagents can spawn subagents; resolve in passes until no new spawn ids appear.
    pending = list(files)
    for _ in range(6):
        progress, rest = False, []
        for f in pending:
            tid = metas[f].get("toolUseId")
            if tid is not None and tid not in spawns:
                rest.append(f)
                continue
            load_file(f, f, spawns.get(tid), spawns, turns, by_msg)
            progress = True
        pending = rest
        if not pending or not progress:
            break
    for f in pending:  # orphans: spawner never seen (e.g. compacted away)
        load_file(f, f, "(orphan-subagent)", spawns, turns, by_msg)
    return turns, cost_state


def scale_to_billed(turns, cost_state):
    """Transcript input/output tokens are stream-start partials (input ~2/turn, output
    ~0.2x billed), but cache buckets match billed within ~15%. Scale input and output
    uniformly per model so totals match cost-state. INFERRED: assumes the undercount is
    proportional across phases. Raw sums are kept in `raw` for the calibration table."""
    usage = cost_state.get("modelUsage") or {}
    for model, mu in usage.items():
        mine = defaultdict(int)
        for t in turns:
            if t.model == model:
                for k in BUCKETS:
                    mine[k] += t.buckets[k]
        for k, billed in (("input", mu.get("inputTokens", 0)), ("output", mu.get("outputTokens", 0))):
            if mine[k]:
                f = billed / mine[k]
                for t in turns:
                    if t.model == model:
                        t.raw = getattr(t, "raw", None) or dict(t.buckets)
                        t.buckets[k] = t.buckets[k] * f


def reconciles(billed, got):
    """Cache buckets within 0.6-1.5x of billed. Sessions outside that (forks, resumed
    runs whose cost-state is cumulative) would poison the rate fit."""
    for i in (1, 2):
        if billed[i] and not 0.6 <= got[i] / billed[i] <= 1.5:
            return False
    return True


MAX_FIT_RESIDUAL = 0.25
MIN_FIT_COST_USD = 1.0


def fit_rates(samples):
    """samples: model -> list of (billed bucket vector, billed USD). Returns
    model -> (coef $/token, median |pred/billed-1|, n). Relative-error weights keep the
    huge sessions from drowning the small ones; non-negativity by active-set elimination.
    Rates are predictive, not individually interpretable (output is ~3% of cost, so its
    rate is poorly identified)."""
    rates = {}
    for model, rows in samples.items():
        rows = [r for r in rows if r[1] >= MIN_FIT_COST_USD]
        if len(rows) < 2 * len(BUCKETS):
            continue
        X = np.array([r[0] for r in rows], dtype=float) / 1e6
        y = np.array([r[1] for r in rows], dtype=float)
        A, b = X / y[:, None], np.ones(len(y))
        active = list(range(len(BUCKETS)))
        for _ in range(len(BUCKETS)):
            c, *_ = np.linalg.lstsq(A[:, active], b, rcond=None)
            if (c >= 0).all():
                break
            active = [a for a, v in zip(active, c) if v >= 0]
        coef = np.zeros(len(BUCKETS))
        coef[active] = c
        err = float(np.median(np.abs(X @ coef / y - 1)))
        rates[model] = (coef / 1e6, err, len(rows))
    return rates


def discover(prefix, root):
    needle = f'"attributionSkill":"{prefix}'.encode()
    out = []
    for p in glob.glob(os.path.join(root, "*", "*.jsonl")):
        try:
            with open(p, "rb") as fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                if mm.find(needle) != -1:
                    out.append(p)
        except (OSError, ValueError):
            continue
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sessions", nargs="*")
    ap.add_argument("--prefix", default="sdd:")
    ap.add_argument("--projects-dir", default=os.path.expanduser("~/.claude/projects"))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--json-out", help="also write the JSON report to this file")
    args = ap.parse_args()

    sessions = args.sessions or discover(args.prefix, args.projects_dir)
    all_turns, samples, calib = [], defaultdict(list), []
    for p in sessions:
        turns, cs = load_session(p)
        all_turns += [(p, t) for t in turns]
        if cs:
            scale_to_billed(turns, cs)
            mine = defaultdict(lambda: dict.fromkeys(BUCKETS, 0))
            for t in turns:
                for k in BUCKETS:
                    mine[t.model][k] += (t.raw or t.buckets)[k]
            for model, mu in (cs.get("modelUsage") or {}).items():
                billed = [mu.get("inputTokens", 0), mu.get("cacheReadInputTokens", 0),
                          mu.get("cacheCreationInputTokens", 0), mu.get("outputTokens", 0)]
                got = [mine[model][k] for k in BUCKETS]
                calib.append((p, model, billed, got))
                samples[model].append((billed, mu.get("costUSD", 0.0)))
    rates = fit_rates(samples)

    def cost(model, b):
        if model not in rates or rates[model][1] > MAX_FIT_RESIDUAL:
            return None
        return float(np.dot(rates[model][0], [b["input"], b["cache_read"], b["cache_write"], b["output"]]))

    phases = defaultdict(lambda: {
        "turns": 0, "inherited": 0, "buckets": dict.fromkeys(BUCKETS, 0), "cost": 0.0,
        "unpriced": 0, "agents": set(),
        "agent_spans": defaultdict(list), "sess_spans": defaultdict(list),
    })
    for p, t in all_turns:
        ph = phases[t.label]
        ph["turns"] += 1
        ph["inherited"] += t.inherited
        for k in BUCKETS:
            ph["buckets"][k] += t.buckets[k]
        c = cost(t.model, t.buckets)
        if c is None:
            ph["unpriced"] += 1
        else:
            ph["cost"] += c
        ph["sess_spans"][p].append((t.t0, t.t1))
        if t.agent_file:
            ph["agents"].add((p, t.agent_file))
            ph["agent_spans"][(p, t.agent_file)].append((t.t0, t.t1))

    rows = []
    for label, ph in phases.items():
        b = ph["buckets"]
        denom = b["input"] + b["cache_read"] + b["cache_write"]
        agent_secs = sum(active_seconds(v) for v in ph["agent_spans"].values())
        wall = sum(active_seconds(v) for v in ph["sess_spans"].values())
        rows.append({
            "phase": label, "sessions": len(ph["sess_spans"]), "turns": ph["turns"],
            "subagents": len(ph["agents"]), "inherited_share": ph["inherited"] / max(ph["turns"], 1),
            **b, "cache_hit": b["cache_read"] / denom if denom else 0.0,
            "cost_usd": ph["cost"], "unpriced_share": ph["unpriced"] / max(ph["turns"], 1),
            "wall_s": wall, "agent_s": agent_secs,
            "parallelism": agent_secs / wall if wall > 0 and agent_secs else None,
        })
    rows.sort(key=lambda r: -r["cost_usd"])

    cal = []
    for p, model, billed, got in calib:
        cal.append({"session": os.path.basename(p), "model": model,
                    "billed": dict(zip(BUCKETS, billed)), "mine": dict(zip(BUCKETS, got))})

    payload = {"phases": rows, "calibration": cal,
               "rates_per_mtok": {m: dict(zip(BUCKETS, (r[0] * 1e6).round(4).tolist()))
                                  for m, r in rates.items()}}
    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump(payload, fh, indent=1)
    if args.json:
        print(json.dumps({"phases": rows, "calibration": cal,
                          "rates_per_mtok": {m: dict(zip(BUCKETS, (r[0] * 1e6).round(4).tolist()))
                                             for m, r in rates.items()}}, indent=2))
        return

    print(f"{len(sessions)} session(s)\n")
    print(f"{'phase':<28}{'sess':>5}{'turns':>7}{'agents':>7}{'$cost':>9}{'cacheHit':>9}"
          f"{'out(M)':>8}{'wall(m)':>9}{'agent(m)':>9}{'par':>6}{'inh%':>6}{'unpr%':>6}")
    for r in rows:
        cost_s = f"{r['cost_usd']:.2f}" if r["cost_usd"] is not None else "n/a"
        par = f"{r['parallelism']:.1f}" if r["parallelism"] else "-"
        print(f"{r['phase']:<28}{r['sessions']:>5}{r['turns']:>7}{r['subagents']:>7}{cost_s:>9}"
              f"{r['cache_hit']*100:>8.0f}%{r['output']/1e6:>8.2f}{r['wall_s']/60:>9.1f}"
              f"{r['agent_s']/60:>9.1f}{par:>6}{r['inherited_share']*100:>5.0f}%{r['unpriced_share']*100:>5.0f}%")
    print("\nFitted $/MTok (input, cache_read, cache_write, output) | median |pred/billed-1| | n sessions")
    for m, (coef, resid, n) in rates.items():
        print(f"  {m}: {[round(float(c) * 1e6, 3) for c in coef]} | {resid*100:.1f}% | {n}")
    print("\nCalibration (raw transcript sums / billed), median over sessions; n = sessions used")
    by_model = defaultdict(lambda: defaultdict(list))
    for c in cal:
        for k in BUCKETS:
            if c["billed"][k]:
                by_model[c["model"]][k].append(c["mine"][k] / c["billed"][k])
    for m, d in by_model.items():
        med = {k: float(np.median(v)) for k, v in d.items()}
        print(f"  {m:<26}" + " ".join(f"{k}={med.get(k, float('nan')):.2f}" for k in BUCKETS)
              + f"  n={max(len(v) for v in d.values())}")
    print("  unpriced = turns on models without a fit under 25% median error (counted as $0).")


if __name__ == "__main__":
    main()
