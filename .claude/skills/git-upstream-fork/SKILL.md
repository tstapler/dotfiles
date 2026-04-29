---
name: git-upstream-fork
description: Identify commits/changes in a locally-checked-out source repo that should be upstreamed to another locally-checked-out target repo, then create a PR. Replaces rsync-based syncing with a git-native, Claude-analyzed workflow. Use when contributing local changes back to an upstream project.
---

# Upstream Fork Changes (Local-to-Local)

Both repos are checked out locally. No rsync. Use `git format-patch` / `git am` to move changes between them, with Claude filtering out personal/private content before anything is committed.

See also:
- `/fork-merge-plan` — run this first when the target has significant divergence; it produces a conflict map and commit classification before you touch any branches
- `/sync-remotes` — use instead when both repos are equally canonical (public, bidirectional, no filtering needed)
- `/git-worktrees` — for creating the upstream branch in isolation

## Step 1: Establish Source and Target

```bash
SOURCE_REPO=/path/to/source     # e.g. /Users/tylerstapler/Documents/personal-wiki
TARGET_REPO=/path/to/target     # e.g. /Users/tylerstapler/IdeaProjects/markdown-confluence
TARGET_BRANCH=main
```

Common setup for this project:
```
SOURCE: /Users/tylerstapler/Documents/personal-wiki
TARGET: /Users/tylerstapler/IdeaProjects/markdown-confluence
```

## Step 2: Determine Repo Relationship

First check whether the repos share git history (one is a fork of the other) or are completely independent:

```bash
cd $SOURCE_REPO
git remote add target-local $TARGET_REPO 2>/dev/null || true
git fetch target-local

# Check for shared history
git merge-base HEAD target-local/$TARGET_BRANCH 2>/dev/null && echo "SHARED HISTORY" || echo "UNRELATED REPOS"
```

- **Shared history** → use [Path A: commit-based sync](#path-a-commit-based-sync-shared-history)
- **Unrelated repos** → use [Path B: file-based sync](#path-b-file-based-sync-unrelated-repos) ← most common

---

## Path A: Commit-Based Sync (Shared History)

For true forks where one repo was branched from the other.

```bash
cd $SOURCE_REPO

# Commits in source not yet in target
git log target-local/$TARGET_BRANCH..HEAD --oneline

# Export as patch files (one per commit)
git format-patch target-local/$TARGET_BRANCH --output-directory /tmp/upstream-patches/
```

Classify patch files with Claude (see classification criteria below), then apply:

```bash
cd $TARGET_REPO
git checkout -b upstream-$(date +%Y%m%d) $TARGET_BRANCH

for patch in /tmp/upstream-patches/0001-fix-*.patch; do
    git am "$patch"
done
```

---

## Path B: File-Based Sync (Unrelated Repos)

For repos with diverged/independent histories (e.g., personal-wiki → markdown-confluence). **This is the common case.**

### Identify Which Paths to Sync

First, decide which top-level paths in the source are relevant to the target. Read the source repo's directory structure:

```bash
ls $SOURCE_REPO
```

Typical paths worth upstreaming to a tool repo:
- `.claude/skills/` — Claude skills developed in personal context
- `scripts/` — utility scripts
- `src/` — source code improvements
- `tests/` — new test cases

### Generate File-Specific Diffs

```bash
cd $SOURCE_REPO

# Diff specific paths between source and target (works across unrelated histories)
git diff target-local/$TARGET_BRANCH -- .claude/skills/ > /tmp/skills.patch
git diff target-local/$TARGET_BRANCH -- scripts/ > /tmp/scripts.patch
git diff target-local/$TARGET_BRANCH -- src/ > /tmp/src.patch
```

### Classify with Claude

Read each patch file and classify every changed file. Keep only files that are:

**Upstreamable:**
- Bug fixes and feature code in `src/`
- New or improved tests
- Claude skills/commands for the shared tool
- CI/workflow improvements
- Documentation relevant to the public project

**Personal/Private — exclude:**
- Journal entries, personal notes (`logseq/`, `pages/`, date-named `.md` files)
- Personal config (`.claude/settings.local.json`, `.idea/`, `.env`, `settings.local.*`)
- Pages about private/work-only projects
- Sensitive credentials or internal URLs
- Scratch files and work-in-progress notes

### Apply the Filtered Diff

Use a **git worktree** to work in an isolated directory — no branch switching, no risk of polluting your main checkout:

```bash
# Create a worktree with a new branch (clean isolated environment)
git -C $TARGET_REPO worktree add /tmp/upstream-work-$(date +%Y%m%d) -b upstream-$(date +%Y%m%d)
WORK=/tmp/upstream-work-$(date +%Y%m%d)

# Apply a specific patch
git -C $WORK apply /tmp/skills.patch

# Or copy specific files directly (simplest for small sets)
cp -r $SOURCE_REPO/.claude/skills/my-new-skill $WORK/.claude/skills/
cp $SOURCE_REPO/src/some/new/file.py $WORK/src/some/new/file.py

# Stage and commit
git -C $WORK add .
git -C $WORK diff --staged --stat    # review before committing
git -C $WORK commit -m "upstream: add X from personal development"

# Clean up worktree after PR is merged
git -C $TARGET_REPO worktree remove /tmp/upstream-work-$(date +%Y%m%d)
```

**Why worktrees**: Applying patches or copying files is a multi-step operation. A worktree keeps your main checkout clean if something goes wrong mid-way, and lets you work on the upstream PR while continuing other work in the main checkout.

## Step 6: Review and Clean Up

```bash
cd $TARGET_REPO

git log main..HEAD --oneline          # confirm what's included
git diff main..HEAD --stat            # confirm no personal files snuck in
git diff main..HEAD -- "*.md" | head  # spot-check any markdown
```

Remove any personal files that were accidentally included:
```bash
git rm --cached path/to/personal/file.md
echo "path/to/personal/file.md" >> .gitignore
git commit --amend --no-edit
```

## Step 6.5: Quality Gate (pre-push)

Before pushing, run the target repo's build and test suite from the upstream branch:

```bash
cd $WORK   # or the upstream branch directory

make build && make test && make lint
```

If the quality gate fails, fix the issue before pushing — don't open a PR with a known broken build.

Also set `diff3` conflict style if you had any merge conflicts — it shows the common ancestor alongside both sides, making resolution much faster:

```bash
git config merge.conflictstyle diff3
```

## Step 7: Create the PR

```bash
cd $TARGET_REPO

git push -u origin $(git branch --show-current)

gh pr create \
  --title "upstream: [description]" \
  --body "$(cat <<'EOF'
## Summary
[Claude-generated summary of what was upstreamed]

## Changes
- `src/...`: [what changed]

## Excluded
Personal content (journal entries, local config, private notes) was filtered out.
EOF
)"
```

## Step 8: Tag the Sync Point in Source Repo

After the PR merges, tag the source repo so future runs know where the last sync was:

```bash
cd $SOURCE_REPO
git tag last-upstream-sync-$(date +%Y%m%d)
git push origin --tags
```

## Key Rules

- **No rsync** — `git format-patch` + `git am` transfers only the diff, not raw files. No bulk file copy = no DLP trigger.
- **Local remotes are safe** — `git remote add target-local /path/to/repo` reads the git objects directly; nothing goes over the network.
- **Classify before applying** — read ALL patches first, then apply only the clean ones. One bad patch can poison the branch.
- **Tag after merging** — without a sync tag, every run must manually figure out where the last sync ended.

## Quick Reference

```bash
# Full workflow in one block
SOURCE=/Users/tylerstapler/Documents/personal-wiki
TARGET=/Users/tylerstapler/IdeaProjects/markdown-confluence

cd $SOURCE
git remote add target-local $TARGET 2>/dev/null; git fetch target-local
git format-patch target-local/main --output-directory /tmp/upstream-patches/

# [Claude classifies patches — edit INCLUDE list below]
INCLUDE=( "0001-..." "0003-..." )

cd $TARGET
git checkout -b upstream-$(date +%Y%m%d) main
for p in "${INCLUDE[@]}"; do git am "/tmp/upstream-patches/$p"; done
git push -u origin HEAD
gh pr create --title "upstream: ..."
```
