//! Shared provider types, error definitions, and OpenAI translation helpers.

pub mod anthropic;
pub mod bedrock;

use bytes::Bytes;
use futures_util::Stream;
use serde_json::{json, Value};
use std::pin::Pin;

/// The response returned by a provider.
///
/// Non-streaming responses carry the full JSON body.
/// Streaming responses carry a byte stream that yields raw SSE chunks
/// (each chunk is a complete `data: {...}\n\n` line as emitted by the upstream).
pub enum ProviderResponse {
    /// A complete, buffered JSON response body.
    Full(serde_json::Value),
    /// An SSE byte stream.  Each `Ok(Bytes)` item is one or more raw SSE lines.
    Stream(Pin<Box<dyn Stream<Item = Result<Bytes, reqwest::Error>> + Send>>),
}

/// Errors that can be returned by any provider.
#[derive(Debug, thiserror::Error)]
pub enum ProviderError {
    #[error("rate limited")]
    RateLimited,
    /// Optional `retry_after` seconds parsed from the `Retry-After` header.
    #[error("rate limited (retry after {retry_after:?}s)")]
    RateLimitedWithRetry { retry_after: u64 },
    #[error("auth error: {0}")]
    Auth(String),
    #[error("validation error: {0}")]
    Validation(String, u16),
    #[error("timeout")]
    Timeout,
    #[error("model unsupported: {0}")]
    ModelUnsupported(String),
    #[error("upstream error: {status} {body}")]
    Upstream { status: u16, body: String },
}

impl ProviderError {
    /// Returns the optional `Retry-After` seconds if this is a rate-limit error.
    pub fn retry_after_secs(&self) -> Option<u64> {
        match self {
            ProviderError::RateLimitedWithRetry { retry_after } => Some(*retry_after),
            _ => None,
        }
    }

    /// Returns true if this error is a rate-limit (429) error.
    pub fn is_rate_limited(&self) -> bool {
        matches!(
            self,
            ProviderError::RateLimited | ProviderError::RateLimitedWithRetry { .. }
        )
    }

    /// Returns true if this is a client-side validation error (4xx, not 429).
    pub fn is_validation(&self) -> bool {
        matches!(self, ProviderError::Validation(..))
    }

    /// Returns true if this is an authentication error.
    pub fn is_auth(&self) -> bool {
        matches!(self, ProviderError::Auth(..))
    }

    /// Returns true if this is a transient error that may be retried
    /// (timeout or upstream 5xx).
    pub fn is_transient(&self) -> bool {
        matches!(self, ProviderError::Timeout | ProviderError::Upstream { .. })
    }
}

// ────────────────────────────────────────────────────────────────────────────
// OpenAI ↔ Anthropic translation (Story 2.2)
// ────────────────────────────────────────────────────────────────────────────

/// Translate an OpenAI Chat Completions request body to Anthropic Messages format.
///
/// Mapping:
/// - `messages[].role` "system" → top-level `system` string; user/assistant → Anthropic messages
/// - `messages[].content` string → `[{"type":"text","text":"..."}]`
/// - `model`, `max_tokens` (default 1024), `temperature`, `stream` → forwarded as-is
pub fn translate_openai_to_anthropic(openai: Value) -> Value {
    let model = openai
        .get("model")
        .and_then(Value::as_str)
        .unwrap_or("claude-3-haiku-20240307")
        .to_string();

    let max_tokens = openai
        .get("max_tokens")
        .and_then(Value::as_u64)
        .unwrap_or(1024);

    let stream = openai
        .get("stream")
        .and_then(Value::as_bool)
        .unwrap_or(false);

    let temperature = openai.get("temperature").cloned();

    let mut system_text: Option<String> = None;
    let mut messages: Vec<Value> = Vec::new();

    if let Some(openai_messages) = openai.get("messages").and_then(Value::as_array) {
        for msg in openai_messages {
            let role = msg.get("role").and_then(Value::as_str).unwrap_or("user");
            let content = openai_content_to_anthropic(msg.get("content").cloned().unwrap_or(Value::Null));

            if role == "system" {
                // Accumulate system messages into a single string
                let text = extract_text_from_content(&content);
                match system_text.as_mut() {
                    Some(s) => { s.push('\n'); s.push_str(&text); }
                    None => system_text = Some(text),
                }
            } else {
                messages.push(json!({"role": role, "content": content}));
            }
        }
    }

    let mut body = json!({
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
        "stream": stream,
    });

    if let Some(sys) = system_text {
        body["system"] = Value::String(sys);
    }

    if let Some(temp) = temperature {
        body["temperature"] = temp;
    }

    body
}

/// Convert OpenAI message content (string or array) to Anthropic content array.
fn openai_content_to_anthropic(content: Value) -> Value {
    match content {
        Value::String(s) => json!([{"type": "text", "text": s}]),
        Value::Array(arr) => {
            // OpenAI content parts: {"type":"text","text":"..."} or {"type":"image_url",...}
            let blocks: Vec<Value> = arr
                .into_iter()
                .filter_map(|part| {
                    let kind = part.get("type").and_then(Value::as_str)?;
                    if kind == "text" {
                        Some(json!({"type": "text", "text": part.get("text").and_then(Value::as_str).unwrap_or("")}))
                    } else {
                        None // skip image_url etc. for now
                    }
                })
                .collect();
            Value::Array(blocks)
        }
        _ => json!([{"type": "text", "text": ""}]),
    }
}

/// Extract plain text from an Anthropic-format content array.
fn extract_text_from_content(content: &Value) -> String {
    match content {
        Value::Array(arr) => arr
            .iter()
            .filter_map(|b| b.get("text").and_then(Value::as_str))
            .collect::<Vec<_>>()
            .join("\n"),
        Value::String(s) => s.clone(),
        _ => String::new(),
    }
}

/// Translate an Anthropic Messages response to OpenAI Chat Completions format.
///
/// Output shape: `choices[0].message.{role,content}`, `usage.*`, `finish_reason`.
pub fn translate_anthropic_to_openai(anthropic: Value) -> Value {
    let content_text = anthropic
        .get("content")
        .and_then(Value::as_array)
        .and_then(|arr| arr.first())
        .and_then(|block| block.get("text"))
        .and_then(Value::as_str)
        .unwrap_or("")
        .to_string();

    let finish_reason = anthropic
        .get("stop_reason")
        .and_then(Value::as_str)
        .unwrap_or("stop")
        .to_string();

    let model = anthropic
        .get("model")
        .and_then(Value::as_str)
        .unwrap_or("unknown")
        .to_string();

    let prompt_tokens = anthropic
        .get("usage")
        .and_then(|u| u.get("input_tokens"))
        .and_then(Value::as_u64)
        .unwrap_or(0);
    let completion_tokens = anthropic
        .get("usage")
        .and_then(|u| u.get("output_tokens"))
        .and_then(Value::as_u64)
        .unwrap_or(0);

    json!({
        "id": anthropic.get("id").and_then(Value::as_str).unwrap_or(""),
        "object": "chat.completion",
        "model": model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": content_text
            },
            "finish_reason": finish_reason
        }],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
    })
}
