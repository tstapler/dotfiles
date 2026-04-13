---
description: Systematically implement a new feature following research-backed best
  practices from the Six-Phase Software Implementation Methodology, with intelligent
  parallelization and multi-agent coordination
prompt: "# Implement Feature: $@\n\nImplement the requested feature following the\
  \ **Six-Phase Software Implementation Methodology** with **intelligent parallelization**\
  \ - a research-backed framework that balances quality, speed, and maintainability\
  \ through concurrent execution where appropriate.\n\n**Key Insight**: Elite performers\
  \ achieve multiple daily deployments not by working sequentially, but by identifying\
  \ independent work streams and executing them in parallel while maintaining quality\
  \ gates at integration points.\n\n---\n\n## Phase 0: Parallelization Analysis (NEW\
  \ - 5% of effort)\n\n**Purpose**: Analyze the feature for parallelization opportunities\
  \ before starting implementation.\n\n### Parallelization Assessment\n\n1. **Decomposition\
  \ Analysis**:\n   - Break feature into atomic sub-components\n   - Identify dependencies\
  \ between components\n   - Map data flow and integration points\n   - Determine\
  \ which components can be developed independently\n\n2. **File Independence Matrix**:\n\
  \   ```\n   Component A | Component B | Dependency Type | Can Parallelize?\n   ------------|-------------|-----------------|------------------\n\
  \   Frontend UI | Backend API | Interface only  | Yes (define contract first)\n\
  \   Service A   | Service B   | None           | Yes (fully independent)\n   Module\
  \ X    | Module Y    | Shared utils   | Partial (utils first)\n   ```\n\n3. **Parallelization\
  \ Strategies**:\n\n   **Vertical Slice Parallelization**:\n   - Independent feature\
  \ slices that deliver value end-to-end\n   - Each slice has its own UI, API, and\
  \ data layer\n   - Example: User profile view vs. user profile edit\n\n   **Horizontal\
  \ Layer Parallelization**:\n   - Different architectural layers worked on simultaneously\n\
  \   - Requires well-defined interfaces/contracts\n   - Example: Frontend and backend\
  \ teams working in parallel\n\n   **Test Parallelization**:\n   - Unit tests independent\
  \ of implementation\n   - Integration test scaffolding while building\n   - Performance\
  \ test harness preparation\n\n   **Research Parallelization**:\n   - Multiple Explore\
  \ agents investigating different areas\n   - Concurrent pattern discovery in different\
  \ modules\n   - Parallel best practice research\n\n### Multi-Agent Spawn Decision\
  \ Matrix\n\n| Scenario | Agents to Spawn | Invocation Pattern |\n|----------|----------------|-------------------|\n\
  | **Multi-module feature** | 2-3 Explore agents | Concurrent exploration of each\
  \ module |\n| **Frontend + Backend** | 2 implementation agents | Parallel after\
  \ interface definition |\n| **Complex refactoring** | Explore + code-refactoring\
  \ | Research patterns while refactoring |\n| **New API with tests** | Implementation\
  \ + test agents | Build and test concurrently |\n| **Unknown codebase** | 3-4 Explore\
  \ agents | Map different subsystems simultaneously |\n\n### Success Criteria for\
  \ Parallelization\n- ✅ Feature decomposed into 3+ independent work streams\n- ✅\
  \ Dependencies clearly mapped with integration points defined\n- ✅ Parallel execution\
  \ plan saves 30%+ time vs sequential\n- ✅ Risk of integration conflicts assessed\
  \ and mitigated\n\n**Use Task tool with multiple invocations in a SINGLE message\
  \ for maximum parallelization.**\n\n---\n\n## Phase 1: Understanding & Planning\
  \ (10-15% of effort) - ENHANCED\n\n**Purpose**: Ensure clear requirements and identify\
  \ parallelization opportunities.\n\n### Activities (with Parallelization)\n\n1.\
  \ **Parallel Requirements Gathering**:\n   ```\n   Launch concurrently:\n   - Task\
  \ @explore \"Find similar features and patterns\"\n   - Task @explore \"Investigate\
  \ existing APIs and interfaces\"\n   - Task @explore \"Search for reusable components\"\
  \n   - Task @knowledge-synthesis \"Research best practices for [feature type]\"\n\
  \   ```\n\n2. **Concurrent Domain Exploration**:\n   - **Agent 1**: Explore frontend\
  \ patterns and UI components\n   - **Agent 2**: Explore backend services and data\
  \ models\n   - **Agent 3**: Explore testing patterns and fixtures\n   - **Agent\
  \ 4**: Research external best practices\n\n3. **Parallel Design Activities**:\n\
  \   - Architecture design (one agent)\n   - API contract definition (another agent)\n\
  \   - Test scenario planning (third agent)\n   - Performance requirements analysis\
  \ (fourth agent)\n\n### Example Multi-Agent Invocation\n\n```markdown\nI'll explore\
  \ this feature using multiple agents in parallel for efficiency:\n\n[Task tool invocations]\n\
  - @explore \"Find all authentication implementations in services/\"\n- @explore\
  \ \"Analyze current database schema for user tables\"\n- @explore \"Identify all\
  \ test patterns for API endpoints\"\n- @knowledge-synthesis \"Best practices for\
  \ JWT authentication in microservices\"\n\nThis parallel exploration will give us\
  \ comprehensive understanding quickly.\n```\n\n### Parallelization Checkpoint\n\
  - ✅ Multiple agents launched in single message\n- ✅ Each agent has clear, non-overlapping\
  \ scope\n- ✅ Results will be synthesized into unified plan\n- ✅ Time saved: 50-70%\
  \ vs sequential exploration\n\n**Use TodoWrite to track both sequential phases AND\
  \ parallel tasks within each phase.**\n\n---\n\n## Phase 2: Implementation (40-50%\
  \ of effort) - PARALLELIZED\n\n**Purpose**: Transform requirements into working\
  \ code through parallel development streams.\n\n### Parallel Implementation Patterns\n\
  \n#### Pattern 1: Interface-First Parallel Development\n```\nStep 1: Define contracts\
  \ (sequential - 1 hour)\n└── API interfaces, data models, message formats\n\nStep\
  \ 2: Parallel implementation (concurrent - 4 hours)\n├── Frontend implementation\
  \ (Agent 1)\n├── Backend implementation (Agent 2)\n├── Database migrations (Agent\
  \ 3)\n└── Test suite development (Agent 4)\n\nStep 3: Integration (sequential -\
  \ 1 hour)\n└── Connect all components and verify\n```\n\n#### Pattern 2: Vertical\
  \ Slice Parallelization\n```\nSlice 1: User Registration (Agent 1)\n├── UI form\n\
  ├── API endpoint\n├── Database operations\n└── Tests\n\nSlice 2: User Login (Agent\
  \ 2)\n├── UI form\n├── API endpoint\n├── Session management\n└── Tests\n\nSlice\
  \ 3: Password Reset (Agent 3)\n├── UI flow\n├── API endpoints\n├── Email integration\n\
  └── Tests\n```\n\n#### Pattern 3: Test-Driven Parallel Development\n```\nConcurrent\
  \ Execution:\n├── Test Writer (Agent 1): Creates all test cases\n├── Implementation\
  \ (Agent 2): Implements to pass tests\n├── Documentation (Agent 3): Writes docs\
  \ as code emerges\n└── Performance (Agent 4): Sets up monitoring/profiling\n```\n\
  \n### Multi-Agent Implementation Example\n\n```markdown\nBased on our parallelization\
  \ analysis, I'll implement this feature using 4 concurrent work streams:\n\n[Task\
  \ tool invocations in single message]\n@feature-implementation \"Implement user\
  \ profile frontend component with edit capability\"\n@feature-implementation \"\
  Build REST API for user profile CRUD operations\"\n@feature-implementation \"Create\
  \ database migrations and repository layer for profiles\"\n@java-test-builder \"\
  Generate comprehensive test suite for profile feature\"\n\nEach agent will work\
  \ independently and we'll integrate at defined checkpoints.\n```\n\n### Coordination\
  \ Checkpoints\n\n**Every 2 hours during parallel work:**\n1. Verify interfaces still\
  \ align\n2. Check for merge conflicts\n3. Run integration tests\n4. Adjust remaining\
  \ work distribution\n\n### Parallel Work Anti-Patterns to Avoid\n\n- ❌ **Duplicated\
  \ effort**: Agents working on same files\n- ❌ **Interface drift**: Changing contracts\
  \ without coordination\n- ❌ **Test-implementation mismatch**: Tests assuming different\
  \ behavior\n- ❌ **Merge hell**: Too long between integration points\n\n### Success\
  \ Criteria for Parallel Implementation\n- ✅ 3+ agents working concurrently on independent\
  \ components\n- ✅ Integration points tested every 2-3 hours\n- ✅ No merge conflicts\
  \ requiring >15 min to resolve\n- ✅ 40-60% time reduction vs sequential implementation\n\
  \n---\n\n## Phase 3: Review & Refinement (10-15% of effort) - PARALLELIZED\n\n###\
  \ Parallel Review Strategy\n\nLaunch multiple review agents simultaneously:\n\n\
  ```markdown\n[Concurrent review invocations]\n@pr-reviewer \"Review code quality\
  \ and best practices\"\n@security-analyzer \"Scan for security vulnerabilities\"\
  \n@performance-analyzer \"Check for performance issues\"\n@test-coverage-analyzer\
  \ \"Verify test coverage and quality\"\n```\n\nEach reviewer focuses on their specialty:\n\
  - **Code Quality**: Style, patterns, maintainability\n- **Security**: Vulnerabilities,\
  \ input validation, auth\n- **Performance**: N+1 queries, memory leaks, bottlenecks\n\
  - **Testing**: Coverage gaps, test quality, edge cases\n\n### Parallel Documentation\
  \ Updates\n\n```markdown\n[Concurrent documentation tasks]\n@documentation-writer\
  \ \"Update API documentation\"\n@documentation-writer \"Update README with new feature\"\
  \n@documentation-writer \"Create user guide for feature\"\n@diagram-creator \"Update\
  \ architecture diagrams\"\n```\n\n---\n\n## Phase 4: Code Review & Iteration (10-20%\
  \ of effort) - ENHANCED\n\n### Parallel Feedback Processing\n\nWhen multiple reviewers\
  \ provide feedback:\n\n1. **Categorize by Independence**:\n   - Independent fixes\
  \ (can be done in parallel)\n   - Dependent fixes (require sequential work)\n  \
  \ - Discussion items (need consensus first)\n\n2. **Spawn Fixup Agents**:\n   ```markdown\n\
  \   [Parallel fix implementation]\n   @code-fixer \"Address linting and style issues\"\
  \n   @code-fixer \"Improve error handling per review\"\n   @code-fixer \"Add missing\
  \ test cases\"\n   @code-fixer \"Optimize database queries\"\n   ```\n\n---\n\n\
  ## Phase 5: Deployment & Validation (5-10% of effort) - PARALLELIZED\n\n### Parallel\
  \ Deployment Validation\n\n```markdown\n[Concurrent validation tasks]\n@smoke-tester\
  \ \"Run smoke tests in staging\"\n@load-tester \"Execute performance tests\"\n@integration-tester\
  \ \"Verify third-party integrations\"\n@monitoring-validator \"Check metrics and\
  \ alerts\"\n```\n\n### Parallel Monitoring Streams\n\nDuring rollout, monitor multiple\
  \ aspects concurrently:\n- **Metrics Agent**: Watch performance metrics\n- **Log\
  \ Agent**: Analyze error logs\n- **User Agent**: Monitor user feedback channels\n\
  - **Business Agent**: Track business metrics\n\n---\n\n## Agent Coordination Patterns\n\
  \n### Pattern 1: Fork-Join\n```\nMain Task\n    ├── Fork: Spawn 3-4 agents for parallel\
  \ work\n    ├── Parallel Execution (independent work)\n    └── Join: Synthesize\
  \ results and continue\n```\n\n### Pattern 2: Pipeline\n```\nAgent 1: Research →\
  \ Agent 2: Design → Agent 3: Implement → Agent 4: Test\n                ↓      \
  \            ↓                    ↓\n            (interface)      (implementation)\
  \      (test results)\n```\n\n### Pattern 3: Map-Reduce\n```\nMap: Distribute work\
  \ across multiple agents\n    Agent 1: Component A\n    Agent 2: Component B\n \
  \   Agent 3: Component C\nReduce: Combine results into integrated solution\n```\n\
  \n### Pattern 4: Producer-Consumer\n```\nProducer Agents: Generate test cases, interfaces,\
  \ specifications\nConsumer Agents: Implement based on specifications\n```\n\n---\n\
  \n## Parallelization Rules of Thumb\n\n### When to Parallelize Aggressively (4+\
  \ agents)\n\n- ✅ Feature has 5+ independent components\n- ✅ Tight deadline requiring\
  \ speed\n- ✅ Well-defined interfaces between components\n- ✅ Team familiar with\
  \ codebase patterns\n- ✅ Low risk of conflicts (different domains)\n\n### When to\
  \ Limit Parallelization (1-2 agents)\n\n- ⚠️ High interdependency between components\n\
  - ⚠️ Unclear requirements requiring iteration\n- ⚠️ Shared state or database schema\
  \ changes\n- ⚠️ Critical path with high risk\n- ⚠️ Small feature (<4 hours total\
  \ work)\n\n### Optimal Parallelization by Feature Type\n\n| Feature Type | Optimal\
  \ Agents | Parallelization Strategy |\n|--------------|---------------|-------------------------|\n\
  | **CRUD API** | 3-4 | UI, API, DB, Tests in parallel |\n| **Refactoring** | 2-3\
  \ | Research + incremental refactor |\n| **Bug Fix** | 1-2 | Reproduce + fix (mostly\
  \ sequential) |\n| **New Service** | 4-5 | Multiple vertical slices |\n| **UI Component**\
  \ | 2-3 | Component, story, tests |\n| **Data Pipeline** | 3-4 | Stages can be parallel\
  \ |\n| **Integration** | 2 | Research + implementation |\n\n---\n\n## Time Savings\
  \ Through Parallelization\n\n### Traditional Sequential Approach\n```\nPhase 1:\
  \ Understanding (2 hours)\nPhase 2: Implementation (8 hours)\nPhase 3: Testing (4\
  \ hours)\nPhase 4: Review (2 hours)\nTotal: 16 hours\n```\n\n### Parallelized Approach\n\
  ```\nPhase 0: Parallel Analysis (0.5 hours)\nPhase 1: Parallel Understanding (0.5\
  \ hours - 4 agents)\nPhase 2: Parallel Implementation (3 hours - 4 agents)\nPhase\
  \ 3: Parallel Testing (1 hour - with implementation)\nPhase 4: Parallel Review (0.5\
  \ hours - 3 agents)\nTotal: 5.5 hours (65% reduction)\n```\n\n---\n\n## Multi-Agent\
  \ Task Tool Usage\n\n### Correct Pattern (Maximum Parallelization)\n```python\n\
  # GOOD: Single message, multiple invocations\nmessage = \"\"\"\nI'll explore all\
  \ aspects of this feature in parallel for maximum efficiency:\n\n[Task @explore\
  \ \"Frontend patterns in components/\"]\n[Task @explore \"Backend APIs in services/\"\
  ]\n[Task @explore \"Database schemas in migrations/\"]\n[Task @explore \"Test patterns\
  \ in tests/\"]\n\nThis parallel exploration will complete in ~15 minutes instead\
  \ of an hour.\n\"\"\"\n```\n\n### Anti-Pattern (Sequential)\n```python\n# BAD: Multiple\
  \ messages, sequential execution\nmessage1 = \"[Task @explore 'Frontend patterns']\"\
  \n# Wait for completion...\nmessage2 = \"[Task @explore 'Backend APIs']\"\n# Wait\
  \ for completion...\n# This takes 4x longer!\n```\n\n---\n\n## Workflow Summary\
  \ with Parallelization\n\n```\nPhase 0: Parallelization Analysis [NEW]\n├─ [ ] Decompose\
  \ feature into independent components\n├─ [ ] Identify parallelization opportunities\n\
  ├─ [ ] Plan multi-agent strategy\n└─ [ ] Define integration checkpoints\n\nPhase\
  \ 1: Understanding & Planning [PARALLEL]\n├─ [ ] Launch 3-4 Explore agents concurrently\n\
  ├─ [ ] Research best practices in parallel\n├─ [ ] Synthesize findings into unified\
  \ plan\n└─ [ ] Define interfaces for parallel work\n\nPhase 2: Implementation [PARALLEL]\n\
  ├─ [ ] Define contracts/interfaces (sequential)\n├─ [ ] Launch parallel implementation\
  \ agents\n│   ├─ [ ] Frontend (Agent 1)\n│   ├─ [ ] Backend (Agent 2)\n│   ├─ [\
  \ ] Database (Agent 3)\n│   └─ [ ] Tests (Agent 4)\n├─ [ ] Integration checkpoint\
  \ every 2 hours\n└─ [ ] Final integration and verification\n\nPhase 3: Review &\
  \ Refinement [PARALLEL]\n├─ [ ] Launch multiple review agents\n├─ [ ] Process feedback\
  \ in parallel\n└─ [ ] Update docs concurrently\n\nPhase 4: Code Review [ENHANCED]\n\
  ├─ [ ] Categorize feedback by independence\n├─ [ ] Fix independent issues in parallel\n\
  └─ [ ] Sequential fixes for dependencies\n\nPhase 5: Deployment [PARALLEL]\n├─ [\
  \ ] Parallel validation streams\n├─ [ ] Concurrent monitoring\n└─ [ ] Synthesize\
  \ results\n\nPhase 6: Post-Deployment [ENHANCED]\n├─ [ ] Multi-stream monitoring\n\
  └─ [ ] Parallel retrospectives\n```\n\n---\n\n## Success Metrics for Parallelization\n\
  \n### Individual Feature Level\n- ✅ 40-70% reduction in implementation time\n- ✅\
  \ 3+ agents working concurrently during peak\n- ✅ <15 minutes to resolve integration\
  \ conflicts\n- ✅ Parallel tests catch issues early\n- ✅ All integration points properly\
  \ synchronized\n\n### Team Efficiency Level\n- ✅ Features completed in hours, not\
  \ days\n- ✅ Reduced context switching through focused agents\n- ✅ Better specialization\
  \ (each agent expert in domain)\n- ✅ Knowledge synthesis from parallel research\n\
  - ✅ Faster iteration cycles\n\n### System Performance Level\n- ✅ Higher throughput\
  \ (more features per sprint)\n- ✅ Better quality (specialized agents catch more\
  \ issues)\n- ✅ Improved test coverage (dedicated test agents)\n- ✅ Comprehensive\
  \ documentation (parallel doc writers)\n- ✅ Reduced time-to-market\n\n---\n\n##\
  \ Implementation Notes\n\n1. **ALWAYS assess parallelization potential** before\
  \ starting implementation\n2. **Launch multiple agents in SINGLE message** for true\
  \ parallelization\n3. **Define clear interfaces** before parallel implementation\n\
  4. **Schedule integration checkpoints** every 2-3 hours\n5. **Use TodoWrite** to\
  \ track both sequential phases and parallel tasks\n6. **Monitor for conflicts**\
  \ and adjust parallelization if needed\n7. **Synthesize parallel results** into\
  \ cohesive solution\n\n---\n\n## Example: Full Parallel Implementation\n\n```markdown\n\
  ## Feature: Add User Authentication System\n\n### Phase 0: Parallelization Analysis\n\
  This feature can be decomposed into:\n- Frontend: Login/Register forms, session\
  \ management\n- Backend: Auth endpoints, JWT handling, middleware\n- Database: User\
  \ tables, session storage\n- Tests: Unit, integration, E2E test suites\n\nThese\
  \ are highly independent after interface definition.\n\n### Execution Plan\n\nI'll\
  \ implement this using maximum parallelization:\n\n**Step 1: Interface Definition\
  \ (30 min)**\n[Define API contracts, data models, and auth flow]\n\n**Step 2: Parallel\
  \ Implementation (2 hours)**\n[Launching 4 agents concurrently:]\n\n@feature-implementation\
  \ \"Frontend auth components with forms and session handling\"\n@feature-implementation\
  \ \"Backend auth API with JWT and middleware\"\n@feature-implementation \"Database\
  \ schema and migrations for users\"\n@test-builder \"Comprehensive test suite for\
  \ authentication\"\n\n**Step 3: Integration (30 min)**\n[Merge all components and\
  \ verify end-to-end flow]\n\nThis parallel approach will complete in 3 hours instead\
  \ of 8-10 hours sequential.\n```\n\n---\n\n## Related Resources\n\n- Six-Phase Software\
  \ Implementation Methodology (enhanced with parallelization)\n- Multi-Agent Coordination\
  \ Patterns for Software Development\n- Parallel Development Best Practices\n- Task\
  \ Tool Advanced Usage Guide\n- Agent Specialization Matrix\n\n---\n\n**Remember**:\
  \ Elite performers achieve speed not by cutting corners, but by intelligent parallelization.\
  \ Identify independent work streams, launch multiple agents concurrently, and coordinate\
  \ at integration points for maximum efficiency while maintaining quality.\n"
---

# Implement Feature: $@

Implement the requested feature following the **Six-Phase Software Implementation Methodology** with **intelligent parallelization** - a research-backed framework that balances quality, speed, and maintainability through concurrent execution where appropriate.

**Key Insight**: Elite performers achieve multiple daily deployments not by working sequentially, but by identifying independent work streams and executing them in parallel while maintaining quality gates at integration points.

---

## Phase 0: Parallelization Analysis (NEW - 5% of effort)

**Purpose**: Analyze the feature for parallelization opportunities before starting implementation.

### Parallelization Assessment

1. **Decomposition Analysis**:
   - Break feature into atomic sub-components
   - Identify dependencies between components
   - Map data flow and integration points
   - Determine which components can be developed independently

2. **File Independence Matrix**:
   ```
   Component A | Component B | Dependency Type | Can Parallelize?
   ------------|-------------|-----------------|------------------
   Frontend UI | Backend API | Interface only  | Yes (define contract first)
   Service A   | Service B   | None           | Yes (fully independent)
   Module X    | Module Y    | Shared utils   | Partial (utils first)
   ```

3. **Parallelization Strategies**:

   **Vertical Slice Parallelization**:
   - Independent feature slices that deliver value end-to-end
   - Each slice has its own UI, API, and data layer
   - Example: User profile view vs. user profile edit

   **Horizontal Layer Parallelization**:
   - Different architectural layers worked on simultaneously
   - Requires well-defined interfaces/contracts
   - Example: Frontend and backend teams working in parallel

   **Test Parallelization**:
   - Unit tests independent of implementation
   - Integration test scaffolding while building
   - Performance test harness preparation

   **Research Parallelization**:
   - Multiple Explore agents investigating different areas
   - Concurrent pattern discovery in different modules
   - Parallel best practice research

### Multi-Agent Spawn Decision Matrix

| Scenario | Agents to Spawn | Invocation Pattern |
|----------|----------------|-------------------|
| **Multi-module feature** | 2-3 Explore agents | Concurrent exploration of each module |
| **Frontend + Backend** | 2 implementation agents | Parallel after interface definition |
| **Complex refactoring** | Explore + code-refactoring | Research patterns while refactoring |
| **New API with tests** | Implementation + test agents | Build and test concurrently |
| **Unknown codebase** | 3-4 Explore agents | Map different subsystems simultaneously |

### Success Criteria for Parallelization
- ✅ Feature decomposed into 3+ independent work streams
- ✅ Dependencies clearly mapped with integration points defined
- ✅ Parallel execution plan saves 30%+ time vs sequential
- ✅ Risk of integration conflicts assessed and mitigated

**Use Task tool with multiple invocations in a SINGLE message for maximum parallelization.**

---

## Phase 1: Understanding & Planning (10-15% of effort) - ENHANCED

**Purpose**: Ensure clear requirements and identify parallelization opportunities.

### Activities (with Parallelization)

1. **Parallel Requirements Gathering**:
   ```
   Launch concurrently:
   - Task @explore "Find similar features and patterns"
   - Task @explore "Investigate existing APIs and interfaces"
   - Task @explore "Search for reusable components"
   - Task @knowledge-synthesis "Research best practices for [feature type]"
   ```

2. **Concurrent Domain Exploration**:
   - **Agent 1**: Explore frontend patterns and UI components
   - **Agent 2**: Explore backend services and data models
   - **Agent 3**: Explore testing patterns and fixtures
   - **Agent 4**: Research external best practices

3. **Parallel Design Activities**:
   - Architecture design (one agent)
   - API contract definition (another agent)
   - Test scenario planning (third agent)
   - Performance requirements analysis (fourth agent)

### Example Multi-Agent Invocation

```markdown
I'll explore this feature using multiple agents in parallel for efficiency:

[Task tool invocations]
- @explore "Find all authentication implementations in services/"
- @explore "Analyze current database schema for user tables"
- @explore "Identify all test patterns for API endpoints"
- @knowledge-synthesis "Best practices for JWT authentication in microservices"

This parallel exploration will give us comprehensive understanding quickly.
```

### Parallelization Checkpoint
- ✅ Multiple agents launched in single message
- ✅ Each agent has clear, non-overlapping scope
- ✅ Results will be synthesized into unified plan
- ✅ Time saved: 50-70% vs sequential exploration

**Use TodoWrite to track both sequential phases AND parallel tasks within each phase.**

---

## Phase 2: Implementation (40-50% of effort) - PARALLELIZED

**Purpose**: Transform requirements into working code through parallel development streams.

### Parallel Implementation Patterns

#### Pattern 1: Interface-First Parallel Development
```
Step 1: Define contracts (sequential - 1 hour)
└── API interfaces, data models, message formats

Step 2: Parallel implementation (concurrent - 4 hours)
├── Frontend implementation (Agent 1)
├── Backend implementation (Agent 2)
├── Database migrations (Agent 3)
└── Test suite development (Agent 4)

Step 3: Integration (sequential - 1 hour)
└── Connect all components and verify
```

#### Pattern 2: Vertical Slice Parallelization
```
Slice 1: User Registration (Agent 1)
├── UI form
├── API endpoint
├── Database operations
└── Tests

Slice 2: User Login (Agent 2)
├── UI form
├── API endpoint
├── Session management
└── Tests

Slice 3: Password Reset (Agent 3)
├── UI flow
├── API endpoints
├── Email integration
└── Tests
```

#### Pattern 3: Test-Driven Parallel Development
```
Concurrent Execution:
├── Test Writer (Agent 1): Creates all test cases
├── Implementation (Agent 2): Implements to pass tests
├── Documentation (Agent 3): Writes docs as code emerges
└── Performance (Agent 4): Sets up monitoring/profiling
```

### Multi-Agent Implementation Example

```markdown
Based on our parallelization analysis, I'll implement this feature using 4 concurrent work streams:

[Task tool invocations in single message]
@feature-implementation "Implement user profile frontend component with edit capability"
@feature-implementation "Build REST API for user profile CRUD operations"
@feature-implementation "Create database migrations and repository layer for profiles"
@java-test-builder "Generate comprehensive test suite for profile feature"

Each agent will work independently and we'll integrate at defined checkpoints.
```

### Coordination Checkpoints

**Every 2 hours during parallel work:**
1. Verify interfaces still align
2. Check for merge conflicts
3. Run integration tests
4. Adjust remaining work distribution

### Parallel Work Anti-Patterns to Avoid

- ❌ **Duplicated effort**: Agents working on same files
- ❌ **Interface drift**: Changing contracts without coordination
- ❌ **Test-implementation mismatch**: Tests assuming different behavior
- ❌ **Merge hell**: Too long between integration points

### Success Criteria for Parallel Implementation
- ✅ 3+ agents working concurrently on independent components
- ✅ Integration points tested every 2-3 hours
- ✅ No merge conflicts requiring >15 min to resolve
- ✅ 40-60% time reduction vs sequential implementation

---

## Phase 3: Review & Refinement (10-15% of effort) - PARALLELIZED

### Parallel Review Strategy

Launch multiple review agents simultaneously:

```markdown
[Concurrent review invocations]
@pr-reviewer "Review code quality and best practices"
@security-analyzer "Scan for security vulnerabilities"
@performance-analyzer "Check for performance issues"
@test-coverage-analyzer "Verify test coverage and quality"
```

Each reviewer focuses on their specialty:
- **Code Quality**: Style, patterns, maintainability
- **Security**: Vulnerabilities, input validation, auth
- **Performance**: N+1 queries, memory leaks, bottlenecks
- **Testing**: Coverage gaps, test quality, edge cases

### Parallel Documentation Updates

```markdown
[Concurrent documentation tasks]
@documentation-writer "Update API documentation"
@documentation-writer "Update README with new feature"
@documentation-writer "Create user guide for feature"
@diagram-creator "Update architecture diagrams"
```

---

## Phase 4: Code Review & Iteration (10-20% of effort) - ENHANCED

### Parallel Feedback Processing

When multiple reviewers provide feedback:

1. **Categorize by Independence**:
   - Independent fixes (can be done in parallel)
   - Dependent fixes (require sequential work)
   - Discussion items (need consensus first)

2. **Spawn Fixup Agents**:
   ```markdown
   [Parallel fix implementation]
   @code-fixer "Address linting and style issues"
   @code-fixer "Improve error handling per review"
   @code-fixer "Add missing test cases"
   @code-fixer "Optimize database queries"
   ```

---

## Phase 5: Deployment & Validation (5-10% of effort) - PARALLELIZED

### Parallel Deployment Validation

```markdown
[Concurrent validation tasks]
@smoke-tester "Run smoke tests in staging"
@load-tester "Execute performance tests"
@integration-tester "Verify third-party integrations"
@monitoring-validator "Check metrics and alerts"
```

### Parallel Monitoring Streams

During rollout, monitor multiple aspects concurrently:
- **Metrics Agent**: Watch performance metrics
- **Log Agent**: Analyze error logs
- **User Agent**: Monitor user feedback channels
- **Business Agent**: Track business metrics

---

## Agent Coordination Patterns

### Pattern 1: Fork-Join
```
Main Task
    ├── Fork: Spawn 3-4 agents for parallel work
    ├── Parallel Execution (independent work)
    └── Join: Synthesize results and continue
```

### Pattern 2: Pipeline
```
Agent 1: Research → Agent 2: Design → Agent 3: Implement → Agent 4: Test
                ↓                  ↓                    ↓
            (interface)      (implementation)      (test results)
```

### Pattern 3: Map-Reduce
```
Map: Distribute work across multiple agents
    Agent 1: Component A
    Agent 2: Component B
    Agent 3: Component C
Reduce: Combine results into integrated solution
```

### Pattern 4: Producer-Consumer
```
Producer Agents: Generate test cases, interfaces, specifications
Consumer Agents: Implement based on specifications
```

---

## Parallelization Rules of Thumb

### When to Parallelize Aggressively (4+ agents)

- ✅ Feature has 5+ independent components
- ✅ Tight deadline requiring speed
- ✅ Well-defined interfaces between components
- ✅ Team familiar with codebase patterns
- ✅ Low risk of conflicts (different domains)

### When to Limit Parallelization (1-2 agents)

- ⚠️ High interdependency between components
- ⚠️ Unclear requirements requiring iteration
- ⚠️ Shared state or database schema changes
- ⚠️ Critical path with high risk
- ⚠️ Small feature (<4 hours total work)

### Optimal Parallelization by Feature Type

| Feature Type | Optimal Agents | Parallelization Strategy |
|--------------|---------------|-------------------------|
| **CRUD API** | 3-4 | UI, API, DB, Tests in parallel |
| **Refactoring** | 2-3 | Research + incremental refactor |
| **Bug Fix** | 1-2 | Reproduce + fix (mostly sequential) |
| **New Service** | 4-5 | Multiple vertical slices |
| **UI Component** | 2-3 | Component, story, tests |
| **Data Pipeline** | 3-4 | Stages can be parallel |
| **Integration** | 2 | Research + implementation |

---

## Time Savings Through Parallelization

### Traditional Sequential Approach
```
Phase 1: Understanding (2 hours)
Phase 2: Implementation (8 hours)
Phase 3: Testing (4 hours)
Phase 4: Review (2 hours)
Total: 16 hours
```

### Parallelized Approach
```
Phase 0: Parallel Analysis (0.5 hours)
Phase 1: Parallel Understanding (0.5 hours - 4 agents)
Phase 2: Parallel Implementation (3 hours - 4 agents)
Phase 3: Parallel Testing (1 hour - with implementation)
Phase 4: Parallel Review (0.5 hours - 3 agents)
Total: 5.5 hours (65% reduction)
```

---

## Multi-Agent Task Tool Usage

### Correct Pattern (Maximum Parallelization)
```python
# GOOD: Single message, multiple invocations
message = """
I'll explore all aspects of this feature in parallel for maximum efficiency:

[Task @explore "Frontend patterns in components/"]
[Task @explore "Backend APIs in services/"]
[Task @explore "Database schemas in migrations/"]
[Task @explore "Test patterns in tests/"]

This parallel exploration will complete in ~15 minutes instead of an hour.
"""
```

### Anti-Pattern (Sequential)
```python
# BAD: Multiple messages, sequential execution
message1 = "[Task @explore 'Frontend patterns']"
# Wait for completion...
message2 = "[Task @explore 'Backend APIs']"
# Wait for completion...
# This takes 4x longer!
```

---

## Workflow Summary with Parallelization

```
Phase 0: Parallelization Analysis [NEW]
├─ [ ] Decompose feature into independent components
├─ [ ] Identify parallelization opportunities
├─ [ ] Plan multi-agent strategy
└─ [ ] Define integration checkpoints

Phase 1: Understanding & Planning [PARALLEL]
├─ [ ] Launch 3-4 Explore agents concurrently
├─ [ ] Research best practices in parallel
├─ [ ] Synthesize findings into unified plan
└─ [ ] Define interfaces for parallel work

Phase 2: Implementation [PARALLEL]
├─ [ ] Define contracts/interfaces (sequential)
├─ [ ] Launch parallel implementation agents
│   ├─ [ ] Frontend (Agent 1)
│   ├─ [ ] Backend (Agent 2)
│   ├─ [ ] Database (Agent 3)
│   └─ [ ] Tests (Agent 4)
├─ [ ] Integration checkpoint every 2 hours
└─ [ ] Final integration and verification

Phase 3: Review & Refinement [PARALLEL]
├─ [ ] Launch multiple review agents
├─ [ ] Process feedback in parallel
└─ [ ] Update docs concurrently

Phase 4: Code Review [ENHANCED]
├─ [ ] Categorize feedback by independence
├─ [ ] Fix independent issues in parallel
└─ [ ] Sequential fixes for dependencies

Phase 5: Deployment [PARALLEL]
├─ [ ] Parallel validation streams
├─ [ ] Concurrent monitoring
└─ [ ] Synthesize results

Phase 6: Post-Deployment [ENHANCED]
├─ [ ] Multi-stream monitoring
└─ [ ] Parallel retrospectives
```

---

## Success Metrics for Parallelization

### Individual Feature Level
- ✅ 40-70% reduction in implementation time
- ✅ 3+ agents working concurrently during peak
- ✅ <15 minutes to resolve integration conflicts
- ✅ Parallel tests catch issues early
- ✅ All integration points properly synchronized

### Team Efficiency Level
- ✅ Features completed in hours, not days
- ✅ Reduced context switching through focused agents
- ✅ Better specialization (each agent expert in domain)
- ✅ Knowledge synthesis from parallel research
- ✅ Faster iteration cycles

### System Performance Level
- ✅ Higher throughput (more features per sprint)
- ✅ Better quality (specialized agents catch more issues)
- ✅ Improved test coverage (dedicated test agents)
- ✅ Comprehensive documentation (parallel doc writers)
- ✅ Reduced time-to-market

---

## Implementation Notes

1. **ALWAYS assess parallelization potential** before starting implementation
2. **Launch multiple agents in SINGLE message** for true parallelization
3. **Define clear interfaces** before parallel implementation
4. **Schedule integration checkpoints** every 2-3 hours
5. **Use TodoWrite** to track both sequential phases and parallel tasks
6. **Monitor for conflicts** and adjust parallelization if needed
7. **Synthesize parallel results** into cohesive solution

---

## Example: Full Parallel Implementation

```markdown
## Feature: Add User Authentication System

### Phase 0: Parallelization Analysis
This feature can be decomposed into:
- Frontend: Login/Register forms, session management
- Backend: Auth endpoints, JWT handling, middleware
- Database: User tables, session storage
- Tests: Unit, integration, E2E test suites

These are highly independent after interface definition.

### Execution Plan

I'll implement this using maximum parallelization:

**Step 1: Interface Definition (30 min)**
[Define API contracts, data models, and auth flow]

**Step 2: Parallel Implementation (2 hours)**
[Launching 4 agents concurrently:]

@feature-implementation "Frontend auth components with forms and session handling"
@feature-implementation "Backend auth API with JWT and middleware"
@feature-implementation "Database schema and migrations for users"
@test-builder "Comprehensive test suite for authentication"

**Step 3: Integration (30 min)**
[Merge all components and verify end-to-end flow]

This parallel approach will complete in 3 hours instead of 8-10 hours sequential.
```

---

## Final Phase: Automated Quality Gate (REQUIRED)

After all implementation phases complete, **always run `/code:fix-loop`** before declaring the feature done.

```
/code:fix-loop
```

This automatically:
1. Runs build, tests, lint, and type checks in parallel using minimal-context agents
2. Fixes every failure found (auto-fix for lint, targeted agents for test/type/build failures)
3. Re-verifies after fixes, looping until all checks pass (max 5 iterations)
4. Exits with a report of what was fixed and what (if anything) needs human attention

**Do not open a PR or declare the feature complete until `fix-loop` exits with ✅ All green.**

After `fix-loop` passes, run `/code:is-it-ready` for architectural sign-off before opening the PR.

---

## Related Resources

- Six-Phase Software Implementation Methodology (enhanced with parallelization)
- Multi-Agent Coordination Patterns for Software Development
- Parallel Development Best Practices
- Task Tool Advanced Usage Guide
- Agent Specialization Matrix

---

**Remember**: Elite performers achieve speed not by cutting corners, but by intelligent parallelization. Identify independent work streams, launch multiple agents concurrently, and coordinate at integration points for maximum efficiency while maintaining quality.
