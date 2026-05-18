# Architecture: Project Structure & Hexagonal Architecture

## Project Structure

### `src/` Layout (Required for Installable Packages)

```
my-project/
├── src/
│   └── mypackage/
│       ├── __init__.py        # explicit __all__ = [...]
│       ├── domain/
│       │   ├── model.py       # pure dataclasses, value objects — NO I/O
│       │   └── events.py      # frozen dataclasses for domain events
│       ├── ports/
│       │   └── repository.py  # Protocol definitions
│       ├── service_layer/
│       │   └── handlers.py    # thin orchestration
│       ├── adapters/
│       │   └── repository.py  # concrete SqlAlchemy/etc. implementations
│       └── entrypoints/
│           └── api.py         # wires adapters; composition root
├── tests/
│   ├── conftest.py
│   ├── unit/                  # domain + service_layer; fakes only
│   ├── integration/           # adapters against real DB (testcontainers)
│   └── e2e/                   # entrypoints; full stack
├── pyproject.toml
└── README.md
```

**Why `src/`**: flat layout lets `import mypackage` succeed from project root even when uninstalled, masking packaging bugs. The `src/` layout prevents this — only the installed (or editable-installed) copy is importable.

**`__init__.py` — explicit public surface:**
```python
from mypackage.core import Client, Config
from mypackage.exceptions import MyPackageError

__all__ = ["Client", "Config", "MyPackageError"]
```

---

## Hexagonal Architecture (Ports & Adapters)

> For deeper SOLID, Clean Architecture, and DDD guidance beyond Python specifics, apply the `code-architecture-best-practices` skill.

The domain core has **zero imports** of infrastructure. All I/O crosses a boundary defined by a `Protocol`. Concrete implementations live outside the core and are injected at the application boundary.

```
    ┌──────────────────────────────────┐
    │  domain/ (pure: no I/O, no now())│
    │  service_layer/ (orchestration)  │
    │  ports/ (Protocol definitions)   │
    └───────────┬──────────────────────┘
                │  structural Protocol
       ┌────────┴────────┐
  adapters/db/      adapters/email/
  SqlRepo            SmtpNotifier
```

### Ports as `Protocol` — structural, no forced inheritance

```python
# ports/repository.py
from typing import Protocol
from domain.model import Order, OrderId

class OrderRepository(Protocol):
    def get(self, order_id: OrderId) -> Order: ...
    def add(self, order: Order) -> None: ...
    def list_pending(self) -> list[Order]: ...
```

### Service Layer — thin orchestration, no business logic

```python
# service_layer/handlers.py
def ship_order(
    order_id: OrderId,
    repo: OrderRepository,     # port — never a concrete type
    notifier: Notifier,
    clock: Callable[[], datetime] = datetime.now,  # inject non-determinism
) -> None:
    order = repo.get(order_id)
    order.mark_shipped(shipped_at=clock())  # domain carries the logic
    repo.add(order)
    notifier.notify_shipped(order)
```

**Rule**: if `ship_order` has a branch that isn't about orchestration flow, that logic belongs in `order.mark_shipped()`.

### Domain Model — no I/O, no `datetime.now()`, no `random`

```python
# domain/model.py
@dataclass
class Order:
    id: OrderId
    status: str = "pending"
    events: list = field(default_factory=list)

    def mark_shipped(self, shipped_at: datetime) -> None:
        if self.status != "pending":
            raise InvalidTransitionError(f"Cannot ship order in {self.status!r}")
        self.status = "shipped"
        self.events.append(OrderShipped(self.id, shipped_at))
```

### Composition Root — wire at one place

```python
# entrypoints/api.py — only place that imports concrete adapters
engine = create_engine(settings.db.url)
Session = sessionmaker(bind=engine)

def get_handler():
    session = Session()
    return handlers.ship_order(
        repo=SqlAlchemyOrderRepository(session),
        notifier=SmtpNotifier(host=settings.smtp_host),
    )
```

Never import concrete adapters inside domain or service layer code.
