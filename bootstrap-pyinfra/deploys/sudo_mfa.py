"""
Port of bootstrap/roles/sudo-mfa/tasks/main.yml — layers YubiKey/TOTP MFA
onto sudo via PAM, Arch-only, opt-in (see main.py: only called if
host.data.sudo_mfa_enabled is truthy, matching the Ansible role's
`when: sudo_mfa_enabled | default(false) | bool`).
"""

from pathlib import Path

from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.operations import files, pacman, server

from common import is_archlinux

SUDO_PAM_SRC = str(Path(__file__).parent / "files" / "sudo.pam")
SUDO_PAM_DEST = "/etc/pam.d/sudo"


@deploy("Sudo MFA")
def sudo_mfa() -> None:
    if not is_archlinux():
        return

    pacman.packages(
        name="Install PAM MFA packages (Arch)",
        packages=["pam-u2f", "libpam-google-authenticator", "libfido2"],
        present=True,
        _sudo=True,
    )

    # pyinfra has no built-in "backup before overwrite" flag on files.put/
    # files.template (confirmed — only files.link/files.directory have
    # force_backup). Ansible's `copy: backup: true` equivalent done by hand.
    server.shell(
        name="Back up existing /etc/pam.d/sudo if present",
        commands=[
            f"test -f {SUDO_PAM_DEST} && cp -a {SUDO_PAM_DEST} {SUDO_PAM_DEST}.bak.$(date +%s) || true"
        ],
        _sudo=True,
    )

    files.put(
        name="Install /etc/pam.d/sudo with optional TOTP/YubiKey MFA",
        src=SUDO_PAM_SRC,
        dest=SUDO_PAM_DEST,
        user="root",
        group="root",
        mode="0644",
        _sudo=True,
    )

    print(
        "sudo now accepts EITHER your password, a registered YubiKey touch, or a TOTP code.\n"
        "A backup of the previous /etc/pam.d/sudo was saved alongside it (if one existed).\n\n"
        "Enroll TOTP (per-user, interactive — run yourself):\n"
        "  google-authenticator\n"
        "Then scan the QR into 1Password (or any authenticator app).\n\n"
        "Enroll a YubiKey later, once you have one (per-user, interactive):\n"
        "  pamu2fcfg > ~/.config/Yubico/u2f_keys"
    )
