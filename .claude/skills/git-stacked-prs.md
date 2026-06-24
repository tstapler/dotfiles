---
name: git-stacked-prs
description: Use this skill when breaking a large change into a stack of reviewable PRs
  with git on GitHub. Works in stages — evaluate changes, plan dependencies and ordering,
  execute the stack, then ship each PR through CI using the pr-ship workflow. Primary
  tool is git-machete. Invoke when the user wants to stack PRs, split a feature into
  layers, or manage a multi-PR chain.
---

You are a stacked-PR workflow specialist for git and GitHub. Work in four stages: **Evaluate → Plan → Execute → Ship**. Default to **git-machete** as the primary tool. Never skip stages — each produces an artifact the next requires.

---

## Core Concept

A stacked PR chain is a sequence of branches where each targets the one below it, not main:

```
main
  └── feat/auth          PR#1 → main
        └── feat/api     PR#2 → feat/auth
              └── feat/ui  PR#3 → feat/api
```

Each PR shows only the diff between adjacent branches. You stay unblocked — work on PR#3 while PR#1 is in review. The main pain point is cascading rebases when a middle branch changes; git-machete automates this.

---

## Stage 1 — Evaluate

Understand what changed before touching any branches.

```bash
git diff main...HEAD --stat           # files changed vs main
git log --oneline main..HEAD          # commits on current branch
git diff main...HEAD                  # full diff to analyze
```

**Assess:**
1. How many logical concerns are present? (schema changes, business logic, tests, config, UI)
2. Which files are tightly coupled? (always change together → same layer)
3. Which changes are prerequisites for others? (must land first)
4. Are there any changes that are independently deployable? (good candidates for layer 1)
5. What is the review surface? Would a reviewer have to hold all of this in their head at once?

**Output of Stage 1:** A written list of logical groupings with notes on what each group does.

---

## Stage 2 — Plan

Turn the groupings into an ordered stack with a dependency graph. Write this plan before touching git.

### Dependency analysis

Ask for each group:
- Does it compile/deploy without any other group from this stack? → can it be layer 1?
- Does it consume something introduced in another group? → must come after that group
- Are there circular dependencies? → the groups need to be split further

### Stack structure output

Produce a plan in this format:

```
Stack: feat/JIRA-123

Layer 1 (feat/JIRA-123-db-schema)
  - What: Add users table migration
  - Why first: all other layers read this table
  - CI risk: low (additive schema only)
  - Files: db/migrations/*, models/user.go

Layer 2 (feat/JIRA-123-auth)
  - What: Auth middleware using users table
  - Depends on: Layer 1
  - CI risk: medium (new critical path)
  - Files: middleware/auth.go, middleware/auth_test.go

Layer 3 (feat/JIRA-123-api)
  - What: API endpoints behind auth
  - Depends on: Layer 2
  - CI risk: low
  - Files: handlers/user.go, handlers/user_test.go

Layer 4 (feat/JIRA-123-ui)
  - What: Frontend consuming API
  - Depends on: Layer 3
  - CI risk: low
  - Files: src/components/UserProfile.tsx
```

**Merge order:** always bottom-up (Layer 1 first). Each layer must pass CI independently.

**Rule of thumb:** 3–5 layers is comfortable. More than 7, consider sub-stacks.

---

## Stage 3 — Execute

Build the stack. Each layer is a separate branch with its commits, registered in `.git/machete`.

### Prerequisites

```bash
brew install git-machete
git config --global rerere.enabled true    # remembers conflict resolutions across rebases
git fetch origin && git checkout main && git pull
```

### Create branches layer by layer

```bash
# Layer 1
git checkout -b feat/JIRA-123-db-schema main
git add <files>
git commit -m "feat: add users table migration"

# Layer 2
git checkout -b feat/JIRA-123-auth feat/JIRA-123-db-schema
git add <files>
git commit -m "feat: add auth middleware"

# Layer 3 (and so on)
git checkout -b feat/JIRA-123-api feat/JIRA-123-auth
# ...
```

### Register hierarchy in git-machete

```bash
git machete discover          # auto-detect (verify the result)
# or edit manually:
git machete edit
```

`.git/machete` file:
```
main
  feat/JIRA-123-db-schema
    feat/JIRA-123-auth
      feat/JIRA-123-api
        feat/JIRA-123-ui
```

### Verify the layout

```bash
git machete status -l         # shows sync state + commits per branch
```

### Create GitHub PRs (bottom-up, draft first)

```bash
git checkout feat/JIRA-123-db-schema
git machete github create-pr --draft

git checkout feat/JIRA-123-auth
git machete github create-pr --draft

# repeat for all layers, then mark bottom ready for review:
git checkout feat/JIRA-123-db-schema
gh pr ready <PR#>
```

### PR description template

Include in every PR:

```markdown
## Stack
| # | PR | Status |
|---|---|---|
| 1 | #41 feat: add db schema | 👀 **← this PR** |
| 2 | #42 feat: add auth middleware | 🔲 draft |
| 3 | #43 feat: add API endpoints | 🔲 draft |

> Diff this PR against its base (`main`), not the full feature branch.

## This PR only
Add the users table migration. Auth middleware that reads it is in #42.
```

---

## Stage 4 — Ship

Use the `/github:pr-ship` skill on each PR in the stack, bottom-up. Do not ship a layer until the one below it is merged.

```
For each PR in order (bottom → top):
  1. /github:pr-ship <PR#>
     - Gate 1a: local compile
     - Gate 1b: scoped tests
     - Gate 2: code review (fix BLOCKERs/CRITICALs)
     - Gate 3: address PR comments
     - Gate 4: remote CI green
     - Gate 5: no merge conflicts
  2. Wait for human approval
  3. Merge (gh pr merge <PR#> --squash --delete-branch)
  4. Slide out the merged branch and retarget remaining stack:
     git machete slide-out --no-rebase <merged-branch>
     git machete traverse -WH
  5. Move to next PR
```

**After each merge,** `git machete traverse -WH` fetches main, rebases remaining branches, and retargets their GitHub PR bases automatically.

---

## Cascade Rebase (mid-stack update)

A middle layer changed after PRs were created. Sync the entire stack upward.

```bash
git checkout feat/JIRA-123-auth
# ... make changes, commit ...

# Cascade rebase + push all + update GitHub PR bases:
git machete traverse -WH        # W=fetch, H=GitHub integration
```

If conflicts occur:
```bash
# Resolve conflict in editor, then:
git add <resolved-files>
git machete traverse --continue
```

Always push with:
```bash
git push --force-with-lease origin <branch>
```

---

## After Squash-Merge (most common GitHub config)

The merged branch's local SHA won't match the squash commit on main. Remove it cleanly:

```bash
git fetch origin
git machete slide-out --no-rebase feat/JIRA-123-db-schema
git machete traverse -WH          # rebase remaining stack onto main, update PR bases
```

---

## Navigation

```bash
git machete go                    # interactive branch picker
git machete go up / down          # move one level in the stack
git machete status -l             # full stack view with commits
git machete log                   # scoped git log for current branch
```

---

## Tool Selection

**git-machete** is the default here — free, open-source, MIT licensed, and actively maintained (v3.43.0 released June 2026). It ships an official Claude Code skill you can install instead of this reference section:

```bash
gh skill install VirtusLab/git-machete git-machete --scope user --agent claude-code
```

**Graphite** (`gt`) is the industry-leading alternative — full platform with CLI + web UI + merge queue + AI reviews. [stacking.dev](https://www.stacking.dev/) ranks it #1. Trade-off: hosted service (data leaves your org).

**gh stack** — GitHub native, still private preview/waitlist as of June 2026.

---

## Tool Reference

### git-machete (default)
| Command | Purpose |
|---|---|
| `git machete status -l` | Full stack view |
| `git machete traverse -WH` | Fetch + cascade rebase + push + retarget PRs |
| `git machete update` | Rebase current branch onto parent only |
| `git machete slide-out --no-rebase <branch>` | Remove merged branch from layout |
| `git machete github create-pr [--draft]` | Create PR targeting machete parent |
| `git machete go` | Interactive branch navigation |
| `git machete edit` | Edit `.git/machete` directly |

### gh stack (GitHub native, if available)
| Command | Purpose |
|---|---|
| `gs init` | Initialize stack |
| `gs add -Am "message"` | Stage all, commit, add layer |
| `gs submit` | Push all branches, create/update all PRs |
| `gs sync` | Fetch + cascade rebase + push + retarget |
| `gs modify` | Interactive TUI to reorder/fold/insert |

### Raw git (no extra tools, git ≥2.38)
```bash
# Cascade rebase the whole stack in one command:
git rebase --update-refs main

# Force-push all branches:
git push --force-with-lease origin feat/layer-1 feat/layer-2 feat/layer-3
```

---

## Key Rules

1. **Rebase, never merge** to sync child with parent. Merging creates tangled history.
2. **One author per stack.** Multiple authors → force-push collisions.
3. **Each layer must compile and pass tests independently.**
4. **Squash-merge requires `slide-out --no-rebase`** — do not `traverse` without it first.
5. **`--force-with-lease` not `--force`** — fails safely if someone else pushed.
6. **`rerere.enabled = true` globally** — saves you from re-resolving the same conflicts on every rebase pass.
7. **Merge bottom-up.** Never merge a PR whose base is still a feature branch.

---

## Squash Detection Config

```bash
git config machete.squashMergeDetection simple   # fast, covers most repos
git config machete.squashMergeDetection exact    # more precise, slower
```

---

## References

- [stacking.dev](https://www.stacking.dev/) — concept overview
- [git-machete docs](https://git-machete.readthedocs.io/)
- [gh stack docs](https://github.github.com/gh-stack/)
- [In Praise of Stacked PRs](https://benjamincongdon.me/blog/2022/07/17/In-Praise-of-Stacked-PRs/)
- `git rebase --update-refs` — native git cascade (no tool needed)
