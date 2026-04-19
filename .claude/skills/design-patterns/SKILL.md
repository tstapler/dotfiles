---
name: design-patterns
description: Apply design patterns from Gang of Four (GoF) and Patterns of Enterprise Application Architecture (Fowler/PoEAA). Use when structuring new code, evaluating design decisions, or identifying the right pattern for a problem. Covers when to use, when to avoid, and Go-idiomatic implementations.
---

# Design Patterns

Apply patterns from two authoritative sources:
- **GoF**: *Design Patterns* — Gamma, Helm, Johnson, Vlissides
- **PoEAA**: *Patterns of Enterprise Application Architecture* — Martin Fowler

**Key principle**: patterns describe solutions to recurring problems — use them when the problem recurs, not to demonstrate pattern knowledge. In Go, first-class functions and interfaces make several GoF patterns unnecessary or simpler than in OOP languages.

---

## GoF Creational Patterns

### Factory Method / Abstract Factory
**Problem**: Create objects without hardcoding concrete types; decouple creation from use.
```go
func NewReader(format string) Reader {
    switch format {
    case "json": return &JSONReader{}
    case "xml":  return &XMLReader{}
    default:     return &TextReader{}
    }
}
```
- **Use when**: multiple concrete types implement the same interface; creation logic varies by context
- **Avoid when**: only one concrete type exists (just use a direct constructor)
- **Go note**: return interfaces, not concrete types; constructor functions are more idiomatic than factory objects

### Builder / Functional Options
**Problem**: Construct complex objects step-by-step, managing many optional parameters cleanly.
```go
// Idiomatic Go: functional options
type Option func(*Server)

func WithTimeout(d time.Duration) Option { return func(s *Server) { s.timeout = d } }
func WithLogger(l Logger) Option         { return func(s *Server) { s.logger = l } }

func NewServer(addr string, opts ...Option) *Server {
    s := &Server{addr: addr}
    for _, o := range opts { o(s) }
    return s
}
```
- **Use when**: many optional/conditional parameters; complex validation at construction time
- **Avoid when**: 1–2 parameters (use a direct constructor)
- **Go note**: functional options (`func New(opts ...Option)`) are more idiomatic than a fluent builder chain

### Singleton
**Problem**: Ensure exactly one instance with thread-safe initialization.
```go
var once sync.Once
var instance *DB

func GetDB() *DB {
    once.Do(func() { instance = connect() })
    return instance
}
```
- **Use when**: coordinating a shared resource that genuinely must be singular
- **Avoid when**: dependency injection can pass the instance instead (almost always preferred — singletons hurt testability)
- **Go note**: treat `sync.Once` as the implementation mechanism, not a design goal

---

## GoF Structural Patterns

### Adapter
**Problem**: Bridge two incompatible interfaces without modifying either.
```go
type PaymentProcessor interface { Process(amount float64) error }

type PaymentAdapter struct{ gateway *LegacyGateway }
func (a *PaymentAdapter) Process(amount float64) error { return a.gateway.Pay(amount) }
```
- **Use when**: integrating third-party/legacy code with an incompatible interface
- **Avoid when**: you can modify the source; adds indirection for no benefit

### Decorator / Middleware
**Problem**: Add behavior (logging, auth, caching) to objects/functions dynamically without modifying them.
```go
func Logging(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        log.Printf("%s %s", r.Method, r.URL)
        next.ServeHTTP(w, r)
    })
}
```
- **Use when**: cross-cutting concerns (logging, auth, caching, rate-limiting); composing behaviors at runtime
- **Avoid when**: decorator chain becomes too deep to reason about
- **Go note**: HTTP middleware is the canonical idiomatic form — function returning function is more natural than object wrapping object

### Facade
**Problem**: Provide a single simplified interface to a complex subsystem.
```go
// Well-designed package API is Go's natural facade
func (s *Store) FindUser(ctx context.Context, id int) (*User, error) {
    if u, ok := s.cache.Get(id); ok { return u, nil }
    u, err := s.repo.GetByID(ctx, id)
    if err != nil { return nil, err }
    s.cache.Set(id, u)
    return u, nil
}
```
- **Use when**: clients need one entry point to a complex set of collaborators
- **Avoid when**: facade becomes as complex as the subsystem; hiding things doesn't simplify them

### Proxy
**Problem**: Control access to an object — lazy init, auth checks, logging, remote calls.
- **Use when**: expensive resource that should be created lazily; transparent access control
- **Go note**: often implemented as middleware or a struct that wraps the real type and implements the same interface

### Composite
**Problem**: Treat individual objects and tree-structured compositions uniformly.
```go
type Node interface { Size() int64 }

type File struct{ size int64 }
func (f *File) Size() int64 { return f.size }

type Dir struct{ children []Node }
func (d *Dir) Size() int64 {
    var total int64
    for _, c := range d.children { total += c.Size() }
    return total
}
```
- **Use when**: tree structures (file systems, UI component trees, expression trees)
- **Go note**: a slice of interface types is the idiomatic composite

---

## GoF Behavioral Patterns

### Strategy
**Problem**: Swap interchangeable algorithms at runtime without changing the calling code.
```go
// Idiomatic: use a function type, not a Strategy interface
type SortFunc func([]int)

type Sorter struct{ fn SortFunc }
func (s *Sorter) Sort(data []int) { s.fn(data) }
```
- **Use when**: multiple algorithms for the same task chosen at runtime; replacing large if-else chains
- **Go note**: function types are more idiomatic than a one-method strategy interface

### Observer
**Problem**: Notify multiple dependents when an object's state changes.
```go
// Idiomatic: channels
type Bus struct{ listeners []chan Event }

func (b *Bus) Publish(e Event) {
    for _, ch := range b.listeners {
        go func(c chan Event) { c <- e }(ch)
    }
}
```
- **Use when**: decoupling event producers from consumers; one-to-many notifications
- **Go note**: channels and goroutines replace traditional observer objects

### Command
**Problem**: Encapsulate a request as an object for queueing, scheduling, or undo.
```go
// Idiomatic: first-class functions
type Command func() error

queue := []Command{
    func() error { return step1() },
    func() error { return step2() },
}
for _, cmd := range queue { if err := cmd(); err != nil { return err } }
```
- **Use when**: undo/redo, command queues, macro recording
- **Go note**: closures eliminate the need for Command objects in most cases

### Template Method
**Problem**: Define an algorithm's skeleton; let implementations fill in specific steps.
```go
type Processor interface {
    Validate([]byte) error
    Parse([]byte) (interface{}, error)
    Process(interface{}) error
}

func Run(p Processor, data []byte) error {
    if err := p.Validate(data); err != nil { return err }
    parsed, err := p.Parse(data)
    if err != nil { return err }
    return p.Process(parsed)
}
```
- **Use when**: multiple related types share an algorithm structure but differ in steps
- **Go note**: Go uses interfaces + a free function (like `Run` above) rather than abstract base classes

### Chain of Responsibility
**Problem**: Pass a request along a handler chain until one handles it.
```go
// Idiomatic: function composition
type Middleware func(http.Handler) http.Handler

func Chain(h http.Handler, mws ...Middleware) http.Handler {
    for i := len(mws) - 1; i >= 0; i-- { h = mws[i](h) }
    return h
}
```
- **Use when**: validation pipelines, middleware stacks, multi-stage processing
- **Go note**: HTTP middleware IS chain of responsibility — function composition is the idiomatic form

### State
**Problem**: Alter an object's behavior based on its internal state; eliminate large state-checking conditionals.
```go
type State interface{ Next(ctx *FSM) State }

type Pending struct{}
func (s *Pending) Next(f *FSM) State {
    if f.ready { return &Running{} }
    return s
}
```
- **Use when**: distinct behaviors per state with clear transition rules; replacing large state-flag conditionals
- **Avoid when**: 2–3 states (a simple switch is clearer)

---

## PoEAA Patterns

### Repository *(most important PoEAA pattern)*
**Problem**: Decouple domain logic from data access; provide a collection-like interface to persistence.
```go
// Define the interface in the domain layer
type UserRepository interface {
    GetByID(ctx context.Context, id int) (*User, error)
    Save(ctx context.Context, user *User) error
    Delete(ctx context.Context, id int) error
}

// Implement in infrastructure layer
type sqlUserRepository struct{ db *sql.DB }
func (r *sqlUserRepository) GetByID(ctx context.Context, id int) (*User, error) { ... }
```
- **Use when**: almost always, unless the app is pure CRUD with no business logic
- **Critical rule**: define the interface in the domain layer; implement in infrastructure
- **Go note**: enables swapping real DB with in-memory implementation for tests — the key testability win

### Unit of Work
**Problem**: Coordinate multiple repositories within a single atomic transaction.
```go
type UoW struct{ tx *sql.Tx }

func (u *UoW) UserRepo() UserRepository   { return &txUserRepo{u.tx} }
func (u *UoW) OrderRepo() OrderRepository { return &txOrderRepo{u.tx} }
func (u *UoW) Commit() error              { return u.tx.Commit() }
func (u *UoW) Rollback() error            { return u.tx.Rollback() }
```
- **Use when**: multiple aggregates must be saved atomically in one transaction
- **Avoid when**: single-aggregate transactions (just use the repository directly)

### Data Mapper vs. Active Record
| | Data Mapper | Active Record |
|--|-------------|---------------|
| **Structure** | Separate mapper/repository | Persistence on the domain object itself |
| **Complexity** | Higher | Lower |
| **Testability** | High (mock the mapper) | Low (coupled to DB) |
| **Use when** | Complex business logic; large systems | Simple CRUD; prototypes |

- **Go default**: prefer Data Mapper (repository pattern) — Active Record couples domain objects to the DB, violating separation of concerns

### Service Layer
**Problem**: Define application boundaries; coordinate domain objects and infrastructure to implement use cases.
```go
type OrderService struct {
    orders   OrderRepository
    payments PaymentService
    events   EventBus
}

func (s *OrderService) PlaceOrder(ctx context.Context, cmd PlaceOrderCmd) (*Order, error) {
    order := domain.NewOrder(cmd.CustomerID, cmd.Items)
    if err := s.payments.Reserve(ctx, order.Total()); err != nil {
        return nil, fmt.Errorf("reserve payment: %w", err)
    }
    if err := s.orders.Save(ctx, order); err != nil {
        return nil, fmt.Errorf("save order: %w", err)
    }
    s.events.Publish(OrderPlaced{OrderID: order.ID})
    return order, nil
}
```
- **Use when**: use case involves multiple domain objects or infrastructure services
- **Avoid when**: service becomes a thin pass-through wrapper — that's an anemic service layer
- **Rule**: no business logic in service layer; it orchestrates, domain objects decide

### Domain Model
**Problem**: Encapsulate complex business logic in rich domain objects with behaviour.
```go
type Order struct {
    id     OrderID
    items  []Item
    status Status
}

func (o *Order) AddItem(item Item) error {
    if o.status != Pending {
        return fmt.Errorf("cannot add to %s order", o.status)
    }
    o.items = append(o.items, item)
    return nil
}

func (o *Order) Complete() error {
    if len(o.items) == 0 { return errors.New("empty order") }
    o.status = Completed
    return nil
}
```
- **Use when**: complex business rules; multiple use cases interact with the same concepts
- **Avoid when**: pure data/CRUD with minimal logic (overkill — use Transaction Script)
- **Anti-pattern to avoid**: anemic domain model — structs with only getters/setters and all logic in services

### Transaction Script
**Problem**: Organize each business operation as a simple procedural function.
```go
func ProcessOrder(ctx context.Context, db *sql.DB, orderID int) error {
    order, err := loadOrder(db, orderID)
    if err != nil { return err }
    if err := chargeCard(ctx, order.CardToken, order.Total); err != nil { return err }
    if err := updateInventory(db, order.Items); err != nil { return err }
    return markComplete(db, orderID)
}
```
- **Use when**: straightforward procedural logic; simple CRUD; getting started quickly
- **When to migrate**: when logic is duplicated across scripts or complexity grows — transition to Domain Model

### Value Object
**Problem**: Represent domain concepts as immutable, equality-by-value objects.
```go
type Money struct {
    amount   int64  // cents — unexported
    currency string
}

func NewMoney(cents int64, currency string) (Money, error) {
    if cents < 0 { return Money{}, errors.New("negative amount") }
    return Money{cents, currency}, nil
}

func (m Money) Add(other Money) (Money, error) {
    if m.currency != other.currency { return Money{}, errors.New("currency mismatch") }
    return Money{m.amount + other.amount, m.currency}, nil
}
```
- **Use when**: small immutable concepts with no identity (Money, Coordinates, DateRange, EmailAddress)
- **Go note**: unexported fields + value receivers + returning new instances = correct immutability pattern
- **Critical**: prefer `Money` over `float64` for domain currency — the type encodes constraints the compiler can check

### Registry
**Problem**: Central lookup for objects by type/name without coupling to creation.
```go
var handlers = map[string]EventHandler{}
func Register(eventType string, h EventHandler) { handlers[eventType] = h }
```
- **Use when**: plugin systems; event routing; driver registration (like `database/sql`)
- **Avoid when**: simple dependency injection would work — registries create hidden dependencies that hurt testability
- **Go note**: `init()` + registry is the standard `database/sql` driver pattern; use sparingly

---

## Decision Guide

| Problem | Pattern | Go Idiom |
|---------|---------|----------|
| Create without specifying concrete type | Factory | Constructor func returning interface |
| Many optional parameters | Builder | Functional options `...Option` |
| Incompatible interfaces | Adapter | Struct composition |
| Cross-cutting concerns | Decorator | Middleware func |
| Simplify complex subsystem | Facade | Clean package API |
| Swappable algorithms | Strategy | Function type |
| One-to-many event notification | Observer | Channels |
| Request queueing / undo | Command | `func() error` closures |
| Tree structures | Composite | `[]Interface` |
| State-dependent behavior | State | State interface with `Next()` |
| Request pipelines | Chain of Responsibility | Middleware composition |
| Data access abstraction | Repository | Interface in domain, impl in infra |
| Multi-repo transactions | Unit of Work | Shared `*sql.Tx` |
| Complex business logic | Domain Model | Rich entities with methods |
| Simple procedural operations | Transaction Script | Plain functions |
| Identity-less domain concepts | Value Object | Immutable struct, value receivers |

---

## Go Idioms That Replace GoF Patterns

| GoF Pattern | Go Replacement |
|-------------|---------------|
| Command | `func() error` closures |
| Strategy | Function types as fields |
| Iterator | `range` built-in |
| Observer | Channels + goroutines |
| Template Method | Interface + free function |
| Singleton | `sync.Once` (but prefer DI) |
| Abstract Factory | Constructor functions returning interfaces |

---

## References
- *Design Patterns: Elements of Reusable Object-Oriented Software* — Gamma, Helm, Johnson, Vlissides (GoF)
- *Patterns of Enterprise Application Architecture* — Martin Fowler
- PoEAA catalog: martinfowler.com/eaaCatalog
