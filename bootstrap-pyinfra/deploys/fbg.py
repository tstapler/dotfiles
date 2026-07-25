"""
Port of bootstrap/roles/fbg/tasks/main.yml — FBG (Fanatics Gaming)-specific
bootstrap: SSH host aliases (github.com = work, github-personal = personal),
the work git identity, and the private dotfiles-fbg repo.

Work-specific and opt-in — see main.py, only called when
host.data.fbg_enabled is truthy (auto-detected from hostname there, matching
bootstrap/run.sh's own `[Ff][Bb][Gg]-*` auto-detection, since this deploy has
no access to that shell logic directly).

Not verified by execution on this (non-FBG, personal) machine — static code
review only. `--dry` does NOT make this safe to test here: this file is
entirely immediate-execution (plain Python/shell_capture, see below), and
`--dry` only withholds queued pyinfra operations — it was actually run once
during development by mistake, which wrote ~/.gitconfig.fbg (a real work
identity), created ~/.ssh/config, wrote SSH aliases, created ~/WorkProjects,
and attempted a real git clone of the private dotfiles-fbg repo. All of it
was manually reverted. See README.md's "`--dry` does NOT protect immediate
execution" section. Needs live verification on an actual FBG machine.

Everything here is plain Python / shell_capture (immediate execution), not
queued pyinfra operations: the SSH auth check later in this deploy needs the
alias file to have actually been written first (the `Host github.com` alias
happens to coincide with SSH's own default key path here, which would mask a
queued-vs-immediate ordering bug rather than surface it — not something to
rely on). See homebrew.py's docstring for the general rule.
"""

import os

from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439

from common import shell_capture
from deploys.github import PERSONAL_KEY, PRIMARY_KEY

FBG_GIT_NAME = "Tyler Stapler"
FBG_WORK_EMAIL = "Tyler.Stapler@betfanatics.com"

SSH_CONFIG_D = os.path.expanduser("~/.ssh/config.d")
SSH_CONFIG = os.path.expanduser("~/.ssh/config")
GITCONFIG_FBG = os.path.expanduser("~/.gitconfig.fbg")
WORK_PROJECTS_DIR = os.path.expanduser("~/WorkProjects")
FBG_DOTFILES_DIR = os.path.join(WORK_PROJECTS_DIR, "dotfiles-fbg")
FBG_DOTFILES_REPO = "git@github.com:TylerStaplerAtFanatics/dotfiles-fbg.git"

# Ansible's include_tasks-based FBG-specific-tasks hook has no pyinfra
# equivalent (same reasoning as deploys/overlays.py's legacy-hook handling) —
# it's a private repo's Ansible task file, dynamically interpreted. Not
# implementing the "run it" side; print a migration nudge if it's ever
# present without a pyinfra-native replacement.
FBG_DEPLOY_HOOK = os.path.join(FBG_DOTFILES_DIR, "deploy.py")
FBG_LEGACY_HOOK = os.path.join(FBG_DOTFILES_DIR, "tasks", "main.yml")

_SSH_CONFIG_MARKER_BEGIN = "# BEGIN ANSIBLE MANAGED — config.d include"
_SSH_CONFIG_MARKER_END = "# END ANSIBLE MANAGED — config.d include"

_SSH_ALIASES = f"""\
# Work account is the default for github.com.
Host github.com
  HostName github.com
  User git
  IdentityFile {PRIMARY_KEY}
  IdentitiesOnly yes

# Personal account, selected by using github-personal in the remote URL.
Host github-personal
  HostName github.com
  User git
  IdentityFile {PERSONAL_KEY}
  IdentitiesOnly yes
"""

_WORK_GITCONFIG = f"""\
# Managed by the fbg deploy. Applied to ~/WorkProjects/* via the
# includeIf in the main ~/.gitconfig.
[user]
    name = {FBG_GIT_NAME}
    email = {FBG_WORK_EMAIL}
"""


def _write_ssh_host_aliases() -> None:
    os.makedirs(SSH_CONFIG_D, mode=0o700, exist_ok=True)
    os.chmod(SSH_CONFIG_D, 0o700)

    alias_path = os.path.join(SSH_CONFIG_D, "github")
    with open(alias_path, "w") as f:
        f.write(_SSH_ALIASES)
    os.chmod(alias_path, 0o600)

    superseded = os.path.join(SSH_CONFIG_D, "github-personal")
    if os.path.exists(superseded):
        os.remove(superseded)


def _ensure_ssh_config_includes_config_d() -> None:
    content = ""
    if os.path.isfile(SSH_CONFIG):
        with open(SSH_CONFIG) as f:
            content = f.read()

    if _SSH_CONFIG_MARKER_BEGIN in content:
        return

    block = f"{_SSH_CONFIG_MARKER_BEGIN}\nInclude ~/.ssh/config.d/*\n{_SSH_CONFIG_MARKER_END}\n"
    with open(SSH_CONFIG, "w") as f:
        f.write(block + ("\n" + content if content else ""))
    os.chmod(SSH_CONFIG, 0o600)


def _write_work_git_identity() -> None:
    with open(GITCONFIG_FBG, "w") as f:
        f.write(_WORK_GITCONFIG)
    os.chmod(GITCONFIG_FBG, 0o644)


def _clone_fbg_dotfiles_if_authenticated() -> None:
    _, output = shell_capture(
        "ssh -T -o BatchMode=yes -o StrictHostKeyChecking=accept-new git@github.com"
    )
    authenticated = "successfully authenticated" in output

    if not authenticated:
        print(
            "Work SSH access to github.com is not active yet — the private "
            "dotfiles-fbg\n"
            "repo was not cloned. Ensure the github deploy registered the primary key "
            "with\n"
            "the work account (set github_op_token_path or authenticate gh), then "
            "re-run this deploy."
        )
        return

    os.makedirs(WORK_PROJECTS_DIR, mode=0o755, exist_ok=True)

    ssh_env = 'GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"'
    if not os.path.isdir(os.path.join(FBG_DOTFILES_DIR, ".git")):
        code, output = shell_capture(
            f"{ssh_env} git clone {FBG_DOTFILES_REPO} {FBG_DOTFILES_DIR}"
        )
    else:
        code, output = shell_capture(f"{ssh_env} git -C {FBG_DOTFILES_DIR} pull")
    if code != 0:
        print(f"dotfiles-fbg clone/pull failed: {output}")
        return

    if os.path.isfile(FBG_LEGACY_HOOK) and not os.path.isfile(FBG_DEPLOY_HOOK):
        print(
            f"dotfiles-fbg ships {FBG_LEGACY_HOOK} (Ansible-only, not supported "
            f"here) but no {FBG_DEPLOY_HOOK} — migrate it to run under the "
            "pyinfra bootstrap."
        )


@deploy("FBG")
def fbg() -> None:
    _write_ssh_host_aliases()
    _ensure_ssh_config_includes_config_d()
    _write_work_git_identity()
    os.makedirs(WORK_PROJECTS_DIR, mode=0o755, exist_ok=True)

    _clone_fbg_dotfiles_if_authenticated()
