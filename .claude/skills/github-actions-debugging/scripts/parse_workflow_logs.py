#!/usr/bin/env python3
"""
GitHub Actions Workflow Log Parser

This script parses GitHub Actions workflow logs, extracts errors, categorizes them,
and generates actionable fix suggestions.

Dual Purpose:
1. Executable tool: Run directly to parse log files
2. Reference documentation: Claude can read to understand error patterns

Usage:
    python parse_workflow_logs.py <log_file>
    cat log.txt | python parse_workflow_logs.py
"""

import re
import sys
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class ErrorCategory(Enum):
    """Error categories for GitHub Actions failures"""
    DEPENDENCY = "dependency"
    PERMISSION = "permission"
    TIMEOUT = "timeout"
    ENVIRONMENT = "environment"
    SYNTAX = "syntax"
    NETWORK = "network"
    DOCKER = "docker"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Severity levels for errors"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ErrorEntry:
    """Represents a single error found in logs"""
    line_number: int
    message: str
    category: str
    severity: str
    context: str
    fixes: List[str]

    def to_dict(self) -> dict:
        return asdict(self)


# Error pattern database - matches against known error signatures
ERROR_PATTERNS = [
    # Dependency errors
    (r'npm ERR! code ERESOLVE', ErrorCategory.DEPENDENCY, ErrorSeverity.CRITICAL,
     ['Add --legacy-peer-deps flag', 'Update conflicting packages', 'Regenerate package-lock.json']),

    (r'npm ERR!.*EUSAGE.*package\.json and package-lock\.json.*in sync', ErrorCategory.DEPENDENCY, ErrorSeverity.CRITICAL,
     ['Run npm install to regenerate lock file', 'Delete package-lock.json and run npm install']),

    (r'pip.*error.*ResolutionImpossible|Cannot install.*incompatible dependencies', ErrorCategory.DEPENDENCY, ErrorSeverity.CRITICAL,
     ['Pin conflicting package versions', 'Upgrade pip resolver', 'Use constraint files']),

    (r'go:.*inconsistent vendoring', ErrorCategory.DEPENDENCY, ErrorSeverity.CRITICAL,
     ['Run go mod tidy', 'Run go mod vendor', 'Delete vendor/ and regenerate']),

    # Permission errors
    (r'Resource not accessible by integration|HttpError.*not accessible', ErrorCategory.PERMISSION, ErrorSeverity.CRITICAL,
     ['Add required permissions to workflow', 'Use PAT instead of GITHUB_TOKEN', 'Check organization settings']),

    (r'Permission denied \(publickey\)', ErrorCategory.PERMISSION, ErrorSeverity.CRITICAL,
     ['Use HTTPS instead of SSH', 'Configure SSH key with webfactory/ssh-agent', 'Add deploy key to repository']),

    (r'Resource protected by organization SAML enforcement', ErrorCategory.PERMISSION, ErrorSeverity.CRITICAL,
     ['Authorize PAT for SAML SSO', 'Create new token with SSO authorization']),

    # Timeout and resource errors
    (r'##\[error\].*exceeded the maximum execution time|timeout', ErrorCategory.TIMEOUT, ErrorSeverity.CRITICAL,
     ['Increase timeout-minutes in workflow', 'Optimize slow operations', 'Use matrix strategy for parallelization']),

    (r'exit code 137|Killed', ErrorCategory.TIMEOUT, ErrorSeverity.CRITICAL,
     ['Increase NODE_OPTIONS --max-old-space-size', 'Reduce parallelism', 'Use larger runner']),

    # Environment errors
    (r'Unable to locate executable file|command not found', ErrorCategory.ENVIRONMENT, ErrorSeverity.CRITICAL,
     ['Add setup action (setup-node, setup-python)', 'Install tool manually', 'Use container with pre-installed tools']),

    (r'ENOENT: no such file or directory', ErrorCategory.ENVIRONMENT, ErrorSeverity.CRITICAL,
     ['Add actions/checkout step', 'Set correct working-directory', 'Check previous steps succeeded']),

    (r'fatal: not a git repository', ErrorCategory.ENVIRONMENT, ErrorSeverity.CRITICAL,
     ['Add actions/checkout before git commands', 'Check working directory']),

    # Syntax errors
    (r'YAML syntax error|Invalid workflow file|Unexpected token', ErrorCategory.SYNTAX, ErrorSeverity.CRITICAL,
     ['Run yamllint on workflow file', 'Fix indentation (use spaces not tabs)', 'Validate YAML syntax']),

    # Network errors
    (r'Could not resolve host|getaddrinfo ENOTFOUND', ErrorCategory.NETWORK, ErrorSeverity.WARNING,
     ['Add retry logic', 'Check service status', 'Use alternative DNS']),

    (r'API rate limit exceeded|403 Forbidden', ErrorCategory.NETWORK, ErrorSeverity.WARNING,
     ['Add authentication to API requests', 'Add delays between requests', 'Use GraphQL instead of REST']),

    # Docker errors
    (r'buildx failed|ERROR: failed to solve', ErrorCategory.DOCKER, ErrorSeverity.CRITICAL,
     ['Verify base image exists', 'Fix COPY paths in Dockerfile', 'Check build context', 'Use --progress=plain for debugging']),
]


def extract_errors(log_text: str) -> List[ErrorEntry]:
    """
    Extract error messages and context from GitHub Actions logs.

    Args:
        log_text: Raw log text from workflow run

    Returns:
        List of ErrorEntry objects with line numbers, messages, and context
    """
    errors = []
    lines = log_text.split('\n')

    # Common error indicators in GHA logs
    error_indicators = [
        r'##\[error\]',
        r'Error:',
        r'ERROR:',
        r'FAIL:',
        r'Failed:',
        r'fatal:',
        r'npm ERR!',
        r'pip error',
    ]

    error_pattern = re.compile('|'.join(error_indicators), re.IGNORECASE)

    for i, line in enumerate(lines, start=1):
        if error_pattern.search(line):
            # Extract context (±5 lines)
            start_ctx = max(0, i - 6)
            end_ctx = min(len(lines), i + 5)
            context = '\n'.join(lines[start_ctx:end_ctx])

            # Categorize and get fixes
            category, severity, fixes = categorize_error(line)

            errors.append(ErrorEntry(
                line_number=i,
                message=line.strip(),
                category=category.value,
                severity=severity.value,
                context=context,
                fixes=fixes
            ))

    return errors


def categorize_error(error_msg: str) -> Tuple[ErrorCategory, ErrorSeverity, List[str]]:
    """
    Match error against known patterns and return category, severity, and fixes.

    Args:
        error_msg: Error message to categorize

    Returns:
        Tuple of (ErrorCategory, ErrorSeverity, List of fix suggestions)
    """
    for pattern, category, severity, fixes in ERROR_PATTERNS:
        if re.search(pattern, error_msg, re.IGNORECASE):
            return category, severity, fixes

    # Default for unknown errors
    return ErrorCategory.UNKNOWN, ErrorSeverity.CRITICAL, ['Review logs for specific error details']


def generate_report(errors: List[ErrorEntry]) -> dict:
    """
    Generate structured JSON report from error list.

    Args:
        errors: List of ErrorEntry objects

    Returns:
        Dictionary with summary and detailed error information
    """
    if not errors:
        return {
            "summary": {
                "total_errors": 0,
                "categories": {},
                "critical_count": 0
            },
            "errors": []
        }

    # Count errors by category
    categories = {}
    critical_count = 0

    for error in errors:
        categories[error.category] = categories.get(error.category, 0) + 1
        if error.severity == ErrorSeverity.CRITICAL.value:
            critical_count += 1

    return {
        "summary": {
            "total_errors": len(errors),
            "categories": categories,
            "critical_count": critical_count
        },
        "errors": [error.to_dict() for error in errors]
    }


def main():
    """Main entry point for script execution"""
    # Read from file or stdin
    if len(sys.argv) > 1:
        try:
            with open(sys.argv[1], 'r', encoding='utf-8') as f:
                log_text = f.read()
        except FileNotFoundError:
            print(f"Error: File '{sys.argv[1]}' not found", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Read from stdin
        log_text = sys.stdin.read()

    if not log_text.strip():
        print("Error: No input provided", file=sys.stderr)
        sys.exit(1)

    # Extract and categorize errors
    errors = extract_errors(log_text)

    # Generate report
    report = generate_report(errors)

    # Output JSON
    print(json.dumps(report, indent=2))

    # Exit with error code if critical errors found
    if report["summary"]["critical_count"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
