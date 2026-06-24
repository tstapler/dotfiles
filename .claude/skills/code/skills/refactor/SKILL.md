---
description: Refactor code following principles, patterns, and best practices from
  respected literature
prompt: "# Code Refactoring Guide\n\nI'll help you refactor code by applying established\
  \ software engineering principles, design patterns, and best practices from highly\
  \ regarded literature and academic research. The refactoring will adapt the code\
  \ to follow idioms and conventions specific to $1 or the detected language if no\
  \ target language is specified.\n\n## Refactoring Process\n\n1. **Analysis Phase**\n\
  \   - Identify code smells using Martin Fowler's classification\n   - Assess current\
  \ design patterns and architectural approach\n   - Evaluate complexity using metrics\
  \ (cyclomatic complexity, coupling, cohesion)\n   - Detect potential technical debt\
  \ indicators\n\n2. **Planning Phase**\n   - Select appropriate refactoring techniques\
  \ from Fowler's catalog\n   - Identify applicable design patterns from GoF or modern\
  \ equivalents\n   - Consider enterprise patterns and domain-driven design principles\
  \ where appropriate\n   - Determine language-specific idioms and best practices\
  \ to apply\n   - Plan refactoring sequence to maintain behavior while transforming\
  \ structure\n\n3. **Implementation Phase**\n   - Apply refactoring transformations\
  \ systematically\n   - Incorporate language-specific idioms and conventions\n  \
  \ - Implement selected design patterns where appropriate\n   - Improve naming, comments,\
  \ and documentation\n\n4. **Validation Phase**\n   - Ensure behavior preservation\
  \ (suggest tests if absent)\n   - Verify adherence to SOLID principles\n   - Confirm\
  \ improved readability and maintainability\n   - Validate language-specific best\
  \ practices\n\n## Principles Applied\n\n- **SOLID Principles** (Robert C. Martin)\n\
  \  - Single Responsibility, Open-Closed, Liskov Substitution, Interface Segregation,\
  \ Dependency Inversion\n\n- **Clean Code Practices** (Robert C. Martin)\n  - Meaningful\
  \ names, small functions, DRY principle, comment purposefully\n\n- **Design Patterns**\
  \ (Gang of Four + Modern Patterns)\n  - Creational, Structural, and Behavioral patterns\
  \ as appropriate\n\n- **Enterprise Application Patterns** (Martin Fowler)\n  - Domain\
  \ Logic patterns (Domain Model, Transaction Script)\n  - Data Source Architectural\
  \ patterns (Table Data Gateway, Active Record, Data Mapper)\n  - Object-Relational\
  \ Behavioral/Structural patterns (Identity Map, Unit of Work, Lazy Load)\n  - Web\
  \ Presentation patterns (MVC, Front Controller, Template View)\n\n- **Domain-Driven\
  \ Design Principles** (Eric Evans)\n  - Ubiquitous Language and Bounded Contexts\n\
  \  - Strategic Design with Context Maps\n  - Tactical Design with Aggregates, Entities,\
  \ Value Objects\n  - Domain Events and Event Sourcing\n\n- **Code Quality Metrics**\n\
  \  - Reduced complexity, improved cohesion, decreased coupling\n  - Language-specific\
  \ performance considerations\n\n- **Technical Debt Reduction** (Ward Cunningham\
  \ concept)\n  - Identifying and addressing deliberate and inadvertent technical\
  \ debt\n\n## Language-Specific Considerations\n\nI'll adapt the refactoring to follow\
  \ $1-specific (or detected language) idioms, including:\n\n- Language-specific design\
  \ patterns\n- Standard library utilization\n- Performance optimizations\n- Community-established\
  \ conventions\n- Modern language features\n\n## Academic and Industry References\n\
  \n- \"Refactoring: Improving the Design of Existing Code\" (Martin Fowler)\n- \"\
  Clean Code: A Handbook of Agile Software Craftsmanship\" (Robert C. Martin)\n- \"\
  Design Patterns: Elements of Reusable Object-Oriented Software\" (Gamma, Helm, Johnson,\
  \ Vlissides)\n- \"Working Effectively with Legacy Code\" (Michael Feathers)\n- \"\
  Patterns of Enterprise Application Architecture\" (Martin Fowler)\n- \"Domain-Driven\
  \ Design: Tackling Complexity in the Heart of Software\" (Eric Evans)\n- \"Implementing\
  \ Domain-Driven Design\" (Vaughn Vernon)\n- \"A Philosophy of Software Design\"\
  \ (John Ousterhout)\n- \"Clean Architecture: A Craftsman's Guide to Software Structure\
  \ and Design\" (Robert C. Martin)\n- \"Building Evolutionary Architectures\" (Neal\
  \ Ford, Rebecca Parsons, Patrick Kua)\n- Relevant language-specific style guides\
  \ and research papers\n\nLet me analyze your code and provide a comprehensive refactoring\
  \ that preserves behavior while improving design, readability, and maintainability\
  \ according to established principles and $1-specific best practices.\n"
---

# Code Refactoring Guide

I'll help you refactor code by applying established software engineering principles, design patterns, and best practices from highly regarded literature and academic research. The refactoring will adapt the code to follow idioms and conventions specific to $1 or the detected language if no target language is specified.

## Refactoring Process

1. **Analysis Phase**
   - Identify code smells using Martin Fowler's classification
   - Assess current design patterns and architectural approach
   - Evaluate complexity using metrics (cyclomatic complexity, coupling, cohesion)
   - Detect potential technical debt indicators

2. **Planning Phase**
   - Select appropriate refactoring techniques from Fowler's catalog
   - Identify applicable design patterns from GoF or modern equivalents
   - Consider enterprise patterns and domain-driven design principles where appropriate
   - Determine language-specific idioms and best practices to apply
   - Plan refactoring sequence to maintain behavior while transforming structure

3. **Implementation Phase**
   - Apply refactoring transformations systematically
   - Incorporate language-specific idioms and conventions
   - Implement selected design patterns where appropriate
   - Improve naming, comments, and documentation

4. **Validation Phase**
   - Ensure behavior preservation (suggest tests if absent)
   - Verify adherence to SOLID principles
   - Confirm improved readability and maintainability
   - Validate language-specific best practices

## Principles Applied

- **SOLID Principles** (Robert C. Martin)
  - Single Responsibility, Open-Closed, Liskov Substitution, Interface Segregation, Dependency Inversion

- **Clean Code Practices** (Robert C. Martin)
  - Meaningful names, small functions, DRY principle, comment purposefully

- **Design Patterns** (Gang of Four + Modern Patterns)
  - Creational, Structural, and Behavioral patterns as appropriate

- **Enterprise Application Patterns** (Martin Fowler)
  - Domain Logic patterns (Domain Model, Transaction Script)
  - Data Source Architectural patterns (Table Data Gateway, Active Record, Data Mapper)
  - Object-Relational Behavioral/Structural patterns (Identity Map, Unit of Work, Lazy Load)
  - Web Presentation patterns (MVC, Front Controller, Template View)

- **Domain-Driven Design Principles** (Eric Evans)
  - Ubiquitous Language and Bounded Contexts
  - Strategic Design with Context Maps
  - Tactical Design with Aggregates, Entities, Value Objects
  - Domain Events and Event Sourcing

- **Code Quality Metrics**
  - Reduced complexity, improved cohesion, decreased coupling
  - Language-specific performance considerations

- **Technical Debt Reduction** (Ward Cunningham concept)
  - Identifying and addressing deliberate and inadvertent technical debt

## Language-Specific Considerations

I'll adapt the refactoring to follow $1-specific (or detected language) idioms, including:

- Language-specific design patterns
- Standard library utilization
- Performance optimizations
- Community-established conventions
- Modern language features

## Academic and Industry References

- "Refactoring: Improving the Design of Existing Code" (Martin Fowler)
- "Clean Code: A Handbook of Agile Software Craftsmanship" (Robert C. Martin)
- "Design Patterns: Elements of Reusable Object-Oriented Software" (Gamma, Helm, Johnson, Vlissides)
- "Working Effectively with Legacy Code" (Michael Feathers)
- "Patterns of Enterprise Application Architecture" (Martin Fowler)
- "Domain-Driven Design: Tackling Complexity in the Heart of Software" (Eric Evans)
- "Implementing Domain-Driven Design" (Vaughn Vernon)
- "A Philosophy of Software Design" (John Ousterhout)
- "Clean Architecture: A Craftsman's Guide to Software Structure and Design" (Robert C. Martin)
- "Building Evolutionary Architectures" (Neal Ford, Rebecca Parsons, Patrick Kua)
- Relevant language-specific style guides and research papers

Let me analyze your code and provide a comprehensive refactoring that preserves behavior while improving design, readability, and maintainability according to established principles and $1-specific best practices.
