# GoF Design Patterns in Java / Spring Boot

Apply patterns from the `design-patterns` skill. Below are idiomatic Java/Spring translations. PoEAA patterns (Repository, Data Mapper, Service Layer, Unit of Work, Value Object) are covered in [DDD and PoEAA Patterns](ddd-and-poeaa-patterns.md) — this file covers GoF patterns.

## Creational

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

## Structural

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

## Behavioral

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
