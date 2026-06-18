//! Compression pipeline engine.
//!
//! Applies native text compression to message content, injects Rewind markers
//! for reversibility, and guards against double-compression and tool-pair
//! breakage (port of `compactor.py`).

use bytes::Bytes;
use once_cell::sync::Lazy;
use regex::Regex;
use serde_json::{json, Value};
use std::sync::Arc;
use tracing::{debug, warn};

use crate::compression::{RewindStore, TextCompressor};
use crate::compression::rewind::{format_rewind_marker, REWIND_MARKER_PATTERN};

// ---------------------------------------------------------------------------
// Compiled regexes
// ---------------------------------------------------------------------------

static REWIND_MARKER_RE: Lazy<Regex> =
    Lazy::new(|| Regex::new(REWIND_MARKER_PATTERN).expect("REWIND_MARKER_RE regex"));

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

/// Engine configuration, typically loaded from environment variables.
pub struct CompressionConfig {
    /// Minimum total byte size of the messages array before compression runs.
    pub compress_floor_bytes: usize,
}

impl Default for CompressionConfig {
    fn default() -> Self {
        CompressionConfig {
            compress_floor_bytes: 1000,
        }
    }
}

/// Per-request compression statistics returned alongside the (possibly)
/// modified request.
pub struct CompressionStats {
    pub bytes_before: usize,
    pub bytes_after: usize,
    pub compressed: bool,
}

/// The compression engine holds shared state (config + stores) and is cloned
/// cheaply via `Arc` wrapping from the caller.
pub struct CompressionEngine {
    pub config: CompressionConfig,
    pub rewind_store: Arc<RewindStore>,
    text_compressor: TextCompressor,
}

// ---------------------------------------------------------------------------
// The `rewind_retrieve` tool definition injected into `tools[]`.
// ---------------------------------------------------------------------------

fn rewind_tool_def() -> Value {
    json!({
        "name": "rewind_retrieve",
        "description": "Retrieve the original uncompressed content for a compressed message. Use when you need to see the full original content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hash_id": {
                    "type": "string",
                    "description": "The hash ID from the compression marker"
                }
            },
            "required": ["hash_id"]
        }
    })
}

// ---------------------------------------------------------------------------
// Implementation
// ---------------------------------------------------------------------------

impl CompressionEngine {
    pub async fn new(config: CompressionConfig, rewind_store: Arc<RewindStore>) -> Self {
        CompressionEngine {
            config,
            rewind_store,
            text_compressor: TextCompressor::new(),
        }
    }

    /// Main entry point: compress `request["messages"]` in place.
    ///
    /// Returns the (possibly modified) request and compression stats.
    pub async fn compress_request(&self, mut request: Value) -> (Value, CompressionStats) {
        // ----------------------------------------------------------------
        // 1. Measure size of the messages array before compression.
        // ----------------------------------------------------------------
        let messages_json = match request.get("messages") {
            Some(m) => serde_json::to_string(m).unwrap_or_default(),
            None => {
                let stats = CompressionStats {
                    bytes_before: 0,
                    bytes_after: 0,
                    compressed: false,
                };
                return (request, stats);
            }
        };
        let bytes_before = messages_json.len();

        // ----------------------------------------------------------------
        // 2. Floor check: skip if total size is below threshold.
        // ----------------------------------------------------------------
        if bytes_before < self.config.compress_floor_bytes {
            debug!(
                bytes_before,
                floor = self.config.compress_floor_bytes,
                "compression skipped: below floor"
            );
            return (
                request,
                CompressionStats {
                    bytes_before,
                    bytes_after: bytes_before,
                    compressed: false,
                },
            );
        }

        // ----------------------------------------------------------------
        // 3. Extract messages array (we'll work on a clone).
        // ----------------------------------------------------------------
        let original_messages = match request.get("messages").and_then(|m| m.as_array()) {
            Some(arr) => arr.clone(),
            None => {
                return (
                    request,
                    CompressionStats {
                        bytes_before,
                        bytes_after: bytes_before,
                        compressed: false,
                    },
                )
            }
        };

        // ----------------------------------------------------------------
        // 4. Double-compression guard: skip if any Rewind marker already
        //    present in message content.
        // ----------------------------------------------------------------
        if has_rewind_markers(&original_messages) {
            debug!("compression skipped: Rewind markers already present");
            return (
                request,
                CompressionStats {
                    bytes_before,
                    bytes_after: bytes_before,
                    compressed: false,
                },
            );
        }

        // ----------------------------------------------------------------
        // 5. Compress each eligible message.
        //    - assistant messages: always compress text blocks
        //    - user messages: compress text blocks that are log-like
        //      (>20 lines OR contain ANSI escape codes)
        //    - tool_use / tool_result blocks: pass through untouched
        // ----------------------------------------------------------------
        let mut compressed_messages = original_messages.clone();
        let mut any_compressed = false;

        for msg in compressed_messages.iter_mut() {
            let role = msg
                .get("role")
                .and_then(|r| r.as_str())
                .unwrap_or("")
                .to_string();

            let content = match msg.get_mut("content").and_then(|c| c.as_array_mut()) {
                Some(arr) => arr,
                None => continue, // string content — skip
            };

            for block in content.iter_mut() {
                let block_type = block
                    .get("type")
                    .and_then(|t| t.as_str())
                    .unwrap_or("")
                    .to_string();

                // Only compress text blocks; pass tool_use/tool_result through.
                if block_type != "text" {
                    continue;
                }

                let text = match block.get("text").and_then(|t| t.as_str()) {
                    Some(t) => t.to_string(),
                    None => continue,
                };

                let should_compress = match role.as_str() {
                    "assistant" => true,
                    "user" => is_log_like(&text),
                    _ => false,
                };

                if !should_compress {
                    continue;
                }

                let compressed_text = self.text_compressor.compress(&text);
                if compressed_text.len() < text.len() {
                    if let Some(t) = block.get_mut("text") {
                        *t = Value::String(compressed_text);
                        any_compressed = true;
                    }
                }
            }
        }

        if !any_compressed {
            return (
                request,
                CompressionStats {
                    bytes_before,
                    bytes_after: bytes_before,
                    compressed: false,
                },
            );
        }

        // ----------------------------------------------------------------
        // 6. Tool-pair guard: verify tool_use/tool_result pairing is intact.
        //    If any orphaned pair → revert and return original messages.
        // ----------------------------------------------------------------
        let (valid, orphaned) = validate_tool_pairs(&compressed_messages);
        if !valid {
            warn!(
                orphaned_count = orphaned.len(),
                "compression broke tool_use/tool_result pairs — reverting"
            );
            return (
                request,
                CompressionStats {
                    bytes_before,
                    bytes_after: bytes_before,
                    compressed: false,
                },
            );
        }

        // ----------------------------------------------------------------
        // 7. Store originals in RewindStore, inject Rewind markers and tool.
        // ----------------------------------------------------------------
        // For each message that was modified, store the original serialized
        // bytes and embed a Rewind marker in the first text block.
        for (i, (orig_msg, comp_msg)) in original_messages
            .iter()
            .zip(compressed_messages.iter_mut())
            .enumerate()
        {
            let orig_serialized = serde_json::to_string(orig_msg).unwrap_or_default();
            let comp_serialized = serde_json::to_string(comp_msg).unwrap_or_default();

            if orig_serialized == comp_serialized {
                // This message was not modified — skip.
                continue;
            }

            // Store original bytes.
            let orig_bytes = Bytes::from(orig_serialized.into_bytes());
            let hash_id = self.rewind_store.insert(&orig_bytes).await;

            // Count content blocks before/after for the marker.
            let items_before = orig_msg
                .get("content")
                .and_then(|c| c.as_array())
                .map(|a| a.len())
                .unwrap_or(1);
            let items_after = comp_msg
                .get("content")
                .and_then(|c| c.as_array())
                .map(|a| a.len())
                .unwrap_or(1);

            let marker = format_rewind_marker(items_before, items_after, &hash_id);

            // Inject marker into the first text block of the compressed message.
            inject_rewind_marker(comp_msg, &marker, i);
        }

        // Inject rewind_retrieve tool into tools[] (idempotent).
        inject_rewind_tool(&mut request);

        // Replace messages in request.
        if let Some(msgs) = request.get_mut("messages") {
            *msgs = Value::Array(compressed_messages);
        }

        let bytes_after = request
            .get("messages")
            .map(|m| serde_json::to_string(m).unwrap_or_default().len())
            .unwrap_or(bytes_before);

        (
            request,
            CompressionStats {
                bytes_before,
                bytes_after,
                compressed: true,
            },
        )
    }
}

// ---------------------------------------------------------------------------
// Helper functions
// ---------------------------------------------------------------------------

/// Return `true` if any message content contains a Rewind marker.
///
/// Port of `_has_rewind_markers` from `compactor.py` (lines 107-132).
fn has_rewind_markers(messages: &[Value]) -> bool {
    for msg in messages {
        let content = msg.get("content");
        match content {
            Some(Value::String(s)) => {
                if REWIND_MARKER_RE.is_match(s) {
                    return true;
                }
            }
            Some(Value::Array(blocks)) => {
                for block in blocks {
                    let text = block
                        .get("text")
                        .or_else(|| block.get("content"))
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    if REWIND_MARKER_RE.is_match(text) {
                        return true;
                    }
                }
            }
            _ => {}
        }
    }
    false
}

/// Validate that every `tool_result.tool_use_id` in user messages has a
/// corresponding `tool_use.id` in the preceding assistant message.
///
/// Port of `_validate_tool_pairs` from `compactor.py` (lines 167-214).
///
/// Returns `(is_valid, orphaned_ids)`.
fn validate_tool_pairs(messages: &[Value]) -> (bool, Vec<String>) {
    let mut orphaned: Vec<String> = Vec::new();

    for (i, msg) in messages.iter().enumerate() {
        if msg.get("role").and_then(|r| r.as_str()) != Some("user") {
            continue;
        }

        let content = match msg.get("content").and_then(|c| c.as_array()) {
            Some(c) => c,
            None => continue,
        };

        // Collect tool_use_ids referenced by tool_result blocks in this user msg.
        let mut tr_ids: std::collections::HashSet<String> = std::collections::HashSet::new();
        for block in content {
            if block.get("type").and_then(|t| t.as_str()) == Some("tool_result") {
                if let Some(uid) = block.get("tool_use_id").and_then(|u| u.as_str()) {
                    tr_ids.insert(uid.to_string());
                }
            }
        }

        if tr_ids.is_empty() {
            continue;
        }

        // Verify the preceding message is an assistant turn with matching tool_use blocks.
        if i == 0 {
            orphaned.extend(tr_ids);
            continue;
        }

        let prev = &messages[i - 1];
        if prev.get("role").and_then(|r| r.as_str()) != Some("assistant") {
            orphaned.extend(tr_ids);
            continue;
        }

        let prev_content = prev.get("content").and_then(|c| c.as_array());
        let tu_ids: std::collections::HashSet<String> = prev_content
            .map(|blocks| {
                blocks
                    .iter()
                    .filter(|b| b.get("type").and_then(|t| t.as_str()) == Some("tool_use"))
                    .filter_map(|b| b.get("id").and_then(|id| id.as_str()))
                    .map(|id| id.to_string())
                    .collect()
            })
            .unwrap_or_default();

        for id in tr_ids {
            if !tu_ids.contains(&id) {
                orphaned.push(id);
            }
        }
    }

    (orphaned.is_empty(), orphaned)
}

/// Return `true` if `text` looks like log output (>20 lines or contains ANSI).
fn is_log_like(text: &str) -> bool {
    use once_cell::sync::Lazy;
    static ANSI_CHECK: Lazy<Regex> =
        Lazy::new(|| Regex::new(r"\x1b\[").expect("ANSI_CHECK regex"));

    let line_count = text.lines().count();
    line_count > 20 || ANSI_CHECK.is_match(text)
}

/// Inject `marker` as a suffix into the first text block of `msg`.
fn inject_rewind_marker(msg: &mut Value, marker: &str, _msg_index: usize) {
    if let Some(content) = msg.get_mut("content").and_then(|c| c.as_array_mut()) {
        for block in content.iter_mut() {
            if block.get("type").and_then(|t| t.as_str()) == Some("text") {
                if let Some(text_val) = block.get_mut("text") {
                    if let Some(text_str) = text_val.as_str() {
                        let new_text = format!("{}\n{}", text_str, marker);
                        *text_val = Value::String(new_text);
                        return;
                    }
                }
            }
        }
    }
}

/// Inject the `rewind_retrieve` tool into `request["tools"]`, creating the
/// array if absent.  Idempotent: no-op if already present.
fn inject_rewind_tool(request: &mut Value) {
    let tools = request
        .get_mut("tools")
        .and_then(|t| t.as_array_mut());

    match tools {
        Some(arr) => {
            let already_present = arr
                .iter()
                .any(|t| t.get("name").and_then(|n| n.as_str()) == Some("rewind_retrieve"));
            if !already_present {
                arr.push(rewind_tool_def());
            }
        }
        None => {
            request["tools"] = Value::Array(vec![rewind_tool_def()]);
        }
    }
}
