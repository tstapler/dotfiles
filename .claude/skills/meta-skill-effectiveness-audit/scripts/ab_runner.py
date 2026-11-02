#!/usr/bin/env python3
"""Run one benchmark task N times per arm and record cost, time and a task-specific score.

An arm is a git ref of this repo. Each run gets a throwaway $HOME whose .claude/ holds only
that ref's skills/agents/commands (so ~/.claude paths inside skills still resolve), a copy of
the task's fixture workdir, and a copy of the login credentials that is deleted afterwards.

    ab_runner.py FIXTURE_DIR --arm A=HEAD --arm B=bench/triad-v1 --runs 5 [--model sonnet]
                 [--max-total-cost USD] [--out DIR]

Runs are sequential (skills write fixed /tmp paths, so concurrent runs would collide) and
interleaved in random order within each block, so slow drift hits both arms equally. Re-running
the same command resumes: finished (arm, run) pairs in results.jsonl are skipped.

SAFETY: runs use --permission-mode bypassPermissions inside a throwaway cwd and HOME. A Bash
call can still reach the rest of the filesystem; only run fixtures you wrote.
"""
import argparse
import importlib.util
import io
import json
import os
import random
import shutil
import subprocess
import sys
import tarfile
import time

REPO = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
CONFIG_DIRS = (".claude/skills", ".claude/agents", ".claude/commands")


def git_has(ref, path):
    return subprocess.run(["git", "cat-file", "-e", f"{ref}:{path}"], cwd=REPO,
                          capture_output=True).returncode == 0


def extract_arm(ref, home):
    paths = [p for p in CONFIG_DIRS if git_has(ref, p)]
    data = subprocess.check_output(["git", "archive", "--format=tar", ref, "--", *paths], cwd=REPO)
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(home, filter="data")


def prepare(run_dir, ref, fixture, task):
    home = os.path.join(run_dir, "home")
    work = os.path.join(run_dir, "work")
    os.makedirs(home)
    extract_arm(ref, home)
    shutil.copytree(os.path.join(fixture, task["workdir"]), work)
    cred = os.path.expanduser("~/.claude/.credentials.json")
    dest = os.path.join(home, ".claude", ".credentials.json")
    shutil.copy(cred, dest)
    os.chmod(dest, 0o600)
    git = ["git", "-c", "user.name=bench", "-c", "user.email=bench@example.invalid"]
    subprocess.run(["git", "init", "-q"], cwd=work, check=True)
    subprocess.run(git + ["add", "-A"], cwd=work, check=True)
    subprocess.run(git + ["commit", "-qm", "fixture"], cwd=work, check=True)
    return home, work


def run_claude(run_dir, home, work, task, model, timeout_s):
    cmd = ["claude", "-p", task["prompt"], "--output-format", "stream-json", "--verbose",
           "--permission-mode", "bypassPermissions", "--max-budget-usd", str(task["max_budget_usd"])]
    if model:
        cmd += ["--model", model]
    env = {**os.environ, "HOME": home}
    env.pop("CLAUDE_CONFIG_DIR", None)
    stream = os.path.join(run_dir, "stream.jsonl")
    t0 = time.time()
    timed_out = False
    with open(stream, "w") as out:
        proc = subprocess.Popen(cmd, cwd=work, env=env, stdout=out, stderr=subprocess.STDOUT)
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            timed_out = True
    result, init = {}, {}
    with open(stream, errors="replace") as fh:
        for line in fh:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("type") == "system" and ev.get("subtype") == "init":
                init = ev
            elif ev.get("type") == "result":
                result = ev
    return {
        "cost_usd": result.get("total_cost_usd"),
        "turns": result.get("num_turns"),
        "duration_s": round(time.time() - t0, 1),
        "api_duration_s": (result.get("duration_api_ms") or 0) / 1000,
        "is_error": bool(result.get("is_error", True)) or timed_out,
        "subtype": "timeout" if timed_out else result.get("subtype"),
        "usage": result.get("usage"),
        "model": init.get("model"),
        "skills_loaded": len(init.get("skills") or []),
    }


def load_check(fixture, task):
    spec = importlib.util.spec_from_file_location("check", os.path.join(fixture, task["check"]))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def done_runs(results_path):
    done, spent = set(), 0.0
    if os.path.exists(results_path):
        with open(results_path) as fh:
            for line in fh:
                rec = json.loads(line)
                done.add((rec["arm"], rec["run"]))
                spent += rec.get("cost_usd") or 0.0
    return done, spent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fixture")
    ap.add_argument("--arm", action="append", required=True, help="LABEL=GITREF, repeat for each arm")
    ap.add_argument("--runs", type=int, default=3, help="runs per arm")
    ap.add_argument("--model", default=None)
    ap.add_argument("--max-total-cost", type=float, default=None, help="stop launching runs past this total")
    ap.add_argument("--out", default=None)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--work-root", default=None, help="where throwaway run dirs live (default: a temp dir)")
    args = ap.parse_args()

    fixture = os.path.abspath(args.fixture)
    with open(os.path.join(fixture, "task.json")) as fh:
        task = json.load(fh)
    arms = dict(a.split("=", 1) for a in args.arm)
    out = args.out or os.path.expanduser(f"~/.cache/skill-ab/{task['name']}")
    os.makedirs(os.path.join(out, "transcripts"), exist_ok=True)
    results_path = os.path.join(out, "results.jsonl")
    done, spent = done_runs(results_path)
    check = load_check(fixture, task)
    truth = os.path.join(fixture, "truth.json")
    rng = random.Random(args.seed)
    work_root = args.work_root or os.path.join(os.environ.get("TMPDIR", "/tmp"), f"skill-ab-{task['name']}")
    os.makedirs(work_root, exist_ok=True)

    for run in range(args.runs):
        order = list(arms)
        rng.shuffle(order)
        for label in order:
            if (label, run) in done:
                continue
            if args.max_total_cost is not None and spent >= args.max_total_cost:
                print(f"STOP: spent ${spent:.2f} >= cap ${args.max_total_cost:.2f}; results so far in {results_path}")
                return
            run_dir = os.path.join(work_root, f"{label}-{run}")
            shutil.rmtree(run_dir, ignore_errors=True)
            os.makedirs(run_dir)
            home = None
            try:
                home, work = prepare(run_dir, arms[label], fixture, task)
                metrics = run_claude(run_dir, home, work, task, args.model, task["timeout_s"])
            finally:
                if home:
                    shutil.rmtree(os.path.join(home, ".claude", ".credentials.json"), ignore_errors=True)
                    try:
                        os.remove(os.path.join(home, ".claude", ".credentials.json"))
                    except OSError:
                        pass
            try:
                metrics["score"] = check.score(run_dir, work, truth)
            except Exception as exc:  # a broken check must not lose the cost record
                metrics["score"] = {"check_error": repr(exc)}
            rec = {"task": task["name"], "arm": label, "ref": arms[label], "run": run,
                   "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S"), **metrics}
            with open(results_path, "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            spent += metrics.get("cost_usd") or 0.0
            tdir = os.path.join(out, "transcripts", f"{label}-{run}")
            shutil.rmtree(tdir, ignore_errors=True)
            shutil.move(os.path.join(home, ".claude", "projects"), tdir)
            shutil.move(os.path.join(run_dir, "stream.jsonl"), os.path.join(tdir, "stream.jsonl"))
            shutil.rmtree(run_dir, ignore_errors=True)
            sc = metrics["score"]
            print(f"[{label} run {run}] ${metrics['cost_usd']} {metrics['turns']} turns "
                  f"{metrics['duration_s']:.0f}s success={sc.get('success')} "
                  f"blockers {sc.get('blockers_fixed')}/{sc.get('blockers_found')} verdict={sc.get('final_verdict')}",
                  flush=True)
    print(f"done; total ${spent:.2f}; results in {results_path}")


if __name__ == "__main__":
    sys.exit(main())
