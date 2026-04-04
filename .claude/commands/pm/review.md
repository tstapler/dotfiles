---
description: Survey what's built, assess roadmap health, surface gaps, and recommend
  next features to prioritize
prompt: '# Product Review


  Survey your project''s current feature set from a product perspective — what exists,
  what''s planned, what''s missing, and what to prioritize next. Uses the `product-management`
  skill.


  ## Scope


  ${1:-current project (scans docs/tasks/, docs/bugs/, project_plans/)}


  ## When to Use


  - Start of a new work cycle — "What should I focus on next?"

  - After shipping several features — "What''s the current state of the product?"

  - When feeling feature-scattered — "Are we building the right things?"

  - Before roadmap planning — "What gaps exist before I can prioritize?"


  ## Instructions to Claude


  **Step 1: Discover what exists**


  Scan the project to build a picture of the current feature landscape:

  - Read `docs/tasks/` — what features are planned or in progress?

  - Read `docs/bugs/open/` and `docs/bugs/in-progress/` — what issues exist?

  - Read `project_plans/` README files — what major initiatives are underway?

  - Read `TODO.md` if present — what''s the top-level view?

  - Scan git log (last 30 commits) for recently shipped work: `git log --oneline -30`


  If a specific project path was provided (`{{args}}`), focus there.


  **Step 2: Apply the product-management skill to assess**


  Using the product-management framework, evaluate:


  **Feature Completeness**

  - What core user jobs are currently served?

  - What jobs are partially served (started but incomplete)?

  - What obvious jobs have no coverage?


  **Roadmap Health**

  - Are features organized around outcomes or just shipped ad-hoc?

  - Is there a clear Now/Next/Later structure, or is everything "someday"?

  - Are there features in flight that should be completed before starting new ones?


  **Scope Coherence**

  - Do the features tell a coherent product story?

  - Are there orphaned features that don''t connect to user outcomes?

  - Is there scope creep — features that should be cut or deferred?


  **Prioritization**

  - Apply a quick RICE assessment to the top 3-5 candidate next features

  - Surface any high-value, low-effort wins that are being ignored

  - Identify any low-value, high-effort work that should be cut


  **Step 3: Produce the product review report**


  ```markdown

  ## Product Review: <Project Name>

  **Date**: {today}


  ### What''s Shipped (last 30 days)

  - {feature} — {user job it serves}


  ### In Progress

  - {feature} — {status} — {user job}


  ### Planned (docs/tasks/)

  - {feature} — {user job}


  ### Open Issues

  - {N} bugs: {Critical: N, High: N, Medium: N, Low: N}


  ---


  ### Feature Gaps

  | User Job | Current Coverage | Gap |

  |----------|-----------------|-----|

  | {job}    | {none/partial}  | {what''s missing} |


  ### Roadmap Health

  **Status**: [Healthy / Scattered / Overloaded]

  {1-2 sentence assessment}


  ### Prioritization: Top 3 Next Features

  | Feature | Reach | Impact | Confidence | Effort | RICE Score |

  |---------|-------|--------|------------|--------|------------|

  | {name}  | ...   | ...    | ...        | ...    | ...        |


  ### Recommended Next Feature

  **Build next**: {feature name}

  **Why**: {outcome it unlocks, RICE rationale}

  **Trigger**: `/pm:triad-review {feature-name}` to check readiness before starting

  ```


  Execute this workflow now for: ${1:-current project}

  '
---

# Product Review

Survey your project's current feature set from a product perspective — what exists, what's planned, what's missing, and what to prioritize next. Uses the `product-management` skill.

## Scope

${1:-current project (scans docs/tasks/, docs/bugs/, project_plans/)}

## When to Use

- Start of a new work cycle — "What should I focus on next?"
- After shipping several features — "What's the current state of the product?"
- When feeling feature-scattered — "Are we building the right things?"
- Before roadmap planning — "What gaps exist before I can prioritize?"

## Instructions to Claude

**Step 1: Discover what exists**

Scan the project to build a picture of the current feature landscape:
- Read `docs/tasks/` — what features are planned or in progress?
- Read `docs/bugs/open/` and `docs/bugs/in-progress/` — what issues exist?
- Read `project_plans/` README files — what major initiatives are underway?
- Read `TODO.md` if present — what's the top-level view?
- Scan git log (last 30 commits) for recently shipped work: `git log --oneline -30`

If a specific project path was provided (`$ARGUMENTS`), focus there.

**Step 2: Apply the product-management skill to assess**

Using the product-management framework, evaluate:

**Feature Completeness**
- What core user jobs are currently served?
- What jobs are partially served (started but incomplete)?
- What obvious jobs have no coverage?

**Roadmap Health**
- Are features organized around outcomes or just shipped ad-hoc?
- Is there a clear Now/Next/Later structure, or is everything "someday"?
- Are there features in flight that should be completed before starting new ones?

**Scope Coherence**
- Do the features tell a coherent product story?
- Are there orphaned features that don't connect to user outcomes?
- Is there scope creep — features that should be cut or deferred?

**Prioritization**
- Apply a quick RICE assessment to the top 3-5 candidate next features
- Surface any high-value, low-effort wins that are being ignored
- Identify any low-value, high-effort work that should be cut

**Step 3: Produce the product review report**

```markdown
## Product Review: <Project Name>
**Date**: {today}

### What's Shipped (last 30 days)
- {feature} — {user job it serves}

### In Progress
- {feature} — {status} — {user job}

### Planned (docs/tasks/)
- {feature} — {user job}

### Open Issues
- {N} bugs: {Critical: N, High: N, Medium: N, Low: N}

---

### Feature Gaps
| User Job | Current Coverage | Gap |
|----------|-----------------|-----|
| {job}    | {none/partial}  | {what's missing} |

### Roadmap Health
**Status**: [Healthy / Scattered / Overloaded]
{1-2 sentence assessment}

### Prioritization: Top 3 Next Features
| Feature | Reach | Impact | Confidence | Effort | RICE Score |
|---------|-------|--------|------------|--------|------------|
| {name}  | ...   | ...    | ...        | ...    | ...        |

### Recommended Next Feature
**Build next**: {feature name}
**Why**: {outcome it unlocks, RICE rationale}
**Trigger**: `/pm:triad-review {feature-name}` to check readiness before starting
```

Execute this workflow now for: ${1:-current project}
