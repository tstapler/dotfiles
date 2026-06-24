---
description: Analyze tests for anti-patterns and smells, documenting issues for later
  remediation using project-coordinator
prompt: "# Find Test Smells\n\nAnalyze Spring Boot tests for anti-patterns and testing\
  \ smells, then document findings using the project-coordinator agent for systematic\
  \ remediation.\n\n## Testing Smells to Detect\n\n### 1. **Implementation Coupling**\n\
  - Tests tightly coupled to internal implementation details\n- Mocking Spring framework\
  \ internals (`TransactionTemplate`, `EntityManager`)\n- Verifying method call counts\
  \ instead of behavior outcomes\n- Using `ArgumentCaptor` to verify implementation\
  \ details\n\n### 2. **Inappropriate Mocking**\n- Over-mocking internal collaborators\
  \ (London School orthodoxy)\n- Mocking repositories and services that should be\
  \ integration tested\n- Complex mock setup with `doAnswer()` and intricate verification\
  \ logic\n- Mocking TestContainers or database connections\n\n### 3. **Test Environment\
  \ Mismatches**\n- Using H2 instead of PostgreSQL TestContainers\n- Missing `@AutoConfigureTestDatabase(replace\
  \ = NONE)` with `@DataJpaTest`\n- Not using TestContainers for persistence layer\
  \ tests\n- In-memory substitutes for production dependencies (Redis, Kafka)\n\n\
  ### 4. **Coverage Theater**\n- High coverage percentage with low confidence tests\n\
  - Tests that pass but don't verify meaningful behavior\n- Testing untestable code\
  \ instead of refactoring\n- Green checkboxes without specification validation\n\n\
  ### 5. **Fragile Tests**\n- Tests that break on every refactoring\n- Brittle assertions\
  \ on exact string matches or message formats\n- Order-dependent tests without proper\
  \ isolation\n- Tests coupled to test data setup implementation\n\n### 6. **Performance\
  \ Issues**\n- Not using TestContainers reuse (`testcontainers.reuse.enable=true`)\n\
  - Excessive use of `@DirtiesContext` (expensive context reloading)\n- Sequential\
  \ test execution when parallel would work\n- Redundant test setup and teardown logic\n\
  \n## Analysis Process\n\n### Phase 1: Scan for Test Anti-Patterns\n\nSearch the\
  \ codebase for common anti-pattern indicators:\n\n1. **Implementation Coupling Indicators**:\n\
  \   - `@Mock TransactionTemplate`\n   - `@Mock EntityManager`\n   - `ArgumentCaptor`\
  \ usage\n   - `verify(service, times(N))` without behavior verification\n   - `doAnswer()`\
  \ for Spring framework internals\n\n2. **Inappropriate Test Type Indicators**:\n\
  \   - `@SpringBootTest` without TestContainers for persistence tests\n   - Mocked\
  \ repositories in service tests\n   - H2 configuration in test resources\n   - Missing\
  \ `@AutoConfigureTestDatabase(replace = NONE)`\n\n3. **Environment Mismatch Indicators**:\n\
  \   - `jdbc:h2:mem` in test configuration\n   - H2 dependency in test scope\n  \
  \ - In-memory Redis/Kafka instead of TestContainers\n   - Different database dialects\
  \ between test and production\n\n### Phase 2: Analyze Test Quality\n\nFor each test\
  \ file, evaluate:\n\n1. **What is being tested?** (Repository, Service, Controller,\
  \ Domain logic)\n2. **What is the testing approach?** (Unit with mocks, Integration\
  \ with TestContainers)\n3. **Does the approach match ADR-0016/0017 guidelines?**\n\
  4. **Are there anti-patterns present?**\n5. **What is the confidence level?** (Low/Medium/High)\n\
  6. **What is the refactoring effort?** (Small/Medium/Large)\n\n### Phase 3: Document\
  \ Findings\n\nFor each identified issue, create a structured bug report including:\n\
  \n- **File and Location**: Exact test class and method\n- **Anti-Pattern Type**:\
  \ Classification from the list above\n- **Current Approach**: Brief description\
  \ of what the test is doing\n- **Problem**: Why this is problematic (fragility,\
  \ false confidence, etc.)\n- **Recommended Fix**: How to refactor (integration test,\
  \ remove mocks, etc.)\n- **ADR References**: Link to ADR-0016 or ADR-0017 if applicable\n\
  - **Priority**: Critical/High/Medium/Low based on:\n  - Business criticality of\
  \ code under test\n  - Fragility of test (how often it breaks)\n  - Confidence level\
  \ (does it catch real bugs?)\n  - Refactoring effort required\n\n### Phase 4: Coordinate\
  \ Bug Tracking\n\nUse the project-coordinator agent to:\n1. Create structured bug\
  \ entries in TODO.md or project tracking system\n2. Organize by priority and refactoring\
  \ effort\n3. Group related test smells for batch refactoring\n4. Track progress\
  \ on remediation\n\n## Usage\n\nAnalyze tests in a specific directory:\n```\n/quality:find-test-smells\
  \ src/test/java/com/example/service\n```\n\nAnalyze all tests in the project:\n\
  ```\n/quality:find-test-smells .\n```\n\nAnalyze a specific test file:\n```\n/quality:find-test-smells\
  \ src/test/java/com/example/UserRepositoryTest.java\n```\n\n## Implementation Steps\n\
  \nFollow these steps to analyze tests and track remediation:\n\n### Step 1: Search\
  \ for Anti-Pattern Indicators\n\nUse Grep to find common anti-pattern markers in\
  \ the specified path (`${1:-.}`):\n\n```bash\n# Search for implementation coupling\
  \ indicators\nGrep \"@Mock.*TransactionTemplate\" --glob \"**/*Test.java\" --path\
  \ ${1:-.}\nGrep \"@Mock.*EntityManager\" --glob \"**/*Test.java\" --path ${1:-.}\n\
  Grep \"ArgumentCaptor\" --glob \"**/*Test.java\" --path ${1:-.}\nGrep \"verify.*times\\\
  (\" --glob \"**/*Test.java\" --path ${1:-.}\nGrep \"doAnswer\\(\" --glob \"**/*Test.java\"\
  \ --path ${1:-.}\n\n# Search for environment mismatch indicators\nGrep \"jdbc:h2:mem\"\
  \ --glob \"**/*.yml\" --path ${1:-.}\nGrep \"jdbc:h2:mem\" --glob \"**/*.properties\"\
  \ --path ${1:-.}\nGrep \"@SpringBootTest\" --glob \"**/*Test.java\" --path ${1:-.}\
  \ | head -n 50\n\n# Search for missing TestContainers configuration\nGrep \"@DataJpaTest\"\
  \ --glob \"**/*Test.java\" --path ${1:-.} | head -n 50\n```\n\n### Step 2: Read\
  \ and Analyze Identified Files\n\nFor each file with anti-pattern indicators:\n\
  - Read the full test class to understand context\n- Identify the component being\
  \ tested (Repository, Service, Controller)\n- Classify the testing approach (Unit\
  \ with mocks, Integration, etc.)\n- Detect specific anti-patterns and smells\n-\
  \ Assess confidence level and fragility\n- Estimate refactoring effort\n\n### Step\
  \ 3: Generate Structured Bug Reports\n\nFor each identified issue, create a report\
  \ following this template:\n\n```markdown\n## Test Smell: [Anti-Pattern Type]\n\n\
  **Location**: `[file-path]:[line-number]`\n\n**Current Approach**:\n[Brief description\
  \ of what the test is doing]\n\n**Problem**:\n- [Why this is problematic]\n- [Impact\
  \ on maintainability/confidence]\n- [Specific issues with current implementation]\n\
  \n**Recommended Fix**:\n[Specific steps to refactor following ADR-0016/0017]\n-\
  \ Use appropriate test approach (integration vs unit)\n- Apply TestContainers if\
  \ needed\n- Remove inappropriate mocks\n- Verify behavior, not implementation\n\n\
  **ADR References**: [Link to relevant ADR]\n\n**Priority**: [Critical/High/Medium/Low]\
  \ - [Rationale]\n\n**Effort**: [Small/Medium/Large] - [Time estimate]\n```\n\n###\
  \ Step 4: Automatically Invoke Project Coordinator\n\nOnce all test smells are documented,\
  \ invoke the project-coordinator agent using the Task tool:\n\n```\nTask(\n  subagent_type:\
  \ \"project-coordinator\",\n  description: \"Track test smell remediation bugs\"\
  ,\n  prompt: \"\"\"\n  Document the following test smells for systematic remediation:\n\
  \n  # Test Smell Analysis Report\n\n  **Analysis Date**: [Current date]\n  **Path\
  \ Analyzed**: ${1:-.}\n  **Total Issues Found**: [Count]\n\n  ## Issues by Category\n\
  \n  ### Implementation Coupling\n  [Bug Report 1]\n  [Bug Report 2]\n\n  ### Inappropriate\
  \ Mocking\n  [Bug Report 3]\n\n  ### Test Environment Mismatches\n  [Bug Report\
  \ 4]\n\n  ### Coverage Theater\n  [Bug Report 5]\n\n  ### Fragile Tests\n  [Bug\
  \ Report 6]\n\n  ### Performance Issues\n  [Bug Report 7]\n\n  ## Summary\n\n  -\
  \ Critical: [count]\n  - High: [count]\n  - Medium: [count]\n  - Low: [count]\n\n\
  \  ## Recommended Remediation Order\n\n  1. Start with Critical priority issues\n\
  \  2. Group related issues for batch refactoring\n  3. Address High priority items\
  \ next\n  4. Schedule Medium/Low as time permits\n\n  Please use the Implementation\
  \ Plan format to:\n  1. Create a structured project plan for test quality improvement\n\
  \  2. Break down remediation work into ATOMIC tasks\n  3. Organize by priority and\
  \ refactoring effort\n  4. Track progress systematically\n  5. Measure improvement\
  \ over time\n  \"\"\"\n)\n```\n\nThis ensures all identified test smells are automatically\
  \ tracked in the project coordination system for systematic remediation.\n\n## Expected\
  \ Output\n\n1. **Summary Report**:\n   - Total tests analyzed\n   - Number of issues\
  \ found by category\n   - Prioritized list of high-impact issues\n   - Estimated\
  \ refactoring effort\n\n2. **Detailed Issue List**:\n   - Structured bug reports\
  \ for each identified smell\n   - Cross-references to ADR-0016/0017 where applicable\n\
  \   - Recommended refactoring approach\n\n3. **Project Tracking**:\n   - Issues\
  \ documented in project coordination system\n   - Organized by priority and effort\n\
  \   - Grouped for efficient batch remediation\n\n## Success Criteria\n\nThis command\
  \ is successful when:\n- ✅ All test anti-patterns are identified with specific file\
  \ locations\n- ✅ Each issue has a clear problem statement and recommended fix\n\
  - ✅ Priority and effort estimates are provided\n- ✅ Issues are tracked in project\
  \ coordination system\n- ✅ Remediation plan is organized for systematic execution\n\
  \n## Notes\n\n- This command focuses on **detection and documentation**, not immediate\
  \ fixes\n- Use the **spring-boot-testing agent** for actual test refactoring work\n\
  - Prioritize fixes based on business criticality and test fragility\n- Batch similar\
  \ issues for efficient refactoring sessions\n- Track progress and measure improvement\
  \ over time\n"
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

  Please use the Implementation Plan format to:
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
