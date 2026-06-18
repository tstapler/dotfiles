//! Rolling latency histogram with 15-minute sliding window.
//!
//! Stores (timestamp, duration_ms) pairs in a `VecDeque` and trims entries
//! older than the window on every operation. Computes p50/p95/p99 and rpm.

use std::collections::VecDeque;
use std::sync::Mutex;
use std::time::{Duration, Instant};

/// A rolling-window histogram for request latency.
///
/// Thread-safe via an internal `Mutex`. The window defaults to 15 minutes.
pub struct DurationHistogram {
    /// (sample_time, duration_ms)
    samples: Mutex<VecDeque<(Instant, u64)>>,
    window: Duration,
}

impl DurationHistogram {
    /// Create a new histogram with the given rolling window.
    pub fn new(window: Duration) -> Self {
        Self {
            samples: Mutex::new(VecDeque::new()),
            window,
        }
    }

    /// Create a new histogram with a default 15-minute window.
    pub fn with_default_window() -> Self {
        Self::new(Duration::from_secs(15 * 60))
    }

    /// Record a new duration sample. Drops samples older than the window.
    pub fn record(&self, duration_ms: u64) {
        let now = Instant::now();
        let cutoff = now.checked_sub(self.window).unwrap_or(now);
        let mut samples = self.samples.lock().unwrap();
        samples.push_back((now, duration_ms));
        // Trim expired samples from the front.
        while samples.front().map_or(false, |(t, _)| *t < cutoff) {
            samples.pop_front();
        }
    }

    /// Compute (p50, p95, p99) over the current window.
    ///
    /// Returns `(0, 0, 0)` if the window is empty.
    pub fn percentiles(&self) -> (u64, u64, u64) {
        let now = Instant::now();
        let cutoff = now.checked_sub(self.window).unwrap_or(now);
        let samples = self.samples.lock().unwrap();

        let mut values: Vec<u64> = samples
            .iter()
            .filter(|(t, _)| *t >= cutoff)
            .map(|(_, d)| *d)
            .collect();

        if values.is_empty() {
            return (0, 0, 0);
        }

        values.sort_unstable();
        let n = values.len();
        let p = |pct: f64| values[((n as f64 * pct / 100.0) as usize).min(n - 1)];
        (p(50.0), p(95.0), p(99.0))
    }

    /// Requests per minute over the last 60 seconds.
    pub fn requests_per_minute(&self) -> f64 {
        let now = Instant::now();
        let one_min_ago = now.checked_sub(Duration::from_secs(60)).unwrap_or(now);
        let samples = self.samples.lock().unwrap();
        let count = samples
            .iter()
            .filter(|(t, _)| *t >= one_min_ago)
            .count();
        count as f64
    }

    /// Build RPM chart data: one bucket per minute for the last `minutes` minutes.
    ///
    /// Returns `Vec<(minute_label_string, count)>`.
    pub fn rpm_chart_data(&self, minutes: u32) -> Vec<serde_json::Value> {
        let now = Instant::now();
        let samples = self.samples.lock().unwrap();

        let mut buckets = vec![0u64; minutes as usize];
        let total_secs = minutes as u64 * 60;

        for (t, _) in samples.iter() {
            // How many seconds ago was this sample?
            if let Some(age) = now.checked_duration_since(*t) {
                let age_secs = age.as_secs();
                if age_secs < total_secs {
                    // Bucket index: 0 = oldest, last = most recent
                    let bucket_from_end = age_secs / 60;
                    let idx = (minutes as u64 - 1 - bucket_from_end) as usize;
                    if idx < buckets.len() {
                        buckets[idx] += 1;
                    }
                }
            }
        }

        buckets
            .iter()
            .enumerate()
            .map(|(i, &count)| {
                // Label as minutes-ago offset (simple HH:MM-style label would need system time)
                let offset_min = minutes as i64 - i as i64 - 1;
                serde_json::json!({
                    "minute": format!("-{}m", offset_min),
                    "requests": count
                })
            })
            .collect()
    }

    /// Build lag chart data for the last `minutes` minutes (stub — returns zeroed buckets).
    ///
    /// Lag data is tracked separately via the event loop lag probe; this method
    /// returns placeholder data so the dashboard chart renders without errors.
    pub fn lag_chart_data(&self, minutes: u32) -> Vec<serde_json::Value> {
        (0..minutes)
            .map(|i| {
                let offset_min = minutes as i64 - i as i64 - 1;
                serde_json::json!({
                    "minute": format!("-{}m", offset_min),
                    "max_ms": 0.0,
                    "avg_ms": 0.0
                })
            })
            .collect()
    }
}
