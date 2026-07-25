"""
Port of bootstrap/roles/nix/tasks/main.yml — installs Nix via the Determinate
Systems installer if not already present.

Everything here is immediate execution (shell_capture/shell_ok), not queued
operations — see homebrew.py's docstring for why (download must finish
before running the installer, which must finish before the cleanup step).
"""

import http.client
import os
import re

from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.api.exceptions import DeployError

from common import arch, is_macos, shell_capture, shell_ok

NIX_BIN = "/nix/var/nix/profiles/default/bin/nix"
NIX_INSTALL_CHANNEL = "stable"
NIX_INSTALLER_PATH = "/tmp/nix-installer"


def _nix_os_arch() -> tuple[str, str]:
    os_name = "darwin" if is_macos() else "linux"
    raw_arch = arch()
    nix_arch = "aarch64" if raw_arch in ("arm64", "aarch64") else raw_arch
    return os_name, nix_arch


def _resolve_installer_tag(channel: str) -> str:
    # Mirrors the Ansible role's `uri: follow_redirects: none` — the channel
    # URL redirects to a release tag; the tag itself is embedded in the
    # Location header, not returned as response content.
    conn = http.client.HTTPSConnection("install.determinate.systems", timeout=15)
    try:
        conn.request("GET", f"/nix/{channel}")
        resp = conn.getresponse()
        resp.read()  # drain so the connection can close cleanly

        if resp.status in (301, 302, 307, 308):
            location = resp.getheader("Location") or ""
            match = re.search(r"v[0-9]+\.[0-9]+\.[0-9]+", location)
            if not match:
                raise DeployError(
                    f"Could not extract a version tag from nix installer redirect: {location}"
                )
            return match.group(0)

        if resp.status == 200:
            return channel

        raise DeployError(
            f"Unexpected status resolving nix installer channel {channel}: {resp.status}"
        )
    finally:
        conn.close()


def _install_nix() -> None:
    os_name, nix_arch = _nix_os_arch()
    tag = _resolve_installer_tag(NIX_INSTALL_CHANNEL)
    url = (
        f"https://install.determinate.systems/nix/tag/{tag}/"
        f"nix-installer-{nix_arch}-{os_name}"
    )

    code, output = shell_capture(
        f'curl -fsSL -o {NIX_INSTALLER_PATH} "{url}" && chmod 0755 {NIX_INSTALLER_PATH}'
    )
    if code != 0:
        raise DeployError(f"Download nix-installer failed: {output}")

    code, output = shell_capture(f"sudo {NIX_INSTALLER_PATH} install --no-confirm")
    if code != 0:
        raise DeployError(f"nix-installer failed: {output}")

    if os.path.exists(NIX_INSTALLER_PATH):
        os.remove(NIX_INSTALLER_PATH)


@deploy("Nix")
def nix() -> None:
    if not shell_ok(f"test -x {NIX_BIN}"):
        _install_nix()

    code, output = shell_capture(f"{NIX_BIN} --version")
    if code == 0:
        print(output.strip())
