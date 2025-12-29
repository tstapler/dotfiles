#!/bin/bash
#
# binary-analyzer.sh - Analyze binary executables safely
#
# Usage: binary-analyzer.sh <binary_file> [--output json|text]
#
# This script:
# - Identifies binary type and architecture
# - Extracts symbols and imports
# - Lists dynamic dependencies
# - Searches for interesting strings
# - Generates structured analysis report
#
# Security:
# - Read-only operations (never executes analyzed binary)
# - Safe string extraction with limits
# - No code modification or injection

set -euo pipefail

# Configuration
MAX_STRINGS=500
MIN_STRING_LENGTH=4
OUTPUT_FORMAT="json"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Usage
usage() {
    cat >&2 <<EOF
Usage: $0 <binary_file> [options]

Options:
  --output json|text    Output format (default: json)
  --max-strings N       Maximum strings to extract (default: 500)
  --min-length N        Minimum string length (default: 4)
  -h, --help           Show this help

Examples:
  # Basic analysis
  $0 /usr/bin/ls

  # Text format with more strings
  $0 myapp --output text --max-strings 1000

  # Pipe JSON to jq
  $0 myapp | jq '.symbols'
EOF
    exit 1
}

# Parse arguments
BINARY_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --output)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        --max-strings)
            MAX_STRINGS="$2"
            shift 2
            ;;
        --min-length)
            MIN_STRING_LENGTH="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            if [ -z "$BINARY_FILE" ]; then
                BINARY_FILE="$1"
            else
                echo -e "${RED}Error: Unknown argument: $1${NC}" >&2
                usage
            fi
            shift
            ;;
    esac
done

if [ -z "$BINARY_FILE" ]; then
    echo -e "${RED}Error: Binary file is required${NC}" >&2
    usage
fi

if [ ! -f "$BINARY_FILE" ]; then
    echo -e "${RED}Error: File not found: $BINARY_FILE${NC}" >&2
    exit 1
fi

# Detect file type
FILE_TYPE=$(file "$BINARY_FILE" 2>/dev/null || echo "unknown")

# Extract architecture
ARCH="unknown"
if [[ "$FILE_TYPE" =~ x86-64|x86_64 ]]; then
    ARCH="x86_64"
elif [[ "$FILE_TYPE" =~ ARM|aarch64 ]]; then
    ARCH="arm64"
elif [[ "$FILE_TYPE" =~ i386|80386 ]]; then
    ARCH="x86"
fi

# Detect binary format
BINARY_FORMAT="unknown"
if [[ "$FILE_TYPE" =~ ELF ]]; then
    BINARY_FORMAT="ELF"
elif [[ "$FILE_TYPE" =~ Mach-O ]]; then
    BINARY_FORMAT="Mach-O"
elif [[ "$FILE_TYPE" =~ PE32 ]]; then
    BINARY_FORMAT="PE"
fi

# Extract symbols
SYMBOLS=()
STRIPPED="false"

if command -v nm &>/dev/null; then
    if nm -D "$BINARY_FILE" 2>/dev/null | head -100 > /tmp/symbols_$$.txt; then
        while IFS= read -r line; do
            # Extract symbol names (third field)
            symbol=$(echo "$line" | awk '{print $3}')
            if [ -n "$symbol" ]; then
                SYMBOLS+=("$symbol")
            fi
        done < /tmp/symbols_$$.txt
        rm -f /tmp/symbols_$$.txt
    else
        # Try regular nm (macOS)
        if nm "$BINARY_FILE" 2>/dev/null | grep -v " U " | head -100 > /tmp/symbols_$$.txt; then
            while IFS= read -r line; do
                symbol=$(echo "$line" | awk '{print $3}')
                if [ -n "$symbol" ]; then
                    SYMBOLS+=("$symbol")
                fi
            done < /tmp/symbols_$$.txt
            rm -f /tmp/symbols_$$.txt
        else
            STRIPPED="true"
        fi
    fi
fi

# Extract dependencies
DEPENDENCIES=()

if [[ "$BINARY_FORMAT" == "ELF" ]] && command -v ldd &>/dev/null; then
    while IFS= read -r line; do
        dep=$(echo "$line" | awk '{print $1}')
        if [ -n "$dep" ] && [ "$dep" != "linux-vdso.so.1" ]; then
            DEPENDENCIES+=("$dep")
        fi
    done < <(ldd "$BINARY_FILE" 2>/dev/null | grep "=>" | head -50)
elif [[ "$BINARY_FORMAT" == "Mach-O" ]] && command -v otool &>/dev/null; then
    while IFS= read -r line; do
        dep=$(echo "$line" | awk '{print $1}')
        if [ -n "$dep" ]; then
            DEPENDENCIES+=("$dep")
        fi
    done < <(otool -L "$BINARY_FILE" 2>/dev/null | tail -n +2 | head -50)
fi

# Extract strings
STRINGS_ARRAY=()
if command -v strings &>/dev/null; then
    while IFS= read -r str; do
        STRINGS_ARRAY+=("$str")
    done < <(strings -n "$MIN_STRING_LENGTH" "$BINARY_FILE" 2>/dev/null | head -"$MAX_STRINGS")
fi

# Interesting patterns
URLS=()
PATHS=()
API_PATTERNS=()

for str in "${STRINGS_ARRAY[@]}"; do
    if [[ "$str" =~ https?:// ]]; then
        URLS+=("$str")
    elif [[ "$str" =~ ^/ ]] && [[ "$str" =~ / ]]; then
        PATHS+=("$str")
    elif [[ "$str" =~ /api/|/v[0-9]/|endpoint ]]; then
        API_PATTERNS+=("$str")
    fi
done

# Get file size
FILE_SIZE=$(stat -f%z "$BINARY_FILE" 2>/dev/null || stat -c%s "$BINARY_FILE" 2>/dev/null || echo "0")

# Generate output
if [ "$OUTPUT_FORMAT" == "json" ]; then
    # JSON output
    cat <<EOF
{
  "file": "$BINARY_FILE",
  "size_bytes": $FILE_SIZE,
  "type": "$BINARY_FORMAT",
  "architecture": "$ARCH",
  "stripped": $STRIPPED,
  "file_info": "$(echo "$FILE_TYPE" | sed 's/"/\\"/g')",
  "symbols": [
    $(printf '"%s",' "${SYMBOLS[@]}" | sed 's/,$//')
  ],
  "dependencies": [
    $(printf '"%s",' "${DEPENDENCIES[@]}" | sed 's/,$//')
  ],
  "strings": {
    "total": ${#STRINGS_ARRAY[@]},
    "sample": [
      $(printf '"%s",' "${STRINGS_ARRAY[@]:0:50}" | sed 's/,$//' | sed 's/"/\\"/g')
    ]
  },
  "interesting": {
    "urls": [
      $(printf '"%s",' "${URLS[@]}" | sed 's/,$//')
    ],
    "paths": [
      $(printf '"%s",' "${PATHS[@]:0:20}" | sed 's/,$//')
    ],
    "api_patterns": [
      $(printf '"%s",' "${API_PATTERNS[@]}" | sed 's/,$//')
    ]
  }
}
EOF
else
    # Text output
    cat <<EOF
Binary Analysis: $BINARY_FILE
Size: $FILE_SIZE bytes
Type: $BINARY_FORMAT
Architecture: $ARCH
Stripped: $STRIPPED

File Info:
$FILE_TYPE

Symbols (${#SYMBOLS[@]} found):
$(printf "  - %s\n" "${SYMBOLS[@]:0:20}")
${#SYMBOLS[@]} > 20 && echo "  ... (showing first 20 of ${#SYMBOLS[@]})"

Dependencies (${#DEPENDENCIES[@]} found):
$(printf "  - %s\n" "${DEPENDENCIES[@]}")

Strings (${#STRINGS_ARRAY[@]} found, showing first 20):
$(printf "  - %s\n" "${STRINGS_ARRAY[@]:0:20}")

Interesting Findings:
  URLs found: ${#URLS[@]}
$([ ${#URLS[@]} -gt 0 ] && printf "    - %s\n" "${URLS[@]:0:10}" || echo "    (none)")

  Paths found: ${#PATHS[@]}
$([ ${#PATHS[@]} -gt 0 ] && printf "    - %s\n" "${PATHS[@]:0:10}" || echo "    (none)")

  API patterns: ${#API_PATTERNS[@]}
$([ ${#API_PATTERNS[@]} -gt 0 ] && printf "    - %s\n" "${API_PATTERNS[@]}" || echo "    (none)")
EOF
fi
