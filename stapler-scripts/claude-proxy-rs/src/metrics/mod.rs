//! Metrics collection: atomic counters, rolling histogram, error tracker,
//! request ring buffer, event-loop lag probe, and the `/metrics` JSON handler.

pub mod counters;
pub mod error_tracker;
pub mod histogram;

use std::collections::VecDeque;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use chrono::Utc;
use serde::{Deserialize, Serialize};
use serde_json::json;
use tokio::time::sleep;

pub use counters::ProxyMetrics;
pub use error_tracker::{AggregatedError, ErrorRecord, ErrorTracker};
pub use histogram::DurationHistogram;

// Re-export so callers can use metrics::AggregatedError etc. without
// specifying the sub-module path.
#[allow(unused_imports)]
pub use error_tracker::{compute_fingerprint, extract_signature, normalize_message};

// ────────────────────────────────────────────────────────────────────────────
// RequestDetail — per-request ring-buffer entry
// ────────────────────────────────────────────────────────────────────────────

/// Lightweight per-request record for the dashboard "Recent Requests" table.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RequestDetail {
    pub request_id: String,
    pub timestamp: String,
    pub model: String,
    pub provider: String,
    pub tokens_before: u64,
    pub tokens_after: u64,
    pub compressed: bool,
    pub stream: bool,
    pub msg_types: String,
    pub has_context_management: bool,
    pub message_count: u32,
    pub duration_ms: f64,
    pub first_byte_ms: f64,
    pub bedrock_invocation_ms: u64,
    pub bedrock_first_byte_ms: u64,
}

// ────────────────────────────────────────────────────────────────────────────
// LagSample — event loop lag ring buffer entry
// ────────────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
struct LagSample {
    timestamp: Instant,
    lag_ms: f64,
}

// ────────────────────────────────────────────────────────────────────────────
// MetricsCollector — the central hub
// ────────────────────────────────────────────────────────────────────────────

/// All metrics state, designed to be held in an `Arc<MetricsCollector>` in
/// `AppState` and shared across request handlers.
pub struct MetricsCollector {
    pub counters: Arc<ProxyMetrics>,
    pub histogram: Arc<DurationHistogram>,
    pub error_tracker: Arc<ErrorTracker>,
    /// Ring buffer: last 100 requests (newest first).
    recent_requests: Mutex<VecDeque<RequestDetail>>,
    /// Rolling event-loop lag samples (15-min window).
    lag_samples: Mutex<VecDeque<LagSample>>,
    /// Most recent lag measurement in milliseconds.
    current_lag_ms: Mutex<f64>,
}

impl MetricsCollector {
    pub fn new() -> Arc<Self> {
        Arc::new(Self {
            counters: Arc::new(ProxyMetrics::new()),
            histogram: Arc::new(DurationHistogram::with_default_window()),
            error_tracker: Arc::new(ErrorTracker::new()),
            recent_requests: Mutex::new(VecDeque::new()),
            lag_samples: Mutex::new(VecDeque::new()),
            current_lag_ms: Mutex::new(0.0),
        })
    }

    // ── Request ring buffer ──────────────────────────────────────────────────

    /// Push a new request detail to the ring buffer (capped at 100 entries).
    pub fn push_request(&self, detail: RequestDetail) {
        let mut buf = self.recent_requests.lock().unwrap();
        if buf.len() == 100 {
            buf.pop_back();
        }
        buf.push_front(detail);
    }

    /// Update timing fields on an existing request by ID.
    pub fn update_request_timing(
        &self,
        request_id: &str,
        provider: &str,
        duration_ms: f64,
        first_byte_ms: f64,
        bedrock_invocation_ms: u64,
        bedrock_first_byte_ms: u64,
    ) {
        let mut buf = self.recent_requests.lock().unwrap();
        for r in buf.iter_mut() {
            if r.request_id == request_id {
                r.provider = provider.to_string();
                r.duration_ms = (duration_ms * 10.0).round() / 10.0;
                r.first_byte_ms = (first_byte_ms * 10.0).round() / 10.0;
                r.bedrock_invocation_ms = bedrock_invocation_ms;
                r.bedrock_first_byte_ms = bedrock_first_byte_ms;
                return;
            }
        }
    }

    /// Get the last `n` requests (newest first).
    pub fn get_recent_requests(&self, n: usize) -> Vec<RequestDetail> {
        let buf = self.recent_requests.lock().unwrap();
        buf.iter().take(n).cloned().collect()
    }

    // ── Event loop lag ───────────────────────────────────────────────────────

    /// Record an event loop lag sample, trimming entries older than 15 minutes.
    pub fn record_lag(&self, lag_ms: f64) {
        let now = Instant::now();
        let cutoff = now
            .checked_sub(Duration::from_secs(15 * 60))
            .unwrap_or(now);
        let mut lag = self.lag_samples.lock().unwrap();
        lag.push_back(LagSample {
            timestamp: now,
            lag_ms,
        });
        while lag.front().map_or(false, |s| s.timestamp < cutoff) {
            lag.pop_front();
        }
        *self.current_lag_ms.lock().unwrap() = lag_ms;
    }

    fn current_lag_ms(&self) -> f64 {
        *self.current_lag_ms.lock().unwrap()
    }

    /// Build the `lag_data` array for the 15-minute lag chart (1 bucket per minute).
    fn lag_chart_data(&self) -> Vec<serde_json::Value> {
        let now = Instant::now();
        let minutes: u32 = 16;
        let mut max_buckets = vec![0.0f64; minutes as usize];
        let mut sum_buckets = vec![0.0f64; minutes as usize];
        let mut count_buckets = vec![0u32; minutes as usize];

        let lag = self.lag_samples.lock().unwrap();
        for s in lag.iter() {
            if let Some(age) = now.checked_duration_since(s.timestamp) {
                let age_secs = age.as_secs();
                let total_secs = minutes as u64 * 60;
                if age_secs < total_secs {
                    let bucket_from_end = age_secs / 60;
                    let idx = (minutes as u64 - 1 - bucket_from_end) as usize;
                    if idx < max_buckets.len() {
                        if s.lag_ms > max_buckets[idx] {
                            max_buckets[idx] = s.lag_ms;
                        }
                        sum_buckets[idx] += s.lag_ms;
                        count_buckets[idx] += 1;
                    }
                }
            }
        }
        drop(lag);

        (0..minutes as usize)
            .map(|i| {
                let offset_min = minutes as i64 - i as i64 - 1;
                let avg = if count_buckets[i] > 0 {
                    sum_buckets[i] / count_buckets[i] as f64
                } else {
                    0.0
                };
                json!({
                    "minute": format!("-{}m", offset_min),
                    "max_ms": (max_buckets[i] * 100.0).round() / 100.0,
                    "avg_ms": (avg * 100.0).round() / 100.0
                })
            })
            .collect()
    }

    // ── Full metrics JSON for GET /metrics ───────────────────────────────────

    /// Build the full `/metrics` JSON response (wire-compatible with Python proxy).
    pub fn to_metrics_json(&self) -> serde_json::Value {
        let counters_json = self.counters.to_json();

        // RPM chart data from histogram
        let rpm_data = self.histogram.rpm_chart_data(16);

        // Latency percentiles
        let (p50, p95, p99) = self.histogram.percentiles();
        let rpm = self.histogram.requests_per_minute();

        // Recent requests
        let recent_requests: Vec<serde_json::Value> = self
            .get_recent_requests(20)
            .iter()
            .map(|r| serde_json::to_value(r).unwrap_or(serde_json::Value::Null))
            .collect();

        // Recent errors
        let recent_errors: Vec<serde_json::Value> = self
            .error_tracker
            .get_recent(20)
            .iter()
            .map(|e| serde_json::to_value(e).unwrap_or(serde_json::Value::Null))
            .collect();

        // Merge counters JSON with additional fields
        let mut result = counters_json;

        // Performance overlay
        result["performance"] = json!({
            "p50_ms": p50,
            "p95_ms": p95,
            "p99_ms": p99,
            "rpm": (rpm * 10.0).round() / 10.0
        });

        result["rpm_data"] = serde_json::Value::Array(rpm_data);
        result["lag_data"] = serde_json::Value::Array(self.lag_chart_data());
        result["current_lag_ms"] = json!(self.current_lag_ms());
        result["recent_requests"] = serde_json::Value::Array(recent_requests);
        result["recent_errors"] = serde_json::Value::Array(recent_errors);
        result["timestamp"] = json!(Utc::now().to_rfc3339());

        // Cooldowns placeholder (wired in from FallbackState in future epics)
        result["cooldowns"] = json!({
            "anthropic": { "cooling_down": false, "remaining_seconds": 0 },
            "bedrock": { "cooling_down": false, "remaining_seconds": 0 }
        });

        result
    }
}

impl Default for MetricsCollector {
    fn default() -> Self {
        // Can't return Arc here — provide the unwrapped struct for completeness.
        Self {
            counters: Arc::new(ProxyMetrics::new()),
            histogram: Arc::new(DurationHistogram::with_default_window()),
            error_tracker: Arc::new(ErrorTracker::new()),
            recent_requests: Mutex::new(VecDeque::new()),
            lag_samples: Mutex::new(VecDeque::new()),
            current_lag_ms: Mutex::new(0.0),
        }
    }
}

// ────────────────────────────────────────────────────────────────────────────
// Event loop lag probe
// ────────────────────────────────────────────────────────────────────────────

/// Spawn a background Tokio task that measures scheduler skew every second.
///
/// Each iteration sleeps for 10ms then measures how much extra time elapsed.
/// Semantically equivalent to Python's `_monitor_event_loop_lag()`.
pub async fn measure_event_loop_lag() -> Duration {
    let start = Instant::now();
    sleep(Duration::from_millis(10)).await;
    let elapsed = start.elapsed();
    elapsed.saturating_sub(Duration::from_millis(10))
}

/// Long-running lag monitoring task. Call with `tokio::spawn`.
pub async fn run_lag_monitor(metrics: Arc<MetricsCollector>) {
    loop {
        let lag = measure_event_loop_lag().await;
        let lag_ms = lag.as_secs_f64() * 1000.0;
        metrics.record_lag(lag_ms);
        if lag_ms > 200.0 {
            tracing::warn!(lag_ms, "event loop lag elevated");
        }
        // Sleep for the remainder of a 1s interval (already consumed ~10ms).
        sleep(Duration::from_millis(990)).await;
    }
}
