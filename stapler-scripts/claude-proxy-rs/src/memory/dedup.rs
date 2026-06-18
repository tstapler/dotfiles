//! Similarity-based deduplication using SimHash pre-filter + MinHash LSH (lshdedup-core).
//!
//! Algorithm (ADR-009):
//! 1. SimHash 64-bit Hamming pre-filter — O(1) per existing entry.
//!    If Hamming distance > 6 bits → skip (not similar enough).
//! 2. For candidates with Hamming ≤ 6: MinHash LSH via lshdedup-core in
//!    `tokio::task::spawn_blocking`. Word 5-shingles, Jaccard ≥ 0.95 threshold.
//! 3. Return the key of the first matching entry, or None.
//!
//! NEVER use `strsim::normalized_levenshtein` on large inputs — O(n²), blocks runtime.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use lshdedup_core::{Config as LshConfig, Index as LshIndex, ShingleUnit};
use simhash::{hamming_distance, simhash};
use tracing::debug;

use crate::memory::store::MemoryStore;

/// Per-entry SimHash fingerprint index.
/// The moka cache owns the `MemoryEntry` values; this map owns only the
/// 64-bit SimHash fingerprints so we can do O(1) Hamming comparisons.
pub struct SimHashIndex {
    /// key → SimHash fingerprint.
    fingerprints: HashMap<String, u64>,
}

impl SimHashIndex {
    pub fn new() -> Self {
        Self {
            fingerprints: HashMap::new(),
        }
    }

    pub fn insert(&mut self, key: String, fingerprint: u64) {
        self.fingerprints.insert(key, fingerprint);
    }

    pub fn remove(&mut self, key: &str) {
        self.fingerprints.remove(key);
    }

    /// Return keys whose SimHash is within `max_hamming` bits of `fp`.
    pub fn candidates(&self, fp: u64, max_hamming: u32) -> Vec<String> {
        self.fingerprints
            .iter()
            .filter(|(_, &stored)| hamming_distance(fp, stored) <= max_hamming)
            .map(|(k, _)| k.clone())
            .collect()
    }
}

impl Default for SimHashIndex {
    fn default() -> Self {
        Self::new()
    }
}

/// Shared deduplication state: SimHash index + MinHash LSH index.
/// Both wrapped in `Arc<Mutex<>>` so they are `Send + Sync`.
pub struct DedupState {
    pub simhash_idx: Arc<Mutex<SimHashIndex>>,
    pub lsh_idx: Arc<Mutex<LshIndex>>,
}

impl DedupState {
    pub fn new() -> Self {
        let lsh_cfg = LshConfig {
            num_hashes: 128,
            // 16 bands × 8 rows = 128 total. ~0.94 Jaccard threshold per ADR-009.
            bands: 16,
            shingle_size: 5,
            shingle_unit: ShingleUnit::Word,
            seed: 0,
        };
        let lsh_idx = LshIndex::new(lsh_cfg).expect("valid lshdedup-core config");
        Self {
            simhash_idx: Arc::new(Mutex::new(SimHashIndex::new())),
            lsh_idx: Arc::new(Mutex::new(lsh_idx)),
        }
    }
}

impl Default for DedupState {
    fn default() -> Self {
        Self::new()
    }
}

/// Check if `new_value` is ≥95% similar to any existing entry in `store`.
///
/// Returns the key of the first matching entry, or `None`.
///
/// Two-tier algorithm:
/// 1. SimHash Hamming pre-filter (O(1) per entry, sync).
/// 2. MinHash LSH via `lshdedup-core` for Hamming ≤ 6 candidates
///    (`spawn_blocking` — CPU-bound, must not block async runtime).
pub async fn find_duplicate(
    store: &MemoryStore,
    dedup: &DedupState,
    new_value: &[u8],
) -> Option<String> {
    let text = match std::str::from_utf8(new_value) {
        Ok(t) => t.to_owned(),
        // Binary values can only match via exact equality — skip dedup.
        Err(_) => return None,
    };

    if text.trim().is_empty() {
        return None;
    }

    // -----------------------------------------------------------------------
    // Tier 1: SimHash Hamming pre-filter
    // -----------------------------------------------------------------------
    let fp = simhash(&text);
    let candidates = {
        let idx = dedup.simhash_idx.lock().unwrap();
        idx.candidates(fp, 6)
    };

    if candidates.is_empty() {
        debug!("dedup: no SimHash candidates within 6 bits");
        return None;
    }

    debug!(
        candidates = candidates.len(),
        "dedup: SimHash candidates → MinHash tier"
    );

    // -----------------------------------------------------------------------
    // Tier 2: MinHash LSH via lshdedup-core (spawn_blocking — CPU-bound)
    // -----------------------------------------------------------------------
    let lsh_arc = Arc::clone(&dedup.lsh_idx);
    let text_clone = text.clone();
    let candidates_clone = candidates.clone();

    let hit: Option<String> = tokio::task::spawn_blocking(move || {
        let idx = lsh_arc.lock().unwrap();

        // `near_duplicates` queries all indexed docs at the Jaccard threshold.
        // We then restrict to our candidate set from the SimHash pre-filter.
        let hits = idx.near_duplicates(&text_clone, 0.95);

        let candidate_set: std::collections::HashSet<&String> =
            candidates_clone.iter().collect();
        hits.into_iter()
            .find(|h| candidate_set.contains(&h.id))
            .map(|h| h.id)
    })
    .await
    .unwrap_or(None); // JoinError → treat as no match

    if hit.is_some() {
        debug!(?hit, "dedup: MinHash duplicate found");
    }

    // Validate that the matched key still exists in the live moka cache.
    if let Some(ref key) = hit {
        if store.get(key).await.is_none() {
            // Entry was evicted between the SimHash lookup and now — stale match.
            return None;
        }
    }

    hit
}

/// Register a new entry in both the SimHash and MinHash indexes.
/// Must be called after `store.put()` so the moka entry is live.
pub fn register(dedup: &DedupState, key: &str, value: &[u8]) {
    let text = match std::str::from_utf8(value) {
        Ok(t) => t,
        Err(_) => return, // binary blobs are not indexed
    };

    let fp = simhash(text);
    {
        let mut idx = dedup.simhash_idx.lock().unwrap();
        idx.insert(key.to_owned(), fp);
    }
    {
        let mut idx = dedup.lsh_idx.lock().unwrap();
        // Ignore insert errors (only invalid config triggers them, not duplicates).
        let _ = idx.insert(key, text);
    }
}

/// Remove a key from the SimHash index (e.g., on explicit delete or TTL eviction).
/// Note: lshdedup-core's Index does not support removal. The entry becomes a
/// stale false-positive candidate but is filtered by the moka live-check in
/// `find_duplicate`.
pub fn deregister(dedup: &DedupState, key: &str) {
    let mut idx = dedup.simhash_idx.lock().unwrap();
    idx.remove(key);
}
