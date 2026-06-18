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

use std::net::SocketAddr;
use std::sync::Arc;

use axum::{
    extract::State,
    http::StatusCode,
    response::{IntoResponse, Json},
    routing::{get, post, put},
    Router,
};
use axum::extract::DefaultBodyLimit;
use rolling_file::{BasicRollingFileAppender, RollingConditionBasic};
use serde_json::json;
use tower_http::trace::TraceLayer;
use tracing::info;
use tracing_appender::non_blocking;
use tracing_subscriber::{filter, layer::SubscriberExt, util::SubscriberInitExt, Layer};

use config::Config;
use memory::MemoryAppState;
use metrics::{run_lag_monitor, MetricsCollector};

// ────────────────────────────────────────────────────────────────────────────
// AppState
// ────────────────────────────────────────────────────────────────────────────

/// Shared application state passed to all route handlers.
#[derive(Clone)]
struct AppState {
    metrics: Arc<MetricsCollector>,
    memory: Arc<MemoryAppState>,
}

// Allow axum to extract Arc<MemoryAppState> directly from AppState,
// so memory module handlers keep their original State<Arc<MemoryAppState>> signature.
impl axum::extract::FromRef<AppState> for Arc<MemoryAppState> {
    fn from_ref(state: &AppState) -> Arc<MemoryAppState> {
        Arc::clone(&state.memory)
    }
}

// ────────────────────────────────────────────────────────────────────────────
// Entry point
// ────────────────────────────────────────────────────────────────────────────

fn main() {
    // Build an explicit multi-thread runtime (Story 1.4: do not use #[tokio::main]).
    let rt = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .thread_name("proxy-worker")
        .build()
        .expect("failed to build tokio runtime");

    rt.block_on(async_main());
}

async fn async_main() {
    // ------------------------------------------------------------------
    // 1. Logging (Story 1.3)
    // ------------------------------------------------------------------
    // WorkerGuards MUST live for the entire process lifetime — dropping them
    // flushes and closes the non-blocking writer channel, causing log loss.
    let (_app_guard, _http_guard) = init_logging();

    // ------------------------------------------------------------------
    // 2. Configuration (Story 1.2)
    // ------------------------------------------------------------------
    let config = Config::from_env();
    info!(
        port = config.port,
        compress = config.stapler_compress,
        verbosity = config.verbosity_level,
        "claude-proxy-rs starting"
    );

    // ------------------------------------------------------------------
    // 3. Shared state
    // ------------------------------------------------------------------
    let metrics = MetricsCollector::new();
    tokio::spawn(run_lag_monitor(Arc::clone(&metrics)));

    let state = AppState {
        metrics: Arc::clone(&metrics),
        memory: Arc::new(MemoryAppState::new(config.memory_max_entries)),
    };

    // ------------------------------------------------------------------
    // 4. Router (Story 1.4)
    // ------------------------------------------------------------------
    let app = build_router(state);

    // ------------------------------------------------------------------
    // 5. Bind and serve
    // ------------------------------------------------------------------
    let addr = SocketAddr::from(([127, 0, 0, 1], config.port));
    info!(%addr, "listening");

    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .expect("failed to bind address");

    axum::serve(listener, app)
        .await
        .expect("server error");
}

/// Initialise rotating file loggers and return `WorkerGuard` handles.
///
/// The guards MUST be stored in `main` scope — they must not be dropped
/// before the process exits or log writes will be silently lost.
fn init_logging() -> (non_blocking::WorkerGuard, non_blocking::WorkerGuard) {
    // App log: 10 MB x 10 files
    let app_appender = BasicRollingFileAppender::new(
        "/tmp/claude-proxy-rs.app.log",
        RollingConditionBasic::new().max_size(10 * 1024 * 1024),
        10,
    )
    .expect("failed to create app log appender");
    let (app_writer, app_guard) = non_blocking(app_appender);

    // HTTP log: 10 MB x 5 files
    let http_appender = BasicRollingFileAppender::new(
        "/tmp/claude-proxy-rs.http.log",
        RollingConditionBasic::new().max_size(10 * 1024 * 1024),
        5,
    )
    .expect("failed to create http log appender");
    let (http_writer, http_guard) = non_blocking(http_appender);

    // App layer: everything except "http_access" target.
    let app_layer = tracing_subscriber::fmt::layer()
        .with_writer(app_writer)
        .with_filter(filter::filter_fn(|meta| {
            meta.target() != "http_access"
        }));

    // HTTP layer: only "http_access" target.
    let http_layer = tracing_subscriber::fmt::layer()
        .with_writer(http_writer)
        .with_filter(filter::filter_fn(|meta| {
            meta.target() == "http_access"
        }));

    tracing_subscriber::registry()
        .with(app_layer)
        .with(http_layer)
        .init();

    (app_guard, http_guard)
}

/// Build the axum `Router` with all routes.
///
/// `DefaultBodyLimit::max(50_000_000)` is applied only to the message routes,
/// not globally (Story 1.4).
fn build_router(state: AppState) -> Router {
    // Message routes get a 50 MB body limit.
    let message_routes = Router::new()
        .route("/v1/messages", post(handle_messages))
        .route("/chat/completions", post(handle_chat_completions))
        .route("/v1/chat/completions", post(handle_v1_chat_completions))
        .layer(DefaultBodyLimit::max(50_000_000));

    Router::new()
        // Info / health
        .route("/", get(handle_root))
        .route("/health", get(handle_health))
        // Dashboard and metrics (Epic 10)
        .route("/dashboard", get(dashboard::handle_dashboard))
        .route("/metrics", get(handle_metrics))
        .route("/errors/summary", get(handle_errors_summary))
        // Memory store (Epic 9)
        .route("/memory", get(memory::handler_memory_list))
        .route("/memory/:key", put(memory::handler_memory_put))
        .route("/memory/:key", get(memory::handler_memory_get))
        // Admin / learn (Epic 8)
        .route("/admin/learn-preview", get(handle_learn_preview))
        .route("/admin/learn-apply", post(handle_learn_apply))
        // Message routes (with body limit)
        .merge(message_routes)
        .with_state(state)
        .layer(TraceLayer::new_for_http())
}

// ────────────────────────────────────────────────────────────────────────────
// Route handlers
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
    Json(state.metrics.to_metrics_json())
}

async fn handle_errors_summary(State(state): State<AppState>) -> impl IntoResponse {
    let errors = state.metrics.error_tracker.get_summary(100);
    let total = errors.len();
    Json(json!({"errors": errors, "total": total}))
}

async fn handle_messages() -> impl IntoResponse {
    // TODO: Epic 2 — wire AnthropicProvider + FallbackHandler
    StatusCode::OK
}

async fn handle_chat_completions() -> impl IntoResponse {
    // TODO: Epic 2
    StatusCode::OK
}

async fn handle_v1_chat_completions() -> impl IntoResponse {
    // TODO: Epic 2
    StatusCode::OK
}

async fn handle_learn_preview() -> impl IntoResponse {
    // TODO: Epic 8 — wire learn::learn_preview
    Json(json!({"corrections": []}))
}

async fn handle_learn_apply() -> impl IntoResponse {
    // TODO: Epic 8 — wire learn::learn_apply
    Json(json!({"written": 0}))
}
