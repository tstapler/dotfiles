use std::path::PathBuf;
use clap::{Parser, Subcommand};

#[derive(Parser, Debug)]
#[command(
    name = "mcp-proxy",
    about = "MCP context filter proxy — reduces token footprint of MCP server schemas",
    version
)]
pub struct Cli {
    /// Path to mcp-proxy.toml config file
    #[arg(long, short = 'c', global = true)]
    pub config: Option<PathBuf>,

    #[command(subcommand)]
    pub command: Command,
}

#[derive(Subcommand, Debug)]
pub enum Command {
    /// Run MCP proxy for a specific server (Claude Code calls this as a stdio subprocess)
    Serve {
        /// Name of the server in mcp-proxy.toml to proxy
        #[arg(long, short = 's')]
        server: String,
    },

    /// Generate starter mcp-proxy.toml by observing current MCP session
    Init {
        /// Skip confirmation prompts
        #[arg(long, short = 'y')]
        yes: bool,
    },

    /// Analyze Claude Code session logs and suggest allowlist updates
    Analyze {
        /// Number of past sessions to scan
        #[arg(long, default_value = "10")]
        sessions: usize,

        /// Skip confirmation prompts
        #[arg(long, short = 'y')]
        yes: bool,
    },

    /// Sync allowlist against current upstream tool catalog and report drift
    Sync {
        /// Apply changes without prompting
        #[arg(long, short = 'y')]
        yes: bool,
    },

    /// Show proxy status: connected servers, active tools, token savings
    Status {
        /// Output format: text or json
        #[arg(long, default_value = "text")]
        format: StatusFormat,
    },
}

#[derive(Debug, Clone, clap::ValueEnum)]
pub enum StatusFormat {
    Text,
    Json,
}

pub async fn run_init(config_path: &std::path::Path, yes: bool) -> anyhow::Result<()> {
    tracing::info!("init: generating starter mcp-proxy.toml");

    if config_path.exists() && !yes {
        let response = prompt_confirm(&format!(
            "{} already exists. Overwrite? [y/N] ",
            config_path.display()
        ))?;
        if !response {
            println!("Aborted.");
            return Ok(());
        }
    }

    let starter = generate_starter_config();
    if let Some(parent) = config_path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    std::fs::write(config_path, starter)?;
    println!("Wrote starter config to {}", config_path.display());
    println!("Edit it to add your server URLs and API keys, then run: mcp-proxy sync");
    Ok(())
}

pub async fn run_analyze(
    config: &crate::config::McpProxyConfig,
    sessions: usize,
    yes: bool,
) -> anyhow::Result<()> {
    println!("Analyzing {} recent sessions for tool usage patterns...", sessions);
    println!("(Session log analysis not yet implemented — coming in Phase 1 Story 1.8.2)");
    Ok(())
}

pub async fn run_sync(
    config_path: &std::path::Path,
    config: &crate::config::McpProxyConfig,
    yes: bool,
) -> anyhow::Result<()> {
    use crate::upstream::UpstreamClient;

    println!("Checking allowlists against upstream catalogs...\n");

    for (server_name, server_cfg) in &config.servers {
        let url = match &server_cfg.upstream_url {
            Some(u) => u.clone(),
            None => {
                println!("  {server_name}: skipped (no upstream_url)");
                continue;
            }
        };

        let api_key = config.effective_api_key(server_cfg);
        let client = match UpstreamClient::connect(server_name, server_cfg, api_key.as_deref()).await {
            Ok(c) => c,
            Err(e) => {
                println!("  {server_name}: UNREACHABLE — {e}");
                continue;
            }
        };

        let upstream_tools = match client.list_tools().await {
            Ok(t) => t,
            Err(e) => {
                println!("  {server_name}: list_tools failed — {e}");
                continue;
            }
        };

        let upstream_names: std::collections::HashSet<&str> = upstream_tools.iter().map(|t| t.name.as_ref()).collect();
        let mut missing: Vec<&str> = server_cfg.allow.iter()
            .filter(|t| !upstream_names.contains(t.as_str()))
            .map(String::as_str)
            .collect();

        if missing.is_empty() {
            println!("  {server_name}: OK — all {} allowed tools present upstream", server_cfg.allow.len());
        } else {
            println!("  {server_name}: DRIFT — {} tools missing from upstream:", missing.len());
            for t in &missing {
                println!("    - {t}");
            }
        }
    }

    Ok(())
}

pub async fn run_status(
    config: &crate::config::McpProxyConfig,
    format: &StatusFormat,
) -> anyhow::Result<()> {
    match format {
        StatusFormat::Text => {
            println!("mcp-proxy status");
            println!("  enabled: {}", config.global.enabled);
            println!("  dry_run: {}", config.global.dry_run);
            println!("  cache_ttl: {}s", config.global.cache_ttl_secs);
            println!("  servers: {}", config.servers.len());
            for (name, srv) in &config.servers {
                let url = srv.upstream_url.as_deref().unwrap_or("<stdio>");
                println!("    {} — {} tools allowed — {}", name, srv.allow.len(), url);
            }
        }
        StatusFormat::Json => {
            let info = serde_json::json!({
                "enabled": config.global.enabled,
                "dry_run": config.global.dry_run,
                "servers": config.servers.keys().collect::<Vec<_>>(),
            });
            println!("{}", serde_json::to_string_pretty(&info)?);
        }
    }
    Ok(())
}

fn prompt_confirm(prompt: &str) -> anyhow::Result<bool> {
    use std::io::{self, Write};
    print!("{}", prompt);
    io::stdout().flush()?;
    let mut input = String::new();
    io::stdin().read_line(&mut input)?;
    Ok(input.trim().eq_ignore_ascii_case("y"))
}

fn generate_starter_config() -> &'static str {
    r#"[global]
enabled = true
dry_run = false
cache_ttl_secs = 300

# Example: Slack
# [servers.slack]
# upstream_url = "https://mcp.slack.com/mcp"
# transport = "streamable-http"
# api_key_env = "SLACK_BOT_TOKEN"   # or api_key = "xoxb-..."
# allow = [
#     "slack_send_message",
#     "slack_read_channel",
#     "slack_search_public",
#     "slack_search_users",
#     "slack_search_channels",
# ]

# Example: Atlassian Rovo
# [servers.atlassian]
# upstream_url = "https://mcp.atlassian.com/mcp"
# transport = "streamable-http"
# api_key_env = "ATLASSIAN_API_TOKEN"
# allow = [
#     "search",
#     "getJiraIssue",
#     "createJiraIssue",
#     "editJiraIssue",
#     "addCommentToJiraIssue",
#     "getConfluencePage",
#     "searchJiraIssuesUsingJql",
# ]

[compression]
level = "off"

[metrics]
enabled = true
"#
}
