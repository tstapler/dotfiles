#!/bin/bash
# Quick profiling script for Claude Proxy
# Usage: ./profile.sh [duration] [output]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Find uvicorn master process
PID=$(pgrep -f "uvicorn main:app" | head -1)

if [ -z "$PID" ]; then
    echo -e "${RED}Error: Claude proxy not running${NC}"
    echo "Start it with: make start"
    exit 1
fi

DURATION=${1:-30}
OUTPUT=${2:-/tmp/proxy-profile-$(date +%Y%m%d-%H%M%S).svg}

echo -e "${GREEN}Profiling Claude Proxy${NC}"
echo "  PID:      $PID"
echo "  Duration: ${DURATION}s"
echo "  Output:   $OUTPUT"
echo ""

# Check if py-spy is installed
if ! command -v py-spy &> /dev/null; then
    echo -e "${YELLOW}py-spy not found, installing...${NC}"
    brew install py-spy || pip install py-spy
fi

# Profile
echo -e "${GREEN}Recording flame graph...${NC}"
sudo py-spy record -o "$OUTPUT" -d "$DURATION" -p "$PID"

# Show top functions
echo ""
echo -e "${GREEN}Top 10 hottest functions:${NC}"
sudo py-spy top -p "$PID" -d 5 | head -20

# Check current lag
echo ""
echo -e "${GREEN}Current event loop lag:${NC}"
CURRENT_LAG=$(curl -s http://localhost:47000/metrics | jq -r '.current_lag_ms')
echo "  ${CURRENT_LAG}ms"

# Get lag stats from last minute
echo ""
echo -e "${GREEN}Lag stats (last minute):${NC}"
curl -s http://localhost:47000/metrics | jq '.lag_data[-1]'

# Open flame graph
echo ""
echo -e "${GREEN}Opening flame graph...${NC}"
open "$OUTPUT"

echo ""
echo -e "${GREEN}Done!${NC}"
echo ""
echo "Tips:"
echo "  - Wide bars at bottom = hot paths"
echo "  - Look for: diskcache, boto3, cache.iterkeys"
echo "  - Compare before/after optimizations"
echo ""
echo "View with: open $OUTPUT"
