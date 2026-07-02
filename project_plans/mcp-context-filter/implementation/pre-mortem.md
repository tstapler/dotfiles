# Pre-mortem: mcp-context-filter
Date: 2026-07-02

## Failure Modes

### FM-1 (P1): Admin-provisioned OAuth connectors cannot be wrapped

**Failure:** The proxy cannot intercept or reduce tokens from admin-provisioned Slack/Atlassian connectors because those connectors use OAuth managed by Anthropic's cloud proxy (`mcp-proxy.anthropic.com`), not locally accessible Bearer tokens — the proxy can only wrap servers where the user holds their own API credentials.

**First symptom:** Phase 1 ships. `mcp-proxy init` reads `~/.claude/settings.json` and finds admin-provisioned server entries with no accessible upstream URL (they resolve through Anthropic's cloud layer, not a direct URL the local binary can connect to). The 42.6k-token baseline is unchanged. Success metric fails: "≥50% reduction" measures zero.

**Prevention:** Before Story 1.8.2 is written, empirically test what URL (if any) `settings.json` exposes for admin-provisioned servers. If the URL routes through `mcp-proxy.anthropic.com`, document the revised scope explicitly in plan.md: Phase 1 covers only servers where the user has direct API credentials. Revise the success metric baseline to exclude admin-provisioned connectors. If the intent is still to filter Slack/Atlassian, establish that the proxy must have the user supply their own Atlassian/Slack API keys as a first-class setup step, and validate that those API key–based tool catalogs match the admin-provisioned connector catalogs.

**Severity:** P1 — The entire problem statement ("admin-provisioned MCP cloud connectors consume 42.6k tokens") describes servers the proxy architecture cannot reach. Ships, doesn't solve the problem.

---

### FM-2 (P1): Phase 3 dynamic slots are invisible — Claude Code never re-fetches tools/list

**Failure:** After `search_tools` populates the active slot pool and the pool is reflected in the next `tools/list` response, Claude Code never issues another `tools/list` request mid-session (tool list is fetched once at initialization and cached). Dynamically discovered tools are never in Claude Code's registered tool list and are never callable.

**First symptom:** LLM calls `search_tools`, receives tool schemas as text in the result content, then attempts to call one of those tools by name. Claude Code returns "tool not found" or silently refuses to execute the call — because the tool is in the active slot pool and in the proxy's `tools/list` but not in Claude Code's session-start-cached tool registry. The `search_tools` call appears to succeed but all follow-on calls for discovered tools fail.

**Prevention:** Before Epic 3.2 is implemented, add a mandatory spike story: start proxy in Phase 3 mode, call `search_tools`, then immediately call a tool from the result via a scripted Claude Code session; observe whether Claude Code executes or rejects it. If Claude Code rejects it, the slot architecture is invalid. Pivot: `search_tools` returns schemas as text AND exposes a `call_discovered_tool(name, arguments_json)` meta-tool that the proxy forwards to upstream — bypassing the Claude Code tool registry entirely for discovered tools. Document the result of the spike as a decision gate before Epic 3.2 begins.

**Severity:** P1 — `notifications/tools/list_changed` is confirmed broken (Issue #13646), and without a re-fetch trigger, the entire Phase 3 active slot mechanism produces no callable tools. Phase 3 ships and fails silently.

---

### FM-3 (P1): Atlassian Rovo connection fails on first real integration test — SSE is already dead

**Failure:** The plan was written on 2026-07-02, one day after Atlassian's SSE transport end-of-life (June 30, 2026). If Streamable HTTP in rmcp 0.16 has any implementation gap against the live Atlassian endpoint (wrong content-type negotiation, missing `MCP-Protocol-Version` header, incorrect POST body format), there is no SSE fallback — Atlassian has disabled it — and the proxy cannot reach the 13k-token target that is 31% of the baseline.

**First symptom:** Story 1.4.1 integration test is run against a live Atlassian Rovo endpoint and returns a 400 or 405. Story 1.4.2 SSE fallback is attempted and returns a 404 or 410. Atlassian is permanently inaccessible through the proxy without a protocol fix.

**Prevention:** Elevate "verify Streamable HTTP connectivity against live Atlassian Rovo" into Task 1.1.1.0 as a co-equal go/no-go gate alongside the axum check. This test must pass before any other implementation begins. Add to Story 1.4.1 acceptance criteria: "connects to a live Atlassian Rovo endpoint and retrieves tools/list successfully" (not just a localhost mock). If this fails, stop and debug rmcp's Streamable HTTP client against Atlassian's actual endpoint before proceeding.

**Severity:** P1 — Atlassian is the largest single token consumer (~13k, 31% of the 42.6k baseline). If the proxy cannot connect to it, the primary success metric is unreachable.

---

### FM-4 (P2): axum version conflict forces separate workspace, silently breaking Phase 2 dashboard integration

**Failure:** rmcp 0.16 requires axum 0.7; claude-proxy-rs uses axum 0.8. The vendoring resolution requires manual re-patching on every rmcp update. The "fallback: separate Cargo workspace" path eliminates the shared type system between mcp-proxy and claude-proxy-rs, making Story 2.3.1's dashboard integration (`src/dashboard.rs`) architecturally impossible. Phase 2 ships metrics that are never visible in the dashboard.

**First symptom:** Task 1.1.1.0 reports axum 0.7. The implementer picks the separate workspace fallback as the path of least resistance. Epic 2.3 (Dashboard Integration) is never revisited; `mcp_filter_tokens_before` gauges are emitted to a file that the claude-proxy-rs dashboard process never reads.

**Prevention:** Run the axum check before any architecture decision is made about the metrics store. If the separate workspace path is taken, immediately update Epic 2.3 to define an IPC boundary (Unix socket, shared JSONL file, or metrics file path) between the two binaries. Document the chosen IPC mechanism in an ADR-001 addendum before Story 1.1.1 begins. Do not allow "emit to existing claude-proxy-rs metrics store" to remain in the plan if the binaries are separate processes.

**Severity:** P2 — Likely (rmcp/axum version conflicts are common in the Rust ecosystem). Recoverable by adding an IPC layer, but dashboards silently stop working if the separate workspace path is taken without updating Epic 2.3.

---

### FM-5 (P2): fastembed ONNX cold start blocks the MCP initialize handshake

**Failure:** The default-on `semantic-search` feature loads a ~23MB BGE-small ONNX model during binary startup, adding 3–8 seconds of blocking initialization latency on macOS before the stdio server can respond to `initialize`. Claude Code times out waiting for the handshake response and marks the proxy server as unreachable, making all Phase 3 installations appear non-functional on first session start.

**First symptom:** After installation with default features, the first Claude Code session shows all mcp-proxy tools as missing. `RUST_LOG=debug` output shows ONNX runtime initialization log lines before the `initialize` JSON-RPC response is written to stdout. Subsequent sessions may work if the OS page-caches the model file.

**Prevention:** Defer ONNX initialization to a background Tokio task that is spawned concurrently with the `initialize` response being sent. The `search_tools` handler checks whether the background init has completed (using a `tokio::sync::watch` channel); if not, it blocks with a 2-second timeout and falls back to BM25-only for that call. Add an integration test asserting: `initialize` response arrives within 500ms from binary launch with the default feature set enabled.

**Severity:** P2 — Likely on first session start (ONNX model not page-cached). Recoverable by making initialization non-blocking, but as written the default install is broken until cold-start latency is addressed.

---

## P1 Items (address before implementation)

- [ ] FM-1 (OAuth architecture) — Before Story 1.8.2: empirically verify whether admin-provisioned server entries in `settings.json` expose a usable upstream URL; revise success metric baseline and scope if they do not.
- [ ] FM-2 (Phase 3 slot visibility) — Before Epic 3.2: run a spike confirming Claude Code issues a second `tools/list` after a `search_tools` call; if it does not, replace the slot architecture with a `call_discovered_tool` meta-tool forwarding approach.
- [ ] FM-3 (Atlassian SSE dead) — Add to Task 1.1.1.0: live Atlassian Rovo Streamable HTTP connectivity test is a go/no-go gate co-equal with the axum version check.

## P2 Items (address before affected phase ships)

- [ ] FM-4 (axum conflict → separate workspace) — If Task 1.1.1.0 forces a separate workspace, update Epic 2.3 with an IPC boundary definition before Story 1.1.1 begins.
- [ ] FM-5 (ONNX cold start) — Before Phase 3 is default-on: move ONNX init to a post-initialize background task; add 500ms initialize latency integration test.
