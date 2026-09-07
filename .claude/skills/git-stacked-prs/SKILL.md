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

Produce a written plan of ordered layers, each naming its branch, purpose, dependency, CI risk, and files touched. Merge order is always bottom-up (Layer 1 first), and each layer must pass CI independently. 3–5 layers is comfortable; beyond 7, consider sub-stacks.

See [references/examples.md](references/examples.md) for the stack-plan output format.

---

## Stage 3 — Execute

Build the stack. Each layer is a separate branch with its commits, registered in `.git/machete`.

### Prerequisites

```bash
brew install git-machete
git config --global rerere.enabled true    # remembers conflict resolutions across rebases
git config --global machete.squashMergeDetection simple
git fetch origin && git checkout main && git pull
```

git-machete also ships an official Claude Code skill with deep agent-specific guidance:
```bash
gh skill install VirtusLab/git-machete git-machete --scope user --agent claude-code
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

### Verify and create PRs

```bash
git machete status -l         # shows sync state + commits per branch
```

Create GitHub PRs bottom-up, draft first:
```bash
git checkout feat/JIRA-123-db-schema
git machete github create-pr --draft
# repeat for all layers, then mark bottom ready for review:
git checkout feat/JIRA-123-db-schema
gh pr ready <PR#>
```

Every PR body should include a stack table and note which PR to diff against. See [references/examples.md](references/examples.md) for the PR description template.

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

If a middle layer changes after PRs are created, or after a squash-merge, see [references/advanced-operations.md](references/advanced-operations.md) for the cascade-rebase and cleanup procedures.

---

## Navigation

```bash
git machete go                    # interactive branch picker
git machete go up / down          # move one level in the stack
git machete status -l             # full stack view with commits
git machete log                   # scoped git log for current branch
```

For the git-machete vs. gh stack vs. Graphite comparison and the full command reference (including the raw-git no-extra-tools alternative), see [references/tool-reference.md](references/tool-reference.md).

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

## References

- [stacking.dev](https://www.stacking.dev/) — concept overview
- [git-machete docs](https://git-machete.readthedocs.io/)
- [gh stack docs](https://github.github.com/gh-stack/)
- [In Praise of Stacked PRs](https://benjamincongdon.me/blog/2022/07/17/In-Praise-of-Stacked-PRs/)
- `git rebase --update-refs` — native git cascade (no tool needed)
