# Pi Staged-Rollout & Rollback Runbook

Maps requirements.md's five-step Risk Control staged-adoption list 1:1 to
runnable commands. Covers Epic 5.1 (Story 5.1.1) and Epic 5.2's Story 5.2.1.
Story 5.2.2 (classifying the real machine's existing `settings.json` keys)
is **out of scope for this document as written** — see the note at the end
of Step 2.

All `llm-sync` commands below assume the repo root as the working directory
and are run via `uv run --directory stapler-scripts/llm-sync main.py ...`.
Flag names are verified against `stapler-scripts/llm-sync/src/cli.py`'s
`main()` argparse block as of this writing; re-check that file if a flag
below fails with `unrecognized arguments`.

## Step 1: Dry-run / temp-dir validation

Validate merge and provisioning behavior without touching any real Pi
install.

Config-sync dry run against a scratch directory instead of `~/.pi/agent`:

```sh
uv run --directory stapler-scripts/llm-sync main.py \
  --target pi --dry-run --pi-dir /tmp/pi-staging
```

Pi *installation* dry run (separate concern from config sync — this
exercises `bootstrap-pyinfra/deploys/pi.py`'s install-mode logic without
installing anything, by forcing `external` mode for the run):

```sh
cd bootstrap-pyinfra
uv run pyinfra -y inventory.py main.py --data pi_install_mode=external --dry
```

`--dry` previews pyinfra's queued operations without executing them
(pyinfra's analog to `ansible-playbook --check`); `--data
pi_install_mode=external` overrides `pi_install_version`/`pi_install_mode`
for this run only, per `bootstrap-pyinfra/deploys/pi.py`'s `plan_pi_install`
(`external` mode always returns action `"external"` — "installation is
externally managed" — regardless of what's already on `PATH`).

Both commands are non-destructive: the first writes nothing outside
`/tmp/pi-staging`, and the second's `--dry` withholds all queued pyinfra
operations, including the Pi install itself.

## Step 2: Backup / inventory the current unmanaged Pi configuration

Before any managed sync touches the real machine, back up the current
`settings.json` and record what's currently designated as dotfiles-owned.
This step is the same action as Task 5.2.1a below — see **"Backup before
adopting"** for the exact commands; it isn't duplicated here.

**Scope note (Story 5.2.2, explicitly out of scope for this runbook as
written):** requirements.md's step 2 also implies classifying *which*
existing `settings.json` keys are universal, work-only, or
machine-generated, so a managed sync never silently overwrites an
unclassified key. That classification is plan.md's Story 5.2.2
(Task 5.2.2a), a Tyler-only manual step against his real machine's
`~/.pi/agent/settings.json` — it requires data not available in this
environment and is **not done by this document**. Per plan.md's
Dependency Visualization ("back-edge" note) and Task 3.2.2b's
`Dependencies:` line, Story 5.2.2's classification table must exist
*before* Story 3.2.2's real-machine adoption step (Step 3 below) runs on
the actual machine — backing up and dry-running (this step and Step 1) can
proceed without it, but adopting on the real machine cannot.

## Steps 3-5: Adopt, verify, and roll out

### Step 3: Adopt and verify on the current macOS machine

Once Step 2's backup exists and Story 5.2.2's classification table is
recorded (see the scope note above — this is a precondition, not something
this runbook performs), run the real sync against the real Pi settings
location:

```sh
uv run --directory stapler-scripts/llm-sync main.py --target pi
```

This uses `cli.py`'s defaults: `--pi-dir` defaults to `~/.pi/agent`, and the
managed-key ownership state defaults to
`~/.config/llm-sync/pi-settings-state.json` (see `main()` in `cli.py`,
around the `PiSettingsTarget` construction). Verify by inspecting
`~/.pi/agent/settings.json` and confirming Pi itself starts and loads
config without error.

### Step 4: Verify idempotent re-run and rollback

Re-run the same command from Step 3 a second time with no config changes in
between; `PiSettingsTarget.save()` (`stapler-scripts/llm-sync/src/targets/pi_settings.py`)
diffs desired vs. existing state and reports no change when converged — a
second run should print that settings are already converged rather than
rewriting the file. Then rehearse rollback per **"Rollback"** below (Task
5.2.1b) — do not defer rollback verification to an actual incident; prove it
works while the blast radius is a scratch/staging copy or an easily
re-adoptable real machine.

### Step 5: Roll out to supported Linux families

No separate mechanism: re-run Steps 1, 3, and 4 unchanged on each target
Linux family (`bootstrap-pyinfra`'s deploys are OS-branching internally,
e.g. via `common.is_macos`/`is_wsl`, not via a different entrypoint). This
runbook's commands and the underlying `llm-sync`/`pyinfra` tooling are the
same regardless of platform; only the machine backup taken in Step 2
differs per host.

## Pre-`pi_install_version`-bump smoke-test gate (Task 5.1.1c) — REQUIRED

This gate is **required, not optional**, and applies independently of the
staged-rollout steps above. It must run before any future edit to
`pi_install_version` in `bootstrap-pyinfra/group_data/all.py`:

1. Start `pi` against a temporary `HOME` with every manifest entry currently
   at `disposition: "approved"` in `.config/pi/extensions-manifest.json`
   enabled with its pinned fork/commit.
2. Assert each such extension loads without error.
3. Re-run plan.md's Task 3.3.1c-2 plan-mode/permission-system composition
   integration test as a regression check.

**Forward reference — this test does not exist yet.** As of this plan's
current implementation state, Task 3.3.1c-2's composition integration test
is blocked on Epics 3.2/3.3, which are themselves blocked on Tyler's manual
fork-and-review steps (see plan.md's Unresolved Questions and Dependency
Visualization). Do not treat step 3 above as already satisfied by an
existing test — confirm the test exists and passes at the time of the
version bump, not by reference to this runbook.

Rationale (mirrors the Observability Plan's pre-bump gate line item in
plan.md): a core-Pi version bump can silently break an unchanged,
already-approved extension's runtime behavior — for example, fail-soft
extension loading masking a broken permission gate — which none of the
existing install/update/skip logging surfaces on its own.

## Backup before adopting (Task 5.2.1a)

Before the first managed sync touches the real machine's `settings.json`,
take both a file backup and a record of the `managedKeys` state at that
time:

```sh
cp ~/.pi/agent/settings.json ~/.pi/agent/settings.json.pre-dotfiles-backup
cp ~/.config/llm-sync/pi-settings-state.json \
   ~/.config/llm-sync/pi-settings-state.json.pre-dotfiles-backup
```

The second copy may not exist yet on a machine that has never been synced
(`PiSettingsTarget._read_object` treats a missing state file as `{}`,
i.e. no `managedKeys` yet) — in that case skip it; there's nothing to
back up.

`~/.config/llm-sync/pi-settings-state.json` is `cli.py`'s confirmed default
for `--pi-settings-state-file` (`main()`'s `PiSettingsTarget` construction:
`args.pi_settings_state_file or Path.home() / ".config" / "llm-sync" /
"pi-settings-state.json"`).

## Rollback (Task 5.2.1b)

Manual restore, then re-run without managed mode:

```sh
cp ~/.pi/agent/settings.json.pre-dotfiles-backup ~/.pi/agent/settings.json
cp ~/.config/llm-sync/pi-settings-state.json.pre-dotfiles-backup \
   ~/.config/llm-sync/pi-settings-state.json
```

If the state-file backup didn't exist in the previous step (pre-managed
machine), remove `~/.config/llm-sync/pi-settings-state.json` instead of
restoring it, returning to the "never synced" starting state.

**Scope guarantee, per Story 5.2.1's acceptance criteria:** this rollback
restores exactly the keys that were present in `managedKeys` at backup
time — no more, no less. Reading `PiSettingsTarget.save()`
(`stapler-scripts/llm-sync/src/targets/pi_settings.py`) confirms why this
restore is safe and scoped:

- `PiSettingsTarget` only ever reads and writes two paths: `settings_path`
  (`~/.pi/agent/settings.json`) and `state_path`
  (`~/.config/llm-sync/pi-settings-state.json`, or their overrides). It has
  no code path that touches any other file under `~/.pi/agent/`.
- `auth.json` and session files under `~/.pi/agent/` are therefore **never
  touched by rollback** — they are never `managedKeys`-tracked, and this
  restore procedure only copies the two files above.
- Do not re-run `llm-sync main.py --target pi` immediately after a
  rollback copy without first confirming you want managed mode back — the
  restored state file's `managedKeys` will cause the next real sync to
  resume managing exactly those same keys.

This is the manual equivalent of the (planned, not yet implemented)
automated check `test_rollback_restores_only_managed_keys_and_preserves_auth_and_sessions`
referenced in `project_plans/pi-dotfiles/implementation/validation.md`'s
Migration Note section — that test exercises the same guarantee against a
`tmp_path` fixture with dummy `auth.json`/session files, asserting they are
byte-identical before and after.
