mod allowlist;
mod cache;
mod cli;
mod config;
mod metrics;
mod search;
mod server;
mod slots;
mod upstream;

use std::path::PathBuf;
use clap::Parser;
use tracing_subscriber::EnvFilter;

use cli::{Cli, Command};
use config::{McpProxyConfig, default_config_path};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    let config_path = cli.config.clone().unwrap_or_else(default_config_path);

    match &cli.command {
        Command::Serve { server } => {
            init_tracing_stderr();
            let config = McpProxyConfig::load(&config_path)?;
            config.validate()?;
            run_serve(server.clone(), &config_path, config).await?;
        }
        Command::Init { yes } => {
            init_tracing_stdout();
            cli::run_init(&config_path, *yes).await?;
        }
        Command::Analyze { sessions, yes } => {
            init_tracing_stdout();
            let config = McpProxyConfig::load(&config_path)?;
            cli::run_analyze(&config, *sessions, *yes).await?;
        }
        Command::Sync { yes } => {
            init_tracing_stdout();
            let config = McpProxyConfig::load(&config_path)?;
            cli::run_sync(&config_path, &config, *yes).await?;
        }
        Command::Status { format } => {
            init_tracing_stdout();
            let config = McpProxyConfig::load(&config_path)?;
            cli::run_status(&config, format).await?;
        }
    }

    Ok(())
}

async fn run_serve(
    server_name: String,
    config_path: &PathBuf,
    config: McpProxyConfig,
) -> anyhow::Result<()> {
    use rmcp::{ServiceExt, transport::io::stdio};
    use server::ProxyServer;
    use upstream::UpstreamClient;

    let server_cfg = config.servers.get(&server_name).ok_or_else(|| {
        anyhow::anyhow!(
            "server '{}' not found in {} — available: {}",
            server_name,
            config_path.display(),
            config.servers.keys().cloned().collect::<Vec<_>>().join(", ")
        )
    })?;

    if !config.global.enabled {
        tracing::warn!("mcp-proxy is disabled (global.enabled = false); serving empty tool list");
    }

    let api_key = config.effective_api_key(server_cfg);
    let upstream = UpstreamClient::connect(&server_name, server_cfg, api_key.as_deref()).await?;

    let proxy = ProxyServer::new(server_name, upstream, &config);

    let transport = stdio();
    let service = proxy.serve(transport).await?;
    service.waiting().await?;

    Ok(())
}

fn init_tracing_stderr() {
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("mcp_proxy=info,warn"));
    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .with_writer(std::io::stderr)
        .init();
}

fn init_tracing_stdout() {
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("mcp_proxy=info,warn"));
    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .init();
}
