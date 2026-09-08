# Pi extension intake audit

Snapshot: 2026-09-03

This is an intake inventory, not an approval or install manifest. See
`full-featured-profile-research.md` for the broader Claude Code parity survey
and proposed tiered profile. Commit IDs are upstream review anchors only. Nothing below may be provisioned until it has been
forked to `tstapler`, reviewed at the selected commit, and referenced from the
Pi config by the fork's exact commit. work-owned and Tyler-owned code are the
only exceptions to the fork rule.

## Initial shortlist

| Capability | Upstream and observed commit | License | Initial disposition | Review focus |
|---|---|---:|---|---|
| MCP and secure auth storage | `nicobailon/pi-mcp-adapter@6ba7d360fcc67a77ccbbb4921586614798020a7a` | MIT | Candidate, high-risk review | Spawns MCP processes, opens OAuth callback/network flows, and includes native keyring integration. Verify secrets never enter model context/logs and fail closed when secure storage is unavailable. |
| Parallel/subagents | `nicobailon/pi-subagents@358110f6d4f7d5981e045cdce5edec1b0ca00743` | MIT | Candidate | Child-process execution, inherited environment, workspace/session isolation, cancellation, concurrency limits, and artifact path traversal. |
| Web access | `nicobailon/pi-web-access@7ca5cdce4fdf33ddec3da4b1858215dcd0c0e382` | MIT | Candidate, opt-in | Broad outbound network and content ingestion. Confirm provider/key handling, SSRF/local-network controls, download limits, and overlap with work tooling. |
| Ask-user UI | `juicesharp/rpiv-mono@338b264c1ca4fd8828cc849b632f4f7ad88d2e78` package `rpiv-ask-user-question` | MIT | Candidate | Small UI surface; review config dependency and ensure prompts cannot forge trusted approval semantics. |
| Persistent todo UI | same `rpiv-mono` commit, package `rpiv-todo` | MIT | Candidate | Persistence paths, project data leakage, task mutation semantics, and config dependency. |
| LSP/lint feedback | `apmantza/pi-lens@528bb96eab3f0394b69d369909f104cdca1722a4` | MIT | Candidate, opt-in | Tool auto-discovery/execution, fix-on-save mutations, untrusted repository config, process limits, and platform support. |
| Visual plan/diff review | `backnotprop/plannotator@96313ab228ede843203d38d9d2a86e1c87e18c81` | Apache-2.0 | Candidate, opt-in | Compatible with the corrected `@earendil-works/pi-coding-agent@0.84.4` public pin. Review local web server/browser exposure and whether approval UI is security-significant. |
| Context reduction | `mksglu/context-mode@0ebbc2b6b64e171b16ab30dcc8b5c0a43429bc0b` | Elastic-2.0 | Hold | Not OSI open source, has an install-time script and native SQLite dependency, and rewrites/sandboxes tool output. Requires license decision plus deep fidelity/security tests. |
| Security audit workflow | `vigolium/piolium@d0da8965f468e0d9f2271c908f55ab4ecc4ac228` | MIT | Hold / on-demand only | High token/process fan-out and PoC generation are inappropriate for a universal always-on base. Evaluate as an explicitly invoked package after subagent policy exists. |
| Composio integration | `ComposioHQ/composio@abefd6962f2ec1e69a4e099c290551541fcb99a6` | MIT | Reject from universal base for now | Experimental Pi provider, hosted auth/tool execution, very broad third-party account access, and credential/service coupling. Reconsider only for an explicit opt-in profile with a threat model. |

## Dependency observations

- `pi-mcp-adapter` includes MCP SDKs, process spawning support, URL/opening
  support, and `@napi-rs/keyring`. Its keyring feature is relevant to the
  credential-provider requirement but does not make the package trusted by
  itself.
- `pi-subagents` pins its small runtime dependency set, but its core security
  boundary is process/environment/session delegation rather than dependency
  count.
- `pi-web-access` performs arbitrary outbound retrieval and document parsing;
  fetched content must remain untrusted data.
- `rpiv-mono` is a multi-package repository. A fork should provision only the
  reviewed packages and their required local config dependency, not telemetry,
  voice, web tools, or the entire suite by accident.
- `context-mode` uses `Elastic-2.0`, runs `scripts/postinstall.mjs`, and relies
  on `better-sqlite3`. It cannot enter the base through a routine MIT-style
  fork review.

## Required gate before enabling any candidate

1. Fork the exact upstream repository to the Tyler-owned GitHub namespace.
2. Record upstream URL, upstream commit, fork commit, license, package paths,
   and reviewer notes.
3. Inspect lifecycle scripts, network destinations, subprocess execution,
   filesystem writes, environment access, secret handling, and telemetry.
4. Run upstream tests from the fork commit and add threat-focused regression
   tests for the capabilities actually enabled.
5. Pin the Pi package source to the exact fork commit; mutable branches/tags and
   upstream npm packages are rejected by `PiConfigSource`.
6. Introduce candidates disabled or in an opt-in fragment first, then validate
   in a temporary Pi home before current macOS and Linux rollout.
7. Upgrades repeat this process; no automated upstream advancement.
