# Stack Research: Cross-Platform Ansible Dotfiles Management

## uv tool install vs pipx for cfgcaddy

### Recommendation: uv tool install
- **uv tool install** is the clear modern choice (2024-2026 consensus). It is 10-100x faster than pipx (Rust vs pure Python), handles Python version management automatically, and adds tools to PATH correctly. `uv tool install cfgcaddy` installs the latest PyPI release into an isolated venv and exposes the binary on PATH at `~/.local/bin`.
- **pipx** remains viable if you need `inject`/`uninject`, `--global`, or migration via `pipx install-all`. For this project, these features are not required.
- **PATH caveat**: The uv installer adds a line to shell rc files but only takes effect in new sessions. In Ansible (non-interactive shell), PATH must be explicitly set. The workaround is to source `$HOME/.local/bin/env` or export `PATH=$HOME/.local/bin:$PATH` before invoking `cfgcaddy`. Use `uv tool update-shell` or manually add `~/.local/bin` to PATH in the Ansible environment vars block.
- The old `bootstrap-dotfiles.sh` used pyenv to install Python just to get pipx to install Ansible — that entire chain is eliminated by using Homebrew (`brew install ansible`) as the entry point and uv for cfgcaddy.

## Homebrew on Linux (Linuxbrew) Prerequisites by Distro

### Installation Path Differences
- **macOS (Apple Silicon)**: `/opt/homebrew`
- **macOS (Intel)**: `/usr/local`
- **Linux (all distros)**: `/home/linuxbrew/.linuxbrew` — chosen to avoid system directories; most precompiled bottles still work.

### Prerequisites
- **Ubuntu/Debian**: `apt install build-essential curl file git`
- **Arch/Manjaro**: `pacman -S base-devel curl file git` (base-devel includes gcc/make equivalent)
- **All Linux**: The installer creates the `/home/linuxbrew` user and sets up the prefix automatically.

### Ansible PATH setup for Linux
```yaml
environment:
  PATH: "/home/linuxbrew/.linuxbrew/bin:{{ ansible_env.PATH }}"
```

### Ansible Community Module
The `community.general.homebrew` module handles macOS. For cross-platform, use `command: brew bundle install` with a path check since the module is macOS-focused.

## Ansible Galaxy Roles for Homebrew

### geerlingguy.mac Collection (current best practice)
- The standalone `geerlingguy.homebrew` role has been **deprecated** and moved to the `geerlingguy.mac` collection.
- Install: `ansible-galaxy collection install geerlingguy.mac`
- Use: `geerlingguy.mac.homebrew` role
- Supports both arm64 (`/opt/homebrew`) and Intel (`/usr/local`) paths automatically.
- Does NOT support Linux — use custom tasks or `MonolithProjects.ansible-homebrew` for Linux.

### Alternative: MonolithProjects/ansible-homebrew
- GitHub: `MonolithProjects/ansible-homebrew`
- Handles both macOS and Linux installation in one role.
- Good candidate for cross-platform single-role approach.

## ansible_os_family Fact Values

| Platform | `ansible_os_family` | `ansible_distribution` |
|---|---|---|
| macOS | `Darwin` | `MacOSX` |
| Ubuntu | `Debian` | `Ubuntu` |
| Debian | `Debian` | `Debian` |
| Arch Linux | `Archlinux` | `Archlinux` |
| Manjaro | `Archlinux` | `Manjaro` |
| WSL2 (Ubuntu-based) | `Debian` | `Ubuntu` |

### WSL2 Detection
WSL2 reports as the underlying Linux distribution — there is no separate `ansible_os_family` for WSL2. Detection requires checking `ansible_kernel` for `microsoft` substring:
```yaml
- name: Detect WSL2
  set_fact:
    is_wsl: "{{ 'microsoft' in ansible_kernel | lower }}"
```

### Recommended when-conditions
```yaml
when: ansible_os_family == "Darwin"          # macOS only
when: ansible_os_family == "Debian"          # Ubuntu/Debian/WSL2
when: ansible_os_family == "Archlinux"       # Arch/Manjaro
when: ansible_os_family != "Darwin"          # Linux (all)
when: is_wsl | default(false)                # WSL2 only (after set_fact)
```

## Sources
- [uv vs pipx comparison (2026)](https://docs.bswen.com/blog/2026-03-05-uvx-vs-pipx/)
- [Homebrew on Linux docs](https://docs.brew.sh/Homebrew-on-Linux)
- [Install Homebrew with Ansible](https://nxzon.com/solving-homebrew-installation-challenges-on-linux-with-ansible-playbooks/)
- [geerlingguy.mac collection](https://github.com/geerlingguy/ansible-collection-mac)
- [Ansible OS Family facts guide](https://computingforgeeks.com/list-of-ansible-os-family-os-distribution-facts/)
