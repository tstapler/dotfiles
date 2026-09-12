# Ansible conventions for this bootstrap playbook

Applies to `bootstrap/playbook.yml` and `bootstrap/roles/*`. `CLAUDE.md` in
this directory is a symlink to this file.

## Idempotency style

Prefer letting the module/tool tell you nothing needs doing over re-running
expensive work every play:

- **Native idempotency flags first.** e.g. `apt`'s `cache_valid_time` to skip
  a redundant `apt-get update` instead of forcing `update_cache: true` every
  run.
- **Check-then-act for multi-step installs.** Run the cheap "is this already
  satisfied?" command (e.g. `brew bundle check`) *before* any tap/trust/fetch
  work, and gate that work on its result — not after, where it always runs
  once per play regardless of state.
- **Throttle expensive network calls with an mtime marker**, not a
  first-class Ansible cache: `stat` a marker file under
  `~/.cache/dotfiles/<name>`, compare its mtime to
  `ansible_facts['date_time']['epoch']`, and `touch` it after running. See
  the "Update Homebrew" task in `roles/homebrew/tasks/main.yml` for the
  pattern. This mirrors the repo's own `.cache/*.ok` sentinel idiom in the
  top-level `Makefile`.
- Role-level `when:` in `playbook.yml` (e.g. `memory_optimizer_enabled`) can
  skip an *entire* role — every task inside will show `skipping`. Check the
  role's entry in `playbook.yml` before assuming a task-level bug when a
  whole role skips.

## Facts

Use `ansible_facts['fact_name']` (dict access), never the legacy top-level
`ansible_fact_name` injected var — the latter is deprecated
(`INJECT_FACTS_AS_VARS`) and will be removed in ansible-core 2.24.

## Checks

`make ready` (repo root) runs `ansible-lint` against `bootstrap/playbook.yml`
using this repo's `bootstrap/.ansible-lint` profile — lint against that, not
ansible-lint's default strict profile, which flags FQCN/shell-pipe noise this
repo doesn't enforce.

## Migrating a role to pyinfra

Ansible's `become: yes` has no drop-in pyinfra equivalent in a hand-rolled
shell command — `../bootstrap-pyinfra/README.md`'s "`sudo` only works through
`_sudo=True`" section covers a real bug this bit us with (embedding `sudo` in
a command string times out reading the password even from a real terminal,
every time). Read that section before porting any role with `become: yes`.
