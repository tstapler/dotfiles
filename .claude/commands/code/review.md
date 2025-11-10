---
title: Code Review
description: Comprehensive code review using specialized agents in parallel to identify improvements, then track findings with project-coordinator
arguments: [path]
---

# Comprehensive Code Review

Perform a multi-dimensional code review using specialized agents in parallel, then consolidate findings through the project-coordinator agent for systematic remediation.

## Review Dimensions

This command orchestrates multiple review perspectives simultaneously:

### 1. **Testing Quality Review** (spring-boot-testing agent)
- Test anti-patterns and smells
- Test coverage appropriateness (integration vs unit)
- TestContainers configuration (ADR-0017)
- Mocking strategy (ADR-0016)
- Test confidence and fragility

### 2. **Code Quality Review** (code-refactoring agent)
- SOLID principles adherence
- Design patterns usage
- Code duplication and complexity
- Clean Code principles
- Refactoring opportunities

### 3. **Architecture Review** (software-planner agent)
- Architectural patterns consistency
- Dependency management
- Layer separation and boundaries
- Domain-driven design principles
- Technical debt identification

### 4. **Database Review** (postgres-optimizer agent)
- Query optimization opportunities
- Index usage and performance
- Schema design and normalization
- PostgreSQL-specific optimizations
- Connection pooling configuration

## Usage

Review a specific directory:
```
/code:review src/main/java/com/example/service
```

Review the entire project:
```
/code:review .
```

Review a specific component:
```
/code:review src/main/java/com/example/UserService.java
```

## Implementation Steps

### Step 1: Parallel Agent Invocation

Launch specialized agents in parallel to review different aspects:

**Testing Quality Agent**:
```
Task(
  subagent_type: "spring-boot-testing",
  description: "Review test quality in ${1:-.}",
  prompt: """
  Review all tests in ${1:-.} for quality issues:

  1. Identify test anti-patterns:
     - Implementation coupling (mocking TransactionTemplate, ArgumentCaptor)
     - Inappropriate mocking (over-mocking internal collaborators)
     - Environment mismatches (H2 instead of PostgreSQL)
     - Coverage theater (high coverage, low confidence)
     - Fragile tests (breaking on refactoring)

  2. Verify ADR compliance:
     - ADR-0016: Integration tests for persistence layer
     - ADR-0017: PostgreSQL TestContainers configuration
     - Proper @AutoConfigureTestDatabase(replace = NONE) usage

  3. Assess test confidence:
     - Do tests verify behavior or implementation?
     - Are tests coupled to internal details?
     - Would these tests catch real production bugs?

  4. Provide structured findings:
     - Location (file:line)
     - Issue description
     - Impact (confidence, fragility, maintainability)
     - Recommended fix following ADRs
     - Priority (Critical/High/Medium/Low)
     - Effort estimate (Small/Medium/Large)

  Return findings in structured format for project-coordinator consolidation.
  """
)
```

**Code Quality Agent**:
```
Task(
  subagent_type: "code-refactoring",
  description: "Review code quality in ${1:-.}",
  prompt: """
  Review code in ${1:-.} for quality and refactoring opportunities:

  1. SOLID Principles:
     - Single Responsibility violations
     - Open/Closed principle issues
     - Liskov Substitution violations
     - Interface Segregation opportunities
     - Dependency Inversion improvements

  2. Clean Code:
     - Method length and complexity
     - Naming clarity and consistency
     - Code duplication (DRY violations)
     - Magic numbers and hardcoded values
     - Comment quality and necessity

  3. Design Patterns:
     - Appropriate pattern usage
     - Missing pattern opportunities
     - Anti-patterns present

  4. Provide structured findings:
     - Location (file:line)
     - Issue description
     - Impact on maintainability
     - Recommended refactoring
     - Priority (Critical/High/Medium/Low)
     - Effort estimate (Small/Medium/Large)

  Return findings in structured format for project-coordinator consolidation.
  """
)
```

**Architecture Review Agent**:
```
Task(
  subagent_type: "software-planner",
  description: "Review architecture in ${1:-.}",
  prompt: """
  Review architecture and design in ${1:-.}:

  1. Architectural Patterns:
     - Layered architecture consistency
     - Dependency flow (layers, modules)
     - Boundary enforcement
     - Separation of concerns

  2. Domain-Driven Design:
     - Entity and value object design
     - Aggregate boundaries
     - Domain logic placement
     - Repository patterns

  3. Technical Debt:
     - Temporary workarounds
     - TODOs and FIXMEs
     - Incomplete implementations
     - Deprecated code usage

  4. Dependency Management:
     - Circular dependencies
     - Unnecessary coupling
     - Interface vs implementation dependencies

  5. Provide structured findings:
     - Location (file:line or module)
     - Issue description
     - Architectural impact
     - Recommended approach
     - Priority (Critical/High/Medium/Low)
     - Effort estimate (Small/Medium/Large)

  Return findings in structured format for project-coordinator consolidation.
  """
)
```

**Database Review Agent** (if applicable):
```
Task(
  subagent_type: "postgres-optimizer",
  description: "Review database code in ${1:-.}",
  prompt: """
  Review database-related code in ${1:-.}:

  1. Query Performance:
     - N+1 query problems
     - Missing indexes
     - Inefficient queries
     - Pagination issues

  2. Schema Design:
     - Normalization issues
     - Foreign key usage
     - Index strategy
     - Data types optimization

  3. PostgreSQL Usage:
     - JSONB opportunities
     - Array types usage
     - Window functions
     - Native features underutilization

  4. Transaction Management:
     - Transaction boundary appropriateness
     - Isolation level issues
     - Deadlock risks

  5. Provide structured findings:
     - Location (file:line or query)
     - Issue description
     - Performance impact
     - Recommended optimization
     - Priority (Critical/High/Medium/Low)
     - Effort estimate (Small/Medium/Large)

  Return findings in structured format for project-coordinator consolidation.
  """
)
```

### Step 2: Consolidate Findings

After all parallel agents complete, consolidate their findings:

**Wait for all agents to complete**, then compile results:
```markdown
# Code Review Report

**Review Date**: [Current date]
**Path Reviewed**: ${1:-.}
**Review Dimensions**: Testing, Code Quality, Architecture, Database

---

## Executive Summary

- **Total Issues Found**: [count]
- **Critical**: [count] - Immediate attention required
- **High**: [count] - Should address soon
- **Medium**: [count] - Plan for future sprint
- **Low**: [count] - Nice to have improvements

---

## Findings by Category

### Testing Quality Issues
[Findings from spring-boot-testing agent]

#### Critical
- [Issue 1 with location, description, impact, fix]

#### High
- [Issue 2 with location, description, impact, fix]

#### Medium
- [Issue 3 with location, description, impact, fix]

---

### Code Quality Issues
[Findings from code-refactoring agent]

#### Critical
- [Issue 4 with location, description, impact, fix]

#### High
- [Issue 5 with location, description, impact, fix]

---

### Architecture Issues
[Findings from software-planner agent]

#### Critical
- [Issue 6 with location, description, impact, fix]

---

### Database Performance Issues
[Findings from postgres-optimizer agent]

#### Critical
- [Issue 7 with location, description, impact, fix]

---

## Recommendations by Priority

### Critical (Fix Immediately)
1. [Issue] - [Location] - [Estimated effort]
2. [Issue] - [Location] - [Estimated effort]

### High (Address Soon)
1. [Issue] - [Location] - [Estimated effort]
2. [Issue] - [Location] - [Estimated effort]

### Medium (Plan for Next Sprint)
1. [Issue] - [Location] - [Estimated effort]

### Low (Nice to Have)
1. [Issue] - [Location] - [Estimated effort]

---

## Effort Summary

- **Total Estimated Effort**: [hours/days]
- **Critical Issues**: [hours]
- **High Issues**: [hours]
- **Medium Issues**: [hours]
- **Low Issues**: [hours]

---

## Related ADRs and Standards

- ADR-0016: Integration Tests Over Mocked Persistence
- ADR-0017: PostgreSQL TestContainers for Database Tests
- Clean Code principles
- SOLID principles
- Domain-Driven Design patterns
```

### Step 3: Invoke Project Coordinator

Automatically delegate consolidated findings to project-coordinator:

```
Task(
  subagent_type: "project-coordinator",
  description: "Track code review findings",
  prompt: """
  Document the following code review findings for systematic remediation:

  [Insert consolidated Code Review Report from Step 2]

  Please use the AIC framework to:

  1. **Create Project Structure**:
     - Organize findings by category and priority
     - Create ATOMIC tasks for each issue
     - Group related issues for batch remediation
     - Establish dependencies between tasks

  2. **Prioritization Strategy**:
     - Critical: Immediate blockers or severe technical debt
     - High: Significant impact on maintainability or performance
     - Medium: Moderate improvements with good ROI
     - Low: Nice-to-have refinements

  3. **Remediation Planning**:
     - Break down large issues into smaller tasks
     - Estimate effort accurately (Small/Medium/Large)
     - Identify quick wins vs long-term improvements
     - Schedule work across sprints

  4. **Progress Tracking**:
     - Create task hierarchy in TODO.md or tracking system
     - Define clear success criteria for each task
     - Enable progress measurement over time
     - Track technical debt reduction metrics

  5. **Context Preservation**:
     - Link to specific code locations
     - Reference relevant ADRs and standards
     - Document recommended approaches
     - Capture rationale for prioritization

  Expected deliverables:
  - Structured project plan for code improvements
  - ATOMIC tasks organized by priority and effort
  - Clear next actions for developers
  - Progress tracking mechanism
  - Technical debt metrics baseline
  """
)
```

## Expected Output

### 1. Comprehensive Review Report
- **Multi-dimensional analysis** from specialized agents
- **Structured findings** with locations, impacts, and fixes
- **Prioritized recommendations** (Critical → Low)
- **Effort estimates** for each issue
- **ADR and standards references**

### 2. Project Tracking Integration
- **ATOMIC tasks** created via project-coordinator
- **Organized by priority** and effort
- **Grouped for efficiency** (batch similar fixes)
- **Progress tracking** enabled
- **Technical debt baseline** established

### 3. Actionable Next Steps
- Clear priorities for immediate work
- Batch remediation opportunities identified
- Long-term improvement roadmap
- Measurable progress metrics

## Parallel Execution Strategy

This command uses **parallel agent invocation** for efficiency:

1. **Launch all review agents simultaneously** (Step 1)
   - Testing agent reviews tests
   - Quality agent reviews code structure
   - Architecture agent reviews design
   - Database agent reviews data layer

2. **Wait for all agents to complete**
   - Each agent works independently
   - No blocking dependencies between reviews
   - Maximizes review throughput

3. **Consolidate and coordinate** (Steps 2-3)
   - Merge findings from all agents
   - Eliminate duplicates
   - Prioritize across dimensions
   - Create unified remediation plan

**Performance**:
- Sequential review: ~20-40 minutes (4 agents × 5-10 min each)
- Parallel review: ~5-10 minutes (longest agent)
- **Time savings**: 75-80% faster reviews

## Success Criteria

This command is successful when:
- ✅ All review dimensions complete (testing, quality, architecture, database)
- ✅ Findings are consolidated with clear priorities
- ✅ Recommendations include locations, impacts, and fixes
- ✅ Project-coordinator creates tracking structure
- ✅ Developers have clear next actions

## Integration with Other Commands

This command works well with:
- `/quality:find-test-smells` - Specialized test analysis
- `/code:refactor` - Execute recommended refactorings
- `/quality:architecture-review` - Deep architectural analysis
- `/plan:feature` - Plan improvements as features

## Notes

- **Comprehensive but efficient**: Parallel execution keeps reviews fast
- **Multi-dimensional perspective**: Different agents catch different issues
- **Actionable output**: Not just problems, but specific solutions
- **Trackable progress**: Project-coordinator enables systematic improvement
- **Standards-based**: References ADRs and industry best practices
- **Effort-aware**: Estimates help prioritize based on ROI

Use this command for:
- Pre-merge code reviews
- Technical debt assessment
- Quality audits
- Onboarding code walkthroughs
- Architecture validation
