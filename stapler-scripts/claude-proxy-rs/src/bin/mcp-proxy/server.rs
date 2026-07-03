use std::sync::Arc;
use rmcp::model::{
    CallToolRequestParams, CallToolResult, Implementation, ListToolsResult,
    PaginatedRequestParams, ServerCapabilities, ServerInfo,
};
use rmcp::{ErrorData, ServerHandler, service::RequestContext, service::RoleServer};
use tracing::{debug, info, warn};

use crate::allowlist::AllowList;
use crate::cache::SchemaCache;
use crate::config::McpProxyConfig;
use crate::upstream::UpstreamClient;

pub struct ProxyServer {
    server_name: String,
    upstream: Arc<UpstreamClient>,
    allowlist: AllowList,
    cache: SchemaCache,
    dry_run: bool,
}

impl ProxyServer {
    pub fn new(
        server_name: String,
        upstream: UpstreamClient,
        config: &McpProxyConfig,
    ) -> Self {
        let server_cfg = config.servers.get(&server_name).cloned().unwrap_or_default();
        let cache_ttl = config.global.cache_ttl_secs;
        let dry_run = config.global.dry_run;

        let allowlist = AllowList::new(&server_name, server_cfg.allow.iter().cloned());
        let cache = SchemaCache::new(cache_ttl);

        Self {
            server_name,
            upstream: Arc::new(upstream),
            allowlist,
            cache,
            dry_run,
        }
    }
}

impl ServerHandler for ProxyServer {
    fn get_info(&self) -> ServerInfo {
        ServerInfo::new(ServerCapabilities::builder().enable_tools().build())
            .with_server_info(Implementation::new("mcp-context-filter", env!("CARGO_PKG_VERSION")))
    }

    async fn list_tools(
        &self,
        _request: Option<PaginatedRequestParams>,
        _context: RequestContext<RoleServer>,
    ) -> Result<ListToolsResult, ErrorData> {
        if let Some(cached) = self.cache.get().await {
            debug!(
                server = %self.server_name,
                tools = cached.len(),
                "serving tools/list from cache"
            );
            return Ok(ListToolsResult { tools: cached, ..Default::default() });
        }

        let raw_tools = self.upstream.list_tools().await.map_err(|e| {
            warn!(
                server = %self.server_name,
                error = %e,
                hint = format!("check upstream connectivity for '{}'", self.server_name),
                "upstream unreachable during tools/list"
            );
            ErrorData::internal_error(
                format!("upstream server unreachable: {} ({})", self.server_name, e),
                None,
            )
        })?;

        self.allowlist.detect_drift(&raw_tools);

        let filtered = self.allowlist.filter_catalog(raw_tools, self.dry_run);
        let total_available = filtered.len();

        let tokens_before = estimate_token_count(&filtered) + estimate_filtered_overhead();
        let tokens_after = estimate_token_count(&filtered);

        info!(
            server = %self.server_name,
            tools_returned = filtered.len(),
            tokens_before = tokens_before,
            tokens_after = tokens_after,
            pct_saved = ((tokens_before.saturating_sub(tokens_after)) * 100)
                .checked_div(tokens_before.max(1))
                .unwrap_or(0),
            "session_start tools/list"
        );

        self.cache.set(filtered.clone()).await;

        Ok(ListToolsResult { tools: filtered, ..Default::default() })
    }

    async fn call_tool(
        &self,
        request: CallToolRequestParams,
        _context: RequestContext<RoleServer>,
    ) -> Result<CallToolResult, ErrorData> {
        let tool_name = request.name.to_string();

        if let Err(not_allowed) = self.allowlist.check_call(&tool_name) {
            warn!(
                tool = %tool_name,
                server = %self.server_name,
                hint = "add to [servers.{}].allow in mcp-proxy.toml",
                "tool_not_in_allowlist"
            );
            return Err(not_allowed.into_mcp_error());
        }

        match self.upstream.call_tool(request).await {
            Ok(result) => Ok(result),
            Err(e) => {
                warn!(
                    tool = %tool_name,
                    server = %self.server_name,
                    error = %e,
                    "upstream call_tool failed"
                );
                Ok(crate::upstream::upstream_transport_error(&self.server_name, &e))
            }
        }
    }
}

fn estimate_token_count(tools: &[rmcp::model::Tool]) -> usize {
    let json = serde_json::to_string(tools).unwrap_or_default();
    json.len() / 4
}

fn estimate_filtered_overhead() -> usize {
    0
}
