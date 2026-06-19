# ~/.shell — Shell Config & Secrets Management

## Directory layout

| File | Tracked | Purpose |
|------|---------|---------|
| `config.sh` | yes | Shared, non-secret shell config (sourced by local.sh) |
| `local.sh` | **no** | Machine-local entry point; injects secrets, sets aliases |
| `secrets.op.sh.tpl` | **no** | Personal 1Password template (`op://Personal/…`) |
| `secrets.fbg.op.sh.tpl` | **no** | FBG work 1Password template (`op://FBG/…`) |
| `setup_fbg_1password.sh` | **no** | One-time migration / new-machine bootstrap for FBG secrets |
| `setup_personal_1password.sh` | **no** | One-time migration for personal secrets |

Files marked **no** are gitignored — they live only on the local machine and in 1Password.

---

## How secrets load at shell startup

`local.sh` is sourced by your shell rc (`.zshrc` / `.bashrc`):

```
local.sh
  └─ op whoami --account my.1password.com   ← confirms active session
       ├─ _inject_secrets secrets.op.sh.tpl      (personal: Anthropic, etc.)
       └─ _inject_secrets secrets.fbg.op.sh.tpl  (FBG: GitHub, Datadog, Slack, …)
```

Each `_inject_secrets` call:
1. Runs `op inject` to expand `{{ op://… }}` references into `export KEY=value` lines
2. Captures exit code separately before `eval` (so a silent empty-output failure is caught)
3. Surfaces stderr as a warning on success or an error on failure

---

## New machine rollout

### Prerequisites
- 1Password CLI (`brew install 1password-cli`)
- 1Password desktop app signed into `my.1password.com` (tystapler@gmail.com)

### Steps

```bash
# 1. Sign in
eval "$(op signin --account my.1password.com)"

# 2. Pull the FBG secrets template from 1Password
~/.shell/setup_fbg_1password.sh --bootstrap

# 3. Pull the personal secrets template (create item first if new machine — see below)
op read "op://Personal/Personal Shell Secrets Template/notesPlain" \
  --account my.1password.com > ~/.shell/secrets.op.sh.tpl

# 4. Load secrets into current shell
source ~/.shell/local.sh

# 5. Verify GITHUB_TOKEN is set
echo $GITHUB_TOKEN
```

### If "Personal Shell Secrets Template" doesn't exist yet (first-time setup)

```bash
op item create \
  --category="Secure Note" \
  --title="Personal Shell Secrets Template" \
  --vault="Personal" \
  --account=my.1password.com \
  "notesPlain=$(cat ~/.shell/secrets.op.sh.tpl)"
```

---

## Updating templates

### Edit locally then push to 1Password

```bash
# FBG template
op item edit "FBG Shell Secrets Template" \
  --vault FBG --account my.1password.com \
  "notesPlain=$(cat ~/.shell/secrets.fbg.op.sh.tpl)"

# Personal template
op item edit "Personal Shell Secrets Template" \
  --vault Personal --account my.1password.com \
  "notesPlain=$(cat ~/.shell/secrets.op.sh.tpl)"
```

### Pull from 1Password (overwrite local)

```bash
# FBG
~/.shell/setup_fbg_1password.sh --bootstrap

# Personal
op read "op://Personal/Personal Shell Secrets Template/notesPlain" \
  --account my.1password.com > ~/.shell/secrets.op.sh.tpl
```

---

## Remaining rollout work

- [ ] Create "Personal Shell Secrets Template" secure note in 1Password Personal vault
      (run the `op item create` command above on a machine that already has secrets loaded)
- [ ] Run `setup_fbg_1password.sh` (without `--bootstrap`) on the source machine to store
      the FBG template in 1Password — required before `--bootstrap` works on new machines
- [ ] Restart hivemind instance after sourcing secrets so `GITHUB_TOKEN` is in its env
      (`./scripts/stop-instance.sh && source ~/.shell/local.sh && ./scripts/new-instance.sh`)
- [ ] Verify GitHub repo picker works in hivemind Settings page once token is present
