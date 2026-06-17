# Stack Research: SSH Bastion

## 1. knockd vs Alternatives

### knockd (jvinet/knock)
- **Current version**: 0.8, released April 24, 2021. Last upstream commit ~2021. 24 open issues, 10 open PRs — upstream is effectively dormant.
- **Ubuntu/Debian packaging**: Available as `knockd` in Debian/Ubuntu (`apt install knockd`). Debian package 0.8-2 is actively maintained by Leo Antunes. Latest Ubuntu package is 0.8-2build3, updated December 2025 (Graham Inggs). Well-packaged despite dormant upstream.
- **Tradeoffs**: Very simple to configure. No authentication or encryption — anyone who captures the knock sequence can replay it. No replay protection. Low complexity, low overhead, works well for personal/home use where the sequence is the secret.
- **Verdict for this project**: Appropriate. The requirements explicitly call for knockd, the threat model is personal use, and the packaging is solid on Ubuntu/Debian.

### fwknop (Single Packet Authorization)
- **What it is**: Sends a single encrypted, HMAC-authenticated UDP packet instead of a sequence. Provides replay protection via timestamp; even if captured, the packet cannot be reused.
- **Maintenance**: Actively maintained at github.com/mrash/fwknop. Multi-platform clients (Linux, macOS via `brew install fwknop`, Windows, Android, iOS).
- **Tradeoffs vs knockd**: Significantly more secure (crypto + replay protection). Requires NTP sync between client and server (timestamp validation). Slightly more complex setup. The `~/.fwknoprc` config file stores keys.
- **Ubuntu/Debian packaging**: `apt install fwknop-server fwknop-client`.
- **Verdict**: Better security for internet-facing production servers. Worth noting as an upgrade path.

### iptables-only (no daemon)
- Possible using the `recent` module in iptables rules directly. Very complex ruleset, hard to maintain, no Ansible-friendly abstraction.
- **Verdict**: Not recommended for this project.

### Recommendation
Use **knockd** as the requirements specify. It is Ansible-friendly, well-packaged, and sufficient for a personal bastion. Document fwknop as a future upgrade option.

---

## 2. SSH Hardware Key Auth Options

### Option A: YubiKey FIDO2 (`sk-ed25519` or `sk-ecdsa-sk` resident keys)
- **Requirements**: OpenSSH 8.2+ on client, OpenSSH 8.2+ on server. No server-side plugins needed — standard `PubkeyAuthentication yes` is sufficient. Public key is just added to `~/.ssh/authorized_keys` like any other key.
- **Key generation**: `ssh-keygen -t ed25519-sk -O resident -O verify-required`
  - `-O resident`: Key stored on YubiKey itself; portable across machines via `ssh-keygen -K`
  - `-O verify-required`: Requires PIN on each use (OpenSSH 8.3+)
  - `ed25519-sk` requires YubiKey firmware 5.2.3+; fall back to `ecdsa-sk` for older firmware
- **Titan Security Key FIDO2**: Works identically to YubiKey FIDO2 for `ecdsa-sk`. May not support `ed25519-sk` (depends on firmware). Does not support resident keys on all models. Works with `ssh-keygen -t ecdsa-sk`.
- **Pros**: Simple, no server-side config beyond authorized_keys. Physical touch required per operation. No PKCS#11 middleware.

### Option B: YubiKey PIV (PKCS#11 via opensc-pkcs11)
- **Requirements**: `opensc` package on client; `pkcs11-provider` or manual `-I /usr/lib/x86_64-linux-gnu/opensc-pkcs11.so` in SSH config.
- **Server-side**: Standard `authorized_keys` with the PIV-derived public key.
- **Complexity**: Requires opensc installed and configured on each client machine. More moving parts than FIDO2.
- **Verdict**: More complex than FIDO2 for SSH use. FIDO2 is preferred for new setups.

### Recommendation
Use **FIDO2 (`sk-ed25519` or `sk-ecdsa-sk`)** for YubiKey and Titan. No server-side changes beyond `authorized_keys`. Requires OpenSSH 8.2+ (Ubuntu 20.04+ ships 8.2, Ubuntu 22.04 ships 8.9 — both fine).

**Server-side sshd_config additions needed**: None beyond standard pubkey auth. Optionally add:
```
PubkeyAuthOptions verify-required
```
to require user-verification (PIN) for sk keys, but this is optional if keys were generated with `-O verify-required`.

---

## 3. 1Password SSH Agent Integration

### macOS Socket Path
The canonical socket path is:
```
~/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock
```

The recommended symlink (created manually once):
```bash
mkdir -p ~/.1password && ln -s ~/Library/Group\ Containers/2BUA8C4S2C.com.1password/t/agent.sock ~/.1password/agent.sock
```

The `~/.ssh/config` entry:
```
Host *
  IdentityAgent "~/.1password/agent.sock"
```

Or per-host:
```
Host bastion
  IdentityAgent "~/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"
```

### Server-side setup required
**None.** 1Password SSH agent presents keys as standard SSH pubkeys. The server only needs the public key in `~/.ssh/authorized_keys`. No special server configuration.

### Key format
1Password supports Ed25519 and RSA SSH keys. Keys must be stored as `SSH Key` item type in Personal/Private/Employee vault (or a custom vault configured in `~/.config/1Password/ssh/agent.toml`).

### Important gotcha: six-key limit
OpenSSH servers by default limit authentication attempts. If 1Password presents more than 6 keys, connections may fail with "Too many authentication failures." Mitigate by using `IdentitiesOnly yes` and specifying the exact key per host.

---

## 4. knockd Configuration Details

### Configuration file: `/etc/knockd.conf`

**Key directives:**

```ini
[options]
  UseSyslog
  logfile = /var/log/knockd.log

[openSSH]
  sequence    = 7000,8000,9000          # comma-separated ports
  seq_timeout = 10                       # seconds to complete sequence
  tcpflags    = syn                      # TCP SYN only (standard port-knock)
  start_command = ufw allow from %IP% to any port 2222
  cmd_timeout = 30                       # seconds rule stays open
  stop_command  = ufw delete allow from %IP% to any port 2222

[closeSSH]
  sequence    = 9000,8000,7000
  seq_timeout = 10
  tcpflags    = syn
  command     = ufw delete allow from %IP% to any port 2222
```

**TCP vs UDP**: TCP (`tcpflags = syn`) is the standard and simplest. UDP knocks also work but are less reliable through some NAT devices. Stick with TCP for this project.

**`%IP%`**: Substituted with the source IP of the knock — enables per-IP firewall rules, so only the knocking host gets access.

**`seq_timeout`**: Time window to complete the full sequence. 5–15 seconds is typical.

**`cmd_timeout` + `stop_command`**: The `cmd_timeout` fires `stop_command` N seconds after `start_command`, automatically re-blocking the port. This is the "auto-close" mechanism. Alternatively, a separate `closeSSH` stanza with a reverse sequence provides explicit close.

**Interface**: Must configure `KNOCKD_OPTS="-i eth0"` in `/etc/default/knockd` to specify which interface to listen on, and set `START_KNOCKD=1`.

---

## 5. ufw vs iptables for the Firewall Layer

### ufw with knockd — the historical problem (FIXED)
Ubuntu Bug [#1823051](https://bugs.launchpad.net/bugs/1823051) documented that knockd's systemd service used `ProtectSystem=full`, which made `/etc/ufw/` read-only, causing `ufw allow` commands called by knockd to fail with `ERROR: '/etc/ufw/user.rules' is not writable`.

**Status: Fixed** in knockd 0.7-1ubuntu2.1 (Ubuntu 19.04+) by changing `ProtectSystem=full` to `ProtectSystem=true`. The fix is in all current Ubuntu/Debian knockd packages (0.8-2+). Current Ubuntu (22.04, 24.04) packages are not affected.

### ufw integration pattern (recommended)
Use `ufw` commands in knockd's `start_command`/`stop_command`:
```ini
start_command = ufw allow from %IP% to any port 2222
stop_command  = ufw delete allow from %IP% to any port 2222
```

### iptables direct pattern (alternative)
```ini
start_command = /sbin/iptables -I INPUT -s %IP% -p tcp --dport 2222 -j ACCEPT
stop_command  = /sbin/iptables -D INPUT -s %IP% -p tcp --dport 2222 -j ACCEPT
```

**Note on Ubuntu 22.04+**: The default `iptables` command routes through `iptables-nft` (nftables backend). Both `ufw` and direct `iptables` calls work with this backend. Do NOT mix native nftables rule management with ufw/iptables-nft rules.

### Recommendation
Use **ufw** as the primary firewall (simpler Ansible management, idiomatic for Ubuntu). Use `ufw` commands in knockd config. Use `iptables -I` (not `-A`) if using direct iptables to ensure the rule is evaluated before the deny-all rule.

**ufw baseline setup for Ansible:**
```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH (knockd will open/close per-IP)'  # REMOVE after knockd configured
ufw enable
```
Then in knockd, use per-IP rules to open/close port 2222 (or whichever port SSH runs on).

---

## 6. knock Client Package

### macOS Homebrew
The `knock` client is available as `brew install knock` (from the `knockd` package which ships both server and client). Confirmed available for:
- macOS Apple Silicon: tahoe, sequoia, sonoma, ventura, monterey, big sur
- macOS Intel: sonoma, ventura, monterey, big sur, catalina

**Homebrew formula**: `knock` (version 0.8, same as server)
**Install count**: ~810 installs/year (low but present)

### Alternatives if knock is unavailable
1. **nmap** (`brew install nmap`): More widely installed, can knock ports:
   ```bash
   nmap -Pn --host-timeout 100 --max-retries 0 -p PORT HOST
   ```
2. **netcat** (`nc -z HOST PORT`): Even simpler, available by default on macOS.
3. **Custom shell script**: Using `nc` or a bash loop over ports — useful as a fallback in the knock-ssh wrapper.

### Brewfile entry
```ruby
brew "knock"
```

---

## Summary Table

| Component | Choice | Notes |
|-----------|--------|-------|
| Port knocking daemon | `knockd` | Simple, packaged, meets requirements |
| Firewall | `ufw` + knockd `ufw allow from %IP%` | ufw/knockd bug is fixed in current packages |
| YubiKey/Titan auth | FIDO2 `sk-ed25519` / `sk-ecdsa-sk` | Requires OpenSSH 8.2+, no server-side extras |
| 1Password agent | `IdentityAgent "~/.1password/agent.sock"` | Server needs only `authorized_keys` |
| Client knock tool | `brew install knock` | Available for all macOS versions |
| Knock protocol | TCP SYN sequence | More reliable than UDP through NAT |
