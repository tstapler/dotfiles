---
title: Implement Feature Using Six-Phase Methodology
description: Systematically implement a new feature following research-backed best practices from the Six-Phase Software Implementation Methodology
arguments: [feature_description]
---

# Implement Feature: $@

Implement the requested feature following the **Six-Phase Software Implementation Methodology** - a research-backed framework that balances quality, speed, and maintainability. This methodology synthesizes proven practices from Clean Code, Test-Driven Development, The Pragmatic Programmer, and DORA research.

**Key Insight**: Elite performers achieve multiple daily deployments with <15% failure rates not by skipping phases, but by making each phase efficient through automation, clear standards, and continuous integration.

---

## Phase 1: Understanding & Planning (10-15% of effort)

**Purpose**: Ensure clear requirements and well-thought-out approach before writing code.

### Activities

1. **Clarify Requirements** (use AskUserQuestion if needed):
   - What is the user value and business goal?
   - What are the specific acceptance criteria?
   - What defines success? (metrics, user feedback)
   - What are the constraints? (performance, security, compliance)

2. **Explore Domain** (use Explore agent for thorough investigation):
   - Search for similar features in the codebase
   - Understand existing patterns and conventions
   - Identify reusable components and utilities
   - Find examples of correct implementation

3. **Design Approach**:
   - Sketch high-level solution architecture
   - Identify data flow and service interactions
   - Consider edge cases and failure modes
   - Plan for observability (logging, metrics, tracing)

4. **Plan Testing Strategy**:
   - Map test scenarios to acceptance criteria
   - Identify unit, integration, and E2E test needs
   - Consider edge cases: null, empty, boundary, concurrent
   - Plan manual testing steps

5. **Analyze Dependencies**:
   - Required libraries, services, APIs
   - Database schema changes needed
   - Configuration changes required
   - Feature flag setup (if applicable)

### Success Criteria
- ✅ Can explain feature in 2-3 clear sentences
- ✅ Understand both happy path and edge cases
- ✅ Have high-level design sketch
- ✅ Test scenarios mapped to acceptance criteria
- ✅ Dependencies identified

### Red Flags to Watch For
- ⚠️ Vague acceptance criteria without measurable success metrics
- ⚠️ Unclear user value proposition
- ⚠️ Missing context about constraints or dependencies
- ⚠️ Pressure to "start coding immediately" without planning

**Use TodoWrite to create Phase 1 tasks and track progress through this phase.**

---

## Phase 2: Implementation (40-50% of effort)

**Purpose**: Transform requirements into working, tested code following established best practices.

### Test-Driven Development Approach

1. **Red-Green-Refactor Cycle**:
   - **Red**: Write failing test for next requirement
   - **Green**: Implement minimum code to make test pass
   - **Refactor**: Clean up while keeping tests green
   - Repeat for each acceptance criterion

2. **Incremental Development**:
   - Make small, logical commits (each builds and passes tests)
   - Use tracer bullets: Build narrow end-to-end functionality first
   - Follow Boy Scout Rule: Leave code cleaner than you found it
   - Apply YAGNI: Implement only what's required now

3. **Code Quality Standards**:
   - Follow team style guide and linting rules
   - Write readable, self-documenting code
   - Add comments only for complex logic (why, not what)
   - Use meaningful variable and function names

4. **Edge Case Handling**:
   - Explicit validation for inputs
   - Meaningful error messages
   - Boundary condition handling
   - Null/empty/undefined checks

5. **Testing Coverage**:
   - Unit tests for business logic
   - Integration tests for service interactions
   - E2E tests for critical user flows
   - Aim for 80%+ coverage on new code

6. **Local Verification**:
   - Test manually against each acceptance criterion
   - Verify edge cases work correctly
   - Check error messages are helpful
   - Test performance with realistic data volumes

### Modern Practices to Apply

- **Feature Flags**: Enable progressive rollout and safe experimentation
- **Tracer Bullets**: Build end-to-end skeleton first, then fill in details
- **Boy Scout Rule**: Leave code better than you found it
- **YAGNI**: Don't build what you don't need yet

### Success Criteria
- ✅ All acceptance criteria met with passing tests
- ✅ Code follows team conventions (linting clean)
- ✅ Edge cases handled with meaningful errors
- ✅ Each commit builds and passes tests
- ✅ 80%+ test coverage on new code
- ✅ Manual testing confirms functionality

**Use TodoWrite to track implementation tasks. Mark each criterion as completed when done.**

---

## Phase 3: Review & Refinement (10-15% of effort)

**Purpose**: Ensure code quality through self-review and comprehensive documentation before peer review.

### Self-Review Checklist

1. **Code Quality**:
   - Read every line as if reviewing someone else's code
   - Remove debug code, commented sections, console logs
   - Check for hardcoded values (use config/env instead)
   - Verify error handling is comprehensive
   - Ensure code follows DRY principle

2. **Testing Verification**:
   - All tests passing (unit, integration, E2E)
   - Linting clean (no warnings or errors)
   - Coverage meets threshold (80%+)
   - Edge cases covered by tests
   - Test names are descriptive

3. **Documentation Updates**:
   - Update README if new features/setup needed
   - Add/update API documentation
   - Update architecture diagrams if structure changed
   - Add inline comments for complex logic only
   - Update CHANGELOG if project uses one

4. **Security & Performance**:
   - No secrets or credentials in code
   - SQL injection / XSS vulnerabilities checked
   - Performance acceptable for expected load
   - Resource cleanup (connections, files, memory)
   - Consider caching where appropriate

### PR Description (Use SUCCESS Framework)

Create a comprehensive PR description:

```markdown
## Ticket
[TICKET-123](link-to-ticket)

## Summary (Simple)
1-2 sentences explaining what this PR does and why it matters.

## Changes (Unexpected)
- Key change 1 and why it's interesting
- Key change 2 and its impact
- Focus on non-obvious changes reviewers should know about

## Context (Concrete)
- **Background**: Why was this needed?
- **Approach**: What alternatives were considered?
- **Trade-offs**: What decisions were made and why?

## Testing (Credible)
### Automated Tests
- Unit tests: [list key test scenarios]
- Integration tests: [list integration scenarios]
- Coverage: X% (target: 80%+)

### Manual Testing Steps
1. Step-by-step instructions to verify functionality
2. Include test data or setup needed
3. Expected results for each step

## Acceptance Criteria (Emotional - User Impact)
- [x] Criterion 1 met - Users can now...
- [x] Criterion 2 met - This solves...
- [x] Edge cases handled - Prevents...

## Screenshots/Videos (Story)
[Visual evidence of functionality - before/after if applicable]

## Deployment Notes
- Configuration changes needed: [list any]
- Database migrations: [list any]
- Feature flag: [name and initial state]
- Rollback plan: [how to quickly disable if needed]
```

### Success Criteria
- ✅ Would approve this PR if you were the reviewer
- ✅ All tests passing, linting clean
- ✅ No hardcoded values, secrets, or TODOs
- ✅ Documentation current and accurate
- ✅ PR description enables understanding in 2-3 minutes

**Self-review catches 50% of issues before peer review - don't skip this!**

---

## Phase 4: Code Review & Iteration (10-20% of effort)

**Purpose**: Leverage team expertise to improve code quality and share knowledge.

### During Review

1. **Respond to Feedback**:
   - Acknowledge each comment promptly
   - Ask clarifying questions if unclear
   - Discuss respectfully if you disagree
   - Explain trade-offs and design decisions
   - Aim for same-day response to keep PR moving

2. **Make Improvements**:
   - Address comments thoroughly
   - Add tests if reviewer identified gaps
   - Improve documentation if needed
   - Refactor if better approach suggested
   - Push changes promptly

3. **Keep PR Moving**:
   - Don't let reviews go stale (respond within 4-8 hours)
   - Escalate if blocked on decisions
   - Request re-review after addressing comments
   - Communicate timeline constraints

### Best Practices

- **Smaller PRs** (<500 lines) get reviewed faster and better
- **Be respectful** - code review is collaborative, not adversarial
- **Explain trade-offs** - help reviewers understand your decisions
- **Learn from feedback** - reviewers provide valuable perspective

### Anti-Patterns to Avoid

- ❌ Defensive responses ("but it works!")
- ❌ Letting PRs sit for days without response
- ❌ Making massive changes without discussion
- ❌ Taking feedback personally

### Success Criteria
- ✅ All review comments addressed or discussed
- ✅ Required approvals received
- ✅ No unresolved conversations
- ✅ Reviewer confidence in changes

**Code review catches 60-80% of defects before production - embrace the feedback!**

---

## Phase 5: Deployment & Validation (5-10% of effort)

**Purpose**: Safely deploy code to production and verify it works as expected under real conditions.

### Pre-Merge Checks

1. **CI/CD Validation**:
   - All automated checks passing
   - No merge conflicts
   - Branch up-to-date with base branch
   - Required approvals obtained

2. **Pre-Deployment Preparation**:
   - Review rollback plan
   - Verify monitoring alerts configured
   - Confirm feature flag setup (if using)
   - Notify stakeholders of deployment timing

### Deployment Execution

1. **Deploy to Staging First** (if available):
   - Validate functionality in production-like environment
   - Test each acceptance criterion
   - Check error rates and performance
   - Verify integrations work correctly

2. **Production Deployment**:
   - Merge PR (triggers deployment pipeline)
   - Monitor deployment pipeline for errors
   - Watch logs for immediate issues
   - Verify deployment completed successfully

3. **Progressive Rollout** (if using feature flags):
   - Start at 10% of traffic
   - Monitor for 15-30 minutes
   - Increase to 50% if no issues
   - Monitor for another 15-30 minutes
   - Full rollout (100%) after confidence established

### Post-Deployment Validation

**Critical: First 30 minutes after deployment**

1. **Functional Verification**:
   - Test each acceptance criterion in production
   - Verify feature works for real users
   - Check edge cases behave correctly
   - Confirm integrations working

2. **Monitoring Checks**:
   - **Error Rates**: No spikes in exceptions
   - **Performance**: Response times within limits
   - **Logs**: No unexpected errors or warnings
   - **Metrics**: Key metrics tracking as expected
   - **Resource Utilization**: CPU/memory/DB within normal range

3. **Rollback if Needed**:
   - Disable feature flag immediately if issues detected
   - Or revert deployment if no feature flag
   - Document what went wrong
   - Plan fix and re-deployment

### Success Criteria
- ✅ Feature works in production for real users
- ✅ No error rate spikes or performance degradation
- ✅ All acceptance criteria validated in production
- ✅ Monitoring shows healthy metrics
- ✅ Stakeholders notified of successful deployment

**The first 30 minutes are critical - stay vigilant!**

---

## Phase 6: Post-Deployment & Learning (5-10% of effort)

**Purpose**: Monitor impact, address technical debt, and learn from the implementation experience.

### First 24-48 Hours: Active Monitoring

1. **Monitor Impact**:
   - Check analytics for usage patterns
   - Review user feedback (support tickets, comments)
   - Watch error rates and performance metrics
   - Verify business metrics moving as expected

2. **Address Issues Quickly**:
   - Respond to any user-reported problems
   - Fix bugs discovered in production
   - Adjust monitoring if gaps discovered
   - Communicate status to stakeholders

### Technical Debt Management

1. **Document Intentional Shortcuts**:
   - Create tickets for TODOs and technical debt
   - Explain WHY shortcut was taken
   - Specify WHEN to address (timeline/trigger)
   - Prioritize based on risk and impact

2. **Never Commit TODO Comments**:
   - Do it now, or create a ticket
   - TODOs become permanent if not tracked
   - Make technical debt visible to team

### Retrospective & Learning

1. **What Went Well?**
   - Practices that worked effectively
   - Tools or approaches that helped
   - Collaboration that was productive
   - Things to repeat next time

2. **What Could Improve?**
   - Bottlenecks or blockers encountered
   - Estimation accuracy (too high/low?)
   - Process gaps or inefficiencies
   - Skills or knowledge gaps identified

3. **What Did We Learn?**
   - Domain knowledge gained
   - Technical insights discovered
   - Patterns or anti-patterns identified
   - Team dynamics observations

4. **Action Items**:
   - Document lessons learned
   - Share knowledge with team
   - Update documentation/patterns
   - Plan improvements for next sprint

### Success Criteria
- ✅ Feature performing as expected in production
- ✅ Technical debt tracked and prioritized
- ✅ Lessons documented for future reference
- ✅ Team has clear improvements to implement
- ✅ User feedback positive or issues addressed

**Learning from each implementation compounds over time - invest in reflection!**

---

## Agent Integration Strategy

Use specialized agents throughout implementation:

### Phase 1: Planning
- **Explore agent**: Search codebase for similar patterns and examples
  - "Find implementations of similar features"
  - "How does the existing authentication system work?"
- **knowledge-synthesis agent**: Research external best practices
  - "Research best practices for rate limiting in REST APIs"
  - "Find documentation on PostgreSQL connection pooling"

### Phase 2: Implementation
- **Direct implementation**: For straightforward features where approach is clear
- **Explore agent**: When you need to understand existing patterns
- **code-refactoring agent**: When improving existing code structure

### Phase 3: Review & Refinement
- **pr-reviewer agent**: Automated code review before submitting
  - Catches common issues
  - Suggests improvements
  - Validates against best practices

### Phase 4: Code Review
- **Direct collaboration**: Human reviewers provide best feedback
- **Explore agent**: If questions arise about other parts of codebase

### Phase 5: Deployment
- **Direct execution**: Follow deployment procedures
- **github-debugger agent**: If CI/CD issues arise

### Phase 6: Post-Deployment
- **knowledge-synthesis agent**: Document lessons learned as zettels
- **Explore agent**: Investigate if issues found in production

---

## Time Allocation Guidance

Based on research from Brooks, DORA, and modern studies:

- **Phase 1 (Planning)**: 10-15% of effort
  - 15-30 minutes prevents hours of rework
  - Catches ambiguity when it's cheap to fix

- **Phase 2 (Implementation)**: 40-50% of effort
  - Includes writing tests (~50% of implementation time)
  - Focus on incremental progress

- **Phase 3 (Review)**: 10-15% of effort
  - Self-review catches 50% of issues
  - Saves reviewer time and review cycles

- **Phase 4 (Code Review)**: 10-20% of effort
  - Catches 60-80% of defects before production
  - Facilitates knowledge transfer

- **Phase 5 (Deployment)**: 5-10% of effort
  - First 30 minutes critical for catching issues
  - Progressive rollout limits risk

- **Phase 6 (Learning)**: 5-10% of effort
  - Compounds improvements over time
  - Makes next feature easier

**Elite performers don't skip phases - they make each phase efficient!**

---

## Common Anti-Patterns to Avoid

### ❌ Skipping Planning ("Let's Just Start Coding")
**Impact**: 2-10x longer total implementation time due to rework
**Solution**: Invest 10-15% upfront; saves 50-100% in rework

### ❌ Deferring Testing ("I'll Add Tests Later")
**Impact**: 40-80% more production defects, 60% more maintenance time
**Solution**: Test-first (TDD) or test-immediately-after approach

### ❌ Massive Pull Requests (>500 Lines)
**Impact**: Slower reviews (days not hours), lower quality feedback
**Solution**: Break into smaller PRs using feature flags

### ❌ Skipping Self-Review
**Impact**: 50% more review cycles, slower approval
**Solution**: Always self-review before submitting

### ❌ Ignoring Edge Cases
**Impact**: Edge cases become production bugs when users find them
**Solution**: Systematic edge case analysis (null, empty, boundary, concurrent)

### ❌ Not Monitoring After Deployment
**Impact**: Silent failures go undetected until users complain
**Solution**: Active monitoring for first 24-48 hours minimum

### ❌ Accumulating TODO Comments
**Impact**: TODOs never get done, become permanent technical debt
**Solution**: Do it now or create a ticket (never commit TODOs)

---

## Workflow Summary

Use TodoWrite to track progress through these phases:

```
Phase 1: Understanding & Planning
├─ [ ] Clarify requirements and acceptance criteria
├─ [ ] Explore domain using Explore agent
├─ [ ] Design high-level approach
├─ [ ] Plan testing strategy
└─ [ ] Identify dependencies

Phase 2: Implementation
├─ [ ] Set up feature flag (if applicable)
├─ [ ] Write failing test (Red)
├─ [ ] Implement minimum code (Green)
├─ [ ] Refactor for quality
├─ [ ] Repeat for each acceptance criterion
├─ [ ] Handle edge cases
└─ [ ] Manual verification

Phase 3: Review & Refinement
├─ [ ] Self-review all changes
├─ [ ] Remove debug code and TODOs
├─ [ ] Update documentation
├─ [ ] Run pr-reviewer agent
└─ [ ] Create comprehensive PR description

Phase 4: Code Review & Iteration
├─ [ ] Submit PR for review
├─ [ ] Respond to feedback promptly
├─ [ ] Make requested improvements
└─ [ ] Obtain required approvals

Phase 5: Deployment & Validation
├─ [ ] Verify all CI/CD checks passing
├─ [ ] Deploy to staging (if available)
├─ [ ] Deploy to production
├─ [ ] Progressive rollout (if using feature flags)
├─ [ ] Validate each acceptance criterion
└─ [ ] Monitor metrics for 30+ minutes

Phase 6: Post-Deployment & Learning
├─ [ ] Monitor for 24-48 hours
├─ [ ] Create tickets for technical debt
├─ [ ] Document lessons learned
└─ [ ] Share knowledge with team
```

---

## Success Indicators

### Individual Developer Level
- ✅ Estimation accuracy improves over time (±50% → ±20%)
- ✅ PR review cycles decrease (3-4 cycles → 1-2 cycles)
- ✅ Production defects decrease (10% → <2% of features)
- ✅ Self-review catches most issues before peer review
- ✅ Consistently delivers working features without surprises

### Team Level
- ✅ Predictable velocity sprint-over-sprint
- ✅ High code review quality (thorough feedback, fast turnaround)
- ✅ Low production defect rate (<5% of deployed features)
- ✅ Clear patterns emerge naturally through implementation
- ✅ Knowledge sharing occurs organically

### Organizational Level (DORA Elite Performers)
- ✅ Multiple daily deployments with confidence
- ✅ <15% change failure rate
- ✅ <1 hour mean time to restore service
- ✅ High developer satisfaction
- ✅ Clear career progression as quality standards raise

---

## Implementation Notes

1. **ALWAYS use TodoWrite** to track workflow and progress through phases
2. **Adjust time allocation** based on feature complexity and context
3. **Use specialized agents** proactively throughout implementation
4. **Don't skip phases** - elite performers make each phase efficient, not optional
5. **Learn from each feature** - continuous improvement compounds over time
6. **Share knowledge** - document patterns and lessons learned

---

## Related Resources

- Six-Phase Software Implementation Methodology (in knowledge base)
- Feature Implementation Cheat Sheet for Developers
- Test Driven Development: By Example
- Clean Code: A Handbook of Agile Software Craftsmanship
- The Pragmatic Programmer: From Journeyman to Master
- DORA Metrics and Elite Performer Characteristics

---

**Remember**: Elite performers achieve speed through systematic quality, not by cutting corners. Follow the methodology, use the right agents, and build features that last.
