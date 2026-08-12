"""Assert-based self-check for the $ARGUMENTS -> Antigravity-skill sync gap.

Run directly: uv run test_gemini_sync.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

from core import Command
from targets.gemini import GeminiTarget, AntigravityTarget, build_antigravity_skill_content


def test_arguments_command_gets_annotated():
    cmd = Command(name="foo", description="does foo", content="run on $ARGUMENTS please")
    content = build_antigravity_skill_content(cmd)
    assert "llm-sync:" in content, "expected an inline annotation when $ARGUMENTS is present"
    assert "$ARGUMENTS" in content, "original token should still be visible, just annotated"


def test_plain_command_is_unaffected():
    cmd = Command(name="bar", description="does bar", content="just do bar, no args")
    content = build_antigravity_skill_content(cmd)
    assert "llm-sync:" not in content, "commands without $ARGUMENTS must be byte-for-byte unaffected"
    assert content.endswith("\n\njust do bar, no args")


def test_gemini_target_antigravity_block_annotates():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        target = GeminiTarget(
            agents_dir=tmp / "agents", skills_dir=tmp / "skills", commands_dir=tmp / "commands"
        )
        cmd = Command(name="stack", description="stack prs", content="stack $ARGUMENTS onto main")
        target.save_commands([cmd])

        skill_file = tmp / "skills" / "stack" / "SKILL.md"
        assert skill_file.exists()
        assert "llm-sync:" in skill_file.read_text()


def test_antigravity_target_annotates():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        target = AntigravityTarget(agents_dir=tmp / "agents", skills_dir=tmp / "skills")
        cmd = Command(name="stack", description="stack prs", content="stack $ARGUMENTS onto main")
        target.save_commands([cmd])

        skill_file = tmp / "skills" / "stack" / "SKILL.md"
        assert skill_file.exists()
        assert "llm-sync:" in skill_file.read_text()


def test_legacy_toml_path_still_substitutes_args():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        target = GeminiTarget(
            agents_dir=tmp / "agents", skills_dir=tmp / "skills", commands_dir=tmp / "commands"
        )
        cmd = Command(name="stack", description="stack prs", content="stack $ARGUMENTS onto main")
        target.save_commands([cmd])

        toml_file = tmp / "commands" / "stack.toml"
        assert toml_file.exists()
        toml_content = toml_file.read_text()
        assert "{{args}}" in toml_content, "legacy .toml path must keep substituting $ARGUMENTS -> {{args}}"
        assert "$ARGUMENTS" not in toml_content


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
