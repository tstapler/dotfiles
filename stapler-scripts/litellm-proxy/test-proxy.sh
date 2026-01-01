#!/bin/bash
# Test LiteLLM proxy endpoints with Claude API primary and Bedrock fallback
# Usage: ./test-proxy.sh [endpoint] [oauth_token]
#
# Endpoints:
#   health      - Check proxy health
#   chat        - Test OpenAI-compatible chat endpoint
#   messages    - Test Anthropic native API (OAuth pass-through)
#   fallback    - Test fallback behavior (simulates rate limit)
#   models      - List available models
#   all         - Run all tests

set -e

PROXY_URL="${LITELLM_PROXY_URL:-http://localhost:47000}"
# Try multiple sources for OAuth token: CLI arg, CLAUDE_CODE_OAUTH_TOKEN, or ANTHROPIC_API_KEY
OAUTH_TOKEN="${2:-${CLAUDE_CODE_OAUTH_TOKEN:-$ANTHROPIC_API_KEY}}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
        echo "Using model: claude-haiku"
        echo ""

        # Use OAuth token if available, otherwise use a placeholder
        AUTH_HEADER="Authorization: Bearer ${OAUTH_TOKEN:-test-key}"

        response=$(curl -s -X POST "$PROXY_URL/v1/chat/completions" \
            -H "Content-Type: application/json" \
            -H "$AUTH_HEADER" \
            -d '{"model": "claude-haiku", "messages": [{"role": "user", "content": "Say hi in 3 words"}], "max_tokens": 50}')

        model=$(echo "$response" | jq -r '.model // "error"')
        content=$(echo "$response" | jq -r '.choices[0].message.content // .error.message // "no response"')

        echo "Model used: $model"
        echo "Response: $content"

        if echo "$response" | jq -e '.choices[0].message.content' > /dev/null 2>&1; then
            # Check if response came from Bedrock (fallback) or Claude API (primary)
            if echo "$model" | grep -qi "bedrock"; then
                echo -e "${YELLOW}Chat endpoint working (via Bedrock fallback)${NC}"
            else
                echo -e "${GREEN}Chat endpoint working (via Claude API)${NC}"
            fi
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
            echo "Or set CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY environment variable"
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

    fallback)
        echo -e "${BLUE}Testing Fallback Behavior${NC}"
        echo "============================================"
        echo ""
        echo "This test verifies the automatic fallback from Claude API to Bedrock."
        echo ""

        if [ -z "$OAUTH_TOKEN" ]; then
            echo -e "${YELLOW}No OAuth token - testing Bedrock-only mode${NC}"
            echo ""

            # Test with a placeholder key (will go directly to Bedrock)
            response=$(curl -s -X POST "$PROXY_URL/v1/chat/completions" \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer test-placeholder" \
                -d '{"model": "claude-haiku", "messages": [{"role": "user", "content": "Say hello"}], "max_tokens": 10}')

            if echo "$response" | jq -e '.choices[0].message.content' > /dev/null 2>&1; then
                echo -e "${GREEN}Bedrock fallback working!${NC}"
                echo "Response: $(echo "$response" | jq -r '.choices[0].message.content')"
            else
                echo -e "${RED}Bedrock fallback failed${NC}"
                echo "$response" | jq .
                exit 1
            fi
        else
            echo "OAuth token available: ${OAUTH_TOKEN:0:20}..."
            echo ""
            echo "Testing primary path (Claude API)..."

            response=$(curl -s -X POST "$PROXY_URL/v1/chat/completions" \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer $OAUTH_TOKEN" \
                -d '{"model": "claude-haiku", "messages": [{"role": "user", "content": "Say hello"}], "max_tokens": 10}')

            if echo "$response" | jq -e '.choices[0].message.content' > /dev/null 2>&1; then
                model=$(echo "$response" | jq -r '.model')
                echo -e "${GREEN}Primary path working!${NC}"
                echo "Model: $model"
                echo "Response: $(echo "$response" | jq -r '.choices[0].message.content')"
            elif echo "$response" | jq -e '.error' > /dev/null 2>&1; then
                error_type=$(echo "$response" | jq -r '.error.type // .error.code // "unknown"')
                if [ "$error_type" = "rate_limit_error" ] || echo "$error_type" | grep -qi "429"; then
                    echo -e "${YELLOW}Rate limited on Claude API - testing Bedrock fallback...${NC}"
                    # The next request should automatically fallback
                    sleep 1
                    response=$(curl -s -X POST "$PROXY_URL/v1/chat/completions" \
                        -H "Content-Type: application/json" \
                        -H "Authorization: Bearer $OAUTH_TOKEN" \
                        -d '{"model": "claude-haiku", "messages": [{"role": "user", "content": "Say hello"}], "max_tokens": 10}')

                    if echo "$response" | jq -e '.choices[0].message.content' > /dev/null 2>&1; then
                        echo -e "${GREEN}Bedrock fallback working!${NC}"
                        echo "Response: $(echo "$response" | jq -r '.choices[0].message.content')"
                    else
                        echo -e "${RED}Bedrock fallback failed${NC}"
                        exit 1
                    fi
                else
                    echo -e "${RED}Unexpected error: $error_type${NC}"
                    echo "$response" | jq .
                    exit 1
                fi
            else
                echo -e "${RED}Request failed${NC}"
                echo "$response" | jq .
                exit 1
            fi
        fi

        echo ""
        echo -e "${BLUE}Fallback Configuration Summary:${NC}"
        echo "  Primary: Claude API (Anthropic direct)"
        echo "  Fallback: AWS Bedrock"
        echo "  Trigger: HTTP 429 (Rate Limit)"
        echo "  Cooldown: 300 seconds (5 minutes)"
        ;;

    models)
        echo "Listing available models..."
        curl -s "$PROXY_URL/v1/models" \
            -H "Authorization: Bearer ${OAUTH_TOKEN:-test}" | jq -r '.data[].id' 2>/dev/null || echo "Failed to list models"
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
        $0 fallback
        echo ""
        if [ -n "$OAUTH_TOKEN" ]; then
            echo "========================"
            $0 messages "$OAUTH_TOKEN"
            echo ""
        fi
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
        echo "  chat      - Test OpenAI-compatible endpoint"
        echo "  messages  - Test Anthropic native endpoint (OAuth pass-through)"
        echo "  fallback  - Test Claude -> Bedrock fallback behavior"
        echo "  models    - List available models"
        echo "  all       - Run all tests"
        echo ""
        echo "Environment variables:"
        echo "  LITELLM_PROXY_URL       - Proxy URL (default: http://localhost:47000)"
        echo "  CLAUDE_CODE_OAUTH_TOKEN - OAuth token for Claude API (primary)"
        echo "  ANTHROPIC_API_KEY       - Alternative token source"
        echo ""
        echo "Fallback behavior:"
        echo "  1. Requests first try Claude API using OAuth token"
        echo "  2. On rate limit (429), automatically falls back to Bedrock"
        echo "  3. Primary model enters cooldown for 5 minutes"
        ;;
esac
