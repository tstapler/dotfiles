---
name: kibitzer-sample-review
description: Find real kibitzer PostToolUse hook firings in Claude Code session transcripts and record them as categorized, checkable false-positive/true-positive samples in tstapler/kibitzer's docs/
---

# Kibitzer Sample Review

kibitzer (`github.com/tstapler/kibitzer`, installed via Homebrew as
`tstapler/kibitzer/kibitzer`) is a Rust CLI that runs as a Claude Code `PostToolUse`
hook. Its checks are whole-file (sometimes whole-repo) and not diff-aware — see
`src/check.rs` and `src/hook.rs` in that repo. That one
architectural fact explains most of its surprising firings: any edit, including a
deletion or an edit unrelated to the actual violation, can re-surface a check failure
that already existed, or exists only because a multi-step edit sequence is mid-way
through. This skill is how to find a *specific real occurrence* of that (or any other
kibitzer behavior worth tracking) and file it where the next investigation can find it
without redoing the transcript archaeology from scratch.

## Step 1 — Find real invocations, not text matches

Follow `checking-invocations.md` in `tstapler/kibitzer`'s `docs/` exactly — do not grep
for the word "kibitzer" and treat hits as evidence; that conflates real hook firings
with kibitzer's own source code being edited or discussed. The reliable filter is
`attachment.command == "kibitzer hook"` (or `attachment.blockingError.command` for
blocks) on `hook_success` / `hook_blocking_error` attachment records.

```bash
for f in ~/.claude/projects/*/*.jsonl; do
  success=$(jq -c 'select(.type=="attachment" and .attachment.type=="hook_success")
    | select(.attachment.command=="kibitzer hook")' "$f" 2>/dev/null | wc -l)
  blocked=$(jq -c 'select(.type=="attachment" and .attachment.type=="hook_blocking_error")
    | select(.attachment.blockingError.command=="kibitzer hook")' "$f" 2>/dev/null | wc -l)
  [ "$success" != "0" ] || [ "$blocked" != "0" ] && echo "$f  success=$success blocked=$blocked"
done
```

## Step 2 — Pull the triggering edit for each hit worth reviewing

For a `hook_blocking_error`, get its `toolUseID`/`blockingError.command`'s parent
`Edit`/`Write`/`MultiEdit` tool_use in the same file, and read its actual arguments —
not just the error message:

```bash
jq -r --arg id "$TOOLU_ID" \
  '.message.content[]? | select(.id==$id) | {file: .input.file_path,
    old_len: (.input.old_string|length), new_len: (.input.new_string|length)}' "$f"
```

Note `.name` on that same content block — this tells you which Claude Code tool
matcher actually fired the hook (`Edit`, `MultiEdit`, `Write`). Every real firing found
on this machine so far (2026-08-10) has come from a plain `Edit` — the project
`.claude/settings.json` matchers observed so far are all `"Edit|Write"`, so `MultiEdit`
calls never invoke kibitzer at all, regardless of the shape of their `edits` array. If
you're chasing a report that names a specific tool-argument shape (e.g. "two arguments,
neither a plain string"), check this field first — don't assume `MultiEdit` without
confirming the matcher actually includes it for that project.

Decide: is the flagged violation genuinely present in the *edited* content, or does it
belong to some other part of the file/repo the edit never touched? The `old_len`/
`new_len` comparison is a cheap first signal for "was this a deletion" but is not
sufficient on its own — a net-shrink edit can still *add* the exact substring that
triggers the check (see the design-docs log entry below for a worked example).

## Step 3 — File it under the check it belongs to, not a new one-off doc

Each kibitzer check gets exactly one tracking doc under `docs/<check-name>-false-positives.md`
in `tstapler/kibitzer`. Two exist already:

- `go-primitive-obsession-false-positives.md`
- `markdown-link-integrity-false-positives.md` (covers `doc-structure-report` too,
  since both fire together on the same reference-link-integrity class of problem)

Before writing a new doc, check whether the check name already has one — append a new
`### <date> — <repo> — <short description>` entry under `## Log` instead of duplicating
the `## Root-cause mechanism` section. Only add a new doc file for a check that doesn't
have one yet, and only write `## Root-cause mechanism` once you've actually confirmed it
by reading the relevant kibitzer source (`check.rs`, `hook.rs`, and whatever
`CheckCommand`/external tool the check shells out to) — don't guess at the mechanism
from the error message alone.

Log-entry template (matches the existing docs — keep it):

```markdown
### YYYY-MM-DD — <repo> — <short description>

- **Repo**: `<org>/<repo>`, file: `<path>`
- **Session**: `<transcript path>`, `<toolUseID>`
- **What changed**: what the edit actually did (old_len/new_len, and a one-line
  description of the content change)
- **Why it fired**: which check(s), and what specifically about the file/repo state
  triggered them
- **Mechanism**: confirmed root cause, citing the specific source line(s) or check
  script docstring — not a guess
- **Not a pure deletion** (only if relevant): note when the "it fired on a deletion"
  framing is imprecise — e.g. the edit both removes and adds content in the same hunk
```

## Step 4 — Don't manufacture a category

If Step 2's read shows the check correctly caught a real problem, that's not a
false-positive sample — don't force it into these docs. These docs exist to build an
evidenced list of *when the check is wrong*, so the whole-file/non-diff-aware
architecture question in `check.rs`/`hook.rs` can eventually be fixed with real cases
in hand, not hypotheticals. A true positive is worth noting in conversation but not
worth a permanent log entry here.

## Related

- `tstapler/kibitzer`'s `docs/checking-invocations.md` — the transcript-query recipe
  this skill's Step 1 depends on; read it in full before running the loop above.
- `tstapler/kibitzer`'s `src/check.rs`, `src/hook.rs`, `src/daemon.rs` — the
  non-diff-aware architecture that is the root cause behind nearly every sample filed
  here.
