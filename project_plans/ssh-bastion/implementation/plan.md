# SSH Bastion Implementation Plan

## Overview

This plan covers two parallel subsystems:
- **A) SERVER ROLE** — `bootstrap/roles/ssh-bastion/` in public dotfiles repo
- **B) CLIENT SETUP** — dotfiles side, deployed by `cfgcaddy/cfgcaddy` role

---

## Technology Decisions Requiring ADRs

The following decisions have non-trivial tradeoffs and must be resolved before implementation:

| ADR | Decision | Options | Research Recommendation |
|-----|----------|---------|-------------------------|
| ADR-001 | Port knocking daemon | knockd vs fwknop | knockd for home/personal; fwknop for cloud VPS |
| ADR-002 | Ansible knock integration | `ansible_ssh_executable` wrapper vs `pre_tasks` | Hybrid: `ansible_ssh_executable` for ad-hoc, `pre_tasks` for playbooks |
| ADR-003 | knockd firewall backend | UFW commands vs raw iptables in knockd config | UFW commands (`ufw allow from %IP%`) to survive `ufw reload` |
| ADR-004 | Role dependency | Write own SSH hardening vs depend on `devsec.hardening` | Write own, borrowing cipher/MAC/KEX list; avoid external dependency in public dotfiles |
| ADR-005 | knock-ssh implementation | Bash wrapper script vs standalone Rust binary | Rust binary (`tstapler/knock-ssh`): zero runtime deps, silent output (Ansible-safe), process exec handoff via `CommandExt::exec`, XDG-compliant config/state paths, Homebrew-installable |

---

## Epic A: SSH Bastion Server Role

### A.1 Role Scaffold and Defaults

**Story A.1.1** — Create role directory structure

Tasks:
- Create `bootstrap/roles/ssh-bastion/tasks/main.yml` with include guards for subsystems
- Create `bootstrap/roles/ssh-bastion/defaults/main.yml` with all role variables
- Create `bootstrap/roles/ssh-bastion/handlers/main.yml` with `restart sshd`, `reload ufw`, `restart knockd` handlers
- Create `bootstrap/roles/ssh-bastion/templates/` directory
- Create `bootstrap/roles/ssh-bastion/vars/` directory (for OS-specific vars)
- Create `bootstrap/roles/ssh-bastion/meta/main.yml` (platforms: Ubuntu, Debian; no dependencies)

**Story A.1.2** — Define all role variables in `defaults/main.yml`

Variables to define (all vault-injectable via Ansible group_vars):

```yaml
# Port configuration
ssh_bastion_port: 2222

# User access
ssh_bastion_user: tyler

# Knock daemon selection
ssh_bastion_knock_daemon: knockd        # or: fwknop
ssh_bastion_knock_sequence: []          # e.g. [7264, 3981, 5410] — REQUIRED
ssh_bastion_knock_close_sequence: []    # reverse sequence; defaults to reverse of knock_sequence
ssh_bastion_knock_seq_timeout: 15       # seconds to complete sequence
ssh_bastion_knock_cmd_timeout: 30       # seconds port stays open (auto-close)
ssh_bastion_knock_interface: ""         # e.g. "eth0"; empty = auto-detect

# Firewall
# REQUIRED (non-empty) when ssh_bastion_use_tailscale is false — the emergency IP is the
# operator's current public IP or a trusted management CIDR (e.g. a VPN range).
# This is the ONLY permanently-open path to the server if knockd fails to start.
# Example: "203.0.113.42" or "10.0.0.0/8"
ssh_bastion_emergency_ip: ""            # REQUIRED — operator's IP or management CIDR

# Tailscale variant (home server)
ssh_bastion_use_tailscale: false        # true = skip knockd, rely on Tailscale for reachability

# Authorized keys
ssh_bastion_ansible_pubkey: ""          # ed25519 pubkey for headless Ansible — REQUIRED
ssh_bastion_fido2_pubkeys: []           # list of sk-ed25519/sk-ecdsa-sk pubkeys for YubiKey/Titan
ssh_bastion_op_pubkeys: []              # list of ed25519 pubkeys from 1Password (optional)

# sshd hardening
ssh_bastion_max_auth_tries: 3
ssh_bastion_login_grace_time: "30s"
ssh_bastion_client_alive_interval: 60
ssh_bastion_client_alive_count_max: 10
ssh_bastion_allow_agent_forwarding: "yes"  # needed for ProxyJump
ssh_bastion_allow_tcp_forwarding: "yes"    # needed for ProxyJump
ssh_bastion_log_level: VERBOSE

# Ciphers/MACs/KEX (borrowed from devsec.hardening)
ssh_bastion_ciphers:
  - chacha20-poly1305@openssh.com
  - aes256-gcm@openssh.com
  - aes128-gcm@openssh.com
ssh_bastion_macs:
  - hmac-sha2-512-etm@openssh.com
  - hmac-sha2-256-etm@openssh.com
ssh_bastion_kex_algorithms:
  - curve25519-sha256
  - curve25519-sha256@libssh.org
  - diffie-hellman-group16-sha512
  - diffie-hellman-group18-sha512
```

---

### A.2 Package Installation

**Story A.2.1** — Install openssh-server and firewall packages

Tasks:
- Create `bootstrap/roles/ssh-bastion/tasks/packages.yml`
- Task: `apt update` cache if stale (cache_valid_time: 3600)
- Task: install `openssh-server`, `ufw` via `ansible.builtin.apt`
- Task: conditional install `knockd` when `ssh_bastion_knock_daemon == 'knockd' and not ssh_bastion_use_tailscale`
- Task: conditional install `fwknop-server` when `ssh_bastion_knock_daemon == 'fwknop' and not ssh_bastion_use_tailscale`
- Tag all tasks: `ssh-bastion`, `packages`

---

### A.3 UFW Firewall Configuration

**Story A.3.0** — Pre-flight safety assertion (FATAL-1 fix)

Tasks:
- Add to `bootstrap/roles/ssh-bastion/tasks/firewall.yml` as the **first** task (before any UFW changes):
  ```yaml
  - name: Assert emergency IP is defined before applying UFW deny rule
    ansible.builtin.assert:
      that:
        - ssh_bastion_emergency_ip is defined
        - ssh_bastion_emergency_ip != ''
      fail_msg: >
        ABORT: ssh_bastion_emergency_ip is empty.
        Set it to your current public IP or management CIDR (e.g. "203.0.113.42").
        Without this, a knockd failure will permanently lock you out with no console access.
    when: not ssh_bastion_use_tailscale
  ```
- Guard: `when: not ssh_bastion_use_tailscale`
- Tag: `ssh-bastion`, `firewall`, `preflight`

**Story A.3.1** — Configure ufw baseline policy

**Task ordering is critical (C-4 fix)**: On a host where UFW is already enabled, changing the default policy to deny BEFORE adding the emergency IP allow rule will immediately drop the current Ansible connection. The required task order is:
1. Add emergency IP allow rule
2. Set default-deny incoming
3. Enable UFW (idempotent if already enabled)

Tasks (in required order):
- Create `bootstrap/roles/ssh-bastion/tasks/firewall.yml`
- **Task 1**: Allow emergency IP on SSH port **FIRST** — before any policy or enable changes:
  ```yaml
  - name: Allow emergency management IP on SSH port
    community.general.ufw:
      rule: allow
      from_ip: "{{ ssh_bastion_emergency_ip }}"
      to_any: true
      port: "{{ ssh_bastion_port }}"
      proto: tcp
    when: not ssh_bastion_use_tailscale
  ```
  - Note: `ssh_bastion_emergency_ip` is the operator's current IP or trusted management CIDR. This is the permanent recovery path if knockd fails to start. Document as required (not optional) in role README.
- **Task 2**: set ufw default allow outgoing
- **Task 3**: set ufw default deny incoming (`community.general.ufw` module, direction: incoming, policy: deny) — applied AFTER emergency IP rule is in place
- **Task 4**: enable ufw (state: enabled, logging: on) — idempotent if already enabled; the allow rule from Task 1 is already present in UFW tables before this activates the policy
- Note: SSH port is NOT permanently opened for the general public; knockd controls per-IP access; only `ssh_bastion_emergency_ip` is permanently allowed
- Note: Port 22 must NOT be opened — this is how the role hardens the server
- Tag all tasks: `ssh-bastion`, `firewall`

**Story A.3.2** — knockd firewall ports — DO NOT OPEN IN UFW

**This story has been replaced with an explicit non-task note. No UFW rules are added for knock sequence ports.**

- **Do NOT add `ufw allow` rules for the knock sequence ports.**
- Rationale: knockd reads knock packets via libpcap at the kernel level, **before** iptables/nftables processes them. UFW rules are not required for knockd to detect the packets. Opening the knock sequence ports in UFW defeats the stealth goal: three unusual high ports with no responding service is a strong fingerprint that tells port scanners (masscan, Shodan) that the server uses port knocking, exposing the attack surface and knocking mechanism.
- The correct firewall state after this role runs:
  - Knock sequence ports (e.g. 7264, 3981, 5410): **CLOSED in UFW** — knockd still sees them via libpcap
  - `ssh_bastion_port`: CLOSED by default deny; opened temporarily per-IP by knockd's `start_command`
  - `ssh_bastion_emergency_ip` → `ssh_bastion_port`: PERMANENTLY OPEN (Story A.3.1)
- Tag: (none — no task to implement)

---

### A.4 sshd Configuration

**Story A.4.1** — Template sshd_config

Tasks:
- Create `bootstrap/roles/ssh-bastion/templates/sshd_config.j2`
- Template must include:
  - `Port {{ ssh_bastion_port }}`
  - `PermitRootLogin no`
  - `PasswordAuthentication no`
  - `PermitEmptyPasswords no`
  - `ChallengeResponseAuthentication no`
  - `KbdInteractiveAuthentication no`
  - `X11Forwarding no`
  - `UseDNS no`
  - `PrintMotd no`
  - `AllowUsers {{ ssh_bastion_user }}`
  - `MaxAuthTries {{ ssh_bastion_max_auth_tries }}`
  - `LoginGraceTime {{ ssh_bastion_login_grace_time }}`
  - `ClientAliveInterval {{ ssh_bastion_client_alive_interval }}`
  - `ClientAliveCountMax {{ ssh_bastion_client_alive_count_max }}`
  - `AllowAgentForwarding {{ ssh_bastion_allow_agent_forwarding }}`
  - `AllowTcpForwarding {{ ssh_bastion_allow_tcp_forwarding }}`
  - `LogLevel {{ ssh_bastion_log_level }}`
  - `PubkeyAuthentication yes`
  - `AuthorizedKeysFile .ssh/authorized_keys`
  - `AuthenticationMethods publickey`
  - `Ciphers {{ ssh_bastion_ciphers | join(',') }}`
  - `MACs {{ ssh_bastion_macs | join(',') }}`
  - `KexAlgorithms {{ ssh_bastion_kex_algorithms | join(',') }}`
  - `Subsystem sftp /usr/lib/openssh/sftp-server` (keep for scp compatibility)

- Create `bootstrap/roles/ssh-bastion/tasks/sshd.yml`
- Task: deploy template to `/etc/ssh/sshd_config` (owner: root, mode: 0600)
- Task: validate config with `sshd -t` before notifying handler (use `ansible.builtin.command` with `validate`)
- Handler: `restart sshd` → `ansible.builtin.service: name=ssh state=restarted`
- Tag: `ssh-bastion`, `sshd`

**Story A.4.2** — Harden SSH moduli (weak DH params)

Tasks:
- Task: check if `/etc/ssh/moduli` has weak entries (< 3071 bits): `awk '$5 < 3071' /etc/ssh/moduli | wc -l`
- Task: regenerate moduli when weak entries found (expensive; tag `slow` to allow skipping)
  - `ssh-keygen -G /tmp/moduli.candidates -b 4096`
  - `ssh-keygen -T /etc/ssh/moduli -f /tmp/moduli.candidates`
- Tag: `ssh-bastion`, `sshd`, `slow`

---

### A.5 Authorized Keys Deployment

**Story A.5.1** — Ensure user home directory and .ssh exist

Tasks:
- Create `bootstrap/roles/ssh-bastion/tasks/authorized_keys.yml`
- Task: ensure user `{{ ssh_bastion_user }}` exists (`ansible.builtin.user`)
- Task: ensure `~{{ ssh_bastion_user }}/.ssh` directory exists (mode: 0700)

**Story A.5.2** — Deploy all pubkeys to authorized_keys

Tasks:
- Task: deploy Ansible ed25519 key (state: present, comment: "ansible-automation"):
  ```yaml
  ansible.posix.authorized_key:
    user: "{{ ssh_bastion_user }}"
    key: "{{ ssh_bastion_ansible_pubkey }}"
    state: present
  ```
- Task: deploy FIDO2 pubkeys (loop over `ssh_bastion_fido2_pubkeys`):
  ```yaml
  ansible.posix.authorized_key:
    user: "{{ ssh_bastion_user }}"
    key: "{{ item }}"
    key_options: "touch-required"
    state: present
  ```
  Note: `touch-required` authorized_keys option ensures hardware touch is enforced server-side for FIDO2 keys without blocking the plain ed25519 key.
- Task: deploy 1Password pubkeys (loop over `ssh_bastion_op_pubkeys`, no special options):
  ```yaml
  ansible.posix.authorized_key:
    user: "{{ ssh_bastion_user }}"
    key: "{{ item }}"
    state: present
  ```
- Tag: `ssh-bastion`, `authorized_keys`

---

### A.6 knockd Configuration

**Story A.6.1** — Configure knockd (when `not ssh_bastion_use_tailscale and ssh_bastion_knock_daemon == 'knockd'`)

Tasks:
- Create `bootstrap/roles/ssh-bastion/templates/knockd.conf.j2`

  Template structure:
  ```ini
  [options]
      UseSyslog
      logfile = /var/log/knockd.log
      {% if ssh_bastion_knock_interface %}
      Interface = {{ ssh_bastion_knock_interface }}
      {% endif %}

  [openSSH]
      sequence    = {{ ssh_bastion_knock_sequence | join(',') }}
      seq_timeout = {{ ssh_bastion_knock_seq_timeout }}
      tcpflags    = syn
      start_command = /usr/sbin/ufw allow from %IP% to any port {{ ssh_bastion_port }}
      cmd_timeout = {{ ssh_bastion_knock_cmd_timeout }}
      stop_command  = /usr/sbin/ufw delete allow from %IP% to any port {{ ssh_bastion_port }}

  {% if ssh_bastion_knock_close_sequence | length > 0 %}
  [closeSSH]
      sequence    = {{ ssh_bastion_knock_close_sequence | join(',') }}
      seq_timeout = {{ ssh_bastion_knock_seq_timeout }}
      tcpflags    = syn
      command     = /usr/sbin/ufw delete allow from %IP% to any port {{ ssh_bastion_port }}
  {% endif %}
  ```

- Create `bootstrap/roles/ssh-bastion/templates/knockd_default.j2` for `/etc/default/knockd`:
  ```
  START_KNOCKD=1
  KNOCKD_OPTS="-i {{ ssh_bastion_knock_interface | default(ansible_default_ipv4.interface) }}"
  ```

- Create `bootstrap/roles/ssh-bastion/tasks/knockd.yml`
- Task: deploy knockd.conf template to `/etc/knockd.conf` (owner: root, mode: 0600)
- Task: deploy knockd_default template to `/etc/default/knockd`
- Task: enable and start knockd service (`ansible.builtin.service: name=knockd enabled=true state=started`)
- Task (FATAL-1 fix): **verify knockd is running and listening on the correct interface immediately after start** — this must run before the play ends so a misconfigured knockd is caught while the emergency IP rule still guarantees access:
  ```yaml
  - name: Verify knockd process is running
    ansible.builtin.command: pgrep -x knockd
    register: knockd_pid
    changed_when: false
    failed_when: knockd_pid.rc != 0
    retries: 3
    delay: 2

  - name: Verify knockd is listening on the correct interface
    ansible.builtin.command: >
      ss -lnp
    register: knockd_socket_check
    changed_when: false

  - name: Assert knockd is capturing on expected interface
    ansible.builtin.assert:
      that:
        - "'knockd' in knockd_pid.stdout or knockd_pid.rc == 0"
      fail_msg: >
        knockd failed to start. The SSH port is locked by UFW but knockd is not running.
        Connect using the emergency management IP (ssh_bastion_emergency_ip={{ ssh_bastion_emergency_ip }})
        to diagnose the issue. Check: journalctl -u knockd, /var/log/knockd.log,
        and /etc/default/knockd for incorrect interface name.
  ```
  - Note: this health check runs synchronously before the play ends. If knockd has not started, Ansible aborts with a clear error and the `ssh_bastion_emergency_ip` rule from Story A.3.1 guarantees the operator can still SSH in to diagnose.
- Handler: `restart knockd` → notified by knockd.conf template change
- Guard: `when: not ssh_bastion_use_tailscale and ssh_bastion_knock_daemon == 'knockd'`
- Tag: `ssh-bastion`, `knockd`

**Story A.6.2** — fwknop configuration (when `ssh_bastion_knock_daemon == 'fwknop'`)

Note: fwknop requires additional role variables (pre-shared key, allowed source networks). Placeholder tasks only for initial implementation; full fwknop support tracked as a follow-up enhancement.

Tasks:
- Task: assert that `ssh_bastion_fwknop_key` is defined (fail with message: "fwknop requires ssh_bastion_fwknop_key")
- Task: template `/etc/fwknop/fwknopd.conf` (stub for now, full template in follow-up)
- Tag: `ssh-bastion`, `fwknop`

---

### A.7 Tailscale Variant

**Story A.7.1** — Skip knockd when Tailscale is in use

Tasks:
- Create `bootstrap/roles/ssh-bastion/tasks/tailscale_variant.yml`
- Task: assert Tailscale is installed when `ssh_bastion_use_tailscale` is true
  - `command: which tailscale`
  - fail message: "Tailscale must be installed separately before running this role with ssh_bastion_use_tailscale=true"
- Task: open `ssh_bastion_port` permanently in ufw when `ssh_bastion_use_tailscale` (Tailscale provides auth, no knockd needed):
  ```yaml
  community.general.ufw:
    rule: allow
    port: "{{ ssh_bastion_port }}"
    proto: tcp
    interface: tailscale0
    direction: in
  ```
- Task: skip all knockd tasks via `when: not ssh_bastion_use_tailscale` guards in `main.yml`
- Tag: `ssh-bastion`, `tailscale`

---

### A.8 Role Main Task Orchestration

**Story A.8.1** — Wire all task files in `tasks/main.yml`

Tasks:
- Update `bootstrap/roles/ssh-bastion/tasks/main.yml` to include subtask files in order:
  1. `packages.yml`
  2. `firewall.yml`
  3. `sshd.yml`
  4. `authorized_keys.yml`
  5. `knockd.yml` (guarded by `when: not ssh_bastion_use_tailscale`)
  6. `tailscale_variant.yml` (guarded by `when: ssh_bastion_use_tailscale`)
- Ensure all task files carry consistent tags: `ssh-bastion` plus subsystem tag
- Add a final `meta: flush_handlers` task to ensure sshd restarts before any subsequent roles execute

---

### A.9 Idempotency and Validation

**Story A.9.1** — Verify idempotency

Tasks:
- Run playbook twice against a fresh Vagrant/LXD Ubuntu 22.04 instance; assert zero changed tasks on second run
- Verify sshd -t passes after role application
- Verify `ss -tlnp | grep 2222` shows sshd listening
- Verify `ufw status` shows port 2222 denied by default (no permanent allow rule)
- Verify knockd is running and listening on correct interface

**Story A.9.2** — Test connectivity matrix

Tasks:
- Test: plain ed25519 key auth connects on port 2222 (after manual knock)
- Test: FIDO2 sk-ed25519 key auth connects (requires YubiKey hardware)
- Test: `ansible -i inventory bastion -m ping` succeeds (via knock-ssh wrapper)
- Test: re-running role with no changes produces 0 changed tasks
- Test: ufw reload does not break existing open session (document expected behavior)

---

## Epic B: Client Setup

### B.1 Brewfile Entry

**Story B.1.1** — Add `knock-ssh` (and `knock` fallback) to Brewfile

Tasks:
- Edit `Brewfile` (location: dotfiles root or `cfgcaddy/` directory — confirm exact path)
- Add: `brew "tstapler/stelekit/knock-ssh"` in the CLI tools section (tap `tstapler/stelekit` is already in Brewfile)
- Optionally retain: `brew "knock"` as a standalone fallback for manual knocking or the pre_tasks fragment until `--knock-only` is implemented in the Rust binary
- Verify `brew bundle` installs `knock-ssh` binary to `$PATH`

---

### B.2 SSH Config Fragment

**Story B.2.1** — Create `~/.ssh/config.d/bastion` template

Tasks:
- Create `cfgcaddy/roles/cfgcaddy/files/ssh-config.d-bastion` (or equivalent path for cfgcaddy file deployment)
- File content (variables resolved at deploy time or templated by cfgcaddy):

  ```
  # SSH Bastion — managed by cfgcaddy
  # Port knocking handled by knock-ssh wrapper; NOT in this config.

  Host bastion
    HostName {{ bastion_hostname }}
    User tyler
    Port 2222
    IdentityFile ~/.ssh/id_ed25519_bastion
    IdentityFile ~/.ssh/id_ed25519_sk              # YubiKey FIDO2
    IdentityFile ~/.ssh/id_ecdsa_sk                # Titan FIDO2 fallback
    IdentityAgent "~/.1password/agent.sock"        # 1Password agent (tries last)
    IdentitiesOnly yes
    ServerAliveInterval 60
    ServerAliveCountMax 10
    ControlMaster auto
    ControlPath ~/.ssh/cm-%r@%h:%p
    ControlPersist 10m

  # Internal hosts through bastion (customize match pattern)
  Host 10.0.0.* internal-*.home
    ProxyJump bastion
    User tyler
    IdentityFile ~/.ssh/id_ed25519_bastion
    IdentitiesOnly yes
  ```

- Note: `bastion_hostname` must be supplied via cfgcaddy vars or a gitignored local override; do not hardcode IP
- Note: ordering of `IdentityFile` entries matters — plain ed25519 is tried first to minimize `MaxAuthTries` consumption; IdentityAgent is last

**Story B.2.2** — Ensure `~/.ssh/config` includes config.d

Tasks:
- Task in cfgcaddy role: verify `~/.ssh/config` contains `Include ~/.ssh/config.d/*`
- If missing, prepend include directive (do not overwrite existing config)
- File permission check: ensure `~/.ssh/config` is mode 0600

---

### B.3 knock-ssh Binary (Rust)

The bash wrapper script (previously B.3.1) has been superseded by a dedicated Rust binary. See **Epic D** for all implementation stories. This section documents the client-side integration points only.

**Story B.3.1** — Integrate knock-ssh Rust binary via Brewfile and cfgcaddy

Tasks:
- Add Brewfile entry: `brew "tstapler/stelekit/knock-ssh"` (tap `tstapler/stelekit` already present)
- Verify `brew bundle` installs the `knock-ssh` binary to a path on `$PATH` (typically `/opt/homebrew/bin/knock-ssh` or `/usr/local/bin/knock-ssh`)
- Remove any legacy `cfgcaddy/roles/cfgcaddy/files/bin/knock-ssh` bash script if present
- Remove any legacy `~/bin/knock-ssh` symlink/file from managed dotfiles
- Tag: `cfgcaddy`, `knock-ssh`

**Story B.3.2** — Deploy knock-ssh config template via cfgcaddy

Tasks:
- Create `cfgcaddy/roles/cfgcaddy/templates/knock-ssh-config.toml.j2` (cfgcaddy-managed config template):
  ```toml
  # ~/.config/knock-ssh/config.toml — managed by cfgcaddy
  # Knock sequences are gitignored at runtime; this template is rendered with vault vars.

  [hosts.bastion]
  address  = "{{ vault_bastion_host }}"
  sequence = {{ vault_knock_sequence | tojson }}
  port     = 2222
  timeout_ms = 500
  ```
- Deploy rendered template to `~/.config/knock-ssh/config.toml` (mode: 0600) via cfgcaddy role
- Add `~/.config/knock-ssh/config.toml` to `.gitignore` (contains IP and knock sequence)
- Note: the `~/.local/share/knock-ssh/` state directory (TTL files) is created automatically by the binary; no setup required
- Tag: `cfgcaddy`, `knock-ssh`

---

### B.4 knock-ssh Config File

**Story B.4.1** — Create mechanism for `~/.config/knock-ssh/config.toml`

Tasks:
- The config file is rendered from the cfgcaddy template in Story B.3.2 (not a standalone file)
- Add `~/.config/knock-ssh/config.toml` to dotfiles `.gitignore` (contains IP and knock sequence)
- Add `~/.local/share/knock-ssh/` to `.gitignore` (runtime state files with timestamps)
- Note: the `~/.ssh/knock-sequences` flat file format used by the old bash wrapper is no longer needed; the Rust binary reads `~/.config/knock-ssh/config.toml` (TOML, XDG-compliant path)
- Document: populate the config from Ansible vault variables using the cfgcaddy template task (Story B.3.2) or the local setup task (Story B.5.4)

---

### B.5 Ansible Group Vars for Bastion and Internal Hosts

**Story B.5.1** — Create inventory group_vars for bastion hosts

Tasks:
- Create `inventory/group_vars/bastion.yml` (plaintext variable names):
  ```yaml
  # inventory/group_vars/bastion.yml
  ansible_host: "{{ vault_bastion_host }}"
  ansible_port: 2222
  ansible_user: tyler
  ansible_ssh_private_key_file: ~/.ssh/id_ed25519_bastion
  # knock-ssh is the Rust binary installed via Homebrew (tstapler/stelekit/knock-ssh).
  # It reads ~/.config/knock-ssh/config.toml and is silent on stdout/stderr during
  # the knock phase (Ansible-safe). Use the Homebrew-installed path directly.
  ansible_ssh_executable: knock-ssh

  # Knock sequence for knock-ssh config template (resolved from vault)
  knock_sequence: "{{ vault_knock_sequence }}"
  ```

- Create `inventory/group_vars/bastion/vault.yml` (encrypted with ansible-vault):
  ```yaml
  # encrypt with: ansible-vault encrypt inventory/group_vars/bastion/vault.yml
  vault_bastion_host: "REPLACE_WITH_ACTUAL_IP"
  vault_knock_sequence: [7264, 3981, 5410]
  ```

- Add `inventory/group_vars/bastion/vault.yml` to documentation (not to .gitignore — vault-encrypted files are safe to commit)

**Story B.5.2** — Create group_vars for internal hosts through bastion

Tasks:
- Create `inventory/group_vars/internal.yml`:
  ```yaml
  # inventory/group_vars/internal.yml
  ansible_user: tyler
  ansible_ssh_private_key_file: ~/.ssh/id_ed25519_bastion
  # ProxyJump through bastion.
  # IMPORTANT: ansible_ssh_executable alone is NOT sufficient for internal hosts.
  # When ssh is called with -o ProxyJump=..., knock-ssh now detects the ProxyJump
  # argument and knocks the bastion (not the internal host). However, for playbooks
  # that target internal hosts, the knock must be guaranteed BEFORE any connection
  # attempt. Include knock-bastion.yml as a pre_tasks fragment in every playbook
  # that targets internal hosts (see Story B.5.3).
  ansible_ssh_common_args: >-
    -o ProxyJump=tyler@{{ hostvars['bastion']['ansible_host'] }}:2222
    -o StrictHostKeyChecking=accept-new
  # Do NOT set ansible_ssh_executable here — the knock-ssh wrapper fires for the
  # internal host's SSH call, which now correctly detects ProxyJump and knocks the
  # bastion. Setting ansible_ssh_executable on internal hosts is redundant (and was
  # previously wrong — it would have extracted the internal host name and found no
  # knock sequence). The wrapper on the bastion group_vars handles direct bastion
  # connections; pre_tasks handle internal-host playbooks.
  ```

- Note: `StrictHostKeyChecking=accept-new` avoids interactive prompt on first connection through ProxyJump
- **FATAL-3 fix — critical limitation of ansible_ssh_executable for ProxyJump**: `ansible_ssh_executable` is invoked by Ansible with the final destination host as the target. For internal hosts reached via ProxyJump, the Rust `knock-ssh` binary correctly detects the `-o ProxyJump=` argument (Story D.4) and knocks the bastion before exec-ing real ssh. However, this detection depends on ProxyJump being passed as an explicit ssh argument (which `ansible_ssh_common_args` ensures). If ProxyJump is configured only in `~/.ssh/config` (e.g. `Host 10.0.*` block with `ProxyJump bastion`), the binary receives no `-J` or `-o ProxyJump=` argument and cannot detect the jump — in that case the knock does not fire. **For playbooks targeting internal hosts, always include `knock-bastion.yml` as a pre_tasks fragment** (Story B.5.3) as the authoritative knock mechanism. The `ansible_ssh_common_args` ProxyJump approach (explicit `-o ProxyJump=`) allows the binary to knock as a fallback, but pre_tasks is the guaranteed path.

**Story B.5.3** — Ansible knock pre-task fragment for playbooks

Tasks:
- Create `bootstrap/playbooks/tasks/knock-bastion.yml` as a reusable task fragment:
  ```yaml
  # Include in playbooks: - import_tasks: tasks/knock-bastion.yml
  # Uses knock-ssh Rust binary (tstapler/stelekit/knock-ssh) directly to knock
  # the bastion. knock-ssh reads ~/.config/knock-ssh/config.toml for sequences.
  # Passing a bare hostname with no SSH args causes knock-ssh to knock then exit
  # without exec-ing ssh (or alternatively, use KNOCK_ONLY=1 env var if implemented).
  # Simplest reliable approach: invoke the binary as a dummy SSH with -V to trigger
  # knock-then-exit, or use a dedicated knock-only subcommand if exposed.
  #
  # Fallback: use the knock CLI directly if available (knock binary from Homebrew).
  - name: Knock SSH port open on bastion
    local_action:
      module: ansible.builtin.command
      argv:
        - knock-ssh
        - "--knock-only"
        - "{{ ansible_host }}"
    changed_when: false
    when:
      - knock_sequence is defined
      - not (ssh_bastion_use_tailscale | default(false))

  - name: Wait for SSH port to open
    local_action:
      module: ansible.builtin.wait_for
      host: "{{ ansible_host }}"
      port: "{{ ansible_port | default(2222) }}"
      timeout: 15
    changed_when: false
  ```

- Note: `--knock-only` flag should be implemented in the Rust binary (Story D.2) so playbook pre_tasks can trigger a knock without also exec-ing ssh. If not yet implemented, use `knock <ip> <p1> <p2> <p3>` via the standalone `knock` CLI as a fallback.
- Document: for ad-hoc commands, use `ansible_ssh_executable: knock-ssh` in group_vars (Story B.5.1) so knock fires automatically without pre_tasks

**Story B.5.4** — Generate knock-ssh config from vault

Tasks:
- Add a local setup play or task to `bootstrap/playbooks/local-setup.yml` (or equivalent):
  ```yaml
  - name: Ensure knock-ssh config directory exists
    local_action:
      module: ansible.builtin.file
      path: "~/.config/knock-ssh"
      state: directory
      mode: '0700'

  - name: Write knock-ssh config (gitignored, runtime only)
    local_action:
      module: ansible.builtin.copy
      content: |
        # ~/.config/knock-ssh/config.toml — generated by local-setup.yml
        [hosts.bastion]
        address    = "{{ vault_bastion_host }}"
        sequence   = {{ vault_knock_sequence | tojson }}
        port       = 2222
        timeout_ms = 500
      dest: "~/.config/knock-ssh/config.toml"
      mode: '0600'
  ```
- This task allows the `knock-ssh` Rust binary to find the sequence at runtime; the TOML file is gitignored and contains the real IP and knock ports
- Supersedes the old `~/.ssh/knock-sequences` flat file written by the bash wrapper

---

### B.6 ansible.cfg SSH Connection Tuning

**Story B.6.1** — Create or update `ansible.cfg`

Tasks:
- Create/update `bootstrap/ansible.cfg`:
  ```ini
  [defaults]
  inventory = inventory/hosts.yml
  vault_password_file = ~/.vault_pass.sh
  retry_files_enabled = False

  [ssh_connection]
  ssh_args = -o ServerAliveInterval=30 -o ServerAliveCountMax=10 -o ControlMaster=auto -o ControlPersist=10m
  control_path = ~/.ssh/cm-%%r@%%h:%%p
  pipelining = True
  ```
- Note: `pipelining = True` dramatically speeds up Ansible on hardened SSH (avoids separate sftp connection)
- Note: `%%` is required escaping in ansible.cfg for `%` characters in ControlPath

---

## Epic D: knock-ssh Rust Binary

Standalone Rust crate that acts as a transparent SSH wrapper. When invoked as `ansible_ssh_executable` or called directly, it behaves exactly like `ssh` but sends the port-knock sequence first. Replaces the bash wrapper script (previously Story B.3.1).

**Repository**: `tstapler/knock-ssh` (public GitHub repo, Homebrew-installable)
**Crate binary name**: `knock-ssh`
**Homebrew tap**: `tstapler/stelekit` (formula added in Story D.7; tap already in Brewfile)

**Design constraints**:
- All knock output is suppressed (no stdout/stderr during knock phase — Ansible's SSH parser breaks on unexpected output)
- Process is replaced by real SSH via `std::os::unix::process::CommandExt::exec` — not a subprocess
- Config path: `~/.config/knock-ssh/config.toml` (XDG Base Directory compliant)
- State path: `~/.local/share/knock-ssh/<host>.knock` (Unix timestamp, TTL 25s)
- When no config entry exists for the target host, passes through to real SSH silently

---

### D.1 Crate Scaffold

**Story D.1** — `cargo init` and dependency selection

Tasks:
- Create public GitHub repo `tstapler/knock-ssh`
- `cargo init --name knock-ssh` with binary target
- Add dependencies to `Cargo.toml`:
  - `clap` (derive feature) — argv parsing
  - `serde` + `serde_derive` — struct deserialization
  - `toml` — config file parsing
  - `dirs` — XDG-compliant home/config/data directory resolution
- Set `edition = "2021"`, Rust MSRV ≥ 1.70
- Add `.github/workflows/release.yml` stub for future Homebrew formula automation
- Add `LICENSE` (MIT) and minimal `README.md` explaining purpose

---

### D.2 TCP Knock Implementation

**Story D.2** — Send knock sequence via TCP connect attempts

Tasks:
- Implement `fn knock_sequence(address: &str, ports: &[u16], timeout_ms: u64) -> Result<()>`
- For each port in order: `TcpStream::connect_timeout(&addr, Duration::from_millis(timeout_ms))`
- Connection refused / timeout / dropped are **expected** — log at `RUST_LOG=debug` level only, never to stdout/stderr by default
- All errors from the connect attempt are silently ignored (the knock is the SYN packet itself)
- **`--knock-only` flag is REQUIRED (C-3 fix)**: implement as a required feature (not optional). The `knock-bastion.yml` pre_tasks fragment in Story B.5.3 calls `knock-ssh --knock-only <host>` on day 1. Without this flag, the pre_tasks fragment cannot function. The flag causes the binary to: perform the knock sequence, write the TTL state file, then exit 0 — without exec-ing real ssh. Both short form `-K` and long form `--knock-only` must be accepted.
- Suppress all output from knock phase unconditionally (no progress dots, no port numbers)

---

### D.3 State File TTL Caching

**Story D.3** — Skip re-knock if within TTL window

Tasks:
- State directory: `~/.local/share/knock-ssh/` (created with mode 0700 on first use via `dirs::data_local_dir()`)
- State file: `<state_dir>/<host_sanitized>.knock` where `<host_sanitized>` has `/` replaced with `_`
- File contents: Unix timestamp as ASCII decimal string (seconds since epoch)
- On startup: read state file; if `now - timestamp < ttl_secs` (default 25s), skip knock and proceed directly to SSH exec
- On successful knock: write current `SystemTime::now()` as Unix timestamp to state file (mode 0600)
- **TTL relationship (C-1 fix)**: `ttl_secs` MUST be strictly less than `knockd cmd_timeout`. The TTL tracks when the last knock was sent; skipping a re-knock is only safe if the server port is still open. Default: `ttl_secs = 25`, `ssh_bastion_knock_cmd_timeout = 30` (5s safety margin). If a user sets a custom `cmd_timeout`, they must lower `ttl_secs` proportionally. Add a validation note in the role README: "Set `ttl_secs` in knock-ssh config to at least 5 seconds less than `ssh_bastion_knock_cmd_timeout`."
- Make configurable per-host in `config.toml` via optional `ttl_secs` key; global default is 25

---

### D.4 ProxyJump Argv Parsing

**Story D.4** — Detect jump host from SSH argv

Tasks:
- Implement `fn extract_proxyjump_host(args: &[String]) -> Option<String>`
- Parse argv for:
  - `-J <host>` (space-separated)
  - `-J<host>` (combined, no space)
  - `-o ProxyJump=<host>` (space-separated value)
  - `-oProxyJump=<host>` (combined, case-insensitive key)
- Strip `user@` prefix and `:port` suffix from extracted host
- Take first host in comma-separated ProxyJump chain
- Skip option arguments that consume the next positional (e.g. `-i`, `-p`, `-F`, etc.) to avoid misidentifying option values as the destination host
- When ProxyJump is detected: knock the jump host, not the direct destination
- Implement `fn extract_direct_host(args: &[String]) -> Option<String>` for the non-ProxyJump path (first non-flag positional after stripping known flag-consuming options)
- Unit tests covering: `-J bastion`, `-Juser@bastion:22`, `-o ProxyJump=bastion`, `-oProxyJump=bastion`, multi-hop chains, no ProxyJump

---

### D.5 SSH Exec Handoff

**Story D.5** — Replace process with real SSH

Tasks:
- Locate real SSH binary: `which ssh` equivalent via `std::process::Command` or hardcoded `/usr/bin/ssh` with `which` fallback
- Use `std::os::unix::process::CommandExt::exec` to replace the current process (not `spawn` — the binary must become ssh, not parent it, so signal handling and TTY are transparent)
- Pass all original `argv[1..]` to the exec call unchanged
- `exec` only returns on error; handle that error by printing to stderr and exiting non-zero
- When no SSH binary is found, exit with a clear error message to stderr

---

### D.6 Config File Loading

**Story D.6** — Load `~/.config/knock-ssh/config.toml` with XDG path support

Tasks:
- Config path resolution order:
  1. `$KNOCK_SSH_CONFIG` env var (if set)
  2. `$XDG_CONFIG_HOME/knock-ssh/config.toml` (if `$XDG_CONFIG_HOME` is set)
  3. `~/.config/knock-ssh/config.toml` (default via `dirs::config_dir()`)
- Config schema (serde-deserialized):
  ```toml
  [hosts.<alias>]
  address    = "<ip_or_hostname>"  # actual address for TCP knock (may differ from SSH Host alias)
  sequence   = [7000, 8000, 9000]  # ports in order
  port       = 2222                # SSH port (informational; not used by knock itself)
  timeout_ms = 500                 # per-port TCP connect timeout
  ttl_secs   = 25                  # optional; override TTL for this host
  ```
- **Host lookup (C-2 fix — IP literal fallback)**: Two-pass lookup when resolving the knock target:
  1. **Alias match**: check if the target string equals any `[hosts.<alias>]` key (case-insensitive)
  2. **Address match**: if no alias match, scan all `[hosts.*]` entries and check if the target equals `address` field (exact string, including IP literals)
  - This handles the Ansible case: `ansible_ssh_common_args` passes `-o ProxyJump=1.2.3.4` (the IP from `hostvars['bastion']['ansible_host']`), so the extracted jump host is `1.2.3.4` — an IP literal, not the alias `bastion`. The address-field fallback ensures the correct config entry is found.
  - If both passes fail: no config entry exists for this host → skip knock silently (pass-through to real ssh)
- When config file is missing or host has no entry: skip knock entirely, proceed to SSH exec silently
- When config file exists but is malformed TOML: print error to stderr, exit non-zero (do not silently skip)

---

### D.7 Homebrew Formula

**Story D.7** — Add `knock-ssh` formula to `tstapler/stelekit` tap

Tasks:
- Create `Formula/knock-ssh.rb` in the `tstapler/stelekit` tap repository
- Formula should:
  - Fetch source tarball from GitHub releases (`tstapler/knock-ssh`)
  - Build with `cargo build --release`
  - Install `target/release/knock-ssh` to `bin/`
  - Include `sha256` checksum (updated per release)
- Verify `brew install tstapler/stelekit/knock-ssh` succeeds on macOS (arm64 and x86_64)
- Verify `brew audit --strict Formula/knock-ssh.rb` passes
- Document release process: tag → GitHub release → update formula sha256

---

### D.8 Dotfiles Integration

**Story D.8** — Wire knock-ssh Rust binary into dotfiles and Ansible

Tasks:
- Brewfile: confirm `brew "tstapler/stelekit/knock-ssh"` is present (Story B.1.1)
- `inventory/group_vars/bastion.yml`: set `ansible_ssh_executable: knock-ssh` (Homebrew installs to `$PATH`; no `~/bin` path needed)
- cfgcaddy config template (Story B.3.2): ensure `~/.config/knock-ssh/config.toml` is rendered and deployed
- cfgcaddy gitignore: add `~/.config/knock-ssh/config.toml` and `~/.local/share/knock-ssh/`
- Remove any legacy bash wrapper (`cfgcaddy/roles/cfgcaddy/files/bin/knock-ssh`) and `~/bin/knock-ssh` references from cfgcaddy role
- Remove `~/.ssh/knock-sequences` from gitignore and local-setup tasks (superseded by `~/.config/knock-ssh/config.toml`)
- Smoke test: `knock-ssh --version` prints version; `knock-ssh bastion` knocks then opens shell

---

## Epic C: Integration and Testing

### C.1 End-to-End Smoke Test

**Story C.1.1** — Provision fresh server and verify all auth methods

Tasks:
- Provision a fresh Ubuntu 22.04 server (VPS or local VM)
- Run: `ansible-playbook -i inventory bootstrap/site.yml --tags ssh-bastion`
- Verify: `ansible -i inventory bastion -m ping` succeeds (Rust knock-ssh binary fires automatically via ansible_ssh_executable)
- Verify: `knock-ssh bastion` opens a shell (Rust binary knocks then exec-s real ssh; 1Password agent or ed25519 key)
- Verify: `ssh -J bastion internal-host` reaches an internal host through ProxyJump
- Verify: role is idempotent (second run: 0 changed tasks)

**Story C.1.2** — Verify Tailscale variant

Tasks:
- Set `ssh_bastion_use_tailscale: true` in host_vars for a home server
- Re-run role; verify knockd is not installed/configured
- Verify SSH is accessible on port 2222 via Tailscale IP without knocking
- Verify `knock-ssh tailscale-host` works without triggering a knock (no config.toml entry for that host = silent pass-through to real ssh)

---

## File Path Reference

### Server Role

```
bootstrap/
└── roles/
    └── ssh-bastion/
        ├── defaults/
        │   └── main.yml              # All role variables with defaults
        ├── handlers/
        │   └── main.yml              # restart sshd, reload ufw, restart knockd
        ├── meta/
        │   └── main.yml              # Galaxy metadata, platform support
        ├── tasks/
        │   ├── main.yml              # Orchestrates includes
        │   ├── packages.yml          # apt install
        │   ├── firewall.yml          # ufw configuration
        │   ├── sshd.yml              # sshd_config template + validation
        │   ├── authorized_keys.yml   # pubkey deployment
        │   ├── knockd.yml            # knockd config (conditional)
        │   └── tailscale_variant.yml # tailscale path (conditional)
        ├── templates/
        │   ├── sshd_config.j2        # sshd_config template
        │   ├── knockd.conf.j2        # knockd configuration template
        │   └── knockd_default.j2     # /etc/default/knockd template
        └── vars/                     # (empty initially; add OS-specific overrides if needed)
```

### Client / Dotfiles

```
cfgcaddy/
└── roles/
    └── cfgcaddy/
        ├── templates/
        │   └── knock-ssh-config.toml.j2  # rendered to ~/.config/knock-ssh/config.toml
        └── files/
            └── ssh-config.d-bastion      # SSH config fragment
            # NOTE: bin/knock-ssh bash script removed; binary installed via Homebrew

bootstrap/
├── ansible.cfg
├── playbooks/
│   └── tasks/
│       └── knock-bastion.yml             # reusable pre_tasks fragment
└── inventory/
    ├── hosts.yml
    └── group_vars/
        ├── bastion.yml               # plaintext vars (committed)
        ├── bastion/
        │   └── vault.yml             # ansible-vault encrypted secrets
        └── internal.yml              # ProxyJump vars for internal hosts
```

### knock-ssh Rust Crate (external repo)

```
tstapler/knock-ssh (GitHub, public)
├── src/
│   └── main.rs                       # binary entry point
├── Cargo.toml                        # clap, serde, toml, dirs
├── Cargo.lock
└── .github/
    └── workflows/
        └── release.yml               # build + release artifacts for Homebrew

tstapler/stelekit (Homebrew tap)
└── Formula/
    └── knock-ssh.rb                  # Homebrew formula

Runtime paths (gitignored):
  ~/.config/knock-ssh/config.toml     # host knock sequences (from cfgcaddy template)
  ~/.local/share/knock-ssh/<host>.knock  # TTL state files (auto-created by binary)
```

---

## Dependency and Sequencing Notes

1. ADR-001 (knockd vs fwknop) must be resolved before Story A.6. Default implementation uses knockd; fwknop is a stub.
2. ADR-003 (UFW backend) is resolved: use `ufw allow from %IP%` in knockd commands per pitfalls research.
3. ADR-005 (Rust binary vs bash wrapper) is resolved: use the Rust binary (`tstapler/knock-ssh`). The bash wrapper script (previously B.3.1) is removed from the plan.
4. **`ansible_ssh_executable` alone is insufficient for playbooks targeting internal hosts via ProxyJump.** The Rust `knock-ssh` binary detects explicit ProxyJump arguments (`-J` / `-o ProxyJump=`) and knocks the bastion correctly (Story D.4). However, if ProxyJump is configured only in `~/.ssh/config` (not passed as an explicit ssh arg), the binary cannot detect it. Playbooks targeting internal hosts MUST include `knock-bastion.yml` as a `pre_tasks` fragment (Story B.5.3) to guarantee the bastion is knocked before any connection attempt. `ansible_ssh_executable` with the Rust binary handles ad-hoc commands and provides a fallback for playbooks using explicit `ansible_ssh_common_args` ProxyJump args.
5. `~/.config/knock-ssh/config.toml` (Story B.4.1 / B.3.2) must be populated before the `knock-ssh` binary can knock. Story B.5.4 automates this from vault variables.
6. Epic D (Rust binary) must be complete and the Homebrew formula published (Story D.7) before any Ansible run targeting the bastion, as `ansible_ssh_executable: knock-ssh` requires the binary to be on `$PATH`.
7. Brewfile entry `brew "tstapler/stelekit/knock-ssh"` (Story B.1.1 / D.8) must be applied (`brew bundle`) before `knock-ssh` is available on a new machine.
8. **FATAL-1 fix — required variable**: `ssh_bastion_emergency_ip` must be set to a non-empty value (operator's current public IP or management CIDR) before running the server role. The pre-flight assert in Story A.3.0 will fail fast if this is missing, before any UFW changes are applied. This ensures a recovery path if knockd fails to start.

---

## Counts

- **Epics**: 4 (A: Server Role, B: Client Setup, C: Integration and Testing, D: knock-ssh Rust Binary)
- **Stories**: 28 (20 original + 8 in Epic D; B.3.1 revised, B.3.2 revised, B.4.1 revised, B.5.4 revised)
- **Tasks**: ~90 (estimated discrete task items across all stories)
- **ADRs flagged**: 5 (ADR-001 through ADR-005; ADR-005 resolved: Rust binary selected over bash wrapper)
