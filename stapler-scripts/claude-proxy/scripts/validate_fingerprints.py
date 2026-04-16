#!/usr/bin/env python3
"""Validate fingerprinting accuracy on historical proxy logs.

This script:
1. Extracts all ERROR-level messages from proxy logs
2. Computes fingerprints for each error
3. Calculates collision rate (different errors with same fingerprint)
4. Calculates stability rate (same error with different fingerprints)
5. Displays sample fingerprint groups for manual review

Target metrics:
- Collision rate: <1% (stretch goal: <0.5%)
- Stability rate: >99%
"""

import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path to import error_tracker
sys.path.insert(0, str(Path(__file__).parent.parent))
from error_tracker import extract_signature, compute_fingerprint


LOG_FILE = '/tmp/claude-proxy.app.log'


def parse_error_log_line(line: str) -> Tuple[str, str, str, str, str]:
    """Parse error log line to extract components.

    Expected format:
    YYYY-MM-DD HH:MM:SS - module - ERROR - [request_id] ✗ provider (model=model_name): error_message

    Returns:
        Tuple of (timestamp, request_id, provider, model, error_message)
        Returns empty strings if parsing fails
    """
    # Pattern: timestamp - module - ERROR - [request_id] ✗ provider (model=model): message
    pattern = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - \w+ - ERROR - \[([a-f0-9]{8})\] ✗ (\w+) \(model=([^)]+)\): (.+)$'

    match = re.match(pattern, line)
    if match:
        return match.groups()

    # Alternative pattern: timestamp - module - ERROR - [request_id] ✗ provider: error_type (model=model) - message
    alt_pattern = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - \w+ - ERROR - \[([a-f0-9]{8})\] ✗ (\w+): ([^(]+) \(model=([^)]+)\) - (.+)$'
    match = re.match(alt_pattern, line)
    if match:
        timestamp, request_id, provider, error_type, model, message = match.groups()
        return (timestamp, request_id, provider, model, f"{error_type} - {message}")

    return ('', '', '', '', '')


def extract_errors_from_log(log_path: str, max_age_days: int = 30) -> List[Dict[str, str]]:
    """Extract all ERROR-level messages from log file.

    Args:
        log_path: Path to log file
        max_age_days: Only include errors from last N days

    Returns:
        List of error dicts with keys: timestamp, request_id, provider, model, message
    """
    cutoff_date = datetime.now() - timedelta(days=max_age_days)
    errors = []

    try:
        with open(log_path, 'r') as f:
            for line in f:
                if ' - ERROR - ' not in line or '✗' not in line:
                    continue

                timestamp, request_id, provider, model, message = parse_error_log_line(line.strip())
                if not timestamp:
                    continue

                # Check if within date range
                try:
                    error_date = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                    if error_date < cutoff_date:
                        continue
                except ValueError:
                    continue

                errors.append({
                    'timestamp': timestamp,
                    'request_id': request_id,
                    'provider': provider,
                    'model': model,
                    'message': message
                })

    except FileNotFoundError:
        print(f"❌ Log file not found: {log_path}")
        print(f"   Make sure the proxy has been running and logging to this location")
        return []

    return errors


def analyze_fingerprints(errors: List[Dict[str, str]]) -> None:
    """Analyze fingerprint quality: collision rate, stability rate, sample groups.

    Args:
        errors: List of error dicts from extract_errors_from_log()
    """
    if not errors:
        print("❌ No errors found in logs")
        return

    print(f"\n{'='*80}")
    print(f"Fingerprint Quality Analysis")
    print(f"{'='*80}\n")

    print(f"📊 Dataset: {len(errors)} errors from last 30 days\n")

    # Group errors by fingerprint
    fingerprint_groups = defaultdict(list)

    for error in errors:
        sig = extract_signature(error['message'], provider=error['provider'])
        fp = compute_fingerprint(sig)

        fingerprint_groups[fp].append({
            'error': error,
            'signature': sig
        })

    unique_fingerprints = len(fingerprint_groups)
    print(f"🔑 Unique fingerprints: {unique_fingerprints}")
    print(f"📈 Deduplication ratio: {len(errors) / unique_fingerprints:.1f}x\n")

    # Calculate collision rate (same fingerprint, different error types)
    collisions = 0
    for fp, group in fingerprint_groups.items():
        error_types = set(item['signature']['error_type'] for item in group)
        if len(error_types) > 1:
            collisions += 1

    collision_rate = (collisions / unique_fingerprints) * 100 if unique_fingerprints > 0 else 0
    print(f"💥 Collision rate: {collision_rate:.2f}% ({collisions}/{unique_fingerprints})")

    if collision_rate < 0.5:
        print(f"   ✅ Excellent! Well below 1% target")
    elif collision_rate < 1.0:
        print(f"   ✅ Good! Meets <1% target")
    elif collision_rate < 5.0:
        print(f"   ⚠️  Warning: Above 1% target, but acceptable")
    else:
        print(f"   ❌ High collision rate! Needs refinement")

    # Calculate stability rate (same logical error, different fingerprints)
    # For simplicity, we'll check if errors with same message (after basic normalization) have same fingerprint
    # This is a proxy metric since we don't have ground truth for "same logical error"
    message_groups = defaultdict(set)
    for fp, group in fingerprint_groups.items():
        for item in group:
            # Use error_type + normalized message (first 50 chars) as proxy for "logical error"
            message_key = f"{item['signature']['error_type']}:{item['signature']['message'][:50]}"
            message_groups[message_key].add(fp)

    unstable_groups = sum(1 for fps in message_groups.values() if len(fps) > 1)
    stability_rate = (1 - unstable_groups / len(message_groups)) * 100 if message_groups else 100

    print(f"\n🎯 Stability rate: {stability_rate:.2f}%")
    if stability_rate > 99:
        print(f"   ✅ Excellent! Above 99% target")
    elif stability_rate > 95:
        print(f"   ⚠️  Acceptable, but could be improved")
    else:
        print(f"   ❌ Low stability! Same errors getting different fingerprints")

    # Display sample fingerprint groups for manual review
    print(f"\n{'='*80}")
    print(f"Sample Fingerprint Groups (Manual Review)")
    print(f"{'='*80}\n")

    # Sort groups by size (most common errors first)
    sorted_groups = sorted(
        fingerprint_groups.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )

    for i, (fp, group) in enumerate(sorted_groups[:10], 1):
        sig = group[0]['signature']
        count = len(group)

        print(f"{i}. Fingerprint: {fp} (count: {count})")
        print(f"   Provider: {sig['provider']}")
        print(f"   Error type: {sig['error_type']}")
        print(f"   Operation: {sig['operation']}")
        print(f"   Message: {sig['message'][:100]}...")

        # Show sample request IDs
        sample_ids = [item['error']['request_id'] for item in group[:3]]
        print(f"   Sample request IDs: {', '.join(sample_ids)}")

        # Check for potential collisions (different error types in same group)
        error_types = set(item['signature']['error_type'] for item in group)
        if len(error_types) > 1:
            print(f"   ⚠️  COLLISION DETECTED: Multiple error types: {', '.join(error_types)}")

        print()

    # Summary
    print(f"\n{'='*80}")
    print(f"Summary")
    print(f"{'='*80}\n")

    if collision_rate < 1.0 and stability_rate > 99:
        print("✅ Fingerprinting quality: EXCELLENT")
        print("   Ready to proceed to Story 2 (Persistent Storage)")
    elif collision_rate < 5.0 and stability_rate > 95:
        print("⚠️  Fingerprinting quality: ACCEPTABLE")
        print("   Consider refining normalization patterns before Story 2")
    else:
        print("❌ Fingerprinting quality: NEEDS IMPROVEMENT")
        print("   Refine normalization before proceeding to Story 2")

    print()


def main():
    """Main entry point."""
    print(f"Validating fingerprinting on historical logs...")
    print(f"Log file: {LOG_FILE}\n")

    # Extract errors
    errors = extract_errors_from_log(LOG_FILE, max_age_days=30)

    if not errors:
        print("\n⚠️  No errors found in logs (last 30 days)")
        print("   This might mean:")
        print("   - Proxy hasn't been running long")
        print("   - No errors have occurred (unlikely)")
        print("   - Log file location is incorrect")
        print("\n   Skipping validation (will proceed with Story 2)")
        return

    # Analyze fingerprints
    analyze_fingerprints(errors)


if __name__ == '__main__':
    main()
