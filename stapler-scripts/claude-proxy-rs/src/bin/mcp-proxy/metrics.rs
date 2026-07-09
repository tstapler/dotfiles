//! MCP filter metrics — in-process counters + shared-file IPC to claude-proxy-rs.
//!
//! mcp-proxy runs as a stdio subprocess; the only cross-process communication
//! path to the claude-proxy-rs dashboard is a JSON file at a well-known path.
//! `write_session_start` atomically updates that file after every `tools/list`.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use chrono::Utc;
use serde::{Deserialize, Serialize};

// ── Shared file types ─────────────────────────────────────────────────────────

#[derive(Debug, Default, Serialize, Deserialize)]
pub struct McpServerSnapshot {
    pub tokens_before: u64,
    pub tokens_after: u64,
}

#[derive(Debug, Default, Serialize, Deserialize)]
pub struct McpMetricsSnapshot {
    pub updated_at: String,
    pub servers: HashMap<String, McpServerSnapshot>,
}

// ── Path helper ───────────────────────────────────────────────────────────────

/// Default path: `~/.cache/claude-proxy/mcp-filter-metrics.json`.
pub fn default_metrics_path() -> PathBuf {
    let home = std::env::var("HOME").unwrap_or_default();
    PathBuf::from(home).join(".cache/claude-proxy/mcp-filter-metrics.json")
}

// ── Write helper ──────────────────────────────────────────────────────────────

/// Persist per-server token counts to the shared metrics file.
///
/// Reads the existing file (if any), updates the named server's entry, then
/// atomically replaces the file via a `.tmp` rename to avoid partial reads by
/// the claude-proxy-rs metrics handler.
pub fn write_session_start(path: &Path, server: &str, tokens_before: u64, tokens_after: u64) {
    let mut snapshot: McpMetricsSnapshot = std::fs::read(path)
        .ok()
        .and_then(|b| serde_json::from_slice(&b).ok())
        .unwrap_or_default();

    let entry = snapshot.servers.entry(server.to_string()).or_default();
    entry.tokens_before = tokens_before;
    entry.tokens_after = tokens_after;
    snapshot.updated_at = Utc::now().to_rfc3339();

    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }

    let tmp = path.with_extension("tmp");
    if let Ok(bytes) = serde_json::to_vec_pretty(&snapshot) {
        if std::fs::write(&tmp, bytes).is_ok() {
            let _ = std::fs::rename(&tmp, path);
        }
    }
}
