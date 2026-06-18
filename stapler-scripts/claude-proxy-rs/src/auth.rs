//! Authentication token extraction.
//!
//! Tokens are extracted from the `Authorization: Bearer <token>` header first,
//! then fall back to the `CLAUDE_CODE_OAUTH_TOKEN` env var (cached via Config).

use axum::http::HeaderMap;

/// A successfully extracted auth token.
#[derive(Debug, Clone)]
pub struct AuthToken {
    pub token: String,
}

/// Failure mode when no token is available.
#[derive(Debug)]
pub enum AuthError {
    /// No Authorization header and no CLAUDE_CODE_OAUTH_TOKEN env var configured.
    Missing,
}

impl std::fmt::Display for AuthError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            AuthError::Missing => write!(f, "no auth token: set Authorization header or CLAUDE_CODE_OAUTH_TOKEN"),
        }
    }
}

/// Extract an auth token from the request headers, falling back to the configured env var token.
///
/// Priority:
/// 1. `Authorization: Bearer <token>` header
/// 2. `fallback_token` (from `Config::claude_code_oauth_token`)
pub fn extract_token(headers: &HeaderMap, fallback_token: Option<&str>) -> Result<AuthToken, AuthError> {
    // 1. Try Authorization header.
    if let Some(auth_value) = headers.get("authorization") {
        if let Ok(auth_str) = auth_value.to_str() {
            if let Some(token) = auth_str.strip_prefix("Bearer ") {
                let token = token.trim().to_string();
                if !token.is_empty() {
                    return Ok(AuthToken { token });
                }
            }
        }
    }

    // 2. Fall back to env var token.
    if let Some(token) = fallback_token {
        if !token.is_empty() {
            return Ok(AuthToken { token: token.to_string() });
        }
    }

    Err(AuthError::Missing)
}
