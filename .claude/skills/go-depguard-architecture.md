---
name: go-depguard-architecture
description: Configure depguard in golangci-lint to enforce hexagonal / clean architecture import direction in a Go project. Use when a Go codebase needs linter rules that prevent domain packages from importing adapters or infrastructure, services from importing global config, or adapters from cross-coupling. Examples — "add depguard rules for hexagonal architecture", "enforce that session package can't import server", "configure linter to enforce clean architecture tiers", "domain package is importing infrastructure, how do I prevent this".
---

# Go depguard: Enforcing Hexagonal Architecture with Import Rules

`depguard` is a `golangci-lint` linter that makes architectural layer boundaries mechanical — violations become build errors instead of review comments.

## ARGUMENTS

If invoked with a path argument (e.g., `/go-depguard-architecture ./session`), scope the tier mapping and generated rules to that package subtree. If invoked with a tier name (e.g., `domain`), focus the fix patterns on violations in that tier. If no argument, apply the full workflow to the entire project.

---

## Workflow — Do These Steps in Order

**Step 0 → Step 1 → Step 2 → Step 3 → Step 4 → Step 5 (if violations exist) → Step 6 (verify)**

Do not skip Step 0. Every subsequent step depends on the module path and package list it produces.

---

## Step 0: Discover Module Path and Package Layout

Before writing any rules, collect two facts about the project.

```bash
# 1. Get the module path — required for every pkg: entry in depguard rules
go list -m

# 2. List all packages — required to classify tiers accurately
go list ./... | sort
```

Record the module path (e.g., `github.com/tstapler/stapler-squad`). Substitute it for `MODULE` in every rule below. Do not use placeholder paths.

Then classify each package from `go list ./...` into one of the five tiers:

| Tier | Role | Allowed imports |
|------|------|-----------------|
| **domain** | Entities, port interfaces, business rules | stdlib only + own sub-packages |
| **application** | Use cases, orchestrates domain via ports | domain + stdlib |
| **adapter** | Implements ports for HTTP, DB, messaging | domain + application + infrastructure |
| **infrastructure** | Frameworks, drivers, config, logging | anything |
| **composition root** | Wires everything — `main.go`, `cmd/`, dependency builder | anything |

Write the tier mapping down before proceeding. Rules are only as precise as this classification.

---

## Step 1: The Core Mental Model

Dependencies point **inward only**. The composition root is the only code allowed to import all tiers.

```
┌──────────────────────────────────────────┐
│  Infrastructure / Adapters               │  ← imports app + domain + stdlib
│  (HTTP handlers, DB repos, config, log)  │
│  ┌────────────────────────────────────┐  │
│  │  Application / Services            │  │  ← imports domain + stdlib
│  │  (use cases, orchestration)        │  │
│  │  ┌──────────────────────────────┐  │  │
│  │  │  Domain                      │  │  │  ← stdlib only
│  │  │  (entities, port interfaces) │  │  │
│  │  └──────────────────────────────┘  │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
         cmd/main.go  ←  imports ALL tiers
```

`depguard` catches imports that cross this boundary in the wrong direction.

---

## Step 2: golangci-lint v2 Configuration

Add the following to `.golangci.yml`, substituting `MODULE` with the output of `go list -m` from Step 0. Adjust `files:` globs to match the actual package paths identified in Step 0.

**Two modes are available:**
- **deny-list** (`list-mode: deny`) — block specific bad imports. Simpler to start; misses future violations.
- **allow-list** (`list-mode: allow`) — only listed imports are permitted. Stricter; recommended for the domain tier.

```yaml
version: "2"

linters:
  enable:
    - depguard

  settings:
    depguard:
      rules:

        # ── RULE 1: Domain must be pure ────────────────────────────────────────
        # Use allow-list on the innermost tier — it catches any future bad import,
        # not just the ones you thought to deny today.
        # Allows: all stdlib, domain's own sub-packages.
        # Blocks: everything else (ORM, HTTP, config, logging, services, adapters).
        domain-is-pure:
          list-mode: allow
          files:
            - "**/domain/**/*.go"
            - "!**_test.go"
          allow:
            - pkg: "$gostd"
              desc: "domain may use the Go standard library"
            - pkg: "MODULE/domain"
              desc: "domain sub-packages may import each other"

        # ── RULE 2: Application services — no adapters, no infrastructure ──────
        # Services orchestrate use cases through domain port interfaces.
        # They must not reach into HTTP, DB clients, or framework packages.
        services-no-adapters:
          list-mode: deny
          files:
            - "**/server/services/*.go"
            - "**/app/**/*.go"
            - "**/usecase/**/*.go"
            - "!**_test.go"
          deny:
            - pkg: "MODULE/server/handlers"
              desc: "services must not import HTTP handlers — handlers depend on services, not the reverse"
            - pkg: "MODULE/server/middleware"
              desc: "services must not import HTTP middleware — add cross-cutting concerns via middleware wrapping in the adapter layer"
            - pkg: "MODULE/adapter/outbound"
              desc: "services must not import concrete adapters — depend on the port interface defined in domain instead"
            - pkg: "net/http"
              desc: "services must not import net/http — HTTP belongs in adapter/inbound; services receive decoded domain types"
            - pkg: "entgo.io/ent"
              desc: "services must not import the ORM — call the repository port interface; the adapter/outbound package implements it"
            - pkg: "github.com/gorilla/websocket"
              desc: "services must not import WebSocket libraries — websocket concerns belong in adapter/inbound"

        # ── RULE 3: Services and domain must not import global config ──────────
        # Each consumer should declare the configuration it needs as a narrow
        # interface or struct injected via constructor. Importing the full config
        # package couples services to every config field and makes them hard to test.
        no-global-config-in-inner-layers:
          list-mode: deny
          files:
            - "**/server/services/*.go"
            - "**/domain/**/*.go"
            - "**/session/*.go"
            - "!**_test.go"
          deny:
            - pkg: "MODULE/config"
              desc: >
                inject a scoped config interface instead of importing the global config package.
                Define: type StorageConfig interface { DatabasePath() string }
                Accept it in the constructor. The composition root (main.go / dependencies.go)
                splits the full Config struct into the scoped interface.

        # ── RULE 4: Inbound adapters must not import outbound adapters ─────────
        # HTTP handlers and other inbound adapters must route through the service
        # layer, not call DB repositories directly. This keeps the service layer
        # as the authoritative coordinator of use cases.
        adapters-no-cross-coupling:
          list-mode: deny
          files:
            - "**/server/handlers/*.go"
            - "**/adapter/inbound/**/*.go"
            - "!**_test.go"
          deny:
            - pkg: "MODULE/adapter/outbound"
              desc: >
                inbound adapters must not import outbound adapters.
                Route: handler → service interface → repository interface → DB adapter.
            - pkg: "entgo.io/ent"
              desc: "inbound adapters must not query the DB directly — call the service layer"
            - pkg: "database/sql"
              desc: "inbound adapters must not import database/sql — call the service layer"
```

---

## Step 3: Run and Triage Violations

```bash
# Baseline: count total violations
golangci-lint run --enable-only depguard ./... 2>&1 | tee /tmp/depguard-violations.txt
wc -l /tmp/depguard-violations.txt
```

```bash
# Break down by rule name
grep -oE "(domain-is-pure|services-no-adapters|no-global-config|adapters-no-cross-coupling)" \
  /tmp/depguard-violations.txt | sort | uniq -c | sort -rn
```

```bash
# List offending files
grep "\.go:" /tmp/depguard-violations.txt | cut -d: -f1 | sort -u
```

**Fix in this order** — later violations often disappear once earlier ones are fixed:

1. `domain-is-pure` — domain contamination cascades outward; fix it first
2. `no-global-config-in-inner-layers` — high leverage, low effort (extract a narrow struct)
3. `services-no-adapters` — requires introducing a port interface if one doesn't exist
4. `adapters-no-cross-coupling` — requires routing through the service layer

---

## Step 4: Fix Patterns by Violation Type

### domain importing the ORM or database/sql

```go
// ❌ Before — domain/session.go
import "entgo.io/ent/schema"

// ✅ After — define a port interface in domain
// domain/repository.go
type InstanceRepository interface {
    Load(ctx context.Context, id string) (*Instance, error)
    Save(ctx context.Context, inst *Instance) error
}

// adapter/outbound/ent/instance_repo.go — satisfies the interface implicitly
type entInstanceRepo struct{ client *ent.Client }

func (r *entInstanceRepo) Load(ctx context.Context, id string) (*domain.Instance, error) { ... }
func (r *entInstanceRepo) Save(ctx context.Context, inst *domain.Instance) error { ... }
```

### service or domain importing the global config package

```go
// ❌ Before — session/storage.go
import "github.com/tstapler/stapler-squad/config"

func NewStorage() *Storage {
    dir := config.GetConfigDir()
}

// ✅ After — declare only what you need; accept it via constructor
// session/storage.go
type StorageConfig interface {
    DatabasePath() string
}

func NewStorage(cfg StorageConfig) *Storage {
    dir := cfg.DatabasePath()
}

// cmd/main.go or server/dependencies.go — the only file that imports config
// appConfig (type *config.Config) already has DatabasePath() → satisfies StorageConfig
storage := session.NewStorage(appConfig)
```

### service importing net/http (HTTP bleeding into use cases)

```go
// ❌ Before — server/services/session_service.go
import "net/http"
func (s *SessionService) HandleWebhook(w http.ResponseWriter, r *http.Request) { ... }

// ✅ After — service receives decoded domain types; HTTP decoding lives in handler
// server/handlers/session_handler.go  (inbound adapter)
func (h *SessionHandler) HandleWebhook(w http.ResponseWriter, r *http.Request) {
    payload, err := decodeWebhookPayload(r)       // HTTP → domain type
    result, err := h.sessionSvc.ProcessWebhook(r.Context(), payload)
    encodeResponse(w, result)                      // domain type → HTTP
}

// server/services/session_service.go  (application layer)
func (s *SessionService) ProcessWebhook(ctx context.Context, p WebhookPayload) (*Result, error) {
    // pure orchestration — no HTTP types
}
```

### inbound adapter importing outbound adapter directly

```go
// ❌ Before — server/handlers/review_handler.go
import "github.com/tstapler/stapler-squad/adapter/outbound/postgres"

func (h *ReviewHandler) GetReview(w http.ResponseWriter, r *http.Request) {
    review, _ := postgres.GetReview(id)  // skips the service layer
}

// ✅ After — handler accepts a service interface; service calls the repository
// server/handlers/review_handler.go
type ReviewQuerier interface {
    GetReview(ctx context.Context, id string) (*domain.Review, error)
}

func NewReviewHandler(svc ReviewQuerier) *ReviewHandler { ... }
```

---

## Step 5: Incremental Adoption for Existing Codebases

When a codebase has many existing violations, introduce the rules without blocking CI immediately. Fix package by package, then make the check blocking when clean.

**Phase 1 — Baseline (shell):**
```bash
golangci-lint run --enable-only depguard ./... 2>&1 | tee /tmp/depguard-baseline.txt
echo "Baseline violation count: $(wc -l < /tmp/depguard-baseline.txt)"
```

**Phase 2 — Suppress known tech-debt with tracked comments (Go):**
```go
//nolint:depguard // TODO: extract StorageConfig interface — tracked in issue #123
import "github.com/tstapler/stapler-squad/config"
```

**Phase 3 — Add as a blocking CI check once violations reach zero (shell):**
```bash
# Confirm clean before enabling in CI
golangci-lint run --enable-only depguard ./...
echo "Exit code: $?"  # must be 0 before adding to CI gate
```

---

## Step 6: Verify Rules Are Actually Firing

Do not create temporary files in the source tree. Instead, check whether `depguard` is active on a file you know should be affected, using a known-bad import that already exists or a `//nolint` bypass count:

```bash
# Confirm depguard is enabled and producing output at all
golangci-lint run --enable-only depguard ./... 2>&1 | head -20

# Confirm a specific rule fires on a specific package
golangci-lint run --enable-only depguard ./domain/... 2>&1

# Check that a file with a known good import does NOT trigger a false positive
golangci-lint run --enable-only depguard ./cmd/... 2>&1
# cmd/ is the composition root — should produce zero depguard violations
```

**Done when:** `golangci-lint run --enable-only depguard ./...` exits 0 with no output (or only expected `//nolint` suppressions), and `golangci-lint run --enable-only depguard ./cmd/...` also exits 0 (confirming the composition root exemption works correctly).

---

## Reference: Principle Behind Each Rule

| Rule | Mode | Principle | Source |
|------|------|-----------|--------|
| `domain-is-pure` | allow-list | Dependency Inversion; ports defined by domain | *Clean Architecture* — Uncle Bob; Alistair Cockburn *Ports and Adapters* |
| `services-no-adapters` | deny-list | Separation of Concerns; Service Layer pattern | *POEAA* — Fowler |
| `no-global-config-in-inner-layers` | deny-list | Constructor Injection; narrow interfaces | *Dependency Injection: Principles, Practices, Patterns* — Seemann |
| `adapters-no-cross-coupling` | deny-list | Single Responsibility; service layer as coordinator | *Clean Architecture* — Uncle Bob; Dave Cheney *SOLID Go Design* |

**The goal:** the linter encodes your architecture decisions so they are enforced on every PR — not only when someone remembers to check during review.
