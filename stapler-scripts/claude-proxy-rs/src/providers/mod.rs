//! Shared provider types and error definitions.

pub mod anthropic;
pub mod bedrock;

/// Errors that can be returned by any provider.
#[derive(Debug, thiserror::Error)]
pub enum ProviderError {
    #[error("rate limited")]
    RateLimited,
    #[error("auth error: {0}")]
    Auth(String),
    #[error("validation error: {0}")]
    Validation(String, u16),
    #[error("timeout")]
    Timeout,
    #[error("upstream error: {status} {body}")]
    Upstream { status: u16, body: String },
}
