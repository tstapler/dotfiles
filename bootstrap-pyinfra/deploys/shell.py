"""
Port of bootstrap/roles/shell/tasks/main.yml — sets zsh as the default login
shell and clones zplug (the zsh plugin manager) if missing.

Both steps are plain queued pyinfra operations (server.user, git.repo), not
immediate shell_capture calls — unlike homebrew.py/asdf.py/nix.py, nothing
else in this run needs to react to these two specific results, so there's no
ordering risk (see homebrew.py's docstring for the general rule).
"""

import os

from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.operations import git, server

ZPLUG_REPO = "https://github.com/tstapler/zplug"
ZPLUG_DIR = os.path.expanduser("~/.zplug")


@deploy("Shell")
def shell() -> None:
    server.user(
        name="Set zsh as default shell",
        user=os.environ["USER"],
        shell="/bin/zsh",
        _sudo=True,
    )

    git.repo(
        name="Clone zplug if missing",
        src=ZPLUG_REPO,
        dest=ZPLUG_DIR,
        pull=False,
    )
