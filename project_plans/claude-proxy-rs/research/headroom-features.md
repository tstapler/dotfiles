# Research: Headroom-Inspired Features (FR-7 through FR-10)

**Date**: 2026-06-17
**Scope**: CacheAligner, Session History Mining, Verbosity Steering, SharedContext Dedup

---

## FR-7: CacheAligner — Anthropic Prompt Caching

### How Prompt Caching Works at the API Level

Caching is now GA (no beta header required). The `anthropic-beta: prompt-caching-2024-07-31` header is **no longer needed** for any current Claude model; all active models support caching natively.

There are two modes:
- **Automatic caching**: Add `cache_control: {"type": "ephemeral"}` at the **top level** of the request body. The API places the breakpoint on the last cacheable block automatically. Best for multi-turn conversations.
- **Explicit cache breakpoints**: Place `cache_control: {"type": "ephemeral"}` on individual content blocks. Maximum 4 breakpoints per request.

### Cache Evaluation Order (Critical for Proxy)

The cache prefix hierarchy is **tools → system → messages** in that exact order. A change to tools invalidates the tool + system + message caches. A change to the system invalidates system + message caches only.

```json
// Example: explicit breakpoint on system block
{
  "model": "claude-sonnet-4-6",
  "system": [
    {
      "type": "text",
      "text": "You are a coding assistant...",
      "cache_control": {"type": "ephemeral"}
    }
  ],
  "messages": [{"role": "user", "content": "..."}]
}
```

### Cache Hit/Miss Response Fields

In `response.usage` (or `message_start` SSE event for streaming):

| Field | Meaning |
|---|---|
| `cache_read_input_tokens` | Tokens served from cache (hit) |
| `cache_creation_input_tokens` | Tokens written to cache (miss + write) |
| `input_tokens` | Tokens **after** the last cache breakpoint (never cached) |

To detect a cache hit: `cache_read_input_tokens > 0`.
To detect a cold write: `cache_creation_input_tokens > 0` and `cache_read_input_tokens == 0`.
To estimate savings: `saved_tokens ≈ cache_read_input_tokens × 0.9` (cache reads cost 10% of base).

Total tokens: `cache_read + cache_creation + input_tokens` (NOT `input_tokens` alone).

### What Breaks Cache Hits (Prefix Stability)

The cache key is a cryptographic hash of the **exact byte sequence** of the prompt up to and including the cache breakpoint. Any change — even a single byte — at or before the breakpoint invalidates the cache.

**Confirmed cache-busters:**
- Modifying any tool definition (name, description, parameters) → invalidates **entire** cache
- Enabling/disabling web search or citations → invalidates system + message caches
- Switching `speed` setting (fast vs. standard) → invalidates system + message caches
- Changing `tool_choice` parameter → invalidates message cache
- Adding/removing images anywhere in messages → invalidates message cache
- Changing extended thinking parameters (enable/disable, budget) → invalidates message cache
- JSON key ordering in `tool_use` blocks (Go/Swift randomize key order) → cache bust
- Timestamps or per-request metadata injected into system prompt → cache bust every request
- Whitespace changes anywhere in cached prefix → cache bust

**Does NOT bust the cache:**
- Changes to content after the last breakpoint
- New messages appended to conversation (auto-caching handles the growing tail)

### System Prompt Multi-Block Format (Critical for FR-9 Integration)

The `system` field can be either a plain string **or** an array of content blocks:

```json
{
  "system": [
    {
      "type": "text",
      "text": "You are a helpful assistant. [~5000 tokens of static instructions]",
      "cache_control": {"type": "ephemeral"}
    },
    {
      "type": "text",
      "text": "Be terse. Don't restate context. Answer directly."
    }
  ]
}
```

The first block has `cache_control` → it will be cached. The second block (verbosity suffix, FR-9) has **no** `cache_control` → it is not cached and counts toward `input_tokens`. This is the correct pattern: the static prefix is cache-stable; the dynamic suffix is appended afterward without cache markers.

**Key constraint**: `cache_control` must be on a block whose prefix is byte-identical across requests. The verbosity suffix goes on the **second** block (no cache marker) so the first block's hash never changes.

### How the Proxy Can Detect Unstable Prefixes

Since the proxy sees both request and response:
1. On each response, record `cache_read_input_tokens` and `cache_creation_input_tokens`
2. If `cache_creation_input_tokens > 0` and `cache_read_input_tokens == 0` on the second+ request for a session → cache miss, prefix changed
3. Common cause: Claude Code injects per-request metadata into the system block. The proxy should detect this and ensure it doesn't place `cache_control` on a volatile block.
4. The Anthropic API offers a `cache diagnostics` beta endpoint that compares two consecutive requests and reports exactly where the prefix diverged.

### Cache Minimum Token Thresholds

For Claude Sonnet models: **1,024 tokens** minimum to cache. Shorter content is silently not cached (no error). For Haiku 4.5: 4,096 tokens. The proxy should only inject cache markers when the prefix is expected to meet the minimum.

### TTL Options

- Default: 5 minutes (`{"type": "ephemeral"}`)
- Extended: 1 hour (`{"type": "ephemeral", "ttl": "1h"}`) at 2× base input price

For Claude Code sessions where turns can be minutes apart, the 1-hour TTL is worth considering.

---

## FR-8: Session History Mining — Claude Code Transcript Format

### JSONL File Location and Schema

Files live at: `~/.claude/projects/<encoded-cwd>/<session-uuid>.jsonl`

The `<encoded-cwd>` is the working directory path with `/` replaced by `-` (e.g., `/home/tstapler/dotfiles` → `-home-tstapler-dotfiles`).

Each line is a JSON object. Key `type` values:

| `type` | Description |
|---|---|
| `user` | Human turn (text message or tool result) |
| `assistant` | Model response (text, tool_use, or thinking block) |
| `system` | Local system events (local_command output) |
| `attachment` | Metadata: hook results, skill listings, file snapshots, MCP instructions |
| `ai-title` | Auto-generated session title |
| `file-history-snapshot` | File state snapshot for undo |
| `last-prompt` | The most recent user prompt text |
| `queue-operation` | Enqueued background operations |

### User Message Schema

```json
{
  "parentUuid": "...",
  "isSidechain": false,
  "promptId": "...",
  "type": "user",
  "message": {
    "role": "user",
    "content": "Can you please commit what we have"
  },
  "uuid": "...",
  "timestamp": "2026-05-20T01:31:28.229Z",
  "permissionMode": "default",
  "userType": "external",
  "entrypoint": "cli",
  "cwd": "/home/tstapler/dotfiles",
  "sessionId": "...",
  "version": "2.1.143",
  "gitBranch": "master"
}
```

`message.content` can be a string (plain text) or an array of content blocks (tool results, images).

### Assistant Message Schema

```json
{
  "parentUuid": "...",
  "isSidechain": false,
  "message": {
    "model": "claude-sonnet-4-6",
    "id": "msg_01...",
    "type": "message",
    "role": "assistant",
    "content": [
      {"type": "thinking", "thinking": "...", "signature": "..."},
      {"type": "text", "text": "..."},
      {"type": "tool_use", "id": "toolu_...", "name": "Bash", "input": {"command": "git status"}}
    ],
    "stop_reason": "tool_use",
    "usage": {
      "input_tokens": 3,
      "cache_creation_input_tokens": 17656,
      "cache_read_input_tokens": 14948,
      "output_tokens": 243,
      "cache_creation": {
        "ephemeral_1h_input_tokens": 17656,
        "ephemeral_5m_input_tokens": 0
      }
    }
  },
  "type": "assistant",
  "uuid": "...",
  "timestamp": "2026-05-20T01:31:30.579Z",
  "sessionId": "...",
  "version": "2.1.143"
}
```

Tool results appear as `user` entries where `message.content` is an array containing `{"type": "tool_result", "tool_use_id": "...", "content": "...", "is_error": false}`.

### Parsing Strategy for Rust

```rust
// Core types needed for FR-8 mining
#[derive(Deserialize)]
struct TranscriptEntry {
    #[serde(rename = "type")]
    entry_type: String,  // "user" | "assistant" | "system" | "attachment" | ...
    message: Option<Message>,
    uuid: Option<String>,
    #[serde(rename = "parentUuid")]
    parent_uuid: Option<String>,
    timestamp: Option<String>,
    session_id: Option<String>,
}

#[derive(Deserialize)]
struct Message {
    role: String,
    content: MessageContent,  // String or Vec<ContentBlock>
}

// Content is either a plain string or array of blocks
#[derive(Deserialize)]
#[serde(untagged)]
enum MessageContent {
    Text(String),
    Blocks(Vec<ContentBlock>),
}
```

Use `serde_json` with `#[serde(untagged)]` for `MessageContent`. Entries with unknown types should deserialize with `#[serde(other)]` or be skipped via `Result<_, _>` on each line.

### Correction Pattern Detection (No LLM Required)

Extract only `type == "user"` entries where `isMeta == false` and `message.content` is a plain string (not a block array with `tool_result`). Short messages under ~300 chars are the human turn text. Apply regex tiers:

**Tier 1 — Explicit negation/redirect (high precision)**:
```rust
// Direct correction phrases
static CORRECTION_DIRECT: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?xi)
    \b(?:
        no[,\s]+(?:don't|do\s+not|stop|please|never)
        | don't\s+(?:do|use|add|create|make|run|call|write|put|output)
        | stop\s+(?:doing|using|adding|creating|making|that)
        | please\s+don't\s+(?:do|use|add|create|make)
        | never\s+(?:do|use|add|create|make|run|call|write|put)\s+that
        | instead[,\s]+(?:use|just|try|do|please)
        | use\s+\w+\s+instead
        | always\s+use\s+\w+
        | you\s+(?:keep|keep\s+on)\s+(?:doing|using|adding|making)
    )\b
").unwrap());
```

**Tier 2 — Frustration / repeated correction signals (medium precision)**:
```rust
static CORRECTION_FRUSTRATION: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?xi)
    \b(?:
        I\s+(?:said|told|asked)\s+you\s+(?:to\s+)?(?:not|never|stop)
        | that'?s?\s+(?:wrong|not\s+right|not\s+what\s+I|incorrect)
        | why\s+(?:did|are|do)\s+you\s+(?:keep|still|always)
        | you're?\s+(?:still|again)\s+(?:doing|using|making)
        | how\s+many\s+times\s+(?:do\s+I\s+have\s+to|have\s+I\s+told)
        | I\s+(?:just|already)\s+said
        | (?:please\s+)?read\s+(?:the\s+)?(?:instructions|CLAUDE\.md|rules|guidelines)\s+(?:again|more\s+carefully)
    )\b
").unwrap());
```

**Tier 3 — Error-recovery loop detection (structural, not regex)**:

Walk the `parentUuid` chain (linked list structure). Flag an error-recovery loop when:
- `assistant(tool_use name=X)` → `user(tool_result is_error=true)` repeats ≥ 2 consecutive times for same tool name
- OR: `assistant` → `user(short human text with Tier 1/2 match)` → `assistant` using different tool/approach

**Tier 4 — Repeated user message (shingling without LLM)**:
Tokenize consecutive user messages into word trigrams, compute Jaccard similarity. If similarity > 0.4 and the later message is within 5 turns → repeated correction candidate.

**Scoring**: Weight corrections by recency and frequency. A phrase appearing in 3+ separate sessions is a strong candidate for MEMORY.md.

### Additional Structural Details from Live Transcripts

- `isSidechain: true` marks messages from sub-agents (Agent tool spawns) — skip for correction mining
- `system/compact_boundary` records mark where context compaction happened; `preTokens`/`postTokens` available for efficiency tracking
- `system/turn_duration` records contain `durationMs` and `messageCount` — useful for session boundary detection
- `message.usage.iterations` array contains per-thinking-iteration token counts (extended thinking)
- Thinking blocks always have empty `"thinking": ""` in stored transcripts (redacted for privacy)

---

## FR-9: System Prompt Suffix Injection (Verbosity Steering)

### Correct Pattern for Cache-Stable Suffix Injection

The system prompt must be sent as an **array** (not a plain string) with the stable prefix in block 0 (with `cache_control`) and the dynamic verbosity suffix in block 1 (without `cache_control`):

```json
{
  "system": [
    {
      "type": "text",
      "text": "<original system prompt content — unchanged from what Claude Code sent>",
      "cache_control": {"type": "ephemeral"}
    },
    {
      "type": "text",
      "text": "\n\nBe terse. Skip preamble. Answer directly without restating context."
    }
  ]
}
```

This is the only correct approach. Any other injection (appending to the original string, modifying it in place) changes the hash of block 0 and busts the cache on every request.

### When the Incoming Request Has an Array System Prompt

Claude Code sometimes sends `system` as an array already. The proxy must:
1. Check if the last block already has `cache_control` — if so, split it: keep the last block's text but move its `cache_control` to the new verbosity-suffix block, OR insert the suffix as a new block before the final `cache_control` marker.
2. If the incoming system is a plain string, convert it to a 2-block array.
3. If the incoming system has no blocks with `cache_control`, add `cache_control` to the last original block, then append the verbosity suffix as a new uncached block.

### Verbosity Steering Phrases by Level

| Level | Suffix |
|---|---|
| 1 (light) | `"Be concise."` |
| 2 (moderate) | `"Be terse. Skip preamble. Answer directly without restating context."` |
| 3 (aggressive) | `"Be extremely terse. One sentence per idea. No preamble, no summary, no context restatement. Code only when asked."` |

### Continuation Turn Detection (FR-9.2)

A turn is a "continuation" if the most recent human message content is primarily `tool_result` blocks (not a new text question). Check:
```rust
fn is_continuation_turn(last_human_message: &[ContentBlock]) -> bool {
    let tool_results = last_human_message.iter()
        .filter(|b| b.block_type == "tool_result").count();
    let text_blocks = last_human_message.iter()
        .filter(|b| b.block_type == "text").count();
    // Continuation = dominated by tool results, no substantial new text
    tool_results > 0 && text_blocks == 0
}
```

---

## FR-10.4: Similarity Detection for Auto-Dedup

### Approach Comparison for 100KB Entries

| Approach | Crate | Time/comparison | Feasible? | Notes |
|---|---|---|---|---|
| SimHash 64-bit | `simhash` (115K dl) | microseconds | Yes | O(n) hash, O(1) compare. Use as pre-filter only. |
| MinHash + LSH | `lshdedup-core`, `gaoya` (11K dl), `txtfp` | 1–5ms to sign, µs to query | Yes (amortized) | Best for ≥95% Jaccard on word shingles |
| Exact Jaccard shingles | manual + `textdistance` (48K dl) | 1–5ms | Yes | O(n log n) |
| Levenshtein `rapidfuzz` | `rapidfuzz` (62K dl) | 1–10ms with cutoff | Marginal | Myers algorithm, early exit at cutoff |
| Levenshtein `strsim` | `strsim` (56.9M dl) | ~10 seconds | **NO** | O(n²) with no early exit — never use on 100KB |

### What "95% Similar" Means for Long Documents

Edit distance and shingle Jaccard give different answers:
- **Levenshtein 95%**: ≤5,000 character edits in 100KB. Order-sensitive. Moving a paragraph counts as ~2× its length in edits.
- **Jaccard 95% on word 5-shingles**: 95% of all 5-word windows are identical. Partially position-invariant. One rewritten paragraph in 20 yields ~85–90% Jaccard (correctly failing 95% threshold). **This is the semantically correct definition for long document dedup.**

### Recommended Implementation

**Two-tier approach** for the SharedContext store:

**Tier 1 — Cheap pre-filter (O(1) compare)**:
Use `simhash` crate. Hash each document to a 64-bit fingerprint on write. On `PUT /memory/{key}`, compute SimHash of new value, XOR with all existing fingerprints, count set bits (Hamming distance). If any entry has Hamming distance ≤ 6 bits → candidate for similarity check. Skip MinHash entirely if Hamming > 6. This eliminates the vast majority of pairwise comparisons at negligible cost.

**Tier 2 — MinHash + LSH (1–5ms)**:
Use `gaoya` crate (`MinHashIndex`, `MinHasher32`). Configure with 128 hash functions, 16 bands × 8 rows for ~0.94 Jaccard threshold.

```rust
use gaoya::minhash::{MinHasher32, MinHashIndex};
use gaoya::text::whitespace_split;

// On startup: create index
let hasher = MinHasher32::new(128);
let mut index: MinHashIndex<u32, String> = MinHashIndex::new(16, 8, 0.5);

// On store:
let shingles: Vec<&str> = whitespace_split(&value, 5); // 5-word shingles
let sig = hasher.create_signature(shingles.iter());
let candidates = index.query_owned(&sig);

// Verify candidates with exact Jaccard
for candidate_key in candidates {
    if exact_jaccard(&value, &store[&candidate_key]) >= 0.95 {
        // Dedup: update existing rather than create
        return update_existing(candidate_key, value);
    }
}
index.insert(key.clone(), sig);
```

**Async safety**: MinHash signing is CPU-bound. Wrap in `tokio::task::spawn_blocking`. The `MinHashIndex` is not `Send` by default — wrap in `Arc<Mutex<...>>` or use a dedicated task for index operations.

**Crate links**:
- `gaoya`: https://crates.io/crates/gaoya (11K downloads, general MinHash/SimHash)
- `simhash`: https://crates.io/crates/simhash (115K downloads, simple 64-bit LSH)
- `lshdedup-core`: https://crates.io/crates/lshdedup-core (purpose-built dedup)
- `rapidfuzz`: https://crates.io/crates/rapidfuzz (62K downloads, if edit distance is needed)

---

## FR-7: Cache Headers Summary

### Request Fields

```json
// Automatic caching (top-level):
{"cache_control": {"type": "ephemeral"}}
// or with 1h TTL:
{"cache_control": {"type": "ephemeral", "ttl": "1h"}}

// Explicit block-level:
{"type": "text", "text": "...", "cache_control": {"type": "ephemeral"}}
```

### Response Usage Fields

```json
{
  "usage": {
    "input_tokens": 50,                    // tokens AFTER last breakpoint
    "cache_read_input_tokens": 100000,     // cache hit tokens (90% cheaper)
    "cache_creation_input_tokens": 0,      // cache write tokens (25% more expensive)
    "output_tokens": 243,
    "cache_creation": {
      "ephemeral_5m_input_tokens": 0,
      "ephemeral_1h_input_tokens": 0
    }
  }
}
```

For streaming, these appear in the `message_start` SSE event's `message.usage` field.

### Proxy Strategy for Maximum Hit Rate

1. **Normalize tool definitions** before placing `cache_control`: sort tool definitions alphabetically by name, sort parameter keys canonically. This ensures the `tools` prefix hash is stable across requests.
2. **Convert system string → array**: When Claude Code sends `system` as a plain string, convert to `[{"type":"text","text":"...", "cache_control":{"type":"ephemeral"}}]`.
3. **Detect volatile system content**: If the system prompt contains tokens like ISO timestamps, UUIDs, or per-session values, do NOT add `cache_control` to that block — it will bust on every request. Log a warning instead.
4. **Minimum threshold check**: Only add `cache_control` when the prefix is estimated to be ≥ 1,024 tokens (conservative; Sonnet minimum). Count tokens approximately as `len(text_bytes) / 4`.
5. **Metrics**: Track `cache_hits_estimated` as sum of requests where `cache_read_input_tokens > 0`, and `cache_misses_estimated` as sum where `cache_creation_input_tokens > 0` and `cache_read_input_tokens == 0`.

---

## Implementation Decision Summary

### Decision 1: System Prompt Injection Architecture (FR-7 + FR-9 Coupling)

**Decision**: The proxy must handle system prompt transformation in a single unified pipeline, not two separate passes. The pipeline order is:
1. Parse incoming system (string or array)
2. Normalize/stabilize the content (strip volatile content if any)
3. Add `cache_control` to the last stable block
4. Append verbosity suffix as a new uncached block (if FR-9 is active)

If FR-9 appends after FR-7 adds `cache_control`, the suffix gets its own uncached block — correct. If they run independently and both modify the system field, they can corrupt each other's output.

### Decision 2: Transcript Parsing Robustness (FR-8)

**Decision**: The JSONL schema is undocumented and evolving (GitHub issue #53516 tracks this). The Rust parser must use `#[serde(deny_unknown_fields)]` on **nothing** — instead skip unknown `type` values gracefully. Only extract lines where `type == "user"` with a plain-text `content`. The `message.content` field is a serde untagged enum (string or array). Lines that fail to parse are silently skipped.

### Decision 3: Similarity Pre-Filter Required (FR-10.4)

**Decision**: Do NOT use `strsim::normalized_levenshtein` for 100KB entries — it will block the async runtime for ~10 seconds per comparison. The correct stack is SimHash as O(1) pre-filter + `gaoya` MinHash for the ~5% of candidate pairs that pass the Hamming distance test. The 95% similarity threshold maps to Jaccard on word 5-shingles, not edit distance, which is the semantically correct definition for document-level dedup.

---

## Sources

- [Anthropic Prompt Caching Docs](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- [Anthropic Cache Invalidation Table](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching#what-invalidates-the-cache)
- [gaoya crate (MinHash)](https://crates.io/crates/gaoya)
- [simhash crate](https://crates.io/crates/simhash)
- [lshdedup-core crate](https://crates.io/crates/lshdedup-core)
- [rapidfuzz crate](https://crates.io/crates/rapidfuzz)
- [strsim crate](https://crates.io/crates/strsim)
- [Claude Code transcript schema issue](https://github.com/anthropics/claude-code/issues/53516)
- [Spring AI Anthropic multi-block system prompt](https://github.com/spring-projects/spring-ai/issues/5494)
