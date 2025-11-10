---
title: Find Test Smells
description: Analyze tests for anti-patterns and smells, documenting issues for later remediation using project-coordinator
arguments: [path]
---

# Find Test Smells

Analyze Spring Boot tests for anti-patterns and testing smells, then document findings using the project-coordinator agent for systematic remediation.

## Testing Smells to Detect

### 1. **Implementation Coupling**
- Tests tightly coupled to internal implementation details
- Mocking Spring framework internals (`TransactionTemplate`, `EntityManager`)
- Verifying method call counts instead of behavior outcomes
- Using `ArgumentCaptor` to verify implementation details

### 2. **Inappropriate Mocking**
- Over-mocking internal collaborators (London School orthodoxy)
- Mocking repositories and services that should be integration tested
- Complex mock setup with `doAnswer()` and intricate verification logic
- Mocking TestContainers or database connections

### 3. **Test Environment Mismatches**
- Using H2 instead of PostgreSQL TestContainers
- Missing `@AutoConfigureTestDatabase(replace = NONE)` with `@DataJpaTest`
- Not using TestContainers for persistence layer tests
- In-memory substitutes for production dependencies (Redis, Kafka)

### 4. **Coverage Theater**
- High coverage percentage with low confidence tests
- Tests that pass but don't verify meaningful behavior
- Testing untestable code instead of refactoring
- Green checkboxes without specification validation

### 5. **Fragile Tests**
- Tests that break on every refactoring
- Brittle assertions on exact string matches or message formats
- Order-dependent tests without proper isolation
- Tests coupled to test data setup implementation

### 6. **Performance Issues**
- Not using TestContainers reuse (`testcontainers.reuse.enable=true`)
- Excessive use of `@DirtiesContext` (expensive context reloading)
- Sequential test execution when parallel would work
- Redundant test setup and teardown logic

## Analysis Process

### Phase 1: Scan for Test Anti-Patterns

Search the codebase for common anti-pattern indicators:

1. **Implementation Coupling Indicators**:
   - `@Mock TransactionTemplate`
   - `@Mock EntityManager`
   - `ArgumentCaptor` usage
   - `verify(service, times(N))` without behavior verification
   - `doAnswer()` for Spring framework internals

2. **Inappropriate Test Type Indicators**:
   - `@SpringBootTest` without TestContainers for persistence tests
   - Mocked repositories in service tests
   - H2 configuration in test resources
   - Missing `@AutoConfigureTestDatabase(replace = NONE)`

3. **Environment Mismatch Indicators**:
   - `jdbc:h2:mem` in test configuration
   - H2 dependency in test scope
   - In-memory Redis/Kafka instead of TestContainers
   - Different database dialects between test and production

### Phase 2: Analyze Test Quality

For each test file, evaluate:

1. **What is being tested?** (Repository, Service, Controller, Domain logic)
2. **What is the testing approach?** (Unit with mocks, Integration with TestContainers)
3. **Does the approach match ADR-0016/0017 guidelines?**
4. **Are there anti-patterns present?**
5. **What is the confidence level?** (Low/Medium/High)
6. **What is the refactoring effort?** (Small/Medium/Large)

### Phase 3: Document Findings

For each identified issue, create a structured bug report including:

- **File and Location**: Exact test class and method
- **Anti-Pattern Type**: Classification from the list above
- **Current Approach**: Brief description of what the test is doing
- **Problem**: Why this is problematic (fragility, false confidence, etc.)
- **Recommended Fix**: How to refactor (integration test, remove mocks, etc.)
- **ADR References**: Link to ADR-0016 or ADR-0017 if applicable
- **Priority**: Critical/High/Medium/Low based on:
  - Business criticality of code under test
  - Fragility of test (how often it breaks)
  - Confidence level (does it catch real bugs?)
  - Refactoring effort required

### Phase 4: Coordinate Bug Tracking

Use the project-coordinator agent to:
1. Create structured bug entries in TODO.md or project tracking system
2. Organize by priority and refactoring effort
3. Group related test smells for batch refactoring
4. Track progress on remediation

## Usage

Analyze tests in a specific directory:
```
/quality:find-test-smells src/test/java/com/example/service
```

Analyze all tests in the project:
```
/quality:find-test-smells .
```

Analyze a specific test file:
```
/quality:find-test-smells src/test/java/com/example/UserRepositoryTest.java
```

## Implementation Steps

Follow these steps to analyze tests and track remediation:

### Step 1: Search for Anti-Pattern Indicators

Use Grep to find common anti-pattern markers in the specified path (`${1:-.}`):

```bash
# Search for implementation coupling indicators
Grep "@Mock.*TransactionTemplate" --glob "**/*Test.java" --path ${1:-.}
Grep "@Mock.*EntityManager" --glob "**/*Test.java" --path ${1:-.}
Grep "ArgumentCaptor" --glob "**/*Test.java" --path ${1:-.}
Grep "verify.*times\(" --glob "**/*Test.java" --path ${1:-.}
Grep "doAnswer\(" --glob "**/*Test.java" --path ${1:-.}

# Search for environment mismatch indicators
Grep "jdbc:h2:mem" --glob "**/*.yml" --path ${1:-.}
Grep "jdbc:h2:mem" --glob "**/*.properties" --path ${1:-.}
Grep "@SpringBootTest" --glob "**/*Test.java" --path ${1:-.} | head -n 50

# Search for missing TestContainers configuration
Grep "@DataJpaTest" --glob "**/*Test.java" --path ${1:-.} | head -n 50
```

### Step 2: Read and Analyze Identified Files

For each file with anti-pattern indicators:
- Read the full test class to understand context
- Identify the component being tested (Repository, Service, Controller)
- Classify the testing approach (Unit with mocks, Integration, etc.)
- Detect specific anti-patterns and smells
- Assess confidence level and fragility
- Estimate refactoring effort

### Step 3: Generate Structured Bug Reports

For each identified issue, create a report following this template:

```markdown
## Test Smell: [Anti-Pattern Type]

**Location**: `[file-path]:[line-number]`

**Current Approach**:
[Brief description of what the test is doing]

**Problem**:
- [Why this is problematic]
- [Impact on maintainability/confidence]
- [Specific issues with current implementation]

**Recommended Fix**:
[Specific steps to refactor following ADR-0016/0017]
- Use appropriate test approach (integration vs unit)
- Apply TestContainers if needed
- Remove inappropriate mocks
- Verify behavior, not implementation

**ADR References**: [Link to relevant ADR]

**Priority**: [Critical/High/Medium/Low] - [Rationale]

**Effort**: [Small/Medium/Large] - [Time estimate]
```

### Step 4: Automatically Invoke Project Coordinator

Once all test smells are documented, invoke the project-coordinator agent using the Task tool:

```
Task(
  subagent_type: "project-coordinator",
  description: "Track test smell remediation bugs",
  prompt: """
  Document the following test smells for systematic remediation:

  # Test Smell Analysis Report

  **Analysis Date**: [Current date]
  **Path Analyzed**: ${1:-.}
  **Total Issues Found**: [Count]

  ## Issues by Category

  ### Implementation Coupling
  [Bug Report 1]
  [Bug Report 2]

  ### Inappropriate Mocking
  [Bug Report 3]

  ### Test Environment Mismatches
  [Bug Report 4]

  ### Coverage Theater
  [Bug Report 5]

  ### Fragile Tests
  [Bug Report 6]

  ### Performance Issues
  [Bug Report 7]

  ## Summary

  - Critical: [count]
  - High: [count]
  - Medium: [count]
  - Low: [count]

  ## Recommended Remediation Order

  1. Start with Critical priority issues
  2. Group related issues for batch refactoring
  3. Address High priority items next
  4. Schedule Medium/Low as time permits

  Please use the AIC framework to:
  1. Create a structured project plan for test quality improvement
  2. Break down remediation work into ATOMIC tasks
  3. Organize by priority and refactoring effort
  4. Track progress systematically
  5. Measure improvement over time
  """
)
```

This ensures all identified test smells are automatically tracked in the project coordination system for systematic remediation.

## Expected Output

1. **Summary Report**:
   - Total tests analyzed
   - Number of issues found by category
   - Prioritized list of high-impact issues
   - Estimated refactoring effort

2. **Detailed Issue List**:
   - Structured bug reports for each identified smell
   - Cross-references to ADR-0016/0017 where applicable
   - Recommended refactoring approach

3. **Project Tracking**:
   - Issues documented in project coordination system
   - Organized by priority and effort
   - Grouped for efficient batch remediation

## Success Criteria

This command is successful when:
- ✅ All test anti-patterns are identified with specific file locations
- ✅ Each issue has a clear problem statement and recommended fix
- ✅ Priority and effort estimates are provided
- ✅ Issues are tracked in project coordination system
- ✅ Remediation plan is organized for systematic execution

## Notes

- This command focuses on **detection and documentation**, not immediate fixes
- Use the **spring-boot-testing agent** for actual test refactoring work
- Prioritize fixes based on business criticality and test fragility
- Batch similar issues for efficient refactoring sessions
- Track progress and measure improvement over time
