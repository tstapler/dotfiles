---
name: sync-remotes
description: Execute a full bidirectional sync between the personal fork (origin) and the work upstream (upstream-fanatics). Creates a dated integration branch, resolves known conflict patterns, runs CI checks, opens two PRs (fork→upstream and upstream→fork), and monitors until checks pass. Use after /fork-merge-plan or whenever both repos have diverged and need to be brought back in sync.
---

# Sync Remotes — Bidirectional Fork ↔ Upstream

**Goal**: Take both repos from diverged → fully in sync via two open PRs with passing CI.

See also:
- `/fork-merge-plan` — analysis only, produces a written plan without executing
- `/git-worktrees` — isolate the merge in a worktree when there are many conflicts

---

## Variables

```bash
FORK_REMOTE=origin                           # tstapler/stapler-squad
UPSTREAM_REMOTE=upstream-fanatics            # TylerStaplerAtFanatics/stapler-squad
FORK_REPO=tstapler/stapler-squad
UPSTREAM_REPO=TylerStaplerAtFanatics/stapler-squad
BRANCH=main
DATE=$(date +%Y%m%d)
MERGE_BRANCH="merge/upstream-$DATE"
```

---

## Step 1: Fetch Both Remotes

```bash
git fetch $FORK_REMOTE
git fetch $UPSTREAM_REMOTE
```

Confirm there is actual divergence — if one side is a fast-forward of the other, skip to Step 6 and just push directly.

```bash
git log $UPSTREAM_REMOTE/$BRANCH..$FORK_REMOTE/$BRANCH --oneline --no-merges | wc -l
git log $FORK_REMOTE/$BRANCH..$UPSTREAM_REMOTE/$BRANCH --oneline --no-merges | wc -l
```

---

## Step 2: Create Integration Branch

Always branch from the **fork** (`origin/main`) so the fork's features are parent-1:

```bash
git checkout -b $MERGE_BRANCH $FORK_REMOTE/$BRANCH
```

---

## Step 3: Merge Upstream

```bash
git config merge.conflictstyle diff3
git merge --no-ff $UPSTREAM_REMOTE/$BRANCH
```

---

## Step 4: Resolve Conflicts

### Benchmark baselines — always take upstream

```bash
git checkout --theirs -- benchmarks/
git add benchmarks/
```

### Registry JSON files — always take ours (fork has populated content)

The upstream periodically empties `docs/registry/features/backend/*.json` files during sync merge resolutions. The fork always has the authoritative populated content.

```bash
git checkout --ours -- docs/registry/features/backend/
git add docs/registry/features/backend/
```

**Verify after**: confirm the upstream's new registry files (any that exist on upstream but not fork) are still staged as additions — `git checkout --ours` only touches files that were in conflict, not new additions.

### Source code conflicts

Read each conflicting source file and resolve manually. High-risk files (both sides made large changes) in this project:
- `session/tmux/control_mode.go`
- `session/tmux/tmux.go`
- `server/services/connectrpc_websocket.go`
- `server/services/session_service.go`

After resolving: `git add <file>`

Verify no remaining conflicts:
```bash
git diff --name-only --diff-filter=U
```

---

## Step 5: Commit and Verify

```bash
git commit  # uses auto-generated merge commit message; edit to summarize fork vs upstream additions
```

Run CI checks locally before pushing:
```bash
make build && make test && make lint
```

All three must pass. If any fail, fix and amend the merge commit before proceeding.

---

## Step 6: Push to Both Remotes

```bash
git push $FORK_REMOTE $MERGE_BRANCH
git push $UPSTREAM_REMOTE $MERGE_BRANCH
```

---

## Step 7: Open Two PRs

**PR 1 — Fork features → Upstream** (sends fork-only commits to the work repo):

```bash
gh pr create \
  --repo $UPSTREAM_REPO \
  --head "$MERGE_BRANCH" \
  --base main \
  --title "chore: sync personal fork → upstream ($DATE)" \
  --body "..."
```

PR body must list:
- What's new from the fork (features/fixes not yet in upstream)
- What was already in upstream and is being reconciled
- Conflict resolutions applied

**PR 2 — Upstream features → Fork** (sends upstream-only commits to the personal fork):

```bash
gh pr create \
  --repo $FORK_REPO \
  --head "$MERGE_BRANCH" \
  --base main \
  --title "chore: sync upstream → personal fork ($DATE)" \
  --body "..."
```

PR body must list:
- What's new from upstream
- Conflict resolutions applied

---

## Step 8: Monitor CI

Wait for both PRs' CI to go green before reporting done.

```bash
# Watch upstream PR
gh pr checks --repo $UPSTREAM_REPO <PR_NUMBER> --watch

# Watch fork PR
gh pr checks --repo $FORK_REPO <PR_NUMBER> --watch
```

If a check fails:
1. Read the failure log: `gh run view --repo <REPO> <RUN_ID> --log-failed`
2. Fix on the merge branch, push to both remotes — PRs update automatically
3. Wait for re-run

Do not merge either PR until both are green. The two PRs are a matched pair — merge order doesn't matter since they carry the same tip commit.

---

## Known Conflict Patterns for This Project

| Pattern | Cause | Resolution |
|---|---|---|
| All `docs/registry/features/backend/*.json` emptied on upstream | Prior sync merge resolved `lastModified` conflicts by emptying files | `git checkout --ours` — fork has populated content |
| Benchmark baseline files diverge | Each side runs benchmarks independently | `git checkout --theirs` — take upstream; regenerate locally after merge |
| `CLAUDE.md` install-service block | Fork uses more detailed wording | Keep fork's version (more detailed is better) |
| tmux/control_mode.go both-sides changes | Fork adds features, upstream adds perf fixes | Both sets of changes are in non-overlapping hunks; verify auto-merge |

---

## Post-Merge Checklist

After both PRs are merged:

- [ ] `origin/main` and `upstream-fanatics/main` point to the same commit (or are fast-forwards of each other)
- [ ] `make registry-aggregate` produces no empty files
- [ ] Benchmark baselines regenerated: `make benchmark-baseline`
- [ ] Delete the `merge/upstream-YYYYMMDD` branch from both remotes

```bash
git push $FORK_REMOTE --delete $MERGE_BRANCH
git push $UPSTREAM_REMOTE --delete $MERGE_BRANCH
```
