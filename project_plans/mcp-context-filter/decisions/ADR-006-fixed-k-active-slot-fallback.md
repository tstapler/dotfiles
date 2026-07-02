# ADR-006: Fixed-K active slot pool as primary Phase 3 registration mechanism

**Date**: 2026-07-02
**Status**: Accepted
**Deciders**: Tyler Stapler
**Context**: mcp-context-filter Phase 3 — dynamic tool registration after search

---

## Context and Problem Statement

Phase 3 dynamic tool discovery requires a mechanism to register tools found by `search_tools` so Claude Code can subsequently call them via `tools/call`. Two approaches were evaluated:

**Option A — `notifications/tools/list_changed` dynamic re-registration**: After `search_tools` returns results, the proxy sends `notifications/tools/list_changed` to Claude Code. Claude Code re-fetches `tools/list`, which now includes the newly activated tools. Tools expire by sending another notification as their active-set membership changes.

**Option B — Fixed-K active slot pool**: The proxy always exposes exactly K "active slot" tool entries in `tools/list`. Slots are initially empty (or filled with the most-called tools from session history). `search_tools` fills/replaces slots. Slots expire by quiet-turn counter.

---

## Decision

**Chosen: Option B — Fixed-K active slot pool as the primary (and only reliable) approach.**

`notifications/tools/list_changed` is implemented as a best-effort notification sent alongside slot updates, but **correctness must not depend on Claude Code processing it.**

---

## Decision Drivers

**`notifications/tools/list_changed` is confirmed broken in Claude Code CLI** (anthropics/claude-code Issue #13646). Claude Code does not re-fetch `tools/list` after receiving this notification. Community investigation (Gemini CLI Issue #13850) shows this notification was only recently added to Gemini CLI in 2025. Claude Code's support is explicitly unconfirmed and empirically observed as absent.

Building Phase 3 on a notification that Claude Code ignores would mean:
- `search_tools` returns results as tool schema text
- Claude Code cannot call those tools (they were never registered)
- The feature is entirely non-functional

The fixed-K slot pool is the proven fallback pattern (documented in atlassian-labs/mcp-compressor and Dumbris/mcpproxy literature). It works regardless of notification support.

---

## Implementation

```toml
[phase3]
enabled = false       # opt-in
top_k = 10            # number of active slots
tool_expiry_turns = 5 # quiet-turn eviction threshold
```

**Active slot lifecycle:**
1. Session start: `search_tools` meta-tool is always in `tools/list`; active slots are empty (or pre-filled from call history)
2. `search_tools(query)` called: BM25/hybrid search returns top-K tools; those tools are placed in active slots
3. Next `tools/list` response: includes `search_tools` + up to K active-slot tools
4. Each turn where a slot tool is not called: increment that slot's quiet-turn counter
5. When counter >= `tool_expiry_turns`: evict slot; tool disappears from next `tools/list`
6. `notifications/tools/list_changed` sent after step 3 and step 5 as best-effort — if Claude Code supports it, it gets an immediate update; if not, the next `tools/list` poll reflects the change

**Token budget impact:**
- Empty state: 1 tool (`search_tools` ~50 tokens)
- Full state: K=10 tools × ~180 tokens avg = 1,800 tokens
- Far below the 42.6k baseline and within the ≤10k target

---

## Consequences

**Positive**:
- Phase 3 functions correctly regardless of whether Claude Code supports `tools/list_changed`
- Token footprint is bounded and predictable: never more than K+1 tools in context
- LRU eviction prevents slot exhaustion
- Best-effort notification preserves compatibility with future Claude Code versions that do support the notification

**Negative**:
- Tools registered via `search_tools` require one turn before they are callable (must wait for next `tools/list` poll, unless notification is honored)
- Fixed K cap means if LLM needs more than K tools simultaneously, oldest are evicted
- Quiet-turn expiry is a heuristic; in long sessions the LLM may lose access to a tool it wanted to revisit
