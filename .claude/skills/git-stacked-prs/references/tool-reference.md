# Tool Selection and Command Reference

## Tool Selection

**git-machete** is the default — free, MIT licensed, actively maintained (v3.43.1, June 2026). Ships an official Claude Code skill:
```bash
gh skill install VirtusLab/git-machete git-machete --scope user --agent claude-code
```

**gh stack** — GitHub's native stacking (private preview, waitlist as of June 2026). The right long-term answer: handles squash cleanup, auto-PR-base updates, merge queue, and server-side "Rebase Stack" button. Monitor for GA.

**Graphite** (`gt`) — full platform (CLI + web UI + merge queue). The upstream open-source CLI was archived July 2023; the community fork (freephite) is single-maintainer. Not recommended for teams.

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

### Raw git (no extra tools, git ≥2.38)
```bash
# Cascade rebase the whole stack in one command (set permanently: git config rebase.updateRefs true):
git rebase --update-refs main

# Force-push all branches:
git push --force-with-lease origin feat/layer-1 feat/layer-2 feat/layer-3
```

Note: `--update-refs` only updates local branch pointers. It does NOT retarget GitHub PR bases — you still need `gh pr edit --base` per PR after pushing. Use as a supplement to git-machete, not a replacement.
