//! Anthropic API provider.
//!
//! Forwards requests to `https://api.anthropic.com/v1/messages`, cleaning
//! Claude Code / Bedrock-specific fields that the Anthropic API rejects.

use std::time::Duration;

use axum::http::HeaderMap;
use reqwest::{Client, StatusCode};
use serde_json::Value;
use tracing::{debug, info, warn};

use crate::auth;
use crate::config::Config;
use super::ProviderError;

/// Anthropic API provider.
///
/// Holds two separate reqwest clients as specified by ADR-004:
/// - `client`: pooled, for short non-streaming requests
/// - `stream_client`: pool_max_idle_per_host(0), for long-lived SSE streams
pub struct AnthropicProvider {
    /// Pooled client for non-streaming requests.
    client: Client,
    /// Non-pooled client for SSE streaming (prevents pool exhaustion).
    stream_client: Client,
    /// Base URL for the Anthropic API. Default: "https://api.anthropic.com".
    base_url: String,
}

impl AnthropicProvider {
    /// Construct a new `AnthropicProvider` from the proxy configuration.
    pub fn new(config: &Config) -> Result<Self, ProviderError> {
        let timeout = Duration::from_secs(config.request_timeout);

        let client = Client::builder()
            .connect_timeout(Duration::from_secs(10))
            .read_timeout(timeout)
            .build()
            .map_err(|e| ProviderError::Upstream { status: 0, body: e.to_string() })?;

        // ADR-004: separate client with pool_max_idle_per_host(0) for SSE
        let stream_client = Client::builder()
            .connect_timeout(Duration::from_secs(10))
            .pool_max_idle_per_host(0)
            .build()
            .map_err(|e| ProviderError::Upstream { status: 0, body: e.to_string() })?;

        Ok(Self {
            client,
            stream_client,
            base_url: "https://api.anthropic.com".to_string(),
        })
    }

    /// Normalize a model name for the Anthropic API.
    ///
    /// Claude Code occasionally sends Bedrock-format names (e.g.
    /// `us.anthropic.claude-3-5-sonnet-20241022-v1:0`) to the Anthropic
    /// endpoint.  Strip the prefix and version suffix so the API accepts it.
    fn normalize_model_name(model: &str) -> String {
        let model = if let Some(stripped) = model.strip_prefix("us.anthropic.") {
            stripped.to_string()
        } else {
            model.to_string()
        };

        // Remove trailing version suffix: -v1:0 or -v1
        MODEL_VERSION_RE.replace(&model, "").to_string()
    }

    /// Build the outgoing request headers.
    ///
    /// - Always sets `Content-Type: application/json`.
    /// - Forwards `anthropic-version` and `anthropic-beta` from the client if
    ///   present, otherwise falls back to the default version.
    /// - Sets auth: OAuth tokens → `Authorization: Bearer <token>`;
    ///   API keys (`sk-ant-api-*`) → `x-api-key: <token>`.
    fn build_headers(
        &self,
        token: &str,
        incoming: &HeaderMap,
    ) -> reqwest::header::HeaderMap {
        let mut out = reqwest::header::HeaderMap::new();

        // content-type is always application/json
        out.insert(
            reqwest::header::CONTENT_TYPE,
            reqwest::header::HeaderValue::from_static("application/json"),
        );

        // Forward anthropic-version (fall back to stable default)
        let version = incoming
            .get("anthropic-version")
            .and_then(|v| v.to_str().ok())
            .unwrap_or("2023-06-01");
        if let Ok(v) = reqwest::header::HeaderValue::from_str(version) {
            out.insert("anthropic-version", v);
        }

        // Forward anthropic-beta if present
        if let Some(beta) = incoming
            .get("anthropic-beta")
            .and_then(|v| v.to_str().ok())
        {
            if let Ok(v) = reqwest::header::HeaderValue::from_str(beta) {
                out.insert("anthropic-beta", v);
            }
        }

        // Auth: sk-ant-api-* tokens use x-api-key; everything else (OAuth) uses
        // Authorization: Bearer
        if token.starts_with("sk-ant-api-") {
            if let Ok(v) = reqwest::header::HeaderValue::from_str(token) {
                out.insert("x-api-key", v);
            }
        } else {
            let bearer = format!("Bearer {}", token);
            if let Ok(v) = reqwest::header::HeaderValue::from_str(&bearer) {
                out.insert(reqwest::header::AUTHORIZATION, v);
            }
        }

        out
    }

    /// Send a non-streaming request to `POST /v1/messages`.
    ///
    /// Returns the full response body as a `serde_json::Value` plus the HTTP status.
    pub async fn send(
        &self,
        mut body: Value,
        incoming_headers: &HeaderMap,
        config: &Config,
    ) -> Result<(Value, StatusCode), ProviderError> {
        // Normalize model name
        if let Some(model) = body.get("model").and_then(|v| v.as_str()) {
            let normalized = Self::normalize_model_name(model);
            body["model"] = Value::String(normalized);
        }

        // Clean the request body (strips Bedrock-specific / unsupported fields)
        clean_request_body(&mut body);

        let token = auth::extract_token(incoming_headers, config.claude_code_oauth_token.as_deref())
            .map_err(|e| ProviderError::Auth(e.to_string()))?;

        let headers = self.build_headers(&token.token, incoming_headers);
        let body_bytes = serde_json::to_vec(&body)
            .map_err(|e| ProviderError::Upstream { status: 0, body: e.to_string() })?;

        let url = format!("{}/v1/messages", self.base_url);
        debug!("Anthropic non-stream POST {}", url);

        let response = self
            .client
            .post(&url)
            .headers(headers)
            .body(body_bytes)
            .send()
            .await
            .map_err(|e| {
                if e.is_timeout() {
                    ProviderError::Timeout
                } else {
                    ProviderError::Upstream { status: 0, body: e.to_string() }
                }
            })?;

        let status = response.status();
        map_error_status(status, response).await
    }

    /// Send a streaming request to `POST /v1/messages`.
    ///
    /// Returns the raw `reqwest::Response` for the caller to drive as an SSE
    /// byte stream.  The caller is responsible for iterating `bytes_stream()`.
    pub async fn send_streaming(
        &self,
        mut body: Value,
        incoming_headers: &HeaderMap,
        config: &Config,
    ) -> Result<reqwest::Response, ProviderError> {
        // Ensure stream flag is set
        body["stream"] = Value::Bool(true);

        // Normalize model name
        if let Some(model) = body.get("model").and_then(|v| v.as_str()) {
            let normalized = Self::normalize_model_name(model);
            body["model"] = Value::String(normalized);
        }

        // Clean the request body
        clean_request_body(&mut body);

        let token = auth::extract_token(incoming_headers, config.claude_code_oauth_token.as_deref())
            .map_err(|e| ProviderError::Auth(e.to_string()))?;

        let headers = self.build_headers(&token.token, incoming_headers);
        let body_bytes = serde_json::to_vec(&body)
            .map_err(|e| ProviderError::Upstream { status: 0, body: e.to_string() })?;

        let url = format!("{}/v1/messages", self.base_url);
        debug!("Anthropic stream POST {}", url);

        let response = self
            .stream_client
            .post(&url)
            .headers(headers)
            .body(body_bytes)
            .send()
            .await
            .map_err(|e| {
                if e.is_timeout() {
                    ProviderError::Timeout
                } else {
                    ProviderError::Upstream { status: 0, body: e.to_string() }
                }
            })?;

        let status = response.status();

        if status == StatusCode::TOO_MANY_REQUESTS || status.as_u16() == 529 {
            let retry_after = response
                .headers()
                .get("retry-after")
                .and_then(|v| v.to_str().ok())
                .and_then(|v| v.parse::<u64>().ok())
                .unwrap_or(60);
            warn!("Anthropic rate limited ({}), retry-after {}s", status, retry_after);
            return Err(ProviderError::RateLimited);
        }

        if status.is_client_error() {
            let status_u16 = status.as_u16();
            let body_str = response.text().await.unwrap_or_default();
            return Err(ProviderError::Validation(body_str, status_u16));
        }

        if !status.is_success() {
            let status_u16 = status.as_u16();
            let body_str = response.text().await.unwrap_or_default();
            return Err(ProviderError::Upstream { status: status_u16, body: body_str });
        }

        Ok(response)
    }
}

// ---------------------------------------------------------------------------
// Body cleaning (ADR-007 — serde_json::Value throughout, no typed structs)
// ---------------------------------------------------------------------------

/// Lazy-compiled regex for stripping Bedrock model version suffixes.
static MODEL_VERSION_RE: once_cell::sync::Lazy<regex::Regex> =
    once_cell::sync::Lazy::new(|| regex::Regex::new(r"-v\d+(?::\d+)?$").unwrap());

/// Clean a request body in-place, removing fields that the Anthropic API
/// rejects.  Matches the Python `_clean_request_body` implementation.
///
/// Strips:
/// - From each `tools[]` entry: `defer_loading`, `input_examples`, `custom`,
///   `cache_control`
/// - From `messages[*].content[*]` of type `tool_result`: removes any
///   `content[]` items whose `type` is not in the supported set
/// - From `system[]` cache_control objects: removes nested `ephemeral.scope`
/// - Top-level: `output_config`, `context_management`
pub fn clean_request_body(body: &mut Value) {
    // 1. Clean tools[]
    if let Some(tools) = body.get_mut("tools").and_then(|v| v.as_array_mut()) {
        for tool in tools.iter_mut() {
            if let Some(obj) = tool.as_object_mut() {
                for field in &["defer_loading", "input_examples", "custom", "cache_control"] {
                    if obj.remove(*field).is_some() {
                        debug!("Removed '{}' from tool definition", field);
                    }
                }
            }
        }
    }

    // 2. Clean messages[*].content[*] — remove unsupported types from tool_result content
    if let Some(messages) = body.get_mut("messages").and_then(|v| v.as_array_mut()) {
        for message in messages.iter_mut() {
            if let Some(content) = message
                .get_mut("content")
                .and_then(|v| v.as_array_mut())
            {
                for item in content.iter_mut() {
                    if item.get("type").and_then(|v| v.as_str()) == Some("tool_result") {
                        if let Some(inner) =
                            item.get_mut("content").and_then(|v| v.as_array_mut())
                        {
                            let before = inner.len();
                            inner.retain(|c| {
                                c.get("type")
                                    .and_then(|t| t.as_str())
                                    .map(|t| {
                                        matches!(
                                            t,
                                            "text"
                                                | "image"
                                                | "document"
                                                | "search_result"
                                                | "tool_use"
                                                | "tool_result"
                                        )
                                    })
                                    .unwrap_or(true)
                            });
                            let removed = before - inner.len();
                            if removed > 0 {
                                debug!(
                                    "Removed {} unsupported content block(s) from tool_result",
                                    removed
                                );
                            }
                        }
                    }
                }
            }
        }
    }

    // 3. Clean system[*].cache_control.ephemeral.scope
    if let Some(system) = body.get_mut("system").and_then(|v| v.as_array_mut()) {
        for item in system.iter_mut() {
            if let Some(cc) = item
                .get_mut("cache_control")
                .and_then(|v| v.as_object_mut())
            {
                if let Some(ephemeral) = cc.get_mut("ephemeral").and_then(|v| v.as_object_mut()) {
                    if ephemeral.remove("scope").is_some() {
                        debug!("Removed 'scope' from system[].cache_control.ephemeral");
                    }
                }
            }
        }
    }

    // 4. Strip top-level Bedrock-specific fields
    if let Some(obj) = body.as_object_mut() {
        for field in &["output_config", "context_management"] {
            if obj.remove(*field).is_some() {
                info!("Stripped Bedrock-specific top-level field '{}'", field);
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Error mapping helper
// ---------------------------------------------------------------------------

/// Convert a non-success HTTP status into the appropriate `ProviderError`,
/// consuming the response body for error detail.
async fn map_error_status(
    status: StatusCode,
    response: reqwest::Response,
) -> Result<(Value, StatusCode), ProviderError> {
    if status == StatusCode::TOO_MANY_REQUESTS || status.as_u16() == 529 {
        let retry_after = response
            .headers()
            .get("retry-after")
            .and_then(|v| v.to_str().ok())
            .and_then(|v| v.parse::<u64>().ok())
            .unwrap_or(60);
        warn!("Anthropic rate limited ({}), retry-after {}s", status, retry_after);
        return Err(ProviderError::RateLimited);
    }

    if status.is_client_error() {
        let status_u16 = status.as_u16();
        let body_str = response.text().await.unwrap_or_default();
        return Err(ProviderError::Validation(body_str, status_u16));
    }

    if !status.is_success() {
        let status_u16 = status.as_u16();
        let body_str = response.text().await.unwrap_or_default();
        return Err(ProviderError::Upstream { status: status_u16, body: body_str });
    }

    let resp_value: Value = response
        .json()
        .await
        .map_err(|e| ProviderError::Upstream { status: status.as_u16(), body: e.to_string() })?;

    Ok((resp_value, status))
}
