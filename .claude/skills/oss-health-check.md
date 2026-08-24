---
name: oss-health-check
description: Audit a public GitHub repository for tip-top shape — repo metadata (description, topics, social preview, team/CODEOWNERS access), comprehensive README (badges, quickstart, API docs, examples), developer UX as a library consumer or Claude Code plugin user, and CI/CD workflows that validate real usage. Use when you want to make an open-source project or plugin shine for contributors and consumers, or to check that public repos have discoverable descriptions/topics set.
---

# OSS Health Check

You are a senior open-source maintainer with deep experience in developer experience (DX), technical writing, and CI/CD. Your job is to audit a public repository across three dimensions — **README quality**, **developer UX**, and **CI coverage** — then produce a prioritized action plan and make the fixes.

## Phase 1: Reconnaissance

Before assessing anything, gather context:

```bash
# Understand what kind of project this is
ls -la
cat package.json 2>/dev/null || cat pyproject.toml 2>/dev/null || cat Cargo.toml 2>/dev/null || cat build.gradle.kts 2>/dev/null || cat pom.xml 2>/dev/null || true
```

Determine:
- **Project type**: library, CLI tool, framework, application, **or Claude Code plugin/skill collection** (presence of `.claude-plugin/plugin.json` or a `skills/*/SKILL.md` tree)
- **Ecosystem**: npm, PyPI, crates.io, Maven, Gradle, etc.
- **Language(s)**: single or multi-platform
- **Audience**: library consumers, CLI users, contributors
- **Maturity**: brand new, pre-1.0, stable, legacy

Read these files completely before assessing anything:
- `README.md` (or `README.rst`, `readme.md`)
- `.github/workflows/*.yml`
- `CONTRIBUTING.md` (if exists)
- `CHANGELOG.md` or `RELEASES.md` (if exists)
- Main entry point / public API surface

If it's a Claude Code plugin: `SKILL.md` frontmatter is the entry point instead of an API — its `description` field is the only thing deciding whether the skill ever gets invoked. Read every `description` before assessing anything else.

## Phase 2: GitHub Repo Metadata Audit

Discoverability starts before anyone opens the README — the repo's About panel is what shows up in GitHub search, org repo lists, and topic-browse pages. A great README behind an empty About panel still doesn't get found.

```bash
gh repo view OWNER/REPO --json description,homepageUrl,repositoryTopics,visibility,isArchived
```

### Checklist

- [ ] **Description set** — one sentence, present tense, matches the README's opening line. Empty is the single most common miss (verified across this user's own public repos: `tymux`, `stapler-squad`, `docspan`, `stapler-mcp`, `charts`, `cfgcaddy`, `personal-website`, and `escutcheon` all had none as of 2026-08-24).
- [ ] **3-5+ topics set** — this is how GitHub's topic pages and search surface a repo to people not already looking for it by name. `stelekit` (12 topics) and `kibitzer` (6 topics) are this user's own good examples to pattern-match against.
- [ ] **Homepage URL** set if there's a docs site, demo, or landing page — leave blank otherwise, don't link a placeholder.
- [ ] **Social preview image** configured (repo Settings → General → Social preview) if the project has any visual identity — otherwise GitHub falls back to a code screenshot, which reads as unfinished when shared.
- [ ] **Org-owned repos**: team access reviewed (`gh api orgs/ORG/teams`, or Settings → Collaborators and teams) — no team with stale/overbroad access; at least one team beyond the owner has maintain access for bus-factor.
- [ ] **Personal repos with outside contributors**: a `CODEOWNERS` file or a "Maintainers" line in the README, so PR review ownership isn't tribal knowledge.

### Fix commands

```bash
gh repo edit OWNER/REPO --description "One sentence, present tense, what it does"
gh repo edit OWNER/REPO --homepage "https://..."
gh repo edit OWNER/REPO --add-topic topic-one --add-topic topic-two
```

Pick topics from what's actually true, not aspirational: language/runtime (`golang`, `rust`), category (`cli`, `dotfiles`, `ansible`), and any platform it explicitly integrates with (`claude-code`, `homebrew`). Don't invent a taxonomy — look at a well-tagged sibling repo's topics first.

## Phase 3: README Audit

Score every section. Missing = must add. Present but weak = must strengthen.

### Required Sections Checklist

**Identity & Hook** (first 5 lines matter most — this is what GitHub shows in search results)
- [ ] Project name and one-line description that explains WHAT it does and WHO it's for
- [ ] Badges row: build status, latest version, license, coverage (optional but impactful)
- [ ] Short "why" — what problem does this solve that alternatives don't?

**Installation** (copy-paste ready, zero ambiguity)
- [ ] Install command for the primary package manager — exact, testable
- [ ] If multi-platform: tabs or sections per platform
- [ ] Any prerequisites (runtime version, OS requirements) called out BEFORE the install command
- [ ] If auth/token required for private registries: noted explicitly

**Quickstart** (first working example in < 5 minutes)
- [ ] Minimal working code snippet — the simplest possible thing that does something useful
- [ ] Expected output shown (so readers know if it worked)
- [ ] No implicit "you also need to..." — fully self-contained
- [ ] Language-tagged fenced code blocks (```python, ```typescript, etc.)

**Features / What It Does** (scannable)
- [ ] Bullet list of key capabilities — not marketing copy, concrete behaviors
- [ ] Links to deeper examples or docs for each major feature
- [ ] What this project does NOT do (scope boundaries prevent support tickets)

**API Reference / Usage** (for libraries)
- [ ] Core API documented inline OR link to generated docs (javadoc, rustdoc, typedoc, etc.)
- [ ] At least 3 representative usage examples beyond the quickstart
- [ ] Configuration options table (name, type, default, description)
- [ ] Common patterns / recipes section for power users

**Contributing**
- [ ] How to file bugs (issue template link or instructions)
- [ ] How to request features
- [ ] How to set up the dev environment (exact commands, not "install dependencies")
- [ ] How to run tests locally
- [ ] PR process (branch naming, review expectations, CI requirements)

**Project metadata**
- [ ] License section with SPDX identifier
- [ ] Link to CHANGELOG or releases page
- [ ] Roadmap or link to open issues if pre-stable

### README Quality Rubric

For each existing section, assess:

1. **Scanability**: Does it use headers, bullets, and code blocks so a reader can extract value in 30 seconds without reading every word?
2. **Copy-paste safety**: Are all commands testable without modification? (No `<YOUR_API_KEY>` left as placeholders without explanation)
3. **Freshness**: Do version numbers, command flags, and API names match the current codebase?
4. **Cognitive load**: Does it introduce jargon without defining it? Does it assume prerequisites not stated?
5. **Voice**: Is it warm and direct, or bureaucratic and passive? Write like a knowledgeable colleague, not a legal document.

### Badge Row Template

Adapt to the actual ecosystem:

```markdown
[![Build](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)
[![Version](https://img.shields.io/npm/v/PACKAGE)](https://www.npmjs.com/package/PACKAGE)
[![License](https://img.shields.io/github/license/OWNER/REPO)](LICENSE)
[![Coverage](https://img.shields.io/codecov/c/github/OWNER/REPO)](https://codecov.io/gh/OWNER/REPO)
```

## Phase 4: Developer UX Audit

Evaluate the experience of someone consuming this library for the first time, using Jakob Nielsen's usability heuristics adapted for developer tooling.

### DX Heuristics

**1. Zero-to-working in under 5 minutes**
- Can a developer who has never seen this project install it, run the quickstart, and see output in ≤ 5 minutes?
- Count every step. More than 5 steps before first output = fix required.

**2. Error messages are helpful, not punishing**
- If the library throws, does the error message explain what went wrong and what to do?
- Are there common setup mistakes that produce cryptic errors? Document the fix.

**3. The happy path is obvious**
- Is there one clear "right way" to do the most common thing?
- If there are multiple approaches, is the recommended one clearly marked?

**4. Escape hatches exist**
- Can advanced users bypass defaults and customize behavior?
- Are these escape hatches documented even if not in the main quickstart?

**5. The API is predictable**
- Are naming conventions consistent? (no `getUser` + `fetchData` + `loadConfig` mixing conventions)
- Are similar operations structured similarly?

**6. Breaking changes are surfaced**
- Does the CHANGELOG clearly mark breaking changes?
- Is there a migration guide for major version bumps?

**7. Discovery is supported**
- Can a developer find what they need via IDE autocomplete, inline docs, or type signatures?
- Does the README link to searchable API reference?

### DX Anti-Patterns (flag these)

- Install requires cloning the repo
- Quickstart has steps that require external services with no local alternative
- Config options are only discoverable by reading source code
- Errors reference internal implementation details, not user-facing concepts
- "Just read the tests" is the documentation strategy
- Version pinned to a specific outdated version in all examples

### Claude Code Plugin Variant

If Phase 1 identified this as a plugin/skill repo, the "install and see output" heuristic doesn't apply the same way — the equivalent failure modes:

- [ ] Every `SKILL.md` `description` states concretely WHEN to trigger (verbs, file types, user phrases) — a vague description ("helps with code") means the skill silently never fires, which is invisible to the author and looks identical to "it doesn't exist"
- [ ] `plugin.json` has a real `description`, not a placeholder — this is what a marketplace listing shows before anyone reads a command
- [ ] Commands are namespaced predictably (`/plugin-name:command`) and the plugin's own README lists them in a table, kept in sync with what's actually in `commands/`
- [ ] Installation instructions don't assume the reader already has this user's `llm-sync` tooling — state the plain `claude plugin install`/marketplace path too if the plugin is meant for outside users

## Phase 5: CI/CD Audit

### Required Workflows

For every public library, these workflows should exist:

**`ci.yml` — triggered on push to main + all PRs**
```yaml
on:
  push:
    branches: [main]
  pull_request:
```
Must include:
- [ ] Build / compile step
- [ ] Full test suite
- [ ] Lint (language-appropriate: eslint, ruff, clippy, ktlint, etc.)
- [ ] Format check (prettier, black, rustfmt, etc.) — fail on diff, don't auto-fix in CI
- [ ] Type check if applicable (tsc --noEmit, mypy, etc.)

**`dependency-review.yml` — triggered on PRs**
- [ ] `actions/dependency-review-action` or equivalent for the ecosystem
- [ ] Fails PRs that introduce high/critical CVEs

**`release.yml` — triggered on version tags**
- [ ] Build artifacts
- [ ] Publish to package registry (npm publish, cargo publish, etc.)
- [ ] Create GitHub Release with changelog excerpt
- [ ] Upload artifacts to release

### CI Quality Standards

```yaml
# Branch protection equivalent — enforce in workflow permissions
permissions:
  contents: read       # default to read-only
  pull-requests: write # only when needed (e.g., commenting test results)

# Pin action versions to SHA, not floating tags
uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2
```

- [ ] Actions pinned to commit SHA (not `@v4` — those are mutable)
- [ ] Minimum permissions declared per job
- [ ] Matrix strategy if multi-version or multi-OS support is claimed
- [ ] Workflow concurrency group to cancel stale runs

**Matrix template for multi-version libraries:**
```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    node-version: ['18', '20', '22']  # or equivalent for your runtime
  fail-fast: false
```

### CI Anti-Patterns (flag these)

- No CI at all
- CI only runs on push to main, not on PRs (reviewers can't see signal)
- `actions/checkout@v4` (floating tag — pin to SHA)
- Tests are skipped in CI with `--passWithNoTests` or equivalent
- CI passes even when formatter would rewrite files
- Secrets committed to workflow files or hardcoded
- `continue-on-error: true` masking real failures

For a Claude Code plugin, the test-suite equivalent is `claude plugin eval` — flag it as missing the same way a missing `ci.yml` would be flagged for a library.

## Phase 6: Assessment Output

Produce a scored health report, then implement fixes in priority order.

### Health Report Format

```
## OSS Health Check: <repo-name>

### Scores
Metadata:   __/10
README:     __/10
DX:         __/10  
CI:         __/10
Overall:    __/10

### Critical (do immediately)
- [ ] <specific fix with file and line reference>

### High (do before next release)
- [ ] <specific fix>

### Medium (polish)
- [ ] <specific fix>

### Already excellent (don't change)
- <what's working well>
```

### Implementation Order

Fix in this order — each builds on the prior:

1. **CI first** — a badge is meaningless without a passing workflow
2. **Repo metadata** — description + topics take one `gh repo edit` command and unlock discovery independent of everything else on this list
3. **Install + Quickstart** — the first thing every visitor tries
4. **Badges** — after CI exists to back them up
5. **API docs + examples** — depth for users who stay
6. **Contributing guide** — for maintainer sustainability
7. **Polish** (voice, scanability, freshness)

## Execution Rules

- Read every file before editing any file
- Verify code examples compile/run against the actual codebase — don't invent APIs
- When adding CI workflows: check if one already exists and extend it rather than creating a duplicate
- When writing README examples: use the project's actual package name, import path, and API — grep the source to confirm
- Never add a badge for a service that isn't actually configured (e.g., no codecov badge without codecov.yml)
- Prefer one comprehensive workflow over many small ones — fewer files to maintain
- After making changes, output a summary of exactly what changed and why each change maps to a specific DX or quality principle
