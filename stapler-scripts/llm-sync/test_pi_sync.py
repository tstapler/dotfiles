"""Regression checks for Claude skill discovery and Pi-compatible output.

Run directly: uv run test_pi_sync.py
"""

import re
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.append(str(Path(__file__).parent / "src"))

from core import Command, Skill
from sources.claude import ClaudeSource
from targets.pi import PiTarget


def _frontmatter(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    return yaml.safe_load(content.split("---", 2)[1])


def test_claude_discovers_only_root_markdown_and_skill_files():
    with tempfile.TemporaryDirectory() as tmp:
        skills_dir = Path(tmp) / "skills"
        (skills_dir / "group" / "tool" / "references").mkdir(parents=True)
        (skills_dir / "group" / "tool" / "SKILL.md").write_text(
            "---\ndescription: Does tool work.\n---\n\n# Tool\n",
            encoding="utf-8",
        )
        (skills_dir / "group" / "tool" / "references" / "details.md").write_text(
            "---\nname: Not A Skill\ndescription: Reference only.\n---\n",
            encoding="utf-8",
        )
        (skills_dir / "legacy.md").write_text(
            "---\nname: Legacy Skill\ndescription: Legacy work.\n---\n\n# Legacy\n",
            encoding="utf-8",
        )

        skills = ClaudeSource(
            agents_dir=Path(tmp) / "agents",
            skills_dir=skills_dir,
            commands_dir=Path(tmp) / "commands",
        ).load_skills()

        assert {skill.name for skill in skills} == {"group/tool", "Legacy Skill"}


def test_pi_writes_agent_skills_compatible_names_and_descriptions():
    with tempfile.TemporaryDirectory() as tmp:
        target = PiTarget(agent_dir=Path(tmp))
        skills = [
            Skill(
                name="Academic CV Builder",
                description="Builds academic CVs.",
                content="# Academic CV",
            ),
            Skill(
                name="code/skills/fix-loop",
                description="x" * 1100,
                content="# Fix Loop",
            ),
        ]

        assert target.save_skills(skills) == 2

        paths = sorted((Path(tmp) / "skills").glob("*/SKILL.md"))
        assert {path.parent.name for path in paths} == {
            "academic-cv-builder",
            "code-skills-fix-loop",
        }
        for path in paths:
            metadata = _frontmatter(path)
            assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", metadata["name"])
            assert len(metadata["name"]) <= 64
            assert 1 <= len(metadata["description"]) <= 1024
            assert metadata["name"] == path.parent.name


def test_pi_skips_skills_without_descriptions():
    with tempfile.TemporaryDirectory() as tmp:
        target = PiTarget(agent_dir=Path(tmp))
        saved = target.save_skills(
            [Skill(name="empty-description", description="", content="# Fixture")]
        )

        assert saved == 0
        assert not (Path(tmp) / "skills" / "empty-description").exists()


def test_pi_disambiguates_normalized_name_collisions():
    with tempfile.TemporaryDirectory() as tmp:
        target = PiTarget(agent_dir=Path(tmp))
        target.save_skills(
            [
                Skill(name="Root Cause", description="First.", content="# One"),
                Skill(name="root-cause", description="Second.", content="# Two"),
            ]
        )

        paths = sorted((Path(tmp) / "skills").glob("*/SKILL.md"))
        assert len(paths) == 2
        names = [path.parent.name for path in paths]
        assert len(set(names)) == 2
        assert all(len(name) <= 64 for name in names)


def test_skill_hash_changes_when_a_bundled_resource_changes():
    with tempfile.TemporaryDirectory() as tmp:
        skill_dir = Path(tmp) / "resource-skill"
        resource = skill_dir / "scripts" / "helper.sh"
        resource.parent.mkdir(parents=True)
        source_file = skill_dir / "SKILL.md"
        source_file.write_text("source", encoding="utf-8")
        resource.write_text("echo first", encoding="utf-8")
        skill = Skill(
            name="Resource Skill",
            description="Uses bundled resources.",
            content="# Resource Skill",
            source_file=str(source_file),
        )

        first_hash = skill.get_hash()
        resource.write_text("echo second", encoding="utf-8")

        assert skill.get_hash() != first_hash


def test_pi_dry_run_does_not_create_output_directories():
    with tempfile.TemporaryDirectory() as tmp:
        agent_dir = Path(tmp) / "missing-pi-agent"
        target = PiTarget(agent_dir=agent_dir)

        assert target.save_skills(
            [Skill(name="Dry Run", description="Preview only.", content="# Dry Run")],
            dry_run=True,
        ) == 0
        assert target.save_commands(
            [Command(name="dry-run", description="Preview only.", content="# Dry Run")],
            dry_run=True,
        ) == 0
        assert not agent_dir.exists()


def test_pi_copies_bundled_skill_resources():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source_dir = tmp_path / "source" / "resource-skill"
        (source_dir / "references").mkdir(parents=True)
        source_file = source_dir / "SKILL.md"
        source_file.write_text("source", encoding="utf-8")
        (source_dir / "references" / "guide.md").write_text("guide", encoding="utf-8")

        target = PiTarget(agent_dir=tmp_path / "pi")
        target.save_skills(
            [
                Skill(
                    name="Resource Skill",
                    description="Uses bundled resources.",
                    content="# Resource Skill",
                    source_file=str(source_file),
                )
            ]
        )

        copied = (
            tmp_path
            / "pi"
            / "skills"
            / "resource-skill"
            / "references"
            / "guide.md"
        )
        assert copied.read_text(encoding="utf-8") == "guide"


if __name__ == "__main__":
    tests = [value for key, value in list(globals().items()) if key.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
