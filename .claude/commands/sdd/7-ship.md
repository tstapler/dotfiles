---
description: "Phase 7 — Prepare and open the PR."
user-invocable: true
---

# sdd:7-ship

Prepare the PR description and open it.

## HARD GATE

Only run this after `/sdd:6-verify` has produced a ✅ PASS verdict. If you skipped verification, run it now.

## Instructions

1. **Follow [SETUP.md](../skills/SETUP.md)** — identify PROJECT_NAME.

2. **Draft the PR description:**

```markdown
## Summary
[2-3 sentences: what this PR does and why it matters]

## Context
[Problem solved, motivation, issue/ticket link]

## Changes
- **<Component A>**: <specific changes>
- **<Component B>**: <specific changes>
- **Tests**: <test coverage added>

## Impact
- **Scope**: <what parts of the system are affected>
- **Breaking Changes**: <none, or list explicitly>
- **Performance**: <improvements, regressions, or neutral>
- **Dependencies**: <new or updated>

## Testing
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Manual verification: <steps>

## Reviewer Notes
- **Focus areas**: <risky areas, design decisions>
- **Known limitations**: <intentional trade-offs>
- **Follow-up tasks**: <deferred work>

## Related
- Closes <issue> (if linked in requirements.md)
```

3. **Present integration options** using `AskUserQuestion`:
   ```
   header: "Ship method"
   question: "How would you like to proceed?"
   options:
     - label: "Open a PR now (recommended)"
       description: "Push branch and create a GitHub PR with the drafted description"
     - label: "Keep branch for more work"
       description: "Leave the branch as-is — no PR yet"
     - label: "Merge locally"
       description: "Merge directly if you have permissions (no PR)"
     - label: "Discard changes"
       description: "Reset — abandon this branch"
   ```

4. **For option A**: create the PR using `gh pr create` with a body file so multi-line Markdown is preserved:
   ```bash
   cat > /tmp/pr-description.md <<'EOF'
   <PR description>
   EOF
   gh pr create --title "<type>(<scope>): <description>" --body-file /tmp/pr-description.md
   ```
   Return the PR URL.

5. **Clean up worktree** (if this feature was developed in a git worktree):
   ```bash
   git worktree remove <path> --force
   ```
   Ask for confirmation before removing.
