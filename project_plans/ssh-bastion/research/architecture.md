# Architecture Research: SSH Bastion

## 1. SSH config.d Pattern for Bastion/ProxyJump

### Structure

The `~/.ssh/config` file uses `Include` to pull in `~/.ssh/config.d/*`. The bastion file defines two Host blocks: one for the bastion itself (direct connection, with knock-aware ProxyCommand or ssh executable), and wildcard blocks for internal hosts that use the bastion as a jump.

```
# ~/.ssh/config.d/bastion

# The bastion host itself — direct connection
# Port knocking is handled by knock-ssh wrapper, not here
Host bastion
  HostName <BASTION_IP_OR_FQDN>
  User tyler
  Port 2222
  IdentityFile ~/.ssh/id_ed25519_bastion
  # 1Password agent: add IdentityAgent ~/.1password/agent.sock
  # FIDO2 key: IdentityFile ~/.ssh/id_ed25519_sk (or id_ecdsa_sk)
  ServerAliveInterval 60

# Internal hosts reachable through the bastion
# ProxyJump: OpenSSH 7.3+, cleaner than ProxyCommand
Host internal-*.example.com 10.0.0.*
  ProxyJump bastion
  User tyler
  IdentityFile ~/.ssh/id_ed25519_bastion
```

### Key Points

- **ProxyJump vs ProxyCommand**: ProxyJump (`-J`) is the modern idiom (OpenSSH 7.3+). It cleanly handles stdio forwarding; ProxyCommand with `-W %h:%p` is equivalent but more verbose. Both work transparently with `scp`, `sftp`, and Ansible.
- **First-match wins**: SSH applies the first matching Host block. Put specific hosts before wildcards.
- **Port knocking is NOT in SSH config**: Knocking must happen before the TCP connection. The knock-ssh wrapper handles that; the SSH config.d entry handles everything from TCP connect onwards.
- **Include directive**: `~/.ssh/config` must contain `Include ~/.ssh/config.d/*` (or `~/.ssh/config.d/` in older OpenSSH) before any Host blocks to ensure config.d entries are applied.

---

## 2. Ansible Inventory for Bastion + Internal Hosts

### Inventory Structure

```yaml
# inventory/hosts.yml
all:
  children:
    bastion:
      hosts:
        bastion-vps:
          ansible_host: "{{ vault_bastion_host }}"
    internal:
      hosts:
        homelab-1:
          ansible_host: 10.0.0.10
        homelab-2:
          ansible_host: 10.0.0.11
```

### Group Variables

```yaml
# inventory/group_vars/bastion.yml
ansible_port: 2222
ansible_user: tyler
ansible_ssh_private_key_file: ~/.ssh/id_ed25519_bastion
# ansible_ssh_executable: ~/bin/knock-ssh
# Use ansible_ssh_executable to call the knock-ssh wrapper instead of bare ssh
```

```yaml
# inventory/group_vars/internal.yml
ansible_user: tyler
ansible_ssh_private_key_file: ~/.ssh/id_ed25519_bastion
# ProxyJump via the bastion; uses SSH config or explicit common args
ansible_ssh_common_args: '-o ProxyJump=tyler@{{ vault_bastion_host }}:2222'
# Alternatively, if SSH config.d is set up on the control machine:
# ansible_ssh_common_args: '-o ProxyJump=bastion'
```

### Key Variables

| Variable | Purpose |
|---|---|
| `ansible_port` | Override SSH port (2222 instead of 22) |
| `ansible_user` | Login user |
| `ansible_ssh_private_key_file` | Headless key for Ansible (not hardware-bound) |
| `ansible_ssh_common_args` | Appended to all ssh/scp/sftp; used for ProxyJump |
| `ansible_ssh_executable` | Replace ssh binary; hook for knock-ssh wrapper |

### ansible_ssh_executable vs pre_tasks Knock

Two approaches for running the knock before Ansible connects:

1. **`ansible_ssh_executable`** (preferred): Set `ansible_ssh_executable: /home/tyler/bin/knock-ssh`. Ansible replaces every `ssh` call with this script. The script parses args, knocks, then `exec`s the real `ssh`. Transparent to scp/sftp too.
2. **pre_tasks with `local_action`**: Run `knock {{ ansible_host }} ...` as a local task before plays. Less transparent—only knocks once per play, not per-connection, and doesn't help with inventory ad-hoc commands.

---

## 3. knockd + UFW Interaction

### How knockd Calls UFW

knockd runs at the link layer (raw socket / libpcap), so it sees all packets including those to closed ports. When the correct sequence is detected, knockd executes the `start_command` (and optionally `stop_command`) as root.

With UFW, the commands in `/etc/knockd.conf` look like:

```ini
[openSSH]
    sequence      = 7264,3981,5410
    seq_timeout   = 5
    start_command = ufw allow from %IP% to any port 2222
    cmd_timeout   = 30
    stop_command  = ufw delete allow from %IP% to any port 2222
```

### The Persistence Problem

This is the critical difference between using raw iptables vs UFW in knockd:

- **Raw iptables** (`iptables -A INPUT -s %IP% ...`): Rules live in kernel memory only. They survive knockd restart, but are **wiped on reboot** (unless persisted with `iptables-persistent`/`netfilter-persistent`). knockd-opened rules accumulate; `iptables -F` or `netfilter-persistent reload` clears them all at once.
- **UFW** (`ufw allow from %IP% ...`): UFW writes rules to `/etc/ufw/` config files. These rules **persist across reboots** — which is the opposite problem. A stale allow rule from a previous session stays until explicitly deleted. The `stop_command` must be reliable; if knockd crashes before running it, the rule sticks.

### Recommended Approach: Custom iptables Chain

A cleaner design (from floating octothorpe pattern) creates a dedicated iptables chain for knockd:

```bash
# At provision time (persistent via netfilter-persistent/iptables-persistent):
iptables -N KNOCKD
iptables -A INPUT -j KNOCKD

# knockd.conf:
start_command = /sbin/iptables -A KNOCKD -s %IP% -p tcp --dport 2222 -j ACCEPT
stop_command  = /sbin/iptables -D KNOCKD -s %IP% -p tcp --dport 2222 -j ACCEPT
```

To use UFW for base policy but iptables for knockd-managed rules, set UFW's default deny and let the KNOCKD chain sit in front. On `ufw reload`, UFW regenerates iptables rules but **preserves the KNOCKD chain reference if set up in `/etc/ufw/after.rules`**.

### UFW Reload / Reboot Behavior

- `ufw reload`: Flushes and regenerates iptables rules from UFW config files. **Knocking-opened raw iptables rules added by knockd are lost**. UFW-managed rules (written to config files) survive.
- Reboot: Same as reload—iptables is rebuilt from UFW config. knockd-added raw iptables rules vanish.
- **Mitigation**: Use the `start_command`/`stop_command` pattern with short `cmd_timeout` (30s) so rules are automatically cleaned. Or use UFW commands in knockd but accept the persistence tradeoff.

---

## 4. FIDO2 Resident Keys (sk-ed25519)

### Generating Resident Keys

Requires OpenSSH 8.2+ (8.3+ for `verify-required`), YubiKey firmware 5.2.3+ for ed25519-sk.

```bash
# Generate resident key on YubiKey/Titan (stored on hardware, touch + PIN required)
ssh-keygen -t ed25519-sk -O resident -O verify-required -C "tyler@bastion-yubikey"

# Generate resident key without PIN requirement (touch only)
ssh-keygen -t ed25519-sk -O resident -C "tyler@bastion-titan"

# For older YubiKey firmware (no ed25519-sk support):
ssh-keygen -t ecdsa-sk -O resident -O verify-required -C "tyler@bastion-yubikey"

# Retrieve resident keys to a new machine:
ssh-keygen -K
```

The resulting `.pub` file contains the **public key and a credential ID** referencing the on-hardware private key. Example:
```
sk-ed25519@openssh.com AAAAGnNrLWVkMjU1MTlAb3BlbnNzaC5jb20AAAAIx... tyler@bastion-yubikey
```

### Server-Side authorized_keys Format

The full public key line is placed in `~/.ssh/authorized_keys` on the server:
```
sk-ed25519@openssh.com AAAAG... tyler@bastion-yubikey
sk-ecdsa-sha2-nistp256@openssh.com AAAA... tyler@bastion-titan
```

### Server-Side sshd_config

No special configuration is needed beyond standard pubkey auth:
```
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
PasswordAuthentication no
```

FIDO2 keys use the `sk-*` key types. OpenSSH server 8.2+ handles them natively. No additional packages or modules needed on Ubuntu 22.04+.

**Optional server-side hardening**:
- `PubkeyAuthOptions verify-required` — requires the client used `-O verify-required` (PIN+touch), rejects touch-only keys
- `VerifyHostKeyDNS yes` — client-side option to validate server's host key via DNS SSHFP records (not directly related to FIDO2)

---

## 5. knock-ssh Wrapper: Transparent for SSH and Ansible

### Design Requirements

The wrapper must:
1. Accept all SSH arguments unchanged
2. Extract the target hostname
3. Knock the target
4. Sleep briefly (timing for firewall rule propagation)
5. `exec` real ssh with original arguments unmodified

### Implementation Pattern

```bash
#!/usr/bin/env bash
# ~/bin/knock-ssh
# Drop-in replacement for ssh that knocks before connecting.
# Usage: same as ssh. Configure knock sequences per host.

SSH_BIN=$(command -v ssh)
KNOCK_BIN=$(command -v knock)

# Extract hostname from args (last non-option argument before any command)
# Simple heuristic: find first non-flag arg that doesn't start with -
TARGET_HOST=""
for arg in "$@"; do
    case "$arg" in
        -*) ;;            # skip flags
        *@*) TARGET_HOST="${arg#*@}" ;;   # user@host -> host
        *)  [[ -z "$TARGET_HOST" ]] && TARGET_HOST="$arg" ;;
    esac
done

# Knock configuration (override from env or vault-injected file)
# Load per-host knock sequences from a config file
KNOCK_CONFIG="${KNOCK_CONFIG_FILE:-$HOME/.ssh/knock-sequences}"

if [[ -f "$KNOCK_CONFIG" && -n "$TARGET_HOST" ]]; then
    # Format: hostname port1 port2 port3
    SEQUENCE=$(grep "^$TARGET_HOST " "$KNOCK_CONFIG" | awk '{$1=""; print $0}')
    if [[ -n "$SEQUENCE" ]]; then
        $KNOCK_BIN "$TARGET_HOST" $SEQUENCE 2>/dev/null
        sleep 1  # allow fw rule to propagate
    fi
fi

exec "$SSH_BIN" "$@"
```

### Ansible Integration

```yaml
# inventory/group_vars/bastion.yml
ansible_ssh_executable: /home/tyler/bin/knock-ssh
```

When `ansible_ssh_executable` is set, Ansible substitutes it for every `ssh`, `scp`, and `sftp` call. The wrapper receives the same argument list that Ansible would pass to bare `ssh`, so ProxyJump and port args work as expected.

**Key constraint**: The wrapper must not output anything to stdout/stderr during the knock phase (or redirect knock output to `/dev/null`). Ansible parses ssh output directly; extra lines break connection handling.

### For ProxyJump (internal hosts through bastion)

Internal hosts do not need knocking directly — they're reached via bastion. The knock for the bastion is triggered when Ansible connects to it. The `ProxyJump` in `ansible_ssh_common_args` causes OpenSSH to first open a connection to the bastion (triggering `knock-ssh` for the bastion host), then tunnel through to the internal host.

If the bastion needs knocking but internal hosts do not, the `knock-sequences` config file simply has no entry for internal IPs, and the wrapper passess through to ssh directly.

---

## 6. Ansible Vault for Secrets

### What to Vault

- `vault_bastion_host`: public IP or FQDN of bastion
- `vault_knock_sequence`: list of ports (e.g., `[7264, 3981, 5410]`)
- `vault_bastion_close_sequence`: optional close sequence
- Any home server IPs or dynamic DNS hostnames

### Pattern: vars + vault_vars

Best practice per Ansible docs is to keep variable names visible in plaintext but values encrypted inline or in a separate vault file:

```yaml
# inventory/group_vars/bastion.yml  (plaintext, committed)
ansible_host: "{{ vault_bastion_host }}"
knock_sequence: "{{ vault_knock_sequence }}"

# inventory/group_vars/bastion/vault.yml  (encrypted with ansible-vault encrypt)
vault_bastion_host: "1.2.3.4"
vault_knock_sequence: [7264, 3981, 5410]
```

Encrypt the vault file:
```bash
ansible-vault encrypt inventory/group_vars/bastion/vault.yml
```

### knock-sequences Config File

The `~/.ssh/knock-sequences` file used by `knock-ssh` contains plaintext sequences at runtime, but should not be committed. Generate it from vault:

```yaml
# roles/ssh-bastion/tasks/client.yml (or a local setup playbook)
- name: Write knock-sequences file
  copy:
    content: "{{ vault_bastion_host }} {{ vault_knock_sequence | join(' ') }}\n"
    dest: "{{ ansible_env.HOME }}/.ssh/knock-sequences"
    mode: '0600'
```

Alternatively, bake it into `knock-ssh` as an env var loaded from a gitignored dotenv file:
```bash
# ~/.ssh/knock-sequences.env  (gitignored)
BASTION_KNOCK="7264 3981 5410"
```

### Vault Password Management

- Store vault password in 1Password or system keychain; reference via `--vault-password-file ~/.vault_pass.sh`
- The `vault_pass.sh` script fetches the password from the keychain/1Password agent at runtime
- For CI or headless: use `ANSIBLE_VAULT_PASSWORD_FILE` env var

---

## Summary of Key Design Decisions

1. **knockd uses a dedicated iptables chain (KNOCKD), not raw UFW commands**: This avoids UFW reload wiping knockd-opened rules and avoids stale persistent UFW rules from missed stop_commands.

2. **knock-ssh wrapper via `ansible_ssh_executable`**: More transparent than pre_tasks; fires for every SSH invocation including scp/sftp; requires `exec "$SSH_BIN" "$@"` pattern and no stdout pollution.

3. **Ansible Vault with split vars/vault_vars**: Plaintext variable names in group_vars files, encrypted values in a separate `vault.yml` per group. knock-sequences file is generated from vault at setup time and gitignored.
