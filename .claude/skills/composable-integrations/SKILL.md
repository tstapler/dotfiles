---
name: composable-integrations
description: This skill should be used when the user asks to design a plugin system, add an integration, create an extension point, compose providers, define a connector or adapter interface, use ConnectRPC for integrations, or design secure config.d-based integration discovery and lifecycle.
version: 0.1.0
---

# Composable Integrations

Design integrations as versioned, capability-scoped systems rather than as arbitrary code loaded into the host process.

## Start with the boundary

Identify which extension model fits before defining APIs:

| Need | Preferred mechanism |
|---|---|
| First-party implementation with shared release cadence | Static adapter crate/package |
| Independently deployed integration service | Versioned ConnectRPC control-plane contract |
| Isolated local executable | Supervised subprocess with versioned RPC contract |
| Third-party executable code | Signed, capability-restricted process or WASM boundary |
| Configuration-only variation | Typed config records plus a static registry |
| Event fan-out | Durable outbox and idempotent consumer contract |

Do not use a dynamic Rust ABI. Rust trait objects and `cdylib` interfaces are not stable cross-version plugin contracts. For runtime extensibility, prefer ConnectRPC over a supervised process boundary or a narrow WASM ABI.

## Core architecture

Keep dependencies pointing inward:

```text
host domain/core
  ├── versioned integration protocol and capability model
  ├── durable jobs and idempotency/fencing primitives
  └── integration registry
          ↑
config resolver → integration adapter/process → external system
```

- Core owns domain types, integration IDs, capability declarations, durable job state, retries, and error taxonomy.
- An integration owns only its external wire protocol, request/response translation, and declared capabilities.
- Never import an external SDK directly into domain logic.
- Prefer small capability interfaces (`deliver`, `provision`, `inspect`) over one large integration interface.

## ConnectRPC contract rules

Use ConnectRPC for a **control plane** or remote adapter protocol when the integration can evolve independently.

1. Version package and service names from the start, e.g. `example.integrations.v1`.
2. Make capability discovery explicit:
   - contract version/revision;
   - supported operations;
   - enabled/disabled state;
   - maximum request sizes and supported auth modes.
3. Include `request_id` and idempotency semantics on every state-changing operation.
4. Use compare-and-set versions for mutable remote registrations.
5. Keep wire DTOs separate from core domain models. Map caller-controlled fields to explicit request fields; do not deserialize directly into internal state.
6. Define retry classes: permanent validation/auth failures vs retryable availability failures vs outcome-unknown mutations requiring reconciliation.
7. Specify deadlines, pagination bounds, response-size limits, and request-size limits in the contract.
8. Return structured, non-secret errors. Never relay unbounded remote error bodies into logs or user output.

The data plane may remain a direct webhook/HTTP delivery protocol where appropriate; do not force every high-volume event through a control-plane RPC service.

## Config composition and discovery

Use deterministic layered configuration:

```text
typed defaults
→ core conf.d fragments (lexical order)
→ approved integration bundle fragments (bundle name, then lexical order)
→ restricted environment scalar overlay
→ persisted runtime overrides
```

Rules:

- State table/map deep-merge and array replacement semantics explicitly. An array of integration records needs one owning fragment; never assume element-wise merge.
- Require stable, user-chosen integration/subscription IDs. Never derive durable identity from array position.
- Separate base human-owned fragments from machine-owned runtime state. Runtime overrides must be atomic, versioned, and independently validated before activation.
- Each integration declaration must include an ID, kind, version/compatibility range, non-secret endpoint identity, capability selection, and secret reference—not a plaintext credential.
- Validate references, IDs, capability combinations, URLs, sizes, and duplicate IDs before process/client initialization.
- Build a complete validated replacement registry off-path; atomically publish it only after validation succeeds. Preserve the last known-good registry on failure.

## Bundle admission and lifecycle

Treat integration bundles, manifests, config fragments, and helper executables as a supply-chain trust boundary.

Require:

- canonicalized, contained discovery roots; reject unsafe symlinks/traversal;
- strict manifest schema with unique name/version/provided capability declarations;
- explicit allowlist or signature/provenance verification before activation;
- immutable version pin/digest for remotely acquired bundles;
- capability grants per integration, with separate read/write/destructive scopes;
- process-level filesystem, network, process, and credential restrictions where the platform supports them;
- startup handshake, health check, bounded timeout, supervised shutdown, and kill switch;
- deterministic conflict/priority rules when two integrations claim a capability.

Do not put plugin `bin/` directories on global `PATH`. Resolve a helper through its admitted bundle identity and canonical absolute path. Pass secrets only through a secret manager, OAuth flow, or narrowly scoped environment/file descriptor—not CLI arguments, config fragments, logs, or durable job records.

## Durable events and retries

For outbound/event integrations:

1. Persist the canonical non-secret payload before acknowledging the source event.
2. Persist stable integration ID, event ID, non-secret endpoint/config fingerprint, attempt count, due time, and a lease fence.
3. Never persist resolved secret bytes, secret references unless operationally necessary and approved, HMAC signatures, authorization headers, cookies, or response bodies.
4. Claim work with an opaque lease token plus monotonic generation; every completion/retry/dead-letter transition must compare both.
5. Resolve the current secret only in memory immediately before sending; regenerate request signatures for each attempt.
6. Treat routing/config drift as `BlockedConfig`, not a silent redirect to a new endpoint.
7. Document at-least-once semantics and preserve an event ID for receiver deduplication.

## Security review checklist

Before enabling an integration, answer:

- What code/data/credentials cross the boundary?
- Which capabilities are granted, and what is the blast radius?
- Who can install, configure, upgrade, disable, or invoke it?
- How is provenance verified and how is compromise revoked?
- Are external endpoints allowlisted and protected from SSRF/redirect abuse?
- Are state-changing requests idempotent and fenced against stale workers?
- Can an integration failure crash the host, exhaust resources, or corrupt durable state?
- Are secrets excluded from logs, diagnostics, durable jobs, telemetry, and process arguments?
- Is there an operator-visible health/error state and a kill switch?

## Tests required

- Contract compatibility fixtures across supported protocol versions.
- Manifest/config rejection: duplicate ID, unknown capability, invalid version, invalid path, untrusted origin.
- Capability denial and least-privilege tests.
- Deadline, bounded retry, error-redaction, and failure-isolation tests.
- Durable event tests: crash after enqueue, restart replay, claim contention, stale transition rejection, and receiver idempotency.
- Upgrade/downgrade and config-reload tests retaining last known-good state on failure.

## Related skills

Use `mcp-integration` for MCP transport/auth details, `plugin-structure` for Claude Code plugin packaging, `plugin-settings` for local plugin configuration, and `code-architecture-best-practices` for ports-and-adapters design.

Read the focused references when needed:
- `references/extension-models.md`
- `references/connectrpc-contracts.md`
- `references/config-composition.md`
- `references/security-and-lifecycle.md`
