use std::collections::HashSet;
use rmcp::model::Tool;
use tracing::warn;

#[derive(Debug, Clone)]
pub struct AllowList {
    tools: HashSet<String>,
    server_name: String,
}

impl AllowList {
    pub fn new(server_name: impl Into<String>, tools: impl IntoIterator<Item = impl Into<String>>) -> Self {
        Self {
            server_name: server_name.into(),
            tools: tools.into_iter().map(Into::into).collect(),
        }
    }

    pub fn is_empty(&self) -> bool {
        self.tools.is_empty()
    }

    pub fn contains(&self, tool_name: &str) -> bool {
        self.tools.contains(tool_name)
    }

    pub fn check_call(&self, tool_name: &str) -> Result<(), ToolNotAllowedError> {
        if self.tools.contains(tool_name) {
            return Ok(());
        }
        Err(ToolNotAllowedError {
            tool: tool_name.to_string(),
            server: self.server_name.clone(),
        })
    }

    pub fn filter_catalog(&self, tools: Vec<Tool>, dry_run: bool) -> Vec<Tool> {
        if dry_run || self.tools.is_empty() {
            if dry_run {
                tracing::info!(server = %self.server_name, "dry-run mode — no filtering applied");
            }
            return tools;
        }
        tools.into_iter().filter(|t| self.tools.contains(t.name.as_ref())).collect()
    }

    pub fn detect_drift(&self, upstream_tools: &[Tool]) {
        let upstream_names: HashSet<&str> = upstream_tools.iter().map(|t| t.name.as_ref()).collect();
        for allowed in &self.tools {
            if !upstream_names.contains(allowed.as_str()) {
                warn!(
                    tool = %allowed,
                    server = %self.server_name,
                    hint = "run mcp-proxy sync",
                    "allowed tool missing from upstream catalog"
                );
            }
        }
    }
}

#[derive(Debug, thiserror::Error)]
#[error("tool not found: {tool} (tool exists but is not in allowlist for server {server})")]
pub struct ToolNotAllowedError {
    pub tool: String,
    pub server: String,
}

impl ToolNotAllowedError {
    pub fn into_mcp_error(self) -> rmcp::ErrorData {
        rmcp::ErrorData {
            code: rmcp::model::ErrorCode::METHOD_NOT_FOUND,
            message: format!(
                "tool not found: {} (tool exists but is not in allowlist)",
                self.tool
            ).into(),
            data: Some(serde_json::json!({
                "tool": self.tool,
                "server": self.server,
                "allowlist_hint": "add to mcp-proxy.toml to enable"
            })),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_tool(name: &str) -> Tool {
        let mut t = Tool::default();
        t.name = name.to_string().into();
        t
    }

    #[test]
    fn filter_returns_only_allowed() {
        let allow = AllowList::new("slack", ["slack_send_message", "slack_read_channel"]);
        let tools = vec![
            make_tool("slack_send_message"),
            make_tool("slack_read_channel"),
            make_tool("slack_create_canvas"),
            make_tool("slack_update_canvas"),
        ];
        let filtered = allow.filter_catalog(tools, false);
        assert_eq!(filtered.len(), 2);
        assert_eq!(filtered[0].name.as_ref(), "slack_send_message");
        assert_eq!(filtered[1].name.as_ref(), "slack_read_channel");
    }

    #[test]
    fn dry_run_passes_all() {
        let allow = AllowList::new("slack", ["slack_send_message"]);
        let tools = vec![make_tool("slack_send_message"), make_tool("slack_create_canvas")];
        let filtered = allow.filter_catalog(tools, true);
        assert_eq!(filtered.len(), 2);
    }

    #[test]
    fn check_call_blocked_returns_err() {
        let allow = AllowList::new("slack", ["slack_send_message"]);
        let err = allow.check_call("slack_create_canvas").unwrap_err();
        assert!(err.to_string().contains("slack_create_canvas"));
        let mcp_err = err.into_mcp_error();
        assert_eq!(mcp_err.code, rmcp::model::ErrorCode::METHOD_NOT_FOUND);
        assert!(mcp_err.data.is_some());
    }

    #[test]
    fn check_call_allowed_ok() {
        let allow = AllowList::new("slack", ["slack_send_message"]);
        assert!(allow.check_call("slack_send_message").is_ok());
    }
}
