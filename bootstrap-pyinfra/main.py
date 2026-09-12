"""
Entrypoint. Mirrors bootstrap/playbook.yml's `roles:` list — deploys are
called in the same order so behavior is easy to eyeball against the Ansible
original during the migration. Roles get removed from this list (and from
playbook.yml's roles: list) one at a time as they're ported and trusted.

Run with: uv run pyinfra inventory.py main.py [--dry] [-y]
"""

from pyinfra import host  # type: ignore[attr-defined]  # pyinfra/#439

from common import is_fbg_machine, is_macos, is_wsl
from deploys.ai_tools import ai_tools
from deploys.asdf import asdf
from deploys.claude import claude
from deploys.dotfiles import dotfiles
from deploys.fbg import fbg
from deploys.fonts import fonts
from deploys.github import github
from deploys.homebrew import homebrew
from deploys.llm_sync import llm_sync
from deploys.memory_optimizer import memory_optimizer
from deploys.nix import nix
from deploys.overlays import overlays
from deploys.pi import pi
from deploys.secrets import secrets
from deploys.shell import shell
from deploys.ssh_bastion_client import ssh_bastion_client
from deploys.sudo_mfa import sudo_mfa
from deploys.tymuxd import tymuxd
from deploys.zerobrew import zerobrew

claude()
homebrew()
ai_tools()
pi()

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
tymuxd()

if is_fbg_machine():
    fbg()

ssh_bastion_client()

if host.data.get("sudo_mfa_enabled"):
    sudo_mfa()

if host.data.get("memory_optimizer_enabled") and not is_wsl() and not is_macos():
    memory_optimizer()
