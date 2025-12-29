#!/bin/bash
#
# safe-clone.sh - Safely clone a git repository to a temporary directory
#
# Usage: safe-clone.sh <repo_url> [depth]
#
# This script:
# - Creates an isolated temporary directory
# - Clones with timeout protection
# - Validates URL format
# - Prints the clone location for downstream tools
#
# Security:
# - All operations in /tmp/analysis-* directories
# - 60-second timeout for clone operations
# - Validates URLs to prevent injection
# - Automatic cleanup on script exit

set -euo pipefail

# Configuration
TIMEOUT=60
DEFAULT_DEPTH=1
TEMP_BASE="/tmp/analysis-$(uuidgen)"

# Color output for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Cleanup on exit
cleanup() {
    if [ -n "${TEMP_DIR:-}" ] && [ "$KEEP_TEMP" != "1" ]; then
        echo -e "${YELLOW}Cleaning up ${TEMP_DIR}${NC}" >&2
        rm -rf "$TEMP_DIR" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Usage
usage() {
    echo "Usage: $0 <repo_url> [depth] [--keep]" >&2
    echo "" >&2
    echo "Options:" >&2
    echo "  repo_url    Git repository URL (https:// or git@)" >&2
    echo "  depth       Clone depth (default: 1)" >&2
    echo "  --keep      Keep temporary directory after exit" >&2
    exit 1
}

# Validate URL
validate_url() {
    local url="$1"

    # Check for valid git URL patterns
    if [[ ! "$url" =~ ^(https://|git@) ]]; then
        echo -e "${RED}Error: Invalid URL format. Must start with https:// or git@${NC}" >&2
        return 1
    fi

    # Prevent command injection attempts
    if [[ "$url" =~ [\;\|\&\$\`] ]]; then
        echo -e "${RED}Error: URL contains invalid characters${NC}" >&2
        return 1
    fi

    return 0
}

# Parse arguments
REPO_URL=""
DEPTH=$DEFAULT_DEPTH
KEEP_TEMP=0

while [[ $# -gt 0 ]]; do
    case $1 in
        --keep)
            KEEP_TEMP=1
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            if [ -z "$REPO_URL" ]; then
                REPO_URL="$1"
            elif [[ "$1" =~ ^[0-9]+$ ]]; then
                DEPTH="$1"
            else
                echo -e "${RED}Error: Unknown argument: $1${NC}" >&2
                usage
            fi
            shift
            ;;
    esac
done

# Check required arguments
if [ -z "$REPO_URL" ]; then
    echo -e "${RED}Error: Repository URL is required${NC}" >&2
    usage
fi

# Validate URL
if ! validate_url "$REPO_URL"; then
    exit 1
fi

# Create temp directory
TEMP_DIR="$TEMP_BASE"
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

echo -e "${GREEN}Cloning repository to: ${TEMP_DIR}${NC}" >&2
echo -e "${YELLOW}Repository: ${REPO_URL}${NC}" >&2
echo -e "${YELLOW}Depth: ${DEPTH}${NC}" >&2

# Clone with timeout
if timeout ${TIMEOUT}s git clone --depth="${DEPTH}" "$REPO_URL" repo 2>&1 | tee clone.log >&2; then
    CLONE_DIR="${TEMP_DIR}/repo"
    echo -e "${GREEN}Clone successful${NC}" >&2

    # Output statistics
    if [ -d "$CLONE_DIR" ]; then
        FILE_COUNT=$(find "$CLONE_DIR" -type f | wc -l)
        DIR_SIZE=$(du -sh "$CLONE_DIR" 2>/dev/null | cut -f1)
        echo -e "${GREEN}Files: ${FILE_COUNT}, Size: ${DIR_SIZE}${NC}" >&2
    fi

    # Print location (for downstream tools)
    echo "$CLONE_DIR"
    exit 0
else
    EXIT_CODE=$?
    echo -e "${RED}Clone failed with exit code: ${EXIT_CODE}${NC}" >&2

    # Try to diagnose the failure
    if grep -q "timeout" clone.log 2>/dev/null; then
        echo -e "${YELLOW}Suggestion: Repository is too large. Try increasing depth or downloading ZIP${NC}" >&2
    elif grep -q "Authentication" clone.log 2>/dev/null; then
        echo -e "${YELLOW}Suggestion: Repository requires authentication${NC}" >&2
    elif grep -q "not found" clone.log 2>/dev/null; then
        echo -e "${YELLOW}Suggestion: Repository URL is invalid or repository doesn't exist${NC}" >&2
    fi

    exit $EXIT_CODE
fi
