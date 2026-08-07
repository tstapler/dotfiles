# claude-proxy-rs / cmdcrush

Rust port of a compression pipeline that shrinks tool output, logs, and JSON
before it reaches an LLM context window. Two entry points: the `claude-proxy-rs`
HTTP proxy (`src/compression/engine.rs`, operates on `/v1/messages` request
bodies) and the `cmdcrush` CLI (`src/bin/cmdcrush/main.rs`, wraps a shell
command and compresses its captured output).

## Inspiration sources and technique adoption

This project is a from-scratch Rust reimplementation of ideas from a Python
predecessor plus two external projects. When adding a compression feature,
check this table first — the technique may already be scoped upstream, or a
prior-art project may have solved an edge case worth stealing.

| Source | What it is | Technique attributed in this repo | Adoption status |
|---|---|---|---|
| `compactor.py` / FusionEngine | This project's own Python predecessor (pre-Rust-port) | Floor check before compressing, double-compression guard (skip if a Rewind marker is already present), tool-pair orphan guard, Rewind marker injection + `rewind_retrieve` tool injection | Adopted — ported in `src/compression/engine.rs` |
| [headroom](https://github.com/headroomlabs-ai/headroom) (`headroomlabs-ai/headroom`, Python/TS, "20% fewer tokens for coding agents, 60-95% fewer tokens for JSON") | Public OSS project, same problem space: compress tool outputs/logs/files/RAG chunks before the LLM sees them; ships as library, proxy, and MCP server | Content-type routing / dispatch idea behind `SmartCrusher` (statistical JSON field elision on large arrays) | Adopted — `src/compression/smart_crusher.rs`, wired into cmdcrush's JSON branch (tried before minify) |
| rtk (Rust Token Killer, `~/.claude/RTK.md`) | Tyler's separate token-optimizing CLI proxy | `never_worse`-guarded output caps + tee-to-disk archival pattern | Adopted — `src/compression/line_truncate.rs`'s `truncate_lines` + cmdcrush's `--archive-dir` mirror this; cmdcrush now also embeds a model-visible `Retrieve: hash=...` marker (reusing `format_rewind_marker`) in its compressed output and exposes `cmdcrush --retrieve <hash>` to fetch the archived original, matching the main proxy's `RewindStore` approach |

Known gaps (all closed as of this writing — kept here as a record of what was implemented and where):
1. **CodeCompressor** (`src/compression/code_compressor.rs`) — implemented via tree-sitter: parses the declared language, excises every comment node, collapses blank lines left behind. Supports rust, python, javascript/jsx, typescript, tsx, go, bash, java, c, cpp. A shared `compress_fenced_blocks` helper applies it to fenced code blocks inside markdown/log text, used by both cmdcrush and `engine.rs`.
2. **SmartCrusher** (`src/compression/smart_crusher.rs`) — implemented: statistical JSON field elision hoists fields constant across every element of a ≥4-element object array into `_elided_constant_fields`, wired into cmdcrush's JSON branch. Not wired into `engine.rs`, whose per-block loop only touches `text`-type content blocks (JSON tool results arrive as `tool_result` blocks, which that loop skips) — worth revisiting if `engine.rs` starts compressing tool-result JSON.
3. **cmdcrush Rewind parity** — cmdcrush now appends a `[N compressed to M. Retrieve: hash=X]` marker (same format as the main proxy's `RewindStore`) directly into its compressed stdout/stderr when it archives an original, and `cmdcrush --retrieve <hash>` reads the archived original back from `--archive-dir`. The stderr path-print is kept alongside for human debugging.

Before starting new compression work: re-check headroom's repo/docs and rtk's
command surface (`rtk gain --history`, `rtk discover`) for techniques not yet
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

## Toolchain gotchas (this environment)

- `cargo` is not on default `PATH`; resolve it via `rustup which cargo`
  (`/Users/tstapler/.rustup/toolchains/stable-aarch64-apple-darwin/bin/cargo`).
- The `rtk` shell hook rewrites bash commands and can break `cargo build`
  invocations — bypass by calling the resolved cargo path directly.
- A broken `RUSTC_WRAPPER=sccache` env var breaks compilation
  (`sccache: caused by: cannot find binary path`). Clear it per-invocation:
  `RUSTC_WRAPPER="" cargo build --release --bin cmdcrush --manifest-path <repo>/Cargo.toml`.
