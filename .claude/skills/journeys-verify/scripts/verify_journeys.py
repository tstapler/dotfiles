#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "typer>=0.12",
#   "loguru>=0.7",
#   "pyyaml>=6.0",
# ]
# ///
"""Mechanically verify docs/journeys/*.md files.

Tier 1 (this script, deterministic): does every source_ref path still exist,
and is every test_id findable as a full-text substring somewhere in the repo?
Cheap enough to run on every PR/pre-commit. Updates status (draft/verified/stale),
last_verified, and verify_notes — never touches extraction-owned fields
(title, user_types, source_refs, body).

Tier 2 (semantic drift — does the narrative still match the actual UI/code) is
an LLM-driven pass, described in this skill's SKILL.md, not implemented here:
a script can't judge "these steps no longer match reality."
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

import typer
import yaml
from loguru import logger

app = typer.Typer(add_completion=False)

FRONTMATTER_DELIM = "---\n"
FIELD_ORDER = [
    "journey_id", "title", "user_types", "status", "test_ids",
    "last_verified", "verify_notes", "source_refs",
]
EXCLUDE_DIR_NAMES = {".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__", ".next", ".cache"}


def split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith(FRONTMATTER_DELIM):
        return {}, text
    _, rest = text.split(FRONTMATTER_DELIM, 1)
    fm_text, body = rest.split(FRONTMATTER_DELIM, 1)
    return yaml.safe_load(fm_text) or {}, body.lstrip("\n")


def render(frontmatter: dict, body: str) -> str:
    ordered = {k: frontmatter[k] for k in FIELD_ORDER if k in frontmatter}
    ordered.update({k: v for k, v in frontmatter.items() if k not in ordered})
    fm_text = yaml.safe_dump(ordered, sort_keys=False, default_flow_style=False)
    return f"---\n{fm_text}---\n\n{body}"


def iter_journey_files(journeys_dir: Path):
    for p in sorted(journeys_dir.glob("*.md")):
        if p.name.lower() == "readme.md":
            continue
        yield p


def list_source_files(repo_root: Path, journeys_dir: Path) -> list[Path]:
    # ponytail: naive full-repo text scan; swap for an `rg -F` subprocess if this
    # is too slow on a large repo — semantics stay identical.
    journeys_resolved = journeys_dir.resolve()
    files = []
    for p in repo_root.rglob("*"):
        if not p.is_file() or any(part in EXCLUDE_DIR_NAMES for part in p.parts):
            continue
        try:
            if journeys_resolved in p.resolve().parents:
                continue
        except OSError:
            continue
        files.append(p)
    return files


def repo_contains(files: list[Path], needle: str) -> bool:
    for p in files:
        try:
            if needle in p.read_text(errors="ignore"):
                return True
        except OSError:
            continue
    return False


def check_journey(path: Path, repo_root: Path, files: list[Path]) -> dict:
    fm, body = split_frontmatter(path.read_text())
    reasons = []

    missing_refs = [r for r in fm.get("source_refs", []) if not (repo_root / r).exists()]
    if missing_refs:
        reasons.append(f"missing source_refs: {missing_refs}")

    test_ids = fm.get("test_ids", [])
    missing_tests = [t for t in test_ids if not repo_contains(files, t)]
    if missing_tests:
        reasons.append(f"missing test_ids: {missing_tests}")

    if reasons:
        new_status = "stale"
    elif not test_ids:
        new_status = "draft"
        reasons = ["no test_ids linked yet"]
    else:
        new_status = "verified"

    fm["status"] = new_status
    fm["verify_notes"] = reasons
    if new_status == "verified":
        fm["last_verified"] = datetime.date.today().isoformat()

    tmp = path.with_suffix(".tmp")
    tmp.write_text(render(fm, body))
    tmp.rename(path)

    return {"slug": fm.get("journey_id", path.stem), "status": new_status, "reasons": reasons}


@app.command()
def check(
    journeys_dir: Path = typer.Option(Path("docs/journeys"), "--journeys-dir"),
    repo_root: Path = typer.Option(Path("."), "--repo-root"),
    strict: bool = typer.Option(False, "--strict", help="Exit 1 if any journey ends up stale"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Mechanically verify every journey's source_refs and test_ids; update status."""
    if not verbose:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    if not journeys_dir.exists():
        logger.error("No journeys dir at {}", journeys_dir)
        raise typer.Exit(1)

    files = list_source_files(repo_root, journeys_dir)
    results = [check_journey(p, repo_root, files) for p in iter_journey_files(journeys_dir)]

    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    logger.success("Checked {} journeys: {}", len(results), counts)
    print(json.dumps({"results": results, "counts": counts}))

    if strict and counts.get("stale"):
        raise typer.Exit(1)


@app.command()
def selftest() -> None:
    """Verified link, broken link -> stale, no-tests -> draft (not stale)."""
    import shutil
    import tempfile

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        repo = tmp_dir / "repo"
        journeys_dir = repo / "docs" / "journeys"
        journeys_dir.mkdir(parents=True)
        (repo / "src").mkdir()
        (repo / "src" / "App.tsx").write_text("// app")
        (repo / "tests").mkdir()
        (repo / "tests" / "flow.spec.ts").write_text('test("creates a new trip", () => {})')

        journey_path = journeys_dir / "demo.md"
        journey_path.write_text(render(
            {
                "journey_id": "demo", "title": "Demo", "user_types": [],
                "test_ids": ["creates a new trip"], "source_refs": ["src/App.tsx"],
            },
            "# Demo\n",
        ))

        files = list_source_files(repo, journeys_dir)
        r1 = check_journey(journey_path, repo, files)
        assert r1["status"] == "verified", r1

        (repo / "tests" / "flow.spec.ts").unlink()
        files = list_source_files(repo, journeys_dir)
        r2 = check_journey(journey_path, repo, files)
        assert r2["status"] == "stale", r2
        assert "missing test_ids" in r2["reasons"][0], r2

        draft_path = journeys_dir / "draft.md"
        draft_path.write_text(render(
            {"journey_id": "draft", "title": "Draft", "user_types": [], "test_ids": [], "source_refs": []},
            "# Draft\n",
        ))
        r3 = check_journey(draft_path, repo, files)
        assert r3["status"] == "draft", r3

        logger.success("selftest OK")
    finally:
        shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    app()
