//! AWS Bedrock provider.

use std::collections::HashMap;
use std::os::unix::io::AsRawFd;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::OnceLock;
use std::time::Duration;

use aws_sdk_bedrockruntime::primitives::Blob;
use aws_sdk_bedrockruntime::types::ResponseStream;
use serde_json::Value;
use tokio::sync::Mutex;
use tokio::time::Instant;
use tracing::{debug, warn};

use async_trait::async_trait;
use axum::http::HeaderMap;
use bytes::Bytes;
use futures_util::stream;

use crate::config::Config;
use crate::fallback::Provider;
use crate::providers::{ProviderError, ProviderResponse};

// Use the SDK's own re-exported SdkError alias so we don't need to add
// aws-smithy-runtime-api as a direct dependency.
use aws_sdk_bedrockruntime::error::SdkError;

// ---------------------------------------------------------------------------
// Beta compatibility table (ported from Python providers/bedrock.py)
// ---------------------------------------------------------------------------

fn build_beta_compat() -> HashMap<&'static str, Vec<&'static str>> {
    let mut m = HashMap::new();
    m.insert("computer-use-2025-01-24", vec!["claude-3-7-sonnet"]);
    m.insert(
        "token-efficient-tools-2025-02-19",
        vec!["claude-3-7-sonnet", "claude-sonnet-4", "claude-opus-4", "claude-haiku-4"],
    );
    m.insert(
        "Interleaved-thinking-2025-05-14",
        vec!["claude-sonnet-4", "claude-opus-4", "claude-haiku-4"],
    );
    m.insert("output-128k-2025-02-19", vec!["claude-3-7-sonnet"]);
    m.insert(
        "dev-full-thinking-2025-05-14",
        vec!["claude-sonnet-4", "claude-opus-4", "claude-haiku-4"],
    );
    m.insert("context-1m-2025-08-07", vec!["claude-sonnet-4"]);
    m.insert(
        "context-management-2025-06-27",
        vec!["claude-sonnet-4-5", "claude-haiku-4-5"],
    );
    m.insert("effort-2025-11-24", vec!["claude-opus-4-5"]);
    m.insert("tool-search-tool-2025-10-19", vec!["claude-opus-4-5"]);
    m.insert("tool-examples-2025-10-29", vec!["claude-opus-4-5"]);
    m
}

static BEDROCK_BETA_COMPAT: std::sync::LazyLock<HashMap<&'static str, Vec<&'static str>>> =
    std::sync::LazyLock::new(build_beta_compat);

// ---------------------------------------------------------------------------
// Model mapping (hardcoded fallback, mirrors Python bedrock.py)
// ---------------------------------------------------------------------------

fn build_model_mapping() -> HashMap<&'static str, &'static str> {
    let mut m = HashMap::new();
    m.insert("claude-sonnet-4-6", "us.anthropic.claude-sonnet-4-6");
    m.insert("claude-opus-4-6", "us.anthropic.claude-opus-4-6-v1");
    m.insert("claude-sonnet-4-5-20250929", "us.anthropic.claude-sonnet-4-5-20250929-v1:0");
    m.insert("claude-opus-4-5-20251101", "us.anthropic.claude-opus-4-5-20251101-v1:0");
    m.insert("claude-haiku-4-5-20251001", "us.anthropic.claude-haiku-4-5-20251001-v1:0");
    m.insert("claude-3-7-sonnet-20250219", "us.anthropic.claude-3-7-sonnet-20250219-v1:0");
    m.insert("claude-3-5-haiku-20241022", "us.anthropic.claude-3-5-haiku-20241022-v1:0");
    m.insert("claude-3-haiku-20240307", "us.anthropic.claude-3-haiku-20240307-v1:0");
    m
}

static MODEL_MAPPING: std::sync::LazyLock<HashMap<&'static str, &'static str>> =
    std::sync::LazyLock::new(build_model_mapping);

// ---------------------------------------------------------------------------
// Credential validity cache (30s TTL, single-process)
// ---------------------------------------------------------------------------

struct CredCache {
    valid: AtomicBool,
    refreshed_at: std::sync::Mutex<Option<Instant>>,
}

impl CredCache {
    fn new() -> Self {
        Self {
            valid: AtomicBool::new(false),
            refreshed_at: std::sync::Mutex::new(None),
        }
    }

    fn is_valid(&self) -> bool {
        if !self.valid.load(Ordering::Relaxed) {
            return false;
        }
        self.refreshed_at
            .lock()
            .unwrap()
            .as_ref()
            .map(|t| t.elapsed() < Duration::from_secs(30))
            .unwrap_or(false)
    }

    fn mark_valid(&self) {
        self.valid.store(true, Ordering::Relaxed);
        *self.refreshed_at.lock().unwrap() = Some(Instant::now());
    }
}

// ---------------------------------------------------------------------------
// BedrockProvider
// ---------------------------------------------------------------------------

pub struct BedrockProvider {
    client: aws_sdk_bedrockruntime::Client,
    sso_lock: OnceLock<Mutex<()>>,
    cred_cache: CredCache,
    config: Config,
}

impl BedrockProvider {
    pub async fn new(config: Config) -> Self {
        let aws_cfg = aws_config::load_from_env().await;
        let client = aws_sdk_bedrockruntime::Client::new(&aws_cfg);
        Self {
            client,
            sso_lock: OnceLock::new(),
            cred_cache: CredCache::new(),
            config,
        }
    }

    // -----------------------------------------------------------------------
    // Model name normalization
    // -----------------------------------------------------------------------

    /// Strip cross-region/Anthropic prefixes and version suffixes to get the
    /// canonical `claude-*` form used for beta compatibility lookups.
    pub fn normalize_model(model: &str) -> String {
        let mut m = model.to_string();

        // Strip cross-region inference prefix (us., eu., ap.)
        for prefix in &["us.", "eu.", "ap."] {
            if let Some(rest) = m.strip_prefix(prefix) {
                m = rest.to_string();
                break;
            }
        }

        // Strip anthropic. prefix
        if let Some(rest) = m.strip_prefix("anthropic.") {
            m = rest.to_string();
        }

        // Strip version suffix like -v1:0 or -v2:0
        if let Some(pos) = m.rfind("-v") {
            let suffix = &m[pos + 2..]; // after "-v"
            let parts: Vec<&str> = suffix.splitn(2, ':').collect();
            if parts.len() == 2
                && parts[0].chars().all(|c| c.is_ascii_digit())
                && parts[1].chars().all(|c| c.is_ascii_digit())
            {
                m.truncate(pos);
            }
        }

        // Strip -bedrock suffix
        if let Some(rest) = m.strip_suffix("-bedrock") {
            m = rest.to_string();
        }

        m
    }

    /// Convert any model name format to the Bedrock cross-region modelId.
    pub fn to_bedrock_model_id(model: &str) -> String {
        let normalized = Self::normalize_model(model);
        if let Some(&id) = MODEL_MAPPING.get(normalized.as_str()) {
            return id.to_string();
        }
        warn!("Model {} not in Bedrock mapping, constructing fallback ID", normalized);
        format!("us.anthropic.{}-v1:0", normalized)
    }

    // -----------------------------------------------------------------------
    // Beta feature filtering
    // -----------------------------------------------------------------------

    fn is_beta_compatible(beta: &str, normalized_model: &str) -> bool {
        BEDROCK_BETA_COMPAT
            .get(beta)
            .map(|patterns| patterns.iter().any(|p| normalized_model.starts_with(p)))
            .unwrap_or(false)
    }

    fn filter_betas(beta_header: &str, normalized_model: &str) -> Vec<String> {
        beta_header
            .split(',')
            .map(str::trim)
            .filter_map(|beta| {
                if !BEDROCK_BETA_COMPAT.contains_key(beta) {
                    debug!("Filtering unsupported Bedrock beta: {}", beta);
                    None
                } else if Self::is_beta_compatible(beta, normalized_model) {
                    Some(beta.to_string())
                } else {
                    debug!("Filtering model-incompatible beta {} for {}", beta, normalized_model);
                    None
                }
            })
            .collect()
    }

    // -----------------------------------------------------------------------
    // Thinking budget validation (issue #8756)
    // -----------------------------------------------------------------------

    fn validate_thinking(body: &mut Value) {
        if body.get("thinking").filter(|t| t.is_object()).is_none() {
            return;
        }

        let budget = body["thinking"]["budget_tokens"].as_u64();
        let max = body["max_tokens"].as_u64();

        let (Some(budget), Some(max)) = (budget, max) else { return };

        if budget > max {
            if max < 1024 {
                warn!(
                    "Bedrock: max_tokens={} too small for thinking mode (min 1024), disabling thinking",
                    max
                );
                body.as_object_mut().unwrap().remove("thinking");
            } else {
                warn!(
                    "Bedrock: Capping thinking.budget_tokens from {} to max_tokens {}",
                    budget, max
                );
                body["thinking"]["budget_tokens"] = Value::from(max);
            }
        } else if budget < 1024 {
            warn!(
                "Bedrock: Increasing thinking.budget_tokens from {} to minimum 1024",
                budget
            );
            body["thinking"]["budget_tokens"] = Value::from(1024u64);
        }
    }

    // -----------------------------------------------------------------------
    // Body cleaning
    // -----------------------------------------------------------------------

    fn clean_body(body: &mut Value) {
        // Remove unsupported fields from tool definitions
        if let Some(tools) = body.get_mut("tools").and_then(|t| t.as_array_mut()) {
            for (idx, tool) in tools.iter_mut().enumerate() {
                if let Some(obj) = tool.as_object_mut() {
                    let mut removed = Vec::new();
                    for field in &["defer_loading", "input_examples", "custom", "cache_control"] {
                        if obj.remove(*field).is_some() {
                            removed.push(*field);
                        }
                    }
                    if !removed.is_empty() {
                        debug!("Cleaned tool[{}]: removed {:?}", idx, removed);
                    }
                }
            }
        }

        // Remove tool_reference blocks from inside tool_result content
        if let Some(messages) = body.get_mut("messages").and_then(|m| m.as_array_mut()) {
            for message in messages.iter_mut() {
                if let Some(content) = message.get_mut("content").and_then(|c| c.as_array_mut()) {
                    for block in content.iter_mut() {
                        if block.get("type").and_then(|t| t.as_str()) == Some("tool_result") {
                            if let Some(inner) =
                                block.get_mut("content").and_then(|c| c.as_array_mut())
                            {
                                inner.retain(|item| {
                                    item.get("type").and_then(|t| t.as_str())
                                        != Some("tool_reference")
                                });
                            }
                        }
                    }
                }
            }
        }
    }

    // -----------------------------------------------------------------------
    // Orphaned tool_result cleanup
    // -----------------------------------------------------------------------

    fn clean_orphaned_tool_results(body: &mut Value) {
        let Some(messages) = body.get_mut("messages").and_then(|m| m.as_array_mut()) else {
            return;
        };

        for i in 0..messages.len() {
            let valid_ids: std::collections::HashSet<String> = if i > 0 {
                let prev = &messages[i - 1];
                prev.get("content")
                    .and_then(|c| c.as_array())
                    .map(|items| {
                        items
                            .iter()
                            .filter_map(|item| {
                                if item.get("type").and_then(|t| t.as_str()) == Some("tool_use") {
                                    item.get("id")
                                        .and_then(|id| id.as_str())
                                        .map(|s| s.to_string())
                                } else {
                                    None
                                }
                            })
                            .collect()
                    })
                    .unwrap_or_default()
            } else {
                std::collections::HashSet::new()
            };

            if let Some(content) = messages[i].get_mut("content").and_then(|c| c.as_array_mut()) {
                content.retain(|item| {
                    if item.get("type").and_then(|t| t.as_str()) == Some("tool_result") {
                        match item.get("tool_use_id").and_then(|id| id.as_str()) {
                            None => {
                                debug!("Removing tool_result with missing tool_use_id (required by Bedrock)");
                                false
                            }
                            Some(id) if !valid_ids.contains(id) => {
                                debug!("Removing orphaned tool_result with tool_use_id={}", id);
                                false
                            }
                            _ => true,
                        }
                    } else {
                        true
                    }
                });
            }
        }
    }

    // -----------------------------------------------------------------------
    // Assemble full Bedrock request body
    // -----------------------------------------------------------------------

    fn prepare_body(&self, body: &Value, normalized_model: &str, beta_header: Option<&str>) -> Value {
        let mut bedrock = body.clone();

        bedrock["anthropic_version"] = Value::String("bedrock-2023-05-31".into());

        if let Some(obj) = bedrock.as_object_mut() {
            for field in &["stream", "model", "output_config", "context_management"] {
                obj.remove(*field);
            }
        }

        Self::clean_body(&mut bedrock);
        Self::validate_thinking(&mut bedrock);

        if let Some(header) = beta_header {
            let betas = Self::filter_betas(header, normalized_model);
            if !betas.is_empty() {
                debug!("Using beta features for {}: {:?}", normalized_model, betas);
                bedrock["anthropic_beta"] =
                    Value::Array(betas.into_iter().map(Value::String).collect());
            }
        }

        Self::clean_orphaned_tool_results(&mut bedrock);

        bedrock
    }

    // -----------------------------------------------------------------------
    // SSO credential check
    // -----------------------------------------------------------------------

    async fn check_sso_credentials(&self) -> Result<(), ProviderError> {
        if self.cred_cache.is_valid() {
            return Ok(());
        }

        let expiry = match self.read_sso_expiry().await {
            Ok(v) => v,
            Err(e) => {
                warn!("Could not read SSO cache: {}", e);
                self.cred_cache.mark_valid();
                return Ok(());
            }
        };

        let Some(expires_at) = expiry else {
            self.cred_cache.mark_valid();
            return Ok(());
        };

        let remaining_secs = (expires_at - chrono::Utc::now()).num_seconds();
        if remaining_secs > 300 {
            self.cred_cache.mark_valid();
            return Ok(());
        }

        warn!("AWS SSO credentials expiring in {}s, attempting refresh", remaining_secs.max(0));
        self.do_sso_login().await
    }

    async fn read_sso_expiry(&self) -> Result<Option<chrono::DateTime<chrono::Utc>>, anyhow::Error> {
        let cache_dir = home_relative(".aws/sso/cache");
        let mut dir = match tokio::fs::read_dir(&cache_dir).await {
            Ok(d) => d,
            Err(_) => return Ok(None),
        };

        let mut soonest: Option<chrono::DateTime<chrono::Utc>> = None;

        while let Ok(Some(entry)) = dir.next_entry().await {
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) != Some("json") {
                continue;
            }
            let Ok(contents) = tokio::fs::read_to_string(&path).await else { continue };
            let Ok(parsed): Result<Value, _> = serde_json::from_str(&contents) else { continue };
            let Some(s) = parsed.get("expiresAt").and_then(|v| v.as_str()) else { continue };
            let Ok(dt) = chrono::DateTime::parse_from_rfc3339(s) else { continue };
            let utc = dt.with_timezone(&chrono::Utc);
            if soonest.map(|prev| utc < prev).unwrap_or(true) {
                soonest = Some(utc);
            }
        }

        Ok(soonest)
    }

    async fn do_sso_login(&self) -> Result<(), ProviderError> {
        // nix::unistd::isatty requires the "fs" feature in nix 0.29
        let has_tty = nix::unistd::isatty(std::io::stdin().as_raw_fd()).unwrap_or(false);

        if !has_tty {
            return Err(ProviderError::Auth(
                "AWS SSO session expired. Run: aws sso login".to_string(),
            ));
        }

        let mutex = self.sso_lock.get_or_init(|| Mutex::new(()));
        let _guard = mutex.lock().await;

        // Re-check after acquiring lock — another waiter may have already refreshed
        if self.cred_cache.is_valid() {
            return Ok(());
        }

        let profile = self.config.aws_profile.clone();
        let status = tokio::process::Command::new("aws")
            .args(["sso", "login", "--profile", &profile])
            .status()
            .await
            .map_err(|e| ProviderError::Auth(format!("Failed to spawn aws sso login: {}", e)))?;

        if status.success() {
            self.cred_cache.mark_valid();
            Ok(())
        } else {
            Err(ProviderError::Auth(
                "aws sso login failed. Run: aws sso login".to_string(),
            ))
        }
    }

    // -----------------------------------------------------------------------
    // Error classification
    // -----------------------------------------------------------------------

    fn classify_stream_error(
        e: SdkError<
            aws_sdk_bedrockruntime::operation::invoke_model_with_response_stream::InvokeModelWithResponseStreamError,
        >,
    ) -> ProviderError {
        use aws_sdk_bedrockruntime::operation::invoke_model_with_response_stream::InvokeModelWithResponseStreamError as E;

        if let SdkError::ServiceError(se) = &e {
            return match se.err() {
                E::ThrottlingException(_) | E::ServiceQuotaExceededException(_) => {
                    ProviderError::RateLimited
                }
                E::ValidationException(v) => ProviderError::Validation(v.to_string(), 400),
                E::AccessDeniedException(a) => ProviderError::Auth(a.to_string()),
                E::ModelTimeoutException(_) => ProviderError::Timeout,
                _ => ProviderError::Upstream { status: 500, body: e.to_string() },
            };
        }
        if matches!(e, SdkError::TimeoutError(_)) {
            return ProviderError::Timeout;
        }
        ProviderError::Upstream { status: 500, body: e.to_string() }
    }

    fn classify_invoke_error(
        e: SdkError<aws_sdk_bedrockruntime::operation::invoke_model::InvokeModelError>,
    ) -> ProviderError {
        use aws_sdk_bedrockruntime::operation::invoke_model::InvokeModelError as E;

        if let SdkError::ServiceError(se) = &e {
            return match se.err() {
                E::ThrottlingException(_) | E::ServiceQuotaExceededException(_) => {
                    ProviderError::RateLimited
                }
                E::ValidationException(v) => ProviderError::Validation(v.to_string(), 400),
                E::AccessDeniedException(a) => ProviderError::Auth(a.to_string()),
                E::ModelTimeoutException(_) => ProviderError::Timeout,
                _ => ProviderError::Upstream { status: 500, body: e.to_string() },
            };
        }
        if matches!(e, SdkError::TimeoutError(_)) {
            return ProviderError::Timeout;
        }
        ProviderError::Upstream { status: 500, body: e.to_string() }
    }

    // -----------------------------------------------------------------------
    // Public streaming API
    // -----------------------------------------------------------------------

    /// Stream via `invoke_model_with_response_stream`. Returns an mpsc
    /// Receiver; drain with `rx.recv().await` — returns `None` when done.
    pub async fn stream_message(
        &self,
        body: &Value,
        beta_header: Option<&str>,
    ) -> Result<tokio::sync::mpsc::Receiver<Result<String, ProviderError>>, ProviderError> {
        self.check_sso_credentials().await?;

        let model_raw = body
            .get("model")
            .and_then(|m| m.as_str())
            .unwrap_or("claude-3-haiku-20240307");

        let normalized = Self::normalize_model(model_raw);
        let bedrock_model_id = Self::to_bedrock_model_id(model_raw);
        let bedrock_body = self.prepare_body(body, &normalized, beta_header);

        let json_bytes = serde_json::to_vec(&bedrock_body)
            .map_err(|e| ProviderError::Validation(e.to_string(), 400))?;

        let response = self
            .client
            .invoke_model_with_response_stream()
            .model_id(&bedrock_model_id)
            .body(Blob::new(json_bytes))
            .content_type("application/json")
            .accept("application/json")
            .send()
            .await
            .map_err(Self::classify_stream_error)?;

        let (tx, rx) = tokio::sync::mpsc::channel::<Result<String, ProviderError>>(64);

        tokio::spawn(async move {
            let mut stream = response.body;
            loop {
                match stream.recv().await {
                    Ok(Some(ResponseStream::Chunk(chunk))) => {
                        if let Some(blob) = chunk.bytes {
                            match serde_json::from_slice::<Value>(blob.as_ref()) {
                                Ok(parsed) => {
                                    let sse = format!("data: {}\n\n", parsed);
                                    if tx.send(Ok(sse)).await.is_err() {
                                        break;
                                    }
                                }
                                Err(e) => {
                                    let _ = tx
                                        .send(Err(ProviderError::Upstream {
                                            status: 500,
                                            body: format!("Failed to parse Bedrock chunk: {}", e),
                                        }))
                                        .await;
                                    break;
                                }
                            }
                        }
                    }
                    Ok(Some(_)) => { /* Unknown ResponseStream variant — ignore */ }
                    Ok(None) => break,
                    Err(e) => {
                        let msg = e.to_string();
                        let err = if msg.to_lowercase().contains("expiredtokenexception")
                            || msg.to_lowercase().contains("security token")
                        {
                            ProviderError::Auth(
                                "AWS SSO session expired. Run: aws sso login".to_string(),
                            )
                        } else {
                            ProviderError::Upstream { status: 500, body: msg }
                        };
                        let _ = tx.send(Err(err)).await;
                        break;
                    }
                }
            }
        });

        Ok(rx)
    }

    // -----------------------------------------------------------------------
    // Public non-streaming API (with timeout retries)
    // -----------------------------------------------------------------------

    pub async fn send_message(
        &self,
        body: &Value,
        beta_header: Option<&str>,
        max_retries: u32,
    ) -> Result<Value, ProviderError> {
        self.check_sso_credentials().await?;

        let model_raw = body
            .get("model")
            .and_then(|m| m.as_str())
            .unwrap_or("claude-3-haiku-20240307");

        let normalized = Self::normalize_model(model_raw);
        let bedrock_model_id = Self::to_bedrock_model_id(model_raw);
        let bedrock_body = self.prepare_body(body, &normalized, beta_header);

        let json_bytes = serde_json::to_vec(&bedrock_body)
            .map_err(|e| ProviderError::Validation(e.to_string(), 400))?;

        let mut retries = 0u32;
        loop {
            let result = self
                .client
                .invoke_model()
                .model_id(&bedrock_model_id)
                .body(Blob::new(json_bytes.clone()))
                .content_type("application/json")
                .accept("application/json")
                .send()
                .await;

            match result {
                Ok(output) => {
                    let bytes = output.body.into_inner();
                    let parsed: Value = serde_json::from_slice(&bytes).map_err(|e| {
                        ProviderError::Upstream {
                            status: 500,
                            body: format!("Failed to parse Bedrock response: {}", e),
                        }
                    })?;
                    return Ok(parsed);
                }
                Err(e) => {
                    let err = Self::classify_invoke_error(e);
                    match err {
                        ProviderError::Timeout if retries < max_retries => {
                            retries += 1;
                            warn!("Bedrock timeout, retry {}/{}", retries, max_retries);
                        }
                        other => return Err(other),
                    }
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

fn home_relative(relative: &str) -> std::path::PathBuf {
    let home = std::env::var("HOME")
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|_| std::path::PathBuf::from("/root"));
    home.join(relative)
}

// ---------------------------------------------------------------------------
// Provider trait impl (wires BedrockProvider into FallbackHandler)
// ---------------------------------------------------------------------------

#[async_trait]
impl Provider for BedrockProvider {
    fn name(&self) -> &str {
        "bedrock"
    }

    async fn send(
        &self,
        body: Value,
        headers: HeaderMap,
        stream: bool,
    ) -> Result<ProviderResponse, ProviderError> {
        let beta_header = headers
            .get("anthropic-beta")
            .and_then(|v| v.to_str().ok())
            .map(str::to_string);

        if stream {
            let mut rx = self
                .stream_message(&body, beta_header.as_deref())
                .await?;

            // Convert the mpsc Receiver into a futures Stream of Bytes.
            let (tx_stream, rx_stream) = tokio::sync::mpsc::channel::<Result<Bytes, reqwest::Error>>(64);

            tokio::spawn(async move {
                while let Some(result) = rx.recv().await {
                    match result {
                        Ok(s) => {
                            if tx_stream.send(Ok(Bytes::from(s))).await.is_err() {
                                break;
                            }
                        }
                        Err(e) => {
                            // Convert ProviderError to a string in an upstream error shape.
                            let msg = format!("data: {{\"type\":\"error\",\"error\":{{\"message\":\"{}\"}}}}\n\n", e);
                            let _ = tx_stream.send(Ok(Bytes::from(msg))).await;
                            break;
                        }
                    }
                }
            });

            let byte_stream = tokio_stream::wrappers::ReceiverStream::new(rx_stream);
            Ok(ProviderResponse::Stream(Box::pin(byte_stream)))
        } else {
            let value = self
                .send_message(&body, beta_header.as_deref(), self.config.bedrock_max_retries)
                .await?;
            Ok(ProviderResponse::Full(value))
        }
    }
}
