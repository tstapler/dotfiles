"""
Entrypoint. Mirrors bootstrap/playbook.yml's `roles:` list — deploys are
called in the same order so behavior is easy to eyeball against the Ansible
original during the migration. Roles get removed from this list (and from
playbook.yml's roles: list) one at a time as they're ported and trusted.

Run with: uv run pyinfra inventory.py main.py [--dry] [-y]
"""

from pyinfra import host  # type: ignore[attr-defined]  # pyinfra/#439

from common import is_fbg_machine
from deploys.asdf import asdf
from deploys.claude import claude
from deploys.dotfiles import dotfiles
from deploys.fbg import fbg
from deploys.fonts import fonts
from deploys.github import github
from deploys.homebrew import homebrew
from deploys.llm_sync import llm_sync
from deploys.nix import nix
from deploys.overlays import overlays
from deploys.secrets import secrets
from deploys.shell import shell
from deploys.sudo_mfa import sudo_mfa
from deploys.zerobrew import zerobrew

claude()
homebrew()

if host.data.get("zerobrew_enabled"):
    zerobrew()

dotfiles()
overlays()
llm_sync()
shell()
asdf()
nix()
secrets()
fonts()
github()

if is_fbg_machine():
    fbg()

if host.data.get("sudo_mfa_enabled"):
    sudo_mfa()
