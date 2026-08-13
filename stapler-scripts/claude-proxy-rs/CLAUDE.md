# claude-proxy-rs / cmdcrush

Rust port of a compression pipeline that shrinks tool output, logs, and JSON
before it reaches an LLM context window. Two entry points: the `claude-proxy-rs`
HTTP proxy (`src/compression/engine.rs`, operates on `/v1/messages` request
bodies) and the `cmdcrush` CLI (`src/bin/cmdcrush/main.rs`, wraps a shell
command and compresses its captured output).

## Inspiration sources and technique adoption

This project is a from-scratch Rust reimplementation of ideas from a Python
predecessor plus external projects. When adding a compression feature,
check this table first — the technique may already be scoped upstream, or a
prior-art project may have solved an edge case worth stealing.

| Source | What it is | Technique attributed in this repo | Adoption status |
|---|---|---|---|
| `compactor.py` (in `stapler-scripts/claude-proxy`) | This project's own Python predecessor (pre-Rust-port). It is a thin proxy-integration wrapper around the `claw-compactor` PyPI package's `FusionEngine` (`claw-compactor==7.1.0`, pinned) — see the `claw-compactor` row below for what's actually inside that engine | Floor check before compressing, double-compression guard (skip if a Rewind marker is already present), tool-pair orphan guard, Rewind marker injection + `rewind_retrieve` tool injection | Adopted — ported in `src/compression/engine.rs` |
| [claw-compactor](https://github.com/open-compress/claw-compactor) (MIT, `open-compress/claw-compactor`, PyPI `claw-compactor`) | The upstream OSS library `compactor.py` depends on. Two layers: (1) a default 14-stage `FusionPipeline` run per-request by `FusionEngine.compress_messages()` — `QuantumLock`(3, KV-cache alignment: isolates dynamic content — dates/UUIDs/tokens — from system-prompt prefixes so Anthropic's prompt cache stays hit), `Cortex`(5, content-type + 16-language auto-detection router feeding all downstream stages), `Photon`(8, base64 image detect+downsize/reformat), `RLE`(10, path shorthand `$WS`, IP-prefix compaction, enum compaction), `SemanticDedup`(12, SimHash 3-shingle near-dup block elimination, intra+cross-message), `Ionizer`(15, JSON array statistical sampling with schema discovery + always-keep error items, 81.9% peak), `LogCrunch`(16, folds repeated INFO/DEBUG lines to occurrence counts while always preserving ERROR/WARN/FATAL/stack traces, normalizes timestamps to relative deltas), `SearchCrunch`(17, groups grep/rg output by file, dedupes, merges consecutive line ranges), `DiffCrunch`(18, folds unchanged diff context to ≤1 line per hunk edge), `StructuralCollapse`(20, import-block merge + repeated-assertion/pattern collapse), `Neurosyntax`(25, tree-sitter AST code compression — never shortens identifiers, regex fallback), `Nexus`(35, ML dual-head token keep/discard classifier, stopword-removal fallback without torch), `TokenOpt`(40, tokenizer-format normalization — strips markdown filler), `Abbrev`(45, NL abbreviation, text content only — never touches code/JSON); (2) a separate message-list-level orchestration layer (v8, explicitly "inspired by Claude Code['s compaction system]", not wired into the default `FusionEngine` pipeline) — `CachePrefixManager` (computes the longest stable prompt-cache prefix across compaction rounds), `ContentStripper` (replaces images/docs with placeholders before summarization), `CompactHooks` (pre/post-compaction plugin callbacks), `PlanReinjection`/`SkillReinjection` (re-inject active plan/tasks and recently-used tool schemas after compaction so they aren't lost), `TieredCompaction` (micro/auto/full 3-tier strategy gated on context-pressure %, with a circuit breaker), `ConversationSummarizer` (deterministic, LLM-free turn summarization), `ToolResultBudget` (age-based truncation keeping only the N most recent tool results intact) | Partial. Ported/parallel: `DiffCrunch`→`diff_compactor.rs`; `RLE`'s path-shorthand piece→`path_collapse.rs` (no IP-prefix or enum compaction); `Ionizer`→`smart_crusher.rs` (statistical field elision, narrower scope — now wired into `engine.rs` for `tool_result` JSON blocks, see gap log below); `text_compressor.rs`'s `dedup_consecutive_lines`/`dedup_log_timestamps` are a narrow slice of `LogCrunch` (no ERROR/WARN preservation, no occurrence-count folding). **Not ported:** `QuantumLock`, `CachePrefixManager` (this directly answers the open "investigate CacheAligner" TODO in `claude-proxy/README.md` — yes, upstream already has cache-boundary awareness via these two, and the Python proxy gets it for free since it runs the full default pipeline; the Rust port does not), `Cortex`, `Photon`, `SemanticDedup`, full `LogCrunch`, `SearchCrunch`, `StructuralCollapse`, `Neurosyntax` (beyond comment-stripping — no import/pattern collapse), `Nexus`, `TokenOpt`, `Abbrev`, and the entire message-list orchestration layer (this repo only compresses per-request; it has no session-level tiered compaction, summarization, or plan/skill reinjection) |
| [headroom](https://github.com/headroomlabs-ai/headroom) (`headroomlabs-ai/headroom`, Python/TS, "20% fewer tokens for coding agents, 60-95% fewer tokens for JSON") | Public OSS project, same problem space: compress tool outputs/logs/files/RAG chunks before the LLM sees them; ships as library, proxy, and MCP server | Content-type routing / dispatch idea behind `SmartCrusher` (statistical JSON field elision on large arrays) | Adopted — `src/compression/smart_crusher.rs`, wired into cmdcrush's JSON branch (tried before minify) |
| rtk (Rust Token Killer, `~/.claude/RTK.md`) | Tyler's separate token-optimizing CLI proxy | `never_worse`-guarded output caps + tee-to-disk archival pattern | Adopted — `src/compression/line_truncate.rs`'s `truncate_lines` + cmdcrush's `--archive-dir` mirror this; cmdcrush now also embeds a model-visible `Retrieve: hash=...` marker (reusing `format_rewind_marker`) in its compressed output and exposes `cmdcrush --retrieve <hash>` to fetch the archived original, matching the main proxy's `RewindStore` approach |

Closed gaps (kept as a record of what was implemented and where):
1. **CodeCompressor** (`src/compression/code_compressor.rs`) — implemented via tree-sitter: parses the declared language, excises every comment node, collapses blank lines left behind. Supports rust, python, javascript/jsx, typescript, tsx, go, bash, java, c, cpp. A shared `compress_fenced_blocks` helper applies it to fenced code blocks inside markdown/log text, used by both cmdcrush and `engine.rs`.
2. **SmartCrusher wired into `engine.rs`** — `try_smart_crush_tool_result()` now runs `SmartCrusher` on `tool_result` block content (string or `[{type:"text", ...}]` form) that parses as a JSON array of objects, e.g. `gh pr checks --json` output where every item repeats `name`/`event`/`headSha`. `inject_rewind_marker()` was extended to append a standalone text block for the marker when a compressed message has no existing text block (pure `tool_result` compression) so Rewind stays recoverable. Covered by `compression::engine::tests`.
3. **cmdcrush Rewind parity** — cmdcrush now appends a `[N compressed to M. Retrieve: hash=X]` marker (same format as the main proxy's `RewindStore`) directly into its compressed stdout/stderr when it archives an original, and `cmdcrush --retrieve <hash>` reads the archived original back from `--archive-dir`. The stderr path-print is kept alongside for human debugging.

Open gaps, roughly prioritized by expected win vs. effort (all sourced from the
claw-compactor row above unless noted):
1. **QuantumLock / CachePrefixManager** (cache-boundary awareness) — highest
   compounding value: stabilizing prefixes before Anthropic's prompt cache
   check means compression and the 90% cache-read discount reinforce each
   other instead of the cache getting busted by dynamic content near the top
   of `system`. No Rust equivalent exists at all yet.
2. **LogCrunch, full version** — `text_compressor.rs` only dedupes *exact
   consecutive* lines; it doesn't fold near-repeated INFO/DEBUG lines with an
   occurrence count, doesn't explicitly protect ERROR/WARN/FATAL/stack-trace
   lines from any future more-aggressive log stage, and doesn't relativize
   timestamps. Build/test log output is one of the largest real-corpus
   categories per `cmdcrush --history-stats`.
3. **StructuralCollapse** (import-block merge, repeated-assertion collapse) —
   complements the existing comment-stripping `CodeCompressor` without
   touching identifiers; safe, self-contained, no new deps.
4. **SemanticDedup** (SimHash near-dup block elimination) — catches
   near-identical (not just byte-identical) repeated blocks across a
   conversation; `dedup_consecutive_lines` only catches exact matches.
5. **RLE's IP-prefix / enum-compaction pieces** — `path_collapse.rs` only
   ports the `$WS` path-shorthand half of RLE.
6. **SearchCrunch, Cortex, Photon, Nexus, TokenOpt, Abbrev** — lower priority:
   SearchCrunch/Cortex would need explicit content-type detection this repo
   doesn't currently do generically; Photon (image resize) needs an image
   library dependency; Nexus needs either `torch` or accepting its
   stopword-only fallback; TokenOpt/Abbrev target markdown/NL filler, a
   smaller share of tool-output-heavy real-corpus traffic than the above.
7. **Message-list-level orchestration** (`TieredCompaction`,
   `ConversationSummarizer`, `PlanReinjection`/`SkillReinjection`,
   `ToolResultBudget`, `CompactHooks`) — a different scope than this repo's
   per-request compression (session-level, needs the full message history
   and a compaction trigger, not just the current request body). Worth a
   separate design pass, not an incremental stage addition.
8. **⚠️ Anthropic native context editing** (`context-management-2025-06-27`
   beta, `clear_tool_uses_20250919` edit) — server-side: the client declares
   a token trigger + "keep N most recent" policy via a top-level
   `context_management` body field + beta header, and Anthropic itself clears
   stale `tool_result` bodies before the prompt reaches the model. This is
   the single highest-value item on this whole list *if* it can be turned
   on — but **do not just inject the field**. `stapler-scripts/claude-proxy`
   (the Python predecessor) already hit this exact field with the direct
   Anthropic API: Claude Code sends a Bedrock-flavored `context_management`
   body field that the direct API rejects outright with
   `"context_management: Extra inputs are not permitted"`
   (`providers/anthropic.py:157-166`, tracks
   [claude-code#21612](https://github.com/anthropics/claude-code/issues/21612)) —
   the Python proxy's workaround is to strip the field before forwarding to
   Anthropic, not to inject/preserve it. Before implementing here: verify
   live against the real Anthropic Messages API (not Bedrock) whether adding
   `anthropic-beta: context-management-2025-06-27` *and* a correctly-shaped
   `context_management` block is accepted today, and whether that's the same
   shape Claude Code itself sends (it may not be — Claude Code's version may
   be Bedrock-specific and a proxy-authored one may need a different shape).
   A wrong shape here 400s every request, not just this feature — test
   behind a flag against the live API first.
9. **Text-noise pattern catalog expansion** (inspired by
   [LeanCTX](https://github.com/yvgude/lean-ctx), a Rust prior-art project
   with 95+ shell-noise regex signatures vs. this repo's handful) —
   lowest-risk item on this list: pure catalog growth in
   `text_compressor.rs`, same never-worse guard, same
   `compression_regression.rs` + `--history-stats` validation bar as every
   existing stage. Candidates: package-manager download/progress noise
   (`npm`/`cargo`/`pip`/`docker pull` layer status lines) not caught by the
   existing CR-collapse (which only handles single-line `\r` overwrites, not
   multi-line ANSI cursor-positioning like `docker pull`'s simultaneous
   per-layer progress).
10. **`tools[]` schema compaction** (inspired by
    [kompact](https://github.com/npow/kompact) and mcp-compressor — both
    compress tool *definitions*, an axis claw-compactor's list doesn't
    touch at all since Claude Code resends the full `tools[]` array every
    request) — flagged as a **research spike, not a commit**: naive
    TF-IDF-style description trimming risks removing information the model
    needs for tool selection (kompact's own README reports 20-27% quality
    loss doing this with LLMLingua-2). A lossless first cut mirroring
    `SmartCrusher`'s constant-field-elision (common boilerplate phrasing
    repeated across many MCP tool descriptions) would clear the "no new
    failure mode" bar; doesn't yet clear "root cause, not hypothetical"
    without a real MCP-heavy session's `tools[]` payload to measure against.

Before starting new compression work: re-check headroom's repo/docs, rtk's
command surface (`rtk gain --history`, `rtk discover`), claw-compactor's
`main` branch, and (per the 2026-08-10 external survey behind gaps 8-10
above) Anthropic's context-editing docs, [LeanCTX](https://github.com/yvgude/lean-ctx),
[kompact](https://github.com/npow/kompact), and
[LLMLingua](https://github.com/microsoft/LLMLingua) for techniques not yet
listed here — this table is a snapshot, not a standing sync.

## Methodology: evaluating a new compression feature

Every compression stage must clear this bar before being considered done —
mirrors how `collapse_carriage_returns` (CR-progress-bar collapsing) was
built and evaluated:

1. **State the root cause / observed waste.** Identify the actual byte
   pattern being wasted (e.g. `\r`-overwritten progress bars where only the
   final segment is ever visible on a real terminal) — not a hypothetical.
2. **Guard for correctness, not just size.** Every stage must be a no-op if
   it wouldn't shrink the input, and the top-level `TextCompressor::compress`
   has a hard safety net that never returns something longer than the
   original. New stages must preserve this invariant.
3. **Unit test the transform in isolation** (pure function, table-driven
   cases) *and* the full pipeline (`compress()` on realistic input) — both
   the "it transforms correctly" case and the "it doesn't fire when it
   shouldn't" case.
4. **Validate against real data, not just synthetic input.** Run
   `cmdcrush --history-stats` against real Claude Code transcripts
   (`~/.claude/projects/**/*.jsonl`) to measure actual before/after bytes by
   compression method. A feature can be mechanically correct (e.g. 94%
   savings on a synthetic progress-bar test) while moving real-corpus savings
   by a fraction of a percent — report both numbers, don't stop at the
   synthetic one.
5. **Check live invocation impact separately from historical replay.**
   cmdcrush persists OTel-style metrics per real invocation to
   `~/.cache/cmdcrush/stats.db` (table `otel_metrics`). Query it
   (`sqlite3` + `json_extract`) to see what's actually being saved day to
   day — this can differ sharply from `--history-stats` because of the
   `compress_floor_bytes` gate (default 1000 bytes) filtering out most small
   commands.
6. **Report honestly.** State the synthetic-test result and the real-corpus
   result side by side. A feature with low real-world impact is still worth
   shipping if it's cheap and safe, but say so plainly rather than
   overclaiming from the synthetic number.
7. **Guard against regression with a checked-in test.**
   `tests/compression_regression.rs` runs fixed fixtures (JSON array, fenced
   code block, unified diff, CR progress bar, long unique text) through the
   real `cmdcrush` binary and asserts both the never-worse invariant and a
   minimum savings percentage per method. This runs in normal `cargo test`
   (no network, no `#[ignore]`) — it exists specifically so a change that
   silently breaks or weakens a compression stage fails CI, since
   `--history-stats` alone depends on a live `~/.claude/projects` corpus that
   isn't checked in and isn't run automatically.
8. **Sanity-check fidelity with an LLM judge (manual only).**
   `tests/e2e_fidelity_judge.rs` compresses a fixture, then asks the `claude`
   CLI to compare original vs. compressed and report a 1-10 fidelity score
   plus any specific lost details. `#[ignore]`d by default (network + tokens
   + subjective); run manually with
   `cargo test --test e2e_fidelity_judge -- --ignored --nocapture` and read
   the printed verdicts — byte-count tests can't tell you *what* was lost,
   only whether bytes shrank.

## Toolchain gotchas (this environment)

- `cargo` is not on default `PATH`; resolve it via `rustup which cargo`
  (`/Users/tstapler/.rustup/toolchains/stable-aarch64-apple-darwin/bin/cargo`).
- The `rtk` shell hook rewrites bash commands and can break `cargo build`
  invocations — bypass by calling the resolved cargo path directly.
- A broken `RUSTC_WRAPPER=sccache` env var breaks compilation
  (`sccache: caused by: cannot find binary path`). Clear it per-invocation:
  `RUSTC_WRAPPER="" cargo build --release --bin cmdcrush --manifest-path <repo>/Cargo.toml`.
