"""Self-check for AntigravityPluginInstaller's hooks.json schema conversion. Run directly:
uv run --directory stapler-scripts/llm-sync python src/targets/test_antigravity_plugin_installer.py
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Command, Plugin, Skill  # noqa: E402
from targets.antigravity_plugin_installer import (  # noqa: E402
    AntigravityPluginInstaller,
    _to_antigravity_hook_spec,
)


def test_single_entry_collapses_to_object():
    # sdd's real PreToolUse: one matcher, one hook.
    spec = _to_antigravity_hook_spec(
        [{"matcher": "Write|Edit", "hooks": [{"type": "command", "command": "check-plan.sh"}]}]
    )
    assert spec == {
        "matcher": "Write|Edit",
        "hooks": [{"type": "command", "command": "check-plan.sh"}],
    }, spec


def test_missing_matcher_defaults_to_broad():
    # sdd's real Stop entry omits/empties matcher entirely.
    spec = _to_antigravity_hook_spec([{"hooks": [{"type": "command", "command": "reminder.sh"}]}])
    assert spec["matcher"] == ".*", spec


def test_multiple_matchers_merge_without_losing_hooks():
    # core-hooks' real PreToolUse: a broad classifier plus a narrow SDD reminder.
    # Both commands must survive even though Antigravity only allows one matcher.
    entries = [
        {"matcher": ".*", "hooks": [{"type": "command", "command": "ssq-hooks check --antigravity"}]},
        {"matcher": "Write|Edit", "hooks": [{"type": "command", "command": "sdd-reminder.sh"}]},
    ]
    spec = _to_antigravity_hook_spec(entries)
    assert spec["matcher"] == ".*", spec  # broadest matcher wins
    assert [h["command"] for h in spec["hooks"]] == [
        "ssq-hooks check --antigravity",
        "sdd-reminder.sh",
    ], spec


def test_duplicate_hooks_across_matchers_are_deduped():
    # prompt-injection-defender's real PostToolUse: same command repeated under
    # five separate matchers (Read, WebFetch, Bash, Grep, Task).
    entries = [
        {"matcher": m, "hooks": [{"type": "command", "command": "defender.py", "timeout": 5}]}
        for m in ["Read", "WebFetch", "Bash", "Grep", "Task"]
    ]
    spec = _to_antigravity_hook_spec(entries)
    assert spec["matcher"] == "Read|WebFetch|Bash|Grep|Task", spec
    assert len(spec["hooks"]) == 1, spec


def test_install_plugin_writes_object_not_array_hooks_json():
    # Regression for the actual bug: agy's plugin loader
    # (jsonhook.JSONHookSpec) rejects an array here with
    # "cannot unmarshal array into Go struct field .PreToolUse" —
    # confirmed against a live agy 1.2.14 session.
    plugin = Plugin(
        name="core-hooks",
        description="test",
        version="1.0.0",
        hooks={
            "PreToolUse": [
                {"matcher": ".*", "hooks": [{"type": "command", "command": "a"}]},
                {"matcher": "Write|Edit", "hooks": [{"type": "command", "command": "b"}]},
            ],
        },
    )
    with tempfile.TemporaryDirectory() as td:
        installer = AntigravityPluginInstaller(target_dir=Path(td))
        installer._install_plugin(plugin, dry_run=False)
        written = json.loads((Path(td) / "core-hooks" / "hooks.json").read_text())
        assert isinstance(written["PreToolUse"], dict), written["PreToolUse"]
        assert written["PreToolUse"]["matcher"] == ".*", written
        assert [h["command"] for h in written["PreToolUse"]["hooks"]] == ["a", "b"], written


def test_register_with_agy_installs_from_staging_copy_not_target_dir():
    # Regression for the second bug: `agy plugin install <path>` was called
    # with self.target_dir / plugin.name — the same path it had just been
    # written to — which agy refuses. Prove the staged copy is used instead.
    plugin = Plugin(name="test-plugin", description="test", version="1.0.0")
    with tempfile.TemporaryDirectory() as td:
        installer = AntigravityPluginInstaller(target_dir=Path(td))
        with patch("shutil.which", return_value="/usr/bin/agy"), patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            installer.install_plugins([plugin], dry_run=False)

        assert mock_run.called, "agy plugin install was never invoked"
        called_path = Path(mock_run.call_args.args[0][-1])
        assert called_path != installer.target_dir / plugin.name, called_path
        assert called_path.parent != installer.target_dir, called_path


def test_install_plugins_survives_copytree_failure_and_continues_loop():
    # Regression: a copytree failure (permission error, disk full, etc.) must
    # not abort registration for the remaining plugins in the loop.
    plugin_a = Plugin(name="plugin-a", description="test", version="1.0.0")
    plugin_b = Plugin(name="plugin-b", description="test", version="1.0.0")
    with tempfile.TemporaryDirectory() as td:
        installer = AntigravityPluginInstaller(target_dir=Path(td))
        with patch("shutil.which", return_value="/usr/bin/agy"), \
             patch("shutil.copytree", side_effect=OSError("disk full")), \
             patch("subprocess.run") as mock_run:
            installed = installer.install_plugins([plugin_a, plugin_b], dry_run=False)

        assert installed == 2, installed  # both plugins' files still written
        assert not mock_run.called  # copytree never succeeded, so agy was never invoked


def test_register_with_agy_handles_timeout():
    plugin = Plugin(name="slow-plugin", description="test", version="1.0.0")
    with tempfile.TemporaryDirectory() as td:
        installer = AntigravityPluginInstaller(target_dir=Path(td))
        with patch("shutil.which", return_value="/usr/bin/agy"), \
             patch("subprocess.run", side_effect=__import__("subprocess").TimeoutExpired(cmd="agy", timeout=30)):
            # Must not raise: a hung agy process shouldn't block the install loop.
            installer.install_plugins([plugin], dry_run=False)


def test_install_skills_writes_skill_markdown_with_frontmatter():
    skill = Skill(name="my-skill", description="A skill", content="# Do the thing\nBody.")
    plugin = Plugin(name="skill-plugin", description="test", version="1.0.0", skills=[skill])
    with tempfile.TemporaryDirectory() as td:
        installer = AntigravityPluginInstaller(target_dir=Path(td))
        installer._install_plugin(plugin, dry_run=False)
        dest = Path(td) / "skill-plugin" / "skills" / "my-skill" / "SKILL.md"
        text = dest.read_text()
        assert text.startswith("---\n"), text
        assert "name: my-skill" in text, text
        assert "description: A skill" in text, text
        assert text.endswith("# Do the thing\nBody."), text


def test_install_commands_writes_skill_markdown_strips_frontmatter_and_normalizes_name():
    cmd = Command(
        name="backlog/ship",
        description="Ship a backlog item",
        content="---\nname: ship\n---\n\nDo the ship steps.",
    )
    plugin = Plugin(name="cmd-plugin", description="test", version="1.0.0", commands=[cmd])
    with tempfile.TemporaryDirectory() as td:
        installer = AntigravityPluginInstaller(target_dir=Path(td))
        installer._install_plugin(plugin, dry_run=False)
        dest = Path(td) / "cmd-plugin" / "skills" / "backlog-ship" / "SKILL.md"
        assert dest.exists(), "expected normalized_name (/ -> -) to be used as the skill dir"
        text = dest.read_text()
        assert "name: backlog-ship" in text, text
        assert "description: Ship a backlog item" in text, text
        assert "Do the ship steps." in text, text
        assert "---\nname: ship\n---" not in text, "command's own frontmatter should be stripped"


def run_all():
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} checks passed")


if __name__ == "__main__":
    run_all()
