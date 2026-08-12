#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "typer>=0.12",
#   "loguru>=0.7",
# ]
# ///
"""Audit project_plans/<project>/ output volume against shipped-code signal.

Answers: which SDD planning sessions produced a lot of markdown relative to
what actually got built? Git commit matching on the project slug is a heuristic,
not ground truth -- treat the ratio as a prioritization signal, not a verdict.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import typer
from loguru import logger

app = typer.Typer(add_completion=False)

PHASE_MAP = {
    "requirements.md": "ideate",
    "research": "research",
    "decisions": "decisions",
    "design": "design",
    "implementation/plan.md": "plan",
    "implementation/validation.md": "validate",
}

CHECKBOX_RE = re.compile(r"^\s*-\s*\[( |x|X)\]", re.MULTILINE)
LARGE_FILE_LINES = 250


def phase_for(rel_path: Path) -> str:
    parts = rel_path.parts
    if str(rel_path) in PHASE_MAP:
        return PHASE_MAP[str(rel_path)]
    if parts[0] in PHASE_MAP:
        return PHASE_MAP[parts[0]]
    if parts[0] == "implementation":
        return "validate-extra"
    return "other"


@dataclass
class ProjectStats:
    name: str
    files: list[tuple[Path, int, int]] = field(default_factory=list)  # path, lines, words
    phase_lines: dict[str, int] = field(default_factory=dict)
    checkboxes_done: int = 0
    checkboxes_total: int = 0
    planning_commits: int = 0
    planning_first_date: str = ""
    planning_last_date: str = ""
    shipped_commits: int = 0
    shipped_lines: int = 0

    @property
    def total_lines(self) -> int:
        return sum(l for _, l, _ in self.files)

    @property
    def total_words(self) -> int:
        return sum(w for _, _, w in self.files)

    @property
    def ratio(self) -> float:
        return self.total_lines / max(self.shipped_lines, 1)


def run_git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )
    return result.stdout.strip()


def collect_project(project_dir: Path, repo_root: Path) -> ProjectStats:
    stats = ProjectStats(name=project_dir.name)

    for md_file in sorted(project_dir.rglob("*.md")):
        rel = md_file.relative_to(project_dir)
        text = md_file.read_text(errors="replace")
        lines = text.count("\n") + 1
        words = len(text.split())
        stats.files.append((rel, lines, words))
        phase = phase_for(rel)
        stats.phase_lines[phase] = stats.phase_lines.get(phase, 0) + lines

        if rel == Path("implementation/plan.md"):
            checks = CHECKBOX_RE.findall(text)
            stats.checkboxes_total = len(checks)
            stats.checkboxes_done = sum(1 for c in checks if c.lower() == "x")

    rel_dir = project_dir.relative_to(repo_root)
    log = run_git(
        ["log", "--follow", "--pretty=format:%ad", "--date=short", "--", str(rel_dir)],
        repo_root,
    )
    dates = [d for d in log.splitlines() if d]
    stats.planning_commits = len(dates)
    if dates:
        stats.planning_last_date = dates[0]
        stats.planning_first_date = dates[-1]

    shipped_log = run_git(
        [
            "log",
            "--all",
            "-i",
            f"--grep={project_dir.name}",
            "--numstat",
            "--pretty=format:__COMMIT__",
        ],
        repo_root,
    )
    shipped_lines = 0
    shipped_commits = 0
    for block in shipped_log.split("__COMMIT__"):
        block = block.strip()
        if not block:
            continue
        touched_plan_dir_only = True
        added = 0
        for line in block.splitlines():
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            ins, dele, path = parts
            if not path.startswith(str(rel_dir)):
                touched_plan_dir_only = False
            ins_n = int(ins) if ins.isdigit() else 0
            added += ins_n
        if not touched_plan_dir_only:
            shipped_commits += 1
            shipped_lines += added
    stats.shipped_commits = shipped_commits
    stats.shipped_lines = shipped_lines

    return stats


@app.command()
def main(
    root: Path = typer.Option(Path("project_plans"), help="Path to project_plans/"),
    output: Path = typer.Option(None, "--output", "-o", help="Write markdown report here"),
    as_json: bool = typer.Option(False, "--json", help="Print raw JSON instead of a table"),
    large_files: bool = typer.Option(
        True, help="List individual files over the trim-candidate threshold"
    ),
) -> None:
    """Audit SDD project_plans/ output volume vs. shipped-code signal."""
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    repo_root = Path(
        run_git(["rev-parse", "--show-toplevel"], root.resolve().parent)
    )
    root = (repo_root / root).resolve() if not root.is_absolute() else root
    if not root.exists():
        logger.error("No such directory: {}", root)
        raise typer.Exit(1)

    projects = sorted(p for p in root.iterdir() if p.is_dir())
    if not projects:
        logger.warning("No project directories found under {}", root)
        raise typer.Exit(0)

    all_stats = [collect_project(p, repo_root) for p in projects]
    all_stats.sort(key=lambda s: s.total_lines, reverse=True)

    if as_json:
        payload = [
            {
                "name": s.name,
                "total_lines": s.total_lines,
                "total_words": s.total_words,
                "phase_lines": s.phase_lines,
                "checkboxes_done": s.checkboxes_done,
                "checkboxes_total": s.checkboxes_total,
                "planning_commits": s.planning_commits,
                "planning_first_date": s.planning_first_date,
                "planning_last_date": s.planning_last_date,
                "shipped_commits": s.shipped_commits,
                "shipped_lines": s.shipped_lines,
                "planning_to_shipped_ratio": round(s.ratio, 1),
            }
            for s in all_stats
        ]
        print(json.dumps(payload, indent=2))
        return

    lines_out: list[str] = []
    lines_out.append("# SDD Plan Audit\n")
    lines_out.append(
        "| project | plan lines | words | checkboxes | shipped commits | shipped lines | plan:ship ratio |"
    )
    lines_out.append("|---|---:|---:|---:|---:|---:|---:|")
    for s in all_stats:
        checkbox_str = f"{s.checkboxes_done}/{s.checkboxes_total}" if s.checkboxes_total else "—"
        lines_out.append(
            f"| {s.name} | {s.total_lines} | {s.total_words} | {checkbox_str} "
            f"| {s.shipped_commits} | {s.shipped_lines} | {s.ratio:.1f}x |"
        )
    lines_out.append("")
    lines_out.append(
        "`plan:ship ratio` = planning markdown lines / lines added in commits whose "
        "message matched the project slug (excludes commits touching only the plan "
        "dir itself). Heuristic, not ground truth -- a commit that doesn't mention "
        "the slug won't be counted as shipped."
    )

    for s in all_stats:
        lines_out.append(f"\n## {s.name}\n")
        lines_out.append("Phase breakdown (lines):")
        for phase, count in sorted(s.phase_lines.items(), key=lambda kv: -kv[1]):
            lines_out.append(f"- {phase}: {count}")
        if s.planning_commits:
            lines_out.append(
                f"\nPlanning commits: {s.planning_commits} "
                f"({s.planning_first_date} → {s.planning_last_date})"
            )
        if large_files:
            big = [(p, l) for p, l, _ in s.files if l > LARGE_FILE_LINES]
            if big:
                lines_out.append(f"\nTrim candidates (>{LARGE_FILE_LINES} lines):")
                for p, l in sorted(big, key=lambda x: -x[1]):
                    lines_out.append(f"- {p} — {l} lines")

    report = "\n".join(lines_out)
    print(report)

    if output:
        output.write_text(report + "\n")
        logger.success("Report written to {}", output)


if __name__ == "__main__":
    app()
