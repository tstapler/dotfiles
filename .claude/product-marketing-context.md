# Product Marketing Context
Type: open-source
Last updated: 2026-06-18

## Project Overview
One-liner: Port knocking without the C daemon — a Rust-native knockd replacement with zero libpcap dependency.
escutcheon ships two binaries: `knock-ssh`, a transparent SSH wrapper that fires a knock sequence before connecting, and `knock-sshd`, a server daemon that listens for sequences via raw sockets and opens your firewall. Together they replace knockd with a self-contained binary deployable via an Ansible role.
Category: security tooling, SSH hardening, network access control
Type: CLI tool + daemon (dual-binary crate)
License: MIT (planned)

## Audience
Primary users: Sysadmins and self-hosters who run SSH-exposed servers and want stealth access control without managing a C daemon with libpcap.
Secondary users: Ansible users who want transparent knock integration — knock-ssh becomes `ansible_ssh_executable`.
Contributors: Rust developers interested in low-level networking (pnet, raw sockets), security tooling, or Ansible Ansible role contributors.
Not: Enterprise IT shops (no LDAP/SSO integration); users needing cryptographic authentication (use fwknop/letmein instead).

## Problem & Differentiation
Core problem: knockd works but requires libpcap headers to build, isn't in all distro repos, and has no native macOS support. Configuring it correctly for UFW vs iptables vs pf is undocumented and error-prone.
Alternatives fall short because: knockd needs libpcap + root (not setcap-friendly); fwknop is heavy (cryptographic auth, PKI setup); letmein is similar but not Ansible-integrated; knock-rs (TimothyYe) has no server firewall integration or Ansible role.
Core philosophy: One binary, no C deps, one `setcap` call. Ansible delivers, ansible uses it transparently.
Word-of-mouth pitch: "It's knockd but you install it with one Ansible task and it works on Ubuntu, Fedora, and macOS."

## Brand Voice
Personality: pragmatic, precise, no-nonsense, slightly opinionated
Technical depth: intermediate (assumes SSH fluency; explains port knocking concepts briefly)
Writing style: terse + precise — docs read like man pages, not tutorials
Use: "sequence", "daemon", "raw socket", "firewall backend", "knock"
Avoid: "magic", "seamless", "enterprise-grade", "cloud-native", marketing superlatives
Voice example: "knock-ssh wraps ssh. It sends the configured sequence, waits for the TTL window, then execs the real ssh binary — no subprocess, no TTY issues."

## Visual Direction
Color mood: dark + technical (terminal-first project, no web UI)
Colors: undefined — no website planned initially
Typography: monospace-forward — README code blocks are the primary "UI"
Aesthetic: like ripgrep docs, like starship README — dense, functional, example-heavy
Logo: wordmark or combination mark; lowercase `escutcheon` or a stylized keyhole plate icon

## Adoption Goals
Primary metric: GitHub stars + Ansible Galaxy downloads
Discovery path: GitHub port-knocking topic tag; "knockd replacement rust" search; Ansible role discovery via Galaxy
Trust signals: Working Ansible role with CI, cross-compiled release binaries on GitHub releases (linux/x86_64, linux/aarch64, macos/arm64, macos/x86_64), no libpcap/C deps in `cargo tree`
Adoption barrier: "Why not just use knockd?" — answer is: no libpcap, macOS support, Ansible-native
"Aha" moment: User adds `knock-ssh` as `ansible_ssh_executable` and their existing playbooks just work against a knock-protected server.

## Key Messages
Headline: Port knocking for Ansible users. No libpcap. No C daemon.
Supporting:
- Drops in as your SSH binary — Ansible doesn't know it's there
- Multi-firewall backend: ufw, firewalld, pf, iptables, nftables
- Ships with an Ansible role that installs and configures everything
CTA: `brew install escutcheon` / `ansible-galaxy install tstapler.ssh-bastion` / star the repo

## GitHub Presence
README purpose: quick start first, then reference — goal is 5-minute working setup
Social proof: Ansible role, release binaries, cross-platform CI badge
Contribution posture: core team-driven initially; PRs welcome for new firewall backends
Topics/tags: port-knocking, ssh, security, ansible, rust, networking, firewall, daemon

## Name Candidates (vetted)
name_candidates_vetted:
  - name: escutcheon
    status: CLEAR
    notes: No developer tool found. Architectural term for the decorative plate framing a keyhole — exact metaphor for port knocking access control. CHOSEN.
  - name: knockrs
    status: CLEAR
    notes: No crate on crates.io, no active GitHub repo. Clean namespace. Runner-up.
  - name: crenel
    status: CLEAR
    notes: No conflicts. Short, unusual. Gap-in-battlements metaphor.
  - name: mullion
    status: CLEAR
    notes: No conflicts. Weak access-control metaphor.
  - name: jamb
    status: CLEAR
    notes: No conflicts. Sounds like "jam"; weak metaphor.
  - name: knock-rs
    status: CONFLICTED
    notes: TimothyYe/knock-rs — active Rust port-knocking tool using pnet, same space. Avoid.
  - name: barbican
    status: CONFLICTED
    notes: OpenStack Barbican — major secrets management service, directly adjacent.
  - name: portcullis
    status: CONFLICTED
    notes: Multiple active GitHub projects including security CLI.
  - name: hasp
    status: CONFLICTED
    notes: gethasp/hasp — active CLI secret broker for coding agents.
  - name: lintel
    status: CONFLICTED
    notes: lintel-rs/lintel — Rust JSON Schema linter, same language/naming pattern.
  - name: embrasure
    status: CONFLICTED
    notes: embrasure-secrets/embrasure — active secrets management tool.
  - name: threshold
    status: CONFLICTED
    notes: Multiple active projects (crypto, network monitor).
  - name: wicket
    status: CONFLICTED
    notes: Apache Wicket Java framework.
  - name: ingress
    status: CONFLICTED
    notes: Kubernetes Ingress Controller — ubiquitous k8s concept.

Chosen name: **escutcheon** (repo/crate) with user-facing binaries `knock-ssh` and `knock-sshd`
