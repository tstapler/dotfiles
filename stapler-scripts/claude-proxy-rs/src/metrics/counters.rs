//! Atomic counters for request, compression, and error metrics.
//!
//! All counters use `AtomicU64` for lock-free concurrent access.
//! The `ProxyMetrics` struct holds a complete snapshot of all proxy statistics.

use serde_json::{json, Value};
use std::sync::atomic::{AtomicU64, Ordering};

/// All proxy metrics as atomic counters.
///
/// Designed for concurrent access with no locks — each field is independently
/// updated by request handlers and background tasks.
pub struct ProxyMetrics {
    // ---- Request counters ----
    pub requests_total: AtomicU64,
    pub requests_anthropic: AtomicU64,
    pub requests_bedrock: AtomicU64,
    pub requests_success: AtomicU64,
    pub errors_total: AtomicU64,
    pub fallback_switches: AtomicU64,

    // ---- Error type counters ----
    pub err_timeout: AtomicU64,
    pub err_auth: AtomicU64,
    pub err_rate_limit: AtomicU64,
    pub err_validation: AtomicU64,

    // ---- Compression counters ----
    pub tokens_before: AtomicU64,
    pub tokens_after: AtomicU64,
    pub requests_compressed: AtomicU64,

    // ---- Cache counters ----
    pub cache_aligner_applied: AtomicU64,
    pub cache_hits_estimated: AtomicU64,
    pub cache_misses_estimated: AtomicU64,

    // ---- Learn counters ----
    pub learn_patterns_found: AtomicU64,
    pub verbosity_applied: AtomicU64,

    // ---- Memory store counters ----
    pub memory_puts: AtomicU64,
    pub memory_gets: AtomicU64,
    pub memory_dedup_hits: AtomicU64,

    // ---- count_tokens counters ----
    pub count_tokens_total: AtomicU64,
    pub count_tokens_failures: AtomicU64,

    // ---- Provider latency accumulators ----
    pub anthropic_duration_sum_ms: AtomicU64,
    pub anthropic_duration_count: AtomicU64,
    pub anthropic_first_byte_sum_ms: AtomicU64,
    pub anthropic_first_byte_count: AtomicU64,
    pub bedrock_duration_sum_ms: AtomicU64,
    pub bedrock_duration_count: AtomicU64,
    pub bedrock_first_byte_sum_ms: AtomicU64,
    pub bedrock_first_byte_count: AtomicU64,

    // ---- Duration bucket counters ----
    pub duration_lt1s: AtomicU64,
    pub duration_1_5s: AtomicU64,
    pub duration_5_30s: AtomicU64,
    pub duration_30_60s: AtomicU64,
    pub duration_gt60s: AtomicU64,
}

impl ProxyMetrics {
    /// Create a new zeroed metrics instance.
    #[allow(clippy::new_without_default)]
    pub fn new() -> Self {
        Self {
            requests_total: AtomicU64::new(0),
            requests_anthropic: AtomicU64::new(0),
            requests_bedrock: AtomicU64::new(0),
            requests_success: AtomicU64::new(0),
            errors_total: AtomicU64::new(0),
            fallback_switches: AtomicU64::new(0),

            err_timeout: AtomicU64::new(0),
            err_auth: AtomicU64::new(0),
            err_rate_limit: AtomicU64::new(0),
            err_validation: AtomicU64::new(0),

            tokens_before: AtomicU64::new(0),
            tokens_after: AtomicU64::new(0),
            requests_compressed: AtomicU64::new(0),

            cache_aligner_applied: AtomicU64::new(0),
            cache_hits_estimated: AtomicU64::new(0),
            cache_misses_estimated: AtomicU64::new(0),

            learn_patterns_found: AtomicU64::new(0),
            verbosity_applied: AtomicU64::new(0),

            memory_puts: AtomicU64::new(0),
            memory_gets: AtomicU64::new(0),
            memory_dedup_hits: AtomicU64::new(0),

            count_tokens_total: AtomicU64::new(0),
            count_tokens_failures: AtomicU64::new(0),

            anthropic_duration_sum_ms: AtomicU64::new(0),
            anthropic_duration_count: AtomicU64::new(0),
            anthropic_first_byte_sum_ms: AtomicU64::new(0),
            anthropic_first_byte_count: AtomicU64::new(0),
            bedrock_duration_sum_ms: AtomicU64::new(0),
            bedrock_duration_count: AtomicU64::new(0),
            bedrock_first_byte_sum_ms: AtomicU64::new(0),
            bedrock_first_byte_count: AtomicU64::new(0),

            duration_lt1s: AtomicU64::new(0),
            duration_1_5s: AtomicU64::new(0),
            duration_5_30s: AtomicU64::new(0),
            duration_30_60s: AtomicU64::new(0),
            duration_gt60s: AtomicU64::new(0),
        }
    }

    /// Record a completed request, updating provider, duration bucket, and success/error counters.
    pub fn record_request(
        &self,
        provider: &str,
        success: bool,
        duration_ms: u64,
        first_byte_ms: u64,
    ) {
        self.requests_total.fetch_add(1, Ordering::Relaxed);
        if success {
            self.requests_success.fetch_add(1, Ordering::Relaxed);
        } else {
            self.errors_total.fetch_add(1, Ordering::Relaxed);
        }

        match provider {
            "anthropic" => {
                self.requests_anthropic.fetch_add(1, Ordering::Relaxed);
                self.anthropic_duration_sum_ms
                    .fetch_add(duration_ms, Ordering::Relaxed);
                self.anthropic_duration_count.fetch_add(1, Ordering::Relaxed);
                if first_byte_ms > 0 {
                    self.anthropic_first_byte_sum_ms
                        .fetch_add(first_byte_ms, Ordering::Relaxed);
                    self.anthropic_first_byte_count
                        .fetch_add(1, Ordering::Relaxed);
                }
            }
            "bedrock" => {
                self.requests_bedrock.fetch_add(1, Ordering::Relaxed);
                self.bedrock_duration_sum_ms
                    .fetch_add(duration_ms, Ordering::Relaxed);
                self.bedrock_duration_count.fetch_add(1, Ordering::Relaxed);
                if first_byte_ms > 0 {
                    self.bedrock_first_byte_sum_ms
                        .fetch_add(first_byte_ms, Ordering::Relaxed);
                    self.bedrock_first_byte_count
                        .fetch_add(1, Ordering::Relaxed);
                }
            }
            _ => {}
        }

        // Duration bucket
        match duration_ms {
            d if d < 1_000 => {
                self.duration_lt1s.fetch_add(1, Ordering::Relaxed);
            }
            d if d < 5_000 => {
                self.duration_1_5s.fetch_add(1, Ordering::Relaxed);
            }
            d if d < 30_000 => {
                self.duration_5_30s.fetch_add(1, Ordering::Relaxed);
            }
            d if d < 60_000 => {
                self.duration_30_60s.fetch_add(1, Ordering::Relaxed);
            }
            _ => {
                self.duration_gt60s.fetch_add(1, Ordering::Relaxed);
            }
        }
    }

    /// Snapshot all counters into a `serde_json::Value` for the `/metrics` endpoint.
    pub fn to_json(&self) -> Value {
        let total = self.requests_total.load(Ordering::Relaxed);
        let success = self.requests_success.load(Ordering::Relaxed);
        let errors = self.errors_total.load(Ordering::Relaxed);
        let fallbacks = self.fallback_switches.load(Ordering::Relaxed);

        let success_rate = if total > 0 {
            (success as f64 / total as f64) * 100.0
        } else {
            0.0
        };
        let error_rate = if total > 0 {
            (errors as f64 / total as f64) * 100.0
        } else {
            0.0
        };

        let anthropic_req = self.requests_anthropic.load(Ordering::Relaxed);
        let bedrock_req = self.requests_bedrock.load(Ordering::Relaxed);

        // Compression stats
        let tb = self.tokens_before.load(Ordering::Relaxed);
        let ta = self.tokens_after.load(Ordering::Relaxed);
        let tokens_saved = tb.saturating_sub(ta);
        let avg_ratio = if tb > 0 {
            tokens_saved as f64 / tb as f64
        } else {
            0.0
        };

        // Provider latency
        let anth_dur_count = self.anthropic_duration_count.load(Ordering::Relaxed);
        let anth_dur_avg = if anth_dur_count > 0 {
            self.anthropic_duration_sum_ms.load(Ordering::Relaxed) / anth_dur_count
        } else {
            0
        };
        let anth_fb_count = self.anthropic_first_byte_count.load(Ordering::Relaxed);
        let anth_fb_avg = if anth_fb_count > 0 {
            self.anthropic_first_byte_sum_ms.load(Ordering::Relaxed) / anth_fb_count
        } else {
            0
        };
        let brk_dur_count = self.bedrock_duration_count.load(Ordering::Relaxed);
        let brk_dur_avg = if brk_dur_count > 0 {
            self.bedrock_duration_sum_ms.load(Ordering::Relaxed) / brk_dur_count
        } else {
            0
        };
        let brk_fb_count = self.bedrock_first_byte_count.load(Ordering::Relaxed);
        let brk_fb_avg = if brk_fb_count > 0 {
            self.bedrock_first_byte_sum_ms.load(Ordering::Relaxed) / brk_fb_count
        } else {
            0
        };

        let ct_total = self.count_tokens_total.load(Ordering::Relaxed);
        let ct_failures = self.count_tokens_failures.load(Ordering::Relaxed);
        let ct_failure_rate = if ct_total > 0 {
            ct_failures as f64 / ct_total as f64
        } else {
            0.0
        };

        json!({
            "summary": {
                "total_requests": total,
                "total_success": success,
                "total_errors": errors,
                "total_fallbacks": fallbacks,
                "success_rate": (success_rate * 100.0).round() / 100.0,
                "error_rate": (error_rate * 100.0).round() / 100.0
            },
            "providers": {
                "anthropic": {
                    "requests": anthropic_req,
                    "success": 0u64,
                    "errors": 0u64
                },
                "bedrock": {
                    "requests": bedrock_req,
                    "success": 0u64,
                    "errors": 0u64
                },
                "none": {
                    "requests": 0u64,
                    "success": 0u64,
                    "errors": 0u64
                }
            },
            "provider_latency": {
                "anthropic": {
                    "avg_duration_ms": anth_dur_avg,
                    "avg_first_byte_ms": anth_fb_avg,
                    "requests": anth_dur_count
                },
                "bedrock": {
                    "avg_duration_ms": brk_dur_avg,
                    "avg_first_byte_ms": brk_fb_avg,
                    "requests": brk_dur_count
                }
            },
            "compression": {
                "total_tokens_before": tb,
                "total_tokens_after": ta,
                "total_tokens_saved": tokens_saved,
                "total_requests_compressed": self.requests_compressed.load(Ordering::Relaxed),
                "avg_compression_ratio": (avg_ratio * 1000.0).round() / 1000.0
            },
            "memory": {
                "puts": self.memory_puts.load(Ordering::Relaxed),
                "gets": self.memory_gets.load(Ordering::Relaxed),
                "dedup_hits": self.memory_dedup_hits.load(Ordering::Relaxed)
            },
            "learn": {
                "patterns_found": self.learn_patterns_found.load(Ordering::Relaxed)
            },
            "cache": {
                "aligner_applied": self.cache_aligner_applied.load(Ordering::Relaxed),
                "hits_estimated": self.cache_hits_estimated.load(Ordering::Relaxed),
                "misses_estimated": self.cache_misses_estimated.load(Ordering::Relaxed)
            },
            "duration_distribution": {
                "< 1s": self.duration_lt1s.load(Ordering::Relaxed),
                "1-5s": self.duration_1_5s.load(Ordering::Relaxed),
                "5-30s": self.duration_5_30s.load(Ordering::Relaxed),
                "30-60s": self.duration_30_60s.load(Ordering::Relaxed),
                "> 60s": self.duration_gt60s.load(Ordering::Relaxed)
            },
            "count_tokens": {
                "total": ct_total,
                "failures": ct_failures,
                "failure_rate": (ct_failure_rate * 1000.0).round() / 1000.0,
                "last_count": 0u64,
                "last_model": ""
            },
            "error_types": {
                "timeout": self.err_timeout.load(Ordering::Relaxed),
                "auth": self.err_auth.load(Ordering::Relaxed),
                "rate_limit": self.err_rate_limit.load(Ordering::Relaxed),
                "validation": self.err_validation.load(Ordering::Relaxed)
            }
        })
    }
}
