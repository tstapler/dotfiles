use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;

#[derive(Debug, Default)]
pub struct ServerMetrics {
    pub tokens_before: AtomicU64,
    pub tokens_after: AtomicU64,
    pub tools_blocked: AtomicU64,
    pub tool_calls: AtomicU64,
}

impl ServerMetrics {
    pub fn record_session_start(&self, tokens_before: u64, tokens_after: u64) {
        self.tokens_before.store(tokens_before, Ordering::Relaxed);
        self.tokens_after.store(tokens_after, Ordering::Relaxed);
    }

    pub fn record_tool_blocked(&self) {
        self.tools_blocked.fetch_add(1, Ordering::Relaxed);
    }

    pub fn record_tool_call(&self) {
        self.tool_calls.fetch_add(1, Ordering::Relaxed);
    }
}

pub fn estimate_json_tokens(json: &str) -> u64 {
    (json.len() as u64) / 4
}
