---
title: Architecture Review with Best Practices
description: Comprehensive architecture review analyzing SOLID, Clean Architecture, Clean Code, DDD, and Design Patterns adherence with actionable recommendations
arguments: [path]
options:
  - name: target
    type: string
    description: "Specific component to analyze (class:Name, package:path, module:name, layer:domain)"
  - name: depth
    type: string
    choices: [quick, standard, deep]
    default: auto
    description: "Analysis depth - quick (5min), standard (15min), deep (30min+)"
  - name: context
    type: string
    choices: [current, changes, recent, all]
    default: auto
    description: "Context to use - current file, git changes, recent commits, or all code"
  - name: principles
    type: array
    choices: [srp, ocp, lsp, isp, dip, clean-arch, clean-code, ddd, patterns, coupling, all]
    default: auto
    description: "Specific principles to analyze (comma-separated)"
  - name: format
    type: string
    choices: [summary, detailed, actionable, pr-review, report]
    default: auto
    description: "Output format based on use case"
  - name: focus
    type: string
    description: "Legacy option - maintained for backward compatibility, maps to principles"
---

# Architecture Review: Context-Aware Analysis

Perform targeted or comprehensive architecture reviews with automatic context detection and configurable depth. The review adapts to your current workflow - whether you're doing a quick PR review, analyzing a specific component, or conducting a full architectural assessment.

## Smart Context Detection

The command automatically detects and uses context when no explicit parameters are provided:

### Auto-Detection Logic

When invoked without explicit parameters, the review intelligently determines:
1. **Scope**: What code to analyze (current file, changes, or full codebase)
2. **Depth**: How thorough the analysis should be (quick, standard, or deep)
3. **Principles**: Which architectural principles are most relevant
4. **Format**: The most appropriate output format for the situation

### Context Detection Rules

#### Current File Context (`--context=current`)
- Triggered when a file is open in the editor
- Analyzes the current class/module and its immediate dependencies
- Automatically sets `--depth=quick` for single files
- Focuses on principles relevant to the file type

#### Git Changes Context (`--context=changes`)
- Triggered when uncommitted changes exist
- Reviews modified files and their architectural impact
- Sets `--depth=standard` for change sets
- Emphasizes regression prevention and maintaining standards

#### Recent Activity Context (`--context=recent`)
- Reviews commits from current branch
- Useful for pre-PR comprehensive review
- Sets `--depth=standard` or `deep` based on change volume
- Focus on architectural consistency

#### Full Context (`--context=all`)
- Complete codebase analysis
- Sets `--depth=deep` for thorough review
- Comprehensive principle evaluation

## Targeted Component Analysis

### Component Targeting Syntax

```bash
# Class-level analysis
--target=class:ServiceCorrelationService

# Package/namespace analysis
--target=package:bet.fanatics.scorecards.service

# Module analysis
--target=module:scorecards-core

# Layer analysis
--target=layer:domain
--target=layer:infrastructure
--target=layer:application

# Pattern-based targeting
--target=pattern:*Repository  # All repositories
--target=pattern:*Controller  # All controllers
--target=pattern:*Service     # All services
```

### Target Resolution Strategy

**Class Target**: Analyzes the class, its dependencies, interfaces, coupling, and single responsibility
**Package Target**: Reviews all classes, package cohesion, inter-package dependencies, bounded contexts
**Module Target**: Reviews module boundaries, public APIs, dependencies, separation of concerns
**Layer Target**: Reviews layer compliance, dependency directions, clean architecture rules

## Analysis Depth Configuration

### Quick Assessment (`--depth=quick`)
**Duration**: 5-10 minutes | **Use Cases**: PR reviews, spot checks, pre-commit validation

- Targets component only with direct dependencies
- Identifies obvious violations and critical issues (P0-P1)
- Provides violation counts and top 3-5 issues
- Quick fixes and pass/fail recommendation

### Standard Review (`--depth=standard`)
**Duration**: 15-30 minutes | **Use Cases**: Feature completion, sprint reviews, module refactoring

- Targets and related components with transitive dependencies
- Identifies common violations and P0-P2 issues
- Provides scored assessment (1-10) with categorized issues
- Refactoring suggestions and priority recommendations

### Deep Analysis (`--depth=deep`)
**Duration**: 30-60+ minutes | **Use Cases**: Architecture reviews, technical debt assessment

- Complete dependency graph analysis
- All architectural layers and comprehensive metrics
- All priority issues with detailed scoring
- Complete refactoring roadmap and documentation

## Principle-Focused Reviews

### Selective Principle Analysis

```bash
# Single principle focus
--principles=srp                    # Single Responsibility only
--principles=dip,isp               # Dependency Inversion + Interface Segregation
--principles=clean-arch,clean-code  # Architecture and code quality
--principles=all                    # Comprehensive analysis
```

### Principle Shortcuts

- `srp`: Single Responsibility Principle
- `ocp`: Open/Closed Principle
- `lsp`: Liskov Substitution Principle
- `isp`: Interface Segregation Principle
- `dip`: Dependency Inversion Principle
- `clean-arch`: Clean Architecture layers and boundaries
- `clean-code`: Naming, functions, organization, error handling
- `ddd`: Domain-Driven Design patterns and boundaries
- `patterns`: Design pattern usage and opportunities
- `coupling`: Coupling and cohesion analysis

## Output Format Options

### Summary Format (`--format=summary`)
Concise overview with score, critical issues, and quick wins. Ideal for quick assessments.

### PR Review Format (`--format=pr-review`)
Structured feedback for pull requests with approval status, good practices, and suggestions.

### Actionable Format (`--format=actionable`)
Step-by-step refactoring plans with specific commands and agent usage instructions.

### Detailed Format (`--format=detailed`)
Comprehensive analysis with examples, metrics, and in-depth recommendations (default for deep analysis).

### Report Format (`--format=report`)
Executive-friendly format with visualizations, trends, and strategic recommendations.

## Enhanced Usage Examples

### Context-Aware Quick Reviews
```bash
# Auto-detect context and scope
/quality:architecture-review

# Quick review of current file
/quality:architecture-review --context=current

# PR review of changes
/quality:architecture-review --context=changes --format=pr-review
```

### Targeted Analysis
```bash
# Review specific class for SOLID violations
/quality:architecture-review --target=class:UserService --principles=srp,ocp,lsp,isp,dip

# Deep coupling analysis of a module
/quality:architecture-review --target=module:core --principles=coupling --depth=deep

# DDD review of domain layer
/quality:architecture-review --target=layer:domain --principles=ddd
```

### Workflow Integration
```bash
# Pre-commit check
/quality:architecture-review --context=changes --depth=quick --format=summary

# Sprint review
/quality:architecture-review --context=recent --depth=standard --format=actionable

# Technical debt assessment
/quality:architecture-review --depth=deep --format=report
```

## Backward Compatibility

The command maintains full backward compatibility:
- Basic invocation (`/quality:architecture-review`) works identically
- Path arguments are still supported
- `--focus` flag is mapped to `--principles` for legacy support
- Default behavior preserved when no options specified

---

## Review Framework

This review is grounded in authoritative software engineering principles:

### 1. **SOLID Principles**
- **Single Responsibility Principle (SRP)**: Classes have one reason to change
- **Open/Closed Principle (OCP)**: Open for extension, closed for modification
- **Liskov Substitution Principle (LSP)**: Subtypes replaceable with base types
- **Interface Segregation Principle (ISP)**: No client forced to depend on unused methods
- **Dependency Inversion Principle (DIP)**: Depend on abstractions, not concretions

### 2. **Clean Architecture Layers**
- **Entities Layer**: Enterprise-wide business rules
- **Use Cases Layer**: Application-specific business rules
- **Interface Adapters Layer**: Controllers, presenters, gateways
- **Frameworks and Drivers Layer**: External tools and frameworks
- **Dependency Rule**: Dependencies point inward toward business logic

### 3. **Clean Code Principles**
- **Meaningful Names**: Intention-revealing, searchable, pronounceable
- **Functions**: Small, single responsibility, few arguments
- **Comments**: Explain "why" not "what", avoid redundancy
- **Error Handling**: Use exceptions, informative messages, don't return null
- **Classes**: Small, high cohesion, maintain encapsulation

### 4. **Domain-Driven Design**
- **Ubiquitous Language**: Shared vocabulary in code
- **Bounded Contexts**: Explicit boundaries for domain models
- **Entities**: Identity-based domain objects
- **Value Objects**: Attribute-based immutable objects
- **Aggregates**: Transaction and consistency boundaries
- **Domain Events**: Business-significant occurrences
- **Repositories**: Collection-like access to aggregates

### 5. **Design Patterns**
- **Creational**: Factory, Singleton, Builder
- **Structural**: Adapter, Facade, Decorator
- **Behavioral**: Strategy, Observer, Command

---

## Phase 1: Discovery and Mapping (Using Explore Agent)

Use the **Explore agent** to systematically discover and map the architecture:

### Codebase Exploration Tasks

1. **Identify Project Structure**:
   - Find main source directories and package organization
   - Identify framework and technology choices
   - Discover configuration and dependency management
   - Map test structure and coverage

2. **Discover Domain Boundaries**:
   - Search for domain models and entities
   - Identify services and use cases
   - Find repositories and data access patterns
   - Locate infrastructure and framework code

3. **Analyze Dependencies**:
   - Map import/dependency relationships
   - Identify coupling between modules
   - Find circular dependencies
   - Discover tight coupling to frameworks

4. **Find Key Abstractions**:
   - Locate interfaces and abstract classes
   - Identify design pattern implementations
   - Find dependency injection usage
   - Discover architectural boundaries

### Exploration Queries

Launch the Explore agent with these queries (adjust based on language/framework):

```
# Project structure and organization
"What is the overall project structure and how is code organized?"

# Domain model discovery
"Find all domain entities, value objects, and aggregates"

# Dependency analysis
"Analyze coupling between packages/modules and identify tight coupling"

# Interface and abstraction usage
"Find all interfaces and analyze dependency inversion usage"

# Design pattern usage
"Identify design pattern implementations (Factory, Strategy, Repository, etc.)"

# Testing architecture
"Analyze test structure and how tests are organized relative to production code"
```

---

## Phase 2: Principle-by-Principle Analysis

### SOLID Principles Analysis

**Single Responsibility Principle (SRP)**
- [ ] Identify classes with multiple responsibilities
- [ ] Look for classes that change for multiple reasons
- [ ] Check for "God classes" (>500 lines, many methods)
- [ ] Verify each class has clear, focused purpose
- [ ] Example violations:
  - Classes mixing business logic with persistence
  - Controllers handling validation, business rules, and presentation
  - Services doing too many unrelated tasks

**Open/Closed Principle (OCP)**
- [ ] Find code requiring modification for extensions
- [ ] Check for long if/else or switch statements on types
- [ ] Verify use of polymorphism for behavior variation
- [ ] Look for hardcoded dependencies that prevent extension
- [ ] Example violations:
  - Switch statements on enum/type that require modification
  - Classes that can't be extended without modifying source

**Liskov Substitution Principle (LSP)**
- [ ] Verify subtypes can replace base types
- [ ] Check for override methods that change expected behavior
- [ ] Look for precondition strengthening or postcondition weakening
- [ ] Identify inheritance misuse (using inheritance for code reuse only)
- [ ] Example violations:
  - Subclasses throwing unexpected exceptions
  - Overridden methods with stricter preconditions

**Interface Segregation Principle (ISP)**
- [ ] Find "fat" interfaces with many methods
- [ ] Check for clients depending on unused methods
- [ ] Verify interfaces are client-specific, not general-purpose
- [ ] Look for interfaces forcing empty implementations
- [ ] Example violations:
  - Large interfaces with 10+ methods
  - Implementations with many no-op methods

**Dependency Inversion Principle (DIP)**
- [ ] Check high-level modules depending on low-level modules
- [ ] Verify dependencies on abstractions (interfaces) not concretions
- [ ] Look for new keyword creating concrete dependencies
- [ ] Check for proper dependency injection usage
- [ ] Example violations:
  - Business logic directly instantiating database implementations
  - Controllers creating service instances directly

### Clean Architecture Analysis

**Layer Separation and Dependency Rule**
- [ ] Map code to architectural layers (Entities, Use Cases, Adapters, Frameworks)
- [ ] Verify dependencies only point inward
- [ ] Check for business logic free of framework dependencies
- [ ] Identify leaky abstractions between layers
- [ ] Example violations:
  - Domain entities depending on ORM annotations
  - Use cases importing web framework types
  - Business logic coupled to database implementation

**Boundary Crossings**
- [ ] Verify proper use of interfaces at boundaries
- [ ] Check data structures crossing boundaries (DTOs)
- [ ] Look for framework types leaking into domain
- [ ] Identify proper adapter usage
- [ ] Example violations:
  - HTTP request/response objects in domain layer
  - Database entities used as domain models
  - Framework exceptions propagating to business logic

**Testability**
- [ ] Verify business rules testable without frameworks
- [ ] Check for mocking capabilities at boundaries
- [ ] Look for dependency injection enabling test doubles
- [ ] Identify hard-to-test code due to tight coupling
- [ ] Example issues:
  - Business logic requiring database for testing
  - Use cases needing web server to test
  - Static dependencies preventing mocking

### Clean Code Analysis

**Naming Quality**
- [ ] Check for intention-revealing names
- [ ] Identify abbreviations and unclear names
- [ ] Look for inconsistent naming conventions
- [ ] Verify domain language used in code
- [ ] Example violations:
  - `processData()`, `doStuff()`, `handle()`
  - Single-letter variables (except loop counters)
  - Inconsistent naming (getUser vs fetchUser vs retrieveUser)

**Function Quality**
- [ ] Identify long functions (>20 lines)
- [ ] Check for functions doing multiple things
- [ ] Look for functions with many parameters (>3)
- [ ] Verify functions at single abstraction level
- [ ] Example violations:
  - Functions with mixed abstraction (high and low level)
  - Functions with side effects not indicated by name
  - Functions both querying and mutating state

**Comment Quality**
- [ ] Identify redundant comments (explaining obvious code)
- [ ] Look for outdated or misleading comments
- [ ] Check if comments indicate code smell (needs refactoring)
- [ ] Verify meaningful comments explain "why" not "what"
- [ ] Example issues:
  - `// increment counter` above `counter++;`
  - Commented-out code blocks
  - TODOs without tickets or timelines

**Error Handling**
- [ ] Check for proper exception usage
- [ ] Look for null returns/checks that could use Optional
- [ ] Verify informative error messages
- [ ] Identify swallowed exceptions (empty catch blocks)
- [ ] Example violations:
  - Returning null instead of Optional or empty collections
  - Generic exception messages without context
  - Catch-all exception handlers

**Code Organization**
- [ ] Check for logical grouping within classes
- [ ] Verify vertical ordering (public → private)
- [ ] Look for mixed concerns in single file
- [ ] Identify inconsistent formatting
- [ ] Example issues:
  - Private methods at top, public at bottom
  - Related functionality scattered across file
  - Inconsistent indentation or spacing

### Domain-Driven Design Analysis

**Ubiquitous Language**
- [ ] Verify business terminology used in code
- [ ] Check for technical jargon where business terms should be
- [ ] Look for inconsistent naming of domain concepts
- [ ] Identify translation layers between business and code
- [ ] Example violations:
  - Business calls it "Reservation" but code uses "Booking"
  - Domain concepts named with generic terms (Manager, Handler, Processor)

**Bounded Contexts**
- [ ] Identify logical domain boundaries
- [ ] Check for clearly separated contexts
- [ ] Look for context mixing (same concept different meanings)
- [ ] Verify anti-corruption layers between contexts
- [ ] Example issues:
  - "Customer" meaning different things without separation
  - Shared models across different business domains
  - Missing translation between contexts

**Tactical Patterns Usage**
- [ ] Identify Entities vs Value Objects usage
- [ ] Check for proper Aggregate boundaries
- [ ] Verify Aggregate Root enforcement
- [ ] Look for Domain Events capturing business occurrences
- [ ] Analyze Repository abstraction quality
- [ ] Example issues:
  - Everything modeled as Entity (no Value Objects)
  - Missing Aggregate boundaries (direct access to internals)
  - Anemic domain model (all logic in services)

**Domain Services**
- [ ] Check for stateless domain operations
- [ ] Verify services contain domain logic, not just orchestration
- [ ] Look for services that should be entity methods
- [ ] Identify infrastructure concerns in domain services
- [ ] Example violations:
  - Domain services with database dependencies
  - Services with getter/setter only (should be value objects)

**Anemic Domain Model Detection**
- [ ] Identify entities with only getters/setters
- [ ] Check for business logic in service layer instead of domain
- [ ] Look for validation outside domain objects
- [ ] Verify invariant enforcement in aggregates
- [ ] Example violations:
  - All business rules in application services
  - Domain objects as data containers only
  - Public setters allowing invalid state

### Design Patterns Analysis

**Pattern Recognition**
- [ ] Identify existing pattern implementations
- [ ] Check for correct pattern application
- [ ] Look for pattern misuse or over-engineering
- [ ] Verify patterns solve actual problems
- [ ] Common patterns to identify:
  - Factory/Factory Method for object creation
  - Repository for data access abstraction
  - Strategy for algorithm variation
  - Observer for event handling
  - Adapter for interface translation
  - Facade for subsystem simplification

**Pattern Opportunities**
- [ ] Identify code that would benefit from patterns
- [ ] Look for duplicated object creation logic (need Factory)
- [ ] Find complex conditional logic (need Strategy)
- [ ] Check for tight coupling to implementations (need Adapter/Facade)
- [ ] Verify proper abstraction of concerns

---

## Phase 3: Coupling and Dependency Analysis

### Types of Coupling to Identify

**Tight Coupling Indicators**
- [ ] Direct class instantiation (new keyword)
- [ ] Static method calls
- [ ] Concrete class dependencies instead of interfaces
- [ ] Framework types in domain code
- [ ] Circular dependencies

**Coupling Metrics**
- [ ] Afferent coupling (Ca): Incoming dependencies
- [ ] Efferent coupling (Ce): Outgoing dependencies
- [ ] Instability (I = Ce / (Ca + Ce)): 0=stable, 1=unstable
- [ ] Distance from main sequence

**Dependency Analysis**
- [ ] Create dependency graph of key modules
- [ ] Identify coupling hotspots (highly coupled modules)
- [ ] Find circular dependencies
- [ ] Check dependency direction (should point toward stable abstractions)

### Cohesion Analysis

**High Cohesion Indicators** (Good)
- [ ] Methods use most instance variables
- [ ] All methods support single responsibility
- [ ] Clear focused purpose
- [ ] Related functionality grouped

**Low Cohesion Indicators** (Bad)
- [ ] Methods using different subsets of variables
- [ ] Unrelated functionality in single class
- [ ] "Utility" classes with disparate methods
- [ ] Large classes doing many things

---

## Phase 4: Architecture Review Report

### Report Structure

Generate a comprehensive report with the following sections:

#### 1. Executive Summary
- Overall architecture quality score (1-10)
- Key strengths identified
- Critical issues requiring immediate attention
- Recommended priority for improvements

#### 2. Principle Adherence Analysis

**SOLID Principles** (Score each 1-10)
- **SRP Score**: X/10
  - Violations found: [count]
  - Example violations: [file:line references]
  - Impact: [description]
  - Recommendations: [specific improvements]

- **OCP Score**: X/10
  - Areas requiring modification for extension: [list]
  - Example violations: [file:line references]
  - Impact: [description]
  - Recommendations: [specific improvements]

- **LSP Score**: X/10
  - Inheritance issues found: [list]
  - Example violations: [file:line references]
  - Impact: [description]
  - Recommendations: [specific improvements]

- **ISP Score**: X/10
  - Fat interfaces found: [count]
  - Example violations: [file:line references]
  - Impact: [description]
  - Recommendations: [specific improvements]

- **DIP Score**: X/10
  - Concrete dependencies found: [count]
  - Example violations: [file:line references]
  - Impact: [description]
  - Recommendations: [specific improvements]

**Clean Architecture** (Score each 1-10)
- **Layer Separation**: X/10
  - Dependency violations: [list with file:line]
  - Leaky abstractions: [list]
  - Recommendations: [specific improvements]

- **Testability**: X/10
  - Hard-to-test areas: [list]
  - Framework dependencies in domain: [count]
  - Recommendations: [specific improvements]

**Clean Code** (Score each 1-10)
- **Naming Quality**: X/10
  - Unclear names found: [count]
  - Recommendations: [specific improvements]

- **Function Quality**: X/10
  - Long functions (>20 lines): [count]
  - High parameter counts: [list]
  - Recommendations: [specific improvements]

- **Code Organization**: X/10
  - Organizational issues: [list]
  - Recommendations: [specific improvements]

**Domain-Driven Design** (Score each 1-10)
- **Ubiquitous Language**: X/10
  - Terminology mismatches: [list]
  - Recommendations: [specific improvements]

- **Bounded Contexts**: X/10
  - Context boundary issues: [list]
  - Recommendations: [specific improvements]

- **Tactical Patterns**: X/10
  - Anemic domain model indicators: [yes/no with evidence]
  - Missing patterns: [list]
  - Recommendations: [specific improvements]

**Design Patterns** (Score 1-10)
- **Pattern Usage**: X/10
  - Patterns found: [list with purpose]
  - Pattern misuse: [list with issues]
  - Missing pattern opportunities: [list]
  - Recommendations: [specific improvements]

#### 3. Coupling and Cohesion Analysis

**Coupling Issues**
- Highly coupled modules: [list with coupling metrics]
- Circular dependencies: [list]
- Framework coupling in domain: [list with file:line]
- Recommendations: [specific decoupling strategies]

**Cohesion Issues**
- Low cohesion classes: [list with descriptions]
- "God classes": [list with line counts]
- Recommendations: [specific improvements]

#### 4. Critical Issues (Priority Ranking)

**P0 - Critical** (Fix Immediately)
1. [Issue description with file:line]
   - **Impact**: [business/technical impact]
   - **Root Cause**: [explanation]
   - **Recommendation**: [specific fix with code-refactoring agent usage]

**P1 - High Priority** (Fix This Sprint)
1. [Issue description with file:line]
   - **Impact**: [business/technical impact]
   - **Root Cause**: [explanation]
   - **Recommendation**: [specific fix]

**P2 - Medium Priority** (Plan for Next Sprint)
1. [Issue description with file:line]
   - **Impact**: [business/technical impact]
   - **Root Cause**: [explanation]
   - **Recommendation**: [specific fix]

**P3 - Low Priority** (Technical Debt Backlog)
1. [Issue description with file:line]
   - **Impact**: [business/technical impact]
   - **Root Cause**: [explanation]
   - **Recommendation**: [specific fix]

#### 5. Refactoring Recommendations

For each major issue, provide:

**Refactoring Plan**:
1. **Current State**: [describe current implementation]
2. **Target State**: [describe desired implementation]
3. **Refactoring Steps**:
   - Step 1: [specific action]
   - Step 2: [specific action]
   - Step 3: [specific action]
4. **Agent Usage**: [which agent to use - code-refactoring, Explore, etc.]
5. **Testing Strategy**: [how to verify refactoring]
6. **Risk Assessment**: [what could go wrong]

#### 6. Architecture Improvement Roadmap

**Short Term (1-2 Sprints)**
- [ ] Priority 0 and 1 issues
- [ ] Quick wins with high impact
- [ ] Establish architectural standards

**Medium Term (3-6 Sprints)**
- [ ] Priority 2 issues
- [ ] Introduce missing patterns
- [ ] Improve layer separation
- [ ] Refactor high-coupling areas

**Long Term (6+ Sprints)**
- [ ] Priority 3 issues
- [ ] Comprehensive refactoring
- [ ] Architecture documentation
- [ ] Team training and knowledge sharing

#### 7. Positive Patterns and Strengths

Document what the codebase does well:
- Well-implemented patterns: [list with examples]
- Good abstractions: [list with examples]
- Strong separation of concerns: [list with examples]
- High-quality code areas: [list with file references]

These should be protected and used as examples for improvements.

---

## Phase 5: Actionable Implementation Plan

### Using Agents for Improvements

**For Structural Refactoring**: Use `code-refactoring` agent
```
# Example: Extract interface for dependency inversion
Use code-refactoring agent to extract interface from concrete class
and update all dependencies to use the abstraction
```

**For Understanding Impact**: Use `Explore` agent
```
# Example: Find all usages before refactoring
Use Explore agent to find all usages of a class before
extracting functionality or changing interfaces
```

**For Research**: Use `knowledge-synthesis` agent
```
# Example: Research pattern implementation
Use knowledge-synthesis agent to research best practices
for implementing Repository pattern in [your framework]
```

### Creating Follow-Up Tickets

For each P0-P2 issue, create tickets with:
- **Title**: Clear, actionable description
- **Description**: Issue explanation, current state, target state
- **Acceptance Criteria**: How to verify fix
- **References**: File:line references, related tickets
- **Effort Estimate**: Based on complexity and scope
- **Priority**: Based on impact and risk

---

## Review Execution Strategy

### Step 1: Automated Discovery (15-20% of effort)
Launch Explore agent with systematic queries to map architecture

### Step 2: Principle Analysis (40-50% of effort)
Deep analysis of each principle with concrete examples and metrics

### Step 3: Report Generation (20-30% of effort)
Comprehensive report with scores, examples, and recommendations

### Step 4: Actionable Planning (10-20% of effort)
Prioritized roadmap with agent usage and ticket creation

---

## Success Criteria

- ✅ Complete mapping of architectural layers and dependencies
- ✅ Scored assessment of each principle (SOLID, Clean Architecture, etc.)
- ✅ Concrete examples for each violation (file:line references)
- ✅ Prioritized list of issues (P0-P3)
- ✅ Actionable refactoring plans with specific steps
- ✅ Agent usage guidance for each improvement
- ✅ Short/medium/long-term roadmap
- ✅ Documentation of architectural strengths to preserve

---

## Usage Examples

```bash
# Review entire codebase
/quality:architecture-review

# Review specific module/package
/quality:architecture-review src/main/java/com/example/payments

# Review with focus on specific principle
/quality:architecture-review --focus=solid

# Review with emphasis on coupling
/quality:architecture-review --focus=coupling
```

---

## Anti-Patterns to Watch For

### Over-Engineering
- ✅ Recommend patterns only when justified by complexity
- ✅ Don't force DDD on simple CRUD operations
- ✅ Consider project context and constraints

### Perfectionism
- ✅ Prioritize based on actual impact, not theoretical purity
- ✅ Accept pragmatic trade-offs when appropriate
- ✅ Focus on high-value improvements first

### Analysis Paralysis
- ✅ Provide concrete, actionable recommendations
- ✅ Break large refactorings into incremental steps
- ✅ Balance thoroughness with practicality

---

## Integration with Development Workflow

**During Sprint Planning**:
- Review P0-P1 issues and plan fixes
- Allocate time for architectural improvements (20% of capacity)
- Include architecture tickets in sprint backlog

**During Development**:
- Apply findings to new code
- Use review as reference for design decisions
- Follow refactoring recommendations incrementally

**During Code Review**:
- Reference architecture review findings
- Ensure new code doesn't repeat identified anti-patterns
- Validate improvements align with recommendations

**During Retrospectives**:
- Track progress on architecture improvements
- Measure impact of refactoring efforts
- Adjust priorities based on learnings

---

## Related Commands

- `/code:implement` - Implement features following best practices
- `/fix-failures` - Systematically fix test and linter failures
- `/quality:refactor-code` - Refactor specific code using established principles

---

**Remember**: Architecture reviews are most valuable when they lead to concrete improvements. Focus on actionable recommendations that balance ideal design with pragmatic constraints. Use agents strategically to accelerate implementation of architectural improvements.
