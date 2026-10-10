"""
Port of bootstrap/roles/llm-sync/tasks/main.yml — syncs Claude agents/
skills/commands and MCP config out to Gemini, OpenCode, Antigravity, and Pi,
then renders tiered Pi settings via the in-repo llm-sync tool
(stapler-scripts/llm-sync). The tool itself is hash-based and idempotent;
this just invokes it and prints its summary.

Also installs a systemd --user timer so the sync keeps running between
bootstrap runs — previously it only ran once per `make run`/bootstrap, so a
Claude-side hook/skill/command edit wouldn't reach ~/.gemini/* (or the other
targets) until someone remembered to rerun it by hand.
"""

import io
import os

from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.api.exceptions import DeployError
from pyinfra.operations import files, systemd

from common import brew_prefix, dev_tools_path_env, is_macos, shell_capture

LLM_SYNC_DIR = os.path.expanduser("~/dotfiles/stapler-scripts/llm-sync")
LLM_SYNC_MAIN = os.path.join(LLM_SYNC_DIR, "main.py")
# PluginSource._find_global() looks for a `plugins/` dir relative to the
# process's cwd, which is LLM_SYNC_DIR here, not the dotfiles repo root — so
# without this flag the dotfiles-bundled plugins (kibitzer, ponytail,
# core-hooks, dotfiles-hooks) are silently never found or installed.
DOTFILES_PLUGINS_DIR = os.path.expanduser("~/dotfiles/plugins")

SYSTEMD_USER_DIR = os.path.expanduser("~/.config/systemd/user")
SYNC_TIMER_SERVICE = "llm-sync.service"
SYNC_TIMER_UNIT = "llm-sync.timer"
# How often the timer re-runs the sync. The tool is hash-based/idempotent, so
# a short interval just costs an extra no-op run, not a destructive resync.
SYNC_TIMER_INTERVAL = "30min"
SYNC_TIMER_BOOT_DELAY = "5min"


def sync_command() -> str:
    """The exact shell invocation llm_sync() runs, factored out so the
    systemd service unit's ExecStart can't drift from the one-shot deploy
    path -- both call this, never duplicate the command string."""
    return (
        f'cd {LLM_SYNC_DIR} && PATH="{dev_tools_path_env()}" {brew_prefix()}/bin/uv run main.py'
        f' --plugins-global-dir "{DOTFILES_PLUGINS_DIR}"'
    )


def sync_service_unit_content(command: str) -> str:
    return (
        "[Unit]\n"
        "Description=Sync Claude Code hooks/skills/commands/MCP config to "
        "Gemini, OpenCode, Antigravity, and Pi\n"
        "\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"ExecStart=/bin/sh -c '{command}'\n"
    )


def sync_timer_unit_content(*, boot_delay: str, interval: str) -> str:
    return (
        "[Unit]\n"
        "Description=Run llm-sync on a timer\n"
        "\n"
        "[Timer]\n"
        f"OnBootSec={boot_delay}\n"
        f"OnUnitActiveSec={interval}\n"
        "Persistent=true\n"
        "\n"
        "[Install]\n"
        "WantedBy=timers.target\n"
    )


def _install_sync_timer() -> None:
    """systemd --user timers aren't available on macOS -- Linux-only for now,
    matching this repo's primary machines (Manjaro/Ubuntu); see
    bootstrap-pyinfra/README.md's per-role status table. No macOS equivalent
    (a launchd LaunchAgent) exists yet since nothing in this repo currently
    manages one."""
    if is_macos():
        return

    files.directory(
        name="Ensure ~/.config/systemd/user exists",
        path=SYSTEMD_USER_DIR,
        present=True,
        mode="0755",
    )
    files.put(
        name=f"Deploy {SYNC_TIMER_SERVICE} (user)",
        src=io.StringIO(sync_service_unit_content(sync_command())),
        dest=os.path.join(SYSTEMD_USER_DIR, SYNC_TIMER_SERVICE),
        mode="0644",
    )
    files.put(
        name=f"Deploy {SYNC_TIMER_UNIT} (user)",
        src=io.StringIO(
            sync_timer_unit_content(
                boot_delay=SYNC_TIMER_BOOT_DELAY, interval=SYNC_TIMER_INTERVAL
            )
        ),
        dest=os.path.join(SYSTEMD_USER_DIR, SYNC_TIMER_UNIT),
        mode="0644",
    )
    systemd.service(
        name=f"Enable and start {SYNC_TIMER_UNIT}",
        service=SYNC_TIMER_UNIT,
        running=True,
        enabled=True,
        user_mode=True,
        daemon_reload=True,
    )


@deploy("llm-sync")
def llm_sync() -> None:
    if not os.path.isfile(LLM_SYNC_MAIN):
        return

    code, output = shell_capture(sync_command())
    if code != 0:
        raise DeployError(f"llm-sync failed: {output}")

    # shell_capture returns main.py's combined stdout+stderr verbatim (see
    # its docstring), so this already reproduces PiPackageLedger's
    # `stale Pi package: ...` report lines unmodified -- no pyinfra-side
    # change needed to surface them (Epic 2.2, Task 2.2.2a).
    print(output)
    _install_sync_timer()
