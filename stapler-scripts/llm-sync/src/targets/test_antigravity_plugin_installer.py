"""Self-check for AntigravityPluginInstaller's hooks.json schema conversion. Run directly:
uv run --directory stapler-scripts/llm-sync python src/targets/test_antigravity_plugin_installer.py
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Plugin  # noqa: E402
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


def run_all():
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} checks passed")


if __name__ == "__main__":
    run_all()
