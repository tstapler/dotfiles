"""Metrics collection and reporting for Claude Proxy."""
import time
import os
import asyncio
from typing import Dict, Any, Optional
from collections import deque
import diskcache
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and reports proxy metrics using diskcache for persistence."""

    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize metrics collector with persistent cache."""
        if cache_dir is None:
            cache_dir = os.path.expanduser("~/.cache/claude-proxy/metrics")

        # 50MB cache size limit
        self.cache = diskcache.Cache(cache_dir, size_limit=50 * 1024 * 1024)

        # In-memory deque for recent errors (no file locking!)
        self.recent_errors = deque(maxlen=20)

        # Cached stats (updated every 5s instead of computing on every request)
        self._cached_stats = None
        self._stats_last_computed = 0
        self._stats_cache_ttl = 5  # seconds

        logger.info(f"Metrics collector initialized: {cache_dir}")

    def _incr(self, key: str, value: int = 1):
        """Atomically increment a counter."""
        try:
            self.cache.incr(key, delta=value, default=0)
        except Exception as e:
            logger.error(f"Failed to increment metric {key}: {e}")

    def _get(self, key: str, default: Any = 0) -> Any:
        """Get a value from cache with default."""
        return self.cache.get(key, default)

    def _set(self, key: str, value: Any):
        """Set a value in cache."""
        try:
            self.cache.set(key, value)
        except Exception as e:
            logger.error(f"Failed to set metric {key}: {e}")

    def record_request_complete(
        self,
        provider: str,
        model: str,
        start_time: float,
        success: bool,
        error_type: Optional[str] = None,
        stream: bool = False
    ):
        """Record a completed request with all relevant metrics."""
        duration = time.time() - start_time

        # Total counters
        self._incr("total_requests")
        if success:
            self._incr("total_success")
        else:
            self._incr("total_errors")

            # Record error details
            if error_type:
                self._incr(f"error_type:{error_type}")

                # Add to recent errors list (in-memory deque, no locking needed!)
                error_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "error_type": error_type,
                    "provider": provider,
                    "model": model
                }
                self.recent_errors.appendleft(error_entry)  # Thread-safe

        # Provider counters
        self._incr(f"provider:{provider}:requests")
        if success:
            self._incr(f"provider:{provider}:success")
        else:
            self._incr(f"provider:{provider}:errors")

        # Model counters
        self._incr(f"model:{model}:requests")

        # Duration buckets
        if duration < 1:
            self._incr("duration:lt1s")
        elif duration < 5:
            self._incr("duration:1_5s")
        elif duration < 30:
            self._incr("duration:5_30s")
        elif duration < 60:
            self._incr("duration:30_60s")
        else:
            self._incr("duration:gt60s")

        # Requests per minute tracking
        minute_key = datetime.now().strftime("rpm:%Y-%m-%dT%H:%M")
        self._incr(minute_key)

    def record_fallback(self, from_provider: str, to_provider: str, reason: str):
        """Record a provider fallback event."""
        self._incr("total_fallbacks")
        self._incr(f"fallback_reason:{reason}")
        logger.debug(f"Recorded fallback: {from_provider} -> {to_provider} ({reason})")

    def record_event_loop_lag(self, lag_ms: float):
        """Record an event loop lag sample (called ~every second).

        DEPRECATED: Use async record_event_loop_lag_async() instead.
        """
        minute_key = datetime.now().strftime("%Y-%m-%dT%H:%M")
        # Store as integer with 0.01ms precision to use atomic incr
        lag_int = int(lag_ms * 100)

        # Update max for this minute
        max_key = f"lag:{minute_key}:max"
        current_max = self._get(max_key, 0)
        if lag_int > current_max:
            self._set(max_key, lag_int)

        # Accumulate sum and count for avg
        self._incr(f"lag:{minute_key}:sum", lag_int)
        self._incr(f"lag:{minute_key}:count")

        # Keep the latest sample for instant display
        self._set("lag:current_ms", round(lag_ms, 2))

    async def record_event_loop_lag_async(self, lag_ms: float):
        """Record an event loop lag sample asynchronously (non-blocking)."""
        # Offload to thread pool to avoid blocking event loop
        await asyncio.to_thread(self.record_event_loop_lag, lag_ms)

    async def record_request_complete_async(
        self,
        provider: str,
        model: str,
        start_time: float,
        success: bool,
        error_type: Optional[str] = None,
        stream: bool = False
    ):
        """Record a completed request asynchronously (non-blocking)."""
        # Offload to thread pool to avoid blocking event loop
        await asyncio.to_thread(
            self.record_request_complete,
            provider, model, start_time, success, error_type, stream
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics for dashboard and API.

        Results are cached for 5s to avoid expensive cache.iterkeys() scans.
        """
        now = time.time()
        if self._cached_stats and (now - self._stats_last_computed) < self._stats_cache_ttl:
            # Return cached stats (avoid expensive iterkeys() scan)
            return self._cached_stats

        # Compute fresh stats
        stats = self._compute_stats()

        # Cache the result
        self._cached_stats = stats
        self._stats_last_computed = now

        return stats

    def _compute_stats(self) -> Dict[str, Any]:
        """Internal method to compute stats (expensive)."""
        # Get basic counters
        total_requests = self._get("total_requests", 0)
        total_success = self._get("total_success", 0)
        total_errors = self._get("total_errors", 0)
        total_fallbacks = self._get("total_fallbacks", 0)

        # Calculate rates
        success_rate = (total_success / total_requests * 100) if total_requests > 0 else 0
        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0

        # Provider stats
        providers = {}
        for provider_name in ["anthropic", "bedrock", "none"]:
            providers[provider_name] = {
                "requests": self._get(f"provider:{provider_name}:requests", 0),
                "success": self._get(f"provider:{provider_name}:success", 0),
                "errors": self._get(f"provider:{provider_name}:errors", 0)
            }

        # Top models (scan all model: keys)
        model_stats = {}
        for key in self.cache.iterkeys():
            if isinstance(key, str) and key.startswith("model:") and key.endswith(":requests"):
                model_name = key[6:-9]  # Extract model name from "model:X:requests"
                count = self._get(key, 0)
                if count > 0:
                    model_stats[model_name] = count

        # Sort by count and take top 10
        top_models = dict(sorted(model_stats.items(), key=lambda x: x[1], reverse=True)[:10])

        # Error types
        error_types = {}
        for key in self.cache.iterkeys():
            if isinstance(key, str) and key.startswith("error_type:"):
                error_type = key[11:]  # Extract type from "error_type:X"
                count = self._get(key, 0)
                if count > 0:
                    error_types[error_type] = count

        # Duration distribution
        duration_distribution = {
            "< 1s": self._get("duration:lt1s", 0),
            "1-5s": self._get("duration:1_5s", 0),
            "5-30s": self._get("duration:5_30s", 0),
            "30-60s": self._get("duration:30_60s", 0),
            "> 60s": self._get("duration:gt60s", 0)
        }

        # Fallback reasons
        fallback_reasons = {}
        for key in self.cache.iterkeys():
            if isinstance(key, str) and key.startswith("fallback_reason:"):
                reason = key[16:]  # Extract reason from "fallback_reason:X"
                count = self._get(key, 0)
                if count > 0:
                    fallback_reasons[reason] = count

        # RPM data for last 15 minutes
        rpm_data = []
        now = datetime.now()
        for i in range(15, -1, -1):  # 15 minutes ago to now
            minute = now - timedelta(minutes=i)
            minute_key = minute.strftime("rpm:%Y-%m-%dT%H:%M")
            count = self._get(minute_key, 0)
            rpm_data.append({
                "minute": minute.strftime("%H:%M"),
                "requests": count
            })

        # Event loop lag history for last 15 minutes
        lag_data = []
        for i in range(15, -1, -1):
            minute = now - timedelta(minutes=i)
            minute_key = minute.strftime("%Y-%m-%dT%H:%M")
            max_int = self._get(f"lag:{minute_key}:max", 0)
            sum_int = self._get(f"lag:{minute_key}:sum", 0)
            count = self._get(f"lag:{minute_key}:count", 0)
            lag_data.append({
                "minute": minute.strftime("%H:%M"),
                "max_ms": round(max_int / 100, 2),
                "avg_ms": round(sum_int / 100 / count, 2) if count > 0 else 0
            })

        current_lag_ms = self._get("lag:current_ms", 0.0)

        # Recent errors (from in-memory deque)
        recent_errors = list(self.recent_errors)

        return {
            "summary": {
                "total_requests": total_requests,
                "total_success": total_success,
                "total_errors": total_errors,
                "total_fallbacks": total_fallbacks,
                "success_rate": round(success_rate, 2),
                "error_rate": round(error_rate, 2)
            },
            "providers": providers,
            "models": top_models,
            "error_types": error_types,
            "duration_distribution": duration_distribution,
            "fallback_reasons": fallback_reasons,
            "rpm_data": rpm_data,
            "lag_data": lag_data,
            "current_lag_ms": current_lag_ms,
            "recent_errors": recent_errors,
            "timestamp": datetime.now().isoformat()
        }
