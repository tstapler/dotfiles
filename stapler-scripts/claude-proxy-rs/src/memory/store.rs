//! In-memory key-value store backed by moka cache for cross-agent shared context.

use std::sync::Arc;
use std::time::Duration;

use chrono::{DateTime, Utc};
use moka::future::Cache;
use once_cell::sync::Lazy;
use regex::Regex;
use serde::Serialize;

/// One stored memory entry.
#[derive(Debug, Clone)]
pub struct MemoryEntry {
    /// Compressed bytes (run through the text compressor; may equal original if below floor).
    pub value_compressed: Vec<u8>,
    /// Original uncompressed bytes.
    pub value_original: Vec<u8>,
    /// Agent identifier from `X-Agent-ID` header, or User-Agent fallback.
    pub agent_id: String,
    /// Raw User-Agent header value.
    pub user_agent: String,
    /// Insertion timestamp.
    pub created_at: DateTime<Utc>,
    /// Byte length before compression.
    pub size_before: usize,
    /// Byte length after compression.
    pub size_after: usize,
    /// TTL in seconds for this entry (informational; moka enforces expiry).
    pub ttl_secs: u64,
}

/// Cross-agent shared context memory store.
pub struct MemoryStore {
    /// moka async cache keyed by caller-supplied string key.
    pub(crate) entries: Cache<String, Arc<MemoryEntry>>,
    /// Maximum number of live entries (passed to moka max_capacity).
    pub max_entries: usize,
}

impl MemoryStore {
    /// Build a new store with a default 24h TTL.
    pub fn new(max_entries: usize) -> Self {
        let entries = Cache::builder()
            .max_capacity(max_entries as u64)
            .time_to_live(Duration::from_secs(86_400))
            .build();
        Self { entries, max_entries }
    }

    /// Insert (or overwrite) a key. The caller is responsible for compressing the value.
    pub async fn put(&self, key: String, entry: Arc<MemoryEntry>) {
        self.entries.insert(key, entry).await;
    }

    /// Retrieve an entry by key.
    pub async fn get(&self, key: &str) -> Option<Arc<MemoryEntry>> {
        self.entries.get(key).await
    }

    /// Iterate over all live keys and their entries. Returns a snapshot vec
    /// because `moka::future::Cache` does not expose an async iterator.
    pub async fn list_all(&self) -> Vec<(String, Arc<MemoryEntry>)> {
        // moka's `iter()` is synchronous and safe to call from async context.
        self.entries
            .iter()
            .map(|(k, v)| ((*k).clone(), v.clone()))
            .collect()
    }

    /// Return the number of live entries. May be slightly stale due to async eviction.
    pub fn len(&self) -> u64 {
        self.entries.entry_count()
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

/// Metadata row returned by `GET /memory` list endpoint.
#[derive(Debug, Serialize)]
pub struct MemoryListItem {
    pub key: String,
    pub agent_id: String,
    pub size_before: usize,
    pub size_after: usize,
    pub created_at: DateTime<Utc>,
    /// Approximate seconds remaining. May be negative if eviction is lagging.
    pub ttl_remaining_secs: i64,
}

static ANSI_RE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"\x1b\[[0-9;]*[mGKHFJABCDEFGHfils]").unwrap()
});

/// Light wrapper for simple text compression: ANSI strip + consecutive-line dedup.
/// Returns the compressed bytes; if output would be larger than input, returns
/// a clone of the original.
pub fn compress_value(input: &[u8]) -> Vec<u8> {
    match std::str::from_utf8(input) {
        Ok(text) => {
            let compressed = simple_compress(text);
            if compressed.len() < input.len() {
                compressed.into_bytes()
            } else {
                input.to_vec()
            }
        }
        Err(_) => input.to_vec(), // binary blobs pass through uncompressed
    }
}

/// ANSI strip + consecutive-line dedup. Mirrors the text_compressor stage
/// from Epic 6 but inline here so the memory module is self-contained.
fn simple_compress(text: &str) -> String {
    let stripped = ANSI_RE.replace_all(text, "");

    let mut out = String::with_capacity(stripped.len());
    let mut prev_line: Option<&str> = None;
    let mut repeat_count: usize = 0;

    for line in stripped.lines() {
        let trimmed = line.trim();
        match prev_line {
            Some(prev) if prev == line && !trimmed.is_empty() => {
                repeat_count += 1;
            }
            _ => {
                if let Some(prev) = prev_line {
                    if repeat_count > 0 {
                        out.push_str(&format!("{} (×{})\n", prev, repeat_count + 1));
                    } else {
                        out.push_str(prev);
                        out.push('\n');
                    }
                }
                prev_line = Some(line);
                repeat_count = 0;
            }
        }
    }
    if let Some(last) = prev_line {
        if repeat_count > 0 {
            out.push_str(&format!("{} (×{})\n", last, repeat_count + 1));
        } else {
            out.push_str(last);
            out.push('\n');
        }
    }
    out
}
