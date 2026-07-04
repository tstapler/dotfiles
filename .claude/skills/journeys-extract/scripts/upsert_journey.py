#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "typer>=0.12",
#   "loguru>=0.7",
#   "pyyaml>=6.0",
# ]
# ///
"""Upsert a docs/journeys/<slug>.md file without clobbering verify/enrich-owned fields.

Extraction owns: title, user_types, source_refs, and the body (trigger, steps,
gaps, mermaid diagram). journeys-verify/journeys-enrich own: status, test_ids,
last_verified. Re-extraction always refreshes the former and preserves the
latter — except status flips "verified" -> "stale" when the body actually
changed, since a verified journey whose steps changed is no longer trustworthy.
"""

from __future__ import annotations

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


def build_body(journey: dict) -> str:
    lines = [
        f"# {journey['title']}",
        "",
        f"**Trigger**: {journey.get('trigger', 'N/A')}",
        f"**Emotional tone**: {journey.get('emotion', 'N/A')}",
        "",
        "## Steps",
    ]
    lines += [f"{i}. {step}" for i, step in enumerate(journey.get("steps", []), 1)]
    if journey.get("gaps"):
        lines += ["", "## Gaps / Notes"] + [f"- {g}" for g in journey["gaps"]]
    if journey.get("diagram"):
        lines += ["", "```mermaid", journey["diagram"].strip(), "```"]
    return "\n".join(lines) + "\n"


def do_upsert(payload: dict) -> dict:
    out_dir = Path(payload.get("out_dir", "docs/journeys"))
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = payload["journey_id"]
    path = out_dir / f"{slug}.md"

    new_body = build_body(payload)
    extraction_fields = {
        "journey_id": slug,
        "title": payload["title"],
        "user_types": payload.get("user_types", []),
        "source_refs": payload.get("source_refs", []),
    }
    if "test_ids" in payload:
        # journeys-enrich links tests explicitly; journeys-extract never sets this key,
        # so a normal extraction re-run still preserves whatever verify/enrich set.
        extraction_fields["test_ids"] = payload["test_ids"]

    if path.exists():
        old_fm, old_body = split_frontmatter(path.read_text())
        content_changed = old_body.strip() != new_body.strip()
        merged = {**old_fm, **extraction_fields}
        if content_changed and old_fm.get("status") == "verified":
            merged["status"] = "stale"
            action = "updated-marked-stale"
        else:
            merged.setdefault("status", "draft")
            action = "updated" if content_changed else "unchanged"
        merged.setdefault("test_ids", [])
        merged.setdefault("last_verified", None)
    else:
        merged = {"status": "draft", "test_ids": [], "last_verified": None, **extraction_fields}
        action = "created"

    tmp = path.with_suffix(".tmp")
    tmp.write_text(render(merged, new_body))
    tmp.rename(path)
    return {"slug": slug, "action": action, "path": str(path)}


@app.command()
def upsert(
    payload: str = typer.Argument(None, help="JSON journey payload; reads stdin if omitted"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Upsert one journey spec file from a JSON payload (see SKILL.md for the schema)."""
    if not verbose:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    raw = payload if payload is not None else sys.stdin.read()
    try:
        data = json.loads(raw)
        result = do_upsert(data)
    except (KeyError, json.JSONDecodeError) as e:
        logger.error("Bad journey payload: {}", e)
        raise typer.Exit(1)

    logger.success("{} -> {}", result["action"], result["path"])
    print(json.dumps(result))


@app.command()
def selftest() -> None:
    """Run the self-check: create, verify, re-extract-with-changes, re-extract-unchanged."""
    import shutil
    import tempfile

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        payload = {
            "out_dir": str(tmp_dir),
            "journey_id": "demo-flow",
            "title": "Demo Flow",
            "user_types": ["Tester"],
            "steps": ["Open app", "Click go"],
            "trigger": "t",
            "emotion": "calm",
        }
        r1 = do_upsert(payload)
        assert r1["action"] == "created", r1
        fm0, _ = split_frontmatter(Path(r1["path"]).read_text())
        assert fm0["test_ids"] == [], "fresh creation with no test_ids payload should default to []"

        # explicit test_ids at creation time must not be silently dropped
        created_path = Path(r1["path"])
        created_path.unlink()
        payload_with_tests = {**payload, "test_ids": ["seed-1"]}
        r1b = do_upsert(payload_with_tests)
        assert r1b["action"] == "created", r1b
        fm0b, _ = split_frontmatter(Path(r1b["path"]).read_text())
        assert fm0b["test_ids"] == ["seed-1"], fm0b

        # simulate journeys-verify marking it verified
        p = Path(r1["path"])
        fm, body = split_frontmatter(p.read_text())
        fm["status"] = "verified"
        fm["test_ids"] = ["t-1"]
        p.write_text(render(fm, body))

        # re-extract with changed steps -> must flip to stale but keep test_ids
        payload["steps"] = ["Open app", "Click go", "Confirm"]
        r2 = do_upsert(payload)
        assert r2["action"] == "updated-marked-stale", r2
        fm2, _ = split_frontmatter(Path(r2["path"]).read_text())
        assert fm2["status"] == "stale", fm2
        assert fm2["test_ids"] == ["t-1"], "verify-owned fields must survive re-extraction"

        # re-run with identical content -> no-op
        r3 = do_upsert(payload)
        assert r3["action"] == "unchanged", r3

        logger.success("selftest OK")
    finally:
        shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    app()
