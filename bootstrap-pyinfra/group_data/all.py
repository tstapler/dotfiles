# Static, host-independent config — equivalent to Ansible group_vars.
# Anything that depends on OS/arch (is_wsl, brew_prefix, github_personal_user)
# is NOT here: group_data is plain Python evaluated once at inventory-load
# time, before any host is connected, so it can't call host.get_fact(). Those
# live in common.py instead, computed at deploy time. See its docstring.

dotfiles_dir = "~/dotfiles"

# Opt-in, like Ansible's `-e sudo_mfa_enabled=true`. Override per-run with
# `--data sudo_mfa_enabled=true`.
sudo_mfa_enabled = False

# Opt-in — builds zerobrew from source (slow, Rust compile) on first run.
# Override per-run with `--data zerobrew_enabled=true`.
zerobrew_enabled = False

# Preserve an existing Pi installation (including a work-managed distribution),
# otherwise install this exact public release under ~/.local. Set mode to
# "external" when another machine manager owns installation, or "managed" to
# converge the public install to the pinned version.
pi_install_mode = "auto"
pi_install_version = "0.84.4"

# 1Password secret-reference paths for `gh auth login --with-token`, e.g.
# "op://Personal/GitHub/token". Empty by default (no default value in the
# Ansible role either) — override with `--data github_op_token_path=...`.
github_op_token_path = ""
github_personal_op_token_path = ""

# ssh-bastion-client — opt-in, like the Ansible role's
# `when: bastion_host | length > 0`. Set bastion_op_item to a 1Password
# "vault/item" path (e.g. "Escutcheon/bastion-1") to turn this on; override
# with `--data bastion_op_item=...`.
bastion_op_item = ""
bastion_name = "bastion-1"
bastion_key_path = "~/.ssh/id_ed25519_bastion"
bastion_knock_proto = "tcp"
bastion_knock_ttl_secs = 300

# memory-optimizer — Linux-only, sudo-gated kernel/swap tuning. Defaults
# mirror stapler-scripts/roles/memory-optimizer/defaults/main.yml. On by
# default like the Ansible role (see bootstrap/playbook.yml,
# bootstrap/AGENTS.md) — override with `--data memory_optimizer_enabled=false`.
memory_optimizer_enabled = True
swap_file = "/swapfile"
swap_size_gb = 32
zswap_enabled = True
zswap_compressor = "zstd"
zswap_max_pool_percent = 20
vm_swappiness = 180
vm_watermark_boost_factor = 0
vm_watermark_scale_factor = 125
vm_page_cluster = 0
ksm_pages_to_scan = 4000
mglru_min_ttl_ms = 1000
damon_quota_ms = 500
damon_quota_sz = 134217728  # 128 MB/interval
damon_min_age = 300000000000  # 5 minutes in nanoseconds
