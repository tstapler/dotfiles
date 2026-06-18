//! Error tracking and deduplication for claude-proxy-rs.
//!
//! Ports the Python `error_tracker.py` module:
//! - `normalize_message` — strip UUIDs, ARNs, hex IDs, long numbers
//! - `extract_signature` — parse Bedrock/Anthropic/generic error formats
//! - `compute_fingerprint` — SHA-256 of provider:operation:error_type:normalized_msg
//! - `ErrorTracker` — in-memory ring buffer (max 100) with fingerprint dedup map
//!
//! SQLite persistence and macOS desktop notifications are not ported (out of scope
//! for the initial Rust rewrite; the in-memory ring buffer covers dashboard needs).

use chrono::{DateTime, Utc};
use once_cell::sync::Lazy;
use regex::Regex;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{HashMap, VecDeque};
use std::sync::Mutex;

// ────────────────────────────────────────────────────────────────────────────
// Normalization regexes (compiled once)
// ────────────────────────────────────────────────────────────────────────────

static RE_TOOL_ID: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"\btoolu_(?:bdrk_)?[0-9a-zA-Z]+").unwrap());

static RE_UUID: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
        .unwrap()
});

static RE_ARN: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"arn:aws:[a-z0-9-]+:[a-z0-9-]*:\d+:[a-zA-Z0-9/._-]+").unwrap()
});

static RE_LONG_NUM: Lazy<Regex> = Lazy::new(|| Regex::new(r"\b\d{11,}\b").unwrap());

static RE_REQUEST_ID: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?i)\brequest[_\s]?id[:\s]+[a-zA-Z0-9-]+").unwrap()
});

static RE_HEX_SHORT: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"(?<!\w)[0-9a-fA-F]{8,15}(?!\w)").unwrap());

static RE_HEX_LONG: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"\b[0-9a-fA-F]{16,}\b").unwrap());

// Bedrock AWS SDK format: "An error occurred (ExcType) when calling the Op operation: msg"
static RE_BEDROCK_SDK: Lazy<Regex> = Lazy::new(|| {
    Regex::new(
        r"(?i)(?:Bedrock\s+)?(?:validation\s+)?(?:error:\s+)?An error occurred \((\w+)\) when calling the (\w+) operation:?\s*(.+)",
    )
    .unwrap()
});

// Bedrock simple: "Bedrock: ExcType - msg"
static RE_BEDROCK_SIMPLE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?i)(?:Bedrock|bedrock):?\s+(\w+(?:Exception|Error))\s*[-:]\s*(.+)").unwrap()
});

// Generic: "SomeException: msg"
static RE_GENERIC_EXC: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"(\w+(?:Exception|Error)):?\s*(.+)").unwrap());

// ────────────────────────────────────────────────────────────────────────────
// Public types
// ────────────────────────────────────────────────────────────────────────────

/// Stable components extracted from a raw error message.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorSignature {
    pub provider: String,
    pub operation: String,
    pub error_type: String,
    pub message: String,
}

/// One deduplicated error type (aggregated across occurrences).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AggregatedError {
    pub fingerprint: String,
    pub provider: String,
    pub operation: String,
    pub error_type: String,
    pub message: String,
    pub count: u64,
    pub first_seen: DateTime<Utc>,
    pub last_seen: DateTime<Utc>,
}

/// A single raw error occurrence stored in the ring buffer.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorRecord {
    pub timestamp: DateTime<Utc>,
    pub fingerprint: String,
    pub error_type: String,
    pub provider: String,
    pub model: String,
    pub message: String,
}

// ────────────────────────────────────────────────────────────────────────────
// Normalization and fingerprinting
// ────────────────────────────────────────────────────────────────────────────

/// Replace dynamic content (UUIDs, ARNs, hex IDs, long numbers) with stable
/// placeholder tokens so the same logical error always produces the same fingerprint.
pub fn normalize_message(message: &str) -> String {
    let s = RE_TOOL_ID.replace_all(message, "<TOOL_ID>");
    let s = RE_UUID.replace_all(&s, "<UUID>");
    let s = RE_ARN.replace_all(&s, "<MODEL_ARN>");
    let s = RE_LONG_NUM.replace_all(&s, "<ID>");
    let s = RE_REQUEST_ID.replace_all(&s, "request_id <REQUEST_ID>");
    // Long hex before short so the 16+ pattern does not leave 8-15 char tails.
    let s = RE_HEX_LONG.replace_all(&s, "<HEX_ID>");
    let s = RE_HEX_SHORT.replace_all(&s, "<HEX_ID>");
    s.into_owned()
}

/// Parse an error message into its stable components.
pub fn extract_signature(error_message: &str, provider: Option<&str>) -> ErrorSignature {
    let mut sig = ErrorSignature {
        provider: provider.unwrap_or("unknown").to_string(),
        operation: "unknown".to_string(),
        error_type: "unknown".to_string(),
        message: error_message.to_string(),
    };

    // Bedrock SDK format
    if let Some(caps) = RE_BEDROCK_SDK.captures(error_message) {
        sig.provider = "bedrock".to_string();
        sig.error_type = caps[1].to_string();
        sig.operation = caps[2].to_string();
        sig.message = caps[3].trim().to_string();
        return sig;
    }

    // Bedrock simple format
    if let Some(caps) = RE_BEDROCK_SIMPLE.captures(error_message) {
        sig.provider = "bedrock".to_string();
        sig.error_type = caps[1].to_string();
        sig.message = caps[2].trim().to_string();
        return sig;
    }

    let lower = error_message.to_lowercase();

    // Rate limit
    if lower.contains("rate limit") {
        sig.error_type = "RateLimitError".to_string();
        return sig;
    }

    // Timeout
    if lower.contains("timeout") {
        sig.error_type = "TimeoutError".to_string();
        return sig;
    }

    // Auth
    if lower.contains("authentication") || lower.contains("auth") {
        sig.error_type = "AuthenticationError".to_string();
        return sig;
    }

    // Generic exception
    if let Some(caps) = RE_GENERIC_EXC.captures(error_message) {
        sig.error_type = caps[1].to_string();
        sig.message = caps[2].trim().to_string();
        return sig;
    }

    sig
}

/// Compute a 16-character hex fingerprint from a signature.
///
/// SHA-256 of `provider:operation:error_type:normalized_message`, first 16 hex chars.
pub fn compute_fingerprint(sig: &ErrorSignature) -> String {
    let normalized = normalize_message(&sig.message);
    let input = format!(
        "{}:{}:{}:{}",
        sig.provider, sig.operation, sig.error_type, normalized
    );
    let hash = Sha256::digest(input.as_bytes());
    hex::encode(&hash[..8]) // 8 bytes → 16 hex chars
}

// ────────────────────────────────────────────────────────────────────────────
// ErrorTracker
// ────────────────────────────────────────────────────────────────────────────

/// In-memory error tracker: ring buffer of recent occurrences + fingerprint map.
///
/// Equivalent to the Python `ErrorTracker` class but without SQLite persistence.
pub struct ErrorTracker {
    inner: Mutex<ErrorTrackerInner>,
}

struct ErrorTrackerInner {
    /// Recent raw occurrences, newest-first, capped at 100.
    recent: VecDeque<ErrorRecord>,
    /// fingerprint → aggregated stats
    aggregated: HashMap<String, AggregatedError>,
    max_recent: usize,
}

impl ErrorTracker {
    pub fn new() -> Self {
        Self {
            inner: Mutex::new(ErrorTrackerInner {
                recent: VecDeque::new(),
                aggregated: HashMap::new(),
                max_recent: 100,
            }),
        }
    }

    /// Record an error occurrence.
    ///
    /// Returns `(fingerprint, is_new)` where `is_new` is true on the first
    /// occurrence of this error type.
    pub fn push(
        &self,
        error_message: &str,
        provider: &str,
        model: &str,
    ) -> (String, bool) {
        let sig = extract_signature(error_message, Some(provider));
        let fp = compute_fingerprint(&sig);
        let now = Utc::now();

        let mut inner = self.inner.lock().unwrap();

        // Ring buffer: cap at max_recent
        if inner.recent.len() == inner.max_recent {
            inner.recent.pop_back();
        }
        inner.recent.push_front(ErrorRecord {
            timestamp: now,
            fingerprint: fp.clone(),
            error_type: sig.error_type.clone(),
            provider: provider.to_string(),
            model: model.to_string(),
            message: sig.message.clone(),
        });

        // Aggregate
        let is_new = !inner.aggregated.contains_key(&fp);
        if is_new {
            inner.aggregated.insert(
                fp.clone(),
                AggregatedError {
                    fingerprint: fp.clone(),
                    provider: sig.provider.clone(),
                    operation: sig.operation.clone(),
                    error_type: sig.error_type.clone(),
                    message: sig.message.clone(),
                    count: 1,
                    first_seen: now,
                    last_seen: now,
                },
            );
        } else if let Some(agg) = inner.aggregated.get_mut(&fp) {
            agg.count += 1;
            agg.last_seen = now;
        }

        (fp, is_new)
    }

    /// Get the `limit` most recent error records (newest first).
    pub fn get_recent(&self, limit: usize) -> Vec<ErrorRecord> {
        let inner = self.inner.lock().unwrap();
        inner.recent.iter().take(limit).cloned().collect()
    }

    /// Get aggregated error types, sorted by `last_seen` descending.
    pub fn get_summary(&self, limit: usize) -> Vec<AggregatedError> {
        let inner = self.inner.lock().unwrap();
        let mut list: Vec<AggregatedError> = inner.aggregated.values().cloned().collect();
        list.sort_by(|a, b| b.last_seen.cmp(&a.last_seen));
        list.truncate(limit);
        list
    }
}

impl Default for ErrorTracker {
    fn default() -> Self {
        Self::new()
    }
}
