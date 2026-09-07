---
name: gha-pin-actions
description: Pin GitHub Actions workflow refs from floating tags (@v4) to full commit SHAs, add a Renovate config to keep them updated automatically, and wire a ratchet lint check into CI. Use when setting up a new repo, auditing an existing one, or after adding new workflow steps that reference unpinned actions.
---

# GitHub Actions SHA Pinning

Floating tags like `@v4` are mutable — a compromised upstream repo can silently swap what they point to. SHA pinning (`@<40-char-sha>`) locks the exact bytes you reviewed. Renovate then opens PRs when upstream cuts new releases, so you stay current without losing the security guarantee.

## The stack

| Tool | Role |
|---|---|
| [`ratchet`](https://github.com/sethvargo/ratchet) | CLI: pin, update, upgrade, lint, unpin |
| [Renovate](https://github.com/apps/renovate) | Auto-opens PRs when actions release new versions |
| [`actionlint`](https://github.com/rhysd/actionlint) | Static linter for workflow syntax (complementary) |

**Do not use Dependabot** for SHA-pinned workflows — it operates at the tag level and cannot update SHA-pinned refs. Pick Renovate.

---

## Step 1: Install ratchet

```bash
brew install ratchet
# or
go install github.com/sethvargo/ratchet@latest
```

ratchet calls the GitHub API to resolve tags → SHAs, so set a token to avoid rate limits:

```bash
export GITHUB_TOKEN=$(gh auth token)
```

---

## Step 2: Pin all workflow files (one-time)

```bash
# Pin in place — overwrites files
ratchet pin .github/workflows/*.yml

# Verify nothing was missed
ratchet lint .github/workflows/*.yml
```

Before/after for a single action:

```yaml
# Before
uses: actions/checkout@v4

# After
uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # ratchet:actions/checkout@v4
```

ratchet records the original tag in a `# ratchet:<owner>/<action>@<tag>` comment so it knows what version constraint to honor when updating later. Renovate also understands this comment format.

**Gotcha — indentation**: ratchet rewrites all YAML indentation to 2 spaces. If your files use 4-space indent, commit the reformat as a separate "chore: normalize workflow indentation" commit before the pin commit so reviewers can diff them independently.

**Gotcha — matrix variables**: ratchet cannot resolve interpolated refs:
```yaml
uses: some/action@${{ matrix.version }}  # ratchet cannot pin this
```
Add `# ratchet:exclude` on that line to suppress the warning:
```yaml
uses: some/action@${{ matrix.version }}  # ratchet:exclude
```

---

## Step 3: Add ratchet lint to CI

Catches any newly added unpinned refs before they merge:

```yaml
- name: Lint pinned actions
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: |
    go install github.com/sethvargo/ratchet@latest
    ratchet lint .github/workflows/*.yml
```

Or use the pre-built container to avoid the install step:

```yaml
- name: Lint pinned actions
  uses: docker://ghcr.io/sethvargo/ratchet:latest
  with:
    args: lint .github/workflows/*.yml
```

---

## Step 4: Configure Renovate for automatic updates

Install the [Renovate GitHub App](https://github.com/apps/renovate) on your repo, then add `renovate.json`:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "config:recommended",
    "helpers:pinGitHubActionDigests"
  ],
  "github-actions": {
    "enabled": true
  }
}
```

`helpers:pinGitHubActionDigests` tells Renovate to:
1. Convert any remaining floating tags to SHA refs (belt-and-suspenders alongside ratchet)
2. Open a PR whenever an action releases a new version — the PR updates both the SHA and the version comment
3. Respect `# ratchet:exclude` lines and leave them alone

Renovate PRs look like:
```
chore(deps): update actions/checkout digest to abc1234  # v4.2.2 → v4.3.0
```

---

## Manual operations

```bash
# Update pinned SHAs to the latest commit matching the current version constraint
# (e.g. v4.2.1 → v4.2.2, stays on v4)
ratchet update .github/workflows/ci.yml

# Upgrade to a new major/minor version AND update the SHA
# (e.g. v4 → v5 — use when you want to bump the constraint itself)
ratchet upgrade .github/workflows/ci.yml

# Temporarily restore readable tags (useful when you need to diff a big action update)
ratchet unpin .github/workflows/ci.yml
# ... review ...
ratchet pin .github/workflows/ci.yml
```

---

## Handling Renovate PRs

When Renovate opens an update PR:

1. Check the action's changelog for the version bump (Renovate links it in the PR body)
2. If the change is safe, approve and merge — CI validates the new SHA
3. If you want to skip a version: close the PR and add the version to `ignoreDeps` or `packageRules` in `renovate.json`

```json
{
  "packageRules": [
    {
      "matchPackageNames": ["actions/upload-artifact"],
      "allowedVersions": "<5"
    }
  ]
}
```

---

## Checklist for a new repo

- [ ] `brew install ratchet` + `export GITHUB_TOKEN=$(gh auth token)`
- [ ] `ratchet pin .github/workflows/*.yml` — commit as "chore: pin action SHAs"
- [ ] `ratchet lint .github/workflows/*.yml` — confirm clean
- [ ] Add `ratchet lint` step to CI
- [ ] Add `renovate.json` with `helpers:pinGitHubActionDigests` — commit as "chore: add Renovate for action updates"
- [ ] Confirm Renovate app is installed on the repo (check Settings → GitHub Apps)

## Checklist for an existing repo audit

- [ ] Run `ratchet lint .github/workflows/*.yml` — note which files have unpinned refs
- [ ] `ratchet pin .github/workflows/*.yml` — pin them all
- [ ] Add `ratchet lint` to CI so the gate holds
- [ ] Add or update `renovate.json`
