# Ansible Roles — Conventions for this Repo

## Role Structure

Create only the directories you actually use. Minimum viable role:

```
roles/<name>/
  defaults/main.yml   # user-overridable variables (low precedence)
  tasks/main.yml      # all tasks
  handlers/main.yml   # event-driven actions (daemon-reload, restarts)
```

Add when needed:
```
  vars/<DistroName>.yml   # OS-specific package names (loaded via include_vars)
  vars/main.yml           # internal constants (high precedence, not user-facing)
  templates/              # Jinja2 (.j2) files for content with logic
  files/                  # static files deployed with copy:
  meta/main.yml           # role dependencies
```

Companion playbook at `stapler-scripts/<name>.yaml` — one role per playbook is the norm here.

## Variables

- **`defaults/main.yml`** — everything a caller might want to override (IPs, domain names, sizes, paths)
- **`vars/main.yml`** — internal constants the role owns and callers should not change
- **`vars/<Distro>.yml`** — OS-specific package names; load via `include_vars` with `with_first_found`
- Prefix role variables with the role name to avoid collisions in multi-role plays:
  `tailscale_dns_node_ip`, not `ip`
- Prefer `tailscale_ip_result.stdout | trim` over raw stdout to avoid whitespace bugs

## Tasks

### Naming
Every task must have a `name:`. Make it a complete sentence describing the end state:
- `Deploy dnsmasq config for {{ local_domain }}` ✓
- `dnsmasq config` ✗

### Idempotency — required for every task
| Goal | Use | Avoid |
|------|-----|-------|
| Write a file | `copy:` / `template:` | `shell: echo > file` |
| Edit a line | `lineinfile:` / `blockinfile:` | `shell: sed -i` |
| Install a package | `package: state=present` | `command: pacman -S` |
| Run a one-shot command | `command:` + `creates:` or `changed_when:` | bare `shell:` |
| Check something | `command:` + `changed_when: false` | — |

### Privilege escalation
Apply `become: yes` **per task**, not at play level. Only elevate for tasks that genuinely need root.

### Commands and shell
- Use `command:` for single commands; `shell:` only when you need pipes, redirects, or globs
- Always set `changed_when:` and `failed_when:` on `command:`/`shell:` tasks
- Register the result when you need to branch on it or use the output as a fact

```yaml
- name: Get Tailscale IPv4 address
  command: tailscale ip --4
  register: tailscale_ip_result
  changed_when: false
  failed_when: tailscale_ip_result.rc != 0
```

### Ordering with handlers
Handlers run at end-of-play by default. When later tasks in the same play depend on a handler having run (e.g., `systemctl daemon-reload` before `systemctl start`), flush explicitly:

```yaml
- meta: flush_handlers
```

## Handlers

Name handlers as imperative actions:
- `Reload systemd daemon`
- `Restart dnsmasq`
- `Regenerate GRUB config`

A handler should only restart/reload — no logic. Keep them in `handlers/main.yml`.

## OS Portability

Use generic modules where possible:
- `package:` not `apt:` / `pacman:`
- `service:` / `systemd:` for services

For distro-specific names, use the bootstrap role's pattern:
```yaml
- include_vars: "{{ item }}"
  with_first_found:
    - "../vars/{{ ansible_distribution }}.yml"
    - "../vars/{{ ansible_os_family }}.yml"
    - "../vars/default.yml"
```

## Templates vs Copy

- `copy: content: |` — for short configs where variables are simple substitutions and the content lives cleanly inline
- `template: src: foo.j2` — for longer configs, configs with loops/conditionals, or when the file benefits from being read separately
- Put `.j2` files in `templates/`, static files in `files/`

## Secrets

Never hardcode secrets. Use:
- `ansible-vault encrypt_string` for inline vault values
- Environment variables via `lookup('env', 'VAR')`
- Add `no_log: true` to tasks that print sensitive values

## Linting

Run before committing:
```bash
cd stapler-scripts && ansible-lint <playbook>.yaml
```
