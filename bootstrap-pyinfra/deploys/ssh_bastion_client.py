"""
Port of bootstrap/roles/ssh-bastion-client/tasks/main.yml.

Opt-in like the Ansible role's `when: bastion_host | length > 0` — driven by
host.data.bastion_op_item (a 1Password "vault/item" path, e.g.
"Escutcheon/bastion-1"). Empty (the default) means no bastion is configured
on this host and the whole deploy no-ops.

Connection details are pulled from 1Password via `op read` at deploy time,
not baked into group_data — matches the Ansible role's
`community.general.onepassword` lookups. Needs an active `op` session
(`eval $(op signin)`).

No `become`/root anywhere in the Ansible original — everything here is
immediate execution (shell_capture/shell_ok), matching the register-chain
style used by homebrew.py/github.py, since generating the key and reading it
back happens in the same run.
"""

import io
import json
import os
from dataclasses import dataclass

from pyinfra import host  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.api.exceptions import DeployError
from pyinfra.operations import files

from common import brew_prefix, hostname, shell_capture, shell_ok

SSH_DIR = os.path.expanduser("~/.ssh")
SSH_CONFIG = os.path.join(SSH_DIR, "config")
SSH_CONFIG_D = os.path.join(SSH_DIR, "config.d")
ESCUTCHEON_CONFIG_DIR = os.path.expanduser("~/.config/escutcheon")
INCLUDE_DIRECTIVE = "Include ~/.ssh/config.d/*"


@dataclass(frozen=True)
class BastionConnection:
    name: str
    host: str
    port: str


def _op_read(op_path: str) -> str:
    code, output = shell_capture(f'PATH={brew_prefix()}/bin:$PATH op read "{op_path}"')
    if code != 0:
        raise DeployError(f"op read {op_path} failed — is `op signin` active? {output}")
    return output.strip()


def _resolve_connection(bastion_op_item: str, bastion_name: str) -> BastionConnection:
    return BastionConnection(
        name=bastion_name,
        host=_op_read(f"op://{bastion_op_item}/address"),
        port=_op_read(f"op://{bastion_op_item}/ssh_port"),
    )


def _ensure_include_directive_at_top() -> None:
    # Must be the first match for SSH's "first match wins" Include semantics —
    # files.line only appends, so this is done by hand.
    if shell_ok(f"test -f {SSH_CONFIG}") and shell_ok(
        f"grep -qxF '{INCLUDE_DIRECTIVE}' {SSH_CONFIG}"
    ):
        return
    shell_capture(
        f'tmp=$(mktemp) && printf "%s\\n" "{INCLUDE_DIRECTIVE}" > "$tmp" && '
        f'([ -f {SSH_CONFIG} ] && cat {SSH_CONFIG} >> "$tmp" || true) && '
        f'mv "$tmp" {SSH_CONFIG} && chmod 600 {SSH_CONFIG}'
    )


def _ensure_bastion_key(key_path: str) -> str:
    if not shell_ok(f"test -f {key_path}"):
        code, output = shell_capture(
            f'ssh-keygen -t ed25519 -f {key_path} -N "" '
            f'-C "bastion-{os.environ["USER"]}@{hostname()}"'
        )
        if code != 0:
            raise DeployError(f"ssh-keygen for {key_path} failed: {output}")

    _, pub_key = shell_capture(f"cat {key_path}.pub")
    return pub_key.strip()


def ssh_config_fragment(conn: BastionConnection, *, key_path: str) -> str:
    return f"""# Managed by pyinfra - ssh_bastion_client deploy
Host {conn.name}
    HostName {conn.host}
    Port {conn.port}
    IdentityFile {key_path}
    IdentitiesOnly yes
    ControlMaster auto
    ControlPath ~/.ssh/cm-%r@%h:%p
    ControlPersist 10m
    ServerAliveInterval 60
    ServerAliveCountMax 10
"""


def escutcheon_toml(
    conn: BastionConnection,
    *,
    knock_sequence: list[int],
    knock_proto: str,
    knock_ttl_secs: int,
) -> str:
    return f"""# Managed by pyinfra - ssh_bastion_client deploy
[hosts.{conn.name}]
host     = "{conn.host}"
port     = {conn.port}
sequence = {json.dumps(knock_sequence)}
proto    = "{knock_proto}"
ttl_secs = {knock_ttl_secs}
"""


def _deploy_ssh_config(conn: BastionConnection, *, key_path: str) -> None:
    files.directory(
        name="Ensure ~/.ssh/config.d exists",
        path=SSH_CONFIG_D,
        present=True,
        mode="0700",
    )
    _ensure_include_directive_at_top()
    files.put(
        name="Deploy bastion SSH config fragment",
        src=io.StringIO(ssh_config_fragment(conn, key_path=key_path)),
        dest=os.path.join(SSH_CONFIG_D, conn.name),
        mode="0600",
    )


def _deploy_escutcheon_config(
    conn: BastionConnection,
    *,
    knock_sequence: list[int],
    knock_proto: str,
    knock_ttl_secs: int,
) -> None:
    files.directory(
        name="Ensure escutcheon config directory exists",
        path=ESCUTCHEON_CONFIG_DIR,
        present=True,
        mode="0755",
    )
    files.put(
        name="Deploy escutcheon config.toml",
        src=io.StringIO(
            escutcheon_toml(
                conn,
                knock_sequence=knock_sequence,
                knock_proto=knock_proto,
                knock_ttl_secs=knock_ttl_secs,
            )
        ),
        dest=os.path.join(ESCUTCHEON_CONFIG_DIR, "config.toml"),
        mode="0600",
    )


@deploy("SSH bastion client")
def ssh_bastion_client() -> None:
    bastion_op_item: str = host.data.get("bastion_op_item") or ""
    if not bastion_op_item:
        return  # matches the Ansible role's `when: bastion_host | length > 0`

    bastion_name: str = host.data.get("bastion_name") or "bastion-1"
    key_path = os.path.expanduser(
        host.data.get("bastion_key_path") or "~/.ssh/id_ed25519_bastion"
    )
    knock_proto = host.data.get("bastion_knock_proto") or "tcp"
    knock_ttl_secs = int(host.data.get("bastion_knock_ttl_secs", 300))

    conn = _resolve_connection(bastion_op_item, bastion_name)
    knock_sequence_raw = _op_read(f"op://{bastion_op_item}/knock_sequence")
    knock_sequence = json.loads(knock_sequence_raw) if knock_sequence_raw else []

    pub_key = _ensure_bastion_key(key_path)
    print(
        f"Bastion public key (add to 1Password {bastion_op_item}/ansible_pubkey "
        f"and to server authorized_keys if first-time setup):\n\n{pub_key}"
    )

    _deploy_ssh_config(conn, key_path=key_path)
    _deploy_escutcheon_config(
        conn,
        knock_sequence=knock_sequence,
        knock_proto=knock_proto,
        knock_ttl_secs=knock_ttl_secs,
    )
