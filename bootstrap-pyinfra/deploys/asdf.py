"""
Port of bootstrap/roles/asdf/tasks/main.yml.

asdf 0.16+ (the Go rewrite). Installed as a Homebrew binary — no git clone
and no asdf.sh sourcing. ~/.asdf is used purely as ASDF_DATA_DIR, so a legacy
(shell-based) install's plugins/installs/shims/downloads are reused.

Everything here runs via shell_capture/plain Python (immediate execution),
not queued pyinfra operations — see the top-of-file comment in homebrew.py
for why: every step here (plugin add, reshim, tool install) needs the
previous one to have actually happened, not just be queued for later.
"""

import os
import shutil

from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.api.exceptions import DeployError

from common import brew_prefix, shell_capture

DOTFILES_DIR = os.path.expanduser("~/dotfiles")
TOOL_VERSIONS = os.path.join(DOTFILES_DIR, ".tool-versions")
ASDF_DATA_DIR = os.path.expanduser("~/.asdf")

# Non-fatal asdf plugin add outcomes — mirrors the Ansible role's
# failed_when: exactly.
_TOLERATED_PLUGIN_ADD_OUTPUT = (
    "already added",
    "already installed",
    "not found in repository",
)


def _tool_names() -> list[str]:
    if not os.path.isfile(TOOL_VERSIONS):
        return []
    with open(TOOL_VERSIONS) as f:
        return [line.split()[0] for line in f if line.strip()]


def _asdf_env(brew_bin_dir: str) -> str:
    return (
        f"PATH={brew_bin_dir}:{ASDF_DATA_DIR}/shims:$PATH ASDF_DATA_DIR={ASDF_DATA_DIR}"
    )


def _migrate_legacy_install() -> None:
    legacy_marker = os.path.join(ASDF_DATA_DIR, "asdf.sh")
    if not os.path.isfile(legacy_marker):
        return

    for name in (
        "asdf.sh",
        "asdf.fish",
        "asdf.elv",
        "bin",
        "lib",
        "completions",
        ".git",
    ):
        path = os.path.join(ASDF_DATA_DIR, name)
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path)
        elif os.path.exists(path) or os.path.islink(path):
            os.remove(path)


def _reshim_after_migration(env: str) -> None:
    # Only meaningful right after a legacy migration — matches the Ansible
    # role's `when: asdf_legacy.stat.exists`, checked by the caller.
    code, output = shell_capture(f"{env} asdf reshim")
    if code != 0:
        raise DeployError(f"asdf reshim failed after legacy migration: {output}")


def _add_plugins(env: str, tool_names: list[str]) -> None:
    for name in tool_names:
        code, output = shell_capture(f"{env} asdf plugin add {name}")
        if code == 0 or any(s in output for s in _TOLERATED_PLUGIN_ADD_OUTPUT):
            continue
        raise DeployError(f"asdf plugin add {name} failed: {output}")


def _install_tool_versions(env: str) -> None:
    code, output = shell_capture(f"cd {DOTFILES_DIR} && {env} asdf install")
    if code != 0:
        raise DeployError(f"asdf install failed: {output}")


@deploy("asdf")
def asdf() -> None:
    brew = brew_prefix()
    code, output = shell_capture(f"{brew}/bin/brew install asdf")
    if code != 0:
        raise DeployError(f"Install asdf via Homebrew failed: {output}")

    had_legacy_install = os.path.isfile(os.path.join(ASDF_DATA_DIR, "asdf.sh"))
    _migrate_legacy_install()

    env = _asdf_env(f"{brew}/bin")
    if had_legacy_install:
        _reshim_after_migration(env)

    tool_names = _tool_names()
    if tool_names:
        _add_plugins(env, tool_names)
        _install_tool_versions(env)
