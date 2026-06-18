//! Shared provider types and error definitions.

pub mod anthropic;
pub mod bedrock;

use bytes::Bytes;
use futures_util::Stream;
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
