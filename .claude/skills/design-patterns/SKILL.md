---
name: design-patterns
description: Apply design patterns from Gang of Four (GoF) and Patterns of Enterprise Application Architecture (Fowler/PoEAA). Use when structuring new code, evaluating design decisions, or identifying the right pattern for a problem. Covers when to use, when to avoid, and Go-idiomatic implementations.
---

# Design Patterns

Apply patterns from two authoritative sources:
- **GoF**: *Design Patterns* — Gamma, Helm, Johnson, Vlissides
- **PoEAA**: *Patterns of Enterprise Application Architecture* — Martin Fowler

**Key principle**: patterns describe solutions to recurring problems — use them when the problem recurs, not to demonstrate pattern knowledge. In Go, first-class functions and interfaces make several GoF patterns unnecessary or simpler than in OOP languages.

---

> For encoding pattern invariants into the type system (Value Objects, sum types, smart constructors), apply the `type-driven-design` skill.

## Decision Guide

Start here: match the problem to a pattern and its Go idiom, then read the relevant reference file for the full write-up (problem statement, code example, use/avoid criteria).

| Problem | Pattern | Go Idiom | Reference |
|---------|---------|----------|-----------|
| Create without specifying concrete type | Factory | Constructor func returning interface | [GoF Creational](references/gof-creational-patterns.md) |
| Many optional parameters | Builder | Functional options `...Option` | [GoF Creational](references/gof-creational-patterns.md) |
| Coordinating one shared instance | Singleton | `sync.Once` (but prefer DI) | [GoF Creational](references/gof-creational-patterns.md) |
| Incompatible interfaces | Adapter | Struct composition | [GoF Structural](references/gof-structural-patterns.md) |
| Cross-cutting concerns | Decorator | Middleware func | [GoF Structural](references/gof-structural-patterns.md) |
| Simplify complex subsystem | Facade | Clean package API | [GoF Structural](references/gof-structural-patterns.md) |
| Lazy/controlled access to a resource | Proxy | Wrapping struct, same interface | [GoF Structural](references/gof-structural-patterns.md) |
| Tree structures | Composite | `[]Interface` | [GoF Structural](references/gof-structural-patterns.md) |
| Swappable algorithms | Strategy | Function type | [GoF Behavioral](references/gof-behavioral-patterns.md) |
| One-to-many event notification | Observer | Channels | [GoF Behavioral](references/gof-behavioral-patterns.md) |
| Request queueing / undo | Command | `func() error` closures | [GoF Behavioral](references/gof-behavioral-patterns.md) |
| Shared algorithm skeleton, varying steps | Template Method | Interface + free function | [GoF Behavioral](references/gof-behavioral-patterns.md) |
| Request pipelines | Chain of Responsibility | Middleware composition | [GoF Behavioral](references/gof-behavioral-patterns.md) |
| State-dependent behavior | State | State interface with `Next()` | [GoF Behavioral](references/gof-behavioral-patterns.md) |
| Data access abstraction | Repository | Interface in domain, impl in infra | [PoEAA Patterns](references/poeaa-patterns.md) |
| Multi-repo transactions | Unit of Work | Shared `*sql.Tx` | [PoEAA Patterns](references/poeaa-patterns.md) |
| Complex business logic | Domain Model | Rich entities with methods | [PoEAA Patterns](references/poeaa-patterns.md) |
| Simple procedural operations | Transaction Script | Plain functions | [PoEAA Patterns](references/poeaa-patterns.md) |
| Identity-less domain concepts | Value Object | Immutable struct, value receivers | [PoEAA Patterns](references/poeaa-patterns.md) |
| Central lookup by type/name | Registry | `map[string]T` + `Register()` | [PoEAA Patterns](references/poeaa-patterns.md) |

## Pattern Catalog

- [GoF Creational Patterns](references/gof-creational-patterns.md) — Factory Method/Abstract Factory, Builder/Functional Options, Singleton
- [GoF Structural Patterns](references/gof-structural-patterns.md) — Adapter, Decorator/Middleware, Facade, Proxy, Composite
- [GoF Behavioral Patterns](references/gof-behavioral-patterns.md) — Strategy, Observer, Command, Template Method, Chain of Responsibility, State
- [PoEAA Patterns](references/poeaa-patterns.md) — Repository, Unit of Work, Data Mapper vs. Active Record, Service Layer, Domain Model, Transaction Script, Value Object, Registry

## Go Idioms That Replace GoF Patterns

Go's language features often make a GoF pattern's object-oriented machinery unnecessary:

| GoF Pattern | Go Replacement |
|-------------|---------------|
| Command | `func() error` closures |
| Strategy | Function types as fields |
| Iterator | `range` built-in |
| Observer | Channels + goroutines |
| Template Method | Interface + free function |
| Singleton | `sync.Once` (but prefer DI) |
| Abstract Factory | Constructor functions returning interfaces |

## References
- *Design Patterns: Elements of Reusable Object-Oriented Software* — Gamma, Helm, Johnson, Vlissides (GoF)
- *Patterns of Enterprise Application Architecture* — Martin Fowler
- PoEAA catalog: martinfowler.com/eaaCatalog

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `type-driven-design` | Encoding pattern invariants (Value Objects, sum types, smart constructors) in the type system |
| `code-spring-boot` | Spring Boot / Java implementations of PoEAA and GoF patterns |
| `code-architecture-best-practices` | SOLID principles, Clean Architecture, module boundary enforcement |
| `golang-development` | Go-idiomatic pattern implementations (functional options, channels, interfaces) |
| `code-refactoring` | Migrating from anti-patterns (Transaction Script → Domain Model) using ast-grep |
| `code-review` | Reviewing pattern usage and identifying anti-patterns in PRs |
