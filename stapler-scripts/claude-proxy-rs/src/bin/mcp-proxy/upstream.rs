use std::time::Duration;
use anyhow::Context;
use rmcp::model::{Tool, CallToolRequestParams, CallToolResult, ContentBlock};
use rmcp::serve_client;
use rmcp::service::RunningService;
use rmcp::transport::streamable_http_client::{StreamableHttpClientTransport, StreamableHttpClientTransportConfig};
use rmcp::{Peer, RoleClient};
use tracing::{info, warn};

use crate::config::{ServerConfig, UpstreamTransportKind};

const ATLASSIAN_DOMAINS: &[&str] = &[".atlassian.net", ".atlassian.com", "rovo.atlassian.com"];

fn is_atlassian_url(url: &str) -> bool {
    ATLASSIAN_DOMAINS.iter().any(|d| url.contains(d))
}

pub struct UpstreamClient {
    peer: Peer<RoleClient>,
    _service: RunningService<RoleClient, ()>,
    server_name: String,
    timeout: Duration,
}

impl UpstreamClient {
    pub async fn connect(server_name: &str, config: &ServerConfig, api_key: Option<&str>) -> anyhow::Result<Self> {
        let url = config.upstream_url.as_deref()
            .ok_or_else(|| anyhow::anyhow!("server '{}' has no upstream_url", server_name))?;

        match &config.transport {
            UpstreamTransportKind::Sse if is_atlassian_url(url) => {
                anyhow::bail!(
                    "SSE transport is not supported for Atlassian-hosted servers (deprecated June 30, 2026). \
                     Update mcp-proxy.toml: set transport = 'streamable-http' for server '{}'",
                    server_name
                );
            }
            UpstreamTransportKind::Stdio => {
                anyhow::bail!(
                    "server '{}' uses stdio transport but has upstream_url instead of upstream_command",
                    server_name
                );
            }
            _ => {}
        }

        let transport_config = build_transport_config(url, api_key);
        let transport = StreamableHttpClientTransport::from_config(transport_config);

        let service: RunningService<RoleClient, ()> = serve_client((), transport)
            .await
            .with_context(|| format!("connecting to upstream MCP server '{}'", server_name))?;

        let peer = service.peer().clone();

        Ok(Self {
            peer,
            _service: service,
            server_name: server_name.to_string(),
            timeout: Duration::from_millis(config.upstream_timeout_ms),
        })
    }

    pub async fn list_tools(&self) -> anyhow::Result<Vec<Tool>> {
        let peer = self.peer.clone();
        let result = tokio::time::timeout(self.timeout, peer.list_all_tools())
            .await
            .with_context(|| format!(
                "upstream server '{}' timed out after {}ms",
                self.server_name, self.timeout.as_millis()
            ))?
            .with_context(|| format!("list_tools from upstream server '{}'", self.server_name))?;
        Ok(result)
    }

    pub async fn call_tool(&self, params: CallToolRequestParams) -> anyhow::Result<CallToolResult> {
        let tool_name = params.name.clone();
        let peer = self.peer.clone();
        let result = tokio::time::timeout(self.timeout, peer.call_tool(params))
            .await
            .with_context(|| format!(
                "upstream server '{}' timed out calling tool '{}' after {}ms",
                self.server_name, tool_name, self.timeout.as_millis()
            ))?
            .with_context(|| format!("call_tool '{}' from upstream server '{}'", tool_name, self.server_name))?;
        Ok(result)
    }
}

fn build_transport_config(url: &str, api_key: Option<&str>) -> StreamableHttpClientTransportConfig {
    let mut config = StreamableHttpClientTransportConfig::with_uri(url);
    if let Some(key) = api_key {
        config = config.auth_header(key);
    }
    config
}

pub fn upstream_timeout_error(server_name: &str, timeout_ms: u64) -> rmcp::ErrorData {
    rmcp::ErrorData::internal_error(
        format!(
            "upstream server unreachable: {} (timeout after {}ms)",
            server_name, timeout_ms
        ),
        Some(serde_json::json!({
            "server": server_name,
            "timeout_ms": timeout_ms,
            "hint": format!("check upstream server connectivity for '{}'", server_name)
        })),
    )
}

pub fn upstream_transport_error(server_name: &str, err: &anyhow::Error) -> CallToolResult {
    CallToolResult::error(vec![ContentBlock::text(format!(
        "Upstream server '{}' error: {}",
        server_name, err
    ))])
}
