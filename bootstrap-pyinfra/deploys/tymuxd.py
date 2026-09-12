"""
Port of bootstrap/roles/tymuxd/tasks/main.yml — symlinks the pinned tymuxd
binary (stapler-squad's tmux backend) onto PATH from a local stapler-squad
checkout, if one exists on this machine.

`tymuxd --help` (like every invocation of this binary) starts the daemon
rather than printing help and exiting — see
stapler-squad/docs/reference/bundling-tymuxd.md — so presence detection wraps
it in `timeout 3` and discriminates on exit code: 2 is the shell's own
"command not found" (ENOENT) convention, not something tymuxd itself
returns. Anything else (1 for AddrInUse, 124 for a timeout kill) means the
binary was found and ran.
"""

import os

from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.operations import files, server

from common import brew_prefix, shell_capture

STAPLER_SQUAD_CHECKOUTS = (
    os.path.expanduser("~/Programming/stapler-squad"),
    os.path.expanduser("~/code/github.com/tstapler/stapler-squad"),
)
LOCAL_BIN = os.path.expanduser("~/.local/bin")
TYMUXD_DEST = os.path.join(LOCAL_BIN, "tymuxd")

_ENOENT = 2


def tymuxd_present(rc: int) -> bool:
    """rc==2 is the shell's "command not found", not tymuxd exiting — anything
    else means the binary was found and ran (see module docstring)."""
    return rc != _ENOENT


def _find_stapler_squad_checkout() -> str | None:
    for checkout in STAPLER_SQUAD_CHECKOUTS:
        code, _ = shell_capture(f'test -f "{checkout}/scripts/fetch-tymuxd.sh"')
        if code == 0:
            return checkout
    return None


@deploy("tymuxd")
def tymuxd() -> None:
    path_env = f"PATH={brew_prefix()}/bin:{LOCAL_BIN}:$PATH"
    rc, _ = shell_capture(f"{path_env} timeout 3 tymuxd --help")
    if tymuxd_present(rc):
        return

    checkout = _find_stapler_squad_checkout()
    if checkout is None:
        print(
            "Skipping tymuxd install: no stapler-squad checkout found at\n"
            "  ~/Programming/stapler-squad or\n"
            "  ~/code/github.com/tstapler/stapler-squad\n"
            "Clone it (see stapler-squad/CLAUDE.md's Repo Placement) and re-run\n"
            "this deploy if stapler-squad's tymux backend is needed on this machine."
        )
        return

    # Reuses stapler-squad's own fetch script (checksum-verified against
    # scripts/tymuxd-checksums.txt) rather than re-deriving the release
    # version/platform-target/checksum mapping here.
    server.shell(
        name="Fetch pinned tymuxd binary via stapler-squad's own fetch script",
        commands=[f"cd {checkout} && ./scripts/fetch-tymuxd.sh"],
    )
    files.directory(
        name="Ensure ~/.local/bin exists",
        path=LOCAL_BIN,
        present=True,
        mode="0755",
    )
    files.link(
        name="Symlink tymuxd onto PATH",
        path=TYMUXD_DEST,
        target=os.path.join(checkout, "session/tymux/embed/tymuxd"),
        force=True,
    )
