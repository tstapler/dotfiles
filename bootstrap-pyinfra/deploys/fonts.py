"""Port of bootstrap/roles/fonts/tasks/main.yml — installs the Meslo Nerd Font."""

import glob
import os

from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.operations import brew, files

from common import is_macos, is_wsl, shell_ok

FONTS_DIR = os.path.expanduser("~/.local/share/fonts")
MESLO_ZIP = "/tmp/Meslo.zip"
MESLO_URL = "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/Meslo.zip"


def _refresh_font_cache() -> None:
    for _ in range(3):
        if shell_ok("fc-cache -fv"):
            return
    print(
        "fc-cache failed after retries — non-fatal, fontconfig falls back to "
        "scanning directories directly and the cache rebuilds lazily on next use."
    )


@deploy("Fonts")
def fonts() -> None:
    if is_wsl():
        print(
            "Skipping fonts role on WSL2 — install Nerd Fonts on Windows side manually."
        )
        return

    if is_macos():
        brew.casks(
            name="Install Meslo Nerd Font (macOS via Homebrew cask)",
            casks=["font-meslo-lg-nerd-font"],
            present=True,
        )
        return

    files.directory(
        name="Ensure fonts directory exists (Linux)",
        path=FONTS_DIR,
        present=True,
        mode="0755",
    )

    already_installed = bool(glob.glob(os.path.join(FONTS_DIR, "MesloLG*")))
    if not already_installed:
        files.download(
            name="Download Meslo Nerd Font zip (Linux)",
            src=MESLO_URL,
            dest=MESLO_ZIP,
        )
        files.unarchive(
            name="Unzip Meslo Nerd Font (Linux)",
            src=MESLO_ZIP,
            dest=FONTS_DIR,
            remote_src=True,
        )

    _refresh_font_cache()
