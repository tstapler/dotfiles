"""
Port of bootstrap/roles/dotfiles/tasks/main.yml — installs/updates cfgcaddy
(the symlinking tool) via uv, then links the repo's dotfiles. Handles the
~/.gitconfig special case: on machines where a corporate identity tool owns
it, we don't symlink over it — see the comment on _link_gitconfig below.
"""

import os
from pathlib import Path

from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.operations import files, server

from common import brew_prefix, dev_tools_path_env, shell_ok

DOTFILES_DIR = "~/dotfiles"


def _ensure_cfgcaddy_installed() -> None:
    brew = brew_prefix()

    if not shell_ok(f"PATH={brew}/bin:$PATH which uv"):
        server.shell(
            name="Install uv via Homebrew",
            commands=[f"{brew}/bin/brew install uv"],
        )

    # --force is idempotent and ensures version bumps in cfgcaddy/ are picked
    # up even when an older copy is already installed.
    server.shell(
        name="Install/upgrade cfgcaddy via uv tool install",
        commands=[
            f'PATH="{dev_tools_path_env()}" {brew}/bin/uv tool install --force {DOTFILES_DIR}/cfgcaddy'
        ],
    )


def _link_dotfiles() -> None:
    if not shell_ok("test -f ~/.cfgcaddy.yml"):
        server.shell(
            name="Init cfgcaddy (symlinks .cfgcaddy.yml to ~/.cfgcaddy.yml)",
            commands=[f'PATH="{dev_tools_path_env()}" cfgcaddy init {DOTFILES_DIR} ~'],
        )

    server.shell(
        name="Link dotfiles via cfgcaddy",
        commands=[f'PATH="{dev_tools_path_env()}" cfgcaddy link -y'],
    )


def _link_gitconfig() -> None:
    # .gitconfig is deliberately excluded from the cfgcaddy links manifest: on
    # machines where a corporate identity/credential tool owns ~/.gitconfig,
    # symlinking over it would break that tool's auto-managed proxy/
    # credential block on its next refresh. So the two cases are handled
    # explicitly:
    #   - tool-managed -> render our config into ~/.config/git/config
    #     instead (lower-precedence global tier, so the tool's file always
    #     wins on any key it actually sets; plain-user-owned, no sudo needed;
    #     read by whichever `git` ends up on PATH, Apple's /usr/bin/git
    #     included).
    #   - normal file -> back it up once, then symlink it like everything
    #     else cfgcaddy manages.
    home = Path.home()
    gitconfig = home / ".gitconfig"
    dotfiles_gitconfig = Path(os.path.expanduser(DOTFILES_DIR)) / ".gitconfig"

    exists = gitconfig.exists()
    is_symlink = gitconfig.is_symlink()
    is_managed = exists and not is_symlink and "AUTOCONFIG" in gitconfig.read_text()

    if is_managed:
        files.directory(
            name="Ensure ~/.config/git exists",
            path=str(home / ".config" / "git"),
            present=True,
            mode="0755",
        )
        files.put(
            name="Render personal git identity into ~/.config/git/config (tool-managed ~/.gitconfig)",
            src=str(dotfiles_gitconfig),
            dest=str(home / ".config" / "git" / "config"),
            mode="0644",
        )
        return

    if exists and not is_symlink:
        backup = home / ".gitconfig.pre-dotfiles-bak"
        if not backup.exists():
            server.shell(
                name="Back up pre-existing ~/.gitconfig before symlinking over it",
                commands=[f'cp "{gitconfig}" "{backup}"'],
            )

    files.link(
        name="Symlink ~/.gitconfig to dotfiles copy (normal, non-tool-managed machines)",
        path=str(gitconfig),
        target=str(dotfiles_gitconfig),
        force=True,
    )


@deploy("Dotfiles")
def dotfiles() -> None:
    _ensure_cfgcaddy_installed()
    _link_dotfiles()
    _link_gitconfig()
