---
name: fork-merge-plan
description: Plan a bidirectional merge between a personal fork and an upstream repo. Produces a written merge plan (commit classification, conflict map, strategy) without executing any git operations. Use when both branches have diverged and you need to preserve functionality from both sides.
---

# Fork ↔ Upstream Merge Plan

**Goal**: Produce a rigorous written plan for merging two diverged branches (fork + upstream). No merge is executed — only analysis and a plan.

---

## Step 1: Establish Context

Identify which remote is the upstream and which is the personal fork. Infer from existing remotes if not specified:

```bash
git remote -v
```

Common pattern for this project:
- **Fork (personal)**: `origin` → `tstapler/stapler-squad`
- **Upstream (work)**: `upstream-fanatics` → `TylerStaplerAtFanatics/stapler-squad`

Set variables:
```bash
FORK_REMOTE=origin
UPSTREAM_REMOTE=upstream-fanatics
BRANCH=main
```

## Step 2: Fetch & Find Divergence

```bash
git fetch $FORK_REMOTE
git fetch $UPSTREAM_REMOTE

# Commits only on fork (not in upstream)
git log $UPSTREAM_REMOTE/$BRANCH..HEAD --oneline --no-merges

# Commits only on upstream (not in fork)
git log HEAD..$UPSTREAM_REMOTE/$BRANCH --oneline --no-merges

# Merge base (common ancestor)
git merge-base HEAD $UPSTREAM_REMOTE/$BRANCH
```

## Step 3: Categorize Every Commit

For each commit on **each side**, classify it into one of these buckets:

| Bucket | Description | Merge action |
|--------|-------------|--------------|
| `FEATURE` | New user-visible functionality | Merge — preserve |
| `FIX` | Bug fix | Merge — preserve |
| `REFACTOR` | Code restructure, no behavior change | Merge — assess conflicts |
| `INFRA` | CI, build, tooling | Merge selectively |
| `BASELINE` | Auto-generated benchmark baselines (`[skip ci]`) | Skip — regenerate after merge |
| `PRIVATE` | Personal config, secrets, work-only changes | Do NOT merge upstream |
| `DUPLICATE` | Already on the other side (cherry-pick or same change) | Skip |

```bash
# Get the full commit list with stats for each side
git log $UPSTREAM_REMOTE/$BRANCH..HEAD --oneline --no-merges --stat
git log HEAD..$UPSTREAM_REMOTE/$BRANCH --oneline --no-merges --stat
```

Read each commit's diff summary (`--stat`) and assign a bucket. Auto-assign `BASELINE` for commits matching `chore(bench): update`.

## Step 4: Map Conflicts

Find files changed on **both** sides since the merge base:

```bash
MERGE_BASE=$(git merge-base HEAD $UPSTREAM_REMOTE/$BRANCH)

# Files changed on fork side
git diff --name-only $MERGE_BASE HEAD

# Files changed on upstream side
git diff --name-only $MERGE_BASE $UPSTREAM_REMOTE/$BRANCH

# Files changed on BOTH sides (potential conflicts)
comm -12 \
  <(git diff --name-only $MERGE_BASE HEAD | sort) \
  <(git diff --name-only $MERGE_BASE $UPSTREAM_REMOTE/$BRANCH | sort)
```

For each conflict file, compare the changes:
```bash
# What fork changed in this file
git diff $MERGE_BASE HEAD -- <file>

# What upstream changed in this file
git diff $MERGE_BASE $UPSTREAM_REMOTE/$BRANCH -- <file>
```

Classify each conflict:
- **Textual only** — git can auto-resolve (different hunks, no overlap)
- **Logical conflict** — same section edited differently (requires manual resolution)
- **Intent conflict** — one side added, other deleted (requires decision)

## Step 5: Simulate the Merge (Dry Run)

```bash
# Create a temporary branch from fork HEAD (do NOT commit to it)
# This is only for conflict detection
git checkout -b merge-simulation HEAD

git merge --no-commit --no-ff $UPSTREAM_REMOTE/$BRANCH

# Show what would conflict
git status

# Abort — we are not executing the merge
git merge --abort
git checkout -
git branch -D merge-simulation
```

Note all files listed as `CONFLICT` in the status output.

## Step 6: Write the Merge Plan

Produce a markdown document with these sections:

### Plan Structure

```markdown
# Merge Plan: fork ↔ upstream — <date>

## Summary
- Fork ahead by N commits (after excluding baselines)
- Upstream ahead by M commits
- Merge base: <sha> (<date>)
- Conflict files: N files need manual resolution

## Commit Classification

### Fork-only commits (origin/main → upstream)
| SHA | Message | Bucket | Action |
|-----|---------|--------|--------|
| ... | ...     | FEATURE | Merge |
| ... | ...     | BASELINE | Skip |

### Upstream-only commits (upstream-fanatics/main → fork)
| SHA | Message | Bucket | Action |
|-----|---------|--------|--------|
| ... | ...     | FIX | Merge |

## Conflict Map

### Files with overlapping changes
| File | Fork change summary | Upstream change summary | Conflict type | Resolution notes |
|------|--------------------|-----------------------|--------------|-----------------|
| ...  | ...                | ...                   | Logical      | Keep both, reconcile X |

## Merge Strategy

**Direction**: Merge upstream INTO fork on a new branch
**Branch name**: `merge/upstream-YYYYMMDD`

**Sequence**:
1. Create integration branch from fork HEAD
2. `git merge upstream-fanatics/main`
3. Resolve conflicts in order: [list files with resolution guidance]
4. Verify: build passes, tests pass, benchmark baselines excluded

## Post-Merge Checklist
- [ ] `make build` passes
- [ ] `make test` passes
- [ ] `make lint` passes
- [ ] No benchmark baseline commits included
- [ ] No private config files included
- [ ] PR created against upstream-fanatics/main (or origin/main, depending on direction)
```

## Rules

- **Plan only** — never execute `git merge`, `git am`, or `git apply` during this skill. The dry-run simulation is the only exception, and it MUST end with `git merge --abort`.
- **Classify before recommending** — read every commit diff before assigning a bucket. Do not guess from the message alone.
- **Baseline commits are noise** — commits matching `chore(bench): update * baseline [skip ci]` are auto-generated artifacts. Always bucket as `BASELINE` and skip.
- **Conflict count drives complexity** — if >5 logical conflicts, flag the merge as HIGH COMPLEXITY and recommend splitting into multiple steps.
- **Both sides matter** — the plan must preserve features from the fork AND from upstream. Do not default to "take upstream" — assess each change on its merits.
- **Private guard** — before including any fork commit in the upstream direction, check: does it contain personal config, credentials, private paths, or work-only references? If so, bucket as `PRIVATE`.
