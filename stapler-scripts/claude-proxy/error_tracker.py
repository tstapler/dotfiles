"""Error tracking and deduplication for claude-proxy.

This module provides:
- Error signature extraction and normalization
- Fingerprinting for error deduplication
- Persistent storage via SQLite
- Custom logging handler integration
- macOS desktop notifications for new errors
"""

import hashlib
import json
import logging
import re
import sqlite3
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple


logger = logging.getLogger(__name__)


# =============================================================================
# Story 1: Core Error Fingerprinting
# =============================================================================


def extract_signature(error_message: str, provider: Optional[str] = None,
                     request_context: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Extract stable signature components from error message.

    Parses error messages in various formats to extract:
    - provider: Provider name (e.g., 'bedrock', 'anthropic')
    - operation: API operation (e.g., 'InvokeModel')
    - error_type: Exception type (e.g., 'ValidationException', 'RateLimitError')
    - message: Error message content (normalized)

    Args:
        error_message: Raw error message from logs
        provider: Optional provider name from context
        request_context: Optional dict with additional context (model, request_id, etc.)

    Returns:
        Dict with keys: provider, operation, error_type, message

    Examples:
        >>> extract_signature("Bedrock validation error: An error occurred (ValidationException) when calling the InvokeModel operation: context_management: Extra inputs not permitted")
        {'provider': 'bedrock', 'operation': 'InvokeModel', 'error_type': 'ValidationException',
         'message': 'context_management: Extra inputs not permitted'}

        >>> extract_signature("Rate limit exceeded for model claude-opus-4-6")
        {'provider': 'unknown', 'operation': 'unknown', 'error_type': 'RateLimitError',
         'message': 'Rate limit exceeded for model claude-opus-4-6'}
    """
    # Initialize with defaults
    signature = {
        'provider': provider or 'unknown',
        'operation': 'unknown',
        'error_type': 'unknown',
        'message': error_message
    }

    # Pattern 1: Bedrock AWS SDK format
    # "Bedrock validation error: An error occurred (ValidationException) when calling the InvokeModel operation: message"
    bedrock_pattern = r'(?:Bedrock\s+)?(?:validation\s+)?(?:error:\s+)?An error occurred \((\w+)\) when calling the (\w+) operation:?\s*(.+)'
    match = re.search(bedrock_pattern, error_message, re.IGNORECASE)
    if match:
        signature['provider'] = 'bedrock'
        signature['error_type'] = match.group(1)  # ValidationException
        signature['operation'] = match.group(2)   # InvokeModel
        signature['message'] = match.group(3).strip()  # Actual error message
        return signature

    # Pattern 2: Bedrock simple format
    # "Bedrock: ThrottlingException - Rate exceeded"
    bedrock_simple = r'(?:Bedrock|bedrock):?\s+(\w+(?:Exception|Error))\s*[-:]\s*(.+)'
    match = re.search(bedrock_simple, error_message, re.IGNORECASE)
    if match:
        signature['provider'] = 'bedrock'
        signature['error_type'] = match.group(1)
        signature['message'] = match.group(2).strip()
        return signature

    # Pattern 3: Rate limit errors
    # "Rate limit exceeded for model claude-opus-4-6"
    if 'rate limit' in error_message.lower():
        signature['error_type'] = 'RateLimitError'
        signature['message'] = error_message
        return signature

    # Pattern 4: Timeout errors
    # "Request timeout after 30s"
    if 'timeout' in error_message.lower():
        signature['error_type'] = 'TimeoutError'
        signature['message'] = error_message
        return signature

    # Pattern 5: Authentication errors
    # "Authentication failed: Invalid API key"
    if 'authentication' in error_message.lower() or 'auth' in error_message.lower():
        signature['error_type'] = 'AuthenticationError'
        signature['message'] = error_message
        return signature

    # Pattern 6: Generic exception format (last resort)
    # "SomeException: message"
    generic_pattern = r'(\w+(?:Exception|Error)):?\s*(.+)'
    match = re.search(generic_pattern, error_message)
    if match:
        signature['error_type'] = match.group(1)
        signature['message'] = match.group(2).strip()
        return signature

    # Fallback: Use the full message as-is
    return signature


def normalize_message(message: str) -> str:
    """Normalize dynamic content in error messages to enable stable fingerprinting.

    Replaces:
    - UUIDs → <UUID>
    - AWS ARNs → <MODEL_ARN>
    - Long numeric IDs (>10 digits) → <ID>
    - Request IDs → <REQUEST_ID>

    Preserves:
    - Short numbers (tokens, counts, etc.) — semantic meaning
    - Error codes (HTTP status codes, etc.)
    - Timestamps (semantic meaning)

    Args:
        message: Raw error message

    Returns:
        Normalized message with dynamic content replaced

    Examples:
        >>> normalize_message("Request abc-123-def-456 failed")
        'Request <UUID> failed'

        >>> normalize_message("Model arn:aws:bedrock:us-east-1:123456789:model/claude-v2 not found")
        'Model <MODEL_ARN> not found'

        >>> normalize_message("Maximum tokens 4096 exceeded")
        'Maximum tokens 4096 exceeded'  # Preserve semantic numbers
    """
    # Tool use IDs: toolu_bdrk_01XXXXX, toolu_01XXXXX (Anthropic/Bedrock tool IDs)
    normalized = re.sub(
        r'\btoolu_(?:bdrk_)?[0-9a-zA-Z]+',
        '<TOOL_ID>',
        message
    )

    # UUID pattern: 8-4-4-4-12 hex digits
    normalized = re.sub(
        r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b',
        '<UUID>',
        normalized
    )

    # AWS ARN pattern: arn:aws:service:region:account:resource
    normalized = re.sub(
        r'arn:aws:[a-z0-9-]+:[a-z0-9-]*:\d+:[a-zA-Z0-9/._-]+',
        '<MODEL_ARN>',
        normalized
    )

    # Long numeric IDs (>10 digits, likely dynamic IDs not semantic numbers)
    # But avoid replacing standalone small numbers (token counts, HTTP codes, etc.)
    normalized = re.sub(
        r'\b\d{11,}\b',
        '<ID>',
        normalized
    )

    # Request ID patterns (common formats)
    normalized = re.sub(
        r'\brequest[_\s]?id[:\s]+[a-zA-Z0-9-]+',
        'request_id <REQUEST_ID>',
        normalized,
        flags=re.IGNORECASE
    )

    # Hexadecimal IDs (often used as request/trace IDs)
    normalized = re.sub(
        r'\b[0-9a-fA-F]{16,}\b',
        '<HEX_ID>',
        normalized
    )

    return normalized


def compute_fingerprint(signature: Dict[str, str]) -> str:
    """Compute stable hash fingerprint from error signature.

    Creates SHA256 hash of: provider + operation + error_type + normalized_message
    Returns first 16 characters for brevity.

    Args:
        signature: Dict with keys provider, operation, error_type, message

    Returns:
        16-character hex fingerprint

    Examples:
        >>> sig = {'provider': 'bedrock', 'operation': 'InvokeModel',
        ...        'error_type': 'ValidationException', 'message': 'Extra inputs'}
        >>> compute_fingerprint(sig)
        'a1b2c3d4e5f67890'  # Example (actual hash will differ)
    """
    # Normalize message before hashing
    normalized_msg = normalize_message(signature['message'])

    # Combine components in stable order
    fingerprint_input = (
        f"{signature['provider']}:"
        f"{signature['operation']}:"
        f"{signature['error_type']}:"
        f"{normalized_msg}"
    )

    # Compute SHA256 and take first 16 chars
    hash_obj = hashlib.sha256(fingerprint_input.encode('utf-8'))
    return hash_obj.hexdigest()[:16]


# =============================================================================
# Story 2: Persistent Storage
# =============================================================================


class ErrorTracker:
    """Persistent error tracking with SQLite storage.

    Manages:
    - Two-tier schema (error_types + error_occurrences)
    - Error fingerprinting and deduplication
    - 90-day retention policy
    - Query capabilities
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize error tracker with SQLite database.

        Args:
            db_path: Path to SQLite database file.
                     Defaults to ~/.cache/claude-proxy/error_tracker.db
        """
        if db_path is None:
            cache_dir = Path.home() / '.cache' / 'claude-proxy'
            cache_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(cache_dir / 'error_tracker.db')

        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database schema with WAL mode enabled."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Enable WAL mode for better concurrency
        cursor.execute("PRAGMA journal_mode=WAL")

        # Create error_types table (summary data, deduplication)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_types (
                fingerprint TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                operation TEXT NOT NULL,
                error_type TEXT NOT NULL,
                message TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create error_occurrences table (detailed history)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_occurrences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                request_id TEXT,
                model TEXT,
                context TEXT,  -- JSON blob for additional context
                FOREIGN KEY (fingerprint) REFERENCES error_types(fingerprint)
            )
        """)

        # Create indexes for query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_occurrences_timestamp
            ON error_occurrences(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_occurrences_fingerprint
            ON error_occurrences(fingerprint)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_error_types_provider
            ON error_types(provider)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_error_types_last_seen
            ON error_types(last_seen)
        """)

        conn.commit()
        conn.close()

        logger.info(f"Error tracker database initialized: {self.db_path}")

    def record_error(self, signature: Dict[str, str],
                    context: Optional[Dict[str, Any]] = None) -> Tuple[str, bool]:
        """Record error occurrence and return fingerprint + is_new flag.

        Args:
            signature: Dict with keys: provider, operation, error_type, message
            context: Optional dict with request_id, model, and other context

        Returns:
            Tuple of (fingerprint, is_new)
            - fingerprint: 16-character hex fingerprint
            - is_new: True if this is the first occurrence of this error type

        Examples:
            >>> tracker = ErrorTracker()
            >>> sig = extract_signature("Bedrock: ValidationException - Extra inputs")
            >>> fp, is_new = tracker.record_error(sig, {'request_id': 'abc123', 'model': 'claude-opus'})
            >>> print(f"Fingerprint: {fp}, New: {is_new}")
            Fingerprint: a1b2c3d4e5f67890, New: True
        """
        # Compute fingerprint
        fingerprint = compute_fingerprint(signature)
        timestamp = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if error type already exists
        cursor.execute("SELECT count FROM error_types WHERE fingerprint = ?", (fingerprint,))
        existing = cursor.fetchone()
        is_new = existing is None

        if is_new:
            # First occurrence - insert new error type
            cursor.execute("""
                INSERT INTO error_types
                (fingerprint, provider, operation, error_type, message, first_seen, last_seen, count)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                fingerprint,
                signature['provider'],
                signature['operation'],
                signature['error_type'],
                signature['message'],
                timestamp,
                timestamp
            ))
        else:
            # Update existing error type (increment count, update last_seen)
            cursor.execute("""
                UPDATE error_types
                SET count = count + 1,
                    last_seen = ?
                WHERE fingerprint = ?
            """, (timestamp, fingerprint))

        # Insert occurrence record
        context_json = json.dumps(context) if context else None
        cursor.execute("""
            INSERT INTO error_occurrences
            (fingerprint, timestamp, request_id, model, context)
            VALUES (?, ?, ?, ?, ?)
        """, (
            fingerprint,
            timestamp,
            context.get('request_id') if context else None,
            context.get('model') if context else None,
            context_json
        ))

        conn.commit()
        conn.close()

        return fingerprint, is_new

    def get_error_by_fingerprint(self, fingerprint: str) -> Optional[Dict[str, Any]]:
        """Retrieve error details by fingerprint.

        Args:
            fingerprint: 16-character hex fingerprint

        Returns:
            Dict with error details or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM error_types WHERE fingerprint = ?
        """, (fingerprint,))

        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return dict(row)

    def search_errors(self, provider: Optional[str] = None,
                     since: Optional[str] = None,
                     limit: int = 100) -> List[Dict[str, Any]]:
        """Search errors with optional filters.

        Args:
            provider: Filter by provider name (e.g., 'bedrock', 'anthropic')
            since: ISO timestamp - only return errors since this time
            limit: Maximum number of results

        Returns:
            List of error dicts sorted by last_seen (descending)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build query with optional filters
        query = "SELECT * FROM error_types WHERE 1=1"
        params = []

        if provider:
            query += " AND provider = ?"
            params.append(provider)

        if since:
            query += " AND last_seen >= ?"
            params.append(since)

        query += " ORDER BY last_seen DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def prune_old_occurrences(self, max_age_days: int = 90) -> int:
        """Delete error occurrences older than max_age_days.

        Keeps error_types intact (summary data), only prunes detailed occurrences.

        Args:
            max_age_days: Maximum age in days (default: 90)

        Returns:
            Number of occurrences deleted
        """
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        cutoff_iso = cutoff_date.isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM error_occurrences WHERE timestamp < ?
        """, (cutoff_iso,))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"Pruned {deleted} error occurrences older than {max_age_days} days")
        return deleted


# =============================================================================
# Story 4: Alert Delivery (defined before Story 3 to avoid forward reference)
# =============================================================================


class AlertManager:
    """Manages desktop notifications for new errors with cooldown logic."""

    def __init__(self, cooldown_seconds: int = 300):
        """Initialize alert manager.

        Args:
            cooldown_seconds: Minimum time between alerts for same fingerprint (default: 5 minutes)
        """
        self.cooldown_seconds = cooldown_seconds
        self._alert_cache: Dict[str, float] = {}  # fingerprint -> last_alert_timestamp

    def should_alert(self, fingerprint: str) -> bool:
        """Check if alert should be sent (respects cooldown).

        Args:
            fingerprint: Error fingerprint

        Returns:
            True if alert should be sent (not in cooldown)
        """
        now = time.time()
        last_alert = self._alert_cache.get(fingerprint)

        if last_alert is None:
            return True  # Never alerted before

        elapsed = now - last_alert
        return elapsed >= self.cooldown_seconds

    def record_alert(self, fingerprint: str) -> None:
        """Record that alert was sent.

        Args:
            fingerprint: Error fingerprint
        """
        self._alert_cache[fingerprint] = time.time()

    def send_desktop_notification(self, fingerprint: str, signature: Dict[str, str]) -> None:
        """Send macOS desktop notification for new error.

        Args:
            fingerprint: Error fingerprint
            signature: Error signature dict with provider, error_type, message
        """
        # Check cooldown
        if not self.should_alert(fingerprint):
            logger.debug(f"Alert cooldown active for {fingerprint}")
            return

        # Build notification
        title = f"New Error: {signature['provider']}"
        message = f"{signature['error_type']}: {signature['message'][:100]}"
        if len(signature['message']) > 100:
            message += "..."

        # Execute osascript (non-blocking, with timeout)
        try:
            result = subprocess.run(
                ['osascript', '-e', f'display notification "{message}" with title "{title}"'],
                timeout=2,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.info(f"🔔 Alert sent: {fingerprint}")
                self.record_alert(fingerprint)
            else:
                logger.warning(f"Alert command failed for {fingerprint}: {result.stderr}")

        except subprocess.TimeoutExpired:
            logger.warning(f"Alert timeout for {fingerprint}")
        except Exception as e:
            logger.error(f"Alert failed for {fingerprint}: {e}")


# =============================================================================
# Story 3: Logging Integration
# =============================================================================


class ErrorTrackingHandler(logging.Handler):
    """Custom logging handler that captures ERROR+ logs and tracks errors.

    Integrates with existing logging infrastructure to:
    - Intercept ERROR and CRITICAL level logs
    - Extract error signatures and context
    - Record to persistent storage
    - Trigger alerts for new error types (Story 4)
    """

    def __init__(self, tracker: ErrorTracker, alert_manager: Optional[AlertManager] = None,
                 level: int = logging.ERROR):
        """Initialize handler with error tracker.

        Args:
            tracker: ErrorTracker instance for persistence
            alert_manager: Optional AlertManager for notifications (default: creates new one)
            level: Logging level threshold (default: ERROR)
        """
        super().__init__(level=level)
        self.tracker = tracker
        self.alert_manager = alert_manager or AlertManager()
        self._recursion_guard = 0

    def _parse_error_log_record(self, record: logging.LogRecord) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Parse log record to extract request_id, provider, and model.

        Expected format:
        [request_id] ✗ provider: error_type (model=model_name) - message
        OR
        [request_id] ✗ provider (model=model_name): message

        Args:
            record: LogRecord from logging system

        Returns:
            Tuple of (request_id, provider, model) or (None, None, None) if parsing fails
        """
        message = record.getMessage()

        # Pattern 1: [request_id] ✗ provider: error_type (model=model) - message
        pattern1 = r'\[([a-f0-9]{8})\] ✗ (\w+):.+\(model=([^)]+)\)'
        match = re.search(pattern1, message)
        if match:
            return match.group(1), match.group(2), match.group(3)

        # Pattern 2: [request_id] ✗ provider (model=model): message
        pattern2 = r'\[([a-f0-9]{8})\] ✗ (\w+) \(model=([^)]+)\)'
        match = re.search(pattern2, message)
        if match:
            return match.group(1), match.group(2), match.group(3)

        # No match - return None
        return None, None, None

    def emit(self, record: logging.LogRecord) -> None:
        """Handle log record by extracting error signature and recording.

        Args:
            record: LogRecord from logging system
        """
        # Guard against circular logging (if our code logs errors)
        if self._recursion_guard > 0:
            return

        # Ignore our own internal logs to prevent circular logging
        if record.name.startswith('error_tracker'):
            return

        self._recursion_guard += 1

        try:
            # Only process error logs with ✗ symbol (actual errors)
            message = record.getMessage()
            if '✗' not in message:
                return

            # Extract context from log record
            request_id, provider, model = self._parse_error_log_record(record)

            # Extract error signature from message
            # Remove the prefix part ([request_id] ✗ provider (model=...) to get the actual error message
            error_message = message

            # Try to strip the prefix to get just the error message
            # Pattern 1: [request_id] ✗ provider: error_type (model=model) - MESSAGE
            pattern1 = r'\[[a-zA-Z0-9]{8}\] ✗ \w+:\s*[^(]+\([^)]+\)\s*-\s*(.+)'
            match = re.search(pattern1, message)
            if match:
                error_message = match.group(1)
            else:
                # Pattern 2: [request_id] ✗ provider (model=model): MESSAGE
                pattern2 = r'\[[a-zA-Z0-9]{8}\] ✗ \w+\s*\([^)]+\):\s*(.+)'
                match = re.search(pattern2, message)
                if match:
                    error_message = match.group(1)

            # Extract signature
            signature = extract_signature(error_message, provider=provider)

            # Build context
            context = {
                'request_id': request_id,
                'model': model,
                'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                'level': record.levelname,
                'module': record.module,
            }

            # Record error
            fingerprint, is_new = self.tracker.record_error(signature, context)

            # Log that we captured the error (DEBUG level)
            logger.debug(f"Captured error: {fingerprint} (new: {is_new})")

            # If new error, trigger alert
            if is_new:
                self.alert_manager.send_desktop_notification(fingerprint, signature)

        except Exception as e:
            # Never let handler exceptions break logging
            # Log to stderr (not logging module) to avoid circular logging
            import sys
            print(f"ERROR: ErrorTrackingHandler failed: {e}", file=sys.stderr)

        finally:
            self._recursion_guard -= 1


# Note: AlertManager moved before ErrorTrackingHandler to fix forward reference


# =============================================================================
# Story 5: Query CLI
# =============================================================================

# TODO: CLI will be in separate scripts/error_cli.py file (Story 5)
