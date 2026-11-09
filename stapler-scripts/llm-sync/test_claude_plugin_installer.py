"""Regression checks for Claude plugin hook merging.

Run directly: uv run test_claude_plugin_installer.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

from core import Plugin
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


def test_effective_command_normalizes_home_and_bin_dir():
    home = str(Path.home())
    assert _effective_command("$HOME/.cargo/bin/kibitzer hook") == "kibitzer hook"
    assert _effective_command(f"{home}/.local/bin/ssq-hooks check") == "ssq-hooks check"
    assert _effective_command("${HOME}/.claude/hooks/x.sh") == f"{home}/.claude/hooks/x.sh"


def test_merge_does_not_duplicate_home_prefixed_hook():
    installer = ClaudePluginInstaller()
    existing = {
        "PreToolUse": [
            {
                "matcher": ".*",
                "hooks": [{"type": "command", "command": f"{Path.home()}/.local/bin/ssq-hooks check"}],
            }
        ]
    }
    plugin_hooks = {
        "PreToolUse": [
            {"matcher": ".*", "hooks": [{"type": "command", "command": "$HOME/.local/bin/ssq-hooks check"}]}
        ]
    }

    assert installer._merge_hooks(existing, plugin_hooks, "core-hooks") == 0
    assert len(existing["PreToolUse"]) == 1


if __name__ == "__main__":
    from _test_runner import run_tests

    run_tests(globals())


def test_install_hooks_skips_marketplace_plugins(tmp_path):
    settings = tmp_path / "settings.json"
    installer = ClaudePluginInstaller()
    installer.settings_file = settings
    plugin = Plugin(
        name="claude-magic-compact",
        description="",
        version="1.3.1",
        hooks={
            "UserPromptSubmit": [
                {"hooks": [{"type": "command", "command": "bun ${CLAUDE_PLUGIN_ROOT}/src/hook.ts"}]}
            ]
        },
        from_marketplace=True,
    )

    added = installer._install_hooks(plugin, dry_run=False)

    assert added == 0
    assert not settings.exists()


def test_install_hooks_still_installs_dotfiles_plugins(tmp_path):
    settings = tmp_path / "settings.json"
    installer = ClaudePluginInstaller()
    installer.settings_file = settings
    plugin = Plugin(
        name="core-hooks",
        description="",
        version="1",
        hooks={"Stop": [{"hooks": [{"type": "command", "command": "echo done"}]}]},
    )

    added = installer._install_hooks(plugin, dry_run=False)

    assert added == 1
    assert "echo done" in settings.read_text()
