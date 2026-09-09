"""Regression checks for pinned first-party AI tool provisioning.

Run directly: uv run test_ai_tools.py
"""

from deploys.ai_tools import (
    STAPLER_MCP_REV,
    plan_stapler_mcp_install,
    stapler_mcp_install_command,
)


def test_stapler_mcp_pin_is_an_immutable_commit() -> None:
    assert len(STAPLER_MCP_REV) == 40
    assert all(character in "0123456789abcdef" for character in STAPLER_MCP_REV)


def test_cargo_install_selects_the_workspace_package_positionally() -> None:
    command = stapler_mcp_install_command("/brew/bin/cargo", "/tmp/tool.rev")

    assert "--package" not in command
    assert f'--rev "{STAPLER_MCP_REV}" stapler-mcp' in command
    assert '"/brew/bin/cargo" install' in command


def test_preserves_matching_stapler_mcp_install() -> None:
    plan = plan_stapler_mcp_install(
        executable_present=True,
        installed_revision=STAPLER_MCP_REV,
        target_revision=STAPLER_MCP_REV,
    )

    assert plan.action == "preserve"


def test_installs_when_binary_or_revision_is_missing_or_stale() -> None:
    cases = (
        (False, None),
        (True, None),
        (True, "0123456789abcdef0123456789abcdef01234567"),
    )
    for executable_present, installed_revision in cases:
        plan = plan_stapler_mcp_install(
            executable_present=executable_present,
            installed_revision=installed_revision,
            target_revision=STAPLER_MCP_REV,
        )
        assert plan.action == "install"


if __name__ == "__main__":
    tests = [value for key, value in list(globals().items()) if key.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
