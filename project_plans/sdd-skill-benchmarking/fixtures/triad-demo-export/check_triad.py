"""Score one triad-demo-export run against truth.json.

Findings count only text the agents themselves produced (assistant text, Write/Edit
inputs), never tool results echoing the fixture files back, so a keyword in the plan
itself cannot score as a finding.
"""
import glob
import json
import os
import re

SKILL_NAME = "pm:triad-review"
REPAIR_DESC = re.compile(r"fix|repair|patch|address", re.I)
REREVIEW_DESC = re.compile(r"re-?review|triad|lens", re.I)


def _blocks(path):
    with open(path, errors="replace") as fh:
        for line in fh:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def collect(projects_dir):
    """Return (agent_text, triad_invocations, subagents, repair_agents, rereview_agents)."""
    texts, invocations, subagents, repairs, rereviews = [], 0, 0, 0, 0
    seen_tool_ids = set()  # persisted transcripts repeat a tool_use on every streamed line
    for path in glob.glob(os.path.join(projects_dir, "**", "*.jsonl"), recursive=True):
        is_sub = os.sep + "subagents" + os.sep in path
        if is_sub:
            subagents += 1
            meta = path[:-6] + ".meta.json"
            try:
                with open(meta) as fh:
                    if REPAIR_DESC.search(json.load(fh).get("description", "")):
                        repairs += 1
            except (OSError, ValueError):
                pass
        for ev in _blocks(path):
            if ev.get("type") != "assistant":
                continue
            for c in ev.get("message", {}).get("content") or []:
                if c.get("type") == "text":
                    texts.append(c["text"])
                elif c.get("type") == "tool_use" and c.get("id") not in seen_tool_ids:
                    seen_tool_ids.add(c.get("id"))
                    inp = c.get("input") or {}
                    if c.get("name") in ("Write", "Edit"):
                        texts.append(str(inp.get("content") or inp.get("new_string") or ""))
                    if c.get("name") == "Skill" and inp.get("skill") == SKILL_NAME:
                        invocations += 1
                    if c.get("name") in ("Agent", "Task") and REREVIEW_DESC.search(inp.get("description", "")):
                        rereviews += 1
    return "\n".join(texts), invocations, subagents, repairs, rereviews


def _read(workdir, rels):
    out = []
    for rel in rels:
        p = os.path.join(workdir, rel)
        if os.path.exists(p):
            with open(p, errors="replace") as fh:
                out.append(fh.read())
    return "\n".join(out)


def score(run_dir, workdir, truth_path):
    with open(truth_path) as fh:
        truth = json.load(fh)
    text, invocations, subagents, repairs, rereviews = collect(os.path.join(run_dir, "home", ".claude", "projects"))
    found, fixed = {}, {}
    for gap in truth["gaps"]:
        found[gap["id"]] = bool(re.search(gap["find"], text, re.I | re.S))
        if gap["severity"] == "blocker":
            body = _read(workdir, gap["fixed_in"])
            if "fixed_all" in gap:
                fixed[gap["id"]] = all(re.search(p, body, re.I) for p in gap["fixed_all"])
            else:
                fixed[gap["id"]] = bool(re.search(gap["fixed"], body, re.I))
    verdicts = re.findall(r"FINAL VERDICT:\s*\**\s*(READY TO BUILD|NEEDS WORK|NOT READY)", text)
    by_sev = {}
    for gap in truth["gaps"]:
        s = by_sev.setdefault(gap["severity"], [0, 0])
        s[1] += 1
        s[0] += found[gap["id"]]
    plan = _read(workdir, ["project_plans/demo-export/implementation/plan.md"])
    ux = _read(workdir, ["project_plans/demo-export/design/ux.md"])
    return {
        "found": found,
        "fixed_blockers": fixed,
        "found_by_severity": {k: f"{a}/{b}" for k, (a, b) in by_sev.items()},
        "blockers_found": sum(found[g["id"]] for g in truth["gaps"] if g["severity"] == "blocker"),
        "blockers_fixed": sum(fixed.values()),
        "gaps_found": sum(found.values()),
        "final_verdict": verdicts[-1] if verdicts else None,
        "triad_invocations": invocations,
        "review_rounds": (1 + rereviews) if invocations else 0,
        "subagents": subagents,
        "repair_agents": repairs,
        "plan_lines": plan.count("\n"),
        "ux_lines": ux.count("\n"),
        "success": all(fixed.values()),
    }
