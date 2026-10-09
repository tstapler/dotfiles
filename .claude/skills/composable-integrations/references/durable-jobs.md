# Durable Jobs

The host owns durable state. An integration receives a leased execution request; it is never the sole record of outstanding work.

```text
queued → leased → running → succeeded
                 → retry_wait → queued
                 → failed | cancelled | dead_letter | blocked_config
```

Persist before dispatch:

- job ID and stable idempotency key;
- integration ID, immutable artifact/version, protocol version, and effective-config fingerprint;
- versioned non-secret input or immutable input reference;
- attempt/max-attempts, deadline, due time, and correlation ID;
- opaque lease token plus monotonic lease generation.

Every completion, retry, dead-letter, or cancellation update compares job ID, lease token, and generation. A stale worker discards its outcome after a failed fenced update.

Never persist resolved credentials, HMAC signatures, authorization headers, cookies, raw response bodies, or broad host config. Resolve scoped credentials in memory immediately before an integration call.

Assume at-least-once effects. Give the integration the same idempotency key on every retry and preserve an event/job identity for downstream deduplication. Retain readers/migrators for every nonterminal job payload version during upgrades. Explicitly decide whether jobs are pinned to an original integration digest or migrated through a reviewed compatibility path.
