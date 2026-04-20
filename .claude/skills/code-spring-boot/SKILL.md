---
name: code-spring-boot
description: Apply Spring Boot and Java coding standards when writing, reviewing, or designing Java code. Use for Spring Boot project structure, DDD patterns (Entities, Aggregates, Repositories, Domain Services), Clean Code principles in Java, PoEAA patterns (Repository, Data Mapper, Service Layer, Unit of Work), testing with JUnit 5 and Mockito, and Spring-specific best practices. Covers constructor injection, transaction boundaries, layer responsibilities, and common anti-patterns to avoid.
---

# Spring Boot Java Development Standards

Apply these standards when writing, reviewing, or designing Java/Spring Boot code.

---

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

## Domain-Driven Design

### Entities and Aggregates
Entities have identity; Aggregates enforce consistency boundaries through their root:

```java
// Aggregate Root — all changes enter through here
public class Order {
    private final OrderId id;
    private final CustomerId customerId;
    private final List<OrderItem> items = new ArrayList<>();
    private OrderStatus status;

    // Factory method — enforces creation invariants
    public static Order create(CustomerId customerId, List<OrderItem> items) {
        if (items.isEmpty()) throw new DomainException("Order must have items");
        return new Order(OrderId.generate(), customerId, items);
    }

    // Business behaviour — not just getters/setters
    public void cancel() {
        if (status == OrderStatus.SHIPPED) {
            throw new DomainException("Cannot cancel a shipped order");
        }
        this.status = OrderStatus.CANCELLED;
    }

    public Money total() {
        return items.stream()
            .map(OrderItem::subtotal)
            .reduce(Money.ZERO, Money::add);
    }
}
```

### Value Objects (PoEAA: Value Object)
Immutable, no identity, equality by value. Use `record` in Java 16+:

```java
// Java record — immutable Value Object
public record Money(BigDecimal amount, Currency currency) {

    public Money {  // Compact constructor for validation
        Objects.requireNonNull(amount, "Amount required");
        Objects.requireNonNull(currency, "Currency required");
        if (amount.compareTo(BigDecimal.ZERO) < 0) {
            throw new IllegalArgumentException("Amount cannot be negative");
        }
    }

    public Money add(Money other) {
        if (!this.currency.equals(other.currency)) {
            throw new DomainException("Currency mismatch");
        }
        return new Money(this.amount.add(other.amount), this.currency);
    }

    public static Money of(String amount, String currencyCode) {
        return new Money(new BigDecimal(amount), Currency.getInstance(currencyCode));
    }
}

// Typed IDs as Value Objects — prevents primitive obsession
public record OrderId(UUID value) {
    public static OrderId generate() { return new OrderId(UUID.randomUUID()); }
    public static OrderId of(String id) { return new OrderId(UUID.fromString(id)); }
}
```

### Repository Pattern (DDD + PoEAA)
Domain defines the interface (port); infrastructure implements it (adapter):

```java
// Domain layer — pure interface, no Spring/JPA annotations
public interface OrderRepository {
    Optional<Order> findById(OrderId id);
    List<Order> findByCustomer(CustomerId customerId);
    Order save(Order order);
    void delete(OrderId id);
}

// Infrastructure layer — JPA implementation
@Repository
class JpaOrderRepository implements OrderRepository {
    private final OrderJpaEntityRepository jpa;   // Spring Data JPA
    private final OrderMapper mapper;

    @Override
    public Optional<Order> findById(OrderId id) {
        return jpa.findById(id.value())
            .map(mapper::toDomain);
    }

    @Override
    public Order save(Order order) {
        OrderJpaEntity entity = mapper.toJpa(order);
        return mapper.toDomain(jpa.save(entity));
    }
}
```

### Data Mapper (PoEAA)
Separates domain objects from persistence representation — domain never extends JPA entities:

```java
@Component
public class OrderMapper {

    public Order toDomain(OrderJpaEntity entity) {
        return Order.reconstitute(
            OrderId.of(entity.getId().toString()),
            CustomerId.of(entity.getCustomerId()),
            entity.getItems().stream().map(this::itemToDomain).toList(),
            entity.getStatus()
        );
    }

    public OrderJpaEntity toJpa(Order order) {
        OrderJpaEntity entity = new OrderJpaEntity();
        entity.setId(order.getId().value());
        entity.setCustomerId(order.getCustomerId().value());
        entity.setStatus(order.getStatus());
        entity.setItems(order.getItems().stream().map(this::itemToJpa).toList());
        return entity;
    }
}
```

### Domain Service vs Application Service
```java
// DOMAIN SERVICE: pure business logic across multiple entities
// No @Service — it's a domain concept, not a Spring bean (or inject carefully)
public class PricingService {
    public Money calculateOrderTotal(Order order, CustomerDiscount discount) {
        Money subtotal = order.total();
        return discount.apply(subtotal);  // Domain rule, no I/O
    }
}

// APPLICATION SERVICE: orchestrates use case, owns transaction
@Service
@Transactional
public class OrderApplicationService {

    public OrderId placeOrder(CreateOrderCommand cmd) {
        Customer customer = customerRepository.findById(cmd.customerId())
            .orElseThrow(() -> new NotFoundException("Customer not found"));

        List<OrderItem> items = cmd.items().stream()
            .map(this::resolveItem).toList();

        Order order = Order.create(customer.getId(), items);

        // Apply pricing (domain service)
        Money total = pricingService.calculateOrderTotal(order, customer.discount());

        orderRepository.save(order);
        eventPublisher.publishEvent(new OrderPlacedEvent(order.getId(), total));

        return order.getId();
    }
}
```

---

## PoEAA Patterns

### Service Layer (Fowler PoEAA)
Application services define the application's boundary. One method = one use case. Transaction starts and ends here.

```java
@Service
@Transactional          // Transaction boundary at application service
@RequiredArgsConstructor
public class OrderApplicationService {

    // Each method is a distinct use case
    public OrderId placeOrder(CreateOrderCommand cmd) { ... }
    public void cancelOrder(CancelOrderCommand cmd) { ... }
    public OrderSummary getOrderSummary(OrderId id) { ... }
}
```

### Unit of Work (PoEAA)
Spring's `@Transactional` implements Unit of Work — all changes within a transaction are tracked and flushed together. Rules:
- Place `@Transactional` on **application service methods**, not repositories or domain objects
- Use `@Transactional(readOnly = true)` on query-only methods for performance
- Never catch and swallow exceptions inside `@Transactional` — it prevents rollback

### Repository (PoEAA)
Already covered above. Key distinction from PoEAA: Repository is a **collection abstraction** over Aggregates. One repository per Aggregate Root.

---

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

## Testing

### Testing Layers

| Layer | Annotation | What to test | Avoid |
|-------|-----------|-------------|-------|
| Domain | None (plain JUnit) | Entity invariants, business rules | Mocks of domain objects |
| Application | `@ExtendWith(MockitoExtension.class)` | Use case flows, coordination | Real DB/HTTP |
| Repository | `@DataJpaTest` | SQL, mapping, queries | Application logic |
| Controller | `@WebMvcTest` | HTTP binding, validation, response codes | Business logic |
| Integration | `@SpringBootTest` | Full stack, happy paths | Exhaustive edge cases |

### Domain Tests — No Spring, No Mocks
```java
class OrderTest {

    @Test
    void cannot_cancel_shipped_order() {
        Order order = Order.create(CustomerId.generate(), List.of(anItem()));
        order.ship();

        assertThatThrownBy(order::cancel)
            .isInstanceOf(DomainException.class)
            .hasMessageContaining("Cannot cancel a shipped order");
    }

    @Test
    void total_sums_all_item_subtotals() {
        Order order = Order.create(CustomerId.generate(), List.of(
            OrderItem.of(productId, 2, Money.of("10.00", "USD")),
            OrderItem.of(productId, 1, Money.of("5.00", "USD"))
        ));

        assertThat(order.total()).isEqualTo(Money.of("25.00", "USD"));
    }
}
```

### Application Service Tests — Mockito
```java
@ExtendWith(MockitoExtension.class)
class OrderApplicationServiceTest {

    @Mock OrderRepository orderRepository;
    @Mock PaymentService paymentService;
    @InjectMocks OrderApplicationService sut;

    @Test
    void places_order_and_saves_it() {
        var cmd = new CreateOrderCommand(customerId, List.of(anItemDto()));
        when(customerRepository.findById(customerId)).thenReturn(Optional.of(aCustomer()));

        OrderId result = sut.placeOrder(cmd);

        assertThat(result).isNotNull();
        verify(orderRepository).save(any(Order.class));
    }
}
```

### Repository Tests — `@DataJpaTest`
```java
@DataJpaTest
class JpaOrderRepositoryTest {

    @Autowired OrderRepository orderRepository;  // The real JPA implementation

    @Test
    void finds_order_by_id() {
        Order saved = orderRepository.save(anOrder());
        Optional<Order> found = orderRepository.findById(saved.getId());
        assertThat(found).isPresent();
        assertThat(found.get().total()).isEqualTo(saved.total());
    }
}
```

### Testcontainers for Real DB
```java
@SpringBootTest
@Testcontainers
class OrderIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Test
    void full_order_placement_flow() { ... }
}
```

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

Apply patterns from the `design-patterns` skill. Below are idiomatic Java/Spring translations. PoEAA patterns (Repository, Data Mapper, Service Layer, Unit of Work, Value Object) are already covered above — this section covers GoF patterns.

### Creational

**Factory Method** — static factory methods on domain objects; avoid `new` in application code:
```java
// On the domain type itself
public static Order create(CustomerId customerId, List<OrderItem> items) {
    if (items.isEmpty()) throw new DomainException("Order must have items");
    return new Order(OrderId.generate(), customerId, items, OrderStatus.PENDING);
}

// Or a dedicated factory component for complex creation
@Component
public class OrderFactory {
    public Order from(CreateOrderCommand cmd, List<Product> products) { ... }
}
```

**Builder** — use `record` compact constructors for Value Objects; Lombok `@Builder` for complex DTOs; avoid for domain entities (use factory methods instead):
```java
// Value Object: record handles construction
public record ShippingAddress(String street, String city, String country) {
    public ShippingAddress {
        Objects.requireNonNull(street); Objects.requireNonNull(city);
    }
}

// Complex DTO: Lombok Builder
@Builder
@Value
public class SendEmailCommand {
    String to, subject, body;
    List<String> cc;
    Instant scheduleAt;
}

// Usage
SendEmailCommand.builder()
    .to("user@example.com")
    .subject("Welcome")
    .body("Hello!")
    .build();
```

**Singleton** — Spring beans are singletons by default; never roll your own:
```java
@Service  // Spring manages lifecycle — one instance per context
public class OrderApplicationService { ... }
```
Never use `static` singleton instances in Spring apps — they break testing and context isolation.

---

### Structural

**Adapter** — implement an interface to wrap a third-party client:
```java
// Your domain port
public interface PaymentGateway {
    PaymentResult charge(Money amount, String cardToken);
}

// Adapter wraps the Stripe SDK
@Component
public class StripePaymentAdapter implements PaymentGateway {
    private final StripeClient stripe;

    @Override
    public PaymentResult charge(Money amount, String cardToken) {
        var charge = stripe.charges().create(ChargeCreateParams.builder()
            .setAmount(amount.toCents())
            .setCurrency(amount.currency().getCode())
            .setSource(cardToken)
            .build());
        return PaymentResult.success(charge.getId());
    }
}
```

**Decorator** — implement the same interface and delegate, adding behaviour:
```java
@Component
@Primary  // Spring injects this when PaymentGateway is requested
public class LoggingPaymentGateway implements PaymentGateway {
    private final PaymentGateway delegate;  // real implementation injected
    private final Logger log = LoggerFactory.getLogger(getClass());

    @Override
    public PaymentResult charge(Money amount, String cardToken) {
        log.info("Charging {} {}", amount.amount(), amount.currency());
        PaymentResult result = delegate.charge(amount, cardToken);
        log.info("Result: {}", result);
        return result;
    }
}
```

**Facade** — the Application Service IS your facade to the domain:
```java
// Clients (controllers, messaging consumers) call only the application service
@Service @Transactional
public class OrderApplicationService {
    public OrderId placeOrder(CreateOrderCommand cmd) { ... }   // one use case
    public void cancelOrder(CancelOrderCommand cmd) { ... }
    public OrderSummary getOrder(OrderId id) { ... }
}
```

---

### Behavioral

**Strategy** — define an interface, inject by name or use a `Map<String, Strategy>`:
```java
public interface ShippingCalculator {
    Money calculate(Order order, Address destination);
}

@Component("standardShipping")
public class StandardShippingCalculator implements ShippingCalculator { ... }

@Component("expressShipping")
public class ExpressShippingCalculator implements ShippingCalculator { ... }

// Inject all implementations and select at runtime
@Service
public class ShippingService {
    private final Map<String, ShippingCalculator> calculators;

    public ShippingService(Map<String, ShippingCalculator> calculators) {
        this.calculators = calculators;
    }

    public Money getRate(String type, Order order, Address dest) {
        return Optional.ofNullable(calculators.get(type + "Shipping"))
            .orElseThrow(() -> new IllegalArgumentException("Unknown shipping type: " + type))
            .calculate(order, dest);
    }
}
```

**Observer / Events** — use `ApplicationEventPublisher` + `@EventListener`; keeps aggregates decoupled from side effects:
```java
// Publish in application service after transaction commits
eventPublisher.publishEvent(new OrderPlacedEvent(order.getId(), order.total()));

// Handle in any @Component — no coupling back to Order
@EventListener
@Async  // run in separate thread if side effect should not block
public void onOrderPlaced(OrderPlacedEvent event) {
    emailService.sendConfirmation(event.orderId());
}

// For transactional event guarantees
@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
public void afterCommit(OrderPlacedEvent event) { ... }
```

**Command (DTO as Command)** — use record Commands as input to application services:
```java
// Command = intent to change state
public record CreateOrderCommand(CustomerId customerId, List<OrderItemDto> items) {}
public record CancelOrderCommand(OrderId orderId, String reason) {}

// Application service receives and executes
public OrderId placeOrder(CreateOrderCommand cmd) { ... }
```
For queueable/undoable commands, implement a `Command` interface with `execute()` and `undo()`.

**Template Method** — abstract class defines the algorithm; subclasses fill in steps:
```java
public abstract class DataImporter<T> {

    // Template method — defines the algorithm
    public final ImportResult run(InputStream input) {
        List<T> records = parse(input);
        List<T> valid = validate(records);
        persist(valid);
        return ImportResult.of(records.size(), valid.size());
    }

    protected abstract List<T> parse(InputStream input);
    protected abstract List<T> validate(List<T> records);
    protected abstract void persist(List<T> records);
}

@Component
public class CsvOrderImporter extends DataImporter<OrderRow> {
    @Override protected List<OrderRow> parse(InputStream in) { ... }
    @Override protected List<OrderRow> validate(List<OrderRow> rows) { ... }
    @Override protected void persist(List<OrderRow> rows) { ... }
}
```

**Chain of Responsibility** — use Spring's `HandlerInterceptor`, Servlet filters, or a manual chain:
```java
// Manual handler chain for domain-level pipeline
@FunctionalInterface
public interface RequestHandler {
    void handle(ProcessingContext ctx, Runnable next);
}

// Each handler calls next.run() to continue the chain or stops
public class ValidationHandler implements RequestHandler {
    @Override
    public void handle(ProcessingContext ctx, Runnable next) {
        if (!ctx.isValid()) throw new ValidationException("Invalid request");
        next.run();
    }
}
```

**State** — use sealed interfaces with `record` implementations (Java 17+):
```java
public sealed interface OrderStatus
    permits OrderStatus.Pending, OrderStatus.Confirmed, OrderStatus.Shipped, OrderStatus.Cancelled {

    record Pending() implements OrderStatus {
        public OrderStatus confirm() { return new Confirmed(); }
        public OrderStatus cancel() { return new Cancelled(); }
    }

    record Confirmed() implements OrderStatus {
        public OrderStatus ship() { return new Shipped(); }
        public OrderStatus cancel() { return new Cancelled(); }
    }

    record Shipped() implements OrderStatus {}    // terminal — no transitions
    record Cancelled() implements OrderStatus {}  // terminal
}
```
Pattern-match with `switch` expressions to handle states exhaustively — the compiler enforces coverage.

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
// Sealed class for exhaustive domain states
public sealed interface PaymentResult
    permits PaymentResult.Success, PaymentResult.Failed, PaymentResult.Pending {

    record Success(String transactionId) implements PaymentResult {}
    record Failed(String reason) implements PaymentResult {}
    record Pending(String referenceId) implements PaymentResult {}
}

// Pattern matching switch — exhaustive, no default needed
String message = switch (result) {
    case PaymentResult.Success s -> "Paid: " + s.transactionId();
    case PaymentResult.Failed f  -> "Failed: " + f.reason();
    case PaymentResult.Pending p -> "Pending: " + p.referenceId();
};
```
