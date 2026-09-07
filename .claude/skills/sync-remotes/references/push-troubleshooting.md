# Push Troubleshooting (Step 6 / Step 7 edge cases)

Detail supporting Step 6 (Push to Both Remotes) and Step 7 (Open Two PRs) of the
main `SKILL.md` workflow.

## Known Conflict Patterns for This Project

| Pattern | Cause | Resolution |
|---|---|---|
| All `docs/registry/features/backend/*.json` emptied on upstream | Prior sync merge resolved `lastModified` conflicts by emptying files | `git checkout --ours` — fork has populated content |
| Benchmark baseline files diverge | Each side runs benchmarks independently | `git checkout --theirs` — take upstream; regenerate locally after merge |
| `CLAUDE.md` install-service block | Fork uses more detailed wording | Keep fork's version (more detailed is better) |
| tmux/control_mode.go both-sides changes | Fork adds features, upstream adds perf fixes | Both sets of changes are in non-overlapping hunks; verify auto-merge |
| HTTP 500 on `git push $UPSTREAM_REMOTE` | Server-side pack size limit (~100+ new commits at once); `http.postBuffer` doesn't help | Batch-push via tmp branches — see the workaround above |

## HTTP 500 on large push (batch-push workaround)

If `git push $UPSTREAM_REMOTE` fails with `RPC failed; HTTP 500` and `unexpected disconnect while reading sideband packet`, the server's pack size limit has been hit. This happens when the merge branch adds many commits at once (~100+ vs the remote's tip). `http.postBuffer` is a client-side buffer and does **not** help — the limit is enforced server-side.

**Fix: push in batches using temporary branches to pre-warm the object store.**

1. Find the midpoint and two-thirds-point commits between the remote's current tip and your HEAD:
   ```bash
   REMOTE_TIP=$(git ls-remote $UPSTREAM_REMOTE refs/heads/main | awk '{print $1}')
   TOTAL=$(git log --oneline $REMOTE_TIP..HEAD | wc -l)
   BATCH1=$(git log --oneline $REMOTE_TIP..HEAD | tail -n $(( TOTAL / 3 )) | head -1 | awk '{print $1}')
   BATCH2=$(git log --oneline $REMOTE_TIP..HEAD | tail -n $(( 2 * TOTAL / 3 )) | head -1 | awk '{print $1}')
   ```

2. Push the batches as tmp branches (small deltas — each succeeds individually):
   ```bash
   git push $UPSTREAM_REMOTE $BATCH1:refs/heads/tmp/batch1
   git push $UPSTREAM_REMOTE $BATCH2:refs/heads/tmp/batch2
   ```

3. Now push the real branch (remote already has most objects — delta is tiny):
   ```bash
   git push $UPSTREAM_REMOTE $MERGE_BRANCH
   ```

4. Clean up the tmp branches:
   ```bash
   git push $UPSTREAM_REMOTE --delete tmp/batch1
   git push $UPSTREAM_REMOTE --delete tmp/batch2
   ```

## SSH remote doesn't bypass the limit

If `git remote get-url $UPSTREAM_REMOTE` shows `https://`, switching to an SSH remote will not help if the gitconfig contains:

```
[url "https://github.com/"]
    insteadOf = git@github.com:
```

This global rewrite silently converts SSH URLs back to HTTPS. The push goes over the same endpoint either way. The batch-push workaround is the correct fix regardless of URL scheme.

## Non-fork cross-repo PRs

The personal fork (`tstapler/stapler-squad`) and work repo (`TylerStaplerAtFanatics/stapler-squad`) are **independent GitHub repos**, not a GitHub fork pair. This means:
- `gh pr create --head "tstapler:branch" --repo TylerStaplerAtFanatics/...` fails ("Head sha can't be blank") because GitHub can't resolve cross-repo head refs between unrelated repos.
- The branch must be pushed to the **target remote** first. Then open the PR without `--head owner:branch`.
