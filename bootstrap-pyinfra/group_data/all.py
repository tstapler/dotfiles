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

# 1Password secret-reference paths for `gh auth login --with-token`, e.g.
# "op://Personal/GitHub/token". Empty by default (no default value in the
# Ansible role either) — override with `--data github_op_token_path=...`.
github_op_token_path = ""
github_personal_op_token_path = ""
