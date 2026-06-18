# Adversarial Review - ssh-bastion

## Verdict: CONCERNS

## Fatal Issues (BLOCKED)
None — the plan does not contain hard blockers. The most dangerous near-miss (lockout from missed `ssh_bastion_emergency_ip`) is addressed by the pre-flight assert in A.3.0. However, several concerns are severe enough to cause silent failures or security regressions if not addressed before implementation.

---

## Concerns (CONCERNS)

### C-1 [SEVERITY: HIGH] knock-ssh TTL cache direction is documented incorrectly — future config changes will cause silent lock-out

**Location**: D.3 (state file TTL), A.1.2 (`ssh_bastion_knock_cmd_timeout: 30`)

The plan says: "TTL value (25s) matches `knockd cmd_timeout` default with a 5s safety margin." This is backwards in the comment. The TTL is the window during which `knock-ssh` will *skip* re-knocking. If the binary skips the knock because the TTL file says it was 24 seconds ago, but knockd has already run `stop_command` (after 30s on the server), the SSH connection arrives at a closed port. The correct invariant is: `ttl_secs < cmd_timeout`. The values happen to be correct (25 < 30), but the comment says "TTL matches cmd_timeout with 5s safety margin" — implying they are close in value rather than that TTL must be smaller.

**Risk**: A user sets `ssh_bastion_knock_cmd_timeout: 20` (shorter, more secure) without changing `ttl_secs` in the knock-ssh config. The binary caches for 25s, tries to connect at second 22, port is already closed. This produces a confusing `Connection refused` with no knock log entry (because the binary skipped the knock).

**Fix**: In Story D.3, explicitly document the invariant: `ttl_secs < cmd_timeout`. Add a startup warning (to stderr, only if `KNOCK_SSH_DEBUG` is set) if `ttl_secs >= cmd_timeout`. Document the relationship in the B.3.2 config template comment.

---

### C-2 [SEVERITY: HIGH] ProxyJump detection fails when Ansible passes an IP literal instead of the "bastion" alias

**Location**: D.4 (ProxyJump argv parsing), B.5.2 (internal.yml)

When `ansible_ssh_common_args` contains `-o ProxyJump=tyler@{{ hostvars['bastion']['ansible_host'] }}:2222`, the Jinja2 expression resolves to an IP address (e.g., `1.2.3.4`). The knock-ssh config.toml uses an `[hosts.bastion]` alias key. The `extract_proxyjump_host` function extracts `1.2.3.4` from the `-o ProxyJump=` arg, then looks it up in the config — but the config has `[hosts.bastion]`, not `[hosts.1.2.3.4]`. No match → no knock → silent connection failure.

**The config lookup will always miss when Ansible passes an IP literal instead of the alias.** The plan does not address this mismatch anywhere. The `address` field in config.toml is the knock target address, but the lookup key is the host alias name.

**Fix options**: Add an `ip` or `aliases` field to the config.toml host stanza so the binary can also match by IP address. Or change `ansible_ssh_common_args` to use `-o ProxyJump=bastion` (SSH config alias) rather than the raw IP, requiring the control machine to have the bastion Host block configured. Or document clearly that ProxyJump auto-knock does not work for internal hosts when the IP form is used, making pre_tasks (B.5.3) the only reliable path — which is fine, but the current plan implies it is a working fallback.

---

### C-3 [SEVERITY: HIGH] `--knock-only` flag is a future intention, not an existing implementation — pre_tasks will fail on day 1

**Location**: B.5.3, D.2

Story B.5.3 documents the pre_tasks fragment calling `knock-ssh --knock-only <host>`. Story D.2 says "Implement optional `--knock-only` flag" as part of the TCP knock story. If D.2 is implemented without `--knock-only`, or that flag is released after Epic B integration testing, the pre_tasks fragment calling `knock-ssh --knock-only` will fail with an unrecognized argument, blocking all playbooks targeting internal hosts.

The fallback note at B.5.3 says to use the standalone `knock` CLI, but that binary is listed as optional in B.1.1, and passing knock sequences as positional arguments requires them to be available outside the TOML config, which is not set up.

**Fix**: Mark `--knock-only` as a required feature gate for the Epic B/D integration. Do not publish or test the pre_tasks fragment until D.2 with `--knock-only` is complete and in the Homebrew formula. Alternatively, ship the pre_tasks using the standalone `knock` CLI as primary (not fallback) and treat `--knock-only` as an enhancement.

---

### C-4 [SEVERITY: HIGH] UFW task ordering — `ufw default deny` may fire before the emergency IP allow rule on already-enabled UFW hosts

**Location**: A.3.1 task order description

The task order in A.3.1 as described is: (1) set default deny incoming, (2) set default allow outgoing, (3) allow emergency IP, (4) enable UFW. On a host where UFW is already enabled (common on cloud Ubuntu images), step (1) takes effect immediately and establishes the deny policy before the emergency IP rule is inserted in step (3). During the gap between steps (1) and (3), new inbound connections from any IP (including Ansible's control machine) are denied. Since Ansible uses persistent SSH connections via ControlMaster, existing sessions survive, but any Ansible connection that requires a new SSH channel during this gap fails.

**Fix**: Reorder tasks: (1) add emergency IP allow rule, (2) set default policies, (3) enable UFW. The `community.general.ufw` module permits this ordering. The plan description misleads implementers with its current listing even if the module ultimately applies atomically on a fresh enable.

---

### C-5 [SEVERITY: MEDIUM] `ssh_bastion_ansible_pubkey` defaults to `""` — no assert before authorized_keys deployment

**Location**: A.1.2 defaults, A.5.2 authorized_keys deployment

`ssh_bastion_ansible_pubkey: ""` is the default. Story A.5.2 calls `ansible.posix.authorized_key` with `key: "{{ ssh_bastion_ansible_pubkey }}"` but adds no guard for the empty case. The `ansible.posix.authorized_key` module with an empty `key` argument may either fail with a cryptic error or silently skip, depending on the module version. There is no `assert` to require this variable before the authorized_keys task runs.

If the key is empty and the module skips silently, the Ansible automation key is not deployed. The operator has no recovery path via Ansible after the role locks down SSH to pubkey-only.

**Fix**: Add an `ansible.builtin.assert` in `authorized_keys.yml` that `ssh_bastion_ansible_pubkey` is non-empty before the deployment task (parallel to the emergency IP assert in A.3.0).

---

### C-6 [SEVERITY: MEDIUM] `key_options: "touch-required"` in authorized_keys may be rejected by the Ansible module

**Location**: A.5.2, FIDO2 key deployment

Story A.5.2 deploys FIDO2 keys with `key_options: "touch-required"`. The `touch-required` keyword in OpenSSH is a *sshd_config* directive (`PubkeyAuthOptions touch-required`), not an authorized_keys option prefix. Some versions of `ansible.posix.authorized_key` pass the value as a literal string prefix to the key line; if the resulting file looks like `touch-required sk-ed25519@openssh.com AAAA...`, OpenSSH on the server may reject the entry as an unrecognized option, breaking all FIDO2 key authentication.

Additionally, `PubkeyAuthOptions touch-required` as an authorized_keys option was added in OpenSSH 8.2 only in the form of the global sshd_config directive. Per-key enforcement in authorized_keys requires the `no-touch-required` option to *disable* touch for specific keys; there is no `touch-required` per-key option in the authorized_keys file format.

**Fix**: Remove `key_options: "touch-required"` from the authorized_key task. If server-side touch enforcement is desired, add `PubkeyAuthOptions touch-required` to the sshd_config template — but this then requires adding `no-touch-required` to the plain ed25519 Ansible key entry to allow unattended automation. Alternatively, rely on key generation flags (`-O verify-required` at keygen time) and document that touch is client-enforced.

---

### C-7 [SEVERITY: MEDIUM] ControlMaster multiplexing may cause connect-after-TTL-expiry to miss re-knock

**Location**: B.6.1 ansible.cfg (`ControlPersist 10m`), D.3 TTL caching

With `ControlPersist 10m`, when a ControlMaster connection is established, `knock-ssh` is invoked once (for the master) and writes a TTL timestamp. All subsequent SSH calls for 10 minutes reuse the master socket without invoking `knock-ssh`. After ControlPersist expires, the master closes. The *next* invocation of `knock-ssh` checks the TTL file, which records the timestamp from the original knock 10+ minutes ago. The TTL (25s) has long expired, so the binary correctly re-knocks. This case is fine.

The dangerous edge case: ControlMaster is disabled or bypassed for a specific invocation (e.g., `ssh -o ControlMaster=no bastion`), and the TTL was written seconds ago from a different invocation. The binary skips the knock (TTL still valid), but the port is closed because `cmd_timeout` (30s) already fired. `Connection refused` with no knock log entry.

This is a low-probability scenario but `ControlMaster=no` is a legitimate override, and it silently breaks without any indication that a knock was expected.

**Fix**: Document this interaction in the knock-ssh README. Consider writing the TTL timestamp at exec-handoff time (latest possible moment) rather than at knock-completion time to maximize the accuracy of the TTL window.

---

### C-8 [SEVERITY: MEDIUM] knockd health check uses `ss -lnp` but knockd uses libpcap — check is a no-op

**Location**: A.6.1 knockd health check

The health check includes:
```yaml
- name: Verify knockd is listening on the correct interface
  ansible.builtin.command: >
    ss -lnp
  register: knockd_socket_check
```

knockd uses `libpcap` (raw packet capture), not a bound socket. `ss -lnp` will never show a knockd entry. The task captures output but there is no subsequent `assert` on `knockd_socket_check.stdout`. This task is effectively a no-op that always passes, providing zero verification that knockd is monitoring the correct interface.

**Fix**: Replace with a meaningful check. `grep -i "listening on" /var/log/knockd.log` or `journalctl -u knockd --no-pager -n 20` will show the startup message including the interface name. Assert that the expected interface appears in the output.

---

### C-9 [SEVERITY: MEDIUM] sshd_config template missing `MaxStartups` and `GSSAPIAuthentication no`

**Location**: A.4.1 sshd_config template

The plan lists all hardening directives but omits two that are present in the `devsec.hardening` reference:

- `MaxStartups 10:30:100` — without this, the default allows 100 pre-authentication connections, enabling simultaneous handshake floods. Lower risk behind port knocking but still a hardening gap.
- `GSSAPIAuthentication no` — the default is distribution-dependent. Ubuntu typically ships with it enabled. An attacker who can perform DNS hijacking or Kerberos spoofing can exploit GSSAPI authentication if not explicitly disabled.

**Fix**: Add `MaxStartups 10:30:100` and `GSSAPIAuthentication no` to the sshd_config template in A.4.1.

---

### C-10 [SEVERITY: MEDIUM] fwknop stub will mislead operators — no NTP requirement, no client tool, no knock-ssh SPA support

**Location**: A.6.2

Story A.6.2 is explicitly a stub. The stub asserts `ssh_bastion_fwknop_key` is defined and templates a stub conf file. There is no task to ensure NTP synchronization (fwknop requires clocks within ~2 minutes; pitfalls research Section 1 identifies this as critical). There is no task to install `fwknop-client` on the control machine (only `fwknop-server` is referenced).

Critically, the knock-ssh Rust binary (Epic D) has no SPA/fwknop support — it sends TCP knock sequences only. If `ssh_bastion_knock_daemon == 'fwknop'` is set, the server is configured for SPA but `knock-ssh` still sends TCP packets. The connection will silently fail.

**Fix**: Either remove the fwknop story from initial implementation scope and mark it explicitly as out-of-scope for v1 with a clear `ansible.builtin.fail` task that aborts if selected, or implement fwknop fully. The current stub gives operators false confidence.

---

### C-11 [SEVERITY: LOW] `ssh_bastion_knock_close_sequence` comment says "defaults to reverse" but actual default is `[]`

**Location**: A.1.2 defaults, A.6.1 template

The `ssh_bastion_knock_close_sequence` variable comment says "reverse sequence; defaults to reverse of knock_sequence" but the actual default is `[]`. The Jinja2 template guards the `[closeSSH]` stanza with `{% if ssh_bastion_knock_close_sequence | length > 0 %}`. With the default `[]`, the close stanza is never added and port closure relies entirely on `cmd_timeout`. There is no Ansible task that auto-populates this from the reverse of `knock_sequence`.

**Fix**: Either implement auto-reverse in the Jinja2 template (`{{ ssh_bastion_knock_sequence | reverse | list | join(',') }}` as fallback when the variable is empty), or update the comment to remove "defaults to reverse" and replace with "optional; if empty, port closes only via cmd_timeout."

---

### C-12 [SEVERITY: LOW] `MaxAuthTries 3` with 3 IdentityFile entries plus IdentityAgent may exhaust auth attempts before 1Password key is tried

**Location**: B.2.1 SSH config fragment, A.1.2 `ssh_bastion_max_auth_tries: 3`

The SSH config fragment lists:
1. `~/.ssh/id_ed25519_bastion`
2. `~/.ssh/id_ed25519_sk` (YubiKey)
3. `~/.ssh/id_ecdsa_sk` (Titan)
4. `IdentityAgent ~/.1password/agent.sock` (1Password — tried last)

With `MaxAuthTries 3`, if none of the three IdentityFile keys are present or work (e.g., hardware key absent on the laptop), all three attempts are consumed before the 1Password agent is tried. The connection drops with `Too many authentication failures` and no 1Password prompt is ever shown.

**Fix**: Consider `MaxAuthTries 4` when using this exact combination, or document that the 1Password agent is only tried when at least one of the three IdentityFile keys succeeds, and users should remove stale key file entries if they primarily use 1Password.

---

### C-13 [SEVERITY: LOW] Homebrew formula sha256 update process is manual with no automation story

**Location**: D.7

Story D.7 documents that the formula requires a `sha256` checksum updated per release and says "Document release process: tag → GitHub release → update formula sha256." The `.github/workflows/release.yml` is described as a stub with no automation. Every `knock-ssh` release requires a manual PR to the `tstapler/stelekit` tap. If this step is forgotten, `brew upgrade knock-ssh` will fail with a checksum mismatch.

**Fix**: Add a concrete GitHub Actions workflow story that uses `brew bump-formula-pr` or equivalent to automate the sha256 update on release. This is a maintainability issue, not a security issue, but it will block upgrades if left manual.

---

## Clean Items

**A.3.0 Pre-flight assert for emergency IP** — The emergency IP assertion before any UFW changes is correctly placed and guarded with `when: not ssh_bastion_use_tailscale`. The `fail_msg` includes recovery instructions.

**A.6.1 knockd uses `ufw allow` not raw iptables** — Correctly addresses the UFW reload pitfall from research. UFW commands write to backing files and survive `ufw reload`. This is the right choice per research Section 3.

**A.4.2 Moduli hardening with `slow` tag** — The expensive operation is correctly tagged to allow skipping. The < 3071 bit threshold is consistent with current NIST guidance.

**D.5 `exec` handoff via `CommandExt::exec`** — Using process replacement instead of spawning ssh as a child process is the correct design. Spawning would break TTY allocation, signal handling, and exit code transparency for Ansible.

**D.6 Missing config = silent passthrough** — The design correctly falls through to plain ssh when no config entry exists for the target host. This is Ansible-safe: `ansible_ssh_executable: knock-ssh` can be set on hosts where knocking is not configured without breaking anything.

**A.5.2 Per-key `touch-required` vs global `PubkeyAuthOptions`** — The design correctly applies `touch-required` only to FIDO2 keys and not the plain ed25519 Ansible key, avoiding the FIDO2/Ansible incompatibility documented in pitfalls Section 4. (Though the implementation method via `key_options` has its own issue documented in C-6.)

**A.7.1 Tailscale variant skips knockd** — The branching logic is correct. For Tailscale-reachable home servers, port knocking is redundant and the plan correctly short-circuits the entire knockd subsystem.

**B.5.1 Vault split pattern** — The vars + vault_vars split (plaintext names in group_vars, encrypted values in vault.yml) is correct Ansible best practice. The vault.yml is safe to commit.

**B.6.1 `pipelining = True` in ansible.cfg** — Correct for hardened SSH. Avoids a second sftp connection per task, which would each require a fresh knock cycle.

**A.9.2 Idempotency test plan includes `ufw reload` check** — "ufw reload does not break existing open session" is an appropriate integration test that directly targets the UFW/knockd interaction pitfall.
