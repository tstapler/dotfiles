# ADR-008: Remediation of already-uploaded items behind a strategy interface

**Status**: Accepted; capability spike pending (Story 9.1) · **Plan**: Stories 9.1-9.8

## Context
- Library API since 2025-04-01 lists/reads only app-created items; `mediaItems.patch` edits `description` only; no date edit or delete via the official API (VERIFIED: https://developers.google.com/photos/library/reference/rest/v1/mediaItems/patch, https://developers.google.com/photos/library/reference/rest, via `research/stack.md` s7).
- rclone item dates come from EXIF else upload time and cannot be changed (https://rclone.org/googlephotos/). rclone's shared `client_id` is "being retired in 2026".
- Google dedups identical bytes, so re-uploading unchanged bytes will not fix a date; changed bytes create a new item (INFERRED, UNVERIFIED in official docs).
- 7,757 files in 604 albums are already uploaded, some possibly misdated.

## Decision
`RemediationStrategy` Protocol (`name`, `capability`, `plan(flagged) -> RemediationWorklist`, `apply()` only where an API exists). Shipped strategies:
- **WebUiWorklist**: per-album checklist for "Edit date & time" on small batches; done-state in `decisions.jsonl`, verified by the next audit.
- **TrashReupload**: journaled EXIF correction locally, CSV of remote items to trash (owner action in the web UI), gated re-upload as `generation=2`, audit to verify. Never deletes remotely.
- **UnofficialToolkit** (opt-in, labeled): prepares input for https://github.com/xob0t/Google-Photos-Toolkit (undocumented web API; can list/trash/add-to-album; README does not mention date edits). Requires `--i-accept-unofficial-risk`; never executed by this tool; no date-edit claim. Breakage and ToS risk.
- **gpmc** (https://pypi.org/project/gpmc/, reverse-engineered mobile API uploader): spike only (Story 9.8); whether it edits dates is UNVERIFIED; not integrated.

Gates (amended 2026-10-16): `upload` requires `AuditClear(album)` (Story 9.2) and a re-upload (`generation>=2`) additionally requires an audit showing zero surviving remote copies, not just the owner marking the album `trashed` (Story 9.6). The audit also classifies remote dates that match the legacy placeholder signature (Jan 1, `12:00:00 + 5 s x k`), because the 604 uploaded albums were uploaded from placeholder-carrying files and their remote dates sit in the past, invisible to an "upload window" check alone (Story 9.3, 9.9).

Audit sources, in order of coverage: rclone `lsjson`/`lsl` (rclone-created items; worked on one album on 2026-10-16), Takeout parse (everything, slow), Picker API (interactive, spike). Every audit states its coverage.

## Spike outcome
*(To fill in Story 9.1: rclone ModTime vs EXIF on 5 files; own-client `mediaItems.list` visibility; result of a `creationTime` patch attempt; whether the `gphotos:` remote uses the shared client_id; where an upload with no EXIF date lands on the timeline (decides whether ADR-007 rule 3 is needed); whether re-uploading to the same album name after a trash reuses or duplicates the album, and whether unchanged bytes re-appear as a new item (backs Strategy TrashReupload, currently INFERRED); if rclone ModTime is not the EXIF date, the audit falls back to Takeout (Story 9.4). Open question: whether scope `photoslibrary.edit.appcreateddata` allows date edits; the reference suggests no.)*

## Alternatives rejected
Building around an assumed date-edit API (none documented); depending on the unofficial toolkit as the main path (fragile, ToS risk).
