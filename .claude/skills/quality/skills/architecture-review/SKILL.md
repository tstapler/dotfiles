---
description: Comprehensive architecture review analyzing SOLID, Clean Architecture,
  Clean Code, DDD, and Design Patterns adherence with actionable recommendations
prompt: "# Architecture Review: Context-Aware Analysis\n\nPerform targeted or comprehensive\
  \ architecture reviews with automatic context detection and configurable depth.\
  \ The review adapts to your current workflow - whether you're doing a quick PR review,\
  \ analyzing a specific component, or conducting a full architectural assessment.\n\
  \n## Smart Context Detection\n\nThe command automatically detects and uses context\
  \ when no explicit parameters are provided:\n\n### Auto-Detection Logic\n\nWhen\
  \ invoked without explicit parameters, the review intelligently determines:\n1.\
  \ **Scope**: What code to analyze (current file, changes, or full codebase)\n2.\
  \ **Depth**: How thorough the analysis should be (quick, standard, or deep)\n3.\
  \ **Principles**: Which architectural principles are most relevant\n4. **Format**:\
  \ The most appropriate output format for the situation\n\n### Context Detection\
  \ Rules\n\n#### Current File Context (`--context=current`)\n- Triggered when a file\
  \ is open in the editor\n- Analyzes the current class/module and its immediate dependencies\n\
  - Automatically sets `--depth=quick` for single files\n- Focuses on principles relevant\
  \ to the file type\n\n#### Git Changes Context (`--context=changes`)\n- Triggered\
  \ when uncommitted changes exist\n- Reviews modified files and their architectural\
  \ impact\n- Sets `--depth=standard` for change sets\n- Emphasizes regression prevention\
  \ and maintaining standards\n\n#### Recent Activity Context (`--context=recent`)\n\
  - Reviews commits from current branch\n- Useful for pre-PR comprehensive review\n\
  - Sets `--depth=standard` or `deep` based on change volume\n- Focus on architectural\
  \ consistency\n\n#### Full Context (`--context=all`)\n- Complete codebase analysis\n\
  - Sets `--depth=deep` for thorough review\n- Comprehensive principle evaluation\n\
  \n## Targeted Component Analysis\n\n### Component Targeting Syntax\n\n```bash\n\
  # Class-level analysis\n--target=class:ServiceCorrelationService\n\n# Package/namespace\
  \ analysis\n--target=package:bet.fanatics.scorecards.service\n\n# Module analysis\n\
  --target=module:scorecards-core\n\n# Layer analysis\n--target=layer:domain\n--target=layer:infrastructure\n\
  --target=layer:application\n\n# Pattern-based targeting\n--target=pattern:*Repository\
  \  # All repositories\n--target=pattern:*Controller  # All controllers\n--target=pattern:*Service\
  \     # All services\n```\n\n### Target Resolution Strategy\n\n**Class Target**:\
  \ Analyzes the class, its dependencies, interfaces, coupling, and single responsibility\n\
  **Package Target**: Reviews all classes, package cohesion, inter-package dependencies,\
  \ bounded contexts\n**Module Target**: Reviews module boundaries, public APIs, dependencies,\
  \ separation of concerns\n**Layer Target**: Reviews layer compliance, dependency\
  \ directions, clean architecture rules\n\n## Analysis Depth Configuration\n\n###\
  \ Quick Assessment (`--depth=quick`)\n**Duration**: 5-10 minutes | **Use Cases**:\
  \ PR reviews, spot checks, pre-commit validation\n\n- Targets component only with\
  \ direct dependencies\n- Identifies obvious violations and critical issues (P0-P1)\n\
  - Provides violation counts and top 3-5 issues\n- Quick fixes and pass/fail recommendation\n\
  \n### Standard Review (`--depth=standard`)\n**Duration**: 15-30 minutes | **Use\
  \ Cases**: Feature completion, sprint reviews, module refactoring\n\n- Targets and\
  \ related components with transitive dependencies\n- Identifies common violations\
  \ and P0-P2 issues\n- Provides scored assessment (1-10) with categorized issues\n\
  - Refactoring suggestions and priority recommendations\n\n### Deep Analysis (`--depth=deep`)\n\
  **Duration**: 30-60+ minutes | **Use Cases**: Architecture reviews, technical debt\
  \ assessment\n\n- Complete dependency graph analysis\n- All architectural layers\
  \ and comprehensive metrics\n- All priority issues with detailed scoring\n- Complete\
  \ refactoring roadmap and documentation\n\n## Principle-Focused Reviews\n\n### Selective\
  \ Principle Analysis\n\n```bash\n# Single principle focus\n--principles=srp    \
  \                # Single Responsibility only\n--principles=dip,isp            \
  \   # Dependency Inversion + Interface Segregation\n--principles=clean-arch,clean-code\
  \  # Architecture and code quality\n--principles=all                    # Comprehensive\
  \ analysis\n```\n\n### Principle Shortcuts\n\n- `srp`: Single Responsibility Principle\n\
  - `ocp`: Open/Closed Principle\n- `lsp`: Liskov Substitution Principle\n- `isp`:\
  \ Interface Segregation Principle\n- `dip`: Dependency Inversion Principle\n- `clean-arch`:\
  \ Clean Architecture layers and boundaries\n- `clean-code`: Naming, functions, organization,\
  \ error handling\n- `ddd`: Domain-Driven Design patterns and boundaries\n- `patterns`:\
  \ Design pattern usage and opportunities\n- `coupling`: Coupling and cohesion analysis\n\
  \n## Output Format Options\n\n### Summary Format (`--format=summary`)\nConcise overview\
  \ with score, critical issues, and quick wins. Ideal for quick assessments.\n\n\
  ### PR Review Format (`--format=pr-review`)\nStructured feedback for pull requests\
  \ with approval status, good practices, and suggestions.\n\n### Actionable Format\
  \ (`--format=actionable`)\nStep-by-step refactoring plans with specific commands\
  \ and agent usage instructions.\n\n### Detailed Format (`--format=detailed`)\nComprehensive\
  \ analysis with examples, metrics, and in-depth recommendations (default for deep\
  \ analysis).\n\n### Report Format (`--format=report`)\nExecutive-friendly format\
  \ with visualizations, trends, and strategic recommendations.\n\n## Enhanced Usage\
  \ Examples\n\n### Context-Aware Quick Reviews\n```bash\n# Auto-detect context and\
  \ scope\n/quality:architecture-review\n\n# Quick review of current file\n/quality:architecture-review\
  \ --context=current\n\n# PR review of changes\n/quality:architecture-review --context=changes\
  \ --format=pr-review\n```\n\n### Targeted Analysis\n```bash\n# Review specific class\
  \ for SOLID violations\n/quality:architecture-review --target=class:UserService\
  \ --principles=srp,ocp,lsp,isp,dip\n\n# Deep coupling analysis of a module\n/quality:architecture-review\
  \ --target=module:core --principles=coupling --depth=deep\n\n# DDD review of domain\
  \ layer\n/quality:architecture-review --target=layer:domain --principles=ddd\n```\n\
  \n### Workflow Integration\n```bash\n# Pre-commit check\n/quality:architecture-review\
  \ --context=changes --depth=quick --format=summary\n\n# Sprint review\n/quality:architecture-review\
  \ --context=recent --depth=standard --format=actionable\n\n# Technical debt assessment\n\
  /quality:architecture-review --depth=deep --format=report\n```\n\n## Backward Compatibility\n\
  \nThe command maintains full backward compatibility:\n- Basic invocation (`/quality:architecture-review`)\
  \ works identically\n- Path arguments are still supported\n- `--focus` flag is mapped\
  \ to `--principles` for legacy support\n- Default behavior preserved when no options\
  \ specified\n\n---\n\n## Review Framework\n\nThis review is grounded in authoritative\
  \ software engineering principles:\n\n### 1. **SOLID Principles**\n- **Single Responsibility\
  \ Principle (SRP)**: Classes have one reason to change\n- **Open/Closed Principle\
  \ (OCP)**: Open for extension, closed for modification\n- **Liskov Substitution\
  \ Principle (LSP)**: Subtypes replaceable with base types\n- **Interface Segregation\
  \ Principle (ISP)**: No client forced to depend on unused methods\n- **Dependency\
  \ Inversion Principle (DIP)**: Depend on abstractions, not concretions\n\n### 2.\
  \ **Clean Architecture Layers**\n- **Entities Layer**: Enterprise-wide business\
  \ rules\n- **Use Cases Layer**: Application-specific business rules\n- **Interface\
  \ Adapters Layer**: Controllers, presenters, gateways\n- **Frameworks and Drivers\
  \ Layer**: External tools and frameworks\n- **Dependency Rule**: Dependencies point\
  \ inward toward business logic\n\n### 3. **Clean Code Principles**\n- **Meaningful\
  \ Names**: Intention-revealing, searchable, pronounceable\n- **Functions**: Small,\
  \ single responsibility, few arguments\n- **Comments**: Explain \"why\" not \"what\"\
  , avoid redundancy\n- **Error Handling**: Use exceptions, informative messages,\
  \ don't return null\n- **Classes**: Small, high cohesion, maintain encapsulation\n\
  \n### 4. **Domain-Driven Design**\n- **Ubiquitous Language**: Shared vocabulary\
  \ in code\n- **Bounded Contexts**: Explicit boundaries for domain models\n- **Entities**:\
  \ Identity-based domain objects\n- **Value Objects**: Attribute-based immutable\
  \ objects\n- **Aggregates**: Transaction and consistency boundaries\n- **Domain\
  \ Events**: Business-significant occurrences\n- **Repositories**: Collection-like\
  \ access to aggregates\n\n### 5. **Design Patterns**\n- **Creational**: Factory,\
  \ Singleton, Builder\n- **Structural**: Adapter, Facade, Decorator\n- **Behavioral**:\
  \ Strategy, Observer, Command\n\n---\n\n## Phase 1: Discovery and Mapping (Using\
  \ Explore Agent)\n\nUse the **Explore agent** to systematically discover and map\
  \ the architecture:\n\n### Codebase Exploration Tasks\n\n1. **Identify Project Structure**:\n\
  \   - Find main source directories and package organization\n   - Identify framework\
  \ and technology choices\n   - Discover configuration and dependency management\n\
  \   - Map test structure and coverage\n\n2. **Discover Domain Boundaries**:\n  \
  \ - Search for domain models and entities\n   - Identify services and use cases\n\
  \   - Find repositories and data access patterns\n   - Locate infrastructure and\
  \ framework code\n\n3. **Analyze Dependencies**:\n   - Map import/dependency relationships\n\
  \   - Identify coupling between modules\n   - Find circular dependencies\n   - Discover\
  \ tight coupling to frameworks\n\n4. **Find Key Abstractions**:\n   - Locate interfaces\
  \ and abstract classes\n   - Identify design pattern implementations\n   - Find\
  \ dependency injection usage\n   - Discover architectural boundaries\n\n### Exploration\
  \ Queries\n\nLaunch the Explore agent with these queries (adjust based on language/framework):\n\
  \n```\n# Project structure and organization\n\"What is the overall project structure\
  \ and how is code organized?\"\n\n# Domain model discovery\n\"Find all domain entities,\
  \ value objects, and aggregates\"\n\n# Dependency analysis\n\"Analyze coupling between\
  \ packages/modules and identify tight coupling\"\n\n# Interface and abstraction\
  \ usage\n\"Find all interfaces and analyze dependency inversion usage\"\n\n# Design\
  \ pattern usage\n\"Identify design pattern implementations (Factory, Strategy, Repository,\
  \ etc.)\"\n\n# Testing architecture\n\"Analyze test structure and how tests are\
  \ organized relative to production code\"\n```\n\n---\n\n## Phase 2: Principle-by-Principle\
  \ Analysis\n\n### SOLID Principles Analysis\n\n**Single Responsibility Principle\
  \ (SRP)**\n- [ ] Identify classes with multiple responsibilities\n- [ ] Look for\
  \ classes that change for multiple reasons\n- [ ] Check for \"God classes\" (>500\
  \ lines, many methods)\n- [ ] Verify each class has clear, focused purpose\n- [\
  \ ] Example violations:\n  - Classes mixing business logic with persistence\n  -\
  \ Controllers handling validation, business rules, and presentation\n  - Services\
  \ doing too many unrelated tasks\n\n**Open/Closed Principle (OCP)**\n- [ ] Find\
  \ code requiring modification for extensions\n- [ ] Check for long if/else or switch\
  \ statements on types\n- [ ] Verify use of polymorphism for behavior variation\n\
  - [ ] Look for hardcoded dependencies that prevent extension\n- [ ] Example violations:\n\
  \  - Switch statements on enum/type that require modification\n  - Classes that\
  \ can't be extended without modifying source\n\n**Liskov Substitution Principle\
  \ (LSP)**\n- [ ] Verify subtypes can replace base types\n- [ ] Check for override\
  \ methods that change expected behavior\n- [ ] Look for precondition strengthening\
  \ or postcondition weakening\n- [ ] Identify inheritance misuse (using inheritance\
  \ for code reuse only)\n- [ ] Example violations:\n  - Subclasses throwing unexpected\
  \ exceptions\n  - Overridden methods with stricter preconditions\n\n**Interface\
  \ Segregation Principle (ISP)**\n- [ ] Find \"fat\" interfaces with many methods\n\
  - [ ] Check for clients depending on unused methods\n- [ ] Verify interfaces are\
  \ client-specific, not general-purpose\n- [ ] Look for interfaces forcing empty\
  \ implementations\n- [ ] Example violations:\n  - Large interfaces with 10+ methods\n\
  \  - Implementations with many no-op methods\n\n**Dependency Inversion Principle\
  \ (DIP)**\n- [ ] Check high-level modules depending on low-level modules\n- [ ]\
  \ Verify dependencies on abstractions (interfaces) not concretions\n- [ ] Look for\
  \ new keyword creating concrete dependencies\n- [ ] Check for proper dependency\
  \ injection usage\n- [ ] Example violations:\n  - Business logic directly instantiating\
  \ database implementations\n  - Controllers creating service instances directly\n\
  \n### Clean Architecture Analysis\n\n**Layer Separation and Dependency Rule**\n\
  - [ ] Map code to architectural layers (Entities, Use Cases, Adapters, Frameworks)\n\
  - [ ] Verify dependencies only point inward\n- [ ] Check for business logic free\
  \ of framework dependencies\n- [ ] Identify leaky abstractions between layers\n\
  - [ ] Example violations:\n  - Domain entities depending on ORM annotations\n  -\
  \ Use cases importing web framework types\n  - Business logic coupled to database\
  \ implementation\n\n**Boundary Crossings**\n- [ ] Verify proper use of interfaces\
  \ at boundaries\n- [ ] Check data structures crossing boundaries (DTOs)\n- [ ] Look\
  \ for framework types leaking into domain\n- [ ] Identify proper adapter usage\n\
  - [ ] Example violations:\n  - HTTP request/response objects in domain layer\n \
  \ - Database entities used as domain models\n  - Framework exceptions propagating\
  \ to business logic\n\n**Testability**\n- [ ] Verify business rules testable without\
  \ frameworks\n- [ ] Check for mocking capabilities at boundaries\n- [ ] Look for\
  \ dependency injection enabling test doubles\n- [ ] Identify hard-to-test code due\
  \ to tight coupling\n- [ ] Example issues:\n  - Business logic requiring database\
  \ for testing\n  - Use cases needing web server to test\n  - Static dependencies\
  \ preventing mocking\n\n### Clean Code Analysis\n\n**Naming Quality**\n- [ ] Check\
  \ for intention-revealing names\n- [ ] Identify abbreviations and unclear names\n\
  - [ ] Look for inconsistent naming conventions\n- [ ] Verify domain language used\
  \ in code\n- [ ] Example violations:\n  - `processData()`, `doStuff()`, `handle()`\n\
  \  - Single-letter variables (except loop counters)\n  - Inconsistent naming (getUser\
  \ vs fetchUser vs retrieveUser)\n\n**Function Quality**\n- [ ] Identify long functions\
  \ (>20 lines)\n- [ ] Check for functions doing multiple things\n- [ ] Look for functions\
  \ with many parameters (>3)\n- [ ] Verify functions at single abstraction level\n\
  - [ ] Example violations:\n  - Functions with mixed abstraction (high and low level)\n\
  \  - Functions with side effects not indicated by name\n  - Functions both querying\
  \ and mutating state\n\n**Comment Quality**\n- [ ] Identify redundant comments (explaining\
  \ obvious code)\n- [ ] Look for outdated or misleading comments\n- [ ] Check if\
  \ comments indicate code smell (needs refactoring)\n- [ ] Verify meaningful comments\
  \ explain \"why\" not \"what\"\n- [ ] Example issues:\n  - `// increment counter`\
  \ above `counter++;`\n  - Commented-out code blocks\n  - TODOs without tickets or\
  \ timelines\n\n**Error Handling**\n- [ ] Check for proper exception usage\n- [ ]\
  \ Look for null returns/checks that could use Optional\n- [ ] Verify informative\
  \ error messages\n- [ ] Identify swallowed exceptions (empty catch blocks)\n- [\
  \ ] Example violations:\n  - Returning null instead of Optional or empty collections\n\
  \  - Generic exception messages without context\n  - Catch-all exception handlers\n\
  \n**Code Organization**\n- [ ] Check for logical grouping within classes\n- [ ]\
  \ Verify vertical ordering (public → private)\n- [ ] Look for mixed concerns in\
  \ single file\n- [ ] Identify inconsistent formatting\n- [ ] Example issues:\n \
  \ - Private methods at top, public at bottom\n  - Related functionality scattered\
  \ across file\n  - Inconsistent indentation or spacing\n\n### Domain-Driven Design\
  \ Analysis\n\n**Ubiquitous Language**\n- [ ] Verify business terminology used in\
  \ code\n- [ ] Check for technical jargon where business terms should be\n- [ ] Look\
  \ for inconsistent naming of domain concepts\n- [ ] Identify translation layers\
  \ between business and code\n- [ ] Example violations:\n  - Business calls it \"\
  Reservation\" but code uses \"Booking\"\n  - Domain concepts named with generic\
  \ terms (Manager, Handler, Processor)\n\n**Bounded Contexts**\n- [ ] Identify logical\
  \ domain boundaries\n- [ ] Check for clearly separated contexts\n- [ ] Look for\
  \ context mixing (same concept different meanings)\n- [ ] Verify anti-corruption\
  \ layers between contexts\n- [ ] Example issues:\n  - \"Customer\" meaning different\
  \ things without separation\n  - Shared models across different business domains\n\
  \  - Missing translation between contexts\n\n**Tactical Patterns Usage**\n- [ ]\
  \ Identify Entities vs Value Objects usage\n- [ ] Check for proper Aggregate boundaries\n\
  - [ ] Verify Aggregate Root enforcement\n- [ ] Look for Domain Events capturing\
  \ business occurrences\n- [ ] Analyze Repository abstraction quality\n- [ ] Example\
  \ issues:\n  - Everything modeled as Entity (no Value Objects)\n  - Missing Aggregate\
  \ boundaries (direct access to internals)\n  - Anemic domain model (all logic in\
  \ services)\n\n**Domain Services**\n- [ ] Check for stateless domain operations\n\
  - [ ] Verify services contain domain logic, not just orchestration\n- [ ] Look for\
  \ services that should be entity methods\n- [ ] Identify infrastructure concerns\
  \ in domain services\n- [ ] Example violations:\n  - Domain services with database\
  \ dependencies\n  - Services with getter/setter only (should be value objects)\n\
  \n**Anemic Domain Model Detection**\n- [ ] Identify entities with only getters/setters\n\
  - [ ] Check for business logic in service layer instead of domain\n- [ ] Look for\
  \ validation outside domain objects\n- [ ] Verify invariant enforcement in aggregates\n\
  - [ ] Example violations:\n  - All business rules in application services\n  - Domain\
  \ objects as data containers only\n  - Public setters allowing invalid state\n\n\
  ### Design Patterns Analysis\n\n**Pattern Recognition**\n- [ ] Identify existing\
  \ pattern implementations\n- [ ] Check for correct pattern application\n- [ ] Look\
  \ for pattern misuse or over-engineering\n- [ ] Verify patterns solve actual problems\n\
  - [ ] Common patterns to identify:\n  - Factory/Factory Method for object creation\n\
  \  - Repository for data access abstraction\n  - Strategy for algorithm variation\n\
  \  - Observer for event handling\n  - Adapter for interface translation\n  - Facade\
  \ for subsystem simplification\n\n**Pattern Opportunities**\n- [ ] Identify code\
  \ that would benefit from patterns\n- [ ] Look for duplicated object creation logic\
  \ (need Factory)\n- [ ] Find complex conditional logic (need Strategy)\n- [ ] Check\
  \ for tight coupling to implementations (need Adapter/Facade)\n- [ ] Verify proper\
  \ abstraction of concerns\n\n---\n\n## Phase 3: Coupling and Dependency Analysis\n\
  \n### Types of Coupling to Identify\n\n**Tight Coupling Indicators**\n- [ ] Direct\
  \ class instantiation (new keyword)\n- [ ] Static method calls\n- [ ] Concrete class\
  \ dependencies instead of interfaces\n- [ ] Framework types in domain code\n- [\
  \ ] Circular dependencies\n\n**Coupling Metrics**\n- [ ] Afferent coupling (Ca):\
  \ Incoming dependencies\n- [ ] Efferent coupling (Ce): Outgoing dependencies\n-\
  \ [ ] Instability (I = Ce / (Ca + Ce)): 0=stable, 1=unstable\n- [ ] Distance from\
  \ main sequence\n\n**Dependency Analysis**\n- [ ] Create dependency graph of key\
  \ modules\n- [ ] Identify coupling hotspots (highly coupled modules)\n- [ ] Find\
  \ circular dependencies\n- [ ] Check dependency direction (should point toward stable\
  \ abstractions)\n\n### Cohesion Analysis\n\n**High Cohesion Indicators** (Good)\n\
  - [ ] Methods use most instance variables\n- [ ] All methods support single responsibility\n\
  - [ ] Clear focused purpose\n- [ ] Related functionality grouped\n\n**Low Cohesion\
  \ Indicators** (Bad)\n- [ ] Methods using different subsets of variables\n- [ ]\
  \ Unrelated functionality in single class\n- [ ] \"Utility\" classes with disparate\
  \ methods\n- [ ] Large classes doing many things\n\n---\n\n## Phase 4: Architecture\
  \ Review Report\n\n### Report Structure\n\nGenerate a comprehensive report with\
  \ the following sections:\n\n#### 1. Executive Summary\n- Overall architecture quality\
  \ score (1-10)\n- Key strengths identified\n- Critical issues requiring immediate\
  \ attention\n- Recommended priority for improvements\n\n#### 2. Principle Adherence\
  \ Analysis\n\n**SOLID Principles** (Score each 1-10)\n- **SRP Score**: X/10\n  -\
  \ Violations found: [count]\n  - Example violations: [file:line references]\n  -\
  \ Impact: [description]\n  - Recommendations: [specific improvements]\n\n- **OCP\
  \ Score**: X/10\n  - Areas requiring modification for extension: [list]\n  - Example\
  \ violations: [file:line references]\n  - Impact: [description]\n  - Recommendations:\
  \ [specific improvements]\n\n- **LSP Score**: X/10\n  - Inheritance issues found:\
  \ [list]\n  - Example violations: [file:line references]\n  - Impact: [description]\n\
  \  - Recommendations: [specific improvements]\n\n- **ISP Score**: X/10\n  - Fat\
  \ interfaces found: [count]\n  - Example violations: [file:line references]\n  -\
  \ Impact: [description]\n  - Recommendations: [specific improvements]\n\n- **DIP\
  \ Score**: X/10\n  - Concrete dependencies found: [count]\n  - Example violations:\
  \ [file:line references]\n  - Impact: [description]\n  - Recommendations: [specific\
  \ improvements]\n\n**Clean Architecture** (Score each 1-10)\n- **Layer Separation**:\
  \ X/10\n  - Dependency violations: [list with file:line]\n  - Leaky abstractions:\
  \ [list]\n  - Recommendations: [specific improvements]\n\n- **Testability**: X/10\n\
  \  - Hard-to-test areas: [list]\n  - Framework dependencies in domain: [count]\n\
  \  - Recommendations: [specific improvements]\n\n**Clean Code** (Score each 1-10)\n\
  - **Naming Quality**: X/10\n  - Unclear names found: [count]\n  - Recommendations:\
  \ [specific improvements]\n\n- **Function Quality**: X/10\n  - Long functions (>20\
  \ lines): [count]\n  - High parameter counts: [list]\n  - Recommendations: [specific\
  \ improvements]\n\n- **Code Organization**: X/10\n  - Organizational issues: [list]\n\
  \  - Recommendations: [specific improvements]\n\n**Domain-Driven Design** (Score\
  \ each 1-10)\n- **Ubiquitous Language**: X/10\n  - Terminology mismatches: [list]\n\
  \  - Recommendations: [specific improvements]\n\n- **Bounded Contexts**: X/10\n\
  \  - Context boundary issues: [list]\n  - Recommendations: [specific improvements]\n\
  \n- **Tactical Patterns**: X/10\n  - Anemic domain model indicators: [yes/no with\
  \ evidence]\n  - Missing patterns: [list]\n  - Recommendations: [specific improvements]\n\
  \n**Design Patterns** (Score 1-10)\n- **Pattern Usage**: X/10\n  - Patterns found:\
  \ [list with purpose]\n  - Pattern misuse: [list with issues]\n  - Missing pattern\
  \ opportunities: [list]\n  - Recommendations: [specific improvements]\n\n#### 3.\
  \ Coupling and Cohesion Analysis\n\n**Coupling Issues**\n- Highly coupled modules:\
  \ [list with coupling metrics]\n- Circular dependencies: [list]\n- Framework coupling\
  \ in domain: [list with file:line]\n- Recommendations: [specific decoupling strategies]\n\
  \n**Cohesion Issues**\n- Low cohesion classes: [list with descriptions]\n- \"God\
  \ classes\": [list with line counts]\n- Recommendations: [specific improvements]\n\
  \n#### 4. Critical Issues (Priority Ranking)\n\n**P0 - Critical** (Fix Immediately)\n\
  1. [Issue description with file:line]\n   - **Impact**: [business/technical impact]\n\
  \   - **Root Cause**: [explanation]\n   - **Recommendation**: [specific fix with\
  \ code-refactoring agent usage]\n\n**P1 - High Priority** (Fix This Sprint)\n1.\
  \ [Issue description with file:line]\n   - **Impact**: [business/technical impact]\n\
  \   - **Root Cause**: [explanation]\n   - **Recommendation**: [specific fix]\n\n\
  **P2 - Medium Priority** (Plan for Next Sprint)\n1. [Issue description with file:line]\n\
  \   - **Impact**: [business/technical impact]\n   - **Root Cause**: [explanation]\n\
  \   - **Recommendation**: [specific fix]\n\n**P3 - Low Priority** (Technical Debt\
  \ Backlog)\n1. [Issue description with file:line]\n   - **Impact**: [business/technical\
  \ impact]\n   - **Root Cause**: [explanation]\n   - **Recommendation**: [specific\
  \ fix]\n\n#### 5. Refactoring Recommendations\n\nFor each major issue, provide:\n\
  \n**Refactoring Plan**:\n1. **Current State**: [describe current implementation]\n\
  2. **Target State**: [describe desired implementation]\n3. **Refactoring Steps**:\n\
  \   - Step 1: [specific action]\n   - Step 2: [specific action]\n   - Step 3: [specific\
  \ action]\n4. **Agent Usage**: [which agent to use - code-refactoring, Explore,\
  \ etc.]\n5. **Testing Strategy**: [how to verify refactoring]\n6. **Risk Assessment**:\
  \ [what could go wrong]\n\n#### 6. Architecture Improvement Roadmap\n\n**Short Term\
  \ (1-2 Sprints)**\n- [ ] Priority 0 and 1 issues\n- [ ] Quick wins with high impact\n\
  - [ ] Establish architectural standards\n\n**Medium Term (3-6 Sprints)**\n- [ ]\
  \ Priority 2 issues\n- [ ] Introduce missing patterns\n- [ ] Improve layer separation\n\
  - [ ] Refactor high-coupling areas\n\n**Long Term (6+ Sprints)**\n- [ ] Priority\
  \ 3 issues\n- [ ] Comprehensive refactoring\n- [ ] Architecture documentation\n\
  - [ ] Team training and knowledge sharing\n\n#### 7. Positive Patterns and Strengths\n\
  \nDocument what the codebase does well:\n- Well-implemented patterns: [list with\
  \ examples]\n- Good abstractions: [list with examples]\n- Strong separation of concerns:\
  \ [list with examples]\n- High-quality code areas: [list with file references]\n\
  \nThese should be protected and used as examples for improvements.\n\n---\n\n##\
  \ Phase 5: Actionable Implementation Plan\n\n### Using Agents for Improvements\n\
  \n**For Structural Refactoring**: Use `code-refactoring` agent\n```\n# Example:\
  \ Extract interface for dependency inversion\nUse code-refactoring agent to extract\
  \ interface from concrete class\nand update all dependencies to use the abstraction\n\
  ```\n\n**For Understanding Impact**: Use `Explore` agent\n```\n# Example: Find all\
  \ usages before refactoring\nUse Explore agent to find all usages of a class before\n\
  extracting functionality or changing interfaces\n```\n\n**For Research**: Use `knowledge-synthesis`\
  \ agent\n```\n# Example: Research pattern implementation\nUse knowledge-synthesis\
  \ agent to research best practices\nfor implementing Repository pattern in [your\
  \ framework]\n```\n\n### Creating Follow-Up Tickets\n\nFor each P0-P2 issue, create\
  \ tickets with:\n- **Title**: Clear, actionable description\n- **Description**:\
  \ Issue explanation, current state, target state\n- **Acceptance Criteria**: How\
  \ to verify fix\n- **References**: File:line references, related tickets\n- **Effort\
  \ Estimate**: Based on complexity and scope\n- **Priority**: Based on impact and\
  \ risk\n\n---\n\n## Review Execution Strategy\n\n### Step 1: Automated Discovery\
  \ (15-20% of effort)\nLaunch Explore agent with systematic queries to map architecture\n\
  \n### Step 2: Principle Analysis (40-50% of effort)\nDeep analysis of each principle\
  \ with concrete examples and metrics\n\n### Step 3: Report Generation (20-30% of\
  \ effort)\nComprehensive report with scores, examples, and recommendations\n\n###\
  \ Step 4: Actionable Planning (10-20% of effort)\nPrioritized roadmap with agent\
  \ usage and ticket creation\n\n---\n\n## Success Criteria\n\n- ✅ Complete mapping\
  \ of architectural layers and dependencies\n- ✅ Scored assessment of each principle\
  \ (SOLID, Clean Architecture, etc.)\n- ✅ Concrete examples for each violation (file:line\
  \ references)\n- ✅ Prioritized list of issues (P0-P3)\n- ✅ Actionable refactoring\
  \ plans with specific steps\n- ✅ Agent usage guidance for each improvement\n- ✅\
  \ Short/medium/long-term roadmap\n- ✅ Documentation of architectural strengths to\
  \ preserve\n\n---\n\n## Usage Examples\n\n```bash\n# Review entire codebase\n/quality:architecture-review\n\
  \n# Review specific module/package\n/quality:architecture-review src/main/java/com/example/payments\n\
  \n# Review with focus on specific principle\n/quality:architecture-review --focus=solid\n\
  \n# Review with emphasis on coupling\n/quality:architecture-review --focus=coupling\n\
  ```\n\n---\n\n## Anti-Patterns to Watch For\n\n### Over-Engineering\n- ✅ Recommend\
  \ patterns only when justified by complexity\n- ✅ Don't force DDD on simple CRUD\
  \ operations\n- ✅ Consider project context and constraints\n\n### Perfectionism\n\
  - ✅ Prioritize based on actual impact, not theoretical purity\n- ✅ Accept pragmatic\
  \ trade-offs when appropriate\n- ✅ Focus on high-value improvements first\n\n###\
  \ Analysis Paralysis\n- ✅ Provide concrete, actionable recommendations\n- ✅ Break\
  \ large refactorings into incremental steps\n- ✅ Balance thoroughness with practicality\n\
  \n---\n\n## Integration with Development Workflow\n\n**During Sprint Planning**:\n\
  - Review P0-P1 issues and plan fixes\n- Allocate time for architectural improvements\
  \ (20% of capacity)\n- Include architecture tickets in sprint backlog\n\n**During\
  \ Development**:\n- Apply findings to new code\n- Use review as reference for design\
  \ decisions\n- Follow refactoring recommendations incrementally\n\n**During Code\
  \ Review**:\n- Reference architecture review findings\n- Ensure new code doesn't\
  \ repeat identified anti-patterns\n- Validate improvements align with recommendations\n\
  \n**During Retrospectives**:\n- Track progress on architecture improvements\n- Measure\
  \ impact of refactoring efforts\n- Adjust priorities based on learnings\n\n---\n\
  \n## Related Commands\n\n- `/code:implement` - Implement features following best\
  \ practices\n- `/fix-failures` - Systematically fix test and linter failures\n-\
  \ `/quality:refactor-code` - Refactor specific code using established principles\n\
  \n---\n\n**Remember**: Architecture reviews are most valuable when they lead to\
  \ concrete improvements. Focus on actionable recommendations that balance ideal\
  \ design with pragmatic constraints. Use agents strategically to accelerate implementation\
  \ of architectural improvements.\n"
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
