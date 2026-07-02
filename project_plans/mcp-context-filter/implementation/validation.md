# Validation Plan: mcp-context-filter

**Date**: 2026-07-02
**Phase**: Pre-implementation
**Test stack**: `cargo test` + `tokio::test`, `httpmock` for upstream mocking
**Coverage target**: `cargo tarpaulin --out Stdout` — ≥80% line coverage

---

## Happy Path Scenario

Given a Claude Code session with 42.6k tokens consumed by MCP tool schemas, when the user runs mcp-proxy with an allowlist config for Slack and Atlassian, then those servers expose only the allowed tool subset and session-start token usage drops by ≥50%.

---

## Requirement → Test Mapping

| REQ | Description | Unit: Happy Path | Unit: Error Path | Integration Test |
|-----|-------------|-----------------|-----------------|-----------------|
| REQ-1 | AllowList filters tools/list to configured subset | `allowlist_should_return_only_allowed_tools_when_upstream_returns_full_catalog` | `allowlist_should_return_empty_list_when_no_tools_match_allowlist` | `pipeline_should_expose_only_allowed_tools_when_proxying_live_upstream` |
| REQ-2 | ToolCallPipeline forwards tools/call transparently | `pipeline_should_forward_call_unchanged_when_tool_is_in_allowlist` | `pipeline_should_return_32601_error_when_tool_not_in_allowlist` | `pipeline_should_return_upstream_response_verbatim_when_tool_call_succeeds` |
| REQ-3 | RawCatalog → ProcessedCatalog type safety (no re-compression) | `filter_catalog_should_produce_processedcatalog_when_given_rawcatalog` | `filter_catalog_should_reject_already_processed_catalog_when_passed_as_raw` | — |
| REQ-4 | SchemaCache returns ProcessedCatalog without upstream call on cache hit | `cache_should_return_cached_catalog_when_within_ttl` | `cache_should_call_upstream_when_ttl_expired` | `cache_should_make_only_one_upstream_request_when_two_tools_list_arrive_within_ttl` |
| REQ-5 | mcp-proxy sync detects schema drift (new/removed tools) | `sync_should_report_added_tools_when_upstream_has_new_tools` | `sync_should_report_stale_tools_when_allowed_tool_absent_from_upstream` | `sync_should_diff_allowlist_against_live_upstream_when_server_is_reachable` |
| REQ-6 | Session-start log reports token counts before/after | `metrics_should_log_token_counts_when_filtering_completes` | `metrics_should_log_zero_saved_when_passthrough_mode_active` | `metrics_should_emit_tokens_before_and_after_when_session_starts_with_real_catalog` |
| REQ-7 | Phase 3 search_tools returns matching tools by BM25 query | `bm25index_should_return_correct_tool_in_top3_when_query_matches_description` | `bm25index_should_set_low_confidence_flag_when_query_has_no_keyword_overlap` | `search_tools_meta_tool_should_return_tool_schemas_as_json_when_called_via_mcp` |
| REQ-8 | Upstream unreachable returns clear error to Claude (not panic) | `upstream_should_return_32603_error_when_connection_times_out` | `upstream_should_return_32603_with_server_name_when_host_unreachable` | `proxy_should_return_32603_json_rpc_error_when_upstream_port_closed` |

**Total tests: 22** (8 unit happy path + 8 unit error path + 6 integration)

---

## Test Naming Convention

`component_should_ExpectedBehavior_when_Condition`

All tests use `#[tokio::test]` for async cases. Sync unit tests use plain `#[test]`.

---

## Unit Test Detail

### REQ-1: AllowList Filtering

```
allowlist_should_return_only_allowed_tools_when_upstream_returns_full_catalog
  Given: RawCatalog with 38 Slack tools; AllowList = ["slack_send_message", "slack_read_channel"]
  When:  filter_catalog(&catalog, &allow, dry_run=false)
  Then:  ProcessedCatalog.tools.len() == 2; tool names match exactly

allowlist_should_return_empty_list_when_no_tools_match_allowlist
  Given: RawCatalog with tools ["foo", "bar"]; AllowList = ["baz"]
  When:  filter_catalog(&catalog, &allow, dry_run=false)
  Then:  ProcessedCatalog.tools.len() == 0 (no panic)
```

### REQ-2: ToolCallPipeline

```
pipeline_should_forward_call_unchanged_when_tool_is_in_allowlist
  Given: AllowList includes "slack_send_message"; mock UpstreamClient returns Ok(result)
  When:  pipeline.call_tool("slack_send_message", args)
  Then:  UpstreamClient receives the identical name+args; Ok(result) returned to caller

pipeline_should_return_32601_error_when_tool_not_in_allowlist
  Given: AllowList = ["slack_read_channel"]; call for "slack_create_canvas"
  When:  pipeline.call_tool("slack_create_canvas", args)
  Then:  Err(ToolNotAllowedError) with code -32601; data.allowlist_hint is non-empty
```

### REQ-3: RawCatalog → ProcessedCatalog type safety

```
filter_catalog_should_produce_processedcatalog_when_given_rawcatalog
  Given: RawCatalog with 5 tools; AllowList = ["tool_a", "tool_b"]
  When:  filter_catalog(&raw, &allow, false)
  Then:  Returns ProcessedCatalog (not RawCatalog); contains exactly "tool_a" and "tool_b"

filter_catalog_should_reject_already_processed_catalog_when_passed_as_raw
  Given: A ProcessedCatalog value erroneously wrapped as RawCatalog input
  When:  Type system is exercised at compile time (not a runtime test)
  Then:  Compile error — ProcessedCatalog does not implement Into<RawCatalog>
  Note:  This is a type-safety verification test: assert the two types are distinct newtypes
         in code; the "test" is `cargo check` succeeding with the newtype definitions in place.
```

### REQ-4: SchemaCache

```
cache_should_return_cached_catalog_when_within_ttl
  Given: TTL = 300s; cache populated at t=0 with a known catalog
  When:  cache.get() called at t=10s (simulated via Instant mock)
  Then:  Returns the cached ProcessedCatalog; upstream call count remains 1

cache_should_call_upstream_when_ttl_expired
  Given: TTL = 300s; cache populated at t=0
  When:  cache.get() called at t=301s (simulated via time injection)
  Then:  Upstream is called a second time; cache refreshed with new catalog
```

### REQ-5: Schema Drift Detection

```
sync_should_report_added_tools_when_upstream_has_new_tools
  Given: AllowList = ["slack_send_message"]; upstream catalog = ["slack_send_message", "slack_huddle_start"]
  When:  detect_drift(&allow, &catalog)
  Then:  Returns vec![SchemaDrift::Added("slack_huddle_start")]

sync_should_report_stale_tools_when_allowed_tool_absent_from_upstream
  Given: AllowList = ["slack_create_canvas_v1"]; upstream catalog = ["slack_create_canvas_v2"]
  When:  detect_drift(&allow, &catalog)
  Then:  Returns vec![SchemaDrift::Removed("slack_create_canvas_v1"), SchemaDrift::Added("slack_create_canvas_v2")]
```

### REQ-6: Session-start Metrics Logging

```
metrics_should_log_token_counts_when_filtering_completes
  Given: RawCatalog serializes to ~9500 tokens; ProcessedCatalog to ~1800 tokens
  When:  emit_session_start_log("slack", &raw, &processed)
  Then:  Log line matches pattern: "session_start server=slack filtered=30/38 tokens_before=9500 tokens_after=1800 pct_saved=81%"

metrics_should_log_zero_saved_when_passthrough_mode_active
  Given: ProxyMode::Observe (dry_run=true); same catalogs as above
  When:  emit_session_start_log("slack", &raw, &processed)
  Then:  Log line contains "pct_saved=0%" or "dry-run mode — no filtering applied"
```

### REQ-7: BM25 Search

```
bm25index_should_return_correct_tool_in_top3_when_query_matches_description
  Given: BM25Index built over catalog including "slack_send_message" (desc: "Sends a message to a Slack channel")
  When:  index.search("send message", 5)
  Then:  "slack_send_message" is in results[0..3]

bm25index_should_set_low_confidence_flag_when_query_has_no_keyword_overlap
  Given: Index with normal tool descriptions
  When:  search_tools_handler({"query": "xyzzy frobulate", "top_k": 3})
  Then:  Response JSON includes "low_confidence": true
```

### REQ-8: Upstream Unreachable

```
upstream_should_return_32603_error_when_connection_times_out
  Given: UpstreamClient configured with 5000ms timeout; mock that never responds
  When:  client.list_tools().await (with tokio::time::timeout)
  Then:  Err with code -32603; message contains "timeout after 5000ms"; elapsed < 5100ms

upstream_should_return_32603_with_server_name_when_host_unreachable
  Given: upstream_url points to a closed port
  When:  UpstreamClient::connect(config).await
  Then:  Err containing the server name and a "hint" field with diagnostic URL
```

---

## Integration Test Detail

| Test | Setup | External call | Assert |
|------|-------|---------------|--------|
| `pipeline_should_expose_only_allowed_tools_when_proxying_live_upstream` | `httpmock` server returns 38-tool JSON; AllowList = 2 tools | `GET /mcp` (httpmock) | Response body tool count == 2 |
| `pipeline_should_return_upstream_response_verbatim_when_tool_call_succeeds` | `httpmock` returns fixed tool result JSON | `POST /mcp` (httpmock) | Proxy response body == mock response body byte-for-byte |
| `cache_should_make_only_one_upstream_request_when_two_tools_list_arrive_within_ttl` | `httpmock` with request counter; TTL = 60s | Two sequential `tools/list` within 1s | httpmock request count == 1 |
| `sync_should_diff_allowlist_against_live_upstream_when_server_is_reachable` | `httpmock` returns 40-tool catalog; allowlist has 38 | `GET /mcp` (httpmock) | Drift report shows 2 `Added` entries; 0 `Removed` |
| `metrics_should_emit_tokens_before_and_after_when_session_starts_with_real_catalog` | Full pipeline with a 5-tool RawCatalog; 2-tool allowlist | — (no network; catalog in-process) | INFO log captured via `tracing_test`; before > after; pct_saved > 0 |
| `proxy_should_return_32603_json_rpc_error_when_upstream_port_closed` | `httpmock` server stopped; upstream URL points to its port | Connection attempt (fails) | JSON-RPC error body has `"code": -32603`; message contains server name |
| `search_tools_meta_tool_should_return_tool_schemas_as_json_when_called_via_mcp` | BM25Index built; `search_tools` handler wired as rmcp tool | — (in-process rmcp test) | Tool result content is valid JSON array of ToolDefinition objects |

---

## UX Acceptance Tests (Surfaces 1–3)

| # | Surface | Criterion | Pass Condition |
|---|---------|-----------|----------------|
| UX-01 | Surface 1: Config file | Alphabetical server ordering | `[servers.atlassian]` appears before `[servers.slack]` in generated TOML |
| UX-02 | Surface 1: Config file | Per-server token estimate comments | Each server block header includes `# Before: / After: / saved` comment line |
| UX-03 | Surface 1: Config file | Restart reminder always present | Generated file header contains `!! Restart proxy to apply changes !!` |
| UX-04 | Surface 1: Error — typo in field name | Actionable error message | Parse error output contains the unknown field name and `did you mean` suggestion |
| UX-05 | Surface 1: Error — duplicate server block | Duplicate key error | Error message names the duplicate key and instructs user to merge blocks |
| UX-06 | Surface 2: `mcp-proxy init` | Token cost table printed | stdout includes a table with Total row showing tools, tokens, and % of 200k window |
| UX-07 | Surface 2: `mcp-proxy init` | OBSERVE mode confirmation | stdout contains "Running in OBSERVE mode" and no filtering is active |
| UX-08 | Surface 2: `mcp-proxy analyze` | USED vs NEVER CALLED breakdown | stdout lists tools grouped by call frequency; 0-call tools in NEVER CALLED section |
| UX-09 | Surface 3: `mcp-proxy sync` | New tools flagged with `[NEW]` | Drift output line for added tool contains `[NEW]` label and one-line description |
| UX-10 | Surface 3: `mcp-proxy sync` | Stale tools flagged with `[REMOVED?]` | Drift output for missing tool shows `[REMOVED?]`, last-seen date, and hint to run `--list-all` |

---

## Test Stack

```toml
# Cargo.toml dev-dependencies
[dev-dependencies]
httpmock     = "0.7"        # HTTP server mock for upstream integration tests
tokio        = { version = "1", features = ["macros", "rt-multi-thread", "time"] }
tracing-test = "0.2"        # Capture tracing/log output in unit tests for REQ-6 assertions
assert_matches = "1.5"      # Pattern-based assertions on enum variants (SchemaDrift)
```

**Test execution**:

```bash
cargo test                          # all unit + integration tests
cargo test --test integration       # integration tests only
cargo tarpaulin --out Stdout        # coverage report (target: ≥80% line)
```

**Mocking strategy**:
- Upstream HTTP servers: `httpmock::MockServer` per integration test (spins up a local server; no real network calls)
- Time injection for cache TTL: pass `tokio::time::Instant` as a parameter; use `tokio::time::pause()` + `tokio::time::advance()` in tests
- Log capture for REQ-6: `tracing_test::init_test_tracing()` + `assert!(logs_contain("tokens_before="))` pattern
- Type safety for REQ-3: verified by `cargo check` succeeding with newtype definitions; no runtime test needed

---

## Coverage Target

```bash
cargo tarpaulin --out Stdout --exclude-files "src/bin/mcp-proxy/main.rs"
```

- **Target**: ≥80% line coverage across `src/mcp_proxy/` and `src/bin/mcp-proxy/`
- **Excluded**: `main.rs` entrypoint (startup wiring only, no logic)
- **Priority modules**: `allowlist.rs`, `cache.rs`, `pipeline.rs`, `search.rs` — target ≥90% each
- **Measurement cadence**: Run in CI on every PR; block merge if coverage drops below 80%
