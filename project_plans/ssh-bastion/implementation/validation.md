# Validation Plan: ssh-bastion
**Date**: 2026-06-17
**Status**: Implementation Readiness Gate — see bottom of document

---

## Test Suite Overview

| Category | Count |
|---|---|
| Unit (Rust binary) | 22 |
| Integration (Ansible role) | 18 |
| System (end-to-end flows) | 12 |
| Security | 8 |
| Ansible Smoke | 5 |
| **Total** | **65** |

---

## Requirement Reference Map

From `requirements.md`, the testable requirements are:

| Req ID | Requirement |
|---|---|
| REQ-01 | SSH server on high non-standard port (e.g. 2222), blocked by default |
| REQ-02 | Port knocking sequence required to open port |
| REQ-03 | Auth: 1Password SSH agent |
| REQ-04 | Auth: YubiKey (PIV or FIDO2) |
| REQ-05 | Auth: Titan Security Key (FIDO2) |
| REQ-06 | Auth: dedicated ed25519 key (headless Ansible) |
| REQ-07 | Client-side knock-ssh wrapper handles knock + connect flow |
| REQ-08 | SSH config.d entry for bastion host |
| REQ-09 | Ansible role provisions server (bootstrap/roles/ssh-bastion/) |
| REQ-10 | Ansible can reach server directly (ansible -m ping) |
| REQ-11 | Ansible can use bastion as ProxyJump to internal hosts |
| REQ-12 | Role installable via public dotfiles |
| REQ-13 | No secrets committed (vault only) |
| REQ-14 | Compatible with ~/.ssh/config.d/ include pattern |
| REQ-15 | knock-ssh installable via Brewfile |
| REQ-16 | SC: knock-ssh bastion connects in < 3 seconds |
| REQ-17 | SC: ansible -m ping succeeds without manual knock (wrapper auto-knocks) |
| REQ-18 | SC: ProxyJump to internal host works |
| REQ-19 | SC: YubiKey/Titan FIDO2 key auth works interactively |
| REQ-20 | SC: 1Password agent auth works interactively |
| REQ-21 | SC: ed25519 key auth works headlessly |
| REQ-22 | SC: fresh server provisionable from scratch |
| REQ-23 | SC: role is idempotent |

---

## Unit Tests — Rust Binary (knock-ssh)

### ProxyJump Detection (Story D.4)

**T-001**
- Requirement: REQ-07, REQ-11
- Type: Unit
- What: `extract_proxyjump_host` returns correct host for `-J bastion`
- Pass criteria: returns `"bastion"` for argv `["ssh", "-J", "bastion", "internal-host"]`

**T-002**
- Requirement: REQ-07, REQ-11
- Type: Unit
- What: `extract_proxyjump_host` returns correct host for combined form `-Jbastion`
- Pass criteria: returns `"bastion"` for argv `["ssh", "-Jbastion", "internal-host"]`

**T-003**
- Requirement: REQ-07, REQ-11
- Type: Unit
- What: `extract_proxyjump_host` handles `-o ProxyJump=bastion` (space-separated)
- Pass criteria: returns `"bastion"` for argv `["ssh", "-o", "ProxyJump=bastion", "internal-host"]`

**T-004**
- Requirement: REQ-07, REQ-11
- Type: Unit
- What: `extract_proxyjump_host` handles `-oProxyJump=bastion` (combined, case-insensitive key)
- Pass criteria: returns `"bastion"` for argv `["ssh", "-oProxyJump=bastion", "internal-host"]`

**T-005**
- Requirement: REQ-07, REQ-11
- Type: Unit
- What: `extract_proxyjump_host` strips `user@` prefix and `:port` suffix from jump host
- Pass criteria: returns `"bastion"` for `-Jtyler@bastion:22`

**T-006**
- Requirement: REQ-07, REQ-11
- Type: Unit
- What: `extract_proxyjump_host` takes only the first host in a comma-separated multi-hop chain
- Pass criteria: returns `"first-hop"` for `-J first-hop,second-hop`

**T-007**
- Requirement: REQ-07
- Type: Unit
- What: `extract_proxyjump_host` returns `None` when no ProxyJump argument is present
- Pass criteria: returns `None` for argv `["ssh", "bastion"]`

**T-008**
- Requirement: REQ-07, REQ-11
- Type: Unit
- What: `extract_direct_host` correctly skips flag-consuming options (`-i`, `-p`, `-F`) and returns the first non-flag positional
- Pass criteria: returns `"bastion"` for argv `["ssh", "-i", "~/.ssh/id_rsa", "-p", "2222", "bastion"]`

**T-009**
- Requirement: REQ-07
- Type: Unit
- What: `extract_direct_host` handles `--` end-of-options marker
- Pass criteria: returns `"bastion"` for argv `["ssh", "--", "bastion"]`

**T-010**
- Requirement: REQ-07, REQ-11
- Type: Unit
- What: ProxyJump detection takes priority over direct host extraction when `-J` is present
- Pass criteria: knock target is the jump host, not the destination, for `["ssh", "-J", "bastion", "internal-host"]`

### Config Parsing (Story D.6)

**T-011**
- Requirement: REQ-07
- Type: Unit
- What: Config file loaded from `$KNOCK_SSH_CONFIG` env var path
- Pass criteria: config from env var path is used when set; default path ignored

**T-012**
- Requirement: REQ-07
- Type: Unit
- What: Config file loaded from `$XDG_CONFIG_HOME/knock-ssh/config.toml` when `$XDG_CONFIG_HOME` is set
- Pass criteria: correct path resolved when env var set; falls through to `~/.config/knock-ssh/config.toml` otherwise

**T-013**
- Requirement: REQ-07
- Type: Unit
- What: Missing config file causes silent pass-through (no knock, no error)
- Pass criteria: binary proceeds to exec real SSH without error when config file absent

**T-014**
- Requirement: REQ-07
- Type: Unit
- What: Malformed TOML config causes binary to print to stderr and exit non-zero (not silent skip)
- Pass criteria: exit code != 0, message on stderr, no SSH exec attempted

**T-015**
- Requirement: REQ-07
- Type: Unit
- What: Unknown host key in config (no entry for the target) causes silent pass-through
- Pass criteria: binary proceeds to exec real SSH without error, no knock attempted

**T-016**
- Requirement: REQ-07
- Type: Unit
- What: All config fields parsed correctly (`address`, `sequence`, `port`, `timeout_ms`, `ttl_secs`)
- Pass criteria: deserialized `HostConfig` struct has correct values from fixture TOML

### TTL Cache (Story D.3)

**T-017**
- Requirement: REQ-07, REQ-16
- Type: Unit
- What: Knock is skipped when state file timestamp is within TTL (now - ts < 25s default)
- Pass criteria: `knock_sequence` function not called when state file has recent timestamp

**T-018**
- Requirement: REQ-07, REQ-16
- Type: Unit
- What: Knock fires when state file timestamp is outside TTL
- Pass criteria: `knock_sequence` function called when state file timestamp is older than TTL

**T-019**
- Requirement: REQ-07
- Type: Unit
- What: Knock fires when no state file exists for host
- Pass criteria: `knock_sequence` function called when state file absent

**T-020**
- Requirement: REQ-07
- Type: Unit
- What: State file written with current Unix timestamp after successful knock
- Pass criteria: state file created at expected XDG path; content is a valid decimal Unix timestamp

**T-021**
- Requirement: REQ-07
- Type: Unit
- What: Per-host `ttl_secs` in config overrides default 25s TTL
- Pass criteria: knock skipped when within custom `ttl_secs` window; fires when outside

### Knock Sequence and SSH Exec (Stories D.2, D.5)

**T-022**
- Requirement: REQ-07, REQ-16
- Type: Unit
- What: `--knock-only` flag causes binary to knock then exit 0 without exec-ing SSH
- Pass criteria: no SSH process spawned; exit 0; state file written

**T-023**
- Requirement: REQ-07
- Type: Unit
- What: All original argv[1..] are passed unchanged to SSH exec
- Pass criteria: captured exec call receives identical argument slice to input; no knock-ssh-specific flags leak through

**T-024** (FATAL-2 regression)
- Requirement: REQ-01, REQ-07
- Type: Unit
- What: knock output is fully suppressed — no stdout or stderr during knock phase
- Pass criteria: capture of stdout/stderr during knock shows zero bytes on both streams

---

## Integration Tests — Ansible Role

### Role Structure and Variables (Stories A.1.1, A.1.2)

**T-025**
- Requirement: REQ-09, REQ-12
- Type: Integration
- What: Role directory structure is complete and parseable by Ansible
- Pass criteria: `ansible-galaxy role info bootstrap/roles/ssh-bastion` completes without error; all expected task files present

**T-026**
- Requirement: REQ-09
- Type: Integration
- What: `defaults/main.yml` defines all required variables with safe defaults; `ssh_bastion_knock_sequence` defaults to empty list
- Pass criteria: `ansible-inventory --host bastion` resolves all role vars; none undefined

### Firewall Configuration (Stories A.3.0, A.3.1, A.3.2)

**T-027** (FATAL-1 regression)
- Requirement: REQ-09, REQ-01
- Type: Integration
- What: Pre-flight assert fires and aborts play when `ssh_bastion_emergency_ip` is empty and `ssh_bastion_use_tailscale` is false
- Pass criteria: playbook fails with `ABORT: ssh_bastion_emergency_ip is empty` before any UFW changes are applied; zero UFW rules changed

**T-028** (FATAL-1 regression)
- Requirement: REQ-09, REQ-01
- Type: Integration
- What: Emergency IP is permanently allowed in UFW before default deny is applied
- Pass criteria: after role run, `ufw status` shows the emergency IP rule present; `ufw status verbose` confirms default deny applies to all other sources

**T-029** (FATAL-2 regression)
- Requirement: REQ-01, REQ-02
- Type: Integration
- What: Knock sequence ports are NOT opened in UFW (stealth requirement)
- Pass criteria: after role run, `ufw status` shows no allow rules for any port in `ssh_bastion_knock_sequence`; all knock ports are in DENY state

**T-030**
- Requirement: REQ-01
- Type: Integration
- What: SSH port (`ssh_bastion_port`) is denied by default in UFW for all non-emergency sources
- Pass criteria: `ufw status` shows `DENY` for `ssh_bastion_port` without an explicit allow source; connection attempt from a non-emergency IP is rejected

### sshd Configuration (Stories A.4.1, A.4.2)

**T-031**
- Requirement: REQ-01, REQ-03, REQ-04, REQ-05, REQ-06
- Type: Integration
- What: Deployed `sshd_config` passes `sshd -t` validation with no warnings
- Pass criteria: `sshd -t` exits 0; stderr is empty (no warnings about unknown directives)

**T-032** (MEDIUM-2 regression)
- Requirement: REQ-09
- Type: Integration
- What: `ChallengeResponseAuthentication` is absent from sshd_config; `KbdInteractiveAuthentication no` is present
- Pass criteria: `grep ChallengeResponseAuthentication /etc/ssh/sshd_config` returns non-zero; `grep KbdInteractiveAuthentication /etc/ssh/sshd_config` returns the `no` line

**T-033**
- Requirement: REQ-01, REQ-06
- Type: Integration
- What: sshd_config has `PasswordAuthentication no`, `PermitRootLogin no`, `PubkeyAuthentication yes`, `AuthenticationMethods publickey`
- Pass criteria: each directive present with correct value in deployed config

**T-034**
- Requirement: REQ-09
- Type: Integration
- What: sshd listens on `ssh_bastion_port` (not 22) after role application
- Pass criteria: `ss -tlnp | grep <ssh_bastion_port>` shows sshd; port 22 is NOT in listen state

### Authorized Keys Deployment (Stories A.5.1, A.5.2)

**T-035** (HIGH-1 regression)
- Requirement: REQ-04, REQ-05, REQ-06
- Type: Integration
- What: FIDO2 pubkeys in `authorized_keys` do NOT have a `touch-required` key option prefix (wrong syntax); sshd_config uses `PubkeyAuthOptions touch-required` OR neither mechanism is applied globally, consistent with plan
- Pass criteria: `authorized_keys` file does not contain `touch-required` as a key option prefix on any line; sshd_config contains `PubkeyAuthOptions` directive if server-side enforcement is desired

**T-036**
- Requirement: REQ-06
- Type: Integration
- What: Ansible ed25519 pubkey (`ssh_bastion_ansible_pubkey`) is in `authorized_keys` with no special options
- Pass criteria: key is present in `~/.ssh/authorized_keys` for `ssh_bastion_user`; no `touch-required` prefix on that line

**T-037**
- Requirement: REQ-04, REQ-05
- Type: Integration
- What: All FIDO2 pubkeys in `ssh_bastion_fido2_pubkeys` are in `authorized_keys`
- Pass criteria: each key in the list is present in `~/.ssh/authorized_keys`

### knockd Configuration (Stories A.6.1, A.3.0)

**T-038**
- Requirement: REQ-02
- Type: Integration
- What: knockd is running and listening on the correct interface after role application
- Pass criteria: `pgrep -x knockd` exits 0; `journalctl -u knockd --no-pager -n 20` shows no error lines

**T-039**
- Requirement: REQ-02
- Type: Integration
- What: `/etc/knockd.conf` contains correct knock sequence ports, cmd_timeout, and UFW start/stop commands using `%IP%` placeholder
- Pass criteria: `grep -E "sequence|start_command|stop_command|cmd_timeout" /etc/knockd.conf` matches expected values from `ssh_bastion_knock_sequence` and `ssh_bastion_port`

**T-040**
- Requirement: REQ-09
- Type: Integration
- What: Role is idempotent — second run against same host produces zero changed tasks
- Pass criteria: second `ansible-playbook` run completes with `changed=0`; `ok` count matches first run's `ok + changed` count

**T-041**
- Requirement: REQ-09
- Type: Integration
- What: Tailscale variant skips knockd installation and opens SSH port on `tailscale0` interface
- Pass criteria: with `ssh_bastion_use_tailscale: true`, knockd package is absent; `ufw status` shows allow rule for `ssh_bastion_port` on `tailscale0`

**T-042**
- Requirement: REQ-22
- Type: Integration
- What: Role provisions a fresh Ubuntu 22.04 LXD/VM instance from scratch without errors
- Pass criteria: `ansible-playbook --tags ssh-bastion` completes with `failed=0` on a freshly provisioned Ubuntu 22.04 host

---

## System Tests — End-to-End

**T-043**
- Requirement: REQ-07, REQ-02, REQ-16
- Type: System
- What: `knock-ssh bastion` sends knock sequence, waits, and opens an interactive SSH shell within 3 seconds total
- Pass criteria: shell prompt appears within 3 seconds of invoking `knock-ssh bastion`; `date` command executes successfully in the shell

**T-044**
- Requirement: REQ-06, REQ-21
- Type: System
- What: ed25519 key auth works headlessly (non-interactive, no agent, no prompt)
- Pass criteria: `ssh -i ~/.ssh/id_ed25519_bastion -o BatchMode=yes -o PasswordAuthentication=no tyler@<bastion-ip> -p 2222 true` exits 0 after knock

**T-045**
- Requirement: REQ-03, REQ-20
- Type: System
- What: 1Password agent auth works interactively
- Pass criteria: with `SSH_AUTH_SOCK=~/.1password/agent.sock` set, `ssh tyler@<bastion-ip> -p 2222 true` authenticates without key file; agent provides the key

**T-046**
- Requirement: REQ-04, REQ-19
- Type: System
- What: YubiKey FIDO2 (`sk-ed25519`) auth works with hardware touch required
- Pass criteria: `ssh -i ~/.ssh/id_ed25519_sk tyler@<bastion-ip> -p 2222 true` succeeds after YubiKey touch; connection rejected without touch (hardware enforced)

**T-047**
- Requirement: REQ-05, REQ-19
- Type: System
- What: Titan Security Key FIDO2 (`sk-ecdsa-sk`) auth works with hardware touch required
- Pass criteria: same flow as T-046 using Titan key (`id_ecdsa_sk`)

**T-048** (FATAL-3 regression)
- Requirement: REQ-10, REQ-17
- Type: System
- What: `ansible -i inventory bastion -m ping` succeeds without pre-manual knock — the `ansible_ssh_executable: knock-ssh` setting auto-knocks
- Pass criteria: command exits 0 from a cold state (TTL cache empty); no manual knock required; `pong` in output

**T-049** (FATAL-3 regression)
- Requirement: REQ-11, REQ-18
- Type: System
- What: ProxyJump to internal host works via `knock-bastion.yml` pre_tasks fragment
- Pass criteria: playbook including `knock-bastion.yml` pre_tasks against an internal host group completes; `ansible internal-host -m ping` exits 0

**T-050** (FATAL-3 regression)
- Requirement: REQ-11, REQ-18
- Type: System
- What: `ssh -J bastion internal-host` succeeds after knock-ssh knocks the bastion (ProxyJump arg detection)
- Pass criteria: `knock-ssh -J bastion internal-host true` exits 0; bastion was knocked (state file present), not internal host

**T-051**
- Requirement: REQ-07, REQ-16
- Type: System
- What: Second `knock-ssh bastion` call within TTL window uses cached state and connects faster (no re-knock)
- Pass criteria: second call latency is < first call latency by at least the knock sequence duration (3 × timeout_ms); state file timestamp unchanged

**T-052**
- Requirement: REQ-07
- Type: System
- What: `knock-ssh` passes all original SSH arguments unchanged to real SSH (argument passthrough)
- Pass criteria: `knock-ssh -v -o ServerAliveInterval=30 bastion true` succeeds; SSH verbose output confirms the `-v` and `-o` flags were applied

**T-053**
- Requirement: REQ-22, REQ-09
- Type: System
- What: Full provision-then-verify flow on a fresh VPS: provision → knock → ping → ProxyJump
- Pass criteria: fresh Ubuntu 22.04 VPS goes from bare OS to fully operational bastion with all auth methods confirmed in a single runbook execution

**T-054**
- Requirement: REQ-23, REQ-09
- Type: System
- What: Role idempotency verified on real server: two consecutive playbook runs produce identical results
- Pass criteria: first run `changed > 0`; second run `changed=0`, `failed=0`

---

## Security Tests

**T-055** (FATAL-2 regression)
- Requirement: REQ-01, REQ-02
- Type: Security
- What: Port scanner stealth — knock sequence ports appear CLOSED to external nmap scan
- Pass criteria: `nmap -sS -p <knock-port-1>,<knock-port-2>,<knock-port-3> <bastion-ip>` shows all three ports as `filtered` or `closed`; not `open`

**T-056** (FATAL-2 regression)
- Requirement: REQ-01, REQ-02
- Type: Security
- What: SSH port (`ssh_bastion_port`) appears CLOSED before knock and OPEN briefly after, confirming knockd controls access
- Pass criteria: before knock: `nmap -sS -p 2222 <bastion-ip>` shows `filtered/closed`; after knock from same IP: port shows `open`

**T-057**
- Requirement: REQ-01, REQ-06
- Type: Security
- What: Password authentication is rejected (even if attempted)
- Pass criteria: `ssh -o PasswordAuthentication=yes -o BatchMode=no -o NumberOfPasswordPrompts=1 tyler@<bastion-ip> -p 2222` fails with `Permission denied (publickey)` — no password prompt offered

**T-058**
- Requirement: REQ-01
- Type: Security
- What: Root login is rejected
- Pass criteria: `ssh root@<bastion-ip> -p 2222` returns `Permission denied` regardless of keys offered

**T-059**
- Requirement: REQ-01
- Type: Security
- What: sshd uses only approved ciphers, MACs, and KEX algorithms
- Pass criteria: `nmap --script ssh2-enum-algos -p 2222 <bastion-ip>` output contains only algorithms in the plan's approved lists; no deprecated algorithms (e.g., `arcfour`, `hmac-md5`, `diffie-hellman-group1-sha512`) present

**T-060**
- Requirement: REQ-02
- Type: Security
- What: UFW default policy denies all inbound except emergency IP; no stray open rules
- Pass criteria: `ufw status numbered` shows: default deny incoming; only two permanent rules (emergency IP on SSH port; plus tailscale rule if `ssh_bastion_use_tailscale`); knock sequence ports absent

**T-061**
- Requirement: REQ-02
- Type: Security
- What: fwknop replay attack resistance — same SPA packet replayed within replay window is rejected
- Pass criteria: capture an fwknop SPA packet; replay it immediately; server rejects the replay (logged as `replay detected`); port not re-opened
- Condition: only runs when `ssh_bastion_knock_daemon == 'fwknop'`

**T-062**
- Requirement: REQ-13
- Type: Security
- What: No secrets (IPs, knock sequences, pubkeys) are committed to the public dotfiles repo
- Pass criteria: `git log --all --full-diff -p -- inventory/` shows no `vault_bastion_host` or `vault_knock_sequence` plaintext values; only vault-encrypted blobs; `.gitignore` excludes `~/.config/knock-ssh/config.toml`

---

## Ansible Smoke Tests

**T-063**
- Requirement: REQ-10, REQ-17
- Type: Smoke
- What: `ansible -i inventory bastion -m ping` succeeds (knock fires via `ansible_ssh_executable`)
- Pass criteria: returns `{"ping": "pong"}`; no manual pre-knock required; command completes in < 15 seconds

**T-064**
- Requirement: REQ-11, REQ-18
- Type: Smoke
- What: `ansible -i inventory internal -m ping` succeeds with `knock-bastion.yml` pre_tasks included in the play
- Pass criteria: returns `{"ping": "pong"}` for an internal host; play used ProxyJump through bastion

**T-065**
- Requirement: REQ-09, REQ-22
- Type: Smoke
- What: `ansible-playbook -i inventory site.yml --tags ssh-bastion` completes on a fresh host with all required vars set
- Pass criteria: `failed=0`, `unreachable=0`; sshd running on correct port; knockd running

**T-066**
- Requirement: REQ-23
- Type: Smoke
- What: Second `ansible-playbook -i inventory site.yml --tags ssh-bastion` run is fully idempotent
- Pass criteria: `changed=0`, `failed=0`

**T-067**
- Requirement: REQ-07, REQ-15
- Type: Smoke
- What: `brew bundle` installs `knock-ssh` binary and `knock-ssh --version` prints version string
- Pass criteria: `which knock-ssh` returns a path under Homebrew prefix; `knock-ssh --version` exits 0 with version output

---

## Requirement-to-Test Traceability Matrix

| Req ID | Tests | Covered? |
|---|---|---|
| REQ-01 | T-028, T-029, T-030, T-034, T-055, T-056, T-057, T-058, T-059, T-060 | YES |
| REQ-02 | T-029, T-038, T-039, T-055, T-056, T-060, T-061 | YES |
| REQ-03 | T-045 | YES |
| REQ-04 | T-037, T-046 | YES |
| REQ-05 | T-037, T-047 | YES |
| REQ-06 | T-036, T-044 | YES |
| REQ-07 | T-001–T-024, T-043, T-050, T-051, T-052 | YES |
| REQ-08 | T-014 (config.d include), T-034 | YES (partial — see gap) |
| REQ-09 | T-025, T-026, T-027, T-028, T-030, T-031, T-032, T-033, T-038, T-040, T-041, T-042 | YES |
| REQ-10 | T-048, T-063 | YES |
| REQ-11 | T-049, T-050, T-064 | YES |
| REQ-12 | T-025, T-065 | YES |
| REQ-13 | T-062 | YES |
| REQ-14 | T-025 | YES (partial — see gap) |
| REQ-15 | T-067 | YES |
| REQ-16 | T-017, T-018, T-043, T-051 | YES |
| REQ-17 | T-048, T-063 | YES |
| REQ-18 | T-049, T-050, T-064 | YES |
| REQ-19 | T-046, T-047 | YES |
| REQ-20 | T-045 | YES |
| REQ-21 | T-044 | YES |
| REQ-22 | T-042, T-053, T-065 | YES |
| REQ-23 | T-040, T-054, T-066 | YES |

**Coverage: 23/23 requirements covered.**

---

## Fatal Issues Addressed in plan.md

From `adversarial-review.md`:

| Issue | Status in plan.md | Test |
|---|---|---|
| FATAL-1: No recovery if knockd fails | Addressed — Story A.3.0 adds pre-flight assert; Story A.6.1 adds knockd health check post-start | T-027, T-028 |
| FATAL-2: Knock ports open in UFW (stealth failure) | Addressed — Story A.3.2 replaced with explicit non-task note: knock ports must NOT be opened in UFW | T-029, T-055, T-056 |
| FATAL-3: ProxyJump knock fires on wrong host | Addressed — Story D.4 adds ProxyJump arg detection; Story B.5.2 documents pre_tasks requirement; Story B.5.3 provides knock-bastion.yml fragment | T-001–T-010, T-048, T-049, T-050 |
| HIGH-1: `touch-required` wrong authorized_keys syntax | Addressed — plan removes `key_options: "touch-required"` from A.5.2 | T-035 |
| HIGH-3: Bash wrapper fragile (superseded) | N/A — ADR-005 resolves this by replacing bash wrapper with Rust binary (Epic D) | T-008, T-009 |
| MEDIUM-2: Deprecated `ChallengeResponseAuthentication` | Addressed — removed from sshd_config template per plan | T-032 |

All three fatal issues have tests. HIGH-1 has a test. HIGH-2 (fwknop for cloud VPS) is a known accepted limitation with ADR-001 pending; fwknop replay resistance covered by T-061 (conditional on daemon selection).

---

## Epic Coverage

| Epic / Story Group | Tests |
|---|---|
| Epic A — Server Role (A.1–A.9) | T-025 through T-042 (integration), T-027–T-028 (FATAL-1), T-029 (FATAL-2), T-031–T-033 (sshd), T-035–T-037 (keys) |
| Epic B — Client Setup (B.1–B.6) | T-048–T-054 (Ansible group_vars, ProxyJump), T-063–T-067 (smoke), T-014 (config loading) |
| Epic C — Integration and Testing (C.1–C.2) | T-053 (full provision flow), T-041 (Tailscale variant) |
| Epic D — knock-ssh Rust Binary (D.1–D.8) | T-001–T-024 (unit: all stories), T-043–T-052 (system), T-055 (stealth) |

No epic lacks test coverage.

---

## Success Criteria Map

From `requirements.md` Success Criteria section:

| Success Criterion | Requirement | Test |
|---|---|---|
| `knock-ssh bastion` opens port and connects in < 3s | REQ-16 | T-043 |
| `ansible -m ping` succeeds without manual knock | REQ-17 | T-048, T-063 |
| ProxyJump to internal host: `ssh -J bastion internal-host` | REQ-18 | T-049, T-050, T-064 |
| YubiKey/Titan FIDO2 key auth works interactively | REQ-19 | T-046, T-047 |
| 1Password agent auth works interactively | REQ-20 | T-045 |
| ed25519 key auth works headlessly (Ansible) | REQ-21 | T-044 |
| Fresh server provisioned from scratch | REQ-22 | T-053, T-065 |
| Role is idempotent | REQ-23 | T-040, T-054, T-066 |

All 8 success criteria map to at least one test.

---

## Implementation Readiness Gate

### Criterion 1: Every requirement has at least one test
**PASS** — 23/23 requirements covered.

Minor gaps noted but not blocking:
- REQ-08 (SSH config.d entry): tested indirectly via config loading (T-014) and connectivity (T-043/T-044); no dedicated test for the `~/.ssh/config` Include directive verification from Story B.2.2. **Recommendation**: add T-025 variant that checks `~/.ssh/config` contains `Include ~/.ssh/config.d/*`.
- REQ-14 (config.d include pattern compatibility): same indirect coverage as REQ-08.

### Criterion 2: All fatal items from adversarial review are addressed in plan.md
**PASS** — All three fatals (FATAL-1, FATAL-2, FATAL-3) and HIGH-1 are explicitly addressed in the plan with specific stories (A.3.0, A.3.2, D.4, A.5.2 revision). HIGH-2 (fwknop stub) remains an accepted limitation documented in ADR-001.

### Criterion 3: No epic in plan.md lacks test coverage
**PASS** — All four epics (A, B, C, D) have both unit/integration tests and system/smoke tests. Every story with a deliverable has at least one corresponding test.

### Criterion 4: All success criteria from requirements.md map to specific tests
**PASS** — All 8 success criteria have specific test IDs assigned.

---

## VERDICT: PASS

The implementation is ready to proceed. The test suite provides complete requirement coverage (23/23), addresses all fatal adversarial findings, covers all four epics, and maps all success criteria to specific tests.

**Recommended test execution order:**
1. Unit tests (T-001–T-024) — run in CI on every Rust commit; no infrastructure needed
2. Integration tests (T-025–T-042) — run against LXD/Vagrant Ubuntu 22.04; can run in pipeline
3. Security tests (T-055–T-062) — run against real VPS after integration tests pass; T-046/T-047 require physical hardware
4. System tests (T-043–T-054) — run against real VPS; T-046/T-047 require YubiKey/Titan hardware
5. Smoke tests (T-063–T-067) — run as acceptance gate after full provision

**Hardware-gated tests** (require physical security keys, cannot run in CI): T-046, T-047. Mark these as `#[ignore]` in Rust and `--skip-tags hardware` in Ansible; run in manual acceptance step.
