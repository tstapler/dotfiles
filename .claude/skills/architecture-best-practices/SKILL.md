---
name: architecture-best-practices
description: Apply software architecture best practices when designing or reviewing systems, classes, modules, or services. Use when structuring new code, evaluating design decisions, applying SOLID principles, Clean Architecture, Hexagonal Architecture, or Domain-Driven Design patterns. Works across languages — includes specific guidance for Python and Java/Spring Boot.
---

# Architecture Best Practices

Apply these principles when designing systems, reviewing structure, or making architectural decisions.

## Core Principles (Language-Agnostic)

### SOLID
- **S**ingle Responsibility: One reason to change per class/module
- **O**pen/Closed: Open for extension, closed for modification (use interfaces/protocols)
- **L**iskov Substitution: Subtypes must be substitutable for base types
- **I**nterface Segregation: Many focused interfaces > one fat interface
- **D**ependency Inversion: Depend on abstractions, not concretions

### Clean Architecture Layers
```
┌─────────────────────────────────┐
│  Frameworks & Drivers (Web, DB) │  ← outermost, most volatile
├─────────────────────────────────┤
│  Interface Adapters (Controllers│
│  Presenters, Gateways)          │
├─────────────────────────────────┤
│  Application Use Cases          │  ← orchestrates domain
├─────────────────────────────────┤
│  Domain Entities & Rules        │  ← innermost, most stable
└─────────────────────────────────┘
```
**Rule**: Dependencies point inward only. Domain knows nothing about frameworks.

### Hexagonal Architecture (Ports & Adapters)
- **Ports**: Interfaces defined by the domain (what the app needs)
- **Adapters**: Implementations of ports (HTTP, DB, messaging)
- **Core**: Business logic with no framework dependencies
- Enables swapping infrastructure without touching domain logic

### Domain-Driven Design Essentials
| Concept | Purpose | Rule |
|---------|---------|------|
| **Entity** | Has identity, mutable | Identified by ID, not attributes |
| **Value Object** | Immutable, no identity | Equality by value; replace, don't mutate |
| **Aggregate** | Consistency boundary | Only modify through Aggregate Root |
| **Repository** | Collection abstraction | One per Aggregate Root; hides persistence |
| **Domain Service** | Logic not owned by entity | Stateless; operates on multiple entities |
| **Application Service** | Use case orchestration | No business logic; coordinates domain objects |

### Key Design Rules
- **Tell, Don't Ask**: Objects should do things, not expose state to be checked externally
- **Law of Demeter**: Don't chain more than one `.` (avoid `a.b().c().d()`)
- **Composition over Inheritance**: Favor has-a over is-a
- **Command-Query Separation**: Methods either change state (command) or return data (query) — not both
- **Ubiquitous Language**: Code names must match domain expert vocabulary exactly

---

## Python-Specific Architecture

### Layer Structure
```
src/
├── domain/          # Entities, Value Objects, Domain Services, Repository interfaces
│   ├── models.py    # Pydantic/dataclass domain models
│   └── services.py  # Pure domain logic
├── application/     # Use cases, Application Services, DTOs
│   └── use_cases.py
├── infrastructure/  # Repository implementations, DB, HTTP clients
│   ├── repositories.py
│   └── clients.py
└── interfaces/      # CLI (Typer), API (FastAPI), etc.
    └── cli.py
```

### Repository Pattern
```python
from abc import ABC, abstractmethod
from typing import Protocol

# Domain defines the interface (port)
class UserRepository(Protocol):
    def find_by_id(self, user_id: str) -> User | None: ...
    def save(self, user: User) -> None: ...

# Infrastructure implements it (adapter)
class PostgresUserRepository:
    def find_by_id(self, user_id: str) -> User | None:
        ...
    def save(self, user: User) -> None:
        ...
```

### Dependency Injection
```python
# Application service receives dependencies — never imports them
class OrderService:
    def __init__(self, orders: OrderRepository, payments: PaymentService) -> None:
        self._orders = orders
        self._payments = payments
```

### Value Objects
```python
from dataclasses import dataclass

@dataclass(frozen=True)  # frozen=True makes it immutable
class Money:
    amount: Decimal
    currency: str

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Currency mismatch")
        return Money(self.amount + other.amount, self.currency)
```

### Avoid
- ❌ Business logic in CLI/API handlers
- ❌ Importing ORM models into domain layer
- ❌ God classes that do everything
- ❌ Mutable global state

---

## Java / Spring Boot-Specific Architecture

### Package Structure (by feature, not layer)
```
com.example.
├── order/
│   ├── domain/          # Order, OrderItem (entities/VOs)
│   ├── application/     # OrderService, CreateOrderCommand
│   ├── infrastructure/  # OrderJpaRepository, OrderMapper
│   └── api/             # OrderController, OrderRequest/Response DTOs
├── payment/
│   └── ...
└── shared/              # Shared kernel: common Value Objects, exceptions
```

### Spring Layering Rules
| Layer | Annotation | Responsibility |
|-------|-----------|----------------|
| API | `@RestController` | HTTP in/out, request validation, DTO mapping |
| Application | `@Service` | Use case orchestration, transaction boundary |
| Domain | (no Spring) | Pure business logic, entities, rules |
| Infrastructure | `@Repository` / `@Component` | DB, external HTTP, messaging |

### Dependency Direction
```
Controller → ApplicationService → DomainService/Entity
                               ↓
                         Repository (interface)
                               ↑
                    RepositoryImpl (infrastructure)
```
- Controllers depend on Application Services
- Application Services depend on Repository **interfaces** (domain layer)
- Infrastructure implements those interfaces
- Domain layer has **zero Spring dependencies**

### Key Spring Boot Patterns
```java
// Application Service — owns transaction boundary
@Service
@Transactional
public class OrderApplicationService {
    private final OrderRepository orderRepository;  // interface, not JPA impl
    private final PaymentService paymentService;

    public OrderId createOrder(CreateOrderCommand cmd) {
        var order = Order.create(cmd.customerId(), cmd.items());
        paymentService.reserve(order.total());
        return orderRepository.save(order).id();
    }
}

// Repository interface in domain layer
public interface OrderRepository {
    Order save(Order order);
    Optional<Order> findById(OrderId id);
}

// JPA implementation in infrastructure layer
@Repository
class JpaOrderRepository implements OrderRepository {
    private final OrderJpaRepository jpa;  // Spring Data JPA
    ...
}
```

### Spring Boot Avoid
- ❌ Business logic in `@RestController`
- ❌ `@Autowired` field injection (use constructor injection)
- ❌ Exposing JPA entities directly in API responses
- ❌ `@Transactional` on domain objects
- ❌ Cross-feature direct class dependencies (use interfaces or events)

---

## Domain Events

Use events to decouple aggregates and trigger side effects without coupling:

```python
# Python
from dataclasses import dataclass, field
from datetime import datetime, UTC

@dataclass(frozen=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    order_id: str
    customer_id: str
    total: float

# Simple in-process event bus
class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type, list] = {}

    def subscribe(self, event_type: type, handler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(type(event), []):
            handler(event)
```

```java
// Java/Spring Boot: use ApplicationEventPublisher
@Service
public class OrderService {
    private final ApplicationEventPublisher eventPublisher;

    public void placeOrder(PlaceOrderCommand cmd) {
        Order order = Order.create(cmd);
        orderRepository.save(order);
        eventPublisher.publishEvent(new OrderPlacedEvent(order.getId()));
    }
}

@EventListener
public void onOrderPlaced(OrderPlacedEvent event) {
    notificationService.sendConfirmation(event.orderId());
}
```

## Protocol vs ABC (Python)

| Use Protocol | Use ABC |
|-------------|---------|
| External/3rd-party implementations | Need to enforce explicit inheritance |
| Duck-typing flexibility | Want to share default behavior |
| Testing (easier to mock) | Framework extension points |
| Ports/interfaces in hexagonal arch | Strategy hierarchies with shared logic |

```python
# Protocol: structural subtyping — no inheritance needed
class BookStorage(Protocol):
    def find_by_id(self, book_id: str) -> Book | None: ...
    def save(self, book: Book) -> None: ...

# ABC: nominal subtyping + shared implementation
class MergeStrategy(ABC):
    @abstractmethod
    def can_handle(self, base, local, remote) -> bool: ...

    @abstractmethod
    def apply(self, base, local, remote) -> list[str]: ...

    # Shared logic subclasses inherit
    def is_safe_merge(self, base, result) -> bool:
        return len(result) >= len(base) * 0.5
```

## Cross-Cutting Concerns

### Error Handling Strategy
- Domain errors: typed exceptions or Result types (not generic RuntimeException)
- Application layer: translates domain errors to user-facing messages
- Infrastructure layer: wraps external errors, never leaks them to domain

### Testing Boundaries
| Layer | Test Type | Strategy |
|-------|-----------|----------|
| Domain | Unit | Pure functions, no mocks needed |
| Application | Unit | Mock repositories/services |
| Infrastructure | Integration | Real DB (Testcontainers / pytest-docker) |
| API | Integration | Full stack or MockMvc/TestClient |

### Configuration
- Externalize all config (no hardcoded URLs, credentials, env-specific values)
- Domain layer never reads config — inject values via constructors
- Use typed config objects, not raw string lookups scattered through code

---

## Decision Guide

| Situation | Pattern |
|-----------|---------|
| Multiple implementations of same concept | Repository / Strategy pattern |
| Complex object creation | Factory / Builder |
| Cross-cutting concerns (logging, auth) | Decorator / Middleware |
| Notify other parts of system about events | Domain Events |
| Simplify complex subsystem | Facade (named `service`) |
| Decouple caller from implementation | Dependency Injection |
