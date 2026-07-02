# ADR-004: Explicit API key auth in Phase 1 (OAuth token forwarding deferred)

**Date**: 2026-07-02
**Status**: Accepted
**Deciders**: Tyler Stapler
**Context**: mcp-context-filter Phase 1 — outbound authentication for upstream cloud connectors

---

## Context and Problem Statement

Admin-provisioned cloud connectors (Atlassian Rovo at `mcp.atlassian.com`, Slack at `mcp.slack.com`, etc.) require OAuth 2.1 Bearer tokens to authorize API calls. Two architectural choices exist for Phase 1:

**Option A — Explicit API key configuration**: User configures a long-lived API token (Atlassian API key, Slack bot token) in `mcp-proxy.toml`. Proxy injects it as `Authorization: Bearer <token>` on outbound HTTP requests.

**Option B — OAuth token forwarding**: Proxy attempts to intercept and reuse OAuth tokens that Claude Code would normally send to the admin-provisioned cloud connector.

---

## Decision

**Chosen: Option A — Explicit API key in `mcp-proxy.toml`.**

```toml
[servers.atlassian]
upstream_url = "https://mcp.atlassian.com/v1/mcp"
auth_token = "${ATLASSIAN_API_TOKEN}"   # env var expansion supported
```

---

## Decision Drivers

**Option B (OAuth forwarding) is infeasible in Phase 1:**

1. **Tokens are managed by `mcp-proxy.anthropic.com`**, not by Claude Code locally. Admin-provisioned connectors use `mcpsrv_` IDs. Their OAuth tokens are injected at the cloud-side Anthropic proxy layer — a local stdio subprocess receives no credentials from Claude Code for these servers.

2. **Token refresh is broken on the proxy path** (confirmed: anthropics/claude-ai-mcp Issue #228). Even if tokens could be accessed, the refresh mechanism is not ported to the proxy path. Local intercepted tokens would expire without renewal.

3. **S256 PKCE required** for any OAuth flow the proxy would need to initiate. This is a multi-week implementation: browser redirect flow, PKCE generation, token storage in macOS keychain, refresh logic. Out of appetite for Phase 1.

4. **No documented hook**: Claude Code has no documented mechanism to pass OAuth Bearer tokens to a stdio subprocess. The env vars in `.mcp.json` `env` block are for user-defined variables, not for Claude's managed auth state.

**Option A is sufficient for Phase 1:**
- Atlassian supports API tokens (per-user, long-lived) at `id.atlassian.com/manage-profile/security/api-tokens`
- Slack supports bot tokens with appropriate OAuth scopes
- Tokens stored in env vars or `.env` file, not in plaintext TOML

---

## Security Constraints

- `auth_token` value must never appear in logs. The logging layer must redact any field named `auth_token`, `authorization`, `bearer`, `token`, `api_key`, or `secret`.
- Tokens should be referenced via env var expansion (`${ATLASSIAN_API_TOKEN}`) rather than hardcoded in TOML.
- Future phase: once Atlassian MCP supports OAuth 2.1 PKCE directly without the claude.ai layer, implement the browser OAuth flow with macOS keychain storage.

---

## Consequences

**Positive**:
- Phase 1 scope is achievable in 1–2 weeks without the OAuth rabbit hole
- Explicit tokens are reliable and do not expire unexpectedly (until manually rotated)
- Users who already have Atlassian API keys and Slack bot tokens can deploy immediately

**Negative**:
- User must manually obtain and manage API tokens (one-time setup per server)
- Admin-provisioned connectors that require the claude.ai OAuth layer and have no direct API key option cannot be proxied — they must remain in `deniedMcpServers` or stay unproxied
- Token rotation requires manual update of `mcp-proxy.toml` (or env var)
