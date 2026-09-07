# Domain-Driven Design and PoEAA Patterns

## Entities and Aggregates

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

## Value Objects (PoEAA: Value Object)

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

## Repository Pattern (DDD + PoEAA)

Domain defines the interface (port); infrastructure implements it (adapter). Repository is a **collection abstraction** over Aggregates — one repository per Aggregate Root.

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

## Data Mapper (PoEAA)

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

## Domain Service vs Application Service

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

## Service Layer (Fowler PoEAA)

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

## Unit of Work (PoEAA)

Spring's `@Transactional` implements Unit of Work — all changes within a transaction are tracked and flushed together. Rules:
- Place `@Transactional` on **application service methods**, not repositories or domain objects
- Use `@Transactional(readOnly = true)` on query-only methods for performance
- Never catch and swallow exceptions inside `@Transactional` — it prevents rollback
