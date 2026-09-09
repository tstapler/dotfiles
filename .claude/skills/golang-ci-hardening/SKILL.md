---
name: golang-ci-hardening
description: Audit or set up a Go repo's CI quality gates against a Rust-toolchain-equivalent bar (clippy/cargo-deny/cargo-audit/miri-level assurance). Use when asked to "harden Go CI", "set up robust Go CI checks", review .golangci.yml / Makefile lint targets, or add security/supply-chain/test-rigor gates to a Go project. Produces a gap report plus concrete config (golangci-lint v2, govulncheck, gosec, coverage/race/fuzz gates) scoped to what CI runner the repo actually uses (GH Actions, Jenkins/Rocket/newt, etc.).
---

# Golang CI hardening

Rust gets most of its CI assurance for free from the toolchain: the borrow
checker, `cargo clippy` (deep static analysis), `cargo audit`/`cargo deny`
(vuln + license + banned-crate gates), `cargo fmt --check`, and increasingly
`cargo mutants`/`miri`. Go's toolchain gives you none of that by default —
`go build` + `go vet` is a much lower bar. Closing that gap is a deliberate
CI-configuration exercise, not a toolchain upgrade. This skill is the
checklist for doing that exercise and the reference config to do it with.

This is a **hardening pass**, not a rewrite: audit what already exists in the
repo's Makefile/CI config before adding anything, and prefer tightening
existing gates over bolting on parallel ones.

## Step 0 — inventory what's already there

Before proposing anything, establish ground truth:

```bash
# What runs today and how
cat Makefile | grep -A3 '^lint:\|^test:\|^vet:\|^fmt'
find . -maxdepth 1 -iname '.golangci*'
find . -path '*/.github/workflows/*' -o -iname 'Jenkinsfile*' -o -iname '.newt.yml' -o -iname '*.ci'
grep -rn 'govulncheck\|gosec\|staticcheck\|osv-scanner\|cosign\|syft\|cyclonedx' Makefile .github/workflows/*.yml 2>/dev/null
```

Identify:
- **The CI runner** (GH Actions / Jenkins-Rocket-newt / other) — this decides
  where gates live (workflow YAML vs. a Rocket-style CI descriptor script vs. both,
  with the Makefile as the shared source of truth either way).
- **What "green" means today** — is there a single `make ci`/`make ready`
  target that mirrors the real CI gate locally, or does CI run steps that
  have no local equivalent? If there's no such target, creating one is
  usually the highest-leverage first change: it's what makes every other
  gate here actually enforceable pre-push instead of only in CI.
- **Repo age/size** — a brand-new repo can enable every linter at max
  strictness immediately. A repo with years of history needs the **ratchet
  pattern** (below) or every gate addition breaks the build for everyone.

## The gate categories (Rust-equivalent mapping)

| Rust gets this from... | Go equivalent | Tier |
|---|---|---|
| the compiler / borrow checker | `go vet`, `go build` | baseline, already have it |
| `cargo fmt --check` | `gofmt -l` / `gofumpt -l` | baseline |
| `cargo clippy` | `golangci-lint` (v2, curated linter set) | **linting depth** |
| `cargo audit` / `cargo deny` (vuln) | `govulncheck` | **security** |
| `cargo deny` (license/ban) | `golangci-lint depguard` + license-checker | **security** |
| clippy's security lints | `gosec` | **security** |
| `cargo audit` (supply chain) | `govulncheck` + `go mod verify` + SBOM | **supply chain** |
| deterministic builds by default | `GOFLAGS=-trimpath`, toolchain pin, generated-code drift guard | **determinism** |
| the type system ruling out data races | `-race` as a **gate**, not advisory + amplification for known-flaky races | **test rigor** |
| `cargo fuzz` | `go test -fuzz` with committed seed corpus | **test rigor** |
| `cargo mutants` (nascent) | `gremlins`/`go-mutesting` (nascent, advisory-only) | **test rigor**, low priority |
| `cargo test` leak-free by construction | `goleak` for goroutine-leak detection | **test rigor** |

None of these individually get you to "Rust level" — the aggregate does, and
only if every gate is a **required check** (see Architecture, below) rather
than a report nobody reads.

## 1. Linting depth — golangci-lint v2

Check the currently pinned version and config:

```bash
grep GOLANGCI_VERSION Makefile   # want golangci-lint v2.x, ideally current (v2.13.x as of 2026-08)
```

v2 (launched March 2025) rewrote the config schema: `linters.default:
standard|all|none|fast` replaces v1's `enable-all`; a separate `formatters:`
block now holds `gofmt`/`gofumpt`/`gci`, distinct from `linters:`; named
exclusion presets (`comments`, `common-false-positives`, `legacy`,
`std-error-handling`) replace hand-rolled regex; `golangci-lint migrate`
converts a v1 config. Several linters were removed outright, not just
deprecated — `structcheck`, `varcheck`, `deadcode` (the linter; distinct from
the `x/tools/cmd/deadcode` binary below), `golint`, `interfacer`, `maligned`,
`scopelint`, `exhaustivestruct`, `ifshort`, `nosnakecase`, `tenv` are gone,
superseded by `unused`/`revive`/`staticcheck`. If you find any of those names
in an old config, that's a stale v1 leftover to delete, not something to
port forward.

v2's default set is thin. A "clippy-equivalent" config additionally enables
at minimum: `staticcheck`, `govet` (already default), `unused`,
`ineffassign`, `errcheck`, `exhaustive`, `gosec`, `nilnil`, `prealloc`,
`bodyclose`, `contextcheck`, `noctx`, `forcetypeassert`, plus
`errorlint`/`sqlclosecheck`/`durationcheck`/`misspell`/`loggercheck`/
`fatcontext`/`usetesting`, plus repo-specific `depguard`/`forbidigo` rules to
ban known footguns (`fmt.Print*` in production code, bare `exec.Command`
without a timeout/context, deprecated stdlib packages, ORM/layer-boundary
leaks). See `references/golangci.yml` for a concrete starting config with
rationale comments — copy it in and delete/adjust sections per repo.
Kubernetes' [`hack/golangci.yaml`](https://github.com/kubernetes/kubernetes/blob/master/hack/golangci.yaml)
and the tiered [ccoVeille/golangci-lint-config-examples](https://github.com/ccoVeille/golangci-lint-config-examples)
(`00-empty` → `90-daredevil`, with `03-safe` as the best "strict but sane"
reference point) are worth diffing against for a specific repo's tuning.

**High-noise linters to be deliberate about, not reflexive about enabling
repo-wide**: `gocyclo`, `gocognit`, `funlen`, `dupl`, `revive`'s
file-length-limit, plus commonly-excluded ones even on greenfield repos —
`wrapcheck` (boilerplate cost outweighs value on internal call chains),
`exhaustruct` (incompatible with idiomatic partial-literal/zero-value Go),
`gochecknoglobals` (too blunt for DI-style sentinel errors), `wsl`/`nlreturn`/
`paralleltest`/`testpackage`/`cyclop`. On a mature repo the complexity/dup
linters will have hundreds of pre-existing violations — enabling them
repo-wide breaks `make lint` for everyone immediately; use the ratchet
pattern instead. Two linters deserve a specific caution rather than a blanket
enable: `gosec`'s defaults over-flag `G404` (weak rand) and `G304` (path
traversal on any `os.Open` with a variable path) — tune with `excludes`/a
severity floor before treating it as signal; `staticcheck`'s `SA1019`
(deprecation) floods on stdlib deprecations and is commonly excluded
(`checks: ["all", "-SA1019"]`).

### Two linters worth understanding, not just enabling

**`revive`** ([revive.run](https://revive.run/)) is a full rule *framework*,
not a fixed checklist — a drop-in golint replacement that's ~2-6x faster and
TOML/YAML-configurable per-rule. Most golangci-lint configs (including
`references/golangci.yml` before this pass) enable `revive` and stop there,
which only turns on its golint-equivalent defaults. Revive ships many more
opt-in rules worth turning on deliberately via `settings.revive.rules` —
`cognitive-complexity`, `unhandled-error` (a stricter errcheck angle),
`unused-parameter`, `bare-return`, `confusing-naming` — rather than treating
it as a single on/off switch. If a repo already runs `revive` and stops
there, that's under-using it, not fully using it.

**`staticcheck`** (upstream: [dominikh/go-tools](https://github.com/dominikh/go-tools))
is itself four historically-separate tools merged into one binary/check
namespace: `SA*` (actual bugs — what golangci-lint's `staticcheck` linter
exposes by default), `S*` (simplifications, formerly the separate
`gosimple` tool), `ST*` (style, formerly `stylecheck`), `U*` (unused code,
formerly `unused` as a *standalone* tool — distinct from golangci-lint's own
`unused` linter, which wraps this). golangci-lint's `staticcheck.checks:`
setting controls which of these classes run — `checks: ["all"]` (with
`-SA1019` excluded per above) gets bug detection *and* simplification *and*
style checks in one pass; most configs that only inherited the default get
`SA*` alone and are leaving the `S*`/`ST*` classes — the closest thing Go
static analysis has to `cargo clippy`'s style/idiom lints — turned off
without realizing it. The go-tools repo also ships `structlayout`/
`structlayout-optimize` (struct field padding/reordering) as standalone
tools, not golangci-lint linters — a memory-layout-efficiency check with no
real Rust-CI analog (Rust doesn't guarantee field order either, but the
tooling culture of checking it is closer to a Rust habit than a Go one);
worth a one-off audit on hot-path structs, not a CI gate.

### The ratchet pattern (mandatory for any non-trivial existing repo)

Configure the strict thresholds in `.golangci.yml`, but only *activate* the
noisy/high-violation-count ones scoped to new code:

```bash
golangci-lint run --enable=gocyclo,gocognit,funlen,revive,dupl --new-from-rev=origin/main
```

This is a second, separate lint invocation (a "tier 2" gate) layered on top
of the full-repo tier-1 pass for the linters that are already clean.
**Do not use GitHub's `only-new-issues: true` action option for this** — it
fetches the diff via the REST API, which 406s above ~20k changed lines and
silently falls back to reporting every pre-existing issue repo-wide (see
golangci/golangci-lint-action#996). `--new-from-rev` diffs locally via git
and has no such cap — verified pattern from stapler-squad's `lint.yml`.

Apply the same new-code-only scoping to `gofmt`: check
`git diff --name-only base...HEAD -- '*.go'` rather than the whole tree, so
a hardening pass doesn't force a repo-wide reformat as a prerequisite.

### Full linter inventory audit (don't design a config from memory)

golangci-lint v2 ships **~110 linters** (5 enabled by default, ~105 opt-in as
of v2.12.2 — confirmed by actually running `golangci-lint help linters`
against the pinned version, not from documentation, since the set changes
release to release). Designing a config from a remembered list of "the
usual suspects" reliably misses real bug-catchers. Run this before finalizing
any config for a specific repo:

```bash
GOLANGCI_VERSION=v2.12.2  # match Makefile's pin
go run github.com/golangci/golangci-lint/v2/cmd/golangci-lint@${GOLANGCI_VERSION} help linters
```

Then cross-reference against the repo's actual dependencies — a linter for
a library the repo doesn't use is noise, and a linter for one it does use
but isn't running is a real gap. For compute-nop specifically (confirmed via
`grep` on `go.mod`: uses `testify`, `slog`+`zap` (via `samber/slog-*` and
`veqryn/slog-*` adapters), and OpenTelemetry for tracing over gRPC), beyond
what's already in `references/golangci.yml`:

| Linter | Why it's relevant here | Priority |
|---|---|---|
| `testifylint` | repo uses `testify` — catches wrong assertion methods (`Equal` vs `True`, etc.) that silently pass | add |
| `spancheck` | repo uses OpenTelemetry spans over gRPC/Temporal — catches spans never `End()`-ed or errors never recorded on them | add |
| `loggercheck` | repo uses slog/zap — catches mismatched key-value pairs in structured logging calls | add (already recommended in §1's baseline list — make sure it's actually in `enable:`) |
| `gochecksumtype` | exhaustiveness on Go "sum types" (interface + unexported method / sealed-style patterns) — the closest golangci-lint linter to Rust's exhaustive `match` on an `enum` | add if the repo uses this pattern anywhere; otherwise low-value |
| `nilerr` / `nilnesserr` | catches `return nil` after an `err != nil` check, or returning the wrong nil'd error — a real, easy-to-miss bug class | add |
| `makezero` | catches `make([]T, n)` followed by `append` in a way that silently duplicates/skips elements | add |
| `unconvert` / `unparam` | dead conversions / genuinely-unused params — hygiene, cheap, near-zero false positives | add |
| `predeclared` | catches shadowing of builtins (`len`, `min`, `new`, etc.) | add |
| `reassign` | catches reassignment of package-level exported vars — a real defensive check against a specific supply-chain-adjacent footgun (a dependency mutating another package's exported state) | consider |
| `modernize` | suggests modern-Go-idiom rewrites (loop→`range over int`, etc.) — the closest thing to `rustfmt`/clippy's "this could be simpler" class, newer linter, actively evolving | add, but review autofix output rather than blind-applying |
| `rowserrcheck` | pairs with `sqlclosecheck` for `database/sql` — **not currently relevant to compute-nop** (no direct `database/sql` usage found — confirmed via grep) | skip here; add if a repo does use `database/sql` directly |

This table is a worked example of the audit process, not a universal
"always add these ten" list — rerun the cross-reference for a different
repo's actual dependency set rather than copying this table verbatim.

### Advanced/optional: research-grade static analysis beyond golangci-lint

Two tools outside golangci-lint's scope, at opposite ends of maturity:

**`golang.org/x/tools/cmd/oracle` — do not add this.** It's dead: last
published 2016, zero known importers, and pkg.go.dev flags it as "not in
the latest version of its module" (verified directly on pkg.go.dev, not
inferred). It was superseded by `guru`, which has itself been superseded for
interactive use by `gopls` (the language server every modern Go editor
already runs — "find callers", "find implementations", etc. are `gopls`
features now) and for CI-shaped call-graph analysis by `golang.org/x/tools/cmd/callgraph`
or the `ar-go-tools` commands below. If a repo's tooling docs mention
`oracle` or `guru`, that's stale documentation to fix, not a tool to install.

**`github.com/awslabs/ar-go-tools`** ("Argot") — an AWS Labs research-grade
static-analysis toolkit built on SSA + pointer analysis, more powerful and
more specialized than anything in golangci-lint. Its subcommands (all under
one `argot` binary):
- `argot taint` — taint analysis: does untrusted/tainted data (HTTP input,
  config, env vars) reach a sensitive sink (a DB query, a log line, a
  shell command) without going through a sanitizer? This is close to what
  Rust's type system gets you *structurally* via newtypes/ownership for
  untrusted data — Go has no such mechanism, so this is the closest
  available substitute, and it's a genuinely good fit for compute-nop given
  the AWS/EKS-credential and ArgoCD-secret handling surfaced by this
  session's `gosec` run (`internal/aws/eks_auth_token.go`,
  `cmd/argocd-shard-access/bootstrap.go` G101 hits, the G702/G703
  taint-flagged findings in `cmd/nopctl`).
- `argot backtrace` — backward dataflow from a given call, useful for
  answering "what can influence this function's input" during an incident
  or a security review, not typically a CI gate.
- `argot maypanic` — flags call paths that may panic without a recover —
  the closest Go equivalent to proving a function can't crash, which Rust's
  `Result`-forces-you-to-handle-it convention gets structurally.
  `argot reachability` / `argot dependencies` / `argot render` — call-graph
  and dependency introspection, useful for architecture review, not gating.
- An experimental `racerg` static data-race detector also ships in `cmd/`.

Treat this whole toolkit as **advisory, not a CI gate**: it's newer and far
less battle-tested than govulncheck/gosec/staticcheck (an active CI badge on
the repo is a maintenance signal, not a maturity one), and taint/may-panic
analysis on a codebase this size will need real tuning before it's
gate-worthy. Right use: a one-off `argot taint` run scoped to the
credential-handling packages as a security-review deepening step, not
something wired into `make lint`.

## 2. Security scanning

Two tools, both missing from most Go repos by default (confirmed absent in
both compute-nop and stapler-squad as of this audit — this is the most
common real gap):

```bash
# Vulnerability scanning — reachability-aware (only flags vulns actually
# reachable from your call graph, not every CVE in every transitive dep)
go run golang.org/x/vuln/cmd/govulncheck@v1.1.4 ./...

# Security-focused static analysis (hardcoded creds, SQL injection shapes,
# weak crypto, unsafe pointer use, etc.)
go run github.com/securego/gosec/v2/cmd/gosec@latest ./...
```

**Pin `govulncheck`'s version explicitly — do not use `@latest`.** Running
`@latest` against compute-nop pulled in `golang.org/x/tools@v0.49.0` and
**crashed with an internal panic** in the SSA builder while analyzing
generics-heavy code (`got jsontext.Value, want variadic parameter of
unnamed slice or string type`) — a tool bug, not a code finding. `v1.1.4`
(pulling `x/tools@v0.29.0`) ran clean on the same code. Verified directly:
this is not a hypothetical caution, it reproduced on this repo on
2026-09-01. Re-check the pinned version periodically as x/tools/govulncheck
release new versions, but always pin, and smoke-test a version bump before
trusting a green run.

Pin both tools' versions the same way the repo pins
`golangci-lint`/`workflowcheck` (a `_VERSION` Makefile variable, bumped
deliberately). `govulncheck` is official (`golang.org/x/vuln`, maintained by
the Go security team), does call-graph reachability analysis rather than
naive version matching, and is the closest Go analog to `cargo audit` — gate
on it, don't just report it, since false positives are rare (it requires
actual reachability). Known limits: conservative around function-pointer/
interface dispatch, blind to `reflect`-only call paths.

`gosec` is actively maintained (commit activity through late 2025, taint-
analysis engine, SARIF output support: `gosec -fmt=sarif -out=results.sarif
./...`). Practice is mixed on whether it's a hard gate — most teams tune
`excludes`/a severity floor first (see §1's `G404`/`G304` note) rather than
gating on untuned defaults. `OSV-Scanner` (`google/osv-scanner`) is worth
knowing about too: for Go specifically its v2 line runs `govulncheck`
internally for reachability rather than doing lockfile-only matching, so it
subsumes rather than duplicates govulncheck if a team is already using it
for multi-ecosystem scanning.

## 3. Supply chain / provenance

Lower priority than the above two, but the direct analog to `cargo deny`'s
supply-chain checks:

- **Module integrity** — the actual dependency-confusion defense, and cheap
  to add unconditionally to the static gate:
  ```bash
  GOFLAGS=-mod=readonly go mod verify
  ```
  Set `GOSUMDB` to its default (never `off` org-wide), pin `GOPROXY`, and
  scope `GOPRIVATE`/`GONOPROXY`/`GONOSUMDB` narrowly (never a bare `*`).
  `go mod verify` only checks the module cache against `go.sum` — it does
  not re-download, so a tampered cache entry plus a stale `go.sum` can still
  pass; that's a cache-hygiene concern for CI runners that reuse a
  `GOMODCACHE` across untrusted branches (see §6's caching note). This
  matters concretely: `github.com/boltdb-go/bolt`, a 2021 typosquat of
  `boltdb/bolt`, sat live in the module proxy with a backdoor for ~3 years
  before being reported in 2025 — `GOSUMDB` verifies integrity of the module
  you asked for, not that the import path itself isn't a typosquat.
- **SBOM generation**: `syft dir:. -o cyclonedx-json=sbom.json` or
  `cyclonedx-gomod mod -json -output bom.json` — produce on release builds,
  not every PR. Caution: Trivy was compromised twice in a March 2026
  coordinated supply-chain attack; prefer syft/cyclonedx-gomod over it for
  SBOM/scanning pipelines until that's resolved.
- **Build provenance/signing**: for a repo that ships binaries externally
  (an OSS CLI release, not an internal debian package pipeline like
  compute-nop's), GitHub-native attestations are the current recommended
  path over the now-legacy `slsa-github-generator` (no further releases
  guaranteed past v2.1.0):
  ```yaml
  permissions: { id-token: write, contents: read, attestations: write }
  - uses: actions/attest-build-provenance@v3
    with: { subject-path: 'dist/myapp-*' }
  ```
  Meets SLSA v1.0 Build L2 out of the box, verified via
  `gh attestation verify ./myapp -R org/repo`. `cosign sign-blob`/
  `verify-blob` (Sigstore) is the alternative when attestations aren't
  available. Caution from a 2025/2026 npm supply-chain incident: valid SLSA
  provenance from a build alone doesn't prove builder isolation — verify the
  builder identity/certificate-identity too, not just that a provenance
  document exists.
- `GOFLAGS=-trimpath` plus `CGO_ENABLED=0` and a fixed (non-`time.Now()`)
  version string for reproducible builds — verify with a build-twice-diff-
  hashes check at release time, not as a per-PR gate.
- `ossf/scorecard-action` for an ongoing supply-chain health score (SARIF →
  code-scanning alerts) — advisory, not a hard-fail threshold; a 2023 study
  found no clean score-to-vulnerability correlation, so treat it as a
  dashboard, not a gate.

## 4. Test rigor

- **Race detector as a gate, not advisory.** If `go test -race` isn't
  already in the primary test target, that's a blocker-tier finding — it's
  the single highest-value Go safety net and many repos silently only run
  race in a separate, non-required job. Real-world exemplars scope it rather
  than running it everywhere unconditionally (2-20x slowdown, 5-10x memory):
  grpc-go runs one dedicated `-race` leg alongside non-race legs; prometheus
  scopes `-race` to specific packages/tags and skips it on the oldest-Go
  leg to save cost; tailscale runs 3 dedicated race-tagged shards plus a
  separate root-privileged race-integration job. Scoping is a cost
  tradeoff, not a signal that race-gating is optional.
- **Amplify race detection for tests with a history of flaking under race.**
  A single `-race` run only executes each test once; a reintroduced race can
  hide. For specific known-flaky-under-race packages, compile a `-race` test
  binary and run it repeatedly under load (`go-stress-test` or a simple
  bash loop with `-count=N -parallel=$(nproc)` for a fixed duration in CI).
  Don't apply this repo-wide — it's expensive; scope it to packages with a
  documented history (cite the incident/bug in a comment) — this is exactly
  the pattern in stapler-squad's `pty-race-regression` job.
- **Fuzzing**: `go test -fuzz=FuzzXxx -fuzztime=30s` in CI for any function
  that parses untrusted input (config, network payloads, CLI args). Commit
  the seed corpus (`testdata/fuzz/<FuzzName>/`) — plain `go test` (no
  `-fuzz` flag) replays it automatically, so the **regression corpus is a
  hard gate for free** even when new-exploration fuzzing isn't. New/unbounded
  fuzzing is rarely a hard PR gate elsewhere either; prometheus's
  [`fuzzing.yml`](https://github.com/prometheus/prometheus/blob/main/.github/workflows/fuzzing.yml)
  is the reference pattern: PR-gated, 4 target groups, `-fuzztime=4m` each,
  crash artifacts uploaded on failure, aggregated into one required status
  check — pair a short PR-gated run with a longer nightly cron run rather
  than making PRs wait on a long fuzz budget.
- **Mutation testing — advisory only, do not hard-gate on it yet.**
  `gremlins` (`go-gremlins/gremlins`) is the actively-maintained option
  (latest v0.6.0, 2025-12) but is pre-1.0 with no back-compat guarantee and
  has been reported broken on Go 1.26.x; `go-mutesting` is abandoned. Cross-
  checked industry consensus (ACM industrial case study, ICST 2025 mutation
  workshop, a CI-focused study that found the tooling "not mature" for CI
  use) agrees mutation testing hasn't caught on as standard practice —
  report a score (`gremlins unleash --dry-run`) for visibility, and only
  consider a hard `--threshold-efficacy` gate on small, well-isolated
  packages, never repo-wide.
- **Coverage gate**: enforce a real threshold, not just generate a report.
  stapler-squad uses `vladopajic/go-test-coverage` with `global-threshold: 60`
  in CI; for a Jenkins/Rocket setup without that GH Action, the equivalent is
  a shell step parsing `go tool cover -func` output and failing under
  threshold. Prefer a **diff/patch coverage** threshold over (or in addition
  to) an overall-% threshold where tooling allows — an overall percentage can
  hide a fully-untested new file behind a high aggregate; `go-test-coverage`
  supports per-package + overall + diff thresholds via `.testcoverage.yml`.
  Coverage scope matters: exclude generated code (`*.pb.go`, `api/gen/**`)
  from the denominator the same way `scripts/test-ci.sh` already does, or the
  metric is meaningless. Contrast case worth noting: hashicorp's
  terraform-plugin-framework uploads raw coverage as an artifact with **no
  threshold gate at all** — visibility-only coverage is a legitimate, lower-
  rigor choice, not automatically wrong for every repo.
- **Goroutine leak detection**: `go.uber.org/goleak` — prefer
  `goleak.VerifyTestMain(m)` once per package over per-test
  `goleak.VerifyNone(t)`; the per-test form has a documented false-positive
  interaction with `t.Parallel()` (uber-go/goleak#48). Cheap, high signal,
  almost no false positives once wired correctly. `IgnoreCurrent()`/
  `IgnoreAnyFunction()` are the escape hatches for incremental adoption on
  an existing repo with known pre-existing leaks.
- **Integration tests needing real infra** (a database, a message broker):
  `testcontainers-go` — GitHub-hosted runners have Docker preinstalled, no
  extra setup. Isolate into a separate job from unit tests (needs Docker,
  slower, shouldn't block the fast static-gate feedback loop).

## 5. Determinism

- **Toolchain pinning**: the `go` directive in `go.mod` plus `GOTOOLCHAIN`
  exported from it (compute-nop's Makefile already does this —
  `GO_TOOLCHAIN ?= go$(shell awk '/^go / {print $$2; exit}' go.mod)`) — copy
  this pattern into any script that shells out to `go`/tool-installs, so a
  developer's ambient Go version can never silently diverge from CI's.
- **Generated-code drift guard**: regenerate (proto/mocks/whatever codegen
  the repo has) and `git diff --exit-code` against the committed output.
  Catches both "forgot to regenerate" and the specific incident class
  stapler-squad's `generated-proto-guard.yml` documents: an agent or a rushed
  commit force-adding stale generated files to unblock a local build. This
  is a **guard-the-invariant** workflow — small, single-purpose, checks one
  thing that would otherwise only surface as a confusing runtime bug days
  later.
- **Reproducible builds**: `CGO_ENABLED=0` where possible (already the norm
  in compute-nop's Makefile), `-trimpath`, avoid embedding build timestamps
  unless intentional and hashed for cache-busting purposes. `-trimpath`
  strips module-cache/CWD paths but not GOROOT-relative stdlib paths — full
  byte-for-byte reproducibility additionally needs a pinned/vendored
  toolchain; this is a release-time verification step (build twice, diff
  hashes), essentially never a per-PR gate.
- **Toolchain pin maintenance tradeoff, stated explicitly**: `GOTOOLCHAIN`
  modes are `auto` (default, auto-downloads and GOSUMDB-verifies), `local`
  (never download — right for locked-down CI paired with a verified official
  toolchain install), or an exact pin (`go1.22.3`, full patch version
  required — a two-part version can 404 a nonexistent toolchain zip during
  `go mod tidy`, golang/go#62278). A toolchain pinned once and never bumped
  ships an unpatched compiler — treat the `go`/`toolchain` lines in `go.mod`
  as a dependency Renovate/Dependabot should manage, not a set-and-forget.
- **Formatting gate strictness ordering**: gofumpt ⊇ gofmt (superset), but
  gofumpt's import grouping differs from goimports'/`gci`'s — many teams run
  both. Adopting gofumpt mid-project mass-reformats and pollutes `git blame`;
  mitigate with one reformat commit plus a `.git-blame-ignore-revs` entry
  rather than avoiding the adoption.

## 6. CI architecture (the part that actually makes gates enforceable)

A gate that isn't wired into the merge-blocking path is decoration. Points,
roughly in order of leverage:

1. **Fail-fast static gate before the expensive test matrix.** Static
   checks (fmt/vet/lint/govulncheck/gosec) are seconds; tests are minutes.
   Run static first and abort on failure — `scripts/test-ci.sh` already does
   this (`make fmtcheck vet lint workflowcheck || exit $?` before tests run).
   Add govulncheck/gosec to that same fail-fast line once introduced.
2. **One Makefile target set, consumed by both local dev and CI.** The
   single most portable idea from stapler-squad: `make ci` runs the exact
   sequence CI runs; `make ready` is `make ci` plus anything CI has that
   local can't fully replicate (e.g. an external coverage-gate action).
   There is never a second, drifted definition of "green" living only in
   YAML. If compute-nop doesn't yet have a `make ci`/`make ready` target that
   the Rocket/newt pipeline's CI descriptor script literally shells out to
   (rather than reimplementing the step list), add one — this is the
   prerequisite that makes every gate above locally reproducible before push.
3. **The required-status-checks mechanism is the actual enforcement point,
   and matrix jobs break it silently.** On a GH-Actions-based repo, a
   workflow that passes but isn't in the branch's required-checks list
   blocks nothing — and a matrix produces one status name per leg, so branch
   protection literally cannot express "require every leg." The fix used by
   prometheus and tailscale: a synthetic aggregator job
   (`if: always()`, inspects `needs.*.result`, exits 1 on any
   failure/cancellation) is the one thing actually marked required. On a
   Rocket/Jenkins/newt repo (no GH Actions, like compute-nop): the analogous
   check is whatever merge-gate Rocket/newt exposes (a PR build's exit code
   gating mergeability) — verify new checks are wired into that exit code,
   not just printed to a log nobody reads.
4. **Local pre-commit/pre-push hooks are a fast-feedback optimization, never
   a substitute for the server-side gate** (they're bypassable with
   `--no-verify`). `lefthook` is the common Go-shop choice over Python
   `pre-commit` — single dependency-free binary, parallel execution. Split
   by cost: pre-commit ≤10s (format/lint on changed files), pre-push ≤2m
   (build/vet/test); anything slower belongs in CI only.
5. **Cache the module/build cache correctly or it's a liability, not a
   speedup.** `actions/setup-go`'s built-in cache keys off `go.mod` only by
   default — set `cache-dependency-path: '**/go.sum'` explicitly, and
   include OS *version* (not just OS) in any manual cache key: a
   documented incident (actions/setup-go#368) had a cache built on Ubuntu
   22.04 silently restored on 20.04, producing cryptic linker errors.
   Restoring `GOMODCACHE` does not re-verify sumdb checksums, so a cache
   shared across differing-trust branches is an integrity concern worth
   being deliberate about, not just a performance one.

## Output format when running this skill

Produce a **gap report**, not a rewrite:

1. Table: gate category → currently present? → tool/version if present →
   recommendation if absent, with priority (govulncheck and a race gate are
   near-mandatory; mutation testing and SBOM signing are optional/low
   priority for an internal service).
2. For each recommended addition: the exact command, whether it's a hard
   gate or advisory-to-start, and — for anything noisy on a mature repo — the
   ratchet-pattern invocation instead of a repo-wide enable.
3. Concrete diffs/files to add: `.golangci.yml` (start from
   `references/golangci.yml`), Makefile target additions, and any
   `make ci`/`make ready` consolidation needed.
4. Explicitly flag anything that would break the build immediately if
   enabled naively (pre-existing violation counts), rather than silently
   scoping it — the user decides whether to ratchet or fix-then-enable.

## Exemplar repos (verified against live workflow files, 2026-09)

Useful as a sanity check that a proposed gate set isn't over- or under-
shooting what mature Go projects actually run:

| Repo | Gates on | Notably does *not* gate on |
|---|---|---|
| [grpc/grpc-go](https://github.com/grpc/grpc-go/blob/master/.github/workflows/testing.yml) | dedicated `-race` leg + i386/arm64 legs, proto-drift as its own job, `govulncheck-action` across 5 submodules on push/PR/nightly | — |
| [tailscale/tailscale](https://github.com/tailscale/tailscale/blob/main/.github/workflows/test.yml) | staticcheck sharded 6 ways, 3 race-tagged shards + root-privileged race-integration job, `depaware` dependency-drift check, license-header test | fuzzing, govulncheck, coverage threshold |
| [hashicorp/terraform-plugin-framework](https://github.com/hashicorp/terraform-plugin-framework/blob/main/.github/workflows/ci-go.yml) | golangci-lint as its own job, cross-repo integration against real Terraform CLI version matrix | `-race`, fuzzing, govulncheck, coverage threshold (coverage is upload-only) |
| [prometheus/prometheus](https://github.com/prometheus/prometheus/blob/main/.github/workflows/ci.yml) | 4 golangci-lint invocations across build-tag variants, scoped `-race`, generated-parser/proto diff checks, fuzzing (PR-gated + nightly), govulncheck, synthetic status-aggregator jobs feeding branch protection | — (closest to the full stack this skill describes) |
| [cockroachdb/cockroach](https://github.com/cockroachdb/cockroach/blob/master/.github/workflows/github-actions-essential-ci.yml) | acceptance tests, generated-code drift, cross-repo ORM compat — via Bazel/EngFlow, not raw `go test` | contrast case: large monorepos sometimes replace the vanilla toolchain's CI story entirely rather than layering onto it |

Takeaway: **no single exemplar repo runs every gate in this skill** — even
prometheus doesn't hard-gate mutation testing or SBOM signing. Calibrate the
gap report's priority column against what a repo of comparable size/maturity
actually runs, not against the theoretical maximum.

## Provenance of this skill

Grounded in three sources, kept explicit so a future update knows what's
been verified vs. inherited: (1) a direct audit of stapler-squad's live CI
config (`.golangci.yml`, `lint.yml`, `build.yml`, etc.) — a mature,
actively-maintained Go+TS monorepo; (2) a dated (2026-09) web research pass
cross-checking tool versions, hard-vs-advisory gate conventions, and the
exemplar-repo table above against their live workflow files; (3) this
skill's own author running `govulncheck`/`gosec` against compute-nop while
authoring it, which is where the `govulncheck@latest` SSA-builder crash in
§2 was actually caught — a reminder that this skill's commands should be
re-verified against the target repo, not assumed to work from the doc alone.
