"""
Builds and installs `zb`/`zbx` (zerobrew: https://github.com/lucasgelfond/zerobrew,
a faster Homebrew-compatible client) from a personal fork
(https://github.com/tstapler/zerobrew, branch linux-reflink-ficlone) that adds a
Linux btrfs/XFS reflink (FICLONE) fast path — upstream only has the macOS
clonefile equivalent. Built from source rather than downloading a prebuilt
binary so it's auditable/trusted, per the user's explicit ask.

No Ansible equivalent — this is new functionality added directly here, not a
port. Opt-in (host.data.zerobrew_enabled, default False in group_data/all.py)
because building Rust from source is slow and this is experimental; run
alongside Homebrew, never replacing it (upstream's own README recommendation).

Everything here is immediate execution (shell_capture), not queued
operations — see homebrew.py's docstring for why: each step (install rustup,
clone, build, install) needs the previous one to have actually finished.
"""

import os

from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.api.exceptions import DeployError

from common import shell_capture, shell_ok

FORK_URL = "https://github.com/tstapler/zerobrew"
FORK_BRANCH = "linux-reflink-ficlone"
CLONE_DIR = os.path.expanduser("~/code/github.com/tstapler/zerobrew")
LOCAL_BIN = os.path.expanduser("~/.local/bin")


def _run(step: str, command: str) -> None:
    code, output = shell_capture(command)
    if code != 0:
        raise DeployError(f"{step} failed ({code}): {output}")


def _ensure_rust_installed() -> None:
    if shell_ok("test -x ~/.cargo/bin/cargo"):
        return
    _run(
        "Install rustup",
        "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y",
    )


def _ensure_fork_cloned() -> None:
    if os.path.isdir(os.path.join(CLONE_DIR, ".git")):
        return
    os.makedirs(os.path.dirname(CLONE_DIR), exist_ok=True)
    _run(
        "Clone zerobrew fork",
        f"git clone --branch {FORK_BRANCH} {FORK_URL} {CLONE_DIR}",
    )


def _build_and_install() -> None:
    cargo_env = 'PATH="$HOME/.cargo/bin:$PATH"'
    _run(
        "Build zerobrew (release)",
        f"cd {CLONE_DIR} && {cargo_env} cargo build --release",
    )

    os.makedirs(LOCAL_BIN, exist_ok=True)
    for binary in ("zb", "zbx"):
        _run(
            f"Install {binary} to ~/.local/bin",
            f'cp "{CLONE_DIR}/target/release/{binary}" "{LOCAL_BIN}/{binary}"',
        )


@deploy("Zerobrew")
def zerobrew() -> None:
    # ponytail: builds once, doesn't auto-update — delete ~/.local/bin/zb and
    # the CLONE_DIR (or just re-run `git pull` + `cargo build` by hand) to
    # pick up a newer commit from the fork.
    if shell_ok(f"test -x {LOCAL_BIN}/zb"):
        return

    _ensure_rust_installed()
    _ensure_fork_cloned()
    _build_and_install()
