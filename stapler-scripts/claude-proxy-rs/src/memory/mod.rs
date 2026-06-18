//! Cross-agent shared context memory store (FR-10).
//!
//! Provides `MemoryStore` + `DedupState` and the axum handler implementations
//! for `PUT /memory/{key}`, `GET /memory/{key}`, and `GET /memory`.

pub mod dedup;
pub mod store;

use std::sync::Arc;

use axum::{
    extract::{Path, Query, State},
    http::{HeaderMap, StatusCode},
    response::{IntoResponse, Json},
};
use chrono::Utc;
use serde::{Deserialize, Serialize};
use serde_json::json;
use tracing::info;

pub use dedup::DedupState;
pub use store::{MemoryEntry, MemoryListItem, MemoryStore};

use dedup::{find_duplicate, register};
use store::compress_value;

/// Combined memory state injected into axum handlers via `State<Arc<MemoryAppState>>`.
pub struct MemoryAppState {
    pub store: MemoryStore,
    pub dedup: DedupState,
}

impl MemoryAppState {
    pub fn new(max_entries: usize) -> Self {
        Self {
            store: MemoryStore::new(max_entries),
            dedup: DedupState::new(),
        }
    }
}

// ---------------------------------------------------------------------------
// Query / request parameter types
// ---------------------------------------------------------------------------

#[derive(Debug, Deserialize)]
pub struct GetMemoryQuery {
    /// If `true`, return the original uncompressed bytes. Default: false.
    #[serde(default)]
    pub full: bool,
}

#[derive(Debug, Deserialize)]
pub struct PutMemoryQuery {
    /// Per-entry TTL override in seconds. Defaults to the store default (24h).
    pub ttl_secs: Option<u64>,
}

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize)]
struct PutResponse {
    action: &'static str,
    key: String,
    size_before: usize,
    size_after: usize,
}

// ---------------------------------------------------------------------------
// Handler implementations (called from main.rs after AppState is wired up)
// ---------------------------------------------------------------------------

/// `PUT /memory/{key}` — store a value, run dedup, return action + size stats.
pub async fn handler_memory_put(
    State(state): State<Arc<MemoryAppState>>,
    Path(key): Path<String>,
    Query(params): Query<PutMemoryQuery>,
    headers: HeaderMap,
    body: axum::body::Bytes,
) -> impl IntoResponse {
    let agent_id = headers
        .get("x-agent-id")
        .and_then(|v| v.to_str().ok())
        .or_else(|| headers.get("user-agent").and_then(|v| v.to_str().ok()))
        .unwrap_or("unknown")
        .to_owned();

    let user_agent = headers
        .get("user-agent")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("")
        .to_owned();

    let raw = body.to_vec();
    let size_before = raw.len();
    let compressed = compress_value(&raw);
    let size_after = compressed.len();
    let ttl_secs = params.ttl_secs.unwrap_or(86_400);

    // Check for near-duplicate (≥95% similar existing entry).
    let dup_key = find_duplicate(&state.store, &state.dedup, &raw).await;

    let (action, effective_key) = if let Some(existing_key) = dup_key {
        // Update the existing entry in-place (same key, new provenance + timestamp).
        let entry = Arc::new(MemoryEntry {
            value_compressed: compressed,
            value_original: raw.clone(),
            agent_id: agent_id.clone(),
            user_agent: user_agent.clone(),
            created_at: Utc::now(),
            size_before,
            size_after,
            ttl_secs,
        });
        state.store.put(existing_key.clone(), entry).await;
        register(&state.dedup, &existing_key, &raw);
        info!(key = %existing_key, size_before, size_after, "memory: dedup update");
        ("updated", existing_key)
    } else {
        let entry = Arc::new(MemoryEntry {
            value_compressed: compressed,
            value_original: raw.clone(),
            agent_id: agent_id.clone(),
            user_agent: user_agent.clone(),
            created_at: Utc::now(),
            size_before,
            size_after,
            ttl_secs,
        });
        state.store.put(key.clone(), entry).await;
        register(&state.dedup, &key, &raw);
        info!(key = %key, size_before, size_after, "memory: created");
        ("created", key)
    };

    Json(PutResponse {
        action,
        key: effective_key,
        size_before,
        size_after,
    })
}

/// `GET /memory/{key}` — retrieve a value.
///
/// Default: returns compressed bytes with `Content-Type: application/octet-stream`.
/// `?full=true`: returns original bytes.
pub async fn handler_memory_get(
    State(state): State<Arc<MemoryAppState>>,
    Path(key): Path<String>,
    Query(params): Query<GetMemoryQuery>,
) -> impl IntoResponse {
    match state.store.get(&key).await {
        None => (
            StatusCode::NOT_FOUND,
            Json(json!({"error": "not found", "key": key})),
        )
            .into_response(),
        Some(entry) => {
            let bytes = if params.full {
                entry.value_original.clone()
            } else {
                entry.value_compressed.clone()
            };
            (
                StatusCode::OK,
                [("content-type", "application/octet-stream")],
                bytes,
            )
                .into_response()
        }
    }
}

/// `GET /memory` — list all keys with metadata.
pub async fn handler_memory_list(
    State(state): State<Arc<MemoryAppState>>,
) -> impl IntoResponse {
    let all = state.store.list_all().await;
    let now = Utc::now();

    let items: Vec<MemoryListItem> = all
        .into_iter()
        .map(|(key, entry)| {
            let age_secs = (now - entry.created_at).num_seconds();
            let ttl_remaining_secs = entry.ttl_secs as i64 - age_secs;
            MemoryListItem {
                key,
                agent_id: entry.agent_id.clone(),
                size_before: entry.size_before,
                size_after: entry.size_after,
                created_at: entry.created_at,
                ttl_remaining_secs,
            }
        })
        .collect();

    let count = items.len();
    Json(json!({ "entries": items, "count": count }))
}
