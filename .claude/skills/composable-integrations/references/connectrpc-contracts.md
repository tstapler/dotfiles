# ConnectRPC Contracts

Use ConnectRPC as a versioned process boundary, not as a way to expose host internals.

## Contract layers

1. Control: `GetIntegrationInfo`, `CheckCompatibility`, `Health`, `Drain`.
2. Invocation: bounded integration-specific commands and queries.
3. Jobs: `ExecuteJob` with a host-owned durable idempotency key.

Version protobuf packages from the start, for example `integrations.platform.v1`. Additive fields are wire-compatible but may still be behaviorally incompatible; do not reuse field numbers or change a field's meaning.

## Minimum handshake

The plugin reports its immutable ID, artifact version/digest, protocol range, config schema version, and declared capabilities. The host checks required capability grants and compatible version ranges before routing work.

## Required boundaries

- Propagate deadlines, cancellation, trace/correlation IDs, and request-size limits.
- Use structured errors that declare retryability; never relay arbitrary remote bodies.
- State-changing requests carry an idempotency key and expected version where applicable.
- Use Unix sockets with restrictive ownership for colocated processes; use mTLS/workload identity for networked processes.
- The host, not the plugin, owns retry, circuit-breaking, durable state, and quarantine.
