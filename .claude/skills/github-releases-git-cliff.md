---
name: github-releases-git-cliff
description: "Use this skill when setting up automated GitHub Releases with conventional-commit changelogs for any project. Covers git-cliff for changelog generation and softprops/action-gh-release for publishing. Tag-push trigger gives intentional control over release timing."
---

# GitHub Releases — git-cliff + action-gh-release

Intentional, tag-triggered releases with auto-generated changelogs. No bots opening PRs, no surprise releases.

## Why not release-please or semantic-release

- **semantic-release**: fires automatically on every merge to main — no intentional control
- **release-please**: Google GitHub App shut down August 2025; buggy `simple` strategy for non-JS projects; bot-PR model adds friction
- **changesets**: JS ecosystem only, requires changeset files per PR

## The pattern

```
git tag v0.3.0 && git push --tags
  → workflow triggers (tag push)
  → environment protection gate (manual approval if configured)
  → git-cliff generates changelog since previous tag
  → build / deploy steps receive APP_VERSION from the tag
  → softprops/action-gh-release publishes GitHub Release with changelog + assets
```

One trigger. Fully intentional. Works for any language.

## cliff.toml (repo root)

```toml
[changelog]
header = ""
body = """
{% for group, commits in commits | group_by(attribute="group") %}\
### {{ group | striptags | trim | upper_first }}
{% for commit in commits %}\
- {% if commit.breaking %}[**breaking**] {% endif %}{{ commit.message | upper_first }}
{% endfor %}
{% endfor %}\
"""
trim = true
footer = ""

[git]
conventional_commits = true
filter_unconventional = true
commit_parsers = [
  { message = "^feat", group = "Features" },
  { message = "^fix", group = "Bug Fixes" },
  { message = "^perf", group = "Performance" },
  { message = "^refactor", group = "Refactoring" },
  { message = "^ci", group = "CI/CD" },
  { message = "^chore\\(deps\\)", group = "Dependencies" },
  { message = "^chore", skip = true },
  { message = "^docs", skip = true },
  { message = "^style", skip = true },
  { message = "^test", skip = true },
]
filter_commits = true
tag_pattern = "v[0-9]*\\.[0-9]*\\.[0-9]*"
sort_commits = "oldest"
```

## Workflow skeleton

```yaml
on:
  push:
    tags:
      - 'v[0-9]+.[0-9]+.[0-9]+'

permissions:
  contents: write  # required for action-gh-release

jobs:
  release:
    runs-on: ubuntu-22.04
    environment: production  # optional: add approval gate here

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # git-cliff needs full history to find previous tag

      - name: Resolve version from tag
        run: |
          APP_VERSION="${{ github.ref_name }}"
          APP_VERSION="${APP_VERSION#v}"   # strip leading 'v'
          echo "APP_VERSION=${APP_VERSION}" >> $GITHUB_ENV

      - name: Generate changelog
        uses: orhun/git-cliff-action@v4
        id: cliff
        with:
          config: cliff.toml
          args: --latest --strip header
        env:
          OUTPUT: CHANGELOG_BODY.md

      # ... your build steps here, using $APP_VERSION ...

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ github.ref_name }}
          name: ${{ github.ref_name }}
          body_path: CHANGELOG_BODY.md
          files: path/to/build/artifact.apk   # optional: attach binaries
```

## Android packed-semver integration

When combining with the [[Android Versioning (Packed SemVer)]] scheme, pass the version to Gradle:

```yaml
- run: ./gradlew assembleRelease -PappVersion="$APP_VERSION" --no-daemon
```

Gradle reads it and computes `versionCode = major*1_000_000 + minor*1_000 + patch`.

## Firebase App Distribution release notes

git-cliff output → trim to scannable length → write to `release-notes.txt`:

```yaml
- name: Write Firebase release notes
  run: |
    { echo "v${APP_VERSION} · $(date -u '+%Y-%m-%d')"; echo ""; head -c 500 CHANGELOG_BODY.md; } \
      > androidApp/release-notes.txt
```

## Release workflow

```bash
# Cut a release
git tag v0.3.0 && git push --tags

# Fix a bad tag before the workflow runs
git tag -d v0.3.0 && git push --delete origin v0.3.0
git tag v0.3.0 && git push --tags

# Bump minor/major — just use a higher tag
git tag v0.4.0 && git push --tags
```

No VERSION file to edit, no PRs to merge. The tag is the release.

## Commit message convention (required)

git-cliff only includes commits that match `commit_parsers`. Use:

| Prefix | Appears in changelog |
|---|---|
| `feat:` | Features |
| `fix:` | Bug Fixes |
| `perf:` | Performance |
| `refactor:` | Refactoring |
| `ci:` | CI/CD |
| `chore(deps):` | Dependencies |
| `chore:`, `docs:`, `style:`, `test:` | skipped (internal) |

## Key actions

- `orhun/git-cliff-action@v4` — official Action for git-cliff
- `softprops/action-gh-release@v2` — creates GitHub Release with body + file assets
- Both are actively maintained (2026)

## Used in

- [[Sortie]] — Android + Web KMP app, adopted 2026-07-06
- [[SteleKit]] — packed semver scheme origin
