# Maximizing Go's Type System

Beyond primitive obsession (see [Type-Driven Design Patterns](type-driven-design-patterns.md)), these are the core Go-specific techniques for getting real leverage out of the type system.

## Pointer vs Value Receivers — Pick One Semantic Per Type

Value receivers copy; pointer receivers share and can mutate. Choose one per type and use it
for every method on that type — never mix them:

```go
// Value semantics: Point is small and safe to copy
type Point struct{ X, Y int }
func (p Point) Add(other Point) Point { return Point{p.X + other.X, p.Y + other.Y} }

// Pointer semantics: Buffer holds mutable, potentially large state
type Buffer struct{ data []byte }
func (b *Buffer) Write(p []byte) (int, error) { b.data = append(b.data, p...); return len(p), nil }
```

Rule of thumb: value receivers for small, immutable, comparable types; pointer receivers once
the type has mutable state or is expensive to copy.

## Struct Embedding for Composition, Never Inheritance

Embedding promotes an embedded type's methods and fields to the outer type, but the embedded
type has no idea it's embedded — this is composition, not a base class:

```go
type Reader struct{ r io.Reader }
type Logger struct{ log *slog.Logger }

// LoggingReader embeds both — Read() and Log() are promoted onto it, but
// neither Reader nor Logger knows LoggingReader exists
type LoggingReader struct {
    Reader
    Logger
}
```

If a promoted method ever needs overriding to "fix" the embedded type's behavior, that's the
signal that inheritance-shaped thinking crept in — prefer holding the type as a named field and
forwarding only the specific calls you need, rather than embedding for the override.

## `iota` for Typed Enums

Go has no `enum` keyword — a distinct type plus `iota` is the idiomatic replacement for magic
strings or ints:

```go
type Level int

const (
    LevelDebug Level = iota
    LevelInfo
    LevelWarn
    LevelError
)

func (l Level) String() string {
    return [...]string{"debug", "info", "warn", "error"}[l]
}
```

The distinct `Level` type — not a bare `int` — is what makes this a compile-time guarantee:
nothing can pass an arbitrary int where a `Level` is expected, the same protection a newtype
gives (see [Type-Driven Design Patterns](type-driven-design-patterns.md)).

## Generics: Constraints Document Intent

A type parameter's constraint is documentation the compiler enforces — pick the narrowest
constraint that expresses what the function actually needs:

```go
type Ordered interface {
    ~int | ~int64 | ~float64 | ~string
}

func Max[T Ordered](a, b T) T {
    if a > b {
        return a
    }
    return b
}
```

Reach for `comparable` when the function only needs `==`/`!=` (map keys, `slices.Contains`),
and a custom constraint like `Ordered` when it needs `<`/`>`. Don't reach for generics at all
when a concrete type or a five-line loop covers the one call site you actually have — see
"Concrete-First Design" in the main skill.

## Struct Tags at Serialization Boundaries

Struct tags describe how a type maps to an external wire format — keep them at the boundary,
not leaking into domain logic:

```go
type UserDTO struct {
    ID    string `json:"id"`
    Email string `json:"email"`
}
```

Parse a `UserDTO` into a domain `Email`/`UserID` (see [Type-Driven Design Patterns](type-driven-design-patterns.md))
immediately after unmarshaling. Tags describe the wire format; the domain model stays tag-free.
