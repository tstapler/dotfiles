"""
Port of bootstrap/roles/github/tasks/main.yml — SSH key generation, gh CLI
auth (via 1Password token references), and SSH key registration for the
primary GitHub account and, on FBG machines, a second personal account.

Everything here is immediate execution (shell_capture/shell_ok) — this role
is a long chain of "check state, act on the real result" steps (Ansible's
`register:` variables reused across later tasks), so it needs the same
sequential-not-queued treatment as homebrew.py/asdf.py/nix.py.
"""

import os

from pyinfra import host  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.api.exceptions import DeployError
from pyinfra.operations import files

from common import brew_prefix, github_personal_user, hostname, shell_capture, shell_ok

SSH_DIR = os.path.expanduser("~/.ssh")
PRIMARY_KEY = os.path.join(SSH_DIR, "id_ed25519")
PERSONAL_KEY = os.path.join(SSH_DIR, "id_ed25519_personal")

_NON_FATAL_KEY_ADD_MARKERS = ("already",)
_MISSING_SCOPE_MARKER = "admin:public_key"


def _gh_env() -> str:
    return f"PATH={brew_prefix()}/bin:$PATH"


def _seed_known_hosts() -> None:
    known_hosts = os.path.join(SSH_DIR, "known_hosts")
    shell_capture(
        f"ssh-keygen -F github.com -f {known_hosts} > /dev/null 2>&1 || "
        f"ssh-keyscan -H github.com >> {known_hosts}"
    )


def _generate_keypair(path: str, comment: str) -> None:
    if os.path.isfile(path):
        return
    code, output = shell_capture(
        f'ssh-keygen -t ed25519 -f {path} -N "" -C "{comment}"'
    )
    if code != 0:
        raise DeployError(f"ssh-keygen for {path} failed: {output}")


def _gh_auth_status() -> bool:
    return shell_ok(f"{_gh_env()} gh auth status")


def _authenticate(op_token_path: str) -> None:
    code, output = shell_capture(
        f'{_gh_env()} op read "{op_token_path}" | gh auth login --with-token'
    )
    if code != 0:
        raise DeployError(f"gh auth login via {op_token_path} failed: {output}")


def _personal_token(personal_user: str) -> tuple[bool, str]:
    code, output = shell_capture(f"{_gh_env()} gh auth token --user {personal_user}")
    return code == 0, output.strip()


def _register_key(pub_key_path: str, title: str, gh_token: str | None = None) -> None:
    env = _gh_env()
    if gh_token:
        env = f'{env} GH_TOKEN="{gh_token}"'

    code, output = shell_capture(
        f'{env} gh ssh-key add {pub_key_path} --title "{title}"'
    )
    if code == 0:
        return

    lower_output = output.lower()
    if any(marker in lower_output for marker in _NON_FATAL_KEY_ADD_MARKERS):
        return

    if _MISSING_SCOPE_MARKER in output:
        raise DeployError(
            f'gh CLI token is missing the "{_MISSING_SCOPE_MARKER}" scope needed to '
            f"register SSH keys ({title}).\n"
            f"Grant it: gh auth refresh -h github.com -s {_MISSING_SCOPE_MARKER}\n"
            "Then re-run this deploy."
        )

    raise DeployError(f"gh ssh-key add {pub_key_path} failed: {output}")


@deploy("GitHub")
def github() -> None:
    files.directory(
        name="Ensure ~/.ssh has correct permissions",
        path=SSH_DIR,
        present=True,
        mode="0700",
    )
    _seed_known_hosts()

    comment = f"{os.environ['USER']}@{hostname()}"
    _generate_keypair(PRIMARY_KEY, comment)

    personal_user = github_personal_user() or ""
    if personal_user:
        _generate_keypair(PERSONAL_KEY, f"personal-{comment}")

    op_token_path = host.data.get("github_op_token_path") or ""
    personal_op_token_path = host.data.get("github_personal_op_token_path") or ""

    primary_authed = _gh_auth_status()
    if not primary_authed and op_token_path:
        _authenticate(op_token_path)
        primary_authed = _gh_auth_status()

    if not primary_authed:
        print(
            "GitHub CLI is not authenticated and github_op_token_path is not set.\n"
            "SSH keys were still generated, but registering them with GitHub\n"
            "(gh ssh-key add) will be skipped, so private/personal repo access over\n"
            "SSH won't work until you either:\n"
            "  gh auth login\n"
            "or set github_op_token_path to your 1Password token path "
            "(e.g. op://Personal/GitHub/token)\n"
            "then re-run this deploy.\n"
            "Public github.com repos remain reachable over HTTPS without any of this."
        )

    personal_authed = False
    if personal_user:
        personal_authed, _ = _personal_token(personal_user)
        if not personal_authed and personal_op_token_path:
            _authenticate(personal_op_token_path)
            personal_authed, _ = _personal_token(personal_user)

        if not personal_authed and not personal_op_token_path:
            print(
                f"Personal GitHub account '{personal_user}' is not authenticated\n"
                "and github_personal_op_token_path is not set.\n"
                "SSH key was still generated, but registering it with GitHub\n"
                "(gh ssh-key add) will be skipped, so personal repo access over SSH\n"
                "won't work until you either:\n"
                "  gh auth login\n"
                "and sign in with your personal account, or set "
                "github_personal_op_token_path\n"
                "(e.g. op://Personal/GitHub Personal/token) then re-run this deploy."
            )

    if primary_authed:
        _register_key(f"{PRIMARY_KEY}.pub", f"{hostname()}-primary")

    if personal_user and personal_authed:
        _, token = _personal_token(personal_user)
        _register_key(f"{PERSONAL_KEY}.pub", f"{hostname()}-personal", gh_token=token)
