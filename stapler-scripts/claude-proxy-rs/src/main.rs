//! claude-proxy-rs — Rust rewrite of the Claude Code OAuth + Bedrock fallback proxy.
//!
//! Entry point: builds the tokio runtime explicitly, initialises logging,
//! reads config, constructs the axum router, and serves until SIGTERM/SIGINT.

mod auth;
mod compression;
mod config;
mod dashboard;
mod fallback;
mod learn;
mod memory;
mod metrics;
mod providers;
mod system_prompt;

use std::collections::VecDeque;
use std::net::SocketAddr;
use std::sync::Arc;
use std::time::{Duration, Instant};

use axum::{
    body::Bytes,
    extract::{Query, State},
    http::{header, HeaderMap, StatusCode},
    response::{
        sse::{Event, KeepAlive, Sse},
        IntoResponse, Response,
    },
    routing::{get, post, put},
    Json, Router,
};
use axum::extract::DefaultBodyLimit;
use futures_util::StreamExt;
use rolling_file::{BasicRollingFileAppender, RollingConditionBasic};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tokio::sync::Mutex;
use tower_http::trace::TraceLayer;
use tracing::{info, warn};
use tracing_appender::non_blocking;
use tracing_subscriber::{filter, layer::SubscriberExt, util::SubscriberInitExt, Layer};

use config::Config;
use fallback::{FallbackHandler, FallbackState};
use memory::MemoryAppState;
use metrics::{run_lag_monitor, MetricsCollector};
use providers::{anthropic::AnthropicProvider, bedrock::BedrockProvider, ProviderResponse};

// ────────────────────────────────────────────────────────────────────────────
// AppState
// ────────────────────────────────────────────────────────────────────────────

/// Shared application state passed to all route handlers.
#[derive(Clone)]
struct AppState {
    config: Arc<Config>,
    metrics: Arc<MetricsCollector>,
    memory: Arc<MemoryAppState>,
    fallback: Arc<FallbackHandler<AnthropicProvider, BedrockProvider>>,
    fallback_state: Arc<FallbackState>,
    request_ring: Arc<Mutex<VecDeque<RequestSummary>>>,
    compression: Arc<compression::CompressionEngine>,
    system_prompt: Arc<system_prompt::SystemPromptPipeline>,
}

/// Lightweight per-request summary stored in the ring buffer for `GET /requests`.
#[derive(Debug, Clone, Serialize, Deserialize)]
struct RequestSummary {
    request_id: String,
    timestamp: String,
    model: String,
    provider_used: String,
    duration_ms: f64,
    status_code: u16,
    stream: bool,
}

// Allow axum to extract Arc<MemoryAppState> directly from AppState.
impl axum::extract::FromRef<AppState> for Arc<MemoryAppState> {
    fn from_ref(state: &AppState) -> Arc<MemoryAppState> {
        Arc::clone(&state.memory)
    }
}

// ────────────────────────────────────────────────────────────────────────────
// Entry point
// ────────────────────────────────────────────────────────────────────────────

fn main() {
    let rt = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .thread_name("proxy-worker")
        .build()
        .expect("failed to build tokio runtime");

    rt.block_on(async_main());
}

async fn async_main() {
    let (_app_guard, _http_guard) = init_logging();

    let config = Arc::new(Config::from_env());
    info!(
        port = config.port,
        compress = config.stapler_compress,
        verbosity = config.verbosity_level,
        "claude-proxy-rs starting"
    );

    // ── Providers ──────────────────────────────────────────────────────────
    let anthropic = AnthropicProvider::new(&config)
        .expect("failed to build AnthropicProvider");
    let bedrock = BedrockProvider::new((*config).clone()).await;
    let fallback_state = Arc::new(FallbackState::new(config.cooldown_seconds));
    let fallback = Arc::new(FallbackHandler::new(
        anthropic,
        bedrock,
        Arc::clone(&fallback_state),
        config.bedrock_max_retries,
    ));

    // ── Compression engine ─────────────────────────────────────────────────
    let rewind_store = Arc::new(compression::RewindStore::new().await);
    let compression_cfg = compression::CompressionConfig {
        compress_floor_bytes: config.compress_floor_bytes,
    };
    let compression_engine = Arc::new(
        compression::CompressionEngine::new(compression_cfg, Arc::clone(&rewind_store)).await,
    );

    // ── System prompt pipeline ──────────────────────────────────────────────
    let spp = Arc::new(system_prompt::SystemPromptPipeline::new(Arc::clone(&config)));

    // ── Metrics ─────────────────────────────────────────────────────────────
    let metrics = MetricsCollector::new();
    tokio::spawn(run_lag_monitor(Arc::clone(&metrics)));

    let state = AppState {
        config: Arc::clone(&config),
        metrics: Arc::clone(&metrics),
        memory: Arc::new(MemoryAppState::new(config.memory_max_entries)),
        fallback,
        fallback_state,
        request_ring: Arc::new(Mutex::new(VecDeque::new())),
        compression: compression_engine,
        system_prompt: spp,
    };

    let app = build_router(state);

    let addr = SocketAddr::from(([127, 0, 0, 1], config.port));
    info!(%addr, "listening");

    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .expect("failed to bind address");

    axum::serve(listener, app)
        .with_graceful_shutdown(build_shutdown_signal())
        .await
        .expect("server error");
}

/// Build a future that resolves on SIGINT or SIGTERM.
async fn build_shutdown_signal() {
    #[cfg(unix)]
    {
        use tokio::signal::unix::{signal, SignalKind};
        let mut sigterm = signal(SignalKind::terminate()).expect("failed to install SIGTERM handler");
        tokio::select! {
            _ = tokio::signal::ctrl_c() => {
                info!("received SIGINT, shutting down");
            }
            _ = sigterm.recv() => {
                info!("received SIGTERM, shutting down");
            }
        }
    }
    #[cfg(not(unix))]
    {
        tokio::signal::ctrl_c().await.expect("ctrl_c failed");
        info!("received SIGINT, shutting down");
    }
}

/// Initialise rotating file loggers and return `WorkerGuard` handles.
fn init_logging() -> (non_blocking::WorkerGuard, non_blocking::WorkerGuard) {
    let app_appender = BasicRollingFileAppender::new(
        "/tmp/claude-proxy-rs.app.log",
        RollingConditionBasic::new().max_size(10 * 1024 * 1024),
        10,
    )
    .expect("failed to create app log appender");
    let (app_writer, app_guard) = non_blocking(app_appender);

    let http_appender = BasicRollingFileAppender::new(
        "/tmp/claude-proxy-rs.http.log",
        RollingConditionBasic::new().max_size(10 * 1024 * 1024),
        5,
    )
    .expect("failed to create http log appender");
    let (http_writer, http_guard) = non_blocking(http_appender);

    let app_layer = tracing_subscriber::fmt::layer()
        .with_writer(app_writer)
        .with_filter(filter::filter_fn(|meta| meta.target() != "http_access"));

    let http_layer = tracing_subscriber::fmt::layer()
        .with_writer(http_writer)
        .with_filter(filter::filter_fn(|meta| meta.target() == "http_access"));

    tracing_subscriber::registry()
        .with(app_layer)
        .with(http_layer)
        .init();

    (app_guard, http_guard)
}

// ────────────────────────────────────────────────────────────────────────────
// Router
// ────────────────────────────────────────────────────────────────────────────

fn build_router(state: AppState) -> Router {
    // Large-body routes (50 MB limit)
    let message_routes = Router::new()
        .route("/v1/messages", post(handle_messages))
        .route("/v1/messages/count_tokens", post(handle_count_tokens))
        .route("/v1/messages/dry-run", post(handle_dry_run))
        .route("/chat/completions", post(handle_chat_completions))
        .route("/v1/chat/completions", post(handle_v1_chat_completions))
        .route("/api/event_logging/batch", post(handle_event_logging_batch))
        .layer(DefaultBodyLimit::max(50_000_000));

    Router::new()
        .route("/", get(handle_root))
        .route("/health", get(handle_health))
        .route("/dashboard", get(dashboard::handle_dashboard))
        .route("/metrics", get(handle_metrics))
        .route("/errors/summary", get(handle_errors_summary))
        .route("/requests", get(handle_requests))
        .route("/v1/models", get(handle_models))
        .route("/memory", get(memory::handler_memory_list))
        .route("/memory/:key", put(memory::handler_memory_put))
        .route("/memory/:key", get(memory::handler_memory_get))
        .route("/admin/learn-preview", get(handle_learn_preview))
        .route("/admin/learn-apply", post(handle_learn_apply))
        .merge(message_routes)
        .with_state(state)
        .layer(TraceLayer::new_for_http())
}

// ────────────────────────────────────────────────────────────────────────────
// Simple info/metrics handlers
// ────────────────────────────────────────────────────────────────────────────

async fn handle_root() -> impl IntoResponse {
    Json(json!({
        "service": "claude-proxy-rs",
        "version": env!("CARGO_PKG_VERSION"),
        "status": "ok"
    }))
}

async fn handle_health() -> impl IntoResponse {
    Json(json!({"status": "ok"}))
}

async fn handle_metrics(State(state): State<AppState>) -> impl IntoResponse {
    let mut metrics_json = state.metrics.to_metrics_json();
    let remaining = state.fallback_state.remaining_secs().await;
    let cooling = remaining > 0;
    metrics_json["cooldowns"] = json!({
        "anthropic": { "cooling_down": cooling, "remaining_seconds": remaining },
        "bedrock":   { "cooling_down": false,   "remaining_seconds": 0 }
    });
    Json(metrics_json)
}

async fn handle_errors_summary(State(state): State<AppState>) -> impl IntoResponse {
    let errors = state.metrics.error_tracker.get_summary(100);
    let total = errors.len();
    Json(json!({"errors": errors, "total": total}))
}

async fn handle_models() -> impl IntoResponse {
    Json(json!({
        "object": "list",
        "data": [
            {"id": "claude-sonnet-4-6",            "object": "model", "created": 1715000000, "owned_by": "anthropic"},
            {"id": "claude-opus-4-6",              "object": "model", "created": 1715000000, "owned_by": "anthropic"},
            {"id": "claude-sonnet-4-5-20250929",   "object": "model", "created": 1715000000, "owned_by": "anthropic"},
            {"id": "claude-opus-4-5-20251101",     "object": "model", "created": 1715000000, "owned_by": "anthropic"},
            {"id": "claude-haiku-4-5-20251001",    "object": "model", "created": 1715000000, "owned_by": "anthropic"},
            {"id": "claude-3-7-sonnet-20250219",   "object": "model", "created": 1715000000, "owned_by": "anthropic"},
            {"id": "claude-3-5-haiku-20241022",    "object": "model", "created": 1715000000, "owned_by": "anthropic"},
            {"id": "claude-3-haiku-20240307",      "object": "model", "created": 1715000000, "owned_by": "anthropic"}
        ]
    }))
}

#[derive(Deserialize)]
struct RequestsQuery {
    limit: Option<usize>,
}

async fn handle_requests(
    State(state): State<AppState>,
    Query(q): Query<RequestsQuery>,
) -> impl IntoResponse {
    let limit = q.limit.unwrap_or(100).min(100);
    let ring = state.request_ring.lock().await;
    let requests: Vec<&RequestSummary> = ring.iter().take(limit).collect();
    Json(json!(requests))
}

async fn handle_learn_preview() -> impl IntoResponse {
    Json(json!({"corrections": []}))
}

async fn handle_learn_apply() -> impl IntoResponse {
    Json(json!({"written": 0}))
}

async fn handle_event_logging_batch() -> impl IntoResponse {
    // LiteLLM telemetry stub — accept any body and return success silently.
    Json(json!({"status": "success"}))
}

// ────────────────────────────────────────────────────────────────────────────
// Pipeline helpers
// ────────────────────────────────────────────────────────────────────────────

fn new_request_id() -> String {
    uuid::Uuid::new_v4().to_string()[..8].to_string()
}

fn extract_auth_token(headers: &HeaderMap, config: &Config) -> Option<String> {
    headers
        .get(header::AUTHORIZATION)
        .and_then(|v| v.to_str().ok())
        .and_then(|v| v.strip_prefix("Bearer ").map(str::to_string))
        .or_else(|| config.claude_code_oauth_token.clone())
}

fn clean_forwarded_headers(headers: &HeaderMap) -> HeaderMap {
    let mut out = headers.clone();
    out.remove(header::CONTENT_LENGTH);
    out.remove(header::TRANSFER_ENCODING);
    out
}

/// Run body cleaning → system prompt pipeline → compression.
async fn run_pipeline(mut body: Value, state: &AppState) -> (Value, bool) {
    providers::anthropic::clean_request_body(&mut body);
    body = state.system_prompt.apply(body);
    let compressed = if state.config.stapler_compress {
        let (cb, stats) = state.compression.compress_request(body).await;
        body = cb;
        stats.compressed
    } else {
        false
    };
    (body, compressed)
}

fn provider_error_to_response(e: providers::ProviderError) -> Response {
    use providers::ProviderError::*;
    let (status, msg) = match &e {
        Auth(m) => (StatusCode::UNAUTHORIZED, m.clone()),
        Validation(m, code) => (
            StatusCode::from_u16(*code).unwrap_or(StatusCode::BAD_REQUEST),
            m.clone(),
        ),
        RateLimited | RateLimitedWithRetry { .. } => (
            StatusCode::TOO_MANY_REQUESTS,
            "upstream rate limited".to_string(),
        ),
        Timeout => (StatusCode::GATEWAY_TIMEOUT, "upstream timeout".to_string()),
        ModelUnsupported(m) => (StatusCode::BAD_REQUEST, format!("model unsupported: {}", m)),
        Upstream { status, body } => (
            StatusCode::from_u16(*status).unwrap_or(StatusCode::BAD_GATEWAY),
            body.clone(),
        ),
    };
    (
        status,
        Json(json!({"error": {"type": "proxy_error", "message": msg}})),
    )
        .into_response()
}

async fn push_ring_entry(state: &AppState, summary: RequestSummary) {
    let mut ring = state.request_ring.lock().await;
    if ring.len() >= 100 {
        ring.pop_back();
    }
    ring.push_front(summary);
}

async fn update_ring_summary(
    state: &AppState,
    request_id: &str,
    provider: &str,
    duration_ms: f64,
    status_code: u16,
) {
    let mut ring = state.request_ring.lock().await;
    for entry in ring.iter_mut() {
        if entry.request_id == request_id {
            entry.provider_used = provider.to_string();
            entry.duration_ms = (duration_ms * 10.0).round() / 10.0;
            entry.status_code = status_code;
            return;
        }
    }
}

// ────────────────────────────────────────────────────────────────────────────
// handle_messages — non-streaming + streaming
// ────────────────────────────────────────────────────────────────────────────

async fn handle_messages(
    State(state): State<AppState>,
    headers: HeaderMap,
    body_bytes: Bytes,
) -> Response {
    let request_id = new_request_id();
    let start = Instant::now();

    let body: Value = match serde_json::from_slice(&body_bytes) {
        Ok(v) => v,
        Err(e) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(json!({"error": {"type": "invalid_json", "message": e.to_string()}})),
            )
                .into_response();
        }
    };

    let is_stream = body.get("stream").and_then(Value::as_bool).unwrap_or(false);
    let model = body
        .get("model")
        .and_then(Value::as_str)
        .unwrap_or("unknown")
        .to_string();

    let forwarded_headers = {
        let mut h = clean_forwarded_headers(&headers);
        if let Some(token) = extract_auth_token(&headers, &state.config) {
            if let Ok(v) = header::HeaderValue::from_str(&format!("Bearer {}", token)) {
                h.insert(header::AUTHORIZATION, v);
            }
        }
        h
    };

    info!(request_id = %request_id, model = %model, stream = is_stream, "→ handle_messages");

    let (processed_body, _compressed) = run_pipeline(body, &state).await;

    push_ring_entry(
        &state,
        RequestSummary {
            request_id: request_id.clone(),
            timestamp: chrono::Utc::now().to_rfc3339(),
            model: model.clone(),
            provider_used: "pending".to_string(),
            duration_ms: 0.0,
            status_code: 0,
            stream: is_stream,
        },
    )
    .await;

    match state
        .fallback
        .dispatch(processed_body, forwarded_headers, is_stream, &request_id)
        .await
    {
        Ok(ProviderResponse::Full(value)) => {
            let duration_ms = start.elapsed().as_secs_f64() * 1000.0;
            update_ring_summary(&state, &request_id, "anthropic", duration_ms, 200).await;
            let mut resp = Json(value).into_response();
            if let Ok(v) = header::HeaderValue::from_str(&request_id) {
                resp.headers_mut().insert("x-request-id", v);
            }
            resp
        }

        Ok(ProviderResponse::Stream(stream)) => {
            let request_id_clone = request_id.clone();

            let sse_stream = stream.map(move |chunk_result| {
                match chunk_result {
                    Ok(bytes) => {
                        let data = String::from_utf8_lossy(&bytes);
                        // Strip "data: " prefix if present from each SSE line.
                        let json_str = data
                            .lines()
                            .filter_map(|line| {
                                if line.starts_with("data: ") {
                                    Some(line.trim_start_matches("data: ").trim().to_string())
                                } else if !line.is_empty() && !line.starts_with(':') {
                                    Some(line.trim().to_string())
                                } else {
                                    None
                                }
                            })
                            .next()
                            .unwrap_or_else(|| data.trim().to_string());

                        Ok::<Event, std::convert::Infallible>(Event::default().data(json_str))
                    }
                    Err(e) => Ok(Event::default()
                        .event("error")
                        .data(format!(r#"{{"type":"error","message":"{}"}}"#, e))),
                }
            });

            let mut resp = Sse::new(sse_stream)
                .keep_alive(KeepAlive::new().interval(Duration::from_secs(15)))
                .into_response();

            let hdrs = resp.headers_mut();
            hdrs.insert("cache-control", header::HeaderValue::from_static("no-cache"));
            hdrs.insert("x-accel-buffering", header::HeaderValue::from_static("no"));
            if let Ok(v) = header::HeaderValue::from_str(&request_id_clone) {
                hdrs.insert("x-request-id", v);
            }
            resp
        }

        Err(e) => {
            let status_code: u16 = match &e {
                providers::ProviderError::Auth(_) => 401,
                providers::ProviderError::Validation(_, c) => *c,
                providers::ProviderError::RateLimited
                | providers::ProviderError::RateLimitedWithRetry { .. } => 429,
                providers::ProviderError::Timeout => 504,
                providers::ProviderError::Upstream { status, .. } => *status,
                _ => 500,
            };
            update_ring_summary(
                &state,
                &request_id,
                "error",
                start.elapsed().as_secs_f64() * 1000.0,
                status_code,
            )
            .await;
            provider_error_to_response(e)
        }
    }
}

// ────────────────────────────────────────────────────────────────────────────
// OpenAI compatibility endpoints
// ────────────────────────────────────────────────────────────────────────────

async fn handle_chat_completions(
    State(state): State<AppState>,
    headers: HeaderMap,
    body_bytes: Bytes,
) -> Response {
    handle_openai_compat(state, headers, body_bytes).await
}

async fn handle_v1_chat_completions(
    State(state): State<AppState>,
    headers: HeaderMap,
    body_bytes: Bytes,
) -> Response {
    handle_openai_compat(state, headers, body_bytes).await
}

async fn handle_openai_compat(state: AppState, headers: HeaderMap, body_bytes: Bytes) -> Response {
    let openai_body: Value = match serde_json::from_slice(&body_bytes) {
        Ok(v) => v,
        Err(e) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(json!({"error": {"type": "invalid_json", "message": e.to_string()}})),
            )
                .into_response();
        }
    };

    let is_stream = openai_body
        .get("stream")
        .and_then(Value::as_bool)
        .unwrap_or(false);

    let anthropic_body = providers::translate_openai_to_anthropic(openai_body);

    let translated_bytes: Bytes = match serde_json::to_vec(&anthropic_body) {
        Ok(b) => b.into(),
        Err(e) => {
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({"error": {"type": "serialization_error", "message": e.to_string()}})),
            )
                .into_response();
        }
    };

    let resp = handle_messages(State(state), headers, translated_bytes).await;

    // For non-streaming, translate the Anthropic response back to OpenAI format.
    if !is_stream {
        let (parts, body_body) = resp.into_parts();
        let resp_bytes = match axum::body::to_bytes(body_body, usize::MAX).await {
            Ok(b) => b,
            Err(_) => return StatusCode::INTERNAL_SERVER_ERROR.into_response(),
        };
        if parts.status.is_success() {
            if let Ok(anthropic_resp) = serde_json::from_slice::<Value>(&resp_bytes) {
                let openai_resp = providers::translate_anthropic_to_openai(anthropic_resp);
                return (parts.status, Json(openai_resp)).into_response();
            }
        }
        Response::from_parts(parts, axum::body::Body::from(resp_bytes))
    } else {
        resp
    }
}

// ────────────────────────────────────────────────────────────────────────────
// count_tokens
// ────────────────────────────────────────────────────────────────────────────

async fn handle_count_tokens(
    State(state): State<AppState>,
    headers: HeaderMap,
    body_bytes: Bytes,
) -> Response {
    let body: Value = match serde_json::from_slice(&body_bytes) {
        Ok(v) => v,
        Err(e) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(json!({"error": {"type": "invalid_json", "message": e.to_string()}})),
            )
                .into_response();
        }
    };

    let forwarded_headers = {
        let mut h = clean_forwarded_headers(&headers);
        if let Some(token) = extract_auth_token(&headers, &state.config) {
            if let Ok(v) = header::HeaderValue::from_str(&format!("Bearer {}", token)) {
                h.insert(header::AUTHORIZATION, v);
            }
        }
        h
    };

    match state
        .fallback
        .dispatch(body, forwarded_headers, false, &new_request_id())
        .await
    {
        Ok(ProviderResponse::Full(value)) => {
            state
                .metrics
                .counters
                .count_tokens_total
                .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            Json(value).into_response()
        }
        Err(providers::ProviderError::Auth(msg)) => {
            // Known Claude Code bug — handle 401 at INFO (not ERROR) level.
            info!("count_tokens 401 (known Claude Code bug): {}", msg);
            state
                .metrics
                .counters
                .count_tokens_failures
                .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            (
                StatusCode::UNAUTHORIZED,
                Json(json!({"error": {"type": "auth_error", "message": msg}})),
            )
                .into_response()
        }
        Err(e) => {
            state
                .metrics
                .counters
                .count_tokens_failures
                .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            warn!("count_tokens error: {}", e);
            provider_error_to_response(e)
        }
        Ok(ProviderResponse::Stream(_)) => StatusCode::INTERNAL_SERVER_ERROR.into_response(),
    }
}

// ────────────────────────────────────────────────────────────────────────────
// dry-run
// ────────────────────────────────────────────────────────────────────────────

async fn handle_dry_run(
    State(state): State<AppState>,
    _headers: HeaderMap,
    body_bytes: Bytes,
) -> Response {
    let body: Value = match serde_json::from_slice(&body_bytes) {
        Ok(v) => v,
        Err(e) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(json!({"error": {"type": "invalid_json", "message": e.to_string()}})),
            )
                .into_response();
        }
    };

    let bytes_before = body_bytes.len();

    let mut cleaned = body.clone();
    providers::anthropic::clean_request_body(&mut cleaned);

    let (compressed_body, stats) = state.compression.compress_request(cleaned).await;

    let bytes_after = serde_json::to_string(&compressed_body)
        .unwrap_or_default()
        .len();

    Json(json!({
        "request_id": new_request_id(),
        "bytes_before": bytes_before,
        "bytes_after": bytes_after,
        "compressed": stats.compressed,
        "compression_ratio": if bytes_before > 0 {
            (bytes_before as f64 - bytes_after as f64) / bytes_before as f64
        } else {
            0.0
        },
        "body": compressed_body
    }))
    .into_response()
}
