//! Fallback state machine: Anthropic primary → Bedrock fallback on 429.
//!
//! # Design (ADR-003)
//!
//! A custom ~40-line `FallbackState` with `tokio::sync::RwLock<ProviderState>`
//! is used instead of a circuit-breaker crate because:
//!
//! - All existing circuit-breaker crates model *failure-rate* thresholds, not a
//!   single-event 429 → fixed-wall-clock-cooldown pattern.
//! - `AtomicBool` alone is insufficient: the expiry *check + state transition*
//!   must be atomic (read-then-write under the same lock).
//!
//! # Routing rules (mirroring Python fallback.py)
//!
//! 1. **Normal state**: route to primary (Anthropic).
//! 2. **Cooldown state** (`Instant::now() < until`): skip primary, route to fallback (Bedrock).
//! 3. **Cooldown expired** (`Instant::now() >= until`): transition back to Normal, route to primary.
//! 4. **Primary RateLimited**: enter cooldown for `cooldown_duration` (or `retry_after` if present),
//!    record fallback metric, retry same request on fallback.
//! 5. **Primary Timeout/Upstream5xx**: log and retry on fallback.  No cooldown — not a 429.
//! 6. **Primary Validation/Auth (4xx)**: return error immediately; do NOT retry on fallback.
//! 7. **Primary ModelUnsupported**: skip primary silently, try fallback.
//! 8. **Bedrock**: NEVER enters cooldown; Bedrock-only retries use exponential back-off
//!    (`2^attempt` seconds, up to `bedrock_max_retries`).

use std::sync::Arc;
use std::time::{Duration, Instant};

use async_trait::async_trait;
use axum::http::HeaderMap;
use tokio::sync::RwLock;
use tracing::{debug, error, info, warn};

use crate::providers::{ProviderError, ProviderResponse};

// ---------------------------------------------------------------------------
// Provider trait
// ---------------------------------------------------------------------------

/// Implemented by [`AnthropicProvider`] and [`BedrockProvider`].
///
/// Both providers are generic over this trait so `FallbackHandler` can route
/// requests without knowing concrete types.
#[async_trait]
pub trait Provider: Send + Sync {
    /// Human-readable provider name for logging (e.g. `"anthropic"`, `"bedrock"`).
    fn name(&self) -> &str;

    /// Send a single request to the provider and return either a full JSON body
    /// or a streaming byte stream.
    ///
    /// # Parameters
    /// - `body`: the (already cleaned) Anthropic-format JSON request body.
    /// - `headers`: forwarded HTTP headers from the incoming client request.
    /// - `stream`: if `true`, the provider should return a `ProviderResponse::Stream`.
    async fn send(
        &self,
        body: serde_json::Value,
        headers: HeaderMap,
        stream: bool,
    ) -> Result<ProviderResponse, ProviderError>;
}

// ---------------------------------------------------------------------------
// State machine
// ---------------------------------------------------------------------------

/// Internal state of the primary provider.
#[derive(Debug, Clone)]
enum ProviderState {
    /// Primary provider is healthy — route requests to it.
    Normal,
    /// Primary provider is in cooldown until `until`.  Route requests to fallback.
    Cooldown { until: Instant },
}

/// Thread-safe state for the fallback mechanism.
///
/// Holds the `RwLock<ProviderState>` for the *primary* provider only.
/// The fallback (Bedrock) is never put in cooldown.
pub struct FallbackState {
    inner: Arc<RwLock<ProviderState>>,
    cooldown_duration: Duration,
}

impl FallbackState {
    /// Create a new `FallbackState` with the given cooldown duration.
    pub fn new(cooldown_secs: u64) -> Self {
        Self {
            inner: Arc::new(RwLock::new(ProviderState::Normal)),
            cooldown_duration: Duration::from_secs(cooldown_secs),
        }
    }

    /// Returns `true` if the primary provider is currently in cooldown.
    ///
    /// Acquires a **read** lock.  If the cooldown has expired, the check
    /// returns `false` but does *not* clear the state (a subsequent write is
    /// needed — see `try_exit_cooldown`).
    pub async fn should_use_fallback(&self) -> bool {
        let state = self.inner.read().await;
        match *state {
            ProviderState::Normal => false,
            ProviderState::Cooldown { until } => Instant::now() < until,
        }
    }

    /// Enter cooldown for `duration` seconds (override the default if
    /// a `Retry-After` header value was parsed from the 429 response).
    ///
    /// Acquires a **write** lock.
    pub async fn enter_cooldown(&self, override_duration: Option<Duration>) {
        let duration = override_duration.unwrap_or(self.cooldown_duration);
        let until = Instant::now() + duration;
        let mut state = self.inner.write().await;
        *state = ProviderState::Cooldown { until };
        warn!(
            provider = "anthropic",
            cooldown_secs = duration.as_secs(),
            "primary provider entering cooldown — switching to fallback"
        );
    }

    /// Atomically check-and-clear an *expired* cooldown.
    ///
    /// Acquires a **write** lock.  If the cooldown has already expired,
    /// transitions to `Normal` and returns `true`.  Otherwise returns `false`.
    pub async fn try_exit_cooldown(&self) -> bool {
        let mut state = self.inner.write().await;
        match *state {
            ProviderState::Cooldown { until } if Instant::now() >= until => {
                *state = ProviderState::Normal;
                info!(provider = "anthropic", "cooldown expired — resuming primary provider");
                true
            }
            _ => false,
        }
    }

    /// Remaining cooldown in seconds (0 if not in cooldown).  Used for metrics.
    pub async fn remaining_secs(&self) -> u64 {
        let state = self.inner.read().await;
        match *state {
            ProviderState::Cooldown { until } => {
                let now = Instant::now();
                if until > now {
                    (until - now).as_secs()
                } else {
                    0
                }
            }
            ProviderState::Normal => 0,
        }
    }
}

// ---------------------------------------------------------------------------
// FallbackHandler — dispatch logic
// ---------------------------------------------------------------------------

/// Orchestrates request dispatch across `primary` and `fallback` providers.
///
/// The primary is Anthropic; the fallback is Bedrock.
/// Generic over the `Provider` trait so unit tests can inject mocks.
pub struct FallbackHandler<P, F> {
    primary: P,
    fallback: F,
    state: Arc<FallbackState>,
    bedrock_max_retries: u32,
}

impl<P, F> FallbackHandler<P, F>
where
    P: Provider,
    F: Provider,
{
    /// Create a new `FallbackHandler`.
    ///
    /// `state` should be the same `Arc<FallbackState>` held in `AppState` so
    /// the cooldown persists across requests.
    pub fn new(
        primary: P,
        fallback: F,
        state: Arc<FallbackState>,
        bedrock_max_retries: u32,
    ) -> Self {
        Self {
            primary,
            fallback,
            state,
            bedrock_max_retries,
        }
    }

    /// Dispatch a request, routing to the correct provider and applying
    /// fallback / retry logic.
    ///
    /// # Routing summary
    ///
    /// ```text
    /// if cooldown_active → skip primary → try fallback (with Bedrock retries)
    /// else               → try primary
    ///                        on RateLimited  → enter_cooldown → try fallback
    ///                        on Transient    → try fallback (no cooldown)
    ///                        on Validation   → return immediately (client error)
    ///                        on Auth         → return immediately
    ///                        on Unsupported  → try fallback silently
    ///                    → if fallback also fails → return last error
    /// ```
    pub async fn dispatch(
        &self,
        body: serde_json::Value,
        headers: HeaderMap,
        stream: bool,
        request_id: &str,
    ) -> Result<ProviderResponse, ProviderError> {
        let model = body
            .get("model")
            .and_then(|v| v.as_str())
            .unwrap_or("unknown");

        // -----------------------------------------------------------------
        // Step 1: decide whether to skip the primary on this request.
        // -----------------------------------------------------------------
        let skip_primary = if self.state.should_use_fallback().await {
            debug!(
                request_id,
                provider = self.primary.name(),
                "skipping primary (cooldown active)"
            );
            true
        } else {
            // Try to clear an already-expired cooldown so next check is fast.
            let _ = self.state.try_exit_cooldown().await;
            false
        };

        // -----------------------------------------------------------------
        // Step 2: try primary (unless in cooldown).
        // -----------------------------------------------------------------
        if !skip_primary {
            info!(
                request_id,
                provider = self.primary.name(),
                model,
                "→ routing to primary"
            );

            match self
                .primary
                .send(body.clone(), headers.clone(), stream)
                .await
            {
                Ok(response) => {
                    info!(
                        request_id,
                        provider = self.primary.name(),
                        model,
                        "✓ primary succeeded"
                    );
                    return Ok(response);
                }

                // 4xx (excluding 429) → return immediately; do NOT retry.
                Err(e) if e.is_validation() => {
                    error!(
                        request_id,
                        provider = self.primary.name(),
                        model,
                        error = %e,
                        "✗ validation error — not retrying on fallback"
                    );
                    return Err(e);
                }

                // 401 → return immediately.
                Err(e) if e.is_auth() => {
                    error!(
                        request_id,
                        provider = self.primary.name(),
                        model,
                        error = %e,
                        "✗ auth error — not retrying on fallback"
                    );
                    return Err(e);
                }

                // 429 → enter cooldown, fall through to fallback.
                Err(e) if e.is_rate_limited() => {
                    let override_duration = e
                        .retry_after_secs()
                        .map(Duration::from_secs);
                    self.state.enter_cooldown(override_duration).await;
                    // Metrics hook (Epic 10): log the switch; counter increment
                    // will be wired in once `COUNTERS` is available.
                    warn!(
                        request_id,
                        from = self.primary.name(),
                        to = self.fallback.name(),
                        model,
                        retry_after_secs = e.retry_after_secs(),
                        "↳ primary rate-limited — switching to fallback (fallback_count++)"
                    );
                    // fall through to fallback below
                }

                // Model not available on primary → try fallback silently.
                Err(ProviderError::ModelUnsupported(ref m)) => {
                    info!(
                        request_id,
                        provider = self.primary.name(),
                        model = %m,
                        "⤳ model unsupported on primary — trying fallback"
                    );
                    // fall through to fallback below
                }

                // Timeout / upstream 5xx → log and try fallback (no cooldown).
                Err(e) => {
                    warn!(
                        request_id,
                        provider = self.primary.name(),
                        model,
                        error = %e,
                        "✗ primary transient error — trying fallback (no cooldown)"
                    );
                    // fall through to fallback below
                }
            }
        }

        // -----------------------------------------------------------------
        // Step 3: try fallback with exponential back-off.
        //
        // Bedrock is NEVER put in cooldown.
        // - Timeout errors → retry up to `bedrock_max_retries` with 2^n seconds.
        // - RateLimited on Bedrock → also retry with back-off (not cooldown).
        // - Validation / Auth → return immediately (client error).
        // -----------------------------------------------------------------
        let mut last_error: Option<ProviderError> = None;

        for attempt in 0..self.bedrock_max_retries {
            if attempt > 0 {
                let backoff = Duration::from_secs(2u64.pow(attempt - 1));
                info!(
                    request_id,
                    provider = self.fallback.name(),
                    model,
                    attempt,
                    backoff_secs = backoff.as_secs(),
                    "↻ fallback retry"
                );
                tokio::time::sleep(backoff).await;
            } else {
                info!(
                    request_id,
                    provider = self.fallback.name(),
                    model,
                    "→ routing to fallback"
                );
            }

            match self
                .fallback
                .send(body.clone(), headers.clone(), stream)
                .await
            {
                Ok(response) => {
                    info!(
                        request_id,
                        provider = self.fallback.name(),
                        model,
                        attempt,
                        "✓ fallback succeeded"
                    );
                    return Ok(response);
                }

                // 4xx → return immediately, no more retries.
                Err(e) if e.is_validation() => {
                    error!(
                        request_id,
                        provider = self.fallback.name(),
                        model,
                        error = %e,
                        "✗ fallback validation error"
                    );
                    return Err(e);
                }

                Err(e) if e.is_auth() => {
                    error!(
                        request_id,
                        provider = self.fallback.name(),
                        model,
                        error = %e,
                        "✗ fallback auth error"
                    );
                    return Err(e);
                }

                // Model not supported on fallback either → bail.
                Err(ProviderError::ModelUnsupported(ref m)) => {
                    error!(
                        request_id,
                        provider = self.fallback.name(),
                        model = %m,
                        "✗ model unsupported on fallback"
                    );
                    last_error = Some(ProviderError::ModelUnsupported(m.clone()));
                    break;
                }

                // Transient (timeout / upstream / rate-limit) → retry.
                Err(e) => {
                    warn!(
                        request_id,
                        provider = self.fallback.name(),
                        model,
                        attempt,
                        max = self.bedrock_max_retries,
                        error = %e,
                        "✗ fallback transient error"
                    );
                    last_error = Some(e);
                    // If we've used all retries, exit the loop.
                    if attempt + 1 >= self.bedrock_max_retries {
                        error!(
                            request_id,
                            provider = self.fallback.name(),
                            model,
                            "✗ fallback exhausted retries"
                        );
                    }
                }
            }
        }

        // -----------------------------------------------------------------
        // Step 4: all providers failed.
        // -----------------------------------------------------------------
        Err(last_error.unwrap_or(ProviderError::Upstream {
            status: 503,
            body: "all providers are in cooldown or failed".to_string(),
        }))
    }
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use async_trait::async_trait;
    use std::sync::atomic::{AtomicU32, Ordering};

    // ---- mock providers ----

    struct AlwaysOkProvider {
        name: &'static str,
        call_count: Arc<AtomicU32>,
    }

    #[async_trait]
    impl Provider for AlwaysOkProvider {
        fn name(&self) -> &str {
            self.name
        }
        async fn send(
            &self,
            _body: serde_json::Value,
            _headers: HeaderMap,
            _stream: bool,
        ) -> Result<ProviderResponse, ProviderError> {
            self.call_count.fetch_add(1, Ordering::SeqCst);
            Ok(ProviderResponse::Full(serde_json::json!({"ok": true})))
        }
    }

    struct AlwaysErrProvider {
        name: &'static str,
        error: fn() -> ProviderError,
        call_count: Arc<AtomicU32>,
    }

    #[async_trait]
    impl Provider for AlwaysErrProvider {
        fn name(&self) -> &str {
            self.name
        }
        async fn send(
            &self,
            _body: serde_json::Value,
            _headers: HeaderMap,
            _stream: bool,
        ) -> Result<ProviderResponse, ProviderError> {
            self.call_count.fetch_add(1, Ordering::SeqCst);
            Err((self.error)())
        }
    }

    fn make_state(secs: u64) -> Arc<FallbackState> {
        Arc::new(FallbackState::new(secs))
    }

    #[tokio::test]
    async fn test_normal_routes_to_primary() {
        let primary_calls = Arc::new(AtomicU32::new(0));
        let fallback_calls = Arc::new(AtomicU32::new(0));
        let handler = FallbackHandler::new(
            AlwaysOkProvider { name: "anthropic", call_count: primary_calls.clone() },
            AlwaysOkProvider { name: "bedrock", call_count: fallback_calls.clone() },
            make_state(300),
            3,
        );
        let res = handler
            .dispatch(serde_json::json!({}), HeaderMap::new(), false, "test-1")
            .await;
        assert!(res.is_ok());
        assert_eq!(primary_calls.load(Ordering::SeqCst), 1);
        assert_eq!(fallback_calls.load(Ordering::SeqCst), 0);
    }

    #[tokio::test]
    async fn test_rate_limit_triggers_fallback() {
        let primary_calls = Arc::new(AtomicU32::new(0));
        let fallback_calls = Arc::new(AtomicU32::new(0));
        let state = make_state(300);
        let handler = FallbackHandler::new(
            AlwaysErrProvider {
                name: "anthropic",
                error: || ProviderError::RateLimited,
                call_count: primary_calls.clone(),
            },
            AlwaysOkProvider { name: "bedrock", call_count: fallback_calls.clone() },
            state.clone(),
            3,
        );
        let res = handler
            .dispatch(serde_json::json!({}), HeaderMap::new(), false, "test-2")
            .await;
        assert!(res.is_ok());
        assert_eq!(primary_calls.load(Ordering::SeqCst), 1);
        assert_eq!(fallback_calls.load(Ordering::SeqCst), 1);
        // Cooldown should be active.
        assert!(state.should_use_fallback().await);
    }

    #[tokio::test]
    async fn test_validation_error_not_retried() {
        let primary_calls = Arc::new(AtomicU32::new(0));
        let fallback_calls = Arc::new(AtomicU32::new(0));
        let handler = FallbackHandler::new(
            AlwaysErrProvider {
                name: "anthropic",
                error: || ProviderError::Validation("bad field".into(), 400),
                call_count: primary_calls.clone(),
            },
            AlwaysOkProvider { name: "bedrock", call_count: fallback_calls.clone() },
            make_state(300),
            3,
        );
        let res = handler
            .dispatch(serde_json::json!({}), HeaderMap::new(), false, "test-3")
            .await;
        assert!(res.is_err());
        assert_eq!(primary_calls.load(Ordering::SeqCst), 1);
        assert_eq!(fallback_calls.load(Ordering::SeqCst), 0, "fallback must not be called for 4xx");
    }

    #[tokio::test]
    async fn test_cooldown_skips_primary() {
        let primary_calls = Arc::new(AtomicU32::new(0));
        let fallback_calls = Arc::new(AtomicU32::new(0));
        let state = make_state(300);
        // Manually put primary in cooldown.
        state.enter_cooldown(None).await;

        let handler = FallbackHandler::new(
            AlwaysOkProvider { name: "anthropic", call_count: primary_calls.clone() },
            AlwaysOkProvider { name: "bedrock", call_count: fallback_calls.clone() },
            state,
            3,
        );
        let res = handler
            .dispatch(serde_json::json!({}), HeaderMap::new(), false, "test-4")
            .await;
        assert!(res.is_ok());
        assert_eq!(primary_calls.load(Ordering::SeqCst), 0, "primary must be skipped during cooldown");
        assert_eq!(fallback_calls.load(Ordering::SeqCst), 1);
    }

    #[tokio::test]
    async fn test_cooldown_expiry_resumes_primary() {
        let state = make_state(0); // 0-second cooldown expires immediately
        state.enter_cooldown(Some(Duration::from_millis(1))).await;
        tokio::time::sleep(Duration::from_millis(5)).await;
        // After expiry, try_exit_cooldown should return true.
        assert!(state.try_exit_cooldown().await);
        // should_use_fallback should now be false.
        assert!(!state.should_use_fallback().await);
    }
}
