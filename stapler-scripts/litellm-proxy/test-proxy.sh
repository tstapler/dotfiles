#!/bin/bash
# Test LiteLLM proxy endpoints
# Usage: ./test-proxy.sh [endpoint] [oauth_token]
#
# Endpoints:
#   health      - Check proxy health
#   chat        - Test OpenAI-compatible chat (uses Bedrock fallback)
#   messages    - Test Anthropic native API (uses OAuth pass-through)
#   models      - List available models

set -e

PROXY_URL="${LITELLM_PROXY_URL:-http://localhost:47000}"
# Try multiple sources for OAuth token: CLI arg, CLAUDE_CODE_OAUTH_TOKEN, or ANTHROPIC_API_KEY
OAUTH_TOKEN="${2:-${CLAUDE_CODE_OAUTH_TOKEN:-$ANTHROPIC_API_KEY}}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_result() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}SUCCESS${NC}"
    else
        echo -e "${RED}FAILED${NC}"
    fi
}

case "${1:-health}" in
    health)
        echo "Testing proxy health..."
        response=$(curl -s "$PROXY_URL/health")
        healthy=$(echo "$response" | jq -r '.healthy_count // 0')
        unhealthy=$(echo "$response" | jq -r '.unhealthy_count // 0')
        echo "Healthy endpoints: $healthy"
        echo "Unhealthy endpoints: $unhealthy"

        if [ "$healthy" -gt 0 ]; then
            echo -e "${GREEN}Proxy is healthy!${NC}"
            exit 0
        else
            echo -e "${RED}No healthy endpoints${NC}"
            exit 1
        fi
        ;;

    chat)
        echo "Testing OpenAI-compatible chat endpoint..."
        echo "Using model: claude-haiku (routes to Bedrock)"
        echo ""
        response=$(curl -s -X POST "$PROXY_URL/v1/chat/completions" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer test" \
            -d '{"model": "claude-haiku", "messages": [{"role": "user", "content": "Say hi in 3 words"}], "max_tokens": 50}')

        model=$(echo "$response" | jq -r '.model // "error"')
        content=$(echo "$response" | jq -r '.choices[0].message.content // .error.message // "no response"')

        echo "Model used: $model"
        echo "Response: $content"

        if echo "$response" | jq -e '.choices[0].message.content' > /dev/null 2>&1; then
            echo -e "${GREEN}Chat endpoint working!${NC}"
        else
            echo -e "${RED}Chat endpoint failed${NC}"
            echo "$response" | jq .
            exit 1
        fi
        ;;

    messages)
        echo "Testing Anthropic native messages endpoint (OAuth pass-through)..."

        if [ -z "$OAUTH_TOKEN" ]; then
            echo -e "${RED}Error: No OAuth token provided${NC}"
            echo "Usage: ./test-proxy.sh messages <oauth_token>"
            echo "Or set ANTHROPIC_API_KEY environment variable"
            exit 1
        fi

        echo "Using OAuth token: ${OAUTH_TOKEN:0:20}..."
        echo ""

        response=$(curl -s -X POST "$PROXY_URL/v1/messages" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $OAUTH_TOKEN" \
            -H "anthropic-version: 2023-06-01" \
            -d '{"model": "claude-3-5-haiku-20241022", "messages": [{"role": "user", "content": "Say hi in 3 words"}], "max_tokens": 50}')

        content=$(echo "$response" | jq -r '.content[0].text // .error.message // "no response"')
        model=$(echo "$response" | jq -r '.model // "error"')

        echo "Model: $model"
        echo "Response: $content"

        if echo "$response" | jq -e '.content[0].text' > /dev/null 2>&1; then
            echo -e "${GREEN}Messages endpoint working!${NC}"
        else
            echo -e "${RED}Messages endpoint failed${NC}"
            echo "$response" | jq .
            exit 1
        fi
        ;;

    models)
        echo "Listing available models..."
        curl -s "$PROXY_URL/v1/models" \
            -H "Authorization: Bearer test" | jq -r '.data[].id' 2>/dev/null || echo "Failed to list models"
        ;;

    all)
        echo "Running all tests..."
        echo "========================"
        $0 health
        echo ""
        echo "========================"
        $0 chat
        echo ""
        echo "========================"
        $0 messages "$OAUTH_TOKEN"
        echo ""
        echo "========================"
        echo "All tests complete!"
        ;;

    *)
        echo "LiteLLM Proxy Test Script"
        echo ""
        echo "Usage: $0 [command] [oauth_token]"
        echo ""
        echo "Commands:"
        echo "  health    - Check proxy health status"
        echo "  chat      - Test OpenAI-compatible endpoint (Bedrock)"
        echo "  messages  - Test Anthropic native endpoint (OAuth pass-through)"
        echo "  models    - List available models"
        echo "  all       - Run all tests"
        echo ""
        echo "Environment variables:"
        echo "  LITELLM_PROXY_URL  - Proxy URL (default: http://localhost:47000)"
        echo "  ANTHROPIC_API_KEY  - OAuth token for messages endpoint"
        ;;
esac
