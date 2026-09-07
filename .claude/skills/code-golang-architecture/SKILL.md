---
name: code-golang-architecture
description: Apply Hexagonal Architecture, Clean Architecture, and Domain-Driven Design to Go package structure. Use when designing or reviewing a Go service's package layout, deciding how to split domain/application/adapter code, choosing between package-by-layer and package-by-feature, or right-sizing architecture for a Go project's actual complexity. Complements `code-architecture-best-practices` (language-agnostic principles) with Go-specific structural decisions.
---

# Go Package Architecture

Decision layer on top of two existing skill families — this skill does not re-derive their content,
it tells you which one to reach for and adds the Go-specific judgment calls none of them make.
`golang-design-patterns` (see its `references/hexagonal-architecture.md`, `clean-architecture.md`,
`ddd.md`) already has full file trees and code for all three styles — go there for the how.
`golang-depguard-architecture` already has ready-to-use linter rules for enforcement. This skill is for
*which style, how much of it, and what Go's own constraints (single-namespace packages, no import
cycles, small-interface culture) force you to decide differently than the Python/Java sections of
`code-architecture-best-practices`.

## Right-Size First

Apply the Reuse Check and the ladder from `code-architecture-best-practices` before picking a style
at all: a CLI or script under ~500 lines, or a service under ~1-2K lines with one storage backend,
does not need domain/application/adapter layers — a flat `internal/<name>/` package with a few files
is correct and `golang-project-layout` already says so ("NEVER over-structure small projects").
Layering earns its keep at multiple adapters (HTTP + gRPC + a worker), multiple bounded contexts, or
business rules complex enough to need isolated unit tests. State explicitly when you're skipping
layering — silent under-structuring is as much a review-blocking call as silent over-structuring.

Before adding a new port (interface), grep/ast-grep for one that already expresses the same
boundary. Go's small-interface culture means the common duplication failure mode isn't a copy-pasted
function, it's two near-identical single-method interfaces (`OrderRepository` vs `OrdersStore`)
defined at two call sites for the same concept.

## Extending Bad Architecture: Refactor, Isolate, or Extend

Same three-option framework as `code-architecture-best-practices` — refactor-first, isolate via
seam, or extend as-is, stated explicitly, never silently defaulted to "extend." The Go-specific
form of "isolate via seam": define a narrow interface at the *new* call site (per
`golang-structs-interfaces`'s "define interfaces where consumed") that only names the methods you
need from the legacy package, rather than exporting more of the legacy package or reworking it.

## Discover the Current Architecture First (kibitzer)

Before picking a target style or naming tiers, find out what the package structure *actually* is
today — don't design against a mental model that's drifted from the code. If `kibitzer` is
available (MCP connected, or `kibitzer` on `PATH`), it answers this with zero configuration:

| Question | MCP tool | CLI equivalent |
|---|---|---|
| Are there import cycles, layer-direction violations, or high-coupling packages right now? | `architecture_assessment` (`scope` to the package(s) under review — also renders a Mermaid dependency diagram) | `kibitzer run <dir> --trigger batch` (filter for `import-cycles`/`layering`/`coupling`) |
| Is a given type already a God Object — too many methods/fields for one struct? | `list_architecture_symbols` (`package: "<pkg>"`) | `kibitzer architecture export --path . --scope '<pkg-glob>' --dry-run --out /dev/null`, group the `symbols` array by `parent` and count |
| What exactly does one symbol look like right now? | `get_architecture_node` (`node: "<pkg>::<Type>.<Method>"`) | grep the `architecture export` JSON for the symbol id |

This runs with no `.claude/inspect.json` at all — it's the discovery step, not the enforcement step.
Two things it feeds directly:

- **The Refactor/Isolate/Extend decision above.** A package that `architecture_assessment` already
  flags for `component-deps`/`layering` is a bad "extend as-is" candidate — the violation you'd be
  adding to already exists and mechanical evidence beats a guess about how bad it is.
- **Which target style fits (below).** If the assessment shows the package already reads as
  vertical slices (each subpackage self-contained, cross-package imports rare), don't fight that by
  imposing a package-by-layer split; if it shows one flat package with growing fan-in, that's the
  signal to introduce layering at all, per Right-Size First above.

Degrades gracefully: if kibitzer isn't connected/on `PATH`, skip this silently and fall back to a
manual read of the package's imports (`go list -deps ./...` or just reading the files) — don't block
the review on kibitzer's absence.

## Three Styles, One Underlying Choice

Hexagonal, Clean Architecture, and DDD tactical patterns overlap heavily in Go — domain entities,
port interfaces, application/use-case orchestration, adapters — and mostly differ in directory
naming and framing, not in the dependency rule. The choice that actually changes your file layout is
orthogonal to which of the three you name:

| Axis | Package-by-layer | Package-by-feature (vertical slice) |
|------|-------------------|--------------------------------------|
| Layout | `domain/`, `application/`, `adapter/` at the top level | `order/domain`, `order/application`, `order/adapters`, `billing/domain`, ... |
| Encapsulation unit | The layer — but cross-layer types must be exported, so the layer boundary is convention, not compiler-enforced | The feature/bounded context — a rename or refactor inside `order/` never touches `billing/` |
| Go fit | Go has no `private`/`protected`; the **package** is the only real encapsulation boundary, so a layer package spanning many features leaks types across features by construction | Matches Go's package-as-boundary model directly |
| Best for | A single bounded context, one team, one deploy unit | 2+ bounded contexts, or a service that will be split later |
| Maps to | `golang-design-patterns/references/hexagonal-architecture.md`, `clean-architecture.md` | `golang-design-patterns/references/ddd.md` ("Project Structure" section) |

Default to package-by-feature once a second bounded context appears — it's strictly harder to
retrofit than to start with, and Go's lack of intra-package visibility modifiers means a
package-by-layer `domain/` package for three unrelated features gives up encapsulation between
those features that package-by-feature keeps for free.

## DDD Tactical Patterns — Go Mapping

Full code examples: `golang-design-patterns/references/ddd.md`. Table for quick lookup during review:

| Concept | Go shape | Rule |
|---|---|---|
| Entity | Struct with an ID field, mutated only through methods | Identity, not attribute equality |
| Value Object | Struct with unexported fields, no ID, returned by value or via a validating constructor | Immutable; `Add`/`With...` return a new value, never mutate in place |
| Aggregate | An entity whose exported methods are the only mutation path for its children | External code never reaches into `order.items` directly — no exported field, only `order.AddItem(...)` |
| Repository | Interface defined in the domain/consumer package; implemented in an adapter package | One per aggregate root; domain never imports the concrete implementation |
| Domain Service | A function or small stateless struct in the domain package | Only when logic genuinely spans multiple aggregates — don't reach for this before an entity method covers it |
| Application Service / Use Case | A struct depending only on domain ports, one method per use case (or a `Handle` method per command/query type) | No business logic here — it orchestrates; if a use case has an `if` on a business rule, that rule belongs on the entity |

Skip tactical DDD (explicit Aggregate/Repository/Domain Service vocabulary) below ~5K lines or a
single bounded context — plain entities plus a couple of interfaces get you the same testability
without the ceremony. Introduce it when a second bounded context or a genuinely cross-aggregate rule
shows up, not before.

## Enforcing the Boundaries Mechanically: kibitzer vs depguard

Once package tiers or bounded contexts are named — using the discovery step above, not guessed —
don't rely on review comments to catch a stray import. Two mechanisms cover overlapping ground; know
which one you're picking and why, since configuring both for the same tier split just doubles the
maintenance surface for one signal.

| | kibitzer | `golangci-lint` (depguard / arch-go / go-arch-lint) |
|---|---|---|
| Config | `.claude/inspect.json`'s `architecture.dependency_rules`/`content_rules`/`naming_rules` — same file the discovery step above already reads, so naming tiers there is a one-time cost | `.golangci.yml` — `golang-depguard-architecture` has ready-to-use rule blocks; `arch-go`/`go-arch-lint` for content/naming rules, same skill has the comparison |
| How it runs | `architecture_assessment`/`run_checks` (MCP) or `kibitzer run <dir> --trigger batch` (CLI) — agent- or editor-time, on demand | `golangci-lint run` — whatever already gates your CI |
| Gates a PR without new CI wiring | Only if kibitzer's CLI/MCP is already part of the pipeline | Yes, if `golangci-lint` already runs in CI — most Go repos already do |
| Language scope | Go, TS/TSX/JS, Java, Kotlin, Python — same config works across a polyglot repo | Go only |
| Works before any rule is configured | Yes — `architecture_assessment` reads current violations with zero config (the discovery step) | No — depguard/arch-go only flag what a rule already names |

**Default:** use kibitzer for the free discovery pass above every time it's available — there's no
setup cost. For the CI gate itself, pick whichever mechanism needs zero *new* tooling: `depguard` if
`golangci-lint` already runs in CI (the common case), kibitzer's checkers if this repo already scripts
kibitzer into CI/pre-commit and adding `golangci-lint` would be the new dependency instead. If you
configure both, classify tiers once and mirror the same split into `.claude/inspect.json` and
`.golangci.yml` — don't let two independently-maintained tier lists drift apart. Configure whichever
you pick only after the layout has settled: rules are only as good as the tier classification, and
that needs real packages to classify.

## Testing Boundaries (Go-Specific)

| Layer | Test type | Approach |
|---|---|---|
| Domain (entities, value objects) | Unit | Table-driven, no mocks — pure functions and methods |
| Application (use cases) | Unit | Hand-written fakes or `mockgen` against the small port interfaces — see `golang-testing` |
| Adapters (repositories, clients) | Integration | Real dependency via `testcontainers-go`, or a recorded-HTTP fixture for external APIs |
| Composition root (`cmd/`) | Smoke | One test that wires the real dependency graph and calls a use case end-to-end — catches wiring mistakes unit tests can't |

## Common Go-Specific Mistakes

- **Ports defined next to their implementation, not their consumer.** Forces the consumer package to
  import the adapter package for the interface, which is often the exact cycle the layering exists
  to prevent. See `golang-structs-interfaces`'s "Define Interfaces Where They're Consumed."
- **A shared `types.go`/`models.go` imported by every layer.** Nothing in Go stops any layer from
  reaching into it, so it silently defeats the dependency rule — split domain types into the domain
  package and DTOs into the layer that owns them.
- **Domain structs carrying ORM struct tags** (`db:"..."`, `gorm:"..."`). Couples the domain type to
  a specific persistence library and usually forces exporting fields that should stay behind
  methods. Keep a separate persistence-layer struct and map between them in the adapter.
- **Stuttering names across the boundary** (`order.OrderService`, `order.OrderRepository`). See
  `golang-naming`; the package name already carries "order" — the boundary/layering conventions here
  don't override normal Go naming rules.
- **Interfaces created before a second implementation or a test needs one.** Applies doubly at
  architecture boundaries — a `Repository` interface with exactly one caller and one implementation
  is speculative layering, not hexagonal architecture. Wait for the second adapter or the first unit
  test that needs a fake.

## Decision Guide

| Situation | Move |
|---|---|
| New service, single bounded context, one storage backend | Flat `internal/` package, no layers — revisit if it grows |
| New service, multiple entry points (HTTP + gRPC + worker) sharing logic | Hexagonal — ports + primary/secondary adapters |
| New service, 2+ bounded contexts or an eventual split into separate services | DDD vertical slices, package-by-feature |
| Existing flat package outgrowing itself | Refactor-first if small, isolate via a port at the new call site if not — never bolt on a 6th responsibility |
| Domain package importing an ORM, HTTP, or config package | Violates the dependency rule — extract a port interface (`golang-depguard-architecture` Step 4 has the exact before/after) |
| Two interfaces expressing the same concept at two call sites | Reuse Check failure — consolidate before adding a third |
| Repository/Aggregate vocabulary appearing in a single-entity CRUD service | Overkill — plain entity + one repository interface, skip the rest of tactical DDD |

## Related Skills

| Skill | When to reach for it |
|---|---|
| `code-architecture-best-practices` | Language-agnostic SOLID/Clean/Hexagonal/DDD principles this skill specializes for Go |
| `golang-design-patterns` | Full file trees and code examples for Hexagonal, Clean Architecture, and DDD in Go |
| `golang-project-layout` | Module/directory conventions (`cmd/`, `internal/`, `pkg/`), workspaces, project-type selection |
| `golang-structs-interfaces` | Interface placement, size, and "accept interfaces, return structs" |
| `golang-naming` | Package and identifier naming, avoiding stutter |
| `golang-depguard-architecture` | Turn the dependency rule into a linter failure; standalone-tool comparison |
| `type-driven-design` | Make aggregate/value-object invariants compiler-enforced instead of review-enforced |
| `golang-testing` | Table-driven tests, fakes/mocks for port interfaces, `testcontainers-go` |
| `code-hotspot-analysis` | Check whether a package is already a churn/complexity hotspot before restructuring it |
| `code-review` | Verify a layout decision meets these rules before merging |
