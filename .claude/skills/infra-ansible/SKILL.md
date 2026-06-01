---
name: infra-ansible
description: Write, review, or extend Ansible roles and playbooks in the stapler-scripts repo. Use when creating a new role, adding tasks to an existing role, reviewing a playbook for correctness, or applying Ansible best practices. Covers role structure, idempotency, OS portability, variable scoping, and the patterns established in this repo.
---

# Ansible Role Writing

Follow the conventions in `~/dotfiles/stapler-scripts/roles/CLAUDE.md` for all role work in this repo. This skill layers actionable process on top of those conventions.

## Before Writing Anything

1. **Read the existing role** if extending one — check `defaults/`, `vars/`, `handlers/` before adding anything
2. **Check `requirements.yml`** for available collections — don't re-implement what a collection already provides
3. **Check `ansible.cfg`** — `roles_path = roles` means role names resolve relative to `stapler-scripts/`

## Starting a New Role

### Scaffold (only create dirs you'll use)
```bash
mkdir -p stapler-scripts/roles/<name>/{tasks,handlers,defaults}
```

### Companion playbook (one role per playbook)
```yaml
---
- name: <Human-readable description of what this does>
  hosts: localhost
  connection: local
  roles:
    - <name>
```

### defaults/main.yml — start here
Define every value a caller might want to override. Use descriptive names prefixed with the role name:
```yaml
---
<rolename>_domain: example.internal
<rolename>_upstream_dns: 192.168.1.1
<rolename>_wait_seconds: 60
```

## Task Checklist

For every task, verify:

- [ ] Has a `name:` that describes the end state in plain English
- [ ] Uses a structured module (`copy`, `template`, `package`, `systemd`, `lineinfile`) rather than `shell`/`command` where possible
- [ ] Has `become: yes` only on the specific tasks that need root — not at play level
- [ ] If using `command:`/`shell:`: has `changed_when:` and `failed_when:` set explicitly
- [ ] Running the play twice leaves the system identical (idempotent)

## Common Patterns

### Detect a value at runtime and use it later
```yaml
- name: Get Tailscale IPv4 address
  command: tailscale ip --4
  register: _result
  changed_when: false
  failed_when: _result.rc != 0

- name: Set tailscale_ip fact
  set_fact:
    tailscale_ip: "{{ _result.stdout | trim }}"
```

### Deploy a config file (short, inline content)
```yaml
- name: Deploy <service> config
  copy:
    dest: /etc/<service>/config.conf
    mode: '0644'
    owner: root
    group: root
    content: |
      key={{ my_variable }}
  become: yes
  notify: Restart <service>
```

### Deploy a config file (longer or logic-heavy — use a template)
```yaml
# templates/config.conf.j2  ← put the file here
- name: Deploy <service> config
  template:
    src: config.conf.j2
    dest: /etc/<service>/config.conf
    mode: '0644'
  become: yes
  notify: Restart <service>
```

### Ensure a service is enabled and running (after daemon-reload)
```yaml
- name: Flush handlers so daemon-reload runs before start
  meta: flush_handlers

- name: Ensure <service> is enabled and started
  systemd:
    name: <service>
    enabled: yes
    state: started
  become: yes
```

### OS-portable package installation with per-distro names
```yaml
# vars/Archlinux.yml:  myapp_pkg: myapp
# vars/Debian.yml:     myapp_pkg: myapp-bin
# defaults/main.yml:   myapp_pkg: myapp  ← fallback

- name: Install {{ myapp_pkg }}
  package:
    name: "{{ myapp_pkg }}"
    state: present
  become: yes
```

### handlers/main.yml — standard handler shapes
```yaml
---
- name: Reload systemd daemon
  systemd:
    daemon_reload: yes
  become: yes

- name: Restart <service>
  systemd:
    name: <service>
    state: restarted
  become: yes
```

## What NOT to Do

| Anti-pattern | Why | Fix |
|---|---|---|
| `shell: echo value > /etc/file` | Not idempotent, no diff | `copy: content:` |
| `shell: sed -i 's/x/y/' file` | Fragile, runs every time | `lineinfile:` or `replace:` |
| `command: pacman -S foo` | Not portable, not idempotent | `package: name: foo state: present` |
| `become: yes` at play level | Over-privilege | Apply per task |
| No `changed_when:` on `command:` | Reports changed on every run | Always set it |
| Hardcoded IP/path in tasks | Breaks on other nodes | Move to `defaults/main.yml` |
| Handler with logic | Hard to reason about | Handlers restart/reload only |

## Running and Verifying

```bash
# Run the playbook
cd ~/dotfiles/stapler-scripts
ansible-playbook <name>.yaml --ask-become-pass

# Verify idempotency — second run should show 0 changed
ansible-playbook <name>.yaml --ask-become-pass

# Dry run to preview changes
ansible-playbook <name>.yaml --ask-become-pass --check --diff

# Override a variable
ansible-playbook <name>.yaml --ask-become-pass -e myvar=value

# Lint before committing
ansible-lint <name>.yaml
```

## Repo Layout Reference

```
stapler-scripts/
  ansible.cfg              # roles_path = roles
  requirements.yml         # Ansible Galaxy collections
  <name>.yaml              # top-level playbook (one per role)
  roles/
    CLAUDE.md              # conventions reference
    <name>/
      defaults/main.yml    # overridable defaults
      vars/main.yml        # internal constants
      vars/<Distro>.yml    # OS-specific names
      tasks/main.yml       # all tasks
      handlers/main.yml    # event handlers
      templates/           # Jinja2 .j2 files
      files/               # static files
```
