# ADR-001: Port Knocking Tool Selection — knockd vs fwknop

## Status

Accepted

## Context

The ssh-bastion role requires a port knocking mechanism to hide SSH from automated scanners. Two viable options were evaluated:

**knockd** sends an unencrypted TCP SYN sequence. The sequence is transmitted in plaintext headers with no authentication or encryption. Any observer on the network path (e.g., same datacenter segment, compromised router, tcpdump on a shared LAN) can capture the full sequence and replay it indefinitely. There is no timestamp validation and no replay protection built in. knockd is well-packaged on Debian/Ubuntu (apt install knockd, version 0.8), simple to configure, and has an Ansible-friendly configuration file format.

**fwknop** (Single Packet Authorization) sends one HMAC-authenticated, AES-encrypted UDP packet containing the desired port, client IP, a timestamp, and a random nonce. The server validates HMAC integrity, checks the timestamp against a configurable replay window, and stores SHA-256 digests of accepted packets to reject reuse. A captured fwknop packet cannot be replayed after the timestamp window expires (~2 minutes). fwknop is also packaged on Debian/Ubuntu (apt install fwknop-server fwknop-client) and has macOS client support via Homebrew. It requires NTP-synchronized clocks — drift beyond ~2 minutes causes all SPA packets to be rejected as expired.

The Ansible role must support two distinct target scenarios:

1. **VPS / cloud server**: Public IP on a shared datacenter network. Other tenants on the same physical segment can observe traffic. The attack surface includes motivated actors who could sniff the knock sequence.
2. **Home server**: Typically behind residential NAT. Primary threat is automated internet scanners (bots), not targeted network-level attackers. However, CGNAT (Carrier-Grade NAT, 100.64.x.x WAN addresses) is common among residential ISPs — in CGNAT environments no public IP is available, port forwarding does not work, and port knocking is irrelevant because external reachability does not exist. For CGNAT home servers, Tailscale is the correct access layer; knockd is not applicable.

## Decision

The Ansible role will support both tools, with **fwknop as the default for cloud/VPS targets** and **knockd as an opt-in alternative for home servers with a public IP**.

Specifically:

- A role variable (e.g., `bastion_port_knock_tool: fwknop`) controls which tool is installed and configured.
- The default value is `fwknop`.
- `knockd` is available as `bastion_port_knock_tool: knockd` for home-server scenarios where the operator has assessed the threat model as bot-only and accepts the lack of replay protection.
- For home servers detected or configured as Tailscale-primary (`bastion_access_method: tailscale`), port knocking is skipped entirely — the role sets `bastion_port_knock_tool: none`.

The rationale for fwknop as default:

- knockd's replay vulnerability is not theoretical — any packet capture tool on a shared network segment exposes the full knock sequence permanently.
- For a VPS where the operator does not control physical or hypervisor-level network isolation, treating the network as untrusted is the correct assumption.
- The additional operational complexity of fwknop (NTP dependency, `~/.fwknoprc` client configuration) is manageable and documented in the role.
- knockd remains appropriate where the threat model genuinely does not include network-level observers (private LAN, home server behind ISP NAT from a trusted location), but given CGNAT prevalence this scenario is increasingly narrow.

## Consequences

**Positive:**
- Cloud deployments gain replay-resistant port authorization with no changes to the role interface — the default is secure.
- Home server operators with a public IP can opt into the simpler knockd path by setting one variable.
- The role explicitly encodes the Tailscale bypass, preventing unnecessary knockd provisioning on CGNAT home servers where it would not function.

**Negative / Tradeoffs:**
- fwknop requires NTP synchronization (`systemd-timesyncd` or `chrony`) on the server. The role must ensure time sync is active before fwknop is configured; a clock drift failure produces cryptic "packet rejected" errors.
- The macOS fwknop client (`brew install fwknop`) and its `~/.fwknoprc` configuration file add client-side setup steps compared to the single `knock` binary.
- knockd's `knock-ssh` wrapper pattern (retry loop with exponential backoff after the knock sequence) does not apply to fwknop — the wrapper must branch on which tool is active.
- The knock-ssh client wrapper and documentation must cover both code paths, increasing maintenance surface slightly.

**NTP dependency mitigation:** The role will include a pre-task that verifies `systemd-timesyncd` or `chrony` is running and will fail with an explicit error message if neither is active, rather than allowing fwknop to silently reject all packets.
