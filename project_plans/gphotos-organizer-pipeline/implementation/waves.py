#!/usr/bin/env python3
"""Wave, collision and effort checker for implementation/plan.md (stdlib only).

Usage (from the repo root or anywhere):
    python3 project_plans/gphotos-organizer-pipeline/implementation/waves.py            # waves + merge order
    python3 project_plans/gphotos-organizer-pipeline/implementation/waves.py --check    # fail on any plan inconsistency
    python3 project_plans/gphotos-organizer-pipeline/implementation/waves.py --effort   # recompute the effort table

DEPS below is the authoritative dependency edge list. Rule: a story's wave is
1 + the maximum wave of its dependencies. `--check` fails when:
  * a story has no DEPS entry or DEPS names a story the plan lacks,
  * a story has no "**Depends on**" line (Story 10.5 may say "every other story"),
  * a story's "**Depends on**" line (first sentence, parentheticals removed) names a story that DEPS does not list as a direct edge,
  * DEPS lists a direct edge that the story's "**Depends on**" line omits (so plan and DEPS cannot drift in either direction),
  * two stories in the same wave list the same file in their story-level Files,
  * a story with more than MAX_TASK_FILES distinct files has a task without a
    "- Files:" line, or a task with more than MAX_TASK_FILES files.
"""
import collections
import pathlib
import re
import sys

PLAN = pathlib.Path(__file__).with_name("plan.md")
MAX_TASK_FILES = 5
MID = {"XS": 20, "S": 55, "M": 130, "L": 240}  # raw tokens (k) per task class, ESTIMATION.md midpoints
OUTPUT_SHARE = 0.12
VERIFY_SHARE = 0.75
VERIFY_OUTPUT = 0.06

DEPS = {
    "1.1": [],
    "1.2": ["1.11"], "1.3": ["1.2"], "1.4": ["1.1"], "1.5": ["1.3", "1.4"],
    "1.6": ["1.2", "1.9", "1.13"], "1.7": ["1.5"], "1.8": ["1.6"], "1.9": ["1.11", "1.4"],
    "1.10": ["1.11"], "1.11": ["1.1"], "1.12": ["1.11"], "1.13": ["1.1"], "1.14": ["1.1", "1.11"],
    "2.1": ["1.4"], "2.2": ["2.1"], "2.3": ["2.1"], "2.4": ["2.2", "1.10"],
    "2.5": ["2.3", "4.2", "2.4"], "2.6": ["2.1"], "2.7": ["2.6"], "2.8": ["2.5", "2.7", "7.1"],
    "3.1": ["1.4", "2.1", "2.3"], "3.2": ["1.4", "2.1", "2.3"], "3.3": ["1.5", "2.3"],
    "3.4": ["1.9", "2.3"], "3.5": ["4.2", "2.3"],
    "4.1": ["1.1"], "4.2": ["2.2"], "4.3": ["4.2", "4.1", "5.6"], "4.4": ["4.3"],
    "4.5": ["4.4", "7.1", "7.2"], "4.6": ["4.5"], "4.7": ["4.3"],
    "5.1": ["4.3"], "5.2": ["3.4", "3.2"], "5.3": ["5.1", "5.2"], "5.4": ["4.6", "5.3"],
    "5.5": ["5.4", "10.1", "2.8", "5.3"], "5.6": ["1.9", "3.2", "3.4", "7.1"],
    "6.1": ["2.3"], "6.2": ["4.2", "5.6"], "6.3": ["5.3", "6.2"], "6.4": ["2.5", "4.2"],
    "7.1": ["1.2"], "7.2": ["2.8", "1.9", "7.5"], "7.3": ["4.4", "4.5", "7.2", "7.5"],
    "7.4": ["7.3", "1.13"], "7.5": ["1.11", "7.1"], "7.6": ["7.2", "7.3", "7.4", "1.9", "1.13"],
    "8.1": ["1.5"], "8.2": ["8.1", "1.9"], "8.3": ["8.2", "2.2"],
    "8.4": ["8.3", "2.8", "7.2", "8.8", "1.13"], "8.5": ["8.4", "1.13"], "8.6": ["8.4"],
    "8.7": ["8.4", "8.5", "8.3", "1.9"], "8.8": ["1.2", "1.10", "1.13"],
    "9.1": ["1.1"], "9.2": ["9.9", "8.4", "8.6", "1.6", "1.7"], "9.3": ["9.1", "1.8", "1.9", "2.2"],
    "9.4": ["9.3"], "9.5": ["9.9"], "9.6": ["9.5", "9.2", "9.1"], "9.7": ["9.5"], "9.8": ["9.1"],
    "9.9": ["9.4", "2.8", "7.2"],
    "10.1": ["10.2", "2.8"], "10.2": ["2.5"], "10.3": ["8.6", "2.8", "7.2", "10.2", "1.13"], "10.4": ["1.1"],
    # 10.5 (the end-to-end smoke) depends on every other story; filled in below.
}


def sort_key(story):
    return tuple(int(x) for x in story.split("."))


def parse_plan(text):
    stories, tasks, depends_on = {}, collections.defaultdict(list), {}
    cur_story = cur_task = None
    for line in text.split("\n"):
        m = re.match(r"#### Story (\d+\.\d+): (.*)", line)
        if m:
            cur_story, cur_task = m.group(1), None
            stories[cur_story] = {"name": m.group(2), "files": []}
            continue
        m = re.match(r"##### Task (\S+): (.*)\((XS|S|M|L)[;)].*$", line)
        if m and cur_story:
            cur_task = {"id": m.group(1), "cls": m.group(3), "files": None}
            tasks[cur_story].append(cur_task)
            continue
        if re.match(r"#{1,3} ", line):
            cur_story = cur_task = None
            continue
        if cur_story and line.startswith("**Files**"):
            stories[cur_story]["files"] += re.findall(r"`([^`]+)`", line)
        elif cur_story and line.startswith("**Depends on**"):
            stated = re.sub(r"\([^)]*\)", "", line)  # drop parentheticals
            stated = re.split(r"\.\s+[A-Z]", stated, maxsplit=1)[0]  # first sentence only
            depends_on[cur_story] = re.findall(r"\b(\d{1,2}\.\d{1,2})\b", stated)
        elif cur_task is not None and line.startswith("- Files:"):
            cur_task["files"] = re.findall(r"`([^`]+)`", line)
    return stories, tasks, depends_on


def compute_waves(deps):
    wave = {}

    def visit(story, stack=()):
        if story in wave:
            return wave[story]
        assert story not in stack, f"cycle through {story}"
        wave[story] = 1 + max([visit(d, stack + (story,)) for d in deps[story]] or [0])
        return wave[story]

    for story in deps:
        visit(story)
    by_wave = collections.defaultdict(list)
    for story, w in wave.items():
        by_wave[w].append(story)
    return wave, by_wave


def closure(deps, story):
    """All stories reachable through DEPS (direct and transitive)."""
    seen, todo = set(), list(deps[story])
    while todo:
        dep = todo.pop()
        if dep not in seen:
            seen.add(dep)
            todo.extend(deps[dep])
    return seen


def merge_order(deps, by_wave):
    dependents = collections.defaultdict(set)
    for story, ds in deps.items():
        for dep in ds:
            dependents[dep].add(story)

    def transitive(story, seen=None):
        seen = set() if seen is None else seen
        for child in dependents[story]:
            if child not in seen:
                seen.add(child)
                transitive(child, seen)
        return seen

    return {w: sorted(ss, key=lambda s: (-len(transitive(s)), sort_key(s))) for w, ss in by_wave.items()}


def effort(stories, tasks):
    rows = {}
    for story in stories:
        raw = sum(MID[t["cls"]] for t in tasks[story])
        counts = collections.Counter(t["cls"] for t in tasks[story])
        rows[story] = (raw, counts)
    return rows


def cost_units(raw_total):
    impl = raw_total * (1 + 4 * OUTPUT_SHARE)
    verify = raw_total * VERIFY_SHARE * (1 + 4 * VERIFY_OUTPUT)
    return impl, verify, impl + verify


def main(argv):
    text = PLAN.read_text()
    stories, tasks, depends_on = parse_plan(text)
    deps = dict(DEPS)
    deps["10.5"] = sorted(set(stories) - {"10.5"}, key=sort_key)
    problems = []

    for story in sorted(set(stories) - set(deps), key=sort_key):
        problems.append(f"story {story} has no DEPS entry")
    for story in sorted(set(deps) - set(stories), key=sort_key):
        problems.append(f"DEPS names story {story} that the plan lacks")
    if problems:
        print("\n".join(problems))
        return 1

    wave, by_wave = compute_waves(deps)
    n_waves = max(by_wave)
    epics = len(re.findall(r"^### Epic ", text, re.M))
    n_tasks = sum(len(v) for v in tasks.values())
    print(f"epics {epics}, stories {len(stories)}, tasks {n_tasks}, waves {n_waves}")

    if "--effort" in argv:
        rows = effort(stories, tasks)
        raw_total = sum(r for r, _ in rows.values())
        impl, verify, total = cost_units(raw_total)
        per_epic = collections.defaultdict(int)
        for story, (raw, _) in rows.items():
            per_epic[story.split(".")[0]] += round(raw * (1 + 4 * OUTPUT_SHARE))
        class_total = collections.Counter(t["cls"] for v in tasks.values() for t in v)
        print(f"classes {dict(class_total)}")
        print(f"raw {raw_total}k, impl CU {impl:.0f}k, verification CU {verify:.0f}k, total CU {total:.0f}k")
        print("per-epic impl CU (sum of rounded story rows): " + ", ".join(f"E{e} {v}k" for e, v in sorted(per_epic.items(), key=lambda kv: int(kv[0]))))
        for story in sorted(rows, key=sort_key):
            raw, counts = rows[story]
            cls = ", ".join(f"{n}{c}" for c, n in sorted(counts.items(), key=lambda kv: list(MID).index(kv[0])))
            print(f"{story}\t{len(tasks[story])} ({cls})\t{raw}k\t{round(raw * (1 + 4 * OUTPUT_SHARE))}k")
        return 0

    for w in sorted(by_wave):
        print(f"- W{w}: " + ", ".join(sorted(by_wave[w], key=sort_key)))

    collisions = 0
    for w, ss in sorted(by_wave.items()):
        seen = {}
        for story in ss:
            for f in set(stories[story]["files"]):
                if f in seen:
                    print(f"COLLISION W{w}: {f} in {seen[f]} and {story}")
                    collisions += 1
                seen[f] = story
    print(f"same-wave file collisions: {collisions}")

    order = merge_order(deps, by_wave)
    print("MERGE ORDER")
    for w in sorted(order):
        print(f"- W{w}: " + " > ".join(order[w]))

    if "--check" in argv:
        failures = []
        if collisions:
            failures.append(f"{collisions} same-wave file collisions")
        for story in sorted(stories, key=sort_key):
            if story == "10.5":
                if story not in depends_on and "**Depends on**" not in text.split("#### Story 10.5", 1)[1]:
                    failures.append("Story 10.5 has no Depends on line")
                continue
            if story not in depends_on:
                failures.append(f"Story {story} has no '**Depends on**' line (DEPS: {', '.join(deps[story]) or 'none'})")
                continue
            stated, direct = set(depends_on[story]) - {story}, set(deps[story])
            for dep in sorted(stated - direct, key=sort_key):
                failures.append(f"Story {story} says it depends on {dep} but DEPS has no such direct edge")
            for dep in sorted(direct - stated, key=sort_key):
                failures.append(f"DEPS has {story} -> {dep} but the plan's Depends on line for Story {story} omits it")
        for story, info in stories.items():
            if len(set(info["files"])) <= MAX_TASK_FILES:
                continue
            for t in tasks[story]:
                if t["files"] is None:
                    failures.append(f"Task {t['id']} (story has {len(set(info['files']))} files) has no Files line")
                elif len(t["files"]) > MAX_TASK_FILES:
                    failures.append(f"Task {t['id']} lists {len(t['files'])} files (max {MAX_TASK_FILES})")
        header = re.search(r"(\d+) epics, (\d+) stories, (\d+) tasks, (\d+) agent waves", text)
        if header:
            claimed = tuple(int(x) for x in header.groups())
            actual = (epics, len(stories), n_tasks, n_waves)
            if claimed != actual:
                failures.append(f"plan header says {claimed} but recount is {actual}")
        else:
            failures.append("plan header count line not found")
        if failures:
            print("CHECK FAILED")
            print("\n".join(failures))
            return 1
        print("CHECK OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
