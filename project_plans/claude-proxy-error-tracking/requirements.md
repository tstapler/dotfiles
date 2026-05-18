# Requirements: Claude Proxy Error Tracking

**Status**: Ready for Implementation | **Phase**: 4 — Validation complete
**Created**: 2026-04-16
**Updated**: 2026-04-16

## Problem Statement

The claude-proxy currently has basic logging but no structured error tracking system. Recent changes have introduced new error types that are blocking proxy usage. Cannot correlate errors to specific conditions (provider, model, request patterns), making it difficult to diagnose issues and prioritize fixes.

**Who has this problem**: Solo practitioner using claude-proxy for API proxying across multiple providers (Bedrock, etc.)

## Success Criteria

**3-month measurable outcome**: Automated alert system that flags when new error types appear, enabling rapid diagnosis of novel failures and preventing extended proxy downtime.

## Scope

### Must Have (MoSCoW)

- **Unique error type identification and deduplication** — group similar errors together, recognize when a new type appears
- **Error metadata capture** — track provider, model, request context associated with each error type
- **Persistence layer** — store historical error data to identify trends and patterns over time
- **New error type alerting** — notification/detection when a previously unseen error signature appears

### Out of Scope

- Real-time dashboard UI (alerting only)
- Integration with external monitoring services (Datadog, etc.)
- Error rate SLO/SLA enforcement
- Automatic error remediation or retry logic

## Constraints

- **Tech stack**: Must use Python — integrate with existing `stapler-scripts/claude-proxy/*.py` codebase
- **Timeline**: Urgent — proxy is currently blocked by recent error types
- **Dependencies**:
  - Existing logging infrastructure (stdout/files)
  - `metrics.py` infrastructure (may extend or integrate)
  - No heavy external dependencies preferred (lightweight solution)

## Context

### Existing Work

- Basic logging exists but is not structured for error tracking
- `metrics.py` tracks some statistics but not error types or patterns
- Manual inspection of logs when issues arise
- No formal error classification or deduplication

### Immediate Trigger

Recent change introduced new error types that broke proxy usage. Example from context:
```
API Error: 400 {"detail":"Bedrock validation error: An error occurred (ValidationException)
when calling the InvokeModel operation: context_management: Extra inputs are not permitted"}
```

### Stakeholders

- Primary user: Solo practitioner (Tyler) using claude-proxy for daily AI development work
- Indirect: Any system or workflow dependent on proxy availability

## Research Dimensions Completed

- [x] **Stack** — Python error tracking libraries, deduplication strategies, alerting mechanisms → `research/findings-stack.md`
- [x] **Features** — How other proxy systems handle error classification, error signature extraction patterns → `research/findings-features.md`
- [x] **Architecture** — Integration points with existing proxy code, storage options (SQLite, JSON, in-memory), alerting channels → `research/findings-architecture.md`
- [x] **Pitfalls** — Over-alerting on transient errors, fingerprinting instability, storage bloat, performance impact on proxy latency → `research/findings-pitfalls.md`
- [x] **Synthesis** — Consolidated findings with recommendation → `research/synthesis.md`
- [x] **Implementation Plan** — Story/task breakdown with ADRs → `implementation/plan.md`
