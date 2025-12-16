# Feature Plan: Automatic Claude API to Bedrock Fallback

## Executive Summary

Configure LiteLLM proxy to automatically fallback from Claude's direct API to AWS Bedrock when rate limits (429 errors) are encountered, enabling seamless operation without user intervention. This leverages LiteLLM's built-in fallback mechanisms with custom OAuth token passthrough.

## Requirements Analysis

### Functional Requirements

**FR-1: Automatic Rate Limit Detection**
- The system SHALL detect HTTP 429 (Rate Limit) errors from Claude's API
- The system SHALL recognize rate limit headers (X-RateLimit-*, Retry-After)
- The system SHALL differentiate between rate limits and other API errors

**FR-2: Seamless Fallback Mechanism**
- The system SHALL automatically retry requests on Bedrock when Claude API returns 429
- The system SHALL maintain request context during fallback
- The system SHALL preserve streaming behavior across fallback transitions

**FR-3: OAuth Token Management**
- The system SHALL extract CLAUDE_CODE_OAUTH_TOKEN from environment
- The system SHALL use OAuth tokens for Claude direct API calls
- The system SHALL use AWS credentials for Bedrock calls

**FR-4: Model Mapping**
- The system SHALL maintain 1:1 model mapping between Claude and Bedrock variants
- The system SHALL support all Claude models available on both platforms
- The system SHALL handle model aliasing (e.g., "claude-opus" → specific version)

**FR-5: Transparent Operation**
- The system SHALL provide identical API interface regardless of backend used
- The system SHALL not require client-side changes for fallback
- The system SHALL log fallback events for debugging

### Non-Functional Requirements

**NFR-1: Performance**
- Fallback decision latency: < 100ms
- No additional latency for successful primary requests
- Connection pooling for both Claude and Bedrock APIs

**NFR-2: Reliability**
- 99.9% availability when either backend is operational
- Graceful degradation when one backend fails
- Circuit breaker pattern to prevent cascade failures

**NFR-3: Observability**
- Structured logging of fallback events
- Metrics for primary vs fallback usage
- Alerting on high fallback rates

**NFR-4: Security**
- Secure storage of OAuth tokens and AWS credentials
- No token leakage in logs or error messages
- Credential rotation support without downtime

**NFR-5: Cost Optimization**
- Track usage costs per backend
- Allow cost-based routing preferences
- Support manual backend override for testing

## Architecture Design

### System Architecture

```
┌─────────────────┐
│  Claude Code    │
│   (Client)      │
└────────┬────────┘
         │ HTTP Request
         ▼
┌─────────────────────────────────────┐
│       LiteLLM Proxy Server          │
│  ┌─────────────────────────────┐   │
│  │   OAuth Passthrough Layer   │   │
│  │  (custom_auth.py)           │   │
│  └──────────┬──────────────────┘   │
│             │                       │
│  ┌──────────▼──────────────────┐   │
│  │   Router with Fallback      │   │
│  │   (config.yaml)             │   │
│  └──────────┬──────────────────┘   │
│             │                       │
│  ┌──────────▼──────────────────┐   │
│  │   Rate Limit Detection      │   │
│  │   (Built-in LiteLLM)        │   │
│  └──────────┬──────────────────┘   │
└─────────────┼───────────────────────┘
              │
     ┌────────┴────────┐
     ▼                 ▼
┌──────────┐     ┌──────────┐
│  Claude  │     │   AWS    │
│   API    │     │ Bedrock  │
└──────────┘     └──────────┘
```

### Component Design

**1. OAuth Token Injection**
- Modify `oauth_passthrough.py` to support environment variable fallback
- Implement token caching to reduce environment lookups
- Add token validation and refresh logic

**2. Fallback Configuration**
- Enhance `config.yaml` with rate-limit-specific fallback rules
- Configure retry policies with exponential backoff
- Set cooldown periods for rate-limited endpoints

**3. Rate Limit Detection**
- Leverage LiteLLM's built-in RateLimitError handling
- Parse Retry-After headers for intelligent retry scheduling
- Implement per-model rate limit tracking

**4. Monitoring Integration**
- Add Prometheus metrics for fallback events
- Create Grafana dashboard for visualization
- Implement alerting rules for high fallback rates

### Design Patterns Applied

- **Circuit Breaker**: Prevent cascading failures when Claude API is down
- **Retry with Exponential Backoff**: Intelligent retry strategy for transient failures
- **Strategy Pattern**: Swappable authentication strategies per backend
- **Proxy Pattern**: Transparent backend switching
- **Observer Pattern**: Event-driven fallback notifications

## Proactive Bug Identification

### Potential Issues and Mitigation

**🐛 Race Condition: Concurrent OAuth Token Refresh**
- **Risk**: Multiple threads refreshing expired tokens simultaneously
- **Mitigation**: Implement token refresh mutex with 30-second timeout
- **Testing**: Concurrent request stress test with expiring tokens

**🐛 Memory Leak: Unbounded Fallback Event Cache**
- **Risk**: Storing all fallback events in memory for metrics
- **Mitigation**: Implement sliding window cache (last 1000 events)
- **Testing**: Long-running load test with continuous fallbacks

**🐛 Cost Explosion: Bedrock Fallback Loop**
- **Risk**: Infinite fallback to more expensive Bedrock tier
- **Mitigation**: Implement daily cost limits and alerts
- **Testing**: Cost tracking integration tests

**🐛 Data Inconsistency: Streaming Response Interruption**
- **Risk**: Partial response when fallback occurs mid-stream
- **Mitigation**: Buffer initial response before committing to backend
- **Testing**: Streaming tests with forced mid-stream failures

**🐛 Authentication Failure: Token/Credential Expiry**
- **Risk**: Both OAuth token and AWS credentials expire simultaneously
- **Mitigation**: Proactive credential refresh 5 minutes before expiry
- **Testing**: Time-based expiry simulation tests

## Epic: Intelligent Rate Limit Fallback System

### Epic Description
As a Claude Code user, I want the LiteLLM proxy to automatically handle rate limits by falling back to AWS Bedrock, so that my workflow is never interrupted by API quotas.

### Success Metrics
- 0% user-visible rate limit errors
- < 500ms additional latency during fallback
- 95% of requests use primary Claude API (cost optimization)
- 100% request success rate when either backend is available

### Risks and Mitigations
- **Risk**: Increased costs from Bedrock usage
  - **Mitigation**: Cost alerting and daily limits
- **Risk**: Different model behaviors between backends
  - **Mitigation**: Model behavior testing suite
- **Risk**: AWS credential management complexity
  - **Mitigation**: AWS SSO integration with auto-refresh

## User Stories

### Story 1: Basic Fallback Configuration
**As a** developer  
**I want to** configure automatic fallback from Claude to Bedrock  
**So that** rate limits don't interrupt my work

**Acceptance Criteria:**
- ✓ Config file supports fallback rules for all Claude models
- ✓ OAuth token is automatically extracted from environment
- ✓ AWS credentials are configured via AWS CLI/SSO
- ✓ Fallback occurs within 1 second of rate limit error
- ✓ Original request succeeds via Bedrock

**Tasks:**
1. Update config.yaml with enhanced fallback configuration (2 hours)
2. Test fallback behavior with mock rate limits (2 hours)
3. Document configuration options (1 hour)

### Story 2: OAuth Token Environment Integration
**As a** Claude Code user  
**I want to** use my CLAUDE_CODE_OAUTH_TOKEN automatically  
**So that** I don't need to manage API keys manually

**Acceptance Criteria:**
- ✓ Token is read from CLAUDE_CODE_OAUTH_TOKEN environment variable
- ✓ Token is validated on startup
- ✓ Invalid tokens produce clear error messages
- ✓ Token refresh is handled automatically
- ✓ No token leakage in logs

**Tasks:**
1. Enhance oauth_passthrough.py with env variable support (3 hours)
2. Add token validation and caching logic (2 hours)
3. Implement secure logging filters (1 hour)

### Story 3: Intelligent Rate Limit Detection
**As a** system administrator  
**I want to** detect and respond to rate limits intelligently  
**So that** the system self-heals without intervention

**Acceptance Criteria:**
- ✓ 429 errors trigger immediate fallback
- ✓ Retry-After headers are respected
- ✓ Per-model rate limit tracking
- ✓ Cooldown periods prevent thundering herd
- ✓ Metrics track fallback frequency

**Tasks:**
1. Implement rate limit detection callback (3 hours)
2. Add per-model cooldown tracking (2 hours)
3. Create Prometheus metrics for monitoring (2 hours)

### Story 4: Cost-Aware Routing
**As a** platform owner  
**I want to** optimize costs across Claude and Bedrock  
**So that** we minimize API expenses

**Acceptance Criteria:**
- ✓ Cost per request is tracked for both backends
- ✓ Daily cost limits can be configured
- ✓ Alerts fire when costs exceed thresholds
- ✓ Manual backend override for testing
- ✓ Cost dashboard in Grafana

**Tasks:**
1. Implement cost tracking middleware (3 hours)
2. Add cost-based routing rules (2 hours)
3. Create Grafana cost dashboard (2 hours)

## Implementation Roadmap

### Phase 1: Core Fallback (Week 1)
- Configure basic fallback rules in config.yaml
- Test with manual rate limit simulation
- Validate OAuth token passthrough
- Document basic usage

### Phase 2: Enhanced Detection (Week 1)
- Implement intelligent rate limit detection
- Add retry-after header parsing
- Configure exponential backoff
- Add structured logging

### Phase 3: Monitoring & Optimization (Week 2)
- Deploy Prometheus metrics
- Create Grafana dashboards
- Implement cost tracking
- Add alerting rules

### Phase 4: Production Hardening (Week 2)
- Load testing with sustained traffic
- Chaos testing with forced failures
- Security audit of token handling
- Performance optimization

## Testing Strategy

### Unit Tests
- OAuth token extraction and validation
- Fallback rule configuration parsing
- Rate limit detection logic
- Cost calculation accuracy

### Integration Tests
- End-to-end request flow with fallback
- Streaming response handling
- Concurrent request processing
- Token refresh during active requests

### Performance Tests
- Load test with 100 req/s sustained
- Latency measurement during fallback
- Memory usage under high fallback rate
- Connection pool efficiency

### Chaos Tests
- Random backend failures
- Network partition simulation
- Token expiry during requests
- Partial response failures

## Configuration Examples

### Enhanced config.yaml
```yaml
# OAuth token configuration
litellm_settings:
  callbacks: [oauth_passthrough.proxy_handler_instance]
  custom_auth_token_env: CLAUDE_CODE_OAUTH_TOKEN  # NEW

# Enhanced router settings
router_settings:
  # Fallback configuration
  fallbacks:
    - {"claude-opus-4-5-20251101": ["claude-opus-4-5-20251101-bedrock"]}
  
  # Rate limit specific settings
  rate_limit_fallback:
    enabled: true
    detection_threshold: 1  # Fallback after 1 rate limit
    cooldown_time: 300      # 5 minute cooldown
    respect_retry_after: true
    max_retry_after: 3600  # Max 1 hour wait
  
  # Retry configuration
  retry_policy:
    RateLimitError:
      retries: 3
      backoff_factor: 2
      max_wait: 60
  
  # Cost optimization
  cost_tracking:
    enabled: true
    daily_limit: 100.00
    alert_threshold: 80.00
    prefer_primary: true
```

### Environment Setup Script
```bash
#!/bin/bash
# setup-fallback.sh

# Extract OAuth token from Claude Code
export CLAUDE_CODE_OAUTH_TOKEN=$(cat ~/.claude/token 2>/dev/null)

# Configure AWS credentials
aws sso login --profile bedrock-access
export AWS_PROFILE=bedrock-access
export AWS_REGION=us-west-2

# Start proxy with fallback
litellm --config enhanced-config.yaml \
  --port 8000 \
  --num_workers 4 \
  --health_check
```

## Monitoring Dashboard

### Key Metrics
- **Request Rate**: Primary vs Fallback breakdown
- **Error Rate**: 429 errors, fallback failures
- **Latency**: P50, P95, P99 by backend
- **Cost**: Hourly cost by model and backend
- **Availability**: Uptime per backend

### Alert Rules
- High fallback rate (>10% of traffic)
- Cost threshold exceeded (>$80/day)
- Both backends unavailable
- High latency (P95 > 5s)
- Token refresh failures

## Documentation Updates

### User Guide Additions
- Fallback configuration tutorial
- OAuth token setup guide
- AWS credential configuration
- Troubleshooting guide
- Cost optimization tips

### API Documentation
- Fallback behavior explanation
- Header requirements
- Error response formats
- Retry behavior
- Backend selection headers

## Security Considerations

### Token Management
- Never log OAuth tokens
- Rotate tokens every 30 days
- Use secure storage (keyring/vault)
- Implement token encryption at rest

### Network Security
- TLS 1.3 for all API calls
- Certificate pinning for Claude API
- Private endpoints for Bedrock
- Network segmentation

### Audit Logging
- Log all fallback events
- Track token usage patterns
- Monitor for unusual activity
- Compliance reporting

## Success Criteria

### Functional Success
- ✓ Zero user-visible rate limit errors
- ✓ Automatic fallback within 1 second
- ✓ All Claude models supported
- ✓ Transparent to Claude Code client

### Performance Success
- ✓ < 500ms fallback latency
- ✓ No memory leaks after 24h operation
- ✓ < 100MB memory footprint
- ✓ Support 1000 concurrent requests

### Operational Success
- ✓ Complete monitoring dashboard
- ✓ Automated alerts configured
- ✓ Documentation complete
- ✓ Runbook for common issues

## Conclusion

This feature plan provides a comprehensive approach to implementing automatic Claude API to Bedrock fallback in the LiteLLM proxy. The solution leverages LiteLLM's built-in capabilities while adding custom OAuth token handling and enhanced monitoring. The phased implementation approach ensures quick wins while building toward a production-ready system.

The key insight from research is that LiteLLM already supports the core fallback mechanism through its router configuration. The main implementation work focuses on:
1. Proper OAuth token extraction from environment
2. Enhanced rate limit detection and response
3. Monitoring and cost optimization
4. Production hardening and testing

With this configuration, Claude Code users will experience seamless operation even when hitting rate limits, with automatic and transparent fallback to AWS Bedrock.
