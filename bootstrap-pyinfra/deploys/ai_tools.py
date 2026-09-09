"""Provision Tyler-owned AI CLI/MCP tools used by Claude and Pi.

Kibitzer and consolette come from the public Homebrew tap declared in both
Brewfiles. stapler-mcp has no binary release yet, so it is built from an exact
reviewed commit with Cargo and installed under ``~/.local``. The Cargo build is
queued, which keeps ``pyinfra --dry`` non-mutating.
"""

import os
from dataclasses import dataclass
from typing import Literal

from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.operations import files, server

from common import brew_prefix, shell_capture, shell_ok

STAPLER_MCP_REPO = "https://github.com/tstapler/stapler-mcp"
STAPLER_MCP_REV = "628ec11be71645f42ecbe6dcd11d432c52f4a4e6"
STAPLER_MCP_MARKER = os.path.expanduser(
    "~/.local/share/dotfiles/first-party-tools/stapler-mcp.rev"
)

InstallAction = Literal["install", "preserve"]


@dataclass(frozen=True)
class ToolInstallPlan:
    action: InstallAction
    reason: str


def plan_stapler_mcp_install(
    *, executable_present: bool, installed_revision: str | None, target_revision: str
) -> ToolInstallPlan:
    """Return a side-effect-free source-install decision."""
    if executable_present and installed_revision == target_revision:
        return ToolInstallPlan(
            "preserve", f"stapler-mcp is pinned at {target_revision}"
        )
    return ToolInstallPlan(
        "install",
        f"install stapler-mcp at {target_revision} (current: {installed_revision or 'unknown'})",
    )


def stapler_mcp_install_command(cargo: str, marker_path: str) -> str:
    """Build the exact Cargo command used by the queued source install."""
    marker_dir = os.path.dirname(marker_path)
    return (
        f'mkdir -p "{marker_dir}" && '
        f'"{cargo}" install --locked --force --root ~/.local '
        f'--git "{STAPLER_MCP_REPO}" --rev "{STAPLER_MCP_REV}" '
        f'stapler-mcp && printf "%s\\n" "{STAPLER_MCP_REV}" > "{marker_path}"'
    )


def _installed_revision() -> str | None:
    code, output = shell_capture(
        f'test -f "{STAPLER_MCP_MARKER}" && cat "{STAPLER_MCP_MARKER}"'
    )
    return output.strip() if code == 0 and output.strip() else None


@deploy("First-party AI tools")
def ai_tools() -> None:
    brew = brew_prefix()
    local_bin = os.path.expanduser("~/.local/bin")

    files.directory(
        name="Ensure the user-local binary directory exists",
        path=local_bin,
    )
    for tool in ("kibitzer", "consolette"):
        files.link(
            name=f"Expose {tool} at a stable user-local path",
            path=f"{local_bin}/{tool}",
            target=f"{brew}/bin/{tool}",
        )

    plan = plan_stapler_mcp_install(
        executable_present=shell_ok(f'test -x "{local_bin}/stapler-mcp"'),
        installed_revision=_installed_revision(),
        target_revision=STAPLER_MCP_REV,
    )
    print(f"First-party AI tools: {plan.reason}")
    if plan.action == "preserve":
        return

    cargo = f"{brew}/bin/cargo"
    install_command = stapler_mcp_install_command(cargo, STAPLER_MCP_MARKER)
    server.shell(
        name=f"Build stapler-mcp at {STAPLER_MCP_REV}",
        commands=[install_command],
    )
