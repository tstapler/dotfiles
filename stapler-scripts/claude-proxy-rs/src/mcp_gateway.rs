//! MCP gateway: mounts `/mcp/{server_name}` on the main axum server.
//!
//! Each server defined in mcp-proxy.toml gets a StreamableHttpService
//! that Claude Code can point to with `"type": "streamable-http"` in .mcp.json.
//!
//! Config path: $MCP_PROXY_CONFIG env var, or ~/.config/mcp-proxy/mcp-proxy.toml.
//! Missing config is not an error — routes are simply omitted.
//!
//! Security: OAuth tokens / API keys are never logged.

use std::collections::{HashMap, HashSet};
use std::path::PathBuf;
use std::sync::Arc;
use std::time::{Duration, Instant};

use anyhow::Context;
use axum::Router;
use rmcp::model::{
    CallToolRequestParams, CallToolResult, ContentBlock, ErrorData, Implementation,
    ListToolsResult, PaginatedRequestParams, ServerCapabilities, ServerInfo, Tool,
};
use rmcp::service::{RequestContext, RoleServer, RunningService};
use rmcp::transport::streamable_http_client::{
    StreamableHttpClientTransport, StreamableHttpClientTransportConfig,
};
use rmcp::transport::streamable_http_server::{
    session::local::LocalSessionManager, StreamableHttpServerConfig, StreamableHttpService,
};
use rmcp::{serve_client, Peer, RoleClient, ServerHandler};
use serde::Deserialize;
use tokio::sync::RwLock;
use tracing::{info, warn};

// ─── Config (minimal subset; mirrors mcp-proxy.toml schema) ──────────────────

#[derive(Debug, Deserialize)]
struct GatewayConfig {
    #[serde(default)]
    global: GatewayGlobal,
    #[serde(default)]
    servers: HashMap<String, GatewayServer>,
}

#[derive(Debug, Deserialize)]
struct GatewayGlobal {
    #[serde(default = "bool_true")]
    enabled: bool,
    #[serde(default)]
    dry_run: bool,
    #[serde(default = "default_ttl")]
    cache_ttl_secs: u64,
}

impl Default for GatewayGlobal {
    fn default() -> Self {
        Self { enabled: true, dry_run: false, cache_ttl_secs: default_ttl() }
    }
}

#[derive(Debug, Clone, Deserialize)]
struct GatewayServer {
    #[serde(default)]
    allow: Vec<String>,
    upstream_url: Option<String>,
    api_key: Option<String>,
    api_key_env: Option<String>,
    #[serde(default = "default_timeout_ms")]
    upstream_timeout_ms: u64,
}

fn bool_true() -> bool { true }
fn default_ttl() -> u64 { 300 }
fn default_timeout_ms() -> u64 { 5000 }

fn resolve_api_key(cfg: &GatewayServer) -> Option<String> {
    if let Some(var) = &cfg.api_key_env {
        if let Ok(val) = std::env::var(var) {
            if !val.is_empty() {
                return Some(val);
            }
        }
    }
    cfg.api_key.clone()
}

fn default_config_path() -> PathBuf {
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    PathBuf::from(home).join(".config").join("mcp-proxy").join("mcp-proxy.toml")
}

// ─── Tool schema cache ────────────────────────────────────────────────────────

#[derive(Clone)]
struct ToolCache {
    inner: Arc<RwLock<Option<(Vec<Tool>, Instant)>>>,
    ttl: Duration,
}

impl ToolCache {
    fn new(ttl_secs: u64) -> Self {
        Self { inner: Arc::new(RwLock::new(None)), ttl: Duration::from_secs(ttl_secs) }
    }

    async fn get(&self) -> Option<Vec<Tool>> {
        let g = self.inner.read().await;
        g.as_ref().and_then(|(tools, ts)| {
            if ts.elapsed() < self.ttl { Some(tools.clone()) } else { None }
        })
    }

    async fn set(&self, tools: Vec<Tool>) {
        *self.inner.write().await = Some((tools, Instant::now()));
    }
}

// ─── Upstream connection ──────────────────────────────────────────────────────

struct UpstreamConn {
    peer: Peer<RoleClient>,
    _service: RunningService<RoleClient, ()>,
    timeout: Duration,
}

impl UpstreamConn {
    async fn connect(url: &str, api_key: Option<&str>, timeout_ms: u64) -> anyhow::Result<Self> {
        let mut cfg = StreamableHttpClientTransportConfig::with_uri(url);
        if let Some(key) = api_key {
            cfg = cfg.auth_header(key);
        }
        let transport = StreamableHttpClientTransport::from_config(cfg);
        let service: RunningService<RoleClient, ()> = serve_client((), transport)
            .await
            .with_context(|| format!("connecting to upstream {url}"))?;
        let peer = service.peer().clone();
        Ok(Self { peer, _service: service, timeout: Duration::from_millis(timeout_ms) })
    }

    async fn list_tools(&self) -> anyhow::Result<Vec<Tool>> {
        let peer = self.peer.clone();
        tokio::time::timeout(self.timeout, peer.list_all_tools())
            .await
            .context("list_tools timed out")?
            .context("list_tools failed")
    }

    async fn call_tool(&self, params: CallToolRequestParams) -> anyhow::Result<CallToolResult> {
        let name = params.name.clone();
        let peer = self.peer.clone();
        tokio::time::timeout(self.timeout, peer.call_tool(params))
            .await
            .with_context(|| format!("call_tool '{name}' timed out"))?
            .with_context(|| format!("call_tool '{name}' failed"))
    }
}

// ─── Per-server MCP handler ───────────────────────────────────────────────────

#[derive(Clone)]
struct GatewayHandler {
    server_name: String,
    upstream: Arc<UpstreamConn>,
    allow: Arc<HashSet<String>>,
    cache: ToolCache,
    dry_run: bool,
}

impl ServerHandler for GatewayHandler {
    fn get_info(&self) -> ServerInfo {
        ServerInfo::new(ServerCapabilities::builder().enable_tools().build())
            .with_server_info(Implementation::new(
                "mcp-context-filter",
                env!("CARGO_PKG_VERSION"),
            ))
    }

    async fn list_tools(
        &self,
        _req: Option<PaginatedRequestParams>,
        _ctx: RequestContext<RoleServer>,
    ) -> Result<ListToolsResult, ErrorData> {
        if let Some(cached) = self.cache.get().await {
            return Ok(ListToolsResult { tools: cached, ..Default::default() });
        }
        let raw = self.upstream.list_tools().await.map_err(|e| {
            warn!(server = %self.server_name, error = %e, "upstream list_tools failed");
            ErrorData::internal_error(format!("upstream error: {e}"), None)
        })?;
        let filtered = if self.dry_run || self.allow.is_empty() {
            raw
        } else {
            raw.into_iter()
                .filter(|t| self.allow.contains(t.name.as_ref()))
                .collect()
        };
        info!(server = %self.server_name, tools = filtered.len(), "tools/list");
        self.cache.set(filtered.clone()).await;
        Ok(ListToolsResult { tools: filtered, ..Default::default() })
    }

    async fn call_tool(
        &self,
        request: CallToolRequestParams,
        _ctx: RequestContext<RoleServer>,
    ) -> Result<CallToolResult, ErrorData> {
        let name = request.name.to_string();
        if !self.dry_run && !self.allow.is_empty() && !self.allow.contains(&name) {
            warn!(tool = %name, server = %self.server_name, "blocked by allowlist");
            return Err(ErrorData {
                code: rmcp::model::ErrorCode::METHOD_NOT_FOUND,
                message: format!("tool not found: {name} (not in allowlist)").into(),
                data: Some(serde_json::json!({
                    "tool": name,
                    "server": self.server_name,
                    "allowlist_hint": "add to mcp-proxy.toml to enable"
                })),
            });
        }
        match self.upstream.call_tool(request).await {
            Ok(r) => Ok(r),
            Err(e) => {
                warn!(tool = %name, server = %self.server_name, error = %e, "upstream call_tool failed");
                Ok(CallToolResult::error(vec![ContentBlock::text(format!(
                    "Upstream '{}' error: {e}",
                    self.server_name
                ))]))
            }
        }
    }
}

// ─── Public API ───────────────────────────────────────────────────────────────

/// Build an axum `Router` with one `/mcp/{server_name}` route per configured server.
///
/// Returns `None` if the config file is absent or no servers could be connected.
/// Errors are logged as warnings; the main server continues without MCP routes.
pub async fn build_mcp_router() -> Option<Router> {
    let config_path = std::env::var("MCP_PROXY_CONFIG")
        .map(PathBuf::from)
        .unwrap_or_else(|_| default_config_path());

    if !config_path.exists() {
        info!(
            path = %config_path.display(),
            "mcp-proxy.toml not found; MCP gateway routes disabled"
        );
        return None;
    }

    let text = match std::fs::read_to_string(&config_path) {
        Ok(t) => t,
        Err(e) => {
            warn!(path = %config_path.display(), error = %e, "failed to read mcp-proxy.toml");
            return None;
        }
    };

    let config: GatewayConfig = match toml::from_str(&text) {
        Ok(c) => c,
        Err(e) => {
            warn!(path = %config_path.display(), error = %e, "failed to parse mcp-proxy.toml");
            return None;
        }
    };

    if !config.global.enabled {
        info!("mcp-proxy disabled (global.enabled = false); skipping gateway routes");
        return None;
    }

    let mut router = Router::new();
    let mut mounted = 0usize;

    for (server_name, server_cfg) in &config.servers {
        let url = match &server_cfg.upstream_url {
            Some(u) => u.clone(),
            None => {
                warn!(server = %server_name, "skipping: no upstream_url configured");
                continue;
            }
        };

        let api_key = resolve_api_key(server_cfg);
        let upstream =
            match UpstreamConn::connect(&url, api_key.as_deref(), server_cfg.upstream_timeout_ms)
                .await
            {
                Ok(u) => Arc::new(u),
                Err(e) => {
                    warn!(server = %server_name, error = %e, "upstream connect failed; skipping");
                    continue;
                }
            };

        let allow: Arc<HashSet<String>> =
            Arc::new(server_cfg.allow.iter().cloned().collect());
        let cache = ToolCache::new(config.global.cache_ttl_secs);
        let dry_run = config.global.dry_run;
        let handler = GatewayHandler {
            server_name: server_name.clone(),
            upstream,
            allow,
            cache,
            dry_run,
        };

        let session_manager = Arc::new(LocalSessionManager::default());
        let svc = StreamableHttpService::new(
            move || Ok(handler.clone()),
            Arc::clone(&session_manager),
            StreamableHttpServerConfig::default(),
        );

        let path = format!("/mcp/{server_name}");
        router = router.route_service(&path, svc);
        info!(server = %server_name, path = %path, "MCP gateway route mounted");
        mounted += 1;
    }

    if mounted == 0 {
        return None;
    }

    Some(router)
}
