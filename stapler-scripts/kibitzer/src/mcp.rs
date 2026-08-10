use std::path::PathBuf;

use anyhow::Result;
use rmcp::handler::server::router::tool::ToolRouter;
use rmcp::handler::server::tool::Parameters;
use rmcp::model::{ServerCapabilities, ServerInfo};
use rmcp::{tool, tool_handler, tool_router, ServerHandler, ServiceExt};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::check::run_checks_for_trigger;
use crate::config::find_config;

#[derive(Debug, Clone)]
pub struct KibitzerServer {
    tool_router: ToolRouter<Self>,
}

#[derive(Serialize, Deserialize, JsonSchema)]
struct RunChecksRequest {
    /// Absolute path to the file to check.
    file_path: String,
    /// Trigger name (e.g. "PostToolUse" or "batch"); checks with no triggers always run.
    #[serde(default = "default_trigger")]
    trigger: String,
}

fn default_trigger() -> String {
    "batch".to_string()
}

#[derive(Serialize, Deserialize, JsonSchema)]
struct ListChecksRequest {
    /// Any path inside the repo whose `.claude/inspect.json` should be listed.
    path: String,
}

#[tool_router(router = tool_router)]
impl KibitzerServer {
    pub fn new() -> Self {
        Self {
            tool_router: Self::tool_router(),
        }
    }

    #[tool(description = "List the checks configured in the nearest .claude/inspect.json above the given path.")]
    async fn list_checks(&self, req: Parameters<ListChecksRequest>) -> String {
        let path = PathBuf::from(&req.0.path);
        match find_config(&path) {
            Ok(Some((config, root))) => {
                let names: Vec<String> = config
                    .checks
                    .iter()
                    .map(|c| format!("{} ({:?}, scope={:?})", c.name, c.severity, c.scope))
                    .collect();
                format!("config root: {}\nchecks:\n{}", root.display(), names.join("\n"))
            }
            Ok(None) => "no .claude/inspect.json found above this path".to_string(),
            Err(e) => format!("error reading config: {e}"),
        }
    }

    #[tool(description = "Run all in-scope checks against a single file for the given trigger and report failures.")]
    async fn run_checks(&self, req: Parameters<RunChecksRequest>) -> String {
        let file_path = PathBuf::from(&req.0.file_path);
        let config = match find_config(&file_path) {
            Ok(Some(c)) => c,
            Ok(None) => return "no .claude/inspect.json found above this file".to_string(),
            Err(e) => return format!("error reading config: {e}"),
        };
        let (config, repo_root) = config;
        match run_checks_for_trigger(&config.checks, &req.0.trigger, &repo_root, &file_path) {
            Ok(results) => {
                let failures: Vec<String> = results
                    .iter()
                    .filter(|r| !r.passed)
                    .map(|r| {
                        format!(
                            "[{:?}] {}: {}",
                            r.severity,
                            r.check_name,
                            r.message.as_deref().unwrap_or(&r.output)
                        )
                    })
                    .collect();
                if failures.is_empty() {
                    "all checks passed".to_string()
                } else {
                    failures.join("\n")
                }
            }
            Err(e) => format!("error running checks: {e}"),
        }
    }
}

#[tool_handler(router = self.tool_router)]
impl ServerHandler for KibitzerServer {
    fn get_info(&self) -> ServerInfo {
        ServerInfo {
            capabilities: ServerCapabilities::builder().enable_tools().build(),
            instructions: Some(
                "kibitzer: cross-language code/doc inspection. Use list_checks to discover \
                 configured checks and run_checks to inspect a single file."
                    .to_string(),
            ),
            ..Default::default()
        }
    }
}

pub async fn run_mcp_server() -> Result<()> {
    let server = KibitzerServer::new().serve(rmcp::transport::stdio()).await?;
    server.waiting().await?;
    Ok(())
}
