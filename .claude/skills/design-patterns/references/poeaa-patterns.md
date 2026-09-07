# PoEAA Patterns

> For Spring Boot Java implementations of these patterns (Repository, Data Mapper, Service Layer), apply the `code-spring-boot` skill.

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
