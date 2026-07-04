---
name: journeys-enrich
description: >
  Improves existing docs/journeys/*.md spec files — fills in gaps flagged by
  journeys-extract, refines vague steps, and links plausible test_ids by
  searching the repo's test suite — without a full rediscovery pass and without
  clobbering fields owned by journeys-verify. Always proposes a before/after diff
  and waits for explicit approval before writing (plan-validate-execute), then
  applies via journeys-extract's upsert script so the verified→stale invariant
  stays enforced in one place. Use when a journey is marked draft or stale and
  needs deepening or test-linking — not for discovering new journeys
  (journeys-extract) or for mechanically checking existing links (journeys-verify).
---

# Journeys: Enrich

Deepen and link existing journey specs incrementally. Unlike `journeys-extract`
(full rediscovery, always overwrites the body from scratch) this skill proposes
targeted improvements to specific journeys and requires approval before writing
anything — it must never silently clobber a hand-edited journey.

## When to Use

- A journey is `status: draft` (usually: no `test_ids` linked yet, or gaps noted)
- A journey is `status: stale` and you want to investigate + fix it, rather than
  just re-run `journeys-extract`
- NOT for finding journeys that don't exist yet (`journeys-extract`) or for
  mechanically re-checking links you already believe are correct (`journeys-verify`)

## Input

```
/journeys:enrich [slug ...]
```

- No args: target every journey with `status: draft` or `status: stale` in
  `docs/journeys/`
- One or more `slug`s: target only those journeys

## Instructions to Claude

### Step 1: Select Targets

List `docs/journeys/*.md` (excluding `README.md`), filter by args or by
`status: draft|stale`. If more than ~3 journeys are targeted, process them with
one lean agent per journey **in parallel** (same context-saving trick as
`journeys-extract`: each agent writes its full proposal to `/tmp/journey-enrich-<slug>.md`
and returns only a small JSON summary). For 1-3 journeys, do it inline.

### Step 2: Propose Per Journey

For each target, read the journey file and its `source_refs` files. Propose:

- **Refined steps**: resolve vagueness, fill gaps listed under "## Gaps / Notes"
  by reading the actual code/UI at `source_refs`
- **Candidate test_ids**: search the repo's test suite (Grep for the journey's
  title/step keywords across test directories) for tests that plausibly already
  cover this flow. Only propose a test_id you found verbatim in an actual test
  file — never invent one. If nothing plausible exists, say so explicitly rather
  than proposing a weak match.
- **Updated trigger/emotion/diagram** if the investigation revealed they were wrong

Each proposal (agent or inline) returns/produces:
```json
{
  "slug": "<journey_id>",
  "before": {"steps": [...], "gaps": [...], "test_ids": [...]},
  "after": {"steps": [...], "gaps": [...], "test_ids": [...], "trigger": "...", "emotion": "...", "diagram": "..."},
  "candidate_test_ids_rejected": ["<match too weak to include, with reason>"]
}
```

### Step 3: Gate — Show the Diff, Wait for Approval

Present each journey's before/after as a compact diff (not the full file) and
ask the user to approve, per-journey or in batch. **Do not write anything before
approval** — this is the one step in the whole journeys family that touches
existing content non-mechanically, so it's the one that must be gated.

### Step 4: Apply (only approved journeys)

Reuse `journeys-extract`'s upsert script — do not duplicate its stale-flip logic
here. Build a payload from the approved "after" state and pipe it in:

```bash
echo '{
  "journey_id": "<slug>",
  "title": "<unchanged from file>",
  "user_types": ["<unchanged from file>"],
  "trigger": "<approved>",
  "emotion": "<approved>",
  "steps": ["<approved>", "..."],
  "gaps": ["<remaining unresolved gaps, if any>"],
  "source_refs": ["<unchanged from file>"],
  "diagram": "<approved, or unchanged>",
  "test_ids": ["<approved candidates merged with existing test_ids>"]
}' | uv run .claude/skills/journeys-extract/scripts/upsert_journey.py upsert
```

Only include `"test_ids"` in the payload if you're actually changing it (adding
newly-found candidates) — omitting the key preserves whatever `journeys-verify`
already set. If the journey's body content changed while `status` was
`verified`, the upsert script will correctly flip it to `stale` — that's
expected; the new/changed test_ids haven't been mechanically confirmed yet.

### Step 5: Report Back, Recommend Verify

Tell the user which journeys were enriched, which candidate test_ids were added
vs. rejected (and why), and which gaps remain unresolved. Recommend running
`journeys-verify` next to confirm the new test_ids actually resolve — enrich
only *proposes* links, it doesn't validate them.

## Anti-Patterns

- **Don't write before approval** — this skill's entire reason to exist
  separately from `journeys-extract` is the human gate; skipping it makes it
  indistinguishable from a silent overwrite.
- **Don't invent test_ids** — a fabricated string that happens to not exist yet
  will just get flagged `stale` by `journeys-verify` on the next run, wasting a
  round trip. Only propose strings you actually found in a test file.
- **Don't touch `status`, `last_verified`, or unrelated `verify_notes` directly** —
  let the upsert script's existing invariant (verified + content-changed → stale)
  handle status; hand-setting it here would fight `journeys-verify`'s ownership.
- **Don't re-run full discovery** — if a journey needs rediscovery from scratch
  (e.g. the flow was rebuilt entirely), that's `journeys-extract`, not this skill.
