"""Tests for error_tracker module."""

import pytest
import time
import sqlite3
import tempfile
import logging
from pathlib import Path
from datetime import datetime, timedelta
from error_tracker import extract_signature, normalize_message, compute_fingerprint, ErrorTracker, ErrorTrackingHandler


# =============================================================================
# Story 1, Task 1.1: Signature Extraction Tests
# =============================================================================


def test_extract_signature_bedrock_validation():
    """Test parsing Bedrock ValidationException format."""
    message = (
        "Bedrock validation error: An error occurred (ValidationException) "
        "when calling the InvokeModel operation: context_management: Extra inputs not permitted"
    )
    sig = extract_signature(message)

    assert sig['provider'] == 'bedrock'
    assert sig['operation'] == 'InvokeModel'
    assert sig['error_type'] == 'ValidationException'
    assert sig['message'] == 'context_management: Extra inputs not permitted'


def test_extract_signature_bedrock_throttling():
    """Test parsing Bedrock ThrottlingException format."""
    message = (
        "An error occurred (ThrottlingException) when calling the InvokeModel operation: "
        "Rate exceeded"
    )
    sig = extract_signature(message)

    assert sig['provider'] == 'bedrock'
    assert sig['operation'] == 'InvokeModel'
    assert sig['error_type'] == 'ThrottlingException'
    assert sig['message'] == 'Rate exceeded'


def test_extract_signature_bedrock_simple():
    """Test parsing simple Bedrock error format."""
    message = "Bedrock: ThrottlingException - Rate limit exceeded"
    sig = extract_signature(message)

    assert sig['provider'] == 'bedrock'
    assert sig['error_type'] == 'ThrottlingException'
    assert sig['message'] == 'Rate limit exceeded'


def test_extract_signature_rate_limit():
    """Test parsing rate limit errors."""
    message = "Rate limit exceeded for model claude-opus-4-6"
    sig = extract_signature(message)

    assert sig['error_type'] == 'RateLimitError'
    assert 'claude-opus-4-6' in sig['message']


def test_extract_signature_timeout():
    """Test parsing timeout errors."""
    message = "Request timeout after 30s (provider=bedrock)"
    sig = extract_signature(message)

    assert sig['error_type'] == 'TimeoutError'
    assert 'timeout' in sig['message'].lower()


def test_extract_signature_auth():
    """Test parsing authentication errors."""
    message = "Authentication failed: Invalid API key"
    sig = extract_signature(message)

    assert sig['error_type'] == 'AuthenticationError'
    assert 'Invalid API key' in sig['message']


def test_extract_signature_generic():
    """Test parsing generic exception format."""
    message = "SomeException: Something went wrong"
    sig = extract_signature(message)

    assert sig['error_type'] == 'SomeException'
    assert sig['message'] == 'Something went wrong'


def test_extract_signature_malformed():
    """Test handling malformed messages with graceful fallback."""
    message = "Something broke"
    sig = extract_signature(message)

    assert sig['provider'] == 'unknown'
    assert sig['operation'] == 'unknown'
    assert sig['error_type'] == 'unknown'
    assert sig['message'] == message


def test_extract_signature_empty():
    """Test handling empty messages."""
    sig = extract_signature("")

    assert sig['provider'] == 'unknown'
    assert sig['operation'] == 'unknown'
    assert sig['error_type'] == 'unknown'
    assert sig['message'] == ""


def test_extract_signature_unicode():
    """Test handling Unicode characters."""
    message = "Erreur: échec de l'opération"
    sig = extract_signature(message)

    # Should handle gracefully (fallback to generic)
    assert sig['message'] == message


# =============================================================================
# Story 1, Task 1.2: Normalization Tests
# =============================================================================


def test_normalize_message_uuid():
    """Test UUID normalization."""
    message = "Request abc-123-def-456 failed: ValidationException"
    normalized = normalize_message(message)

    # UUIDs are not in standard format, but hexadecimal IDs might be normalized
    # This depends on regex patterns - let's test actual UUID format
    message_with_uuid = "Request 550e8400-e29b-41d4-a716-446655440000 failed"
    normalized = normalize_message(message_with_uuid)
    assert '<UUID>' in normalized
    assert '550e8400-e29b-41d4-a716-446655440000' not in normalized


def test_normalize_message_arn():
    """Test AWS ARN normalization."""
    message = "Model arn:aws:bedrock:us-east-1:123456789:model/claude-v2 not found"
    normalized = normalize_message(message)

    assert '<MODEL_ARN>' in normalized
    assert 'arn:aws:bedrock' not in normalized


def test_normalize_message_long_id():
    """Test long numeric ID normalization."""
    message = "Request ID 98765432109876543210 timed out"
    normalized = normalize_message(message)

    assert '<ID>' in normalized
    assert '98765432109876543210' not in normalized


def test_normalize_message_preserve_short_numbers():
    """Test that short numbers (semantic) are preserved."""
    message = "Maximum tokens 4096 exceeded"
    normalized = normalize_message(message)

    # Should preserve 4096 (semantic token count)
    assert '4096' in normalized
    assert message == normalized


def test_normalize_message_request_id():
    """Test request ID pattern normalization."""
    message = "Request ID: abc123def456 failed"
    normalized = normalize_message(message)

    assert '<REQUEST_ID>' in normalized


def test_normalize_message_hex_id():
    """Test hexadecimal ID normalization."""
    message = "Trace ID: 1234567890abcdef1234 for request"
    normalized = normalize_message(message)

    assert '<HEX_ID>' in normalized
    assert '1234567890abcdef1234' not in normalized


def test_normalize_message_tool_ids():
    """Test tool use ID normalization."""
    # Bedrock tool ID
    message1 = "unexpected tool_use_id found: toolu_bdrk_01GcFxHwaGd"
    normalized1 = normalize_message(message1)
    assert '<TOOL_ID>' in normalized1
    assert 'toolu_bdrk_01GcFxHwaGd' not in normalized1

    # Anthropic tool ID
    message2 = "unexpected tool_use_id found: toolu_01AbcXyz123"
    normalized2 = normalize_message(message2)
    assert '<TOOL_ID>' in normalized2
    assert 'toolu_01AbcXyz123' not in normalized2

    # Multiple tool IDs
    message3 = "toolu_bdrk_01ABC and toolu_01XYZ both failed"
    normalized3 = normalize_message(message3)
    assert normalized3.count('<TOOL_ID>') == 2


def test_normalize_message_multiple_patterns():
    """Test normalization with multiple dynamic patterns."""
    message = (
        "Request 550e8400-e29b-41d4-a716-446655440000 for "
        "arn:aws:bedrock:us-east-1:123:model/claude failed with ID 12345678901234"
    )
    normalized = normalize_message(message)

    assert '<UUID>' in normalized
    assert '<MODEL_ARN>' in normalized
    assert '<ID>' in normalized


# =============================================================================
# Story 1, Task 1.2: Fingerprinting Tests
# =============================================================================


def test_compute_fingerprint_determinism():
    """Test that same signature produces same fingerprint."""
    sig = {
        'provider': 'bedrock',
        'operation': 'InvokeModel',
        'error_type': 'ValidationException',
        'message': 'context_management: Extra inputs not permitted'
    }

    # Compute fingerprint 10 times
    fingerprints = [compute_fingerprint(sig) for _ in range(10)]

    # All should be identical
    assert len(set(fingerprints)) == 1
    assert len(fingerprints[0]) == 16  # 16-character hex string
    assert all(c in '0123456789abcdef' for c in fingerprints[0])


def test_compute_fingerprint_different_messages():
    """Test that different errors produce different fingerprints."""
    sig1 = {
        'provider': 'bedrock',
        'operation': 'InvokeModel',
        'error_type': 'ValidationException',
        'message': 'context_management: Extra inputs'
    }

    sig2 = {
        'provider': 'bedrock',
        'operation': 'InvokeModel',
        'error_type': 'ThrottlingException',
        'message': 'Rate exceeded'
    }

    fp1 = compute_fingerprint(sig1)
    fp2 = compute_fingerprint(sig2)

    assert fp1 != fp2


def test_compute_fingerprint_normalizes_dynamic_content():
    """Test that fingerprint is stable across dynamic content."""
    sig1 = {
        'provider': 'bedrock',
        'operation': 'InvokeModel',
        'error_type': 'ValidationException',
        'message': 'Request 550e8400-e29b-41d4-a716-446655440000 failed'
    }

    sig2 = {
        'provider': 'bedrock',
        'operation': 'InvokeModel',
        'error_type': 'ValidationException',
        'message': 'Request 661f9511-f3ac-52e5-b827-557766551111 failed'
    }

    fp1 = compute_fingerprint(sig1)
    fp2 = compute_fingerprint(sig2)

    # Different UUIDs should produce same fingerprint (normalized to <UUID>)
    assert fp1 == fp2


def test_compute_fingerprint_normalizes_tool_ids():
    """Test that fingerprint is stable across different tool IDs."""
    sig1 = {
        'provider': 'bedrock',
        'operation': 'InvokeModel',
        'error_type': 'ValidationException',
        'message': 'unexpected tool_use_id found: toolu_bdrk_01GcFxHwaGd'
    }

    sig2 = {
        'provider': 'bedrock',
        'operation': 'InvokeModel',
        'error_type': 'ValidationException',
        'message': 'unexpected tool_use_id found: toolu_bdrk_01S5WbKp3RP'
    }

    fp1 = compute_fingerprint(sig1)
    fp2 = compute_fingerprint(sig2)

    # Different tool IDs should produce same fingerprint (normalized to <TOOL_ID>)
    assert fp1 == fp2, f"Expected same fingerprint for tool ID errors, got {fp1} vs {fp2}"


def test_compute_fingerprint_performance():
    """Test that fingerprint computation is fast (<100µs)."""
    sig = {
        'provider': 'bedrock',
        'operation': 'InvokeModel',
        'error_type': 'ValidationException',
        'message': 'Some error message'
    }

    # Warm up
    compute_fingerprint(sig)

    # Measure 100 iterations
    start = time.perf_counter()
    for _ in range(100):
        compute_fingerprint(sig)
    elapsed = time.perf_counter() - start

    # Average should be <100µs per fingerprint
    avg_time_us = (elapsed / 100) * 1_000_000
    assert avg_time_us < 100, f"Average fingerprint time: {avg_time_us:.1f}µs (target: <100µs)"


# =============================================================================
# Integration Tests
# =============================================================================


def test_extract_and_fingerprint_integration():
    """Test end-to-end: extract signature → normalize → fingerprint."""
    error_message = (
        "Bedrock validation error: An error occurred (ValidationException) "
        "when calling the InvokeModel operation: Request 550e8400-e29b-41d4-a716-446655440000 "
        "failed for model arn:aws:bedrock:us-east-1:123:model/claude-v2"
    )

    # Extract signature
    sig = extract_signature(error_message)
    assert sig['provider'] == 'bedrock'
    assert sig['error_type'] == 'ValidationException'

    # Compute fingerprint
    fp = compute_fingerprint(sig)
    assert len(fp) == 16

    # Same error with different dynamic content should produce same fingerprint
    error_message2 = error_message.replace(
        '550e8400-e29b-41d4-a716-446655440000',
        '661f9511-f3ac-52e5-b827-557766551111'
    ).replace(
        'arn:aws:bedrock:us-east-1:123:model/claude-v2',
        'arn:aws:bedrock:us-west-2:456:model/claude-v3'
    )

    sig2 = extract_signature(error_message2)
    fp2 = compute_fingerprint(sig2)

    assert fp == fp2, "Same logical error should produce same fingerprint"


# =============================================================================
# Story 2: Persistent Storage Tests
# =============================================================================


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    yield db_path
    Path(db_path).unlink(missing_ok=True)


def test_error_tracker_init(temp_db):
    """Test database initialization."""
    tracker = ErrorTracker(temp_db)

    # Check that database file exists
    assert Path(temp_db).exists()

    # Check that tables were created
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    # Check error_types table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='error_types'")
    assert cursor.fetchone() is not None

    # Check error_occurrences table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='error_occurrences'")
    assert cursor.fetchone() is not None

    # Check indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = [row[0] for row in cursor.fetchall()]
    assert 'idx_occurrences_timestamp' in indexes
    assert 'idx_occurrences_fingerprint' in indexes
    assert 'idx_error_types_provider' in indexes
    assert 'idx_error_types_last_seen' in indexes

    # Check WAL mode
    cursor.execute("PRAGMA journal_mode")
    journal_mode = cursor.fetchone()[0]
    assert journal_mode.lower() == 'wal'

    conn.close()


def test_record_error_new(temp_db):
    """Test recording a new error."""
    tracker = ErrorTracker(temp_db)

    sig = {
        'provider': 'bedrock',
        'operation': 'InvokeModel',
        'error_type': 'ValidationException',
        'message': 'context_management: Extra inputs'
    }
    context = {'request_id': 'abc123', 'model': 'claude-opus-4-6'}

    fp, is_new = tracker.record_error(sig, context)

    # Check return values
    assert len(fp) == 16
    assert is_new is True

    # Check database
    error = tracker.get_error_by_fingerprint(fp)
    assert error is not None
    assert error['provider'] == 'bedrock'
    assert error['error_type'] == 'ValidationException'
    assert error['count'] == 1


def test_record_error_duplicate(temp_db):
    """Test that duplicate errors increment count."""
    tracker = ErrorTracker(temp_db)

    sig = {
        'provider': 'bedrock',
        'operation': 'InvokeModel',
        'error_type': 'ValidationException',
        'message': 'context_management: Extra inputs'
    }

    # First occurrence
    fp1, is_new1 = tracker.record_error(sig, {'request_id': 'req1'})
    assert is_new1 is True

    # Second occurrence
    fp2, is_new2 = tracker.record_error(sig, {'request_id': 'req2'})
    assert is_new2 is False
    assert fp1 == fp2  # Same fingerprint

    # Check that count was incremented
    error = tracker.get_error_by_fingerprint(fp1)
    assert error['count'] == 2

    # Check that both occurrences were stored
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM error_occurrences WHERE fingerprint = ?", (fp1,))
    occurrence_count = cursor.fetchone()[0]
    assert occurrence_count == 2
    conn.close()


def test_get_error_by_fingerprint_not_found(temp_db):
    """Test retrieving non-existent error."""
    tracker = ErrorTracker(temp_db)

    error = tracker.get_error_by_fingerprint('nonexistent1234')
    assert error is None


def test_search_errors_no_filter(temp_db):
    """Test searching all errors."""
    tracker = ErrorTracker(temp_db)

    # Record 3 different errors
    sig1 = extract_signature("Bedrock: ValidationException - Error 1")
    sig2 = extract_signature("Bedrock: ThrottlingException - Error 2")
    sig3 = extract_signature("Rate limit exceeded")

    tracker.record_error(sig1)
    tracker.record_error(sig2)
    tracker.record_error(sig3)

    # Search all
    results = tracker.search_errors()
    assert len(results) == 3


def test_search_errors_by_provider(temp_db):
    """Test searching errors by provider."""
    tracker = ErrorTracker(temp_db)

    # Record errors from different providers
    sig1 = {'provider': 'bedrock', 'operation': 'InvokeModel', 'error_type': 'ValidationException', 'message': 'Error 1'}
    sig2 = {'provider': 'anthropic', 'operation': 'unknown', 'error_type': 'RateLimitError', 'message': 'Error 2'}

    tracker.record_error(sig1)
    tracker.record_error(sig2)

    # Search by provider
    bedrock_errors = tracker.search_errors(provider='bedrock')
    assert len(bedrock_errors) == 1
    assert bedrock_errors[0]['provider'] == 'bedrock'

    anthropic_errors = tracker.search_errors(provider='anthropic')
    assert len(anthropic_errors) == 1
    assert anthropic_errors[0]['provider'] == 'anthropic'


def test_search_errors_by_time(temp_db):
    """Test searching errors by time range."""
    tracker = ErrorTracker(temp_db)

    sig = extract_signature("Bedrock: ValidationException - Test error")
    tracker.record_error(sig)

    # Search with time filter (recent)
    since = (datetime.now() - timedelta(hours=1)).isoformat()
    results = tracker.search_errors(since=since)
    assert len(results) == 1

    # Search with time filter (future - should return nothing)
    since_future = (datetime.now() + timedelta(hours=1)).isoformat()
    results = tracker.search_errors(since=since_future)
    assert len(results) == 0


def test_prune_old_occurrences(temp_db):
    """Test retention policy pruning."""
    tracker = ErrorTracker(temp_db)

    sig = {
        'provider': 'bedrock',
        'operation': 'InvokeModel',
        'error_type': 'ValidationException',
        'message': 'Test error'
    }

    # Record error
    fp, _ = tracker.record_error(sig, {'request_id': 'req1'})

    # Manually insert old occurrence (91 days ago)
    old_timestamp = (datetime.now() - timedelta(days=91)).isoformat()
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO error_occurrences (fingerprint, timestamp, request_id)
        VALUES (?, ?, ?)
    """, (fp, old_timestamp, 'req_old'))
    conn.commit()
    conn.close()

    # Check that we have 2 occurrences
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM error_occurrences WHERE fingerprint = ?", (fp,))
    count_before = cursor.fetchone()[0]
    assert count_before == 2
    conn.close()

    # Prune old occurrences
    deleted = tracker.prune_old_occurrences(max_age_days=90)
    assert deleted == 1

    # Check that only recent occurrence remains
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM error_occurrences WHERE fingerprint = ?", (fp,))
    count_after = cursor.fetchone()[0]
    assert count_after == 1
    conn.close()

    # Check that error_types entry is still intact
    error = tracker.get_error_by_fingerprint(fp)
    assert error is not None
    assert error['count'] == 1  # Count reflects record_error() calls only


def test_storage_growth_linearity(temp_db):
    """Test that storage grows with unique errors, not total count."""
    tracker = ErrorTracker(temp_db)

    # Record 10 unique errors, each occurring 10 times
    for i in range(10):
        sig = {
            'provider': 'bedrock',
            'operation': 'InvokeModel',
            'error_type': 'ValidationException',
            'message': f'Unique error {i}'
        }
        for j in range(10):
            tracker.record_error(sig, {'request_id': f'req_{i}_{j}'})

    # Check error_types: should have 10 rows
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM error_types")
    types_count = cursor.fetchone()[0]
    assert types_count == 10

    # Check error_occurrences: should have 100 rows
    cursor.execute("SELECT COUNT(*) FROM error_occurrences")
    occurrences_count = cursor.fetchone()[0]
    assert occurrences_count == 100

    conn.close()


# =============================================================================
# Story 3: Logging Integration Tests
# =============================================================================


def test_error_tracking_handler_captures_errors(temp_db):
    """Test that handler captures ERROR logs."""
    tracker = ErrorTracker(temp_db)
    handler = ErrorTrackingHandler(tracker)

    # Create test logger
    test_logger = logging.getLogger('test_logger')
    test_logger.setLevel(logging.ERROR)
    test_logger.addHandler(handler)

    # Log an error in expected format
    test_logger.error("[abc12345] ✗ bedrock (model=claude-opus-4-6): Could not connect to endpoint")

    # Check that error was captured
    errors = tracker.search_errors()
    assert len(errors) == 1
    assert errors[0]['provider'] == 'bedrock'


def test_error_tracking_handler_extracts_context(temp_db):
    """Test that handler extracts request_id, provider, model from log."""
    tracker = ErrorTracker(temp_db)
    handler = ErrorTrackingHandler(tracker)

    test_logger = logging.getLogger('test_context')
    test_logger.setLevel(logging.ERROR)
    test_logger.addHandler(handler)

    # Log error with full context
    test_logger.error("[12345678] ✗ bedrock: validation error (model=claude-haiku-4-5) - Extra inputs not permitted")

    # Check captured context
    errors = tracker.search_errors()
    assert len(errors) == 1

    # Get occurrences to check context
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT request_id, model FROM error_occurrences")
    row = cursor.fetchone()
    conn.close()

    assert row[0] == '12345678'
    assert row[1] == 'claude-haiku-4-5'


def test_error_tracking_handler_ignores_non_error_logs(temp_db):
    """Test that handler only processes ERROR+ logs."""
    tracker = ErrorTracker(temp_db)
    handler = ErrorTrackingHandler(tracker)

    test_logger = logging.getLogger('test_ignore')
    test_logger.setLevel(logging.DEBUG)
    test_logger.addHandler(handler)

    # Log INFO messages (should be ignored)
    test_logger.info("Some info message")
    test_logger.warning("Some warning message")

    # Should have no errors captured
    errors = tracker.search_errors()
    assert len(errors) == 0


def test_error_tracking_handler_circular_logging_prevention(temp_db):
    """Test that handler exceptions don't cause infinite recursion."""
    # Create tracker with invalid path to trigger error
    tracker = ErrorTracker(temp_db)
    handler = ErrorTrackingHandler(tracker)

    # Mock extract_signature to raise exception
    import error_tracker
    original_extract = error_tracker.extract_signature

    def mock_extract_error(*args, **kwargs):
        # This would normally cause circular logging if not guarded
        logging.getLogger('error_tracker').error("Something went wrong")
        raise Exception("Mock error")

    error_tracker.extract_signature = mock_extract_error

    try:
        test_logger = logging.getLogger('test_circular')
        test_logger.setLevel(logging.ERROR)
        test_logger.addHandler(handler)

        # This should not cause infinite recursion
        test_logger.error("[abc12345] ✗ bedrock (model=claude): Test error")

        # If we reach here, circular logging was prevented
        assert True

    finally:
        # Restore original function
        error_tracker.extract_signature = original_extract


def test_error_tracking_handler_deduplication(temp_db):
    """Test that handler deduplicates similar errors."""
    tracker = ErrorTracker(temp_db)
    handler = ErrorTrackingHandler(tracker)

    test_logger = logging.getLogger('test_dedup')
    test_logger.setLevel(logging.ERROR)
    test_logger.addHandler(handler)

    # Log same error type twice with different request IDs
    test_logger.error("[req00001] ✗ bedrock (model=claude-opus): Could not connect to endpoint URL")
    test_logger.error("[req00002] ✗ bedrock (model=claude-opus): Could not connect to endpoint URL")

    # Should have only 1 unique error type
    errors = tracker.search_errors()
    assert len(errors) == 1
    assert errors[0]['count'] == 2


def test_error_tracking_handler_new_error_detection(temp_db):
    """Test that handler detects new error types."""
    tracker = ErrorTracker(temp_db)
    handler = ErrorTrackingHandler(tracker)

    test_logger = logging.getLogger('test_new')
    test_logger.setLevel(logging.ERROR)
    test_logger.addHandler(handler)

    # First occurrence - should be new
    test_logger.error("[req001] ✗ bedrock (model=claude): ValidationException - Error 1")

    errors = tracker.search_errors()
    assert len(errors) == 1

    # Second occurrence - should not be new (same error)
    test_logger.error("[req002] ✗ bedrock (model=claude): ValidationException - Error 1")

    errors = tracker.search_errors()
    assert len(errors) == 1  # Still 1 unique error
    assert errors[0]['count'] == 2  # But count increased


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
