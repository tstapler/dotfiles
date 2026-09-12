"""
Host-dependent facts computed at deploy time — the pyinfra equivalent of
playbook.yml's pre_tasks. These call host.get_fact(), so they must be called
from within deploy code (after the host is connected), never from group_data
(which is static Python evaluated before any host exists).
"""

from pathlib import Path

from pyinfra import host  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.facts.server import Arch, Command, Hostname, Kernel, LinuxDistribution


def is_wsl() -> bool:
    output = host.get_fact(
        Command, "grep -qi microsoft /proc/version 2>/dev/null && echo yes || echo no"
    )
    return bool(output.strip() == "yes")


def is_macos() -> bool:
    return bool(host.get_fact(Kernel) == "Darwin")


def is_archlinux() -> bool:
    distro = host.get_fact(LinuxDistribution)
    if not distro:
        return False
    id_like = distro.get("release_meta", {}).get("ID_LIKE", "")
    return distro.get("release_meta", {}).get("ID") == "arch" or "arch" in id_like


def is_debian_like() -> bool:
    distro = host.get_fact(LinuxDistribution)
    if not distro:
        return False
    id_like = distro.get("release_meta", {}).get("ID_LIKE", "")
    return (
        distro.get("release_meta", {}).get("ID") in ("debian", "ubuntu")
        or "debian" in id_like
    )


def is_btrfs_root() -> bool:
    output = host.get_fact(Command, "stat -f -c '%T' /")
    return output.strip() == "btrfs"


def brew_prefix() -> str:
    if is_macos():
        return "/opt/homebrew" if host.get_fact(Arch) == "arm64" else "/usr/local"
    return "/home/linuxbrew/.linuxbrew"


def arch() -> str:
    """Raw uname -m string (e.g. x86_64, arm64, aarch64)."""
    return str(host.get_fact(Arch))


def hostname() -> str:
    return str(host.get_fact(Hostname))


def is_fbg_machine() -> bool:
    """Matches bootstrap/run.sh's own `[Ff][Bb][Gg]-*` hostname auto-detection."""
    return hostname().lower().startswith("fbg-")


def github_personal_user() -> str | None:
    return "tstapler" if is_fbg_machine() else None


def dev_tools_path_env() -> str:
    """
    PATH prefix for commands that need asdf/homebrew/uv-tool-installed
    binaries (cfgcaddy, uv, etc.) — matches the `environment: PATH: ...`
    block repeated across several roles in the original Ansible playbook.
    """
    home = str(Path.home())
    return (
        f"{home}/.local/bin:{brew_prefix()}/bin:{home}/.asdf/bin:{home}/.asdf/shims:"
        "/opt/homebrew/bin:/home/linuxbrew/.linuxbrew/bin:$PATH"
    )


def shell_ok(command: str, *, sudo: bool = False) -> bool:
    """
    Run `command` and return whether it exited 0, WITHOUT raising or marking
    the host failed on a non-zero exit. The server.Command fact raises
    PyinfraError (and removes the host from the rest of the run — confirmed
    empirically) on any non-zero exit, which is wrong for checks that are
    expected to legitimately fail sometimes (Ansible's `failed_when: false`
    equivalent) — e.g. "is there an active op session yet?".

    `sudo=True` uses pyinfra's own `_sudo` fact argument, which is REQUIRED
    for a real interactive password prompt to work — confirmed by tracing
    pyinfra.connectors.local.LocalConnector.run_shell_command (which never
    attaches a pty: `_get_pty` is popped and discarded) and
    connectors/util.py's execute_command_with_sudo_retry (which only
    getpass()-prompts and retries for a command carrying `_sudo`). A bare
    `sudo` embedded in `command` text bypasses that machinery entirely and
    hangs/times out reading a password even from a real terminal, unless
    sudo's credential cache already happens to be warm — confirmed live:
    `homebrew.py`'s embedded-`sudo` pacman install failed with "sudo: timed
    out reading password" on an interactive run.
    """
    output = host.get_fact(
        Command,
        f"({command}) >/dev/null 2>&1 && echo __OK__ || echo __FAIL__",
        _sudo=sudo,
    )
    return output.strip() == "__OK__"


def shell_capture(command: str, *, sudo: bool = False) -> tuple[int, str]:
    """
    Like shell_ok, but returns (exit_code, combined stdout+stderr) instead of
    a bool — for commands where the caller needs to inspect output text to
    decide whether a non-zero exit is actually fine (e.g. `asdf plugin add`
    exits non-zero for "already added", which isn't a real failure).

    See shell_ok's docstring for why `sudo=True` (pyinfra's `_sudo` fact
    argument), not embedding `sudo` in `command`, is the only way to get a
    real interactive password prompt.
    """
    marker = "__PYINFRA_EXIT__"
    raw = host.get_fact(
        Command,
        f'OUT=$({command} 2>&1); CODE=$?; printf "%s{marker}%d" "$OUT" "$CODE"',
        _sudo=sudo,
    )
    text, _, code_str = raw.rpartition(marker)
    return int(code_str), text
