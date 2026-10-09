# Extension Models

Choose the narrowest mechanism that meets isolation and deployment needs.

| Model | Use when | Avoid when |
|---|---|---|
| Static adapter | Same release cadence; first-party dependency | Third parties need independent upgrades |
| Registry + config | Behavior varies by declarative records only | Adapter needs new executable behavior |
| Supervised ConnectRPC process | Independent lifecycle, language/runtime isolation, versioned control plane | A simple in-process adapter is sufficient |
| WASM sandbox | Third-party code needs strong local isolation | Native SDK/process integrations are required |
| Webhook/event subscriber | One-way asynchronous notification | Query/control lifecycle is required |

Do not dynamically load native Rust trait objects. Rust does not promise a stable ABI for that boundary.

## Ownership

The host owns policy, admission, effective configuration, credentials, durable jobs, retries, and audit. An integration owns only translation to an external system and explicitly declared capabilities.

Use capability-oriented contracts such as `deliver`, `provision`, `inspect`, and `reconcile`; do not define one giant plugin interface.
