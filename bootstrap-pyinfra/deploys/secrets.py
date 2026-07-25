"""
Port of bootstrap/roles/secrets/tasks/main.yml.

On macOS, the 1Password desktop app comes from the Brewfile cask (handled by
the still-Ansible `homebrew` role for now) — this deploy only installs it on
Linux, via the official signed .tar.gz (not Flatpak/Snap — those sandboxed
builds can't do CLI/SSH-agent/MCP integration at all, confirmed by inspecting
the sandbox directly: no op/1password-mcp binary ships inside it).
"""

from pyinfra import host  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.api.exceptions import DeployError
from pyinfra.facts.server import Arch
from pyinfra.operations import files, pacman, server

from common import brew_prefix, is_archlinux, is_macos, shell_ok
from operations import gpg

ONEPASSWORD_BIN = "/opt/1Password/1password"
TMP_KEY = "/tmp/1password.asc"
TMP_KEYRING = "/tmp/1password-keyring.gpg"
TMP_TARBALL = "/tmp/1password-latest.tar.gz"
TMP_SIG = "/tmp/1password-latest.tar.gz.sig"


def _install_1password_linux() -> None:
    # shell_ok(test -e), not a File fact: File returns False (not just None)
    # for a symlink — see _check_op_cli_and_session below for where that bit.
    if shell_ok(f"test -e {ONEPASSWORD_BIN}"):
        return  # ponytail: installs once, doesn't auto-update — see after-install.sh step below

    arch = "aarch64" if host.get_fact(Arch) == "aarch64" else "x86_64"

    files.download(
        name="Download 1Password signing key",
        src="https://downloads.1password.com/linux/keys/1password.asc",
        dest=TMP_KEY,
    )
    server.shell(
        name="Import 1Password signing key into a scratch keyring",
        commands=[
            f"gpg --no-default-keyring --keyring {TMP_KEYRING} --import {TMP_KEY}"
        ],
    )
    files.download(
        name="Download 1Password tarball",
        src=f"https://downloads.1password.com/linux/tar/stable/{arch}/1password-latest.tar.gz",
        dest=TMP_TARBALL,
    )
    files.download(
        name="Download 1Password tarball signature",
        src=f"https://downloads.1password.com/linux/tar/stable/{arch}/1password-latest.tar.gz.sig",
        dest=TMP_SIG,
    )
    gpg.verify(
        name="Verify 1Password tarball signature",
        signature=TMP_SIG,
        target=TMP_TARBALL,
        keyring=TMP_KEYRING,
    )
    files.directory(
        name="Ensure /opt/1Password directory exists",
        path="/opt/1Password",
        present=True,
        mode="0755",
        _sudo=True,
    )
    files.unarchive(
        name="Extract 1Password into /opt/1Password",
        src=TMP_TARBALL,
        dest="/opt/1Password",
        remote_src=True,
        extra_opts=["--strip-components=1"],
        _sudo=True,
    )
    server.shell(
        name="Run 1Password after-install script",
        commands=["/opt/1Password/after-install.sh"],
        _sudo=True,
    )
    for path in (TMP_KEY, TMP_KEYRING, TMP_TARBALL, TMP_SIG):
        files.file(
            name=f"Clean up install artifact {path}",
            path=path,
            present=False,
        )


def _print_biometric_unlock_instructions() -> None:
    print(
        "Skip `op signin`/session-token juggling entirely by turning on 1Password's\n"
        "CLI biometric unlock (one-time, in the desktop app GUI — can't be scripted):\n"
        "  1. Open and unlock the 1Password desktop app.\n"
        '  2. Settings > Developer > "Integrate with 1Password CLI".\n'
        "  3. Set your Linux user's system authentication method to fingerprint or\n"
        "     password under your system settings.\n"
        "Once enabled, any `op` command (e.g. `op inject`, `op whoami`) prompts via\n"
        "the PolKit agent instead of requiring `eval $(op signin)` or an OP_SESSION\n"
        "env var. i3 doesn't ship a PolKit agent — lxqt-policykit was installed\n"
        "above and is autostarted from .i3/config. KDE and GNOME already ship\n"
        "their own agent, so this only matters for minimal WMs like i3."
    )


def _check_op_cli_and_session() -> None:
    op_bin = f"{brew_prefix()}/bin/op"

    # Not `host.get_fact(File, op_bin)`: File returns False (not None) for a
    # symlink — confirmed live, since Homebrew's `op` is a symlink into the
    # Caskroom, which made this check always report "not found". `test -x`
    # follows symlinks correctly.
    if not shell_ok(f"test -x {op_bin}"):
        raise DeployError(
            "1Password CLI (op) is required for secrets management but was not "
            f"found at {op_bin}.\n"
            "Install it: brew install --cask 1password-cli\n"
            "Then re-run this deploy."
        )

    has_session = shell_ok(f'{op_bin} account list | grep -q "."')
    if not has_session:
        print(
            "No active 1Password session found. Sign in with:\n"
            "  eval $(op signin)\n"
            "Then re-run this deploy.\n"
            "Skipping dry-run secret injection test."
        )
        return

    inject_ok = shell_ok(
        f'echo "{{{{ op://Personal/test-placeholder/password }}}}" | {op_bin} inject --dry-run'
    )
    print(f"op inject dry-run: {'PASS' if inject_ok else 'FAIL — check op session'}")


@deploy("Secrets (1Password)")
def secrets() -> None:
    if not is_macos():
        _install_1password_linux()

        if is_archlinux():
            pacman.packages(
                name="Install PolKit authentication agent for CLI biometric unlock",
                packages=["lxqt-policykit"],
                present=True,
                _sudo=True,
            )

        _print_biometric_unlock_instructions()

    _check_op_cli_and_session()
