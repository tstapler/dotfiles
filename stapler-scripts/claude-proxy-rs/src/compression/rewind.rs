//! Rewind store: reversible compression cache.
//!
//! Stores original message bytes keyed by a short hash ID so the AI can
//! retrieve the full content if the compressed version is insufficient.

use bytes::Bytes;
use moka::future::Cache;
use sha2::{Digest, Sha256};
use std::sync::Arc;
use std::time::Duration;

/// Regex pattern that matches a Rewind retrieval marker embedded by the
/// compression engine into compressed messages.
///
/// Example: `[3 items compressed to 1. Retrieve: hash=a1b2c3d4]`
pub const REWIND_MARKER_PATTERN: &str =
    r"\[(\d+) items? compressed to \d+\. Retrieve: hash=([0-9a-f]+)\]";

/// Format a Rewind marker string for embedding in compressed content.
///
/// - `items_before`: number of content blocks/lines before compression
/// - `items_after`: number of content blocks/lines after compression
/// - `hash_id`: the 8-char hex ID returned by `RewindStore::insert`
pub fn format_rewind_marker(items_before: usize, items_after: usize, hash_id: &str) -> String {
    format!(
        "[{} items compressed to {}. Retrieve: hash={}]",
        items_before, items_after, hash_id
    )
}

/// In-memory cache that maps short hash IDs to original (pre-compression) bytes.
///
/// TTL: 10 minutes.  Max capacity: 500 entries.
/// Values are wrapped in `Arc` to avoid cloning payload bytes on cache hit.
pub struct RewindStore {
    cache: Cache<String, Arc<Bytes>>,
}

impl RewindStore {
    /// Create a new `RewindStore` with TTL=10 min and max_capacity=500.
    pub async fn new() -> Self {
        let cache = Cache::builder()
            .max_capacity(500)
            .time_to_live(Duration::from_secs(600))
            .build();
        RewindStore { cache }
    }

    /// Store `original` bytes and return an 8-character hex hash ID.
    ///
    /// The hash is derived from the first 4 bytes of the SHA-256 digest of
    /// the input, formatted as lowercase hex.  Collisions are astronomically
    /// unlikely within a 10-minute window with 500 max entries.
    pub async fn insert(&self, original: &Bytes) -> String {
        let digest = Sha256::digest(original.as_ref());
        // Take first 4 bytes → 8 hex chars
        let hash_id = format!(
            "{:02x}{:02x}{:02x}{:02x}",
            digest[0], digest[1], digest[2], digest[3]
        );
        self.cache
            .insert(hash_id.clone(), Arc::new(original.clone()))
            .await;
        hash_id
    }

    /// Retrieve the original bytes for `hash_id`, if still in cache.
    pub async fn retrieve(&self, hash_id: &str) -> Option<Arc<Bytes>> {
        self.cache.get(hash_id).await
    }
}
