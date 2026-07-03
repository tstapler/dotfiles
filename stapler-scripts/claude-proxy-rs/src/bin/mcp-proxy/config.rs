use std::collections::HashMap;
use std::path::PathBuf;
use anyhow::{anyhow, Context};
use serde::{Deserialize, Serialize};
use tracing::warn;

#[derive(Debug, Deserialize, Serialize)]
pub struct McpProxyConfig {
    #[serde(default)]
    pub global: GlobalConfig,
    #[serde(default)]
    pub servers: HashMap<String, ServerConfig>,
    #[serde(default)]
    pub compression: CompressionConfig,
    #[serde(default)]
    pub phase3: Phase3Config,
    #[serde(default)]
    pub metrics: MetricsConfig,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct GlobalConfig {
    #[serde(default = "default_true")]
    pub enabled: bool,
    #[serde(default)]
    pub dry_run: bool,
    #[serde(default = "default_cache_ttl_secs")]
    pub cache_ttl_secs: u64,
}

impl Default for GlobalConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            dry_run: false,
            cache_ttl_secs: default_cache_ttl_secs(),
        }
    }
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ServerConfig {
    #[serde(default)]
    pub allow: Vec<String>,
    pub upstream_url: Option<String>,
    pub upstream_command: Option<String>,
    pub upstream_args: Option<Vec<String>>,
    #[serde(default)]
    pub transport: UpstreamTransportKind,
    pub api_key: Option<String>,
    pub api_key_env: Option<String>,
    #[serde(default = "default_upstream_timeout_ms")]
    pub upstream_timeout_ms: u64,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            allow: Vec::new(),
            upstream_url: None,
            upstream_command: None,
            upstream_args: None,
            transport: UpstreamTransportKind::default(),
            api_key: None,
            api_key_env: None,
            upstream_timeout_ms: default_upstream_timeout_ms(),
        }
    }
}

#[derive(Debug, Clone, Default, Deserialize, Serialize)]
#[serde(rename_all = "kebab-case")]
pub enum UpstreamTransportKind {
    #[default]
    StreamableHttp,
    Sse,
    Stdio,
}

#[derive(Debug, Default, Deserialize, Serialize)]
pub struct CompressionConfig {
    #[serde(default)]
    pub level: CompressionLevel,
}

#[derive(Debug, Default, Clone, PartialEq, Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum CompressionLevel {
    #[default]
    Off,
    Light,
    Aggressive,
}

#[derive(Debug, Default, Deserialize, Serialize)]
pub struct Phase3Config {
    #[serde(default)]
    pub enabled: bool,
    pub model_path: Option<PathBuf>,
    #[serde(default = "default_slot_k")]
    pub slot_k: usize,
    #[serde(default = "default_slot_ttl_turns")]
    pub slot_ttl_turns: usize,
}

#[derive(Debug, Default, Deserialize, Serialize)]
pub struct MetricsConfig {
    #[serde(default = "default_true")]
    pub enabled: bool,
}

fn default_true() -> bool {
    true
}

fn default_cache_ttl_secs() -> u64 {
    300
}

fn default_upstream_timeout_ms() -> u64 {
    5000
}

fn default_slot_k() -> usize {
    10
}

fn default_slot_ttl_turns() -> usize {
    5
}

impl McpProxyConfig {
    pub fn load(path: &PathBuf) -> anyhow::Result<Self> {
        let text = std::fs::read_to_string(path)
            .with_context(|| format!("reading {}", path.display()))?;
        let config: McpProxyConfig = toml::from_str(&text)
            .with_context(|| format!("parsing {}", path.display()))?;
        Ok(config)
    }

    pub fn validate(&self) -> anyhow::Result<()> {
        let mut errors: Vec<String> = Vec::new();

        for (name, server) in &self.servers {
            if server.upstream_url.is_none() && server.upstream_command.is_none() {
                errors.push(format!(
                    "server '{}' has no upstream_url or upstream_command",
                    name
                ));
            }
        }

        // Warn on duplicate tool names across servers
        let mut tool_to_servers: HashMap<&str, Vec<&str>> = HashMap::new();
        for (server_name, server) in &self.servers {
            for tool in &server.allow {
                tool_to_servers
                    .entry(tool.as_str())
                    .or_default()
                    .push(server_name.as_str());
            }
        }
        for (tool, servers) in &tool_to_servers {
            if servers.len() > 1 {
                warn!(
                    tool = *tool,
                    servers = ?servers,
                    "tool name appears in multiple server allowlists"
                );
            }
        }

        if !errors.is_empty() {
            return Err(anyhow!("Config validation failed:\n{}", errors.join("\n")));
        }
        Ok(())
    }

    pub fn effective_api_key(&self, server: &ServerConfig) -> Option<String> {
        if let Some(env_var) = &server.api_key_env {
            if let Ok(val) = std::env::var(env_var) {
                if !val.is_empty() {
                    return Some(val);
                }
            }
        }
        server.api_key.clone()
    }
}

pub fn default_config_path() -> PathBuf {
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    PathBuf::from(home).join(".config").join("mcp-proxy").join("mcp-proxy.toml")
}

#[cfg(test)]
mod tests {
    use super::*;

    const EXAMPLE_TOML: &str = r#"
[global]
enabled = true
dry_run = false

[servers.slack]
upstream_url = "https://mcp.slack.com/mcp"
transport = "streamable-http"
api_key_env = "SLACK_BOT_TOKEN"
allow = [
    "slack_send_message",
    "slack_read_channel",
    "slack_read_thread",
    "slack_search_public",
    "slack_search_users",
    "slack_search_channels",
    "slack_read_user_profile",
    "slack_send_message_draft",
]

[servers.atlassian]
upstream_url = "https://mcp.atlassian.com/mcp"
transport = "streamable-http"
api_key_env = "ATLASSIAN_API_TOKEN"
allow = [
    "search",
    "getJiraIssue",
    "createJiraIssue",
    "editJiraIssue",
    "addCommentToJiraIssue",
    "getConfluencePage",
    "searchJiraIssuesUsingJql",
    "searchConfluenceUsingCql",
    "transitionJiraIssue",
    "getTransitionsForJiraIssue",
    "getVisibleJiraProjects",
]

[compression]
level = "off"

[metrics]
enabled = true
"#;

    #[test]
    fn parses_example_toml() {
        let config: McpProxyConfig = toml::from_str(EXAMPLE_TOML).unwrap();
        assert!(config.global.enabled);
        let slack = config.servers.get("slack").unwrap();
        assert_eq!(slack.allow.len(), 8);
        assert_eq!(slack.allow[0], "slack_send_message");
        let atlassian = config.servers.get("atlassian").unwrap();
        assert_eq!(atlassian.allow.len(), 11);
        assert_eq!(config.compression.level, CompressionLevel::Off);
        assert!(config.metrics.enabled);
    }

    #[test]
    fn validate_missing_upstream_fails() {
        let mut config: McpProxyConfig = toml::from_str("[global]\nenabled = true").unwrap();
        config.servers.insert("test".into(), ServerConfig {
            allow: vec![],
            upstream_url: None,
            upstream_command: None,
            ..Default::default()
        });
        let err = config.validate().unwrap_err();
        assert!(err.to_string().contains("no upstream_url or upstream_command"));
    }

    #[test]
    fn validate_ok_with_upstream_url() {
        let config: McpProxyConfig = toml::from_str(EXAMPLE_TOML).unwrap();
        config.validate().unwrap();
    }
}
