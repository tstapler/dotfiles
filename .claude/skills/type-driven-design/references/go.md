# Type-Driven Design — Go Examples

Worked Go examples for every technique in the main `SKILL.md`.

## Technique 1: Newtypes (Branded / Opaque Types)

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

## Technique 2: Smart Constructors

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

## Technique 3: Sum Types (Make Invalid States Unrepresentable)

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

## Technique 4: Value Objects

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

## Technique 5: Refinement Types (Constrained Primitives)

```go
type NonEmptySlice[T any] struct{ items []T }

func NewNonEmptySlice[T any](items ...T) (NonEmptySlice[T], error) {
    if len(items) == 0 { return NonEmptySlice[T]{}, errors.New("must not be empty") }
    return NonEmptySlice[T]{items: items}, nil
}

func (s NonEmptySlice[T]) Head() T { return s.items[0] }  // safe — proven non-empty
```

## Technique 6: Typestate Pattern (State Machines as Types)

Phantom types + generics:
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
