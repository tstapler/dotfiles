# Type-Driven Design — Java Examples

Worked Java examples for every technique in the main `SKILL.md`. For enforcing
parse-at-boundary with Spring Boot `@RequestBody` validation, see the `code-spring-boot`
skill.

## Technique 1: Newtypes (Branded / Opaque Types)

```java
// Use records for newtypes — compact, immutable, value-equality
public record UserId(String value) {
    public UserId {
        Objects.requireNonNull(value);
        if (value.isBlank()) throw new IllegalArgumentException("UserId cannot be blank");
    }
    public static UserId of(String s) { return new UserId(s); }
}

public record OrderId(UUID value) {
    public static OrderId generate() { return new OrderId(UUID.randomUUID()); }
}

// Phantom type via generics
public record Id<T>(String value) {
    public static <T> Id<T> of(String s) { return new Id<>(s); }
}
// Id<User> and Id<Order> are incompatible at compile time
```

## Technique 2: Smart Constructors

```java
public final class Email {
    private final String value;  // private — can't be set outside

    public static Email of(String s) {
        if (s == null || !s.contains("@"))
            throw new InvalidEmailException(s);
        return new Email(s.toLowerCase());
    }

    private Email(String value) { this.value = value; }

    public String value() { return value; }
}
```

## Technique 3: Sum Types (Make Invalid States Unrepresentable)

Java 17+:
```java
public sealed interface OrderStatus
    permits Pending, Confirmed, Shipped, Cancelled {}

public record Pending()   implements OrderStatus {}
public record Confirmed() implements OrderStatus {}
public record Shipped()   implements OrderStatus {}
public record Cancelled() implements OrderStatus {}

// Pattern-matching switch — compiler enforces exhaustiveness
String describe(OrderStatus status) {
    return switch (status) {
        case Pending   p -> "awaiting confirmation";
        case Confirmed c -> "confirmed";
        case Shipped   s -> "on the way";
        case Cancelled x -> "cancelled";
        // No default needed — sealed = exhaustive
    };
}

// State transition
public Order confirm() {
    if (!(status instanceof Pending))
        throw new IllegalStateException("Can only confirm a pending order");
    return new Order(id, new Confirmed(), items);
}
```

## Technique 4: Value Objects

```java
public record Money(long cents, String currency) {
    private static final Set<String> SUPPORTED = Set.of("USD", "EUR", "GBP");

    public Money {
        if (cents < 0) throw new IllegalArgumentException("negative amount");
        if (!SUPPORTED.contains(currency))
            throw new IllegalArgumentException("unsupported currency: " + currency);
    }

    public static Money of(BigDecimal amount, String currency) {
        return new Money(amount.multiply(BigDecimal.valueOf(100)).longValueExact(), currency);
    }

    public Money add(Money other) {
        if (!this.currency.equals(other.currency))
            throw new DomainException("currency mismatch");
        return new Money(this.cents + other.cents, this.currency);
    }
    // record provides equals/hashCode/toString automatically
}
```

## Technique 5: Refinement Types (Constrained Primitives)

```java
public record NonEmptyList<T>(List<T> items) {
    public NonEmptyList {
        if (items.isEmpty()) throw new IllegalArgumentException("list must not be empty");
        items = List.copyOf(items);  // defensive copy + immutable
    }
    public T head() { return items.get(0); }  // safe
}
```

## Technique 6: Typestate Pattern (State Machines as Types)

Sealed interfaces for states — each state is a distinct type, transitions return new types:
```java
public record PendingOrder(OrderId id, List<Item> items) {
    public ConfirmedOrder confirm(PaymentId paymentId) {
        return new ConfirmedOrder(id, items, paymentId);
    }
    public CancelledOrder cancel() { return new CancelledOrder(id); }
}

public record ConfirmedOrder(OrderId id, List<Item> items, PaymentId paymentId) {
    public ShippedOrder ship(TrackingNumber tracking) {
        return new ShippedOrder(id, items, paymentId, tracking);
    }
}

// ShippedOrder has no `confirm()` — that transition doesn't exist in the type
```
