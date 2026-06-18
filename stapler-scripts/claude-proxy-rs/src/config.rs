//! Configuration loaded from environment variables at startup.
//!
//! All settings have sensible defaults and are read once at startup.
//! No hot-reloading — restart the proxy to pick up new values.

use std::env;

/// Top-level proxy configuration derived from environment variables.
#[derive(Debug, Clone)]
pub struct Config {
    /// Port to listen on. Default: 47000.
    pub port: u16,

    /// Duration in seconds that Anthropic stays in cooldown after a 429. Default: 300.
    pub cooldown_seconds: u64,

    /// Per-request timeout in seconds for upstream HTTP calls. Default: 300.
    pub request_timeout: u64,

    /// Number of times to retry a timed-out Bedrock request. Default: 3.
    pub bedrock_max_retries: u32,

    /// Enable compression pipeline. Default: true. Set STAPLER_COMPRESS=0 to disable.
    pub stapler_compress: bool,

    /// Minimum request body size (bytes) below which compression is skipped. Default: 4096.
    pub compress_floor_bytes: usize,

    /// Enable cache-aligner (tool sorting for KV cache stability). Default: true. Set CACHE_ALIGNER=0 to disable.
    pub cache_aligner: bool,

    /// Verbosity steering level. 0=off, 1=light, 2=moderate (default), 3=aggressive.
    pub verbosity_level: u8,

    /// Maximum number of memory store entries. Default: 1000.
    pub memory_max_entries: usize,

    /// AWS profile used for Bedrock. Default: "Sandbox.AdministratorAccess".
    pub aws_profile: String,

    /// AWS region for Bedrock. Default: "us-west-2".
    pub aws_region: String,

    /// Optional OAuth token for Anthropic API. Overrides Authorization header fallback.
    pub claude_code_oauth_token: Option<String>,
}

impl Config {
    /// Read all configuration from environment variables, applying defaults for missing values.
    pub fn from_env() -> Self {
        Self {
            port: parse_env("PROXY_PORT", 47000),
            cooldown_seconds: parse_env("COOLDOWN_SECONDS", 300),
            request_timeout: parse_env("REQUEST_TIMEOUT", 300),
            bedrock_max_retries: parse_env("BEDROCK_MAX_RETRIES", 3),
            stapler_compress: parse_bool_env("STAPLER_COMPRESS", true),
            compress_floor_bytes: parse_env("COMPRESS_FLOOR_BYTES", 4096),
            cache_aligner: parse_bool_env("CACHE_ALIGNER", true),
            verbosity_level: parse_env_clamped("VERBOSITY_LEVEL", 2, 0, 3),
            memory_max_entries: parse_env("MEMORY_MAX_ENTRIES", 1000),
            aws_profile: env::var("AWS_PROFILE")
                .unwrap_or_else(|_| "Sandbox.AdministratorAccess".to_string()),
            aws_region: env::var("AWS_REGION")
                .unwrap_or_else(|_| "us-west-2".to_string()),
            claude_code_oauth_token: env::var("CLAUDE_CODE_OAUTH_TOKEN").ok(),
        }
    }
}

/// Parse an environment variable as `T`, falling back to `default` if missing or unparseable.
fn parse_env<T>(name: &str, default: T) -> T
where
    T: std::str::FromStr + Copy,
{
    env::var(name)
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(default)
}

/// Parse a boolean env var. "0" or "false" (case-insensitive) → false; anything else → true.
fn parse_bool_env(name: &str, default: bool) -> bool {
    match env::var(name).as_deref() {
        Ok("0") | Ok("false") | Ok("FALSE") | Ok("False") => false,
        Ok(_) => true,
        Err(_) => default,
    }
}

/// Parse a numeric env var and clamp it to [min, max].
fn parse_env_clamped<T>(name: &str, default: T, min: T, max: T) -> T
where
    T: std::str::FromStr + Copy + PartialOrd,
{
    let val: T = parse_env(name, default);
    if val < min {
        min
    } else if val > max {
        max
    } else {
        val
    }
}
