# Security and Lifecycle

Discovery is not admission and admission is not activation:

```text
discover → parse → validate → verify provenance → evaluate policy
→ check compatibility → provision scoped identity → launch
→ negotiate → health check → activate
```

A candidate bundle never executes merely because it exists on disk or in a registry.

## Admission requirements

- Canonicalize discovery roots and enforce containment; reject unsafe symlinks and traversal.
- Parse a strict manifest with unique integration ID, version, provided capabilities, protocol range, and artifact digest.
- Verify signature/provenance and pin immutable artifact digest before activation.
- Evaluate operator policy and capability grants separately from manifest requests.
- Use an explicit conflict/priority rule for overlapping capabilities.

## Runtime controls

- Run third-party code out of process where possible.
- Apply least-privilege identity, egress allowlists, filesystem/process limits, and CPU/memory/concurrency caps.
- Issue short-lived scoped credentials; never pass broad host credentials, CLI secret arguments, or unbounded environment secrets.
- Resolve helper executables by admitted bundle identity and canonical absolute path—not ambient `PATH`.
- Require timeouts, health/readiness, drain, shutdown, disable, and quarantine/kill-switch behavior.
- Log admission, activation, grants, health, configuration changes, and privileged actions without secret or payload disclosure.

## Failure behavior

Contain integration failures: bounded retries, explicit retry classification, circuit breaking, backpressure, and per-integration bulkheads. Fail closed for provenance, authorization, integrity, or configuration validation failures. Do not execute, render, or follow instructions returned by an integration without treating them as untrusted data.
