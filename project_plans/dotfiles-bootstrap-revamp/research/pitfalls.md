# Pitfalls Research: Known Failure Modes

## 1. Homebrew on Linux: Path Differences

### The Problem
The existing `bootstrap/roles/homebrew/tasks/main.yml` hardcodes:
```yaml
path: /opt/homebrew/bin/brew
```
This breaks on:
- **Intel Macs**: brew is at `/usr/local/bin/brew`
- **All Linux**: brew is at `/home/linuxbrew/.linuxbrew/bin/brew`

### Correct Cross-Platform Detection
```yaml
- name: Find brew binary
  set_fact:
    brew_path: >-
      {{ '/opt/homebrew/bin/brew'
         if ansible_architecture == 'arm64'
         else '/usr/local/bin/brew'
         if ansible_os_family == 'Darwin'
         else '/home/linuxbrew/.linuxbrew/bin/brew' }}
```

### PATH in Ansible Environment
For all subsequent tasks needing brew on Linux, set:
```yaml
environment:
  PATH: "/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:{{ ansible_env.PATH }}"
```
Without this, `brew` commands in Ansible tasks will fail with "command not found" even after installation because Ansible does not source `~/.bashrc` or `~/.zshrc`.

### Linux Prerequisites Must Run First
Before Homebrew can install on Linux, you need:
- Ubuntu/Debian: `apt-get install -y build-essential curl file git`
- Arch: `pacman -S --noconfirm base-devel curl file git`
These must be installed as a separate pre-homebrew task with `become: true`.

---

## 2. WSL2 Ansible Gotchas

### become/sudo is Broken in WSL2 with sudo 1.9.16+
**Critical bug (2024-2026)**: sudo 1.9.16+ wraps its output in a way that breaks Ansible's become plugin. Ansible's regex to detect the sudo password prompt mismatches because the sentinel is no longer at the start of the line.

**Symptoms**: Ansible tasks with `become: true` hang or time out even with correct passwords.

**Workarounds**:
1. Grant passwordless sudo for the playbook run: add `%sudo ALL=(ALL) NOPASSWD:ALL` to `/etc/sudoers.d/ansible-bootstrap`, run the playbook, then remove it.
2. Avoid `become: true` in the playbook entirely — run as a user that already has sudo without password.
3. Pre-run: `sudo -v` before the playbook (caches credentials for some operations).

**WSL2-specific**: This is most commonly encountered on Ubuntu 26.04 on WSL2 but affects any distro with sudo 1.9.16+.

### systemd is not available by default in WSL2
`become: true` + `service:` module tasks will fail. Services managed via systemd will not start.
- Check: `[[ -d /run/systemd/system ]]` — false in most WSL2 setups unless systemd is explicitly enabled
- WSL2 supports systemd via `/etc/wsl.conf` with `[boot] systemd=true` but requires WSL version 0.67.6+
- **Recommendation**: Use `when: not is_wsl` guards on any `service:` or `systemd:` tasks

### Font Installation in WSL2
Nerd Fonts installed in WSL2's Linux filesystem (`~/.local/share/fonts/`) are NOT visible to Windows terminal applications (Windows Terminal, ConEmu). For fonts to work in WSL2 terminal:
- Fonts must be installed on the **Windows side**: `%USERPROFILE%\AppData\Local\Microsoft\Windows\Fonts`
- Or use Windows-side PowerShell to install the font
- **Recommendation**: Skip font role on WSL2 (`when: not is_wsl`) and document manual Windows-side font installation.

---

## 3. cfgcaddy: PyPI Name vs GitHub Repo

### The Mismatch
- **PyPI package name**: `cfgcaddy` (install with `pip install cfgcaddy` or `uv tool install cfgcaddy`)
- **GitHub submodule**: `dotfiles/cfgcaddy/` — contains the Python source, not a compiled binary
- **Old Ansible role assumption**: Treated `cfgcaddy/` as a Go project and ran `go build`

### Correct Usage
```bash
uv tool install cfgcaddy        # installs from PyPI
cfgcaddy init ~/dotfiles ~      # creates/symlinks ~/.cfgcaddy.yml
cfgcaddy link --no-interactive  # creates all symlinks
```

The submodule at `dotfiles/cfgcaddy/` is the source code. The Ansible role should install from PyPI, NOT from the local submodule (which would require `uv tool install ./cfgcaddy` — a different, dev-mode install). Using PyPI is simpler and correct for bootstrap.

### Version on PyPI
The `pyproject.toml` shows version `0.1.8`. Ensure this version has the `link` and `init` commands. Since cfgcaddy is the user's own project, pin to latest: `uv tool install cfgcaddy`.

---

## 4. asdf Plugin Installation in Ansible

### The Current Bug
```yaml
when: "'.tool-versions' in lookup('fileglob', dotfiles_dir + '/.tool-versions')"
```
`lookup('fileglob', path)` returns a **list of matching file paths** (e.g., `['/home/user/dotfiles/.tool-versions']`). The `in` operator checks if the string `'.tool-versions'` is literally one of those list items — it never is, because the list contains full paths.

**Fix options**:
```yaml
# Option A: Check if file exists
when: ".tool-versions" in (dotfiles_dir + '/.tool-versions')  # WRONG, same problem

# Option B: Use stat (correct)
- stat:
    path: "{{ dotfiles_dir }}/.tool-versions"
  register: tool_versions_file

- command: asdf install
  when: tool_versions_file.stat.exists
  args:
    chdir: "{{ dotfiles_dir }}"

# Option C: Use lookup('file') 
when: lookup('fileglob', dotfiles_dir + '/.tool-versions') | length > 0
```
Option B (stat) is most idiomatic and reliable.

### asdf Plugin Idempotency: command vs shell
`asdf plugin add nodejs` fails with exit code 2 if the plugin is already installed, causing Ansible `command:` tasks to report failed. Solutions:
```yaml
# Use failed_when to ignore "already installed" errors
- name: Add asdf plugin
  command: asdf plugin add {{ item }}
  register: result
  failed_when: result.rc != 0 and 'already added' not in result.stderr
  loop: "{{ asdf_plugins }}"

# Or use shell with || true (less idiomatic)
- shell: asdf plugin add nodejs || true
```

### asdf PATH in Non-Interactive Ansible Shell
`asdf` must be initialized before use. In non-interactive shells, `~/.bashrc` is not sourced. Must explicitly source:
```yaml
- name: Install tool versions
  shell: |
    . {{ ansible_env.HOME }}/.asdf/asdf.sh
    asdf install
  args:
    chdir: "{{ dotfiles_dir }}"
    executable: /bin/bash
```

---

## 5. uv tool install PATH Issues in Non-Interactive Shells

### The Problem
`uv tool install cfgcaddy` succeeds but `cfgcaddy` is not found in subsequent Ansible tasks because:
1. `uv` installs tool binaries to `~/.local/bin/`
2. `uv` adds a line to `~/.bashrc`/`~/.zshrc` to add this to PATH
3. Ansible runs tasks in non-interactive shells that do **not** source `~/.bashrc`

### Fix: Explicit PATH in environment
```yaml
- name: Install cfgcaddy
  command: "{{ ansible_env.HOME }}/.local/bin/uv tool install cfgcaddy"
  # or: command: uv tool install cfgcaddy
  # (if uv itself is on PATH from brew)

- name: Link dotfiles
  command: cfgcaddy link --no-interactive
  environment:
    PATH: "{{ ansible_env.HOME }}/.local/bin:{{ ansible_env.PATH }}"
```

The safest approach: use the full path for the first call to `uv` (since uv is installed via brew and brew bin is already on PATH), then add `~/.local/bin` to environment for all subsequent cfgcaddy calls.

### uv install source
`brew install uv` is the recommended installation for this project since brew is the primary package manager. Do NOT use the uv curl installer in addition to brew — duplicates on PATH will cause confusion.

---

## 6. Private Brewfile Taps on Fresh Machine

### The Problem
The Brewfile contains:
```
tap "fanatics-gaming/tap", "git@github-personal:fanatics-gaming/homebrew-tap"
tap "tstapler/stelekit", "git@github-personal:tstapler/stelekit.git"
```
These use SSH with a custom host alias (`github-personal`) defined in `~/.ssh/config`. On a fresh machine:
- SSH key is not yet added to GitHub
- `~/.ssh/config` does not exist
- `brew bundle install` will fail or hang on these taps

### Recommended Fix
Use `--no-lock` and `--skip-cask` flags for Linux; add a pre-check for SSH key presence. Better: split Brewfile into tiers or use `HOMEBREW_NO_AUTO_UPDATE=1` with `brew bundle --no-lock` and `|| true` for private taps, falling back gracefully.

---

## 7. Brewfile Linux Incompatibility

The existing `Brewfile` contains `cask` entries (macOS GUI apps). Running `brew bundle install --file=Brewfile` on Linux will fail on all cask lines. Need:
- `Brewfile.linux` with CLI tools only, no casks
- Role logic: `brewfile: "{{ 'Brewfile' if ansible_os_family == 'Darwin' else 'Brewfile.linux' }}"`

---

## 8. Submodule SSH vs HTTPS

`.gitmodules` or submodule remotes may use SSH URLs. On a fresh machine before SSH keys are configured, `git submodule update --init --recursive` may fail for private submodules. Use HTTPS for all submodule remotes in `.gitmodules` or configure a conditional rewrite:
```
[url "https://github.com/"]
  insteadOf = git@github.com:
```

## Sources
- [Homebrew on Linux docs](https://docs.brew.sh/Homebrew-on-Linux)
- [Install Homebrew with Ansible on Linux](https://nxzon.com/solving-homebrew-installation-challenges-on-linux-with-ansible-playbooks/)
- [WSL2 ultimate setup 2024](https://dev.to/alia5/the-ultimate-wsl2-setup-4m08)
- [Ansible WSL2 become/sudo issue](https://forum.ansible.com/t/installation-of-ansible-in-wsl2-fails/3240)
- [uv PATH configuration](https://docs.astral.sh/uv/getting-started/installation/)
- [uv tool update-shell docs](https://mintlify.wiki/astral-sh/uv/cli/tool-update-shell)
- [ansible-role-asdf](https://github.com/markosamuli/ansible-asdf)
