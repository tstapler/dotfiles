"""
Port of bootstrap/roles/claude/tasks/main.yml — installs Claude Code via its
binary installer if not already present, verifying the download's sha256
against the published release manifest.

Everything here is immediate execution (shell_capture/plain Python) — same
reasoning as homebrew.py/nix.py: download, checksum-verify, install, cleanup
each need the previous step to have actually finished.
"""

import hashlib
import http.client
import json
import os
import urllib.request

from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.api.exceptions import DeployError

from common import arch, brew_prefix, is_macos, shell_capture, shell_ok

CLAUDE_RELEASE_CHANNEL = "stable"
DOWNLOADS_DIR = os.path.expanduser("~/.claude/downloads")
INSTALLER_PATH = os.path.join(DOWNLOADS_DIR, "claude-installer")


def _claude_env() -> str:
    home = os.path.expanduser("~")
    return f"PATH={brew_prefix()}/bin:{home}/.local/bin:$PATH"


def _claude_platform() -> str:
    os_name = "darwin" if is_macos() else "linux"
    claude_arch = "arm64" if arch() in ("arm64", "aarch64") else "x64"
    return f"{os_name}-{claude_arch}"


def _fetch(path: str) -> str:
    conn = http.client.HTTPSConnection("downloads.claude.ai", timeout=15)
    try:
        conn.request("GET", path)
        resp = conn.getresponse()
        if resp.status != 200:
            raise DeployError(
                f"GET https://downloads.claude.ai{path} returned {resp.status}"
            )
        return resp.read().decode()
    finally:
        conn.close()


def _install_claude() -> None:
    platform = _claude_platform()
    version = _fetch(f"/claude-code-releases/{CLAUDE_RELEASE_CHANNEL}").strip()
    manifest = json.loads(_fetch(f"/claude-code-releases/{version}/manifest.json"))
    checksum = manifest["platforms"][platform]["checksum"]

    os.makedirs(DOWNLOADS_DIR, mode=0o755, exist_ok=True)

    url = (
        f"https://downloads.claude.ai/claude-code-releases/{version}/{platform}/claude"
    )
    urllib.request.urlretrieve(url, INSTALLER_PATH)

    with open(INSTALLER_PATH, "rb") as f:
        actual_checksum = hashlib.sha256(f.read()).hexdigest()
    if actual_checksum != checksum:
        os.remove(INSTALLER_PATH)
        raise DeployError(
            f"Claude Code installer checksum mismatch: expected {checksum}, got {actual_checksum}"
        )

    os.chmod(INSTALLER_PATH, 0o755)

    code, output = shell_capture(f"{_claude_env()} {INSTALLER_PATH} install")
    if code != 0:
        raise DeployError(f"Claude Code installer failed: {output}")

    os.remove(INSTALLER_PATH)


@deploy("Claude Code")
def claude() -> None:
    if not shell_ok(f"{_claude_env()} claude --version"):
        _install_claude()

    code, output = shell_capture(f"{_claude_env()} claude --version")
    if code != 0:
        raise DeployError(f"Claude Code install verification failed: {output}")
    print(f"Claude Code installed: {output.strip()}")
