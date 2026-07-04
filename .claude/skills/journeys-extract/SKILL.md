---
name: journeys-extract
description: >
  Extracts user journeys from an app's existing code into persistent, declarative
  markdown+YAML spec files under docs/journeys/ — one file per journey, each with
  a stable journey_id and frontmatter fields for test linkage (test_ids, status,
  last_verified) that journeys-verify and journeys-enrich own and update later.
  Uses three parallel lean agents (PM story-map backbone, UX flow analysis, Mermaid
  diagram generation) to discover journeys, then upserts by journey_id so re-running
  never duplicates or clobbers verification state. Use when journeys aren't
  documented yet, or to rediscover/add journeys after major app changes. This is
  the extraction phase only — it does not check whether journeys still work
  (journeys-verify) or fill in narrative detail on existing drafts (journeys-enrich).
---

# Journeys: Extract

Discover user journeys in an existing app and persist them as individual, re-runnable
markdown spec files (`docs/journeys/<slug>.md`), each frontmatter-tagged with a stable
`journey_id` and empty test-linkage fields for downstream skills to fill in. Builds on
the same parallel lean-agent discovery pattern as `ux-journey-mapper`, but writes an
upsertable declarative format instead of a single one-shot report.

## When to Use

- No `docs/journeys/` directory exists yet — first-time extraction
- The app changed significantly (new screens, flows, features) and journeys need
  rediscovery
- NOT for checking if existing journeys still pass tests (`journeys-verify`) or for
  deepening/annotating an existing draft journey (`journeys-enrich`)

## Input

```
/journeys:extract [focus]
```

- `[focus]` (optional): a specific area (e.g. "checkout flow") or omit for the whole app

## Journey Spec Format

Each journey is one file: `docs/journeys/<slug>.md`

```markdown
---
journey_id: first-trip-creation      # kebab-case, stable — do not rename by hand
title: First Trip Creation
user_types: [Trip Owner]
status: draft                        # draft | verified | stale — owned by verify/enrich
test_ids: []                         # owned by journeys-verify
last_verified: null                  # owned by journeys-verify
source_refs:                         # owned by journeys-extract
  - shared/src/.../TripCreationScreen.kt
---

# First Trip Creation

**Trigger**: ...
**Emotional tone**: ...

## Steps
1. ...

## Gaps / Notes
- ...

```mermaid
stateDiagram-v2
...
```
```

`journey_id`, `test_ids`, `status`, and `last_verified` belong to journeys-verify/enrich.
Extraction never sets `status` past `draft` and never touches `test_ids`/`last_verified`
directly — the upsert script handles this (see Step 4).

## Instructions to Claude

### Step 0: Orient

Locate context files with one tool call: `docs/tasks/`, `project_plans/`, UI/screen
source directories, `README.md`. Read the top-level README and at most 2-3 other
high-signal files inline. Agents will do the deep reads — don't read everything here.

### Step 1: Parallel — Story Map + UX Flows (launch both in one message)

**Agent A — Story Map Backbone** (use `pm-product-manager` agent type if available)

```
Build a User Story Map (Jeff Patton framework) for an existing app.
Read: <3-5 highest-signal files from Step 0>
Focus area: <FOCUS OR "whole app">

Write full story map to: /tmp/journey-backbone.md

Return ONLY this JSON:
{
  "agent": "backbone",
  "activities": [{"name": "...", "users": ["..."], "tasks": ["...", "..."]}],
  "user_types": ["..."],
  "gaps": ["..."]
}
```

**Agent B — UX Flow Analysis** (use `ux-expert` agent type if available)

```
Analyze UX flows of an existing app: journeys, state transitions, emotional tone.
Read: <UI/screen files and nav graph from Step 0>
Focus area: <FOCUS OR "whole app">

Write full analysis to: /tmp/journey-ux-flows.md

Return ONLY this JSON:
{
  "agent": "ux-flows",
  "flows": [{"name": "...", "trigger": "...", "steps": ["..."], "emotion": "...", "gaps": ["..."]}],
  "global_gaps": ["..."]
}
```

### Step 2: Synthesize Summaries

Read both JSON summaries only (not the `/tmp` files). Build a merged flow list:
unique flows from both agents, deduplicated by name, sorted by importance. Note
which activities have no matching UX flow (coverage gap) and vice versa.

### Step 3: Parallel — Mermaid Diagrams

For each flow in the merged list (cap at 6), launch one agent:

```
Generate a Mermaid diagram for this user flow.
Flow name: <NAME>  Steps: <STEPS>  Emotional tone: <EMOTION>
Use stateDiagram-v2 for clear state transitions, flowchart TD for decision-heavy flows.
Keep node labels short. Add [*] start/end. No code fences — raw Mermaid only.

Write to: /tmp/journey-diagram-<SLUG>.mmd
Return ONLY: {"flow": "<NAME>", "file": "/tmp/journey-diagram-<SLUG>.mmd"}
```

Launch all diagram agents in one message.

### Step 4: Upsert Journey Files (deterministic — use the script, don't hand-write frontmatter)

For each merged flow, build a JSON payload and pipe it to the upsert script — this
is what preserves `test_ids`/`status`/`last_verified` on re-runs instead of
clobbering them, and flips `status: verified` to `stale` when the body actually
changed:

```bash
echo '{
  "journey_id": "<kebab-case-slug-from-flow-name>",
  "title": "<Flow Name>",
  "user_types": ["..."],
  "trigger": "...",
  "emotion": "...",
  "steps": ["...", "..."],
  "gaps": ["..."],
  "source_refs": ["path/to/file.ts"],
  "diagram": "<contents of the .mmd file for this flow>"
}' | uv run .claude/skills/journeys-extract/scripts/upsert_journey.py upsert
```

Run one invocation per flow (sequential is fine — this is a cheap deterministic
script, not worth parallelizing). Collect each `{slug, action, path}` result.

### Step 5: Regenerate the Index

Write `docs/journeys/README.md` — this file is **fully derived, always overwritten**
(unlike the per-journey files, it carries no hand-edited or verify-owned state):

```markdown
# User Journeys — <App Name>
> Regenerated <date> by journeys-extract. Focus: <focus or "whole app">.

## Journeys
| Journey | Status | User Types | File |
|---|---|---|---|
| <title> | <status from upsert result — read the file to get current status> | <types> | [<slug>.md](<slug>.md) |

## Cross-Cutting Gaps
<gaps that appeared in multiple flows>

## Next Steps
- Run `journeys-verify` to link these journeys to automated tests
- Journeys marked "stale" need re-verification after this extraction
```

### Step 6: Report Back

Tell the user: how many journeys created / updated / marked stale / unchanged, how
many cross-cutting gaps found, and the path to `docs/journeys/`. Flag any journey
the upsert marked `updated-marked-stale` — its linked tests may no longer match
reality. Do NOT dump full journey files into the conversation.

## Anti-Patterns

- **Don't hand-write frontmatter** — always go through `upsert_journey.py`. Hand-editing
  risks silently dropping `test_ids`/`status` that journeys-verify set.
- **Don't read all screen files inline in Step 0** — hand paths to agents.
- **Don't generate more than 6 diagrams** — pick the highest-traffic flows.
- **Don't invent a new `journey_id` for a flow that already has a file** — if a flow's
  name changed but it's clearly the same journey, keep the original slug so the
  upsert matches the existing file instead of creating a duplicate.
