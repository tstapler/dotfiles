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

```go
// Bad: both are strings — compiler accepts swapping them
func Transfer(fromID, toID string, amount float64) error

// Good: distinct types
type UserID string
type AccountID string
type Cents int64

func Transfer(from AccountID, to AccountID, amount Cents) error
```

Use `type Foo string` (new type), never `type Foo = string` (alias — no protection). Phantom types with generics (`ID[T any]`) prevent cross-entity ID confusion at compile time (e.g. passing an `OrderID` where a `UserID` is expected).

Full Go/Python/Java examples, including phantom-typed IDs and Pydantic `NewType` equivalents: [references/go.md](references/go.md#technique-1-newtypes-branded--opaque-types), [references/python.md](references/python.md#technique-1-newtypes-branded--opaque-types), [references/java.md](references/java.md#technique-1-newtypes-branded--opaque-types).

---

> For Pydantic-based smart constructors and Python type annotations, apply the `python-development` skill.

## Technique 2: Smart Constructors

Private constructor + public factory function. The factory validates; holding the type proves validity.

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

Full examples (Python dataclass + Pydantic `field_validator`, Java private-constructor record): [references/go.md](references/go.md#technique-2-smart-constructors), [references/python.md](references/python.md#technique-2-smart-constructors), [references/java.md](references/java.md#technique-2-smart-constructors).

---

## Technique 3: Sum Types (Make Invalid States Unrepresentable)

Model mutually exclusive states as distinct types. The compiler enforces exhaustive handling.

```go
// Bad: magic strings, typos compile fine
type Order struct { Status string }

// Good: interface + unexported marker method seals the set
type OrderStatus interface{ orderStatus() }

type Pending   struct{}
type Confirmed struct{}

func (Pending) orderStatus()   {}
func (Confirmed) orderStatus() {}

// Exhaustive switch (add default to catch future states)
func describeStatus(s OrderStatus) string {
    switch s.(type) {
    case Pending:   return "awaiting confirmation"
    case Confirmed: return "confirmed"
    default:        panic(fmt.Sprintf("unknown status %T", s))
    }
}
```

Full examples (Go interface+marker method with state transitions, Python 3.10+ `match`/Pydantic discriminated unions, Java 17+ sealed interfaces with exhaustive `switch`): [references/go.md](references/go.md#technique-3-sum-types-make-invalid-states-unrepresentable), [references/python.md](references/python.md#technique-3-sum-types-make-invalid-states-unrepresentable), [references/java.md](references/java.md#technique-3-sum-types-make-invalid-states-unrepresentable).

---

## Technique 4: Value Objects

Small, immutable, equality-by-value objects that enforce their own invariants. The type eliminates the need to validate domain concepts downstream.

### Key Properties
1. **Immutable** — operations return new instances
2. **Self-validating** — constructor rejects invalid state
3. **Equality by value** — two instances with same data are equal
4. **No identity** — not distinguished by ID

```go
type Money struct {
    cents    int64  // unexported
    currency string
}

func NewMoney(amount float64, currency string) (Money, error) {
    if amount < 0 { return Money{}, errors.New("amount cannot be negative") }
    return Money{cents: int64(math.Round(amount * 100)), currency: currency}, nil
}
```

Full examples (Go with `Add`/`Equal` methods, Python frozen dataclass, Java record with defensive validation): [references/go.md](references/go.md#technique-4-value-objects), [references/python.md](references/python.md#technique-4-value-objects), [references/java.md](references/java.md#technique-4-value-objects).

---

## Technique 5: Refinement Types (Constrained Primitives)

Types that carry a proof of a constraint — `NonEmptyList`, `PositiveInt`, `EmailAddress`.

```go
type NonEmptySlice[T any] struct{ items []T }

func NewNonEmptySlice[T any](items ...T) (NonEmptySlice[T], error) {
    if len(items) == 0 { return NonEmptySlice[T]{}, errors.New("must not be empty") }
    return NonEmptySlice[T]{items: items}, nil
}

func (s NonEmptySlice[T]) Head() T { return s.items[0] }  // safe — proven non-empty
```

Full examples (Go generic wrapper, Python Pydantic `Field(min_length=1)`, Java record with defensive copy): [references/go.md](references/go.md#technique-5-refinement-types-constrained-primitives), [references/python.md](references/python.md#technique-5-refinement-types-constrained-primitives), [references/java.md](references/java.md#technique-5-refinement-types-constrained-primitives).

---

## Technique 6: Typestate Pattern (State Machines as Types)

Encode valid state transitions in the type system so invalid transitions are compile errors, not runtime checks.

```go
// Go: phantom types + generics
type Open   struct{}
type Closed struct{}

type Connection[State any] struct{ addr string }

func (c Connection[Closed]) Open() (Connection[Open], error) { /* ... dial */ }
func (c Connection[Open]) Query(sql string) (*Rows, error)   { ... }

// c.Query(sql)  ← compile error if c is Connection[Closed]
```

Full examples (Go phantom-typed connection, Java sealed-interface order states where each transition returns a new type): [references/go.md](references/go.md#technique-6-typestate-pattern-state-machines-as-types), [references/java.md](references/java.md#technique-6-typestate-pattern-state-machines-as-types).

---

> For enforcing parse-at-boundary with Spring Boot `@RequestBody` validation, apply the `code-spring-boot` skill.

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

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `design-patterns` | Selecting GoF/PoEAA patterns that type-driven design encodes (Value Object, State) |
| `code-spring-boot` | Java-specific type techniques: records, sealed interfaces, parse at Spring boundaries |
| `python-development` | Python newtypes, Pydantic smart constructors, frozen dataclasses |
| `golang-development` | Go newtype, phantom generics, unexported-field Value Objects |
| `code-refactoring` | Automated refactors to replace primitive obsession across a codebase |
| `code-review` | Identifying primitive obsession, missing smart constructors, or magic strings in PRs |

## References
- *Parse, Don't Validate* — Alexis King (lexi-lambda.github.io/blog/2019/11/05)
- *Domain Modeling Made Functional* — Scott Wlaschin (Pragmatic Programmers)
- *Designing with Types* series — F# for Fun and Profit (fsharpforfunandprofit.com)
- *Making Impossible States Impossible* — Richard Feldman (elm-conf 2016)
- *Type-Driven Development* — Mark Seemann (blog.ploeh.dk)
- *Patterns of Enterprise Application Architecture* — Martin Fowler (Value Object chapter)
