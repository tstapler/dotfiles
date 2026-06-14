---
name: ux-journey-mapper
description: >
  Map user journeys for an existing app using parallel lean agents — a PM story-map
  backbone, a UX flow analysis, and Mermaid diagram generation — then synthesize into
  a structured documentation artifact. Minimizes coordinator context by having each
  agent write full output to /tmp and return only a structured summary. Grounded in
  Jeff Patton (User Story Mapping), Jakob Nielsen (Usability Heuristics), and the
  lean-agent-loop pattern.
---

# UX Journey Mapper

Map what real users can do in an existing app across three lenses — story map backbone,
UX flow analysis, and visual diagrams — using parallel lean agents. Each agent writes
full output to `/tmp/` and returns only a tight JSON summary. The coordinator reads
summaries, not full files, keeping context O(summaries) not O(outputs).

## When to Use

- Brainstorming what the app does at a high level before writing docs
- Identifying missing flows or UX gaps in an existing product
- Generating the structure for a documentation site or help center
- Onboarding a new contributor to the product's user model

## Input

```
/ux:journey-mapper [focus]
```

- `[focus]` (optional): a specific area (e.g. "post-trip flow", "trip creation") or omit for the whole app
- The skill reads the current working directory for code, docs, and project plans automatically

## Instructions to Claude

### Step 0: Orient

Before launching agents, spend one tool call to locate the key context files. Look for:
- `docs/tasks/` — feature specs
- `project_plans/` — PRDs and proposals
- `shared/src/commonMain/kotlin/**/ui/` — screen/ViewModel files (for KMP apps)
- `README.md` — product overview

Read the top-level README and at most 2-3 other high-signal files inline. Do NOT read every file — agents will do the deep reads. Note the paths you found so you can hand them to agents.

### Step 1: Parallel — Story Map + UX Flows (launch both agents in the same message)

**Context budget rule**: Each agent gets ONE context block. Do not feed both agents the same large file dump. Instead, tell each agent WHERE to read (file paths), not what's in the files.

---

**Agent A — Story Map Backbone** (use `pm-product-manager` agent type if available, else general)

Prompt template:
```
You are building a User Story Map (Jeff Patton framework) for an existing app.

Read these files to understand the product:
<LIST THE 3-5 HIGHEST-SIGNAL FILES YOU FOUND IN STEP 0>

User Story Map structure:
- Activities: top-level things users do (verb phrases, ~5-8 total)
- Tasks: specific actions under each activity (what the user actually clicks/does)
- User types: who does each activity (e.g. "Trip Owner", "Travel Partner")

Focus area: <FOCUS OR "whole app">

Write your full story map to: /tmp/journey-backbone.md
Use this format in the file:
  # Story Map Backbone
  ## Activity: [Name]
  Users: [who]
  Tasks:
  - [task 1]
  - [task 2]

Return ONLY this JSON (no explanation):
{
  "agent": "backbone",
  "activities": [
    {"name": "...", "users": ["..."], "tasks": ["...", "..."]}
  ],
  "user_types": ["..."],
  "gaps": ["anything clearly missing from the current app"]
}
```

---

**Agent B — UX Flow Analysis** (use `ux-expert` agent type if available, else general)

Prompt template:
```
You are analyzing the UX flows of an existing app to identify key user journeys,
state transitions, and emotional high/low points.

Read these files to understand the screens and navigation:
<LIST UI/SCREEN FILES AND NAV GRAPH IF FOUND>

For each major user journey you identify:
- Name it (e.g. "First Trip Creation", "Mid-Trip Packing Check")
- Describe the trigger (what causes the user to enter this flow)
- List the steps (screen → action → screen)
- Note the emotional tone (anxious, excited, routine, frustrated)
- Flag any dead ends, missing states, or Nielsen violations

Focus area: <FOCUS OR "whole app">

Write your full analysis to: /tmp/journey-ux-flows.md

Return ONLY this JSON (no explanation):
{
  "agent": "ux-flows",
  "flows": [
    {
      "name": "...",
      "trigger": "...",
      "steps": ["..."],
      "emotion": "...",
      "gaps": ["..."]
    }
  ],
  "global_gaps": ["gaps that span multiple flows"]
}
```

---

### Step 2: Synthesize Summaries

Read both JSON summaries. Do NOT read the /tmp files yet.

Cross-reference:
- Which activities from the backbone have no corresponding UX flow? (coverage gap)
- Which UX flows expose a gap the backbone didn't name? (undocumented path)
- Are the user types consistent between agents?

Build a merged flow list: unique flows from both agents, deduplicated, sorted by user importance.

### Step 3: Parallel — Mermaid Diagrams

For each flow in the merged list (cap at 6 to stay tractable), launch one agent:

**Agent per flow — Mermaid Diagram** (use `mermaid-diagrams` agent type if available)

Prompt template:
```
Generate a Mermaid diagram for this user flow in the app.

Flow name: <NAME>
Steps: <STEPS FROM SUMMARY>
Emotional tone: <EMOTION>

Rules:
- Use stateDiagram-v2 for flows with clear state transitions (most packing/trip flows)
- Use flowchart TD for decision-heavy flows (e.g. "should I add this item?")
- Keep node labels short (≤ 5 words)
- Add a [*] start and one or more [*] end states
- Do NOT include code fences in the output — raw Mermaid only

Write the diagram to: /tmp/journey-diagram-<SLUG>.mmd
Return ONLY this JSON:
{
  "flow": "<NAME>",
  "type": "stateDiagram-v2 | flowchart",
  "file": "/tmp/journey-diagram-<SLUG>.mmd",
  "node_count": <n>
}
```

Launch all diagram agents in one message (parallel).

### Step 4: Assemble the Output Document

Read each /tmp/journey-diagram-*.mmd file (these are small — safe to read inline).
Read /tmp/journey-backbone.md and /tmp/journey-ux-flows.md for the full prose.

Write the final document to: `docs/ux/journey-map.md` (create `docs/ux/` if needed).

Output structure:
```markdown
# User Journey Map — <App Name>
> Generated <date>. Focus: <focus or "whole app">.

## User Types
[table: type | description | primary activities]

## Story Map Backbone
[table: activity | users | key tasks]

## Journeys

### [Flow Name]
**Trigger**: ...
**Emotional tone**: ...
**Steps**: numbered list
**Gaps / UX notes**: bullet list

```mermaid
[paste diagram here]
```

---
[repeat for each flow]

## Cross-Cutting Gaps
[consolidated gaps that appeared in multiple flows]

## Documentation Opportunities
[suggest doc pages: "Getting Started", "Planning Your First Trip", etc. — one line each]
```

### Step 5: Report Back

Tell the user:
- How many activities and flows were mapped
- How many gaps were found
- Where the output doc was written
- Which flows might need deeper UX review (flag ones with 3+ gaps)

Do NOT dump the full document into the conversation — just the summary and the path.

## Context Budget

| Phase | Coordinator reads | Tokens |
|---|---|---|
| Step 0 | 2-3 files inline | ~2k |
| Step 1 summaries | 2 JSON blobs | ~300 |
| Step 2 synthesis | In-head, no reads | 0 |
| Step 3 summaries | N × small JSON | ~100×N |
| Step 4 assembly | /tmp files (small) | ~3-5k |
| **Total** | | **~8-10k** |

vs. feeding all files to one agent: easily 40-80k tokens.

## Anti-Patterns

- **Don't read all screen files inline in Step 0** — hand paths to agents; they read what they need
- **Don't pass Agent A's full output to Agent B** — they work independently from the same source files
- **Don't generate more than 6 diagrams** — diminishing returns, pick the highest-traffic flows
- **Don't write the output doc before reading the /tmp files** — summaries omit detail needed for prose
