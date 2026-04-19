---
name: type-driven-design
description: Encode invariants and business logic into the type system so illegal states are unrepresentable. Use when designing domain models, reviewing code for primitive obsession, building Value Objects, modeling state machines, or applying Parse-Don't-Validate. Covers Go, Python, and Java with concrete before/after examples.
---

# Type-Driven Design

> "Make illegal states unrepresentable." — Yaron Minsky, Jane Street

Use the type system as the first line of defense. If the compiler rejects invalid states, they cannot occur at runtime. Shift validation from a runtime cost scattered across the codebase to a one-time compile-time guarantee at the boundary.

---

## Core Principles

### 1. Parse, Don't Validate (Alexis King)
The key distinction:
- **Validate**: check if data is valid, then pass the raw value around — you must check again everywhere
- **Parse**: transform raw input into a type that *proves* the check passed — downstream code needs no checks at all

```
// Validate (bad): string passes the check but stays a string
validateEmail(s string) bool

// Parse (good): if you have Email, it's already proven valid
parseEmail(s string) (Email, error)
```

Once you hold an `Email`, you never ask "is this a valid email?" again. The type *is* the proof.

### 2. Make Illegal States Unrepresentable (Yaron Minsky)
If certain data combinations are invalid in your domain, design your types so those combinations cannot be expressed. Don't document constraints — encode them.

```
// Bad: both fields optional, but domain says "must have one or the other"
type Contact struct {
    Email *string
    Phone *string
}

// Good: the type forces at least one
type Contact struct {
    Primary   ContactMethod  // required
    Secondary *ContactMethod // optional
}
type ContactMethod = Email | Phone  // sum type
```

### 3. Type as Proof
If construction requires validation, and the only constructor is private/unexported, then *holding an instance of the type proves the invariant holds*. No further checking needed — downstream code can trust the type.

### 4. Primitive Obsession is a Code Smell
Using `string`, `int`, `float64` for domain concepts (`UserId`, `Money`, `EmailAddress`) causes:
- Parameters mixed up silently (`func transfer(from, to string)` — easy to swap)
- Validation logic duplicated across the codebase
- No domain meaning at the type level

---

## Technique 1: Newtypes (Branded / Opaque Types)

Replace primitives with named domain types. The type carries domain meaning and prevents accidental mixing.

### Go
```go
// Bad: both are strings — compiler accepts swapping them
func Transfer(fromID, toID string, amount float64) error

// Good: distinct types
type UserID string
type AccountID string
type Cents int64

func Transfer(from AccountID, to AccountID, amount Cents) error

// Smart constructor
func NewUserID(s string) (UserID, error) {
    if s == "" { return "", errors.New("user ID cannot be empty") }
    return UserID(s), nil
}
```

Use `type Foo string` (new type), never `type Foo = string` (alias — no protection).

**Phantom types with generics** (prevent cross-entity ID confusion):
```go
type ID[T any] string  // T never used at runtime, exists only for type safety

type User struct{}
type Order struct{}

type UserID  = ID[User]
type OrderID = ID[Order]

func GetUser(id UserID) (*User, error)   { ... }
func GetOrder(id OrderID) (*Order, error) { ... }

// GetUser(orderID)  ← compile error
```

### Python
```python
from typing import NewType

UserID   = NewType('UserID', str)    # mypy enforces distinction
OrderID  = NewType('OrderID', str)

# Runtime enforcement: use a frozen dataclass
@dataclass(frozen=True)
class Email:
    value: str
    def __post_init__(self):
        if "@" not in self.value:
            raise ValueError(f"Invalid email: {self.value}")

    @classmethod
    def parse(cls, s: str) -> "Email":
        return cls(value=s)  # __post_init__ validates
```

### Java
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

---

## Technique 2: Smart Constructors

Private constructor + public factory function. The factory validates; holding the type proves validity.

### Go
```go
type Email string  // unexported fields can't be set directly in other packages

func ParseEmail(s string) (Email, error) {
    if !emailRegex.MatchString(s) {
        return "", fmt.Errorf("invalid email %q", s)
    }
    return Email(s), nil
}

// Callers: hold Email → it's proven valid. No further checks needed.
func SendWelcome(to Email) { ... }  // never validates inside
```

### Python
```python
@dataclass(frozen=True)
class PositiveAmount:
    _value: Decimal  # leading underscore = convention for "don't touch"

    @classmethod
    def of(cls, value: Decimal) -> "PositiveAmount":
        if value <= 0:
            raise ValueError(f"Amount must be positive, got {value}")
        return cls(_value=value)

    @property
    def value(self) -> Decimal: return self._value
```

With Pydantic (recommended for external input):
```python
from pydantic import BaseModel, field_validator

class Email(BaseModel):
    value: str
    model_config = ConfigDict(frozen=True)

    @field_validator("value")
    @classmethod
    def must_be_valid(cls, v: str) -> str:
        if "@" not in v: raise ValueError(f"Invalid email: {v}")
        return v.lower()
```

### Java
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

---

## Technique 3: Sum Types (Make Invalid States Unrepresentable)

Model mutually exclusive states as distinct types. The compiler enforces exhaustive handling.

### Go
```go
// Bad: magic strings, typos compile fine
type Order struct { Status string }

// Good: interface + unexported marker method seals the set
type OrderStatus interface{ orderStatus() }

type Pending   struct{}
type Confirmed struct{}
type Shipped   struct{}
type Cancelled struct{}

func (Pending) orderStatus()   {}
func (Confirmed) orderStatus() {}
func (Shipped) orderStatus()   {}
func (Cancelled) orderStatus() {}

// State transitions enforce business rules
func (o *Order) Confirm() error {
    if _, ok := o.Status.(Pending); !ok {
        return fmt.Errorf("can only confirm a pending order, got %T", o.Status)
    }
    o.Status = Confirmed{}
    return nil
}

// Exhaustive switch (add default to catch future states)
func describeStatus(s OrderStatus) string {
    switch s.(type) {
    case Pending:   return "awaiting confirmation"
    case Confirmed: return "confirmed"
    case Shipped:   return "on the way"
    case Cancelled: return "cancelled"
    default:        panic(fmt.Sprintf("unknown status %T", s))
    }
}
```

### Python (3.10+)
```python
@dataclass(frozen=True)
class Pending:   pass

@dataclass(frozen=True)
class Confirmed: pass

@dataclass(frozen=True)
class Shipped:   pass

@dataclass(frozen=True)
class Cancelled: pass

OrderStatus = Pending | Confirmed | Shipped | Cancelled

def describe(status: OrderStatus) -> str:
    match status:
        case Pending():   return "awaiting confirmation"
        case Confirmed(): return "confirmed"
        case Shipped():   return "on the way"
        case Cancelled(): return "cancelled"
        # mypy warns if a case is missing (with sealed Protocol)
```

Pydantic discriminated unions for API input:
```python
class PendingOrder(BaseModel):
    status: Literal["pending"] = "pending"

class ConfirmedOrder(BaseModel):
    status: Literal["confirmed"] = "confirmed"

class OrderPayload(BaseModel):
    details: PendingOrder | ConfirmedOrder = Field(discriminator="status")
```

### Java (17+)
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

---

## Technique 4: Value Objects

Small, immutable, equality-by-value objects that enforce their own invariants. The type eliminates the need to validate domain concepts downstream.

### Key Properties
1. **Immutable** — operations return new instances
2. **Self-validating** — constructor rejects invalid state
3. **Equality by value** — two instances with same data are equal
4. **No identity** — not distinguished by ID

### Go
```go
type Money struct {
    cents    int64  // unexported
    currency string
}

func NewMoney(amount float64, currency string) (Money, error) {
    if amount < 0 { return Money{}, errors.New("amount cannot be negative") }
    switch currency {
    case "USD", "EUR", "GBP":
    default: return Money{}, fmt.Errorf("unsupported currency: %s", currency)
    }
    return Money{cents: int64(math.Round(amount * 100)), currency: currency}, nil
}

func (m Money) Add(other Money) (Money, error) {
    if m.currency != other.currency {
        return Money{}, errors.New("currency mismatch")
    }
    return Money{cents: m.cents + other.cents, currency: m.currency}, nil
}

func (m Money) Equal(other Money) bool {
    return m.cents == other.cents && m.currency == other.currency
}
```

### Python
```python
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("amount cannot be negative")
        if self.currency not in ("USD", "EUR", "GBP"):
            raise ValueError(f"unsupported currency: {self.currency}")

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("currency mismatch")
        return Money(self.amount + other.amount, self.currency)
    # __eq__ and __hash__ provided free by frozen dataclass
```

### Java
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

---

## Technique 5: Refinement Types (Constrained Primitives)

Types that carry a proof of a constraint — `NonEmptyList`, `PositiveInt`, `EmailAddress`.

```go
// Go
type NonEmptySlice[T any] struct{ items []T }

func NewNonEmptySlice[T any](items ...T) (NonEmptySlice[T], error) {
    if len(items) == 0 { return NonEmptySlice[T]{}, errors.New("must not be empty") }
    return NonEmptySlice[T]{items: items}, nil
}

func (s NonEmptySlice[T]) Head() T { return s.items[0] }  // safe — proven non-empty
```

```python
# Python — Pydantic makes this ergonomic
from pydantic import BaseModel, Field

class OrderItems(BaseModel):
    items: list[OrderItem] = Field(min_length=1)  # non-empty proven at parse time
    model_config = ConfigDict(frozen=True)
```

```java
// Java
public record NonEmptyList<T>(List<T> items) {
    public NonEmptyList {
        if (items.isEmpty()) throw new IllegalArgumentException("list must not be empty");
        items = List.copyOf(items);  // defensive copy + immutable
    }
    public T head() { return items.get(0); }  // safe
}
```

---

## Technique 6: Typestate Pattern (State Machines as Types)

Encode valid state transitions in the type system so invalid transitions are compile errors, not runtime checks.

### Go (phantom types + generics)
```go
type Open   struct{}
type Closed struct{}

type Connection[State any] struct{ addr string }

func NewConnection(addr string) Connection[Closed] { return Connection[Closed]{addr} }

// Only a closed connection can be opened
func (c Connection[Closed]) Open() (Connection[Open], error) {
    // ... dial
    return Connection[Open]{c.addr}, nil
}

// Only an open connection can query
func (c Connection[Open]) Query(sql string) (*Rows, error) { ... }

// Only an open connection can close
func (c Connection[Open]) Close() Connection[Closed] { return Connection[Closed]{c.addr} }

// c.Query(sql)  ← compile error if c is Connection[Closed]
```

### Java (sealed interfaces for states)
```java
// Each state is a distinct type; transitions return new types
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

---

## Technique 7: Parse at the Boundary, Trust Internally

Validate and parse **once** at the system boundary (HTTP handler, CLI input, message consumer). Inside the system, pass proven types — no re-validation.

```
┌──────────────────────────────────────────────────────────┐
│  Boundary: HTTP handler / CLI / message consumer          │
│  Raw string → Email.parse(s) → Email                     │
│  Raw int    → PositiveInt.of(n) → PositiveInt            │
│  Returns error/400 if invalid                            │
├──────────────────────────────────────────────────────────┤
│  Application Service  (receives Email, PositiveInt)       │
│  No validation — types prove it's already done            │
├──────────────────────────────────────────────────────────┤
│  Domain (Order, User, Money)                             │
│  Types enforce invariants; no defensive checks            │
└──────────────────────────────────────────────────────────┘
```

---

## Anti-Patterns to Fix

| Smell | Technique |
|-------|-----------|
| `func f(from, to string)` — easy to swap args | Newtypes: `UserID`, `AccountID` |
| `status == "pending"` — magic strings | Sum types: `Pending{}`, `sealed interface` |
| `amount float64` in domain code | Value Object: `Money` with currency |
| Validation in every function that receives `string` | Parse at boundary, pass `Email` internally |
| `items []Item` that must be non-empty | Refinement type: `NonEmptySlice[Item]` |
| `*string` / `*int` optional fields everywhere | Explicit optional type or sum type |
| `isValid()` method on mutable struct | Smart constructor: validity is construction-time |
| `status: "confirmed"` parsed from JSON everywhere | Discriminated union with `Literal` / sealed class |

---

## Decision Guide

| Problem | Solution |
|---------|----------|
| Two primitives of same type mixed up | Newtype / phantom type |
| Invalid string values accepted silently | Sum type / enum / sealed interface |
| Invariant validated in multiple places | Smart constructor + parse at boundary |
| Domain concept represented as primitive | Value Object |
| State transition permitted when it shouldn't be | Typestate pattern |
| Empty collection causes crashes | Refinement type (`NonEmptyList`) |
| Null-checking everywhere | Explicit option type / require non-null in constructor |
| Business rule in caller, not in type | Move rule into the type's constructor |

---

## Composing with Domain Patterns

Type-driven design integrates directly with DDD (see `design-patterns` skill):

```
Order {
    id:     OrderID          ← newtype, not UUID directly
    status: OrderStatus      ← sum type, not string
    total:  Money            ← value object, not float64
    items:  NonEmptyList[Item] ← refinement type, not []Item
}
```

Every field carries a proof. A valid `Order` instance means all these invariants hold — no defensive checks needed anywhere Order is used.

---

## References
- *Parse, Don't Validate* — Alexis King (lexi-lambda.github.io/blog/2019/11/05)
- *Domain Modeling Made Functional* — Scott Wlaschin (Pragmatic Programmers)
- *Designing with Types* series — F# for Fun and Profit (fsharpforfunandprofit.com)
- *Making Impossible States Impossible* — Richard Feldman (elm-conf 2016)
- *Type-Driven Development* — Mark Seemann (blog.ploeh.dk)
- *Patterns of Enterprise Application Architecture* — Martin Fowler (Value Object chapter)
