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

## Step 0: Save State and Record Original Branch

Before touching git, capture where we are so we can resume if interrupted and
return cleanly when done. The state file is keyed on the HEAD commit at
invocation time, making it unique per sync run.

```bash
INVOCATION_COMMIT=$(git rev-parse --short HEAD)
STATE_FILE="/tmp/sync-remotes-${INVOCATION_COMMIT}.env"

# Capture current branch (or detached-HEAD ref as fallback)
ORIGINAL_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || git rev-parse --short HEAD)

cat > "$STATE_FILE" <<EOF
ORIGINAL_BRANCH=$ORIGINAL_BRANCH
MERGE_BRANCH=$MERGE_BRANCH
INVOCATION_COMMIT=$INVOCATION_COMMIT
DATE=$DATE
STEP_COMPLETED=0
FORK_PR=
UPSTREAM_PR=
EOF

echo "State file: $STATE_FILE"
echo "Will return to branch: $ORIGINAL_BRANCH"
```

After every completed step, update `STEP_COMPLETED` in the state file:

```bash
# Template — replace N with the step number just finished
sed -i "s/^STEP_COMPLETED=.*/STEP_COMPLETED=N/" "$STATE_FILE"
```

---

## Resuming a Paused Sync

If a previous run was interrupted, find and source its state file before continuing:

```bash
# List any active state files
ls /tmp/sync-remotes-*.env 2>/dev/null

# Source the one you want to resume
source /tmp/sync-remotes-<INVOCATION_COMMIT>.env
echo "Resuming from step $STEP_COMPLETED, merge branch: $MERGE_BRANCH"

# Jump to the merge branch if not already there
git checkout $MERGE_BRANCH
```

Pick up at the step after `STEP_COMPLETED`.

---

> For analyzing divergence and producing a written plan before executing, apply the `fork-merge-plan` skill.

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

```bash
sed -i "s/^STEP_COMPLETED=.*/STEP_COMPLETED=1/" "$STATE_FILE"
```

---

## Step 2: Create Integration Branch

Always branch from the **fork** (`origin/main`) so the fork's features are parent-1:

```bash
git checkout -b $MERGE_BRANCH $FORK_REMOTE/$BRANCH
sed -i "s/^STEP_COMPLETED=.*/STEP_COMPLETED=2/" "$STATE_FILE"
```

---

## Step 3: Merge Upstream

```bash
git config merge.conflictstyle diff3
git merge --no-ff $UPSTREAM_REMOTE/$BRANCH
sed -i "s/^STEP_COMPLETED=.*/STEP_COMPLETED=3/" "$STATE_FILE"
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

```bash
sed -i "s/^STEP_COMPLETED=.*/STEP_COMPLETED=4/" "$STATE_FILE"
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

```bash
sed -i "s/^STEP_COMPLETED=.*/STEP_COMPLETED=5/" "$STATE_FILE"
```

---

## Step 6: Push to Both Remotes

```bash
git push $FORK_REMOTE $MERGE_BRANCH
git push $UPSTREAM_REMOTE $MERGE_BRANCH
sed -i "s/^STEP_COMPLETED=.*/STEP_COMPLETED=6/" "$STATE_FILE"
```

### Push failures and cross-repo PR quirks

If the push to `$UPSTREAM_REMOTE` fails with `RPC failed; HTTP 500` (a server-side pack size limit, hit when the merge branch adds ~100+ commits at once), or if `gh pr create --head owner:branch` fails with "Head sha can't be blank" (the fork and upstream are independent repos, not a GitHub fork pair — push to the target remote first, then open the PR without `--head`), see [Push Troubleshooting](references/push-troubleshooting.md) for the batch-push workaround and full explanation.

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

After both PRs are open, record their numbers in the state file:

```bash
sed -i "s/^FORK_PR=.*/FORK_PR=<NUMBER>/" "$STATE_FILE"
sed -i "s/^UPSTREAM_PR=.*/UPSTREAM_PR=<NUMBER>/" "$STATE_FILE"
sed -i "s/^STEP_COMPLETED=.*/STEP_COMPLETED=7/" "$STATE_FILE"
```

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

```bash
sed -i "s/^STEP_COMPLETED=.*/STEP_COMPLETED=8/" "$STATE_FILE"
```

---

## Step 9: Return to Original Branch

Once both PRs are merged and the sync is complete, return to wherever the user
was before the sync started and clean up the state file.

```bash
git checkout $ORIGINAL_BRANCH
echo "Returned to $ORIGINAL_BRANCH"
rm "$STATE_FILE"
echo "State file removed."
```

---

## Known Conflict Patterns for This Project

See [Push Troubleshooting](references/push-troubleshooting.md#known-conflict-patterns-for-this-project) for the quick-lookup table of recurring conflict patterns (registry JSON, benchmark baselines, `CLAUDE.md`, tmux/control_mode.go, HTTP 500 on push) and their resolutions.

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `github-pr` | Create and manage the two sync PRs after pushing the integration branch |
| `github-actions-debugging` | Debug CI failures on the merge branch before merging |
| `git-worktrees` | Isolate the merge in a worktree when there are many conflicts |
| `code-debugging` | Investigate test failures introduced by the merge |

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
