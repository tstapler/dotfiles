/// Integration tests for mcp-proxy stdio handshake and allowlist filtering.
///
/// Story 1.3.1 AC1 — initialize handshake returns proxy server info
/// Story 1.5.1 AC1 — allowlist filtering returns exactly the allowed tools
/// Story 1.6.2 AC1 — blocked tool returns error code -32601 with allowlist_hint
use std::io::Write as _;
use std::process::Stdio;
use std::sync::Arc;
use std::time::Duration;

use rmcp::model::{
    ErrorData, Implementation, ListToolsResult, PaginatedRequestParams, ServerCapabilities,
    ServerInfo, Tool,
};
use rmcp::service::{RequestContext, RoleServer};
use rmcp::transport::streamable_http_server::{
    StreamableHttpServerConfig, StreamableHttpService,
    session::local::LocalSessionManager,
};
use rmcp::ServerHandler;
use serde_json::Value;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader, Lines};
use tokio::net::TcpListener;
use tokio::process::{Child, Command, ChildStdin};

// ---------------------------------------------------------------------------
// Configurable fake upstream
// ---------------------------------------------------------------------------

#[derive(Clone)]
struct FakeUpstream {
    tools: Arc<Vec<Tool>>,
}

impl FakeUpstream {
    fn with_tools(names: &[&str]) -> Self {
        let tools = names
            .iter()
            .map(|n| {
                let mut t = Tool::default();
                t.name = n.to_string().into();
                t
            })
            .collect();
        Self { tools: Arc::new(tools) }
    }

    fn empty() -> Self {
        Self::with_tools(&[])
    }
}

impl ServerHandler for FakeUpstream {
    fn get_info(&self) -> ServerInfo {
        ServerInfo::new(ServerCapabilities::builder().enable_tools().build())
            .with_server_info(Implementation::new("fake-upstream", "0.0.1"))
    }

    async fn list_tools(
        &self,
        _req: Option<PaginatedRequestParams>,
        _ctx: RequestContext<RoleServer>,
    ) -> Result<ListToolsResult, ErrorData> {
        let mut result = ListToolsResult::default();
        result.tools = (*self.tools).clone();
        Ok(result)
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async fn start_fake_upstream(upstream: FakeUpstream) -> u16 {
    let session_manager = Arc::new(LocalSessionManager::default());
    let svc = StreamableHttpService::new(
        move || Ok(upstream.clone()),
        session_manager,
        StreamableHttpServerConfig::default(),
    );

    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let port = listener.local_addr().unwrap().port();
    let app = axum::Router::new().route_service("/mcp", svc);

    tokio::spawn(async move {
        axum::serve(listener, app).await.unwrap();
    });

    tokio::time::sleep(Duration::from_millis(50)).await;
    port
}

fn write_config(port: u16, allow: &[&str]) -> tempfile::NamedTempFile {
    let allow_toml = allow
        .iter()
        .map(|t| format!("  \"{t}\""))
        .collect::<Vec<_>>()
        .join(",\n");
    let allow_arr = if allow.is_empty() {
        "[]".to_string()
    } else {
        format!("[\n{allow_toml},\n]")
    };

    let mut f = tempfile::NamedTempFile::new().unwrap();
    write!(
        f,
        r#"[global]
enabled = true
dry_run = false
cache_ttl_secs = 300

[servers.test-fake]
upstream_url = "http://127.0.0.1:{port}/mcp"
transport = "streamable-http"
allow = {allow_arr}
"#
    )
    .unwrap();
    f
}

/// Spawn mcp-proxy and perform the initialize/initialized handshake.
/// Returns (child, stdin, stdout_lines) ready for further requests.
async fn spawn_and_handshake(
    config_path: &str,
) -> (Child, ChildStdin, Lines<BufReader<tokio::process::ChildStdout>>) {
    let binary = env!("CARGO_BIN_EXE_mcp-proxy");
    let mut child = Command::new(binary)
        .args(["--config", config_path, "serve", "--server", "test-fake"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .expect("failed to spawn mcp-proxy");

    let mut stdin = child.stdin.take().unwrap();
    let stdout = child.stdout.take().unwrap();
    let mut lines = BufReader::new(stdout).lines();

    // initialize
    send_msg(
        &mut stdin,
        serde_json::json!({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "0.0.1"}
            }
        }),
    )
    .await;

    // consume initialize response
    tokio::time::timeout(Duration::from_secs(10), lines.next_line())
        .await
        .expect("timed out waiting for initialize response")
        .expect("io error")
        .expect("stdout closed during initialize");

    // initialized notification
    send_msg(
        &mut stdin,
        serde_json::json!({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }),
    )
    .await;

    (child, stdin, lines)
}

async fn send_msg(stdin: &mut ChildStdin, msg: Value) {
    let mut s = serde_json::to_string(&msg).unwrap();
    s.push('\n');
    stdin.write_all(s.as_bytes()).await.unwrap();
    stdin.flush().await.unwrap();
}

async fn read_response(lines: &mut Lines<BufReader<tokio::process::ChildStdout>>) -> Value {
    let line = tokio::time::timeout(Duration::from_secs(10), lines.next_line())
        .await
        .expect("timed out waiting for response")
        .expect("io error reading stdout")
        .expect("stdout closed unexpectedly");
    serde_json::from_str(&line).expect("response is not valid JSON")
}

// ---------------------------------------------------------------------------
// Story 1.3.1 AC1: initialize handshake returns proxy server info
// ---------------------------------------------------------------------------

#[tokio::test]
async fn initialize_handshake_returns_proxy_server_info() {
    let port = start_fake_upstream(FakeUpstream::empty()).await;
    let config = write_config(port, &[]);

    let binary = env!("CARGO_BIN_EXE_mcp-proxy");
    let mut child = Command::new(binary)
        .args(["--config", config.path().to_str().unwrap(), "serve", "--server", "test-fake"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .unwrap();

    let mut stdin = child.stdin.take().unwrap();
    let stdout = child.stdout.take().unwrap();
    let mut lines = BufReader::new(stdout).lines();

    send_msg(
        &mut stdin,
        serde_json::json!({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "0.0.1"}
            }
        }),
    )
    .await;

    let resp = read_response(&mut lines).await;

    assert_eq!(resp["jsonrpc"], "2.0");
    assert_eq!(resp["id"], 1);
    assert!(resp["error"].is_null(), "unexpected error: {}", resp["error"]);
    assert_eq!(
        resp["result"]["serverInfo"]["name"], "mcp-context-filter",
        "proxy must advertise its own identity"
    );
    assert!(
        resp["result"]["capabilities"]["tools"].is_object(),
        "tools capability must be advertised"
    );

    child.kill().await.ok();
}

// ---------------------------------------------------------------------------
// Story 1.5.1 AC1: allowlist filtering returns exactly the allowed tools
// ---------------------------------------------------------------------------

#[tokio::test]
async fn allowlist_filtering_returns_only_allowed_tools() {
    // Upstream has 4 tools; allowlist permits exactly 2
    let port = start_fake_upstream(FakeUpstream::with_tools(&[
        "slack_send_message",
        "slack_read_channel",
        "slack_create_canvas",
        "slack_update_canvas",
    ]))
    .await;
    let config = write_config(port, &["slack_send_message", "slack_read_channel"]);

    let (mut child, mut stdin, mut lines) =
        spawn_and_handshake(config.path().to_str().unwrap()).await;

    send_msg(
        &mut stdin,
        serde_json::json!({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
    )
    .await;

    let resp = read_response(&mut lines).await;

    assert!(resp["error"].is_null(), "unexpected error: {}", resp["error"]);
    let tools = resp["result"]["tools"].as_array().expect("tools must be array");
    let names: Vec<&str> = tools.iter().map(|t| t["name"].as_str().unwrap()).collect();

    assert_eq!(names.len(), 2, "expected exactly 2 tools, got: {names:?}");
    assert!(names.contains(&"slack_send_message"), "missing slack_send_message");
    assert!(names.contains(&"slack_read_channel"), "missing slack_read_channel");
    assert!(!names.contains(&"slack_create_canvas"), "blocked tool leaked through");
    assert!(!names.contains(&"slack_update_canvas"), "blocked tool leaked through");

    child.kill().await.ok();
}

// ---------------------------------------------------------------------------
// Story 1.6.2 AC1: blocked tool call returns -32601 with allowlist_hint
// ---------------------------------------------------------------------------

#[tokio::test]
async fn blocked_tool_call_returns_method_not_found() {
    let port = start_fake_upstream(FakeUpstream::with_tools(&[
        "slack_send_message",
        "slack_create_canvas",
    ]))
    .await;
    // Only slack_send_message is allowed; slack_create_canvas is blocked
    let config = write_config(port, &["slack_send_message"]);

    let (mut child, mut stdin, mut lines) =
        spawn_and_handshake(config.path().to_str().unwrap()).await;

    send_msg(
        &mut stdin,
        serde_json::json!({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "slack_create_canvas", "arguments": {}}
        }),
    )
    .await;

    let resp = read_response(&mut lines).await;

    let error = &resp["error"];
    assert!(!error.is_null(), "expected error for blocked tool, got result: {}", resp["result"]);

    let code = error["code"].as_i64().expect("error.code must be integer");
    assert_eq!(code, -32601, "blocked tool must return METHOD_NOT_FOUND (-32601), got {code}");

    let data = &error["data"];
    assert!(
        !data.is_null(),
        "error.data must be present with allowlist_hint"
    );
    assert_eq!(
        data["tool"], "slack_create_canvas",
        "error.data.tool must identify the blocked tool"
    );
    assert!(
        data["allowlist_hint"].as_str().is_some(),
        "error.data.allowlist_hint must be a string"
    );

    child.kill().await.ok();
}
