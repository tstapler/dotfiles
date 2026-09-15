# ADR-002: Credential Provider Approach

**Date**: 2026-09-14
**Status**: Accepted

## Context

`requirements.md` is explicit: dotfiles must never contain, copy, or
provision API keys, OAuth sessions, work credentials, `auth.json`, or other
credential material; credentials may only be obtained at runtime through
explicitly approved extensions integrating with a secure desktop/OS credential
store. `full-featured-profile-research.md` surveys the candidate space and
identifies `jmcombs/pi-extensions`' `@jmcombs/pi-1password` package
(review anchor `733bb02439ed1f633909a7142bbbefb412245f81`, MIT) as the closest
match: it stores `!op read ...` *references* — not resolved secrets — in
mutable `~/.pi/agent/auth.json`, resolves them in the host process through
1Password, and injects values into child command environments while logging
only names. The same research flags the major risk plainly: resolved values
are injected into every allowed bash child, so any allowed command, build
script, or repository hook can read them.

Separately, `PiConfigSource` (`stapler-scripts/llm-sync/src/sources/pi_config.py`)
already rejects credential-shaped keys (`_reject_credential_material`)
anywhere in the tracked config tree — that guarantee exists today and needs no
new code, only a regression test proving it still holds once this extension is
wired in.

## Decision

1. Fork and pin `jmcombs/pi-extensions` under ADR-001's manifest/gate process
   (capability `credential-provider`), disabled by default.
2. Wire it as an opt-in `packages` entry in
   `.config/pi/config.d/90-credential-1password.json` with `enabled: false` —
   activation is a machine-local override the user makes deliberately, never
   a tracked default.
3. Treat the extension as an **Adapter** (GoF) around Pi's existing
   `packages`/`extensions` registry mechanism, not as a bespoke Tyler-owned
   credential system. Dotfiles never generate, copy, or touch
   `~/.pi/agent/auth.json`; setup of the actual `!op read ...` reference
   remains an explicit local action the user performs outside any tracked
   config.
4. Require the manifest entry's review `notes` to record, specifically: vault
   item least-privilege scoping, per-tool/per-project scoping, output
   redaction, and confirmation that resolved values are not inherited into
   subagents or background tasks by default — per the research doc's
   "Required review" list. A generic sign-off does not satisfy the gate.
5. Rely on the existing permission system (Phase 3, `gotgenes/pi-packages`)
   as the actual boundary controlling which commands may run at all, since the
   credential extension's own scoping is necessary but not sufficient — any
   allowed command still sees the injected environment.

## Alternatives Considered

1. **Build a custom Tyler-owned credential extension from scratch.** Rejected:
   this re-solves native-keyring integration and OAuth-adjacent risk that
   `pi-1password`'s fork review already scopes; the research doc found no
   gap `pi-1password` leaves unaddressed for the desktop-store model
   specifically requested.
2. **`liamvinberg/pi-secrets`** as the primary mechanism. Rejected per the
   research doc: it documents its own model as cooperative rather than
   adversarial, and explicitly states transformations can bypass redaction —
   unsuitable as a universal default. It remains a candidate ephemeral
   masked-input fallback only, out of this ADR's scope.
3. **Rely on Pi's native provider credential command resolution** for model
   API keys instead of a general secret-environment extension. Not rejected —
   the research doc notes this may be preferable specifically for model API
   keys (narrower exposure: one credential for one provider, not a general
   environment). Out of scope for this ADR; tracked as a possible narrower
   alternative for model-key resolution specifically, to revisit once
   `pi-1password` is reviewed and its actual blast radius is better
   understood in practice.

## Consequences

- No credential material is ever committed, matching `PiConfigSource`'s
  existing enforcement — this ADR adds no new enforcement code, only a
  regression test (Task 4.1.1e) proving the guarantee holds with this
  extension present.
- The credential provider stays off by default on every machine until a human
  explicitly enables it locally, and stays off entirely on work machines
  unless a work overlay separately approves it (per the research doc's
  session-search precedent for similar work/personal-boundary concerns).
- The real security boundary against credential misuse by an allowed command
  is the permission system (Phase 3), not this extension alone — this ADR
  does not claim `pi-1password` is sufficient in isolation.
