# Research: SSH Bastion Features

## 1. Ansible SSH Hardening Roles

### dev-sec/ansible-collection-hardening (ssh_hardening role)

**Status**: Actively maintained. The standalone `dev-sec/ansible-ssh-hardening` repo was archived in Dec 2020; the live role is now `devsec.hardening` collection at `dev-sec/ansible-collection-hardening`.

**Install**: `ansible-galaxy collection install devsec.hardening`

**What it configures (borrowable defaults)**:
- `ssh_server_ports`: configurable (we want `[2222]`)
- `ssh_permit_root_login: 'no'`
- `ssh_server_password_login: false`
- `sshd_authenticationmethods: 'publickey'`
- Cipher/MAC/KEX hardening: restricts to modern algorithms (chacha20-poly1305, aes256-gcm, curve25519, etc.)
- `sshd_log_level: 'VERBOSE'` and `sshd_syslog_facility: 'AUTH'`
- `ssh_max_auth_retries: 2`, `ssh_login_grace_time: 30s`
- `ssh_max_startups: '10:30:100'`
- `sshd_moduli_minimum: 2048` (regenerates weak DH params)
- `ssh_allow_agent_forwarding: false`, `ssh_allow_tcp_forwarding: 'no'` (override as needed for bastion)
- `sftp_enabled: false` by default
- `ssh_deny_users`, `ssh_allow_users` for access control

**What to borrow**:
- The cipher/MAC/KEX list (copy or depend on the collection)
- The sshd_config Jinja2 template pattern (their `opensshd.conf.j2` is a solid reference)
- `sshd_moduli_minimum` check / moduli regeneration task
- The idempotent `authorized_key` deploy pattern

**What NOT to borrow as-is**:
- Port is hard-coded to `['22']` in defaults — we override to `2222`
- Role disables agent/tcp forwarding by default — bastion needs forwarding enabled for ProxyJump
- SFTP disabled by default — keep that, we don't need it

### geerlingguy/ansible-role-security

**Status**: Actively maintained (simpler, lighter role).

**What it does for SSH**:
- Disables: `PasswordAuthentication`, `PermitRootLogin`, `UseDNS`, `PermitEmptyPasswords`, `ChallengeResponseAuthentication`, `GSSAPIAuthentication`, `X11Forwarding`
- Configures SSH port (default 22, overridable)
- AllowUsers / AllowGroups list support
- Much lighter than dev-sec — just the essentials

**Verdict**: Too minimal for us. Borrow the "simple sshd template" structure; depend on dev-sec for crypto hardening.

---

## 2. Ansible Roles for knockd / Port Knocking

### Available options

| Role | Status | Notes |
|------|--------|-------|
| `fcsonline/ansible-port-knocking` | ~2016, no recent commits but still functional | Installs knockd, templates `knockd.conf`, manages ufw rules. Variables: `port_sequence`, `secure_ports`, `open_ports`, `command_line_options`, `sequence_timeout`, `command_timeout` |
| `roguh/ansible-fwknop` | Newer but uses fwknop (SPA), not knockd | Different tool — stronger security but more complex client |
| `mcsimz/ansible-knock` | 2018, 1 star, minimal | Connection plugin (`ssh_pkn.py`) not a server-side role |

**Conclusion**: No well-maintained, Galaxy-published knockd role exists as of 2024. The `fcsonline/ansible-port-knocking` is the closest reference but is essentially unmaintained. **Write our own** — it's ~50 lines of tasks. Use fcsonline's `knockd.conf.j2` template as a reference.

### fcsonline knockd.conf.j2 template pattern

Key settings to template:
```
[openSSH]
    sequence    = {{ port_sequence | join(',') }}
    seq_timeout = {{ sequence_timeout | default(15) }}
    command     = ufw allow from %IP% to any port {{ ssh_port }}
    tcpflags    = syn

[closeSSH]
    sequence    = {{ port_sequence | reverse | list | join(',') }}
    seq_timeout = {{ sequence_timeout | default(15) }}
    command     = ufw delete allow from %IP% to any port {{ ssh_port }}
    tcpflags    = syn
```

---

## 3. Knock + SSH Wrapper Patterns (Dotfiles / Community Examples)

### Common bash wrapper pattern

The dominant pattern across dotfiles and gists is a simple shell function or script:

```bash
#!/usr/bin/env bash
# knock-ssh HOST [ssh args...]
HOST="$1"; shift
knock "$HOST" PORT1 PORT2 PORT3
sleep 1
ssh "$HOST" "$@"
```

Variants found:
- Use `nc -z -w3` instead of `knock` binary (avoids dependency, but slower)
- Add a close-sequence after disconnect: `knock "$HOST" PORT3 PORT2 PORT1`
- Check if SSH port is already open before knocking (avoids double-knock)
- `thomasvs/portknock`: reads `~/.portknock` config file with per-host sequences, can wrap ssh/scp/rsync

### Recommended pattern for our wrapper

```bash
#!/usr/bin/env bash
set -euo pipefail
HOST="${1:?Usage: knock-ssh <host> [ssh args...]}"
shift

KNOCK_HOST="${KNOCK_HOSTS[$HOST]:-$HOST}"
KNOCK_SEQ="${KNOCK_SEQS[$HOST]:?No knock sequence for $HOST}"

knock "$KNOCK_HOST" $KNOCK_SEQ
sleep 1
ssh "$HOST" "$@"
```

Better: Read host config from `~/.ssh/config.d/bastion` so the sequence is in one place. Or keep sequence in the wrapper itself with env var / sourced config.

---

## 4. Ansible ProxyJump Configuration Patterns

### Three approaches, ranked by recommendation

**Option A — ansible_ssh_common_args in group_vars (recommended)**

```yaml
# group_vars/internal_hosts.yml
ansible_ssh_common_args: '-o ProxyJump=tyler@bastion.example.com:2222'
```

- Modern (OpenSSH 7.3+, all current Ubuntu/Debian)
- Cleanest syntax
- Survives ControlMaster multiplexing correctly
- ProxyJump handles agent forwarding automatically

**Option B — ProxyCommand (legacy fallback)**

```yaml
ansible_ssh_common_args: '-o ProxyCommand="ssh -p 2222 -W %h:%p -q tyler@bastion.example.com"'
```

- Works on older SSH but is slower (no multiplexing)
- `-W` pipes stdin/stdout through the bastion

**Option C — Rely on ~/.ssh/config**

```
Host bastion
  Hostname bastion.example.com
  Port 2222
  User tyler

Host internal-*
  ProxyJump bastion
```

Ansible picks up SSH config automatically. Best for workstation use; NOT portable (playbook runner needs the config).

**Decision**: Use `ansible_ssh_common_args: '-o ProxyJump=...'` in group_vars for portability. Document the SSH config alternative for interactive use.

---

## 5. Ansible Knock Integration: pre_tasks vs ansible_ssh_executable

### Option A: Custom connection plugin (ssh_pkn, mcsimz/ansible-knock)

- Sets `ansible_connection: ssh_pkn` per host/group
- Plugin makes raw TCP connections to knock ports before calling SSH
- **Pros**: transparent, works for all modules
- **Cons**: custom plugin must be distributed, not on Galaxy, only for Ansible 2.7 era, brittle

### Option B: ansible_ssh_executable wrapper script

```yaml
# group_vars/bastion.yml
ansible_ssh_executable: /usr/local/bin/knock-then-ssh
```

The wrapper:
```bash
#!/usr/bin/env bash
# knock-then-ssh: wraps ssh, knocks first
knock "${ANSIBLE_HOST:-${!#}}" 7000 8000 9000
sleep 1
exec /usr/bin/ssh "$@"
```

- **Pros**: works with any Ansible version, no plugin required, same tool as user-facing wrapper
- **Cons**: extracting the target host from SSH args is brittle (must parse positional args); env var `ANSIBLE_HOST` not always set

### Option C: pre_tasks knock module (recommended)

```yaml
# site.yml or play header
pre_tasks:
  - name: Knock SSH port open
    local_action:
      module: command
      argv:
        - knock
        - "{{ ansible_host }}"
        - "{{ knock_port_1 }}"
        - "{{ knock_port_2 }}"
        - "{{ knock_port_3 }}"
    changed_when: false

  - name: Wait for SSH port
    local_action:
      module: wait_for
      host: "{{ ansible_host }}"
      port: "{{ ansible_port | default(2222) }}"
      timeout: 10
```

- **Pros**: explicit, visible in playbook output, uses standard Ansible modules, `ansible_host`/`knock_port_*` vars from inventory, idempotent (changed_when: false)
- **Cons**: must be included in every playbook that targets the bastion; `ansible -m ping` ad-hoc commands don't run pre_tasks

### Hybrid recommendation

- **For playbooks**: `pre_tasks` knock + `wait_for` (reliable, explicit)
- **For ad-hoc `ansible -m ping`**: use `ansible_ssh_executable` wrapper OR knock manually before running
- **For ProxyJump through bastion to internal hosts**: knock the bastion in pre_tasks before plays targeting internal hosts

The `ansible_ssh_executable` approach is unreliable as a sole solution because Ansible passes args in varying ways depending on the connection type. The `pre_tasks` approach is the most maintainable.

---

## 6. 1Password SSH Agent + Ansible: Known Issues and Workarounds

### Core problem

The 1Password SSH agent exposes a socket at `~/.1password/agent.sock` (symlink to the real socket). Ansible's SSH connection works via `SSH_AUTH_SOCK`. This creates several issues:

1. **Interactive touch required**: 1Password prompts for biometric/PIN approval per-key. For automated Ansible runs with multiple hosts/tasks, this means many approval prompts.
2. **Ansible 12+ regression**: Lazy variable evaluation in Ansible 12 causes 1Password agent prompts for every `become` step, not just at connection time — makes it essentially unusable.
3. **Non-interactive environments**: cron, systemd services, and CI pipelines do not inherit `SSH_AUTH_SOCK`, so the agent socket is not available.
4. **Agent socket pass-through in containers**: Explicitly does not work with 1Password SSH agent (confirmed by 1Password).

### Workarounds

**Workaround 1 — Dedicated ed25519 key for Ansible (recommended)**

```yaml
# group_vars/all.yml
ansible_ssh_private_key_file: ~/.ssh/ansible_ed25519
```

Keep a dedicated key (no passphrase, or passphrase unlocked by ssh-agent at shell startup) for headless Ansible. This key is separate from the 1Password-managed key used interactively.

**Workaround 2 — Explicit SSH_AUTH_SOCK in ansible.cfg or environment**

```ini
# ansible.cfg
[ssh_connection]
ssh_args = -o IdentityAgent=~/.1password/agent.sock
```

This works for interactive sessions but still triggers approval prompts per-key.

**Workaround 3 — 1Password CLI to extract key at run time**

```bash
op read "op://vault/item/private key" > /tmp/ansible_key && chmod 600 /tmp/ansible_key
ansible-playbook site.yml --private-key /tmp/ansible_key
rm /tmp/ansible_key
```

Useful for scripted runs; requires `op` CLI and session token. Key lives on disk briefly.

### Design decision for this project

- **Interactive sessions** (manual SSH, knock-ssh): use 1Password agent (`IdentityAgent ~/.1password/agent.sock` in SSH config)
- **Ansible automation**: use dedicated `~/.ssh/ansible_ed25519` with `ansible_ssh_private_key_file`
- Keep both pubkeys in `authorized_keys` on the server (deployed by the role)
- Document that `knock-ssh` uses 1Password agent; `ansible` uses the file key

This is the correct separation. Do not try to use 1Password agent for Ansible automation.

---

## Summary

| Question | Finding |
|----------|---------|
| SSH hardening role | Use `devsec.hardening` collection (active). Borrow cipher/MAC/KEX list and moduli check. Override port and forwarding settings for bastion use case. |
| knockd role | No maintained Galaxy role. Write our own (~50 lines). Reference `fcsonline/ansible-port-knocking` template. |
| knock-ssh wrapper | Standard pattern: `knock HOST P1 P2 P3 && sleep 1 && ssh HOST`. Add optional close-sequence. Source host/sequence config from env or sourced file. |
| ProxyJump config | Use `ansible_ssh_common_args: '-o ProxyJump=...'` in group_vars. Most portable. SSH config method works for interactive only. |
| Knock integration | `pre_tasks` with `local_action: command knock` + `wait_for` for playbooks. `ansible_ssh_executable` wrapper for ad-hoc. Hybrid needed. |
| 1Password + Ansible | Do not mix. Use dedicated ed25519 key file (`ansible_ssh_private_key_file`) for Ansible. Use 1Password agent for interactive SSH only. |

## Sources

- [dev-sec/ansible-collection-hardening](https://github.com/dev-sec/ansible-collection-hardening) (active)
- [dev-sec/ansible-ssh-hardening defaults/main.yml](https://github.com/dev-sec/ansible-ssh-hardening/blob/master/defaults/main.yml) (archived, reference only)
- [geerlingguy/ansible-role-security](https://github.com/geerlingguy/ansible-role-security)
- [fcsonline/ansible-port-knocking](https://github.com/fcsonline/ansible-port-knocking)
- [mcsimz/ansible-knock (ssh_pkn plugin)](https://github.com/mcsimz/ansible-knock)
- [Jeff Geerling: Ansible with SSH bastion / jump host](https://www.jeffgeerling.com/blog/2022/using-ansible-playbook-ssh-bastion-jump-host/)
- [1Password SSH agent docs](https://developer.1password.com/docs/ssh/agent/)
- [1Password Community: SSH agent and Ansible 12 prompting](https://www.1password.community/discussions/developers/ssh-agent-and-ansible-12-prompting-incessantly/163614)
