# ADR-003: AWS SDK TLS Backend — aws-smithy-http-client with rustls-ring Feature

**Status**: Accepted
**Date**: 2026-06-17

## Context

The proxy uses `aws-sdk-bedrockruntime` for AWS Bedrock calls. As of 2025, the AWS SDK for Rust changed its default TLS backend to `aws-lc-rs`, which requires a C compiler and CMake at build time. The proxy's HTTP client (reqwest) uses `rustls` with `ring` by default. Running two different TLS crypto providers in the same process causes a panic at startup: "no process-level CryptoProvider".

This was tracked as GitHub issue #1264 (March 2025).

## Decision

Explicitly add `aws-smithy-http-client` with the `rustls-ring` feature to `Cargo.toml`:

```toml
aws-smithy-http-client = { version = "*", features = ["rustls-ring"] }
```

This forces the AWS SDK to use `ring`-backed rustls, matching reqwest's TLS backend and eliminating the startup panic.

## Alternatives Considered

| Option | Rejected because |
|--------|-----------------|
| Default `aws-lc-rs` backend | Requires CMake at build time (violates single-binary NFR-2.1 spirit; complicates CI); causes "no process-level CryptoProvider" panic at startup when combined with reqwest's ring-based rustls |
| Switching reqwest to `aws-lc-rs` | `aws-lc-rs` adds ~4MB to the stripped binary (vs ring); builds slower; no benefit for a proxy that needs neither FIPS compliance nor aws-lc-rs-specific features |
| `reqwest + aws-sigv4` (manual Bedrock signing) | Still pulls 4–5 smithy support crates; would require reimplementing STS/SSO credential refresh chains for FR-4.7, which is non-trivial — the SDK's automatic refresh is worth the compile cost |

## Consequences

- Cold release build cost: `aws-sdk-bedrockruntime` is one of the slowest-compiling AWS crates (known issue: awslabs/aws-sdk-rust #113); use a dev profile with `lto = false`, `codegen-units = 16` to speed iteration
- Binary size: `ring` saves ~4MB vs `aws-lc-rs` in the stripped binary; combined with disabled unused reqwest features (`default-features = false`), binary stays within NFR-1.2 (<30MB)
- `aws-sdk-bedrockruntime` and `aws-config` SDK calls are fully async — no `spawn_blocking` needed (FR-4.8's "dedicated thread pool" requirement was written against boto3's blocking interface and is moot in Rust)
- AWS SSO credential refresh via `aws sso login` subprocess must use `tokio::process::Command`, not `std::process::Command`, to avoid blocking the async runtime
