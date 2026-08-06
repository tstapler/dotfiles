---
name: code-hotspot-analysis
description: Ground architecture/refactoring reviews in tool-generated evidence instead of code-reading alone — static coupling graphs (package dependency, call graph, struct/interface size) plus temporal coupling (files that change together in git history, independent of imports) combined into a complexity × churn hotspot score. The open-source technique behind CodeScene. Use before `architecture-review`/`find-refactor-candidates` to find WHERE to look; use those commands to analyze WHY once you're there.
---

# Code Hotspot & Coupling Analysis

CodeScene's core insight, stated plainly: **complexity alone doesn't predict maintenance pain, and churn alone doesn't either — but complexity × churn does.** A gnarly 2000-line file nobody has touched in two years is a museum piece, not a risk. A simple 50-line file that changes in every other commit is fine. A complex file that changes constantly is where incidents come from. CodeScene is a commercial product; this skill documents the same technique with open-source tooling, primarily for Go codebases (with pointers for other languages).

This is a **prioritization** tool, not a judgment tool. It tells you where to point `architecture-review`'s SOLID/DDD/Clean-Architecture analysis first. Running principle-checklists across an entire codebase uniformly wastes review effort on files nobody is actually struggling with.

## The Two Axes

### 1. Static structural coupling (what imports/references what, right now)

| Signal | Go tool | What it tells you |
|---|---|---|
| Package dependency graph | `goda graph` | Afferent coupling (who depends on this package — a chokepoint if too high), dependency cycles, direction violations against your own layering |
| Call graph | `go-callvis` | Visualizes which functions call which, clustered by package; a huge `.dot` file size for one package's focused graph is itself a density signal, even unrendered |
| Struct/interface size (UML-ish) | `goplantuml` | `.puml` class-diagram text for a package — the field/method list surfaces God Objects fast, even unrendered to an image |
| Complexity | `gocyclo`, `gocognit` | Cyclomatic and cognitive complexity per function — the "complexity" half of the hotspot score. Prefer cognitive complexity when ranking review-difficulty: it penalizes nesting depth, cyclomatic only counts branches, so two functions with equal cyclomatic complexity can differ wildly in how hard they actually are to hold in your head |
| Structural pattern queries | `ast-grep` (`sg`) | Anything a graph tool won't catch directly: largest structs by field count, functions with the most parameters (primitive-obsession signal — see `type-driven-design` skill), direct cross-package field access (`pkg.Thing.Field = x` from outside `pkg` — an encapsulation violation graph tools don't flag, and the single highest-value query below) |

Run all of these against the whole repo or a suspect package; save `dot`/`svg`/`.puml` output somewhere durable if the finding is worth referencing later (this repo's convention: `docs/architecture-audit-<date>.md` plus any generated artifacts alongside it).

**Working commands and gotchas actually hit running this stack** (Go 1.25, this repo):

```bash
# goda — the loov.dev vanity import path is currently broken (go.mod inside the module
# declares github.com/loov/goda, so `go install loov.dev/goda@latest` fails with a
# version-constraint conflict). Install the canonical path directly:
go install github.com/loov/goda@latest
goda graph "github.com/yourorg/yourrepo/..." > full-graph.dot

# Afferent coupling per package (who depends on this — high + business-logic package = chokepoint;
# high + leaf-utility package like a logging lib is healthy and expected):
goda list "incoming(github.com/yourorg/yourrepo/..., github.com/yourorg/yourrepo/somepkg)"

# Dependency-direction check — empty result means clean (no package in X imports anything in Y):
goda list "reach(session/..., server/...)"   # should be empty if session must not depend on server
goda list "reach(config,      session/...)"  # should be empty if config is a leaf

# go-callvis — default -algo=cha may fail on Go 1.25+ with:
#   "generic type alias requires GODEBUG=gotypesalias=1 or unset"
# from a transitive dependency using generic type aliases, and setting the GODEBUG var
# explicitly may not fix it (whole-program CHA analysis can hang instead of erroring, with
# no clear timeout, on a large codebase). Fall back to -algo=static (intraprocedural only,
# no whole-program call-graph resolution) — much faster, sufficient for a density signal:
go install github.com/ofabry/go-callvis@latest   # maintained fork; the original repo may not build
GODEBUG=gotypesalias=1 go-callvis -algo=static -format=dot \
  -focus=github.com/yourorg/yourrepo/somepkg \
  -group=pkg,type -limit=github.com/yourorg/yourrepo -nostd .

# gocyclo / gocognit — no gotchas, straightforward:
go install github.com/fzipp/gocyclo/cmd/gocyclo@latest
go install github.com/uudashr/gocognit/cmd/gocognit@latest
gocyclo -top 60 -avg .    # -avg prints the repo-wide average alongside the top-N — a
                          # healthy average (this repo's was 2.42) confirms outliers are
                          # genuine hotspots, not a systemic style problem
gocognit -top 40 .
# Exclude generated code from both (ORM/protobuf output is mechanically complex by
# construction and not a refactor target): pipe through grep -v on the generated paths,
# or pass those directories explicitly instead of `.` if your generator writes elsewhere.

# goplantuml — no gotchas; rendering to an image needs a local PlantUML jar/server, which
# is usually unavailable — the .puml text alone is sufficient evidence (line count of one
# class's entry in the .puml output correlates directly with that struct's field+method count):
go install github.com/jfeliu007/goplantuml/cmd/goplantuml@latest
goplantuml -recursive somepkg > somepkg.puml

# ast-grep — the four queries that found real findings in this repo, in order of value:
# (d) is almost always the highest-value one: it catches encapsulation violations no other
# tool here detects at all.
sg run --pattern 'type $NAME struct { $$$FIELDS }' --lang go --json=compact .   # (a) struct field counts — post-process JSON, count non-comment lines per struct body
sg run --pattern 'func $NAME($$$PARAMS) $$$RET { $$$ }' --lang go .            # (b) param counts — primitive-obsession signal
grep -rn "^func " --include="*.go" somepkg/*.go | grep -v _test.go | wc -l      # (c) exported-function density per file (a plain grep suffices; ast-grep is overkill here)
# (d) cross-package direct field mutation — the pattern that matters most:
grep -rn '\b\(instance\|inst\|sess\|session\)\.\w\+ = ' server/ daemon/ main.go \
  --include="*.go" | grep -v _test.go
# ^ tune the variable names/package paths to your own codebase's dominant aggregate type
# and the packages that shouldn't be reaching into it directly.
```

### 2. Temporal coupling (what changes together, in git history — independent of imports)

This is the half most reviews skip, and it's the one that finds coupling *static analysis structurally cannot see*: two files in unrelated packages that always change together because a feature spans both, with no import relationship connecting them. That's a missing abstraction boundary hiding in plain sight.

**Tool**: `code-maat` (https://github.com/adamtornhill/code-maat) — the actual open-source tool Adam Tornhill built before commercializing the same technique as CodeScene. It's a Clojure JAR that consumes `git log` output and computes coupling/hotspot/complexity-trend analyses directly.

**Fallback** (code-maat's Leiningen/Clojure setup can be finicky in a sandboxed environment): a short co-change script is a fine substitute for the core metric —

```bash
# For each pair of files, count commits that touched both, over a bounded window
git log --since="6 months ago" --name-only --pretty=format:'--%H--' \
  | awk '/^--/{if(NR>1)print ""; next} NF{print}' \
  # then group consecutive lines per commit and count co-occurring pairs
```
(a Python script pairing up each commit's changed-file list with `itertools.combinations` and a `Counter` is the simplest correct implementation — don't over-invest in a shell one-liner if the awk/sort pipeline gets unreadable)

**Hotspot score**: for each file, `(commit count touching it in the window) × (complexity proxy)`. Cyclomatic/cognitive complexity from `gocyclo`/`gocognit` is the real proxy if you have it; line count is an acceptable fallback. Rank descending — the top of this list is where bugs and slow PRs concentrate, regardless of what the static dependency graph says.

**Cross-check**: a file that is both a top hotspot AND already has multiple ADRs/design docs written about it (grep `docs/adr/`, `project_plans/*/requirements.md` for the filename) is a strong signal of a genuinely contested, high-churn architectural area — not a false positive.

### Working script (code-maat fallback)

`code-maat` itself is frequently impractical to stand up in a sandboxed/CI environment — its `nixpkgs` package can pull a 500+ MiB unrelated transitive closure (GTK/cairo/dbus, apparently from a shared build environment) with no cached jar, and it otherwise needs Leiningen/Clojure tooling that may not be installed. When that's the case, this self-contained script implements the same core algorithm code-maat's `coupling` analysis uses — used successfully on this repo's own 1000-commit window:

```python
#!/usr/bin/env python3
"""Temporal coupling + hotspot analysis — code-maat's coupling algorithm, self-contained.

Usage: python3 hotspot_analysis.py [--commits N] [--since "6 months ago"] [--max-files-per-commit 60]
Requires only stdlib + a git checkout; no network, no JVM.
"""
import argparse
import itertools
import subprocess
from collections import Counter, defaultdict

def get_commits(n=None, since=None):
    """Returns list of (commit_hash, [changed_files]) tuples, newest first."""
    cmd = ["git", "log", "--name-only", "--pretty=format:--%H--"]
    if n:
        cmd.insert(2, f"-n{n}")
    if since:
        cmd.insert(2, f"--since={since}")
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    commits, current_hash, current_files = [], None, []
    for line in out.splitlines():
        if line.startswith("--") and line.endswith("--") and len(line) == 44:  # --<40-char sha>--
            if current_hash:
                commits.append((current_hash, current_files))
            current_hash, current_files = line[2:-2], []
        elif line.strip():
            current_files.append(line.strip())
    if current_hash:
        commits.append((current_hash, current_files))
    return commits

def author_of(commit_hash):
    return subprocess.run(
        ["git", "log", "-1", "--pretty=format:%an", commit_hash],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

def compute_coupling(commits, max_files_per_commit=60, min_shared=3, exclude_authors=()):
    """Returns (revisions: Counter[file]->count, coupling: Counter[(fileA,fileB)]->shared_commits)."""
    revisions, coupling = Counter(), Counter()
    for commit_hash, files in commits:
        if exclude_authors and author_of(commit_hash) in exclude_authors:
            continue
        for f in files:
            revisions[f] += 1
        # Exclude "shotgun commits" (mass rename/vendor bump) from PAIRING only —
        # they still count toward each file's own revision total above. This mirrors
        # code-maat's real mitigation for the same problem.
        if len(files) > max_files_per_commit:
            continue
        for a, b in itertools.combinations(sorted(set(files)), 2):
            coupling[(a, b)] += 1
    coupling = Counter({pair: n for pair, n in coupling.items() if n >= min_shared})
    return revisions, coupling

def hotspot_score(revisions, complexity_by_file=None, line_counts=None):
    """complexity_by_file (e.g. from gocyclo/gocognit) is the real proxy if you have it;
    line_counts is the fallback. Returns sorted [(file, score)] descending."""
    proxy = complexity_by_file or line_counts or {}
    scores = {f: revisions[f] * proxy.get(f, 0) for f in revisions if f in proxy}
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--commits", type=int, default=1000)
    p.add_argument("--since", default=None)
    p.add_argument("--max-files-per-commit", type=int, default=60)
    p.add_argument("--min-shared", type=int, default=3)
    p.add_argument("--exclude-author", action="append", default=[],
                    help="e.g. --exclude-author 'github-actions[bot]' to drop CI automation noise")
    args = p.parse_args()

    commits = get_commits(n=args.commits, since=args.since)
    revisions, coupling = compute_coupling(
        commits, args.max_files_per_commit, args.min_shared, tuple(args.exclude_author)
    )

    print("# Top 20 files by revision count")
    for f, n in revisions.most_common(20):
        print(f"{n:5d}  {f}")

    print("\n# Top 20 co-change pairs (>= min-shared commits)")
    for (a, b), n in coupling.most_common(20):
        ratio = n / min(revisions[a], revisions[b])
        print(f"{n:3d}  ratio={ratio:.2f}  {a}  <->  {b}")

    # Hotspot score needs a complexity/line-count map — plug in `wc -l` output or
    # gocyclo/gocognit's per-function output rolled up to per-file sums, e.g.:
    #   line_counts = {f: int(subprocess.run(["wc","-l",f], capture_output=True,
    #                  text=True).stdout.split()[0]) for f in revisions if f.endswith(".go")}
    #   for f, score in hotspot_score(revisions, line_counts=line_counts)[:20]:
    #       print(f"{score:8d}  {f}")
```

**Notes from actually running this** (this repo, 1000-commit window):
- `github-actions[bot]` automation (`--exclude-author 'github-actions[bot]'`) removed 551/1000 commits that were pure CI benchmark/demo regeneration noise — always check `git log --author` on your top revision-count entries before trusting them; automated commits touching the same few files on every run will dominate raw counts without being an architectural signal.
- Generated code (ORM mutation files, protobuf bindings) should be excluded from the **hotspot ranking** (a 23K-line generated file will top any line-count-based score meaninglessly) but *kept* in the **coupling data** — coupling between a generated file and its source (`.proto` ↔ `.pb.go`) is a legitimate, if uninteresting, confirmation signal, and coupling that flows *through* a generated file to other hand-written files is informative.
- `line_counts` is a real but weak complexity proxy — prefer summing `gocyclo`/`gocognit` per-function output by file if that data is available from a parallel static-analysis pass (see axis 1 above); fall back to line count only when it isn't.

## Workflow

1. Run the static structural pass (goda/go-callvis/gocyclo/gocognit/goplantuml/ast-grep) — cheap, deterministic, no time window to pick.
2. Run the temporal pass (code-maat or the fallback script) over a deliberately bounded window (e.g. last 500-1000 commits or 6 months — pick something that finishes in reasonable time; don't scan entire project history by default).
3. Compute the hotspot score (axis 2's complexity × churn) and the top co-change pairs (axis 2's pairwise coupling).
4. Cross-reference axis 1's static coupling against axis 2's temporal coupling for the same files/packages — agreement between them (a file that's both structurally central AND a temporal hotspot) is your highest-confidence target.
5. Hand the ranked list to `architecture-review` (`--target=class:X`/`--target=package:Y`, targeted not `--depth=deep` full-codebase) for the principle-level "why is this bad and how do we fix it" analysis. Don't run a full SOLID/DDD sweep uniformly across a whole codebase when you have a ranked list telling you where the actual pain is.
6. If a fix is warranted, hand it to `find-refactor-candidates`/`code-refactoring` — informed by which axis flagged it (a static-coupling problem wants an interface/boundary extraction; a temporal-coupling problem across packages wants investigating whether a shared concept should be extracted into its own type/package).
7. After fixing (or instead of fixing, if the finding is a "watch this" not a "fix this now") wire the same complexity/size metrics into CI as a regression gate — see **CI Enforcement** below for per-language tooling. The goal is the hotspot never re-forms silently; a one-time analysis without a standing gate just delays the next audit finding the same file again.

## CI Enforcement — Per-Language Reference

Once a hotspot is found (or fixed), the durable follow-up is a CI check that catches the same shape — a file or function crossing a size/complexity threshold — before it grows back. Three principles hold across every language below, learned the hard way running this end-to-end on a Go repo (session/backlog_lifecycle.go: 4930 lines → split, then gated):

1. **Scope thresholds to this repo's own measured average**, not a textbook default. Pull the average from axis 1's complexity tool (e.g. `gocyclo -avg`) and set the gate threshold well above it (5-10x) — the goal is "catch things this bad," not "enforce a style preference."
2. **Scope enforcement to new/changed code only**, not the whole repo at once. A repo with an existing hotspot almost always has dozens of other pre-existing violations elsewhere; enabling a new gate unscoped fails CI for everyone immediately on unrelated code. Every ecosystem below has a diff-aware mode for exactly this (VCS-diff/new-code-period/changed-files) — use it instead of hand-writing a grandfather list of exclusions, which rots and needs manual upkeep. Confirm this by actually running the tool in diff-scoped mode against the *fixing* PR's own diff before merging — the fix should introduce zero new violations, not just "look better."
3. **A refactor that moves code into new files can trip its own gate.** If the fix splits one file into several, most VCS diff tools don't recognize this as a rename (especially "split into 3 files" — there's no 1:1 target for a rename detector to match). Every line in the new files reads as newly-added, so pre-existing complexity that moved verbatim gets flagged as if it were just introduced. Handle this explicitly at the specific declaration (a targeted suppression comment naming the origin and a follow-up, e.g. Go's `//nolint:gocognit // relocated verbatim by the <file> split, see <PR>`) — never respond by widening the gate's scope or grandfathering the whole file, which would also hide genuinely new debt landing in the same file later.

### Go

`golangci-lint` (already the linter in most Go repos) has all four metrics as bundled linters — no extra tool install needed beyond what axis 1 already uses for ad-hoc analysis:

| Metric | Linter | Settings |
|---|---|---|
| Cyclomatic complexity | `gocyclo` | `min-complexity: 25` (repo avg × ~10) |
| Cognitive complexity | `gocognit` | `min-complexity: 40` |
| Function length | `funlen` | `lines: 150`, `statements: 100`, `ignore-comments: true` |
| File length | `revive` (`file-length-limit` rule) | `max: 1000`, `skipComments: true`, `skipBlankLines: true` |

```yaml
# .golangci.yml (v2 schema) — settings live here regardless of how the linter gets enabled
linters:
  settings:
    gocyclo: {min-complexity: 25}
    gocognit: {min-complexity: 40}
    funlen: {lines: 150, statements: 100, ignore-comments: true}
    revive:
      rules:
        - name: file-length-limit
          arguments: [{max: 1000, skipComments: true, skipBlankLines: true}]
```

**New-code-only scoping**: do NOT add these four to `linters.enable:` in the shared config — that makes every local `golangci-lint run` / `make lint` fail on pre-existing repo-wide debt. Instead enable them only in a dedicated CI step via `--enable`, paired with `golangci-lint-action`'s `only-new-issues: true` (or CLI `--new-from-merge-base=<base-branch>` if not using the Action):

```yaml
# .github/workflows/lint.yml — separate step, not folded into the main lint step
- uses: golangci/golangci-lint-action@v7
  with:
    args: --timeout=3m --max-issues-per-linter=0 --max-same-issues=0 --enable=gocyclo,gocognit,funlen,revive
    only-new-issues: true   # scopes to the PR's diff — pre-existing repo debt doesn't block
```

**Go-specific gotchas hit running this**:
- `golangci-lint`'s default `--max-issues-per-linter=50` silently truncates results below what you'd expect — always pass `--max-issues-per-linter=0 --max-same-issues=0` when auditing the *true* violation count (a first pass without these flags underreported `gocognit` findings by 17 in one run, with no error or warning that truncation happened).
- `revive`'s `file-length-limit` rule requires `revive` itself to be in the enabled linters list — configuring it under `settings.revive.rules` alone, without enabling `revive`, silently does nothing.
- Passing `--config <path outside the repo>` (e.g. a scratch `/tmp/test.yml`) can break golangci-lint's relative-path computation when the config also has a pre-existing `exclusions.paths: ["^\\.\\."]`-style pattern — it can end up matching every file and silently excluding 100% of issues with no error. Always validate new config changes via auto-discovery (`cd <repo root> && golangci-lint run`, no `--config` flag) before trusting a result.
- `//nolint:` directives must be the *last* line of the comment block immediately before the declaration — `gofmt` will reflow/reject a doc comment that has prose after the `//nolint:` line.
- `gocyclo -avg` (used in axis 1) gives the repo-wide baseline to calibrate `min-complexity` against — don't guess a threshold.

### TypeScript / JavaScript

ESLint's built-in `complexity` and `max-lines`/`max-lines-per-function`/`max-depth`/`max-params` rules cover cyclomatic complexity, file length, and function length without a plugin. Cognitive complexity needs `eslint-plugin-sonarjs`'s `sonarjs/cognitive-complexity` rule.

```json
// .eslintrc — new-code-only equivalent: run only against files changed in the diff
{
  "rules": {
    "complexity": ["error", 25],
    "max-lines": ["error", 1000],
    "max-lines-per-function": ["error", 150],
    "sonarjs/cognitive-complexity": ["error", 40]
  }
}
```

Scope to changed files the same way this repo's own `lint.yml` already scopes ESLint's `no-100vh` check: `git diff --name-only "$BASE_SHA"...HEAD -- '**.ts' '**.tsx' | xargs npx eslint`, falling back to a full-repo run only on push-to-main (no PR base to diff against). `reviewdog` is a ready-made alternative if you want inline PR annotations instead of a hand-rolled diff filter.

### Python

`radon cc`/`radon mi` compute cyclomatic complexity and a maintainability index per function/file; `xenon` wraps `radon` with pass/fail exit codes for CI (`xenon --max-absolute B --max-modules A --max-average A .`). Cognitive complexity needs the `flake8-cognitive-complexity` plugin. File length isn't natively covered by any of these — `pylint`'s `too-many-lines` message (default 1000) is the standard choice.

New-code-only scoping: none of these tools have a native diff mode — wrap with the changed-file list (`git diff --name-only <base>...HEAD -- '*.py'`) passed as explicit file args, same pattern as the TS section above.

### Java / Kotlin

This ecosystem's tooling is the most mature here because SonarQube popularized "New Code" as a first-class quality-gate concept — if the repo already runs SonarQube/SonarCloud, its built-in Cognitive Complexity metric + "New Code" period setting *is* the new-code-only scoping mechanism, no extra wiring needed.

Without SonarQube: PMD (`CyclomaticComplexity`, `CognitiveComplexity`, `ExcessiveMethodLength`, `ExcessiveClassLength` rules) or Checkstyle (`CyclomaticComplexity`, `MethodLength`, `FileLength` modules) for Java; `detekt` (`ComplexMethod`, `LongMethod`, `LargeClass` rules) for Kotlin. All three support a changed-file list via their respective CLI file-args, same diff-scoping pattern as above.

### Rust

`cargo clippy`'s `clippy::cognitive_complexity` lint (allow-by-default, needs `#![warn(clippy::cognitive_complexity)]` or `-W`) covers cognitive complexity directly. No mainstream dedicated file-length gate exists; `tokei`/`scc` give line counts you can threshold in a CI script if needed. Diff-scoping: `cargo clippy` doesn't have a native changed-files mode — `reviewdog`'s clippy integration is the standard way to get diff-scoped annotations instead of a repo-wide gate.

## When NOT to Use This

- **A single file/PR review.** This is a whole-codebase or whole-package prioritization technique. For "is this one file well-designed," go straight to `architecture-review --context=current`.
- **A young codebase with little git history.** Temporal coupling needs enough commits to be statistically meaningful — a few dozen commits won't produce a reliable signal. Static coupling (axis 1) still works fine on day one.
- **As a scoring mechanism for people, not code.** `find-refactor-candidates`' existing "files with most contributors" metric edges toward this — resist using churn/coupling data to evaluate who wrote what; it's a codebase signal, not a performance metric.

## Anti-Patterns

- **Treating the hotspot score as ground truth.** It's a proxy that correlates with maintenance pain; a high score means "look here first," not "this is definitely broken." Always read the actual code before recommending a fix.
- **Scanning entire project history by default.** Pick a bounded, recent window — ancient history dilutes the signal with code nobody touches anymore and makes the analysis slow for no benefit.
- **Running every tool in the stack every time.** Static coupling (goda/gocyclo/ast-grep) is cheap and always worth running; the temporal pass (code-maat/co-change script) is the expensive, judgment-call part — reach for it when static coupling alone doesn't explain why an area feels painful to work in.
- **Skipping the cross-reference step.** A file flagged by only one axis is a weaker signal than one flagged by both — don't treat every hit as equally urgent.

## Related Skills

| Skill | When to apply |
|---|---|
| `architecture-best-practices` | The principle framework (SOLID/DDD/Clean Architecture) this analysis prioritizes work for |
| `golang-development` | Idiomatic Go patterns to apply once a hotspot is identified |
| `code-ast-grep` | Deeper `sg` pattern syntax for the structural-query half of axis 1 |
| `code-refactoring` | Executing the fix once a target is chosen |
| `type-driven-design` | If a hotspot's root cause is primitive obsession / missing invariant encoding, not just size |
