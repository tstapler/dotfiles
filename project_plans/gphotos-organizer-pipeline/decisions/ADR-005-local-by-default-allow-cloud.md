# ADR-005: Analysis is local by default; cloud plugins only behind `--allow-cloud`

**Status**: Accepted (owner decision, 2026-10-16) · **Plan**: Stories 2.3, 6.4, 10.4

## Context
Photos are private family images; face embeddings are biometric-adjacent (requirements: confidential, data residency local). A cloud vision plugin may help on uncertain files but sends images off the machine.

## Decision
- Cloud use is opt-in per run via `--allow-cloud`, expressed as a `CloudPolicy` object that a plugin must receive (sample cap, spend cap, send log). A `requires_cloud` plugin is not imported without it.
- Every send is appended to `DATA/logs/cloud-send.jsonl` (ContentKey, bytes, model, prompt version, time; no image content). Prompts are image-only (no folder name or neighbor dates) to avoid confirmation bias; first answer is cached.
- DB, embeddings, thumbnails, reports live under `~/.local/share/gphotos-organizer/` (700/600), never in the dotfiles tree; reports redact names by default.
- The Claude vision cost estimate ($4-$40) rests on UNVERIFIED pricing; recheck before enabling. Whether to enable it on real data is an owner decision (plan Unresolved Questions).

## Consequences
Default runs make zero network calls except rclone upload. Cloud results carry `cost=cloud` provenance and low weight.

## Alternatives rejected
Global config flag (a plugin could read it ad hoc); always-on cloud (violates the owner's decision).
