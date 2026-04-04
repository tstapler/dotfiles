---
description: Systematically identify, categorize, and fix test/linter failures using
  appropriate tools and agents
prompt: "# Fix Test and Linter Failures\n\nSystematically identify, document, categorize,\
  \ and fix test/linter failures in the codebase using the most appropriate tools\
  \ and agents for each failure type.\n\n## Workflow\n\n### Phase 1: Discovery and\
  \ Documentation\n1. **Run tests/linters** to identify all failures\n   - If `$1`\
  \ is provided, use that as the test command\n   - Otherwise, detect the project\
  \ type and use appropriate defaults:\n     - Python: `pytest`, `ruff check`, `mypy`\n\
  \     - Java/Kotlin: `./gradlew test`, `./gradlew check`\n     - JavaScript/TypeScript:\
  \ `npm test`, `npm run lint`\n     - Go: `go test ./...`, `golangci-lint run`\n\n\
  2. **Capture full failure output** including:\n   - Error messages and stack traces\n\
  \   - File paths and line numbers\n   - Failure categories (compilation, test, linter,\
  \ type checking)\n   - Exit codes and summary statistics\n\n3. **Create structured\
  \ failure inventory** using TodoWrite:\n   - Group failures by type and severity\n\
  \   - Track dependencies between failures\n   - Estimate complexity for each failure\n\
  \n### Phase 2: Categorization and Strategy\nCategorize each failure into one of\
  \ these types and determine the appropriate fix strategy:\n\n#### Test Failures\n\
  - **Unit test failures**: Logic bugs, incorrect assertions, missing edge cases\n\
  - **Integration test failures**: API changes, database issues, timing problems\n\
  - **Flaky tests**: Race conditions, test isolation, environment dependencies\n-\
  \ **Strategy**: Use `java-test-debugger` or `golang-test-debugger` agents for systematic\
  \ diagnosis\n\n#### Linter Failures\n- **Style violations**: Formatting, naming\
  \ conventions, code organization\n- **Code smells**: Complexity, duplication, unused\
  \ code\n- **Best practice violations**: Security issues, anti-patterns\n- **Strategy**:\
  \ Use `code-refactoring` agent with AST-based tools (gritql) for systematic fixes\n\
  \n#### Compilation/Type Failures\n- **Type errors**: Missing types, incompatible\
  \ types, generic issues\n- **Import errors**: Missing dependencies, circular imports\n\
  - **Syntax errors**: Language version issues, invalid constructs\n- **Strategy**:\
  \ Direct fixes for simple issues, research agent for complex type system problems\n\
  \n#### Build Configuration Failures\n- **Dependency issues**: Version conflicts,\
  \ missing packages\n- **Build tool errors**: Configuration problems, plugin issues\n\
  - **Environment issues**: Missing tools, incompatible versions\n- **Strategy**:\
  \ Research best practices, update configurations systematically\n\n### Phase 3:\
  \ Execution Strategy\nFor each failure category, apply the appropriate approach:\n\
  \n#### Simple, Independent Fixes (Direct Approach)\n- **Criteria**: Single file,\
  \ clear fix, no dependencies\n- **Action**: Fix directly using Edit tool\n- **Examples**:\
  \ Import errors, simple type fixes, formatting\n\n#### Complex, Systematic Fixes\
  \ (Agent Approach)\n- **Test failures**: Launch `java-test-debugger` or `golang-test-debugger`\n\
  \  - Provide test output and context\n  - Let agent diagnose root cause\n  - Review\
  \ and apply fixes\n\n- **Code quality issues**: Launch `code-refactoring` agent\n\
  \  - Specify refactoring pattern\n  - Use gritql for structural changes\n  - Validate\
  \ with tests after refactoring\n\n- **Codebase research needed**: Launch `Explore`\
  \ agent\n  - Search codebase for similar patterns\n  - Understand how related functionality\
  \ works\n  - Find examples of correct implementation\n  - Identify architectural\
  \ patterns to follow\n\n- **External research needed**: Launch `knowledge-synthesis`\
  \ agent\n  - Research solutions in official documentation\n  - Investigate GitHub\
  \ issues and discussions\n  - Synthesize best practices from multiple sources\n\
  \  - Create zettel notes for future reference\n\n#### Parallel Execution\n- **Launch\
  \ multiple agents in parallel** for independent failures\n- **Example**: Different\
  \ test classes failing independently → parallel test-debugger agents\n- **Benefit**:\
  \ Maximize throughput and efficiency\n\n### Phase 4: Validation and Iteration\n\
  1. **Re-run tests/linters** after each fix batch\n2. **Track progress** in todo\
  \ list:\n   - Mark resolved failures as completed\n   - Document new failures discovered\n\
  \   - Update dependencies between fixes\n3. **Iterate** until all failures resolved\
  \ or blocked\n4. **Document blockers** that require human decisions\n\n## Observability\
  \ Improvements\nIf failures are difficult to diagnose, improve observability:\n\n\
  ### For Test Failures\n- Add detailed assertion messages\n- Improve test output\
  \ formatting\n- Add debug logging at key points\n- Use test fixtures to isolate\
  \ problems\n- Add timing information for flaky tests\n\n### For Build Failures\n\
  - Enable verbose build output\n- Add dependency tree visualization\n- Log environment\
  \ information\n- Add pre-build validation checks\n\n### For Linter Failures\n- Configure\
  \ linter for detailed explanations\n- Add inline documentation for complex rules\n\
  - Enable auto-fix where safe\n- Create custom rules for project patterns\n\n## Usage\
  \ Examples\n\n```bash\n# Use default test command for project type\n/fix-failures\n\
  \n# Use specific test command\n/fix-failures \"npm run test:ci\"\n\n# Use specific\
  \ linter\n/fix-failures \"ruff check --output-format=full\"\n\n# Use build command\n\
  /fix-failures \"./gradlew clean build\"\n```\n\n## Agent Selection Decision Tree\n\
  \n```\nFailure Type → Agent Choice\n├─ Test Failure (Java/Kotlin) → java-test-debugger\n\
  ├─ Test Failure (Go) → golang-test-debugger\n├─ Test Failure (Other) → Explore agent\
  \ (find patterns) + Direct fix\n├─ Code Quality/Refactoring → code-refactoring agent\n\
  ├─ Build/Configuration → knowledge-synthesis agent (research docs)\n├─ Type Errors\
  \ → Direct fix or Explore agent (find examples)\n├─ Codebase Investigation → Explore\
  \ agent (thorough search)\n└─ External Documentation → knowledge-synthesis agent\
  \ (research + zettel)\n```\n\n## Output Format\n\nProvide a structured summary at\
  \ the end:\n\n### Failure Summary\n- Total failures found: X\n- Failures fixed:\
  \ Y\n- Failures remaining: Z\n- Failures blocked: W\n\n### Fixes Applied\nFor each\
  \ fix:\n- **Type**: Test/Linter/Build/Type\n- **Location**: File:line\n- **Strategy**:\
  \ Direct/Agent/Research\n- **Status**: Fixed/Blocked/In Progress\n\n### Remaining\
  \ Work\n- List of unresolved failures with categorization\n- Recommended next steps\n\
  - Blockers requiring human decision\n\n### Observability Improvements\n- List of\
  \ observability enhancements made\n- Recommendations for future improvements\n\n\
  ## Implementation Notes\n\n1. **Always use TodoWrite** to track the workflow and\
  \ progress\n2. **Prefer specialized agents** over direct fixes for complex issues\n\
  3. **Run agents in parallel** when failures are independent\n4. **Re-validate after\
  \ each batch** to catch regressions\n5. **Document blockers clearly** with context\
  \ for human review\n6. **Improve observability proactively** when diagnosis is difficult\n"
---

# Fix Test and Linter Failures

Systematically identify, document, categorize, and fix test/linter failures in the codebase using the most appropriate tools and agents for each failure type.

## Workflow

### Phase 1: Discovery and Documentation
1. **Run tests/linters** to identify all failures
   - If `$1` is provided, use that as the test command
   - Otherwise, detect the project type and use appropriate defaults:
     - Python: `pytest`, `ruff check`, `mypy`
     - Java/Kotlin: `./gradlew test`, `./gradlew check`
     - JavaScript/TypeScript: `npm test`, `npm run lint`
     - Go: `go test ./...`, `golangci-lint run`

2. **Capture full failure output** including:
   - Error messages and stack traces
   - File paths and line numbers
   - Failure categories (compilation, test, linter, type checking)
   - Exit codes and summary statistics

3. **Create structured failure inventory** using TodoWrite:
   - Group failures by type and severity
   - Track dependencies between failures
   - Estimate complexity for each failure

### Phase 2: Categorization and Strategy
Categorize each failure into one of these types and determine the appropriate fix strategy:

#### Test Failures
- **Unit test failures**: Logic bugs, incorrect assertions, missing edge cases
- **Integration test failures**: API changes, database issues, timing problems
- **Flaky tests**: Race conditions, test isolation, environment dependencies
- **Strategy**: Use `java-test-debugger` or `golang-test-debugger` agents for systematic diagnosis

#### Linter Failures
- **Style violations**: Formatting, naming conventions, code organization
- **Code smells**: Complexity, duplication, unused code
- **Best practice violations**: Security issues, anti-patterns
- **Strategy**: Use `code-refactoring` agent with AST-based tools (gritql) for systematic fixes

#### Compilation/Type Failures
- **Type errors**: Missing types, incompatible types, generic issues
- **Import errors**: Missing dependencies, circular imports
- **Syntax errors**: Language version issues, invalid constructs
- **Strategy**: Direct fixes for simple issues, research agent for complex type system problems

#### Build Configuration Failures
- **Dependency issues**: Version conflicts, missing packages
- **Build tool errors**: Configuration problems, plugin issues
- **Environment issues**: Missing tools, incompatible versions
- **Strategy**: Research best practices, update configurations systematically

### Phase 3: Execution Strategy
For each failure category, apply the appropriate approach:

#### Simple, Independent Fixes (Direct Approach)
- **Criteria**: Single file, clear fix, no dependencies
- **Action**: Fix directly using Edit tool
- **Examples**: Import errors, simple type fixes, formatting

#### Complex, Systematic Fixes (Agent Approach)
- **Test failures**: Launch `java-test-debugger` or `golang-test-debugger`
  - Provide test output and context
  - Let agent diagnose root cause
  - Review and apply fixes

- **Code quality issues**: Launch `code-refactoring` agent
  - Specify refactoring pattern
  - Use gritql for structural changes
  - Validate with tests after refactoring

- **Codebase research needed**: Launch `Explore` agent
  - Search codebase for similar patterns
  - Understand how related functionality works
  - Find examples of correct implementation
  - Identify architectural patterns to follow

- **External research needed**: Launch `knowledge-synthesis` agent
  - Research solutions in official documentation
  - Investigate GitHub issues and discussions
  - Synthesize best practices from multiple sources
  - Create zettel notes for future reference

#### Parallel Execution
- **Launch multiple agents in parallel** for independent failures
- **Example**: Different test classes failing independently → parallel test-debugger agents
- **Benefit**: Maximize throughput and efficiency

### Phase 4: Validation and Iteration
1. **Re-run tests/linters** after each fix batch
2. **Track progress** in todo list:
   - Mark resolved failures as completed
   - Document new failures discovered
   - Update dependencies between fixes
3. **Iterate** until all failures resolved or blocked
4. **Document blockers** that require human decisions

## Observability Improvements
If failures are difficult to diagnose, improve observability:

### For Test Failures
- Add detailed assertion messages
- Improve test output formatting
- Add debug logging at key points
- Use test fixtures to isolate problems
- Add timing information for flaky tests

### For Build Failures
- Enable verbose build output
- Add dependency tree visualization
- Log environment information
- Add pre-build validation checks

### For Linter Failures
- Configure linter for detailed explanations
- Add inline documentation for complex rules
- Enable auto-fix where safe
- Create custom rules for project patterns

## Usage Examples

```bash
# Use default test command for project type
/fix-failures

# Use specific test command
/fix-failures "npm run test:ci"

# Use specific linter
/fix-failures "ruff check --output-format=full"

# Use build command
/fix-failures "./gradlew clean build"
```

## Agent Selection Decision Tree

```
Failure Type → Agent Choice
├─ Test Failure (Java/Kotlin) → java-test-debugger
├─ Test Failure (Go) → golang-test-debugger
├─ Test Failure (Other) → Explore agent (find patterns) + Direct fix
├─ Code Quality/Refactoring → code-refactoring agent
├─ Build/Configuration → knowledge-synthesis agent (research docs)
├─ Type Errors → Direct fix or Explore agent (find examples)
├─ Codebase Investigation → Explore agent (thorough search)
└─ External Documentation → knowledge-synthesis agent (research + zettel)
```

## Output Format

Provide a structured summary at the end:

### Failure Summary
- Total failures found: X
- Failures fixed: Y
- Failures remaining: Z
- Failures blocked: W

### Fixes Applied
For each fix:
- **Type**: Test/Linter/Build/Type
- **Location**: File:line
- **Strategy**: Direct/Agent/Research
- **Status**: Fixed/Blocked/In Progress

### Remaining Work
- List of unresolved failures with categorization
- Recommended next steps
- Blockers requiring human decision

### Observability Improvements
- List of observability enhancements made
- Recommendations for future improvements

## Implementation Notes

1. **Always use TodoWrite** to track the workflow and progress
2. **Prefer specialized agents** over direct fixes for complex issues
3. **Run agents in parallel** when failures are independent
4. **Re-validate after each batch** to catch regressions
5. **Document blockers clearly** with context for human review
6. **Improve observability proactively** when diagnosis is difficult
