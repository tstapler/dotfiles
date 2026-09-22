"""Regression checks for Claude plugin hook merging.

Run directly: uv run test_claude_plugin_installer.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

from targets.claude_plugin_installer import ClaudePluginInstaller, _effective_command


def test_effective_command_strips_hookmetrics_wrapper():
    wrapped = "/Users/tstapler/bin/scripts/hookmetrics kibitzer-postedit -- kibitzer hook"
    assert _effective_command(wrapped) == "kibitzer hook"


def test_effective_command_passes_through_unwrapped():
    assert _effective_command("kibitzer hook") == "kibitzer hook"


def test_merge_does_not_reinstall_wrapped_hook_unwrapped():
    installer = ClaudePluginInstaller()
    existing = {
        "PostToolUse": [
            {
                "matcher": "Edit|Write",
                "hooks": [
                    {
                        "type": "command",
                        "command": "/Users/tstapler/bin/scripts/hookmetrics kibitzer-postedit -- kibitzer hook",
                    }
                ],
            }
        ]
    }
    plugin_hooks = {
        "PostToolUse": [
            {"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "kibitzer hook"}]}
        ]
    }

    added = installer._merge_hooks(existing, plugin_hooks, "kibitzer")

    assert added == 0
    assert len(existing["PostToolUse"]) == 1


def test_merge_still_adds_genuinely_new_hooks():
    installer = ClaudePluginInstaller()
    existing = {"PostToolUse": []}
    plugin_hooks = {
        "PostToolUse": [{"hooks": [{"type": "command", "command": "kibitzer hook"}]}]
    }

    added = installer._merge_hooks(existing, plugin_hooks, "kibitzer")

    assert added == 1
    assert existing["PostToolUse"][0]["hooks"][0]["command"] == "kibitzer hook"


if __name__ == "__main__":
    tests = [value for key, value in list(globals().items()) if key.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
