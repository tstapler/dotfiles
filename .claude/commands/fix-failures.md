---
title: Fix Test and Linter Failures
description: Systematically identify, categorize, and fix test/linter failures using appropriate tools and agents
arguments: [test_command]
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
