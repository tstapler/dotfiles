# Advanced Stack Operations

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

## After Squash-Merge (most common GitHub config)

The merged branch's local SHA won't match the squash commit on main. Remove it cleanly:

```bash
git fetch origin
git machete slide-out --no-rebase feat/JIRA-123-db-schema
git machete traverse -WH          # rebase remaining stack onto main, update PR bases
```
