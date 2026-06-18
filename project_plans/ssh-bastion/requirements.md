# Requirements: ssh-bastion

## Problem Statement
Set up a hardened SSH jump server with port knocking, supporting multiple hardware-backed authentication methods (1Password SSH agent, YubiKey, Titan Security Key, ed25519 key file), accessible via a simple client-side wrapper. The server should be manageable via Ansible both directly and as a ProxyJump bastion to internal hosts.

## Goals
- SSH server running on a high non-standard port (e.g. 2222), blocked by default
- Port knocking sequence required to open the port before connecting
- Multiple auth options: 1Password agent, YubiKey (PIV or FIDO2), Titan Security Key, dedicated ed25519 key
- Client-side knock-ssh wrapper script that handles the knock + connect flow
- SSH config.d entry for the bastion host
- Ansible role in public dotfiles (bootstrap/roles/ssh-bastion) to provision the server
- Ansible can reach the server directly and use it as a ProxyJump to reach internal hosts

## Non-Goals
- VPN replacement (this is a bastion/jump host, not a full network tunnel)
- Multi-user setup (single user: tyler)
- Automated key rotation

## Target Users
- Tyler, bootstrapping a personal/work server from dotfiles

## Server Targets
- Ubuntu/Debian VPS (cloud, public IP)
- Home server / Raspberry Pi (may be behind NAT; dynamic DNS or Tailscale for reachability)
- Both scenarios should be supported

## Authentication Methods (all optional, layered)
1. **1Password SSH agent** — `~/.1password/agent.sock` — preferred for interactive sessions
2. **YubiKey** — PIV (PKCS#11 via opensc) or FIDO2 (`sk-ed25519` resident key)
3. **Titan Security Key** — FIDO2 (`sk-ed25519` resident key)
4. **Dedicated ed25519 key** — file on disk, for headless Ansible automation

## Port Knocking
- knockd on server, sequence of 3 TCP ports (configurable)
- Firewall (ufw) blocks SSH port by default; opens for source IP for 30s after correct sequence
- Optional: close sequence to re-block immediately after connect
- `knock` client tool for sending sequence

## Client Components
1. `~/.ssh/config.d/bastion` — SSH Host alias with port, user, agent/key config
2. `~/bin/knock-ssh` — wrapper: knock sequence → sleep → ssh
3. Brewfile entry for `knock`
4. Ansible inventory/group_vars for the bastion host

## Ansible Role (server-side provisioning)
- Install knockd, ufw
- Configure sshd: high port, disable password auth, disable root login
- Configure knockd: knock sequence, firewall open/close commands
- Configure ufw: deny SSH port by default, allow knock ports
- Deploy authorized_keys: ed25519 pubkey + YubiKey/Titan FIDO2 pubkeys
- Support both Ubuntu (apt) and Debian

## Ansible Client Configuration
- Group vars: `ansible_port`, `ansible_user`, `ansible_ssh_private_key_file`
- ProxyJump config for reaching internal hosts through bastion
- Knock wrapper integration: either pre-task knock or custom ssh_executable

## Constraints
- Role must go in public dotfiles (`bootstrap/roles/ssh-bastion/`)
- No secrets committed — IPs, knock sequences, pubkeys via vars/vault
- Must work with existing `~/.ssh/config.d/` include pattern
- knock-ssh wrapper installable via Brewfile

## Success Criteria
- `knock-ssh bastion` opens port and connects in < 3 seconds
- `ansible -i inventory bastion -m ping` succeeds without manual knock (wrapper handles it)
- ProxyJump to internal host works: `ssh -J bastion internal-host`
- YubiKey/Titan FIDO2 key auth works interactively
- 1Password agent auth works interactively
- ed25519 key auth works headlessly (Ansible)
- Fresh server provisioned from scratch with `ansible-playbook -i inventory site.yml --tags ssh-bastion`
- Role is idempotent (safe to re-run)
