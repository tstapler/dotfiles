# Type-Driven Design Patterns (Avoiding Primitive Obsession)

Apply these techniques to encode invariants directly into Go's type system so illegal states
are unrepresentable. Full cross-language coverage (Python, Java) lives in the
`type-driven-design` skill — this file is the Go-specific implementation of each.

## Newtypes

Give domain concepts their own type instead of passing raw primitives, so the compiler
catches parameter mixups:

```go
type UserID string
type AccountID string
type Cents int64

func Transfer(from, to AccountID, amount Cents) error { /* ... */ return nil }
```

Use `type Foo string` (a distinct type), never `type Foo = string` (an alias — no
type-checking protection).

## Phantom Types (Cross-Entity ID Safety)

```go
type ID[T any] string // T only exists at compile time, never at runtime

type User struct{}
type Order struct{}

type UserID = ID[User]
type OrderID = ID[Order]

func GetUser(id UserID) (*User, error) { return nil, nil }
// GetUser(orderID) is a compile error — UserID and OrderID are distinct types
```

## Smart Constructors

An unexported underlying type plus an exported parsing function — holding the type proves
the value was already validated. The validation itself can be a format check:

```go
type Email string // representation is unexported; can't be constructed directly from another package

func ParseEmail(s string) (Email, error) {
    if !emailRegex.MatchString(s) {
        return "", fmt.Errorf("invalid email %q", s)
    }
    return Email(s), nil
}

// Callers holding an Email never need to re-validate it
func SendWelcome(to Email) { /* ... */ }
```

...or just a presence check, which is all a non-empty ID needs — the type still stops an
empty string, and a distinct type per entity still stops parameter mixups:

```go
type UserID string

func NewUserID(s string) (UserID, error) {
    if s == "" {
        return "", errors.New("user ID cannot be empty")
    }
    return UserID(s), nil
}

// A UserID can only exist via NewUserID — an empty one can never reach this function
func GetUser(id UserID) (*User, error) { /* ... */ return nil, nil }
```

## Sum Types (Closed State Sets)

An unexported marker method seals the set of implementations; a `switch` on the concrete
type enforces exhaustive handling instead of comparing magic strings:

```go
type OrderStatus interface{ orderStatus() }

type Pending   struct{}
type Confirmed struct{}
type Shipped   struct{}
type Cancelled struct{}

func (Pending) orderStatus()   {}
func (Confirmed) orderStatus() {}
func (Shipped) orderStatus()   {}
func (Cancelled) orderStatus() {}

func (o *Order) Confirm() error {
    if _, ok := o.Status.(Pending); !ok {
        return fmt.Errorf("can only confirm a pending order, got %T", o.Status)
    }
    o.Status = Confirmed{}
    return nil
}
```

## Value Objects

Immutable, self-validating, equality-by-value types for domain concepts like money — see
`Money` in `type-driven-design` for the full pattern:

```go
type Money struct {
    cents    int64
    currency string
}

func NewMoney(amount float64, currency string) (Money, error) {
    if amount < 0 {
        return Money{}, errors.New("amount cannot be negative")
    }
    return Money{cents: int64(math.Round(amount * 100)), currency: currency}, nil
}

func (m Money) Add(other Money) (Money, error) {
    if m.currency != other.currency {
        return Money{}, errors.New("currency mismatch")
    }
    return Money{cents: m.cents + other.cents, currency: m.currency}, nil
}
```

## Refinement Types

A type that carries proof of a constraint, such as non-emptiness, so downstream code needs
no defensive check:

```go
type NonEmptySlice[T any] struct{ items []T }

func NewNonEmptySlice[T any](items ...T) (NonEmptySlice[T], error) {
    if len(items) == 0 {
        return NonEmptySlice[T]{}, errors.New("must not be empty")
    }
    return NonEmptySlice[T]{items: items}, nil
}

func (s NonEmptySlice[T]) Head() T { return s.items[0] } // safe — proven non-empty
```

## Typestate Pattern

Encode valid state transitions with phantom generics, so an invalid transition is a compile
error rather than a runtime check:

```go
type Open   struct{}
type Closed struct{}

type Connection[State any] struct{ addr string }

func NewConnection(addr string) Connection[Closed] { return Connection[Closed]{addr} }

func (c Connection[Closed]) Open() (Connection[Open], error) {
    return Connection[Open]{c.addr}, nil // dial happens here
}
func (c Connection[Open]) Query(sql string) (*Rows, error) { return nil, nil }
func (c Connection[Open]) Close() Connection[Closed]        { return Connection[Closed]{c.addr} }
// c.Query(sql) is a compile error if c is Connection[Closed]
```

## Parse at the Boundary, Trust Internally

Validate and parse exactly once at the HTTP/CLI/message boundary; pass the proven type
(`Email`, `UserID`, `Money`) through the rest of the call chain with no re-validation.

**Signs you need this section:** magic string comparisons (`status == "pending"`), functions
that take two `string` parameters that could be swapped, validation logic repeated across
multiple functions, `nil` pointer panics from missing construction checks.
