# UX Design: pi-dotfiles (Fork-Pin-Review Governance)

**Date**: 2026-09-14
**Scope**: No graphical UI. All surfaces are CLI output, log lines, or a hand-edited JSON file, read by a single developer (Tyler). This document condenses each surface to a representative sample plus acceptance criteria, per `requirements.md`'s Observability Requirements (layer/action identification, malformed-input reporting, credential-safe dry-run, failures naming the responsible layer/entry).

No `research/ux.md` exists for this project; this file is written directly from `requirements.md` and `implementation/plan.md`.

---

### Surface: `fork_pin_extension.py fork` (scaffold + `--dry-run`)
**Representative output/sample:**
```
$ uv run fork_pin_extension.py fork gotgenes/pi-packages \
    --id gotgenes-pi-packages --capability "permission-system,subagents" --dry-run

Would fork:      github.com/gotgenes/pi-packages -> github.com/tstapler/pi-packages
Would capture:    fork_commit = <current default-branch HEAD, resolved via gh api>
Would write to:   .config/pi/extensions-manifest.json
  + extensions.gotgenes-pi-packages:
      disposition:    "candidate"
      capability:     "permission-system,subagents"
      upstream_repo:  "github.com/gotgenes/pi-packages"
      fork_repo:      "github.com/tstapler/pi-packages"
      approved_by:    null
      approved_date:  null

No changes made (dry run). Re-run without --dry-run to fork and write the manifest entry.
```
**Acceptance criteria:**
- Running `fork_pin_extension.py fork <repo> --dry-run` shows the planned fork target and the exact manifest diff without calling `gh repo fork` or writing `.config/pi/extensions-manifest.json` — matching Task 1.3.1d.
- The dry-run and real-run output both show `disposition: "candidate"` and `approved_by`/`approved_date` as `null` — never any other disposition value, since no flag on this command can write `"approved"` (Task 1.3.1c's static-inspection test enforces this at the code level; the CLI output must not contradict it by implying an approval flag exists).
- On a real run, the printed `fork_commit` matches the SHA written to the manifest entry — the terminal output and the file are never allowed to diverge (read the mutation back, don't just claim it).
- Re-running `fork` for an `--id` that already has a manifest entry fails with a message naming the existing entry id and its current `disposition`, not a generic "already exists" — so Tyler knows whether it's safe to re-scaffold (e.g. blocked on an existing `approved` entry) without opening the JSON file.
- No dead end: the dry-run's closing line states the next concrete action ("Re-run without --dry-run...").

---

### Surface: `verify_pinned_sources_reviewed()` blocked-sync error
**Representative output/sample:**
```
$ uv run --directory stapler-scripts/llm-sync main.py --target pi

PiConfigError: unreviewed fork source in rendered config:
  git:github.com/tstapler/pi-permission-system@abc1234
No approved extensions-manifest.json entry matches this source at this exact commit.
Next step: run the pi-extension-review checklist (.claude/skills/pi-extension-review/SKILL.md),
then hand-edit .config/pi/extensions-manifest.json to set disposition: "approved".
Sync aborted; no changes were written to settings.json.
```
**Acceptance criteria:**
- A blocked sync's error message names the exact unreviewed source string (e.g. `git:github.com/tstapler/pi-permission-system@abc1234`), not a generic "validation failed" — matching Story 1.2.1's three GWT cases (missing entry, stale/mismatched-commit approval).
- The stale-approval case (approved at a different commit than the one now configured) produces a message that names both the configured commit and the approved commit, so Tyler can tell at a glance whether the fragment or the manifest is out of date.
- The message states explicitly that no file was written (`settings.json` unchanged) — a partial or ambiguous write state is never implied.
- Work-owned and `@tstapler`-scoped sources exempted via `trustedPackageScopes` never appear in this error path, even with an empty manifest — confirming Story 1.2.2's exemption holds in the actual CLI output, not just in unit tests.
- No dead end: the message's last line names the concrete next action — run the review skill, then hand-edit `disposition` to `"approved"` — exactly as Task 1.4.1a's skill documents.

---

### Surface: `llm-sync --prune-stale-pi-packages` and stale-package report lines
**Representative output/sample:**
```
$ uv run --directory stapler-scripts/llm-sync main.py --target pi

stale Pi package: old-extension (not pruned; run with --prune-stale-pi-packages)

$ uv run --directory stapler-scripts/llm-sync main.py --target pi --prune-stale-pi-packages

stale Pi package: old-extension (pruning...)
Pruned: ~/.pi/agent/packages/old-extension
```
**Acceptance criteria:**
- Without the flag, the stale-package report line format is exactly `stale Pi package: <id> (not pruned; run with --prune-stale-pi-packages)`, matching plan.md Story 2.2.2's stated line — a byte-for-byte match so Tyler (or a future agent) can grep the bootstrap log for this line reliably.
- The report always runs (every sync), while deletion only happens with `--prune-stale-pi-packages` — the report and the destructive action are never combined into one implicit behavior, per the Package Ledger's `find_stale`/`prune` split in Story 2.2.1.
- With the flag, each pruned artifact's path is printed after pruning (`Pruned: <path>`) — so a re-read of the mutation, not just a claim, is visible in the terminal.
- A path outside any ledger entry is never mentioned in prune output — the ledger only reports and prunes what it recorded, matching Story 2.2.1's "unmanaged path is untouched" criterion; silence here (no output) is itself the correct behavior.
- The bootstrap pass-through (`llm_sync()` in `bootstrap-pyinfra/deploys/llm_sync.py`) reproduces this exact line unmodified in its own printed output — confirming Task 2.2.2a's "no pyinfra change needed" claim rather than asserting it from the plan alone.

---

### Surface: bootstrap/pyinfra dry-run output (`--pi-dir` / `--dry`)
**Representative output/sample:**
```
$ uv run --directory stapler-scripts/llm-sync main.py --target pi --dry-run --pi-dir /tmp/pi-staging

Syncing pi_config -> pi...
Detected 3/12 modified items.
[yellow]Would write settings.json keys: packages.gotgenes-pi-permission-system, extensions.claude-compat[/yellow]
[yellow]Would delete legacy agent old-agent.md[/yellow]
No changes made to /tmp/pi-staging (dry run).

$ uv run pyinfra -y inventory.py main.py --data pi_install_mode=external --dry
--> Loaded 1 host
[Pi]    Would skip install (pi_install_mode=external; deferring to externally managed Pi)
```
**Acceptance criteria:**
- Every dry-run invocation names the destination it would have written to (`/tmp/pi-staging`, or the real `~/.pi/agent` path when not overridden), so Tyler can visually confirm a staging run never touched the real machine — per requirements' "Dry-run output must show intended changes without exposing credentials or secret values."
- Dry-run output enumerates each changed key/resource individually (e.g. `packages.gotgenes-pi-permission-system`), not just a count — matching the observability requirement that bootstrap output identify "the effective configuration layers, extension/package actions, and whether each item was installed, updated, disabled, skipped, or already converged."
- No credential-shaped value ever appears in dry-run output — this is testable by grepping the printed text for common secret-key patterns (`apikey`, `token`, `auth`) after a run against a fixture containing one; `PiConfigSource._reject_credential_material` should have already errored before any dry-run print occurs.
- `pi_install_mode=external` dry-run output states explicitly that install was skipped and why (deferring to externally managed Pi) — never a silent no-op with no explanation, since a work machine must never look like a failed run when it correctly did nothing.
- The closing line of every dry-run always states plainly that no changes were made and to what path — no dead end, since the human's next action (re-run without `--dry-run`/`--dry` once satisfied) is either implied by convention already established elsewhere in this doc or stated directly.

---

### Surface: manual "approve a manifest entry" hand-edit workflow
**Representative output/sample:**
```jsonc
// .config/pi/extensions-manifest.json — before (scaffolded by fork_pin_extension.py)
{
  "extensions": {
    "gotgenes-pi-packages": {
      "disposition": "candidate",
      "upstream_repo": "github.com/gotgenes/pi-packages",
      "upstream_commit": "e64946b5ce96ca004b753d98932c8b13106dd132",
      "fork_repo": "github.com/tstapler/pi-packages",
      "fork_commit": "e64946b5ce96ca004b753d98932c8b13106dd132",
      "license": "MIT",
      "reviewer": null,
      "review_date": null,
      "notes": "",
      "approved_by": null,
      "approved_date": null
    }
  }
}

// after Tyler's hand-edit (a reviewable git diff, not a tool-written change)
-      "reviewer": null,
-      "review_date": null,
-      "notes": "",
-      "approved_by": null,
-      "approved_date": null
+      "reviewer": "tystapler",
+      "review_date": "2026-09-14",
+      "notes": "Verified fail-closed parser paths; deny/ask defaults confirmed for writes, external paths, credentials, git publication, package installation, destructive commands. Children don't inherit secrets/capabilities. Worktree cleanup confirmed.",
+      "approved_by": "tystapler",
+      "approved_date": "2026-09-14"
+      "disposition": "approved"
```
**Acceptance criteria:**
- `ExtensionManifestSource.load()` rejects an `approved` entry missing `approved_by`/`approved_date` with a `ManifestError` naming the entry id and the missing field(s) — so a partially-completed hand-edit is caught immediately on the next sync, not silently accepted (Story 1.1.2).
- The `notes` field, once approved, records specific review findings (fail-closed parser paths, deny/ask defaults, no-secret-inheritance, worktree cleanup, or per-extension equivalents like scoping/redaction/no-inheritance for the credential provider) — a generic string like `"reviewed, looks fine"` is a process failure this doc flags but cannot mechanically block; the `pi-extension-review` skill (Task 1.4.1a) is the documented control, not code, since content quality of prose is not machine-checkable the way `disposition` state is.
- No tool, script, or automation in this codebase (`fork_pin_extension.py` included) writes the literal string `"approved"` to any `disposition` field — verified structurally by Task 1.3.1c's inspection test, and this workflow's diff is the only sanctioned path to that value.
- The diff is a normal, reviewable git change — `git diff .config/pi/extensions-manifest.json` shows exactly the fields above changed, nothing else in the file touched, so the approval is auditable in `git log`/`git blame` the same way any other code change is.
- No dead end: a `candidate` entry that fails review has a documented disposition to move to (`hold` or `rejected`, per the Domain Glossary) rather than being left in limbo — the entry always states, or the skill states, what to do with a non-approved candidate next.

---

## Summary

- **Surfaces designed**: 5 (`fork_pin_extension.py fork` + `--dry-run`; `verify_pinned_sources_reviewed()` blocked-sync error; `--prune-stale-pi-packages` + stale-package report; bootstrap/pyinfra dry-run output; manual manifest-approval hand-edit workflow).
- **UX acceptance criteria written**: 25 (5 per surface).
