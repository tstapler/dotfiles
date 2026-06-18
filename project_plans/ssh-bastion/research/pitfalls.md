# SSH Bastion Pitfalls Research

Research into known failure modes, security issues, and implementation pitfalls for the ssh-bastion role.

---

## 1. Port Knocking Security: knockd vs fwknop

### knockd Limitations

knockd provides **security through obscurity only**. The knock sequence is transmitted as plain TCP SYN headers with no authentication or encryption. Anyone sniffing the network (e.g., on the same cloud provider segment, via a compromised router) can capture the sequence and replay it. There is no built-in replay protection.

**Specific attack vectors:**

- **Packet sniffing / eavesdropping**: The knock sequence appears as a series of connection attempts to specific ports. tcpdump or Wireshark will expose it trivially on any network where the attacker has access to the path.
- **Replay attacks**: There is nothing in knockd to prevent an attacker from replaying a captured sequence later to open the port. The same sequence always works.
- **SYN spoofing**: An attacker who can spoof source IPs (e.g., on a broadcast LAN) can enumerate the 3-port sequence and open the rule for a victim IP they don't control, causing a port to open that they then can't use (minor DOS) — or more relevantly, an attacker on the same LAN can spoof the knock and have the rule open for their own actual IP by sending crafted packets in rapid succession.
- **Brute force**: A 3-port sequence from ports 1–65535 has ~(65535^3 / 6) ≈ 46 billion ordered combinations. At typical knock scan rates this is impractical, but knockd has no rate-limiting on knock attempts by default.

### fwknop (Single Packet Authorization) is Significantly Better

fwknop sends **one encrypted, HMAC-authenticated UDP packet** containing: desired destination port, client IP, timestamp, and a random nonce. The server validates:
1. HMAC integrity (detect tampering)
2. Timestamp within a window (prevent replay: SHA-256 digest of each valid packet is stored and rejected on reuse)
3. Decryption with a shared symmetric key (AES) or GPG

**Result**: Even if an attacker captures the SPA packet, replay is blocked by the timestamp check + digest store. The sequence can't be brute-forced from headers.

**Practical recommendation for this project**: knockd is acceptable for a personal home server on a trusted ISP connection where the risk model is automated internet scanners, not targeted network-level attackers. For a public-facing VPS where someone could be on the same datacenter network segment, fwknop is meaningfully more secure. The Ansible role should support both, with fwknop as the recommended default for cloud targets.

**fwknop additional pitfall**: Client and server must have **NTP-synchronized clocks**. A clock drift of more than ~2 minutes will cause all SPA packets to be rejected as replays. Ensure `systemd-timesyncd` or `chrony` is running on the server.

---

## 2. knockd Race Condition: Rule Opens After SSH Connect Attempt

### The Problem

knockd calls the configured command (e.g., `iptables -I INPUT ...` or `ufw allow ...`) synchronously when the sequence completes, but there is a real-world timing gap:

1. knockd processes the final port in the sequence
2. knockd forks/execs the shell command
3. The iptables/ufw rule is added
4. The rule takes effect in the kernel

Steps 2–4 add approximately 50–300ms. If the `knock-ssh` wrapper script does:

```bash
knock $HOST $P1 $P2 $P3 && ssh $USER@$HOST
```

...the SSH SYN packet may arrive at the server before the firewall rule is active, resulting in **Connection refused**.

### Observed Behavior

- The `knock` client returns after sending the last packet, not after the server has processed it.
- Network latency adds further indeterminacy — the knock packets themselves take time to arrive and be processed.
- A `sleep 1` after the knock sequence is the conventional workaround, but it is fragile: on a high-latency connection (>500ms RTT), even `sleep 1` may be insufficient.

### Recommended Mitigation

Use a retry loop with exponential backoff rather than a fixed sleep:

```bash
knock $HOST $P1 $P2 $P3
for i in $(seq 1 5); do
    ssh -o ConnectTimeout=3 -o BatchMode=yes $USER@$HOST && break
    sleep $i
done
```

Alternatively, use `knock -d 300` (300ms delay between knocks) to spread the sequence over time, giving knockd more processing headroom before the final port arrives and the command runs.

For the `knock-ssh` wrapper script, default to `sleep 2` and document it as tunable.

---

## 3. ufw reload Wiping knockd-Opened Rules

### The Problem

knockd opens firewall rules dynamically at runtime (e.g., `ufw allow from 1.2.3.4 to any port 2222`). When `ufw reload` is run — which happens on Ansible provisioning runs, package upgrades, or manual admin actions — **all dynamically added rules are wiped** because ufw reloads its persisted configuration from disk, discarding any in-memory rule additions that were not saved.

This means: if a user is connected and another Ansible run happens that calls `ufw reload` or restarts the ufw service, the knockd-opened rule disappears. The next connection attempt will fail until the knock sequence is sent again.

### Root Cause

ufw stores its canonical rule set in `/etc/ufw/user.rules` and `/etc/ufw/user6.rules`. Rules added via `ufw allow ...` at runtime **are written to disk** (unlike raw `iptables` commands). However, rules added via knockd using `ufw allow from %IP% ...` are **also written to disk** by ufw — this is actually the safer pattern.

The real problem is that **direct iptables rules** (used in many knockd examples: `/sbin/iptables -I INPUT -s %IP% ...`) are **not written to ufw's state files**. A `ufw reload` rebuilds iptables from ufw's on-disk state, discarding all raw iptables additions.

### Solutions

**Option A (recommended): Configure knockd to use `ufw` commands, not raw iptables**

```ini
[openSSH]
    start_command = /usr/sbin/ufw allow from %IP% to any port 2222
    stop_command  = /usr/sbin/ufw delete allow from %IP% to any port 2222
```

These rules are written to ufw's backing files and survive `ufw reload`. The tradeoff is that `ufw allow` is slower than `iptables -I` (parses and rewrites rule files on disk).

**Option B: Use raw iptables with a dedicated high-priority chain**

Configure knockd to insert rules into a static chain (e.g., `KNOCK-ACCEPT`) that is always jumped-to from INPUT, before ufw's chains. This chain survives `ufw reload` because ufw doesn't manage it. Requires custom `/etc/ufw/before.rules` plumbing.

**Option C: Accept the limitation**

For single-user personal use, the knock-then-connect workflow is always done fresh, so existing sessions dropping after a ufw reload is not a practical problem. The Ansible role should document this behavior and avoid triggering ufw reload during active connections.

**Critical Ansible pitfall**: The Ansible role must not call `ufw reload` as a handler while it is connected _through_ the bastion port that knockd manages. Structure handlers so `sshd` restart and `ufw reload` happen before the knock port is the only access path, or ensure Ansible connects from an IP in the management allowlist.

---

## 4. FIDO2 SSH Key Pitfalls

### User Presence (Touch) Requirements

FIDO2 keys (`sk-ed25519`, `ecdsa-sk`) require **physical touch by default**. This is enforced at the key generation level and verified by the SSH client on every signing operation. Even with ssh-agent loaded, the touch requirement is not cached — each new authentication attempt requires a physical touch.

Server-side enforcement via `PubkeyAuthOptions touch-required` in `sshd_config` makes this explicit. Without it, a key generated with `no-touch-required` at keygen time will bypass touch on auth.

**Generating a key without the touch requirement** (for headless use):

```bash
ssh-keygen -t ed25519-sk -O no-touch-required -f ~/.ssh/id_ed25519_sk_notouch
```

The `authorized_keys` entry must also include `no-touch-required` or the server will reject it.

### macOS System SSH Does Not Support FIDO2

The bundled `/usr/bin/ssh-keygen` on macOS does **not support FIDO2 key generation** (no libfido2 linkage). Homebrew `openssh` must be installed and used: `brew install openssh`. After install, `command -v ssh-keygen` may still point to `/usr/bin/ssh-keygen` until the shell is restarted or `hash -r` is run. This is a common source of "invalid format" errors when generating sk- keys on macOS.

### Ansible + FIDO2: Fundamental Incompatibility

FIDO2 keys requiring touch **cannot be used for unattended Ansible automation**. Specifically:

- **Ansible 12+** explicitly removed the code path that allowed the SSH subprocess to prompt for hardware key touch/PIN. Bug tracked as ansible/ansible#86154.
- Running a playbook against multiple hosts with `--forks > 1` means multiple SSH handshakes happen in parallel — only one touch can be registered at a time; all other forks fail.
- CI/CD and cron-based Ansible runs have no interactive terminal at all.

**Correct architecture for this project**:

- FIDO2 keys (YubiKey, Titan) are for **interactive SSH sessions only**.
- Ansible automation uses the **dedicated ed25519 key file** on disk (`ansible_ssh_private_key_file`).
- The bastion `authorized_keys` must include both the FIDO2 public keys (for interactive use) and the plain ed25519 key (for Ansible).
- `PubkeyAuthOptions touch-required` on the server would block the plain ed25519 key — do **not** set this server-wide. Instead, use per-key `authorized_keys` options: prefix the FIDO2 key entries with `touch-required`, leave the ed25519 entry without it.

---

## 5. 1Password Agent Pitfalls

### Socket Path Instability

The 1Password SSH agent socket path has changed across versions and platform updates:

| Situation | Socket Path |
|-----------|-------------|
| Standard macOS (current) | `~/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock` |
| Symlink (must be created manually or by 1Password settings) | `~/.1password/agent.sock` |
| Requirements.md reference | `~/.1password/agent.sock` |

The symlink path `~/.1password/agent.sock` is what the requirements reference and what should be set in `SSH_AUTH_SOCK` / `IdentityAgent`. It is not created automatically on all installs — users must enable it in 1Password Settings > Developer > SSH Agent.

### Agent Not Running in Non-GUI Sessions

1Password's SSH agent is a **GUI application process**. It only runs when the 1Password desktop app is open and unlocked. Implications:

- **SSH over tmux/screen after detach**: If the session detaches and the GUI is closed or the laptop sleeps with 1Password locking, the agent socket vanishes. Reconnection attempts fail with `Connection refused` on the socket.
- **cron, launchd without GUI**: Any job running outside a graphical login session will not have access to the 1Password agent.
- **Remote SSH sessions (ssh-agent forwarding)**: Forwarding the 1Password socket to a remote host works only when the local GUI app is running. The `ForwardAgent yes` in SSH config will forward whatever `SSH_AUTH_SOCK` points to.

### Ansible Headless Failures

When Ansible runs from a terminal where `SSH_AUTH_SOCK=~/.1password/agent.sock`:
- If 1Password is locked (screen saver triggered, lid closed), the agent socket still exists but returns `Connection refused` on key listing.
- Ansible fails with a generic `Permission denied (publickey)` — the error does not indicate the agent is locked, leading to confusion.

**Mitigations**:
- For Ansible automation, **always use `ansible_ssh_private_key_file`** pointing to the plain ed25519 key, bypassing the agent entirely.
- In `~/.ssh/config`, structure the bastion Host block to try the agent first (for interactive use) and fall back to the key file: use multiple `IdentityFile` entries in order.
- Ensure `SSH_AUTH_SOCK` is set in the shell environment where Ansible runs. The path is not automatically exported to subprocesses by all shell configurations.

---

## 6. sshd_config Hardening Gotchas

### AllowUsers vs AllowGroups

- **AllowUsers** matches login name patterns exactly (supports wildcards: `tyler@192.168.*`).
- **AllowGroups** matches the user's **primary or supplementary groups**. This is the correct directive for multi-user scenarios where group membership controls access.
- **Critical gotcha**: If you set `AllowUsers tyler` and later add a new user or rename the account, all other users are implicitly denied — including `root` for emergency access. Always test in a second session before closing the first.
- Both directives can coexist. When both are present, a user must satisfy **both** to be allowed. This is a common lockout cause.
- `AllowUsers` does not accept numeric UIDs; only usernames. Similarly `AllowGroups` does not accept GIDs.

### MaxAuthTries

- Default is 6. Setting it to 3 is recommended for hardened setups.
- **Gotcha with multiple keys**: If a client has 5 keys loaded in the agent, OpenSSH tries each in order. With `MaxAuthTries 3`, the connection is dropped after the third failed attempt — before the correct key is even tried. This manifests as `Too many authentication failures`.
- **Mitigation**: Use `IdentityFile` / `IdentitiesOnly yes` in `~/.ssh/config` to restrict which keys are offered for a given host, so the correct key is tried first (or only).

### LoginGraceTime

- Recommended: `30s`. Default is 120s.
- Setting too short (e.g., 5s) can cause failures on slow connections or when the 1Password agent requires an unlock prompt before signing.

### ClientAliveInterval and Ansible Long-Running Plays

- `ClientAliveInterval 300` with `ClientAliveCountMax 2` means a 10-minute idle timeout. This kills Ansible connections during long-running tasks (apt upgrade, compilation, etc.).
- Ansible by default does not send SSH keepalives from the client side. Long tasks produce no SSH traffic, triggering the idle timer.
- **Recommended server values for a bastion that runs Ansible**:
  ```
  ClientAliveInterval 60
  ClientAliveCountMax 10
  ```
  This gives a 10-minute idle window with frequent keepalives.
- **Recommended Ansible client config** in `ansible.cfg`:
  ```ini
  [ssh_connection]
  ssh_args = -o ServerAliveInterval=30 -o ServerAliveCountMax=10 -o ControlMaster=auto -o ControlPersist=60s
  ```
- **ControlMaster / ControlPersist**: SSH multiplexing via ControlMaster reuses an existing connection for new SSH invocations. This avoids repeated knockd round-trips for each Ansible task. Set `ControlPath ~/.ssh/cm-%r@%h:%p` and `ControlPersist 10m`. **Gotcha**: Stale control sockets (from a previous failed session) cause `Connection refused` on the control socket. The Ansible role should document cleanup: `ssh -O exit bastion` or `find ~/.ssh -name 'cm-*' -delete`.

---

## 7. Home Server NAT / Dynamic IP Issues

### The Core Problem

For a home server (Raspberry Pi, etc.) behind a residential NAT:

1. **The external IP changes**: ISP DHCP leases expire, IP changes. DDNS (DynDNS, Duck DNS, etc.) is the standard mitigation — run a daemon on the Pi that updates the DNS record when IP changes.
2. **Carrier-Grade NAT (CGNAT)**: Many ISPs assign a `100.64.x.x` WAN IP to the customer router, placing it behind the ISP's own NAT. In CGNAT scenarios, **no amount of port forwarding works** because you do not have a public IP. DDNS is also useless. Tailscale is the correct solution for CGNAT.
3. **knockd sees the router's public IP, not the client's machine IP**: When the knock client is on a remote network (e.g., Tyler's laptop at a coffee shop), knockd records the WAN IP of the coffee shop's router as `%IP%`. The firewall rule is opened for that entire coffee shop. This is usually acceptable for single-user personal use but means the "source IP" filtering is for the egress NAT, not the specific device.

### NAT Traversal for knockd Sequences

- The knock sequence itself traverses NAT fine — TCP SYN packets to arbitrary ports are sent outbound and the NAT state table records the translation.
- The firewall rule opened by knockd on the home server allows traffic **from the client's public IP** (the NAT gateway). Inbound connections back through NAT require a port forwarding rule on the home router: forward external port 2222 to the Pi's internal IP port 2222.

### Recommended Architecture Per Target Type

| Target | Scenario | Recommended Approach |
|--------|----------|----------------------|
| VPS (cloud) | Public static IP | knockd or fwknop + ufw; DDNS not needed |
| Home server, public IP | Dynamic DNS reachable | DDNS + port forward + knockd; be aware of CGNAT |
| Home server, CGNAT | No public IP | **Tailscale** as the primary access path; knockd irrelevant inside Tailscale network |

### Tailscale and knockd

If the home server uses Tailscale for reachability (100.x.x.x Tailscale IP), port knocking on the Tailscale interface is redundant — the Tailscale network already requires device authentication. For Tailscale-reachable targets, the Ansible role should skip knockd provisioning or make it opt-in.

The knock-ssh wrapper and SSH config should detect or allow configuration of whether to knock: `KNOCK_ENABLED=false` env var or a per-host flag in the wrapper.

---

## Summary of Cross-Cutting Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| knockd sequence sniffable/replayable | Medium (obscurity only) | Use fwknop for cloud targets |
| Race condition: SSH before rule active | Low (easy to fix) | Retry loop or `sleep 2` in wrapper |
| ufw reload wipes knockd iptables rules | Medium | Use `ufw allow` not `iptables` in knockd commands |
| FIDO2 touch blocks Ansible | High (breaks automation) | Separate key for Ansible; never use sk-keys for playbooks |
| 1Password agent not running headless | High (breaks automation) | Use key file for Ansible; document agent-only for interactive |
| MaxAuthTries too low drops correct key | Medium | Use `IdentitiesOnly yes` per host in SSH config |
| ClientAliveInterval kills long Ansible task | Medium | Tune to 60/10; set ServerAliveInterval client-side |
| CGNAT makes home server unreachable | High (blocks all access) | Tailscale fallback; DDNS only works without CGNAT |
