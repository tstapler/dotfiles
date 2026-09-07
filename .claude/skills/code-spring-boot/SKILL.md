---
name: code-spring-boot
description: Apply Spring Boot and Java coding standards when writing, reviewing, or designing Java code. Use for Spring Boot project structure, DDD patterns (Entities, Aggregates, Repositories, Domain Services), Clean Code principles in Java, PoEAA patterns (Repository, Data Mapper, Service Layer, Unit of Work), testing with JUnit 5 and Mockito, and Spring-specific best practices. Covers constructor injection, transaction boundaries, layer responsibilities, and common anti-patterns to avoid.
paths: "**/*.java,**/*.kt"
---

# Spring Boot Java Development Standards

Apply these standards when writing, reviewing, or designing Java/Spring Boot code.

---

> For structural refactors across this codebase, apply the `code-refactoring` skill.

## Project Structure (Package by Feature)

Organize by domain concept, not by technical layer. Each feature package is a self-contained vertical slice:

```
com.example.
├── order/
│   ├── domain/
│   │   ├── Order.java              # Aggregate Root (Entity)
│   │   ├── OrderItem.java          # Entity within aggregate
│   │   ├── Money.java              # Value Object
│   │   ├── OrderRepository.java    # Port (interface)
│   │   └── OrderDomainService.java # Domain Service
│   ├── application/
│   │   ├── OrderApplicationService.java  # Use case orchestration
│   │   ├── CreateOrderCommand.java       # Input DTO
│   │   └── OrderSummary.java             # Output DTO
│   ├── infrastructure/
│   │   ├── JpaOrderRepository.java  # Repository adapter
│   │   ├── OrderJpaEntity.java      # ORM mapping entity
│   │   └── OrderMapper.java         # Domain ↔ ORM mapping
│   └── api/
│       ├── OrderController.java     # REST adapter
│       ├── OrderRequest.java        # API input DTO
│       └── OrderResponse.java       # API output DTO
├── payment/
│   └── ...
└── shared/
    └── domain/                      # Shared kernel: common VOs, exceptions
        ├── Money.java
        └── DomainException.java
```

**Import rule**: Domain never imports Spring, JPA, or infrastructure classes.

---

## Layer Responsibilities

| Layer | Annotation | Owns | Never |
|-------|-----------|------|-------|
| `api/` | `@RestController` | HTTP parsing, input validation, DTO mapping | Business logic |
| `application/` | `@Service` | Use case orchestration, transaction boundary | Domain rules |
| `domain/` | (none) | Business logic, invariants, rules | Spring, JPA, I/O |
| `infrastructure/` | `@Repository` / `@Component` | DB, HTTP, messaging | Business logic |

**Dependency direction**: `api → application → domain ← infrastructure`

---

## Clean Code in Java

### Naming
- Classes: `PascalCase`, noun — `OrderApplicationService`, not `OrderManager`
- Methods: `camelCase`, verb phrase — `placeOrder()`, `findOverdueOrders()`
- Booleans: predicate form — `isEligible()`, `hasItems()`, `canBeCancelled()`
- Constants: `SCREAMING_SNAKE_CASE` — `MAX_RETRIES`, `DEFAULT_TIMEOUT_MS`
- Avoid noise words: `OrderData`, `OrderInfo`, `OrderObject` → just `Order`

### Functions (Clean Code Ch. 3)
- Do one thing at one level of abstraction
- Prefer fewer arguments; use a Command/DTO object when >2 related params
- Boolean flags as parameters are a code smell — split into two methods

```java
// ANTI-PATTERN: flag parameter
void renderPage(boolean isSuite) { ... }

// CORRECT: two clearly named methods
void renderTestPage() { ... }
void renderSuitePage() { ... }
```

### Constructor Injection (mandatory)
Never use `@Autowired` field injection — it hides dependencies and breaks testability:

```java
// ANTI-PATTERN
@Service
public class OrderService {
    @Autowired private OrderRepository repo;  // Hidden dependency
}

// CORRECT: constructor injection (Spring auto-injects when single constructor)
@Service
public class OrderApplicationService {
    private final OrderRepository orderRepository;
    private final PaymentService paymentService;

    public OrderApplicationService(
        OrderRepository orderRepository,
        PaymentService paymentService
    ) {
        this.orderRepository = orderRepository;
        this.paymentService = paymentService;
    }
}
```

---

## Domain-Driven Design and PoEAA Patterns

Core building blocks: **Entities/Aggregates** enforce invariants and consistency boundaries through their root; **Value Objects** (`record`s) are immutable and compared by value; the **Repository** is a collection abstraction over one Aggregate Root, with the interface defined in `domain/` and implemented in `infrastructure/`; a **Data Mapper** keeps domain objects from ever extending JPA entities; **Domain Services** hold pure cross-entity business logic while **Application Services** orchestrate use cases and own the `@Transactional` boundary (Unit of Work).

Full worked examples (Order aggregate, Money value object, JPA repository + mapper, domain vs. application service) are in [DDD and PoEAA Patterns](references/ddd-and-poeaa-patterns.md).

---

> For security concerns in REST controllers, exception handling, and data validation, apply the `security-review` skill.

## Error Handling

Define a typed exception hierarchy rooted in your domain:

```java
// Base exception
public class DomainException extends RuntimeException {
    public DomainException(String message) { super(message); }
    public DomainException(String message, Throwable cause) { super(message, cause); }
}

public class NotFoundException extends DomainException { ... }
public class BusinessRuleViolationException extends DomainException { ... }
public class ConflictException extends DomainException { ... }

// Global handler maps domain exceptions to HTTP responses
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(NotFoundException.class)
    ResponseEntity<ErrorResponse> handleNotFound(NotFoundException ex) {
        return ResponseEntity.status(404).body(new ErrorResponse(ex.getMessage()));
    }

    @ExceptionHandler(BusinessRuleViolationException.class)
    ResponseEntity<ErrorResponse> handleBusinessRule(BusinessRuleViolationException ex) {
        return ResponseEntity.status(422).body(new ErrorResponse(ex.getMessage()));
    }
}
```

---

> For full test coverage planning before writing code, apply the `infra-testing` skill.

## Testing

### Testing Layers

| Layer | Annotation | What to test | Avoid |
|-------|-----------|-------------|-------|
| Domain | None (plain JUnit) | Entity invariants, business rules | Mocks of domain objects |
| Application | `@ExtendWith(MockitoExtension.class)` | Use case flows, coordination | Real DB/HTTP |
| Repository | `@DataJpaTest` | SQL, mapping, queries | Application logic |
| Controller | `@WebMvcTest` | HTTP binding, validation, response codes | Business logic |
| Integration | `@SpringBootTest` | Full stack, happy paths | Exhaustive edge cases |

Full worked test examples for each layer (domain tests with no mocks, Mockito application-service tests, `@DataJpaTest` repository tests, Testcontainers integration tests) are in [Testing Examples](references/testing-examples.md).

---

## Type-Driven Design

Apply techniques from the `type-driven-design` skill to encode invariants into Java's type system.

**Core Java techniques:**
- Newtypes: `record UserId(String value)` with compact constructor validation — prevents mixing `UserId` with `OrderId`
- Phantom types: `Id<User>` vs `Id<Order>` via generics — incompatible at compile time
- Smart constructors: `private` constructor + `public static Email of(String s)` — holding `Email` proves validity
- Sum types: `sealed interface OrderStatus permits Pending, Confirmed, Shipped, Cancelled` — pattern-matching `switch` is exhaustive, no `default` needed
- Value Objects: `record Money(long cents, String currency)` — records are immutable and provide `equals`/`hashCode` automatically
- Typestate: `PendingOrder.confirm()` returns `ConfirmedOrder`; `ShippedOrder` has no `.confirm()` — invalid transitions don't exist in the type
- Parse at the boundary: Bean Validation (`@NotBlank`, `@Pattern`) on `@RequestBody` DTOs; pass proven domain types into the application service

**Signs you need this skill:** `String` status fields with magic-value comparisons, `@Nullable` fields that "always coexist", validation logic in multiple service methods, `double` for monetary amounts, `Optional.get()` without guard.

---

## GoF Design Patterns in Java / Spring Boot

Apply patterns from the `design-patterns` skill. Idiomatic Java/Spring translations exist for all three GoF categories:

- **Creational** — Factory Method (static factories on domain types), Builder (`record` compact constructors or Lombok `@Builder` for DTOs — not domain entities), Singleton (Spring beans are singletons by default; never roll your own)
- **Structural** — Adapter (wrap a third-party client behind a domain port interface), Decorator (`@Primary` bean delegating to the real implementation), Facade (the Application Service IS the facade)
- **Behavioral** — Strategy (`Map<String, Strategy>` injection), Observer (`ApplicationEventPublisher` + `@EventListener`/`@TransactionalEventListener`), Command (record Commands as application-service input), Template Method (abstract class defining the algorithm), Chain of Responsibility (`HandlerInterceptor` or a manual chain), State (sealed interfaces with `record` implementations)

Full code for each pattern is in [GoF Patterns in Java](references/gof-patterns-java.md).

---

## Common Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| `@Autowired` field injection | Constructor injection |
| Business logic in `@RestController` | Move to application/domain service |
| Exposing JPA entities in API responses | Use response DTOs + mapper |
| Domain objects extending JPA `@Entity` | Separate domain model from ORM entity |
| `@Transactional` on domain methods | `@Transactional` on application service only |
| `Optional.get()` without check | `orElseThrow()` with meaningful exception |
| Checked exceptions for domain errors | Unchecked `DomainException` hierarchy |
| `new` inside service constructors | Inject via constructor, compose at config time |
| Cross-feature direct class dependencies | Use interfaces or domain events |
| Anemic domain model (getters/setters only) | Move behaviour into entities (tell, don't ask) |

---

## Modern Java Features to Use

| Feature | Version | Use For |
|---------|---------|---------|
| `record` | 17 | Value Objects, DTOs, Commands |
| Sealed classes | 17 | Exhaustive domain states/events |
| Pattern matching `instanceof` | 16 | Replacing verbose casts |
| `switch` expressions | 14 | Replacing multi-case if/else |
| Text blocks | 15 | SQL strings, JSON in tests |
| `var` | 11 | Local variables with obvious type |

```java
// Sealed class for exhaustive domain states, matched with a pattern-matching switch
public sealed interface PaymentResult
    permits PaymentResult.Success, PaymentResult.Failed, PaymentResult.Pending {
    record Success(String transactionId) implements PaymentResult {}
    record Failed(String reason) implements PaymentResult {}
    record Pending(String referenceId) implements PaymentResult {}
}

String message = switch (result) {
    case PaymentResult.Success s -> "Paid: " + s.transactionId();
    case PaymentResult.Failed f  -> "Failed: " + f.reason();
    case PaymentResult.Pending p -> "Pending: " + p.referenceId();
};
```

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `design-patterns` | Selecting GoF or PoEAA patterns for Java/Spring design problems |
| `type-driven-design` | Encoding domain invariants with newtypes, sealed interfaces, smart constructors |
| `code-architecture-best-practices` | SOLID principles, Clean Architecture, module boundary enforcement |
| `code-refactoring` | Structural refactors across packages using ast-grep or gritql |
| `security-review` | OWASP audit of REST controllers, auth, input validation, secrets |
| `infra-testing` | Test coverage planning, Testcontainers, integration test strategies |
| `code-review` | PR feedback and verification gates for Java code |
| `jvm-performance` | JVM tuning, GC configuration, heap/thread profiling |

## References

- [DDD and PoEAA Patterns](references/ddd-and-poeaa-patterns.md) — Entities, Aggregates, Value Objects, Repository, Data Mapper, Service Layer, Unit of Work
- [Testing Examples](references/testing-examples.md) — full JUnit 5/Mockito/Testcontainers examples per layer
- [GoF Patterns in Java](references/gof-patterns-java.md) — Creational, Structural, Behavioral patterns with Spring idioms
