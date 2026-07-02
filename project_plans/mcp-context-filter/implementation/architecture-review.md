# Architecture Review: mcp-context-filter
Date: 2026-07-02
Verdict: CONCERNS

Architecture constitution (ADR-000) not present — reviewed against SOLID, Clean Architecture, DDD, and PoEAA principles directly.

---

## Blockers

- [RESOLVED] **proxy.rs god module [Epics 1.3, 1.5, 1.6, 1.7, 3.2] — SRP violation** — Story 1.1.2 now creates `src/mcp_proxy/` with dedicated submodules: `pipeline.rs`, `allowlist.rs`, `upstream.rs`, `server.rs`, `config.rs`, `cache.rs`, `search.rs`, `slots.rs`. Task 1.1.2.2 defines `ToolListPipeline` and `ToolCallPipeline` traits in `pipeline.rs`; `server.rs` wires stages but owns none of them. All formerly-colliding tasks are redistributed: filter logic to `allowlist.rs`, forwarding to `upstream.rs`, slot management to `slots.rs`, token counting to `metrics.rs`.

- [RESOLVED] **ToolCatalog used as compression I/O type — illegal pipeline state [Story 2.1.1, Story 1.5.2]** — Domain Glossary now defines `RawCatalog` (struct, "never filtered or compressed") and `ProcessedCatalog` (struct, "filtered and/or compressed result") as distinct types. Task 1.5.1.1 declares `filter_catalog(catalog: &RawCatalog, ...) -> ProcessedCatalog`. Task 2.1.1.1 declares `SchemaCompressor::compress(catalog: RawCatalog) -> ProcessedCatalog`. Task 3.1.1.1 builds `BM25Index` from `&RawCatalog`. The compiler now enforces the pipeline ordering; all three original bug classes (re-compression, cross-stage type confusion, incorrect token baseline) are blocked at compile time.

---

## Concerns

- [ ] **AllowList = Vec\<String\> primitive obsession [Story 1.5.1, filter.rs]** — `AllowList` is a domain concept with invariants (uniqueness, case-sensitive matching, not-empty-after-parsing warning), but it is a raw `Vec<String>` type alias. Callers must perform ad-hoc string comparisons; deduplication is unchecked; there is no domain method. **Recommendation**: Newtype `struct AllowList(BTreeSet<String>)` with `fn allows(&self, name: &str) -> bool` and `fn from_config(names: Vec<String>) -> (AllowList, Vec<String>)` where the second element is the list of duplicate entries for WARN emission.

- [ ] **McpProxyConfig::validate() mixes structural parsing with network I/O [Story 1.2.2]** — AC2 requires `validate()` to attempt an HTTP HEAD request with a 5-second timeout. This embeds a network side-effect into what should be a pure structural validation step. Unit tests for config parsing now require a real (or mocked) HTTP server. **Recommendation**: Split into `McpProxyConfig::parse()` (synchronous, pure — checks missing fields, duplicate names) and `async fn McpProxyConfig::check_connectivity(&self)` (infallible, emits WARN per unreachable server). The `validate` CLI subcommand calls both in sequence; internal startup calls parse-only.

- [ ] **SchemaCache hardcodes std::time::Instant — clock injection missing [Story 1.5.2]** — `Arc<RwLock<Option<(ToolCatalog, Instant)>>>` bakes `std::time::Instant` into the cache struct. Testing TTL expiry (AC2: "cache invalid after 301s") requires either a real 301-second wait or `tokio::time::pause()`. The latter only works in single-threaded tokio test runtimes and conflicts with `RwLock` across threads. **Recommendation**: Add a `now: Arc<dyn Fn() -> Instant + Send + Sync>` field (defaulting to `|| Instant::now()`) to `SchemaCache`, passed from the constructor. Tests inject a `FakeClock`.

- [ ] **mcp-compressor evaluation ordered after compression implementation [Epic 2.2 vs Epic 2.1]** — Epic 2.1 implements the full `SchemaCompressor` (Stories 2.1.1 and 2.1.2). Epic 2.2 then evaluates whether `mcp-compressor` is a usable library dep. If ADR-007 concludes "use mcp-compressor," all Epic 2.1 work is throwaway. This is an inverted dependency; the build-vs-buy decision should gate the implementation, not follow it. **Recommendation**: Move Story 2.2.1 (mcp-compressor inspection) to a research task executable in parallel with Phase 1 (no code dependency). Mark Epic 2.1 stories as "conditionally proceed after ADR-007." This is already partially called out in Unresolved Questions but not reflected in the dependency graph.

- [ ] **ProxyMode::Observe vs dry_run: bool — dual mode representation [Story 1.5.1 AC2, Domain Glossary]** — The glossary defines `ProxyMode` as an enum with `Observe | Filter`. Story 1.5.1 AC2 uses `dry_run = true` in global config and passes `dry_run: bool` into `filter_catalog(catalog, allow, dry_run: bool)`. These are two representations of the same concept — the pass-through mode. Both will exist in the codebase simultaneously, requiring callers to synchronize them. **Recommendation**: Remove `dry_run: bool` from `filter_catalog`'s signature. Pass `ProxyMode` instead. Map the TOML `dry_run = true` field to `ProxyMode::Observe` during config parsing. The boolean flag also violates the "no boolean flag arguments" idiom (see Nitpick 1).

---

## Nitpicks

- `filter_catalog(catalog, allow, dry_run: bool)` is a boolean flag argument; should be `filter_catalog(catalog, allow, mode: ProxyMode)` once the ProxyMode duality concern above is resolved.
- `BM25Index::build(catalog)` is an associated function while `detect_drift(allow, catalog)` and `filter_catalog(catalog, allow, ...)` are free functions — inconsistent API style across the search/filter modules; prefer consistent associated-function convention or a `impl FilterService` / `impl SearchService` approach.
- `top_k`, `tool_expiry_turns`, and TTL seconds are untyped integers in config with no validation against zero or negative values. A `top_k = 0` would silently empty the active slot pool. Consider `NonZeroUsize` or explicit `> 0` validation in `parse()`.
- `init` subcommand parses `~/.claude/settings.json` by field path (`mcpServers[*].url`) with no typed struct; a breaking change to settings.json format will crash at runtime, not at compile time. Define a minimal `ClaudeCodeSettings` serde struct.
- Unresolved Question 1 (rmcp axum version compatibility) should be a Story 0 (pre-work) task in Epic 1.1, not a footnote — if axum 0.7/0.8 conflict exists, the workspace won't compile and nothing else matters.
