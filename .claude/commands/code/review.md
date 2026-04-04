---
description: Comprehensive code review using specialized agents in parallel to identify
  improvements, then track findings with project-coordinator
prompt: "# Comprehensive Code Review\n\nPerform a multi-dimensional code review using\
  \ specialized agents in parallel, then consolidate findings through the project-coordinator\
  \ agent for systematic remediation.\n\n## Review Dimensions\n\nThis command orchestrates\
  \ multiple review perspectives simultaneously:\n\n### 1. **Testing Quality Review**\
  \ (spring-boot-testing agent)\n- Test anti-patterns and smells\n- Test coverage\
  \ appropriateness (integration vs unit)\n- TestContainers configuration (ADR-0017)\n\
  - Mocking strategy (ADR-0016)\n- Test confidence and fragility\n\n### 2. **Code\
  \ Quality Review** (code-refactoring agent)\n- SOLID principles adherence\n- Design\
  \ patterns usage\n- Code duplication and complexity\n- Clean Code principles\n-\
  \ Refactoring opportunities\n\n### 3. **Architecture Review** (software-planner\
  \ agent)\n- Architectural patterns consistency\n- Dependency management\n- Layer\
  \ separation and boundaries\n- Domain-driven design principles\n- Technical debt\
  \ identification\n\n### 4. **Database Review** (postgres-optimizer agent)\n- Query\
  \ optimization opportunities\n- Index usage and performance\n- Schema design and\
  \ normalization\n- PostgreSQL-specific optimizations\n- Connection pooling configuration\n\
  \n## Usage\n\nReview a specific directory:\n```\n/code:review src/main/java/com/example/service\n\
  ```\n\nReview the entire project:\n```\n/code:review .\n```\n\nReview a specific\
  \ component:\n```\n/code:review src/main/java/com/example/UserService.java\n```\n\
  \n## Implementation Steps\n\n### Step 1: Parallel Agent Invocation\n\nLaunch specialized\
  \ agents in parallel to review different aspects:\n\n**Testing Quality Agent**:\n\
  ```\nTask(\n  subagent_type: \"spring-boot-testing\",\n  description: \"Review test\
  \ quality in ${1:-.}\",\n  prompt: \"\"\"\n  Review all tests in ${1:-.} for quality\
  \ issues:\n\n  1. Identify test anti-patterns:\n     - Implementation coupling (mocking\
  \ TransactionTemplate, ArgumentCaptor)\n     - Inappropriate mocking (over-mocking\
  \ internal collaborators)\n     - Environment mismatches (H2 instead of PostgreSQL)\n\
  \     - Coverage theater (high coverage, low confidence)\n     - Fragile tests (breaking\
  \ on refactoring)\n\n  2. Verify ADR compliance:\n     - ADR-0016: Integration tests\
  \ for persistence layer\n     - ADR-0017: PostgreSQL TestContainers configuration\n\
  \     - Proper @AutoConfigureTestDatabase(replace = NONE) usage\n\n  3. Assess test\
  \ confidence:\n     - Do tests verify behavior or implementation?\n     - Are tests\
  \ coupled to internal details?\n     - Would these tests catch real production bugs?\n\
  \n  4. Provide structured findings:\n     - Location (file:line)\n     - Issue description\n\
  \     - Impact (confidence, fragility, maintainability)\n     - Recommended fix\
  \ following ADRs\n     - Priority (Critical/High/Medium/Low)\n     - Effort estimate\
  \ (Small/Medium/Large)\n\n  Return findings in structured format for project-coordinator\
  \ consolidation.\n  \"\"\"\n)\n```\n\n**Code Quality Agent**:\n```\nTask(\n  subagent_type:\
  \ \"code-refactoring\",\n  description: \"Review code quality in ${1:-.}\",\n  prompt:\
  \ \"\"\"\n  Review code in ${1:-.} for quality and refactoring opportunities:\n\n\
  \  1. SOLID Principles:\n     - Single Responsibility violations\n     - Open/Closed\
  \ principle issues\n     - Liskov Substitution violations\n     - Interface Segregation\
  \ opportunities\n     - Dependency Inversion improvements\n\n  2. Clean Code:\n\
  \     - Method length and complexity\n     - Naming clarity and consistency\n  \
  \   - Code duplication (DRY violations)\n     - Magic numbers and hardcoded values\n\
  \     - Comment quality and necessity\n\n  3. Design Patterns:\n     - Appropriate\
  \ pattern usage\n     - Missing pattern opportunities\n     - Anti-patterns present\n\
  \n  4. Provide structured findings:\n     - Location (file:line)\n     - Issue description\n\
  \     - Impact on maintainability\n     - Recommended refactoring\n     - Priority\
  \ (Critical/High/Medium/Low)\n     - Effort estimate (Small/Medium/Large)\n\n  Return\
  \ findings in structured format for project-coordinator consolidation.\n  \"\"\"\
  \n)\n```\n\n**Architecture Review Agent**:\n```\nTask(\n  subagent_type: \"software-planner\"\
  ,\n  description: \"Review architecture in ${1:-.}\",\n  prompt: \"\"\"\n  Review\
  \ architecture and design in ${1:-.}:\n\n  1. Architectural Patterns:\n     - Layered\
  \ architecture consistency\n     - Dependency flow (layers, modules)\n     - Boundary\
  \ enforcement\n     - Separation of concerns\n\n  2. Domain-Driven Design:\n   \
  \  - Entity and value object design\n     - Aggregate boundaries\n     - Domain\
  \ logic placement\n     - Repository patterns\n\n  3. Technical Debt:\n     - Temporary\
  \ workarounds\n     - TODOs and FIXMEs\n     - Incomplete implementations\n    \
  \ - Deprecated code usage\n\n  4. Dependency Management:\n     - Circular dependencies\n\
  \     - Unnecessary coupling\n     - Interface vs implementation dependencies\n\n\
  \  5. Provide structured findings:\n     - Location (file:line or module)\n    \
  \ - Issue description\n     - Architectural impact\n     - Recommended approach\n\
  \     - Priority (Critical/High/Medium/Low)\n     - Effort estimate (Small/Medium/Large)\n\
  \n  Return findings in structured format for project-coordinator consolidation.\n\
  \  \"\"\"\n)\n```\n\n**Database Review Agent** (if applicable):\n```\nTask(\n  subagent_type:\
  \ \"postgres-optimizer\",\n  description: \"Review database code in ${1:-.}\",\n\
  \  prompt: \"\"\"\n  Review database-related code in ${1:-.}:\n\n  1. Query Performance:\n\
  \     - N+1 query problems\n     - Missing indexes\n     - Inefficient queries\n\
  \     - Pagination issues\n\n  2. Schema Design:\n     - Normalization issues\n\
  \     - Foreign key usage\n     - Index strategy\n     - Data types optimization\n\
  \n  3. PostgreSQL Usage:\n     - JSONB opportunities\n     - Array types usage\n\
  \     - Window functions\n     - Native features underutilization\n\n  4. Transaction\
  \ Management:\n     - Transaction boundary appropriateness\n     - Isolation level\
  \ issues\n     - Deadlock risks\n\n  5. Provide structured findings:\n     - Location\
  \ (file:line or query)\n     - Issue description\n     - Performance impact\n  \
  \   - Recommended optimization\n     - Priority (Critical/High/Medium/Low)\n   \
  \  - Effort estimate (Small/Medium/Large)\n\n  Return findings in structured format\
  \ for project-coordinator consolidation.\n  \"\"\"\n)\n```\n\n### Step 2: Consolidate\
  \ Findings\n\nAfter all parallel agents complete, consolidate their findings:\n\n\
  **Wait for all agents to complete**, then compile results:\n```markdown\n# Code\
  \ Review Report\n\n**Review Date**: [Current date]\n**Path Reviewed**: ${1:-.}\n\
  **Review Dimensions**: Testing, Code Quality, Architecture, Database\n\n---\n\n\
  ## Executive Summary\n\n- **Total Issues Found**: [count]\n- **Critical**: [count]\
  \ - Immediate attention required\n- **High**: [count] - Should address soon\n- **Medium**:\
  \ [count] - Plan for future sprint\n- **Low**: [count] - Nice to have improvements\n\
  \n---\n\n## Findings by Category\n\n### Testing Quality Issues\n[Findings from spring-boot-testing\
  \ agent]\n\n#### Critical\n- [Issue 1 with location, description, impact, fix]\n\
  \n#### High\n- [Issue 2 with location, description, impact, fix]\n\n#### Medium\n\
  - [Issue 3 with location, description, impact, fix]\n\n---\n\n### Code Quality Issues\n\
  [Findings from code-refactoring agent]\n\n#### Critical\n- [Issue 4 with location,\
  \ description, impact, fix]\n\n#### High\n- [Issue 5 with location, description,\
  \ impact, fix]\n\n---\n\n### Architecture Issues\n[Findings from software-planner\
  \ agent]\n\n#### Critical\n- [Issue 6 with location, description, impact, fix]\n\
  \n---\n\n### Database Performance Issues\n[Findings from postgres-optimizer agent]\n\
  \n#### Critical\n- [Issue 7 with location, description, impact, fix]\n\n---\n\n\
  ## Recommendations by Priority\n\n### Critical (Fix Immediately)\n1. [Issue] - [Location]\
  \ - [Estimated effort]\n2. [Issue] - [Location] - [Estimated effort]\n\n### High\
  \ (Address Soon)\n1. [Issue] - [Location] - [Estimated effort]\n2. [Issue] - [Location]\
  \ - [Estimated effort]\n\n### Medium (Plan for Next Sprint)\n1. [Issue] - [Location]\
  \ - [Estimated effort]\n\n### Low (Nice to Have)\n1. [Issue] - [Location] - [Estimated\
  \ effort]\n\n---\n\n## Effort Summary\n\n- **Total Estimated Effort**: [hours/days]\n\
  - **Critical Issues**: [hours]\n- **High Issues**: [hours]\n- **Medium Issues**:\
  \ [hours]\n- **Low Issues**: [hours]\n\n---\n\n## Related ADRs and Standards\n\n\
  - ADR-0016: Integration Tests Over Mocked Persistence\n- ADR-0017: PostgreSQL TestContainers\
  \ for Database Tests\n- Clean Code principles\n- SOLID principles\n- Domain-Driven\
  \ Design patterns\n```\n\n### Step 3: Invoke Project Coordinator\n\nAutomatically\
  \ delegate consolidated findings to project-coordinator:\n\n```\nTask(\n  subagent_type:\
  \ \"project-coordinator\",\n  description: \"Track code review findings\",\n  prompt:\
  \ \"\"\"\n  Document the following code review findings for systematic remediation:\n\
  \n  [Insert consolidated Code Review Report from Step 2]\n\n  Please use the Implementation\
  \ Plan format to:\n\n  1. **Create Project Structure**:\n     - Organize findings\
  \ by category and priority\n     - Create ATOMIC tasks for each issue\n     - Group\
  \ related issues for batch remediation\n     - Establish dependencies between tasks\n\
  \n  2. **Prioritization Strategy**:\n     - Critical: Immediate blockers or severe\
  \ technical debt\n     - High: Significant impact on maintainability or performance\n\
  \     - Medium: Moderate improvements with good ROI\n     - Low: Nice-to-have refinements\n\
  \n  3. **Remediation Planning**:\n     - Break down large issues into smaller tasks\n\
  \     - Estimate effort accurately (Small/Medium/Large)\n     - Identify quick wins\
  \ vs long-term improvements\n     - Schedule work across sprints\n\n  4. **Progress\
  \ Tracking**:\n     - Create task hierarchy in TODO.md or tracking system\n    \
  \ - Define clear success criteria for each task\n     - Enable progress measurement\
  \ over time\n     - Track technical debt reduction metrics\n\n  5. **Context Preservation**:\n\
  \     - Link to specific code locations\n     - Reference relevant ADRs and standards\n\
  \     - Document recommended approaches\n     - Capture rationale for prioritization\n\
  \n  Expected deliverables:\n  - Structured project plan for code improvements\n\
  \  - ATOMIC tasks organized by priority and effort\n  - Clear next actions for developers\n\
  \  - Progress tracking mechanism\n  - Technical debt metrics baseline\n  \"\"\"\n\
  )\n```\n\n## Expected Output\n\n### 1. Comprehensive Review Report\n- **Multi-dimensional\
  \ analysis** from specialized agents\n- **Structured findings** with locations,\
  \ impacts, and fixes\n- **Prioritized recommendations** (Critical → Low)\n- **Effort\
  \ estimates** for each issue\n- **ADR and standards references**\n\n### 2. Project\
  \ Tracking Integration\n- **ATOMIC tasks** created via project-coordinator\n- **Organized\
  \ by priority** and effort\n- **Grouped for efficiency** (batch similar fixes)\n\
  - **Progress tracking** enabled\n- **Technical debt baseline** established\n\n###\
  \ 3. Actionable Next Steps\n- Clear priorities for immediate work\n- Batch remediation\
  \ opportunities identified\n- Long-term improvement roadmap\n- Measurable progress\
  \ metrics\n\n## Parallel Execution Strategy\n\nThis command uses **parallel agent\
  \ invocation** for efficiency:\n\n1. **Launch all review agents simultaneously**\
  \ (Step 1)\n   - Testing agent reviews tests\n   - Quality agent reviews code structure\n\
  \   - Architecture agent reviews design\n   - Database agent reviews data layer\n\
  \n2. **Wait for all agents to complete**\n   - Each agent works independently\n\
  \   - No blocking dependencies between reviews\n   - Maximizes review throughput\n\
  \n3. **Consolidate and coordinate** (Steps 2-3)\n   - Merge findings from all agents\n\
  \   - Eliminate duplicates\n   - Prioritize across dimensions\n   - Create unified\
  \ remediation plan\n\n**Performance**:\n- Sequential review: ~20-40 minutes (4 agents\
  \ × 5-10 min each)\n- Parallel review: ~5-10 minutes (longest agent)\n- **Time savings**:\
  \ 75-80% faster reviews\n\n## Success Criteria\n\nThis command is successful when:\n\
  - ✅ All review dimensions complete (testing, quality, architecture, database)\n\
  - ✅ Findings are consolidated with clear priorities\n- ✅ Recommendations include\
  \ locations, impacts, and fixes\n- ✅ Project-coordinator creates tracking structure\n\
  - ✅ Developers have clear next actions\n\n## Integration with Other Commands\n\n\
  This command works well with:\n- `/quality:find-test-smells` - Specialized test\
  \ analysis\n- `/code:refactor` - Execute recommended refactorings\n- `/quality:architecture-review`\
  \ - Deep architectural analysis\n- `/plan:feature` - Plan improvements as features\n\
  \n## Notes\n\n- **Comprehensive but efficient**: Parallel execution keeps reviews\
  \ fast\n- **Multi-dimensional perspective**: Different agents catch different issues\n\
  - **Actionable output**: Not just problems, but specific solutions\n- **Trackable\
  \ progress**: Project-coordinator enables systematic improvement\n- **Standards-based**:\
  \ References ADRs and industry best practices\n- **Effort-aware**: Estimates help\
  \ prioritize based on ROI\n\nUse this command for:\n- Pre-merge code reviews\n-\
  \ Technical debt assessment\n- Quality audits\n- Onboarding code walkthroughs\n\
  - Architecture validation\n"
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

  Please use the Implementation Plan format to:

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
