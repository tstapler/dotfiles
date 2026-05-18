--
name: code-python
description: Apply Python coding standards when writing, reviewing, or debugging Python code. Use for type annotations, package management with uv, Pydantic DTOs, Typer CLIs, pytest patterns, and PEP 8 style guidelines.
---

# Python Development Standards

Apply these standards when writing, reviewing, or debugging Python code.

## Package Management

- **Always use `uv`** for dependency management
- Use `uv install -e .` for development installations
- Use `uv run` for executing scripts with dependencies

## Dependencies Declaration (PEP 723)

```python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests<3",
#   "rich",
# ]
# ///
```

## Type Annotations

Annotate all function arguments and return types. Use **modern syntax** (Python 3.10+):

```python
# Modern: use built-in generics and | for unions
def process(items: list[str], value: int | None = None) -> dict[str, int]: ...

# Anti-pattern: old typing imports (avoid in new code)
# from typing import List, Dict, Optional  ← don't use these
# def process(items: List[str], value: Optional[int] = None) -> Dict[str, int]: ...
```

Use **keyword-only arguments** (after `*`) for clarity at call sites:

```python
def create_task(
    content: str,
    *,  # Everything after is keyword-only
    project_id: str,
    priority: int = 1,
    labels: list[str] | None = None,
) -> Task:
    ...

# Caller must be explicit: create_task("Buy milk", project_id="123", priority=2)
```

## Library Preferences

**Default**: Use built-in libraries for portability in simple scripts.
**With Dependencies**: Always confirm with the user before adding dependencies. Then use:

| Need | Built-in | With Dependencies |
|------|----------|-------------------|
| CLI | `argparse` | `Typer` |
| Data models | `dataclasses` | `Pydantic` |
| String enums | `enum.Enum` | `Literal` |

## Code Style

- Follow PEP 8 with line lengths up to **120 characters**
- Use **Black** for formatting
- Mark unfinished code with `# TODO:` or `# FIXME:`
- Comment only when code isn't self-explanatory
- Write clear docstrings for all public functions and modules:

```python
def calculate_discount(price: float, rate: float = 0.1) -> float:
    """
    Calculate discounted price.

    Args:
        price: Original price in dollars.
        rate: Discount rate between 0 and 1 (default: 0.1).

    Returns:
        Discounted price.
    """
    return price * (1 - rate)
```

## Data Models

Use `dataclasses` (built-in) or `Pydantic` (with dependencies) for DTOs and domain objects.

**With dataclasses** (default, no dependencies):
```python
from dataclasses import dataclass

@dataclass
class UserRequest:
    username: str
    email: str
    age: int | None = None

    def validate(self) -> list[str]:
        errors = []
        if not self.username:
            errors.append("Username is required")
        return errors
```

**With Pydantic** (when dependencies confirmed):
```python
from pydantic import BaseModel, Field
from typing import Literal

class UserRole(str):
    pass

RoleType = Literal["admin", "editor", "viewer"]

class UserRequest(BaseModel):
    """DTO for user creation requests."""
    username: str = Field(..., description="Unique username, 3-32 chars")
    email: str = Field(..., description="Valid email address")
    role: RoleType = Field(default="viewer", description="Access role")
    age: int | None = Field(default=None, description="Age in years, optional")

    @classmethod
    def create(cls, username: str, email: str, role: RoleType = "viewer") -> "UserRequest":
        """Typed constructor for common creation pattern."""
        return cls(username=username, email=email, role=role)
```

## API Clients

Use class-based structures with pagination support:

```python
class APIClient:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout

    def list_items(self, page: int = 1, per_page: int = 100) -> list[Item]:
        pass
```

## Testing with Pytest

Use parametrized tests with descriptive IDs:

```python
from dataclasses import dataclass

@dataclass
class ParseTestCase:
    description: str
    input: str
    expected: dict

test_cases = [
    ParseTestCase("valid json", '{"key": "value"}', {"key": "value"}),
    ParseTestCase("empty json", '{}', {}),
]

@pytest.mark.parametrize("testcase", test_cases, ids=lambda tc: tc.description)
def test_parse_json(testcase):
    result = parse_json(testcase.input)
    assert result == testcase.expected
```

## Error Handling

Define a domain exception hierarchy — never use bare `except:`:

```python
class AppError(Exception):
    """Base exception for all application errors."""

class AuthenticationError(AppError): ...
class NetworkError(AppError): ...
class NotFoundError(AppError): ...

# Use specific exceptions with context chaining
try:
    response = client.get(url)
    response.raise_for_status()
except httpx.TimeoutException as e:
    raise NetworkError(f"Timeout fetching {url}") from e
except httpx.HTTPStatusError as e:
    if e.response.status_code == 404:
        return None  # Expected absence — not exceptional
    raise NetworkError(f"HTTP {e.response.status_code}") from e
```

**When to return `None` vs raise:**
- `find_by_id("x") -> T | None` — lookup that may find nothing
- `raise ValueError` — invalid input that should never happen
- `raise DomainError` — violated business rule

## Code Structure Principles

- **Separation of Concerns**: Isolate UI/IO from business logic to enhance testability
- **Facade Pattern**: For API or networking libraries, implement a facade named `service` (e.g., `GithubService`)
- **Dependency Injection**: Via constructor — never import concrete implementations in domain code
- **DTOs**: Use for function arguments and return values
- **Module `__init__.py`**: Define the public API surface explicitly with `__all__`

## Testing with Benchmarks

For performance-critical code, use `pytest-benchmark`:

```python
import pytest

def test_parse_performance(benchmark):
    result = benchmark(parse_large_file, "sample.csv")
    assert result is not None

# Configure benchmark marks in pyproject.toml:
# [tool.pytest.ini_options]
# markers = ["benchmark: mark test as a benchmark"]
```

Run benchmarks:
```bash
uv run pytest --benchmark-only         # Run only benchmarks
uv run pytest --benchmark-disable      # Skip benchmarks in normal runs
uv run pytest --benchmark-compare      # Compare against saved baseline
```

## Tooling Baseline

Add to `pyproject.toml`:
```toml
[tool.ruff]
line-length = 120
target-version = "py311"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "UP", "B", "SIM", "RUF"]
# UP = pyupgrade (modernizes Optional→X|None, List→list, etc.)

[tool.mypy]
strict = true
warn_return_any = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-xvs"
```

Use `ruff` alongside (or instead of) `flake8` — it also handles import sorting and auto-modernizes old type syntax.

## Type-Driven Design

Apply techniques from the `type-driven-design` skill to encode invariants into Python's type system. See also: `code-architecture-best-practices` for SOLID + Clean Architecture rules that govern where these types live.

**Core Python techniques:**
- `NewType('UserID', str)` — static distinction enforced by mypy; `@dataclass(frozen=True)` for runtime enforcement
- Smart constructors: `@classmethod def of(cls, s: str) -> "Email"` — `__post_init__` validates, raising on invalid input
- Sum types: `@dataclass(frozen=True)` classes per state + `match` (3.10+); or Pydantic discriminated unions with `Literal`
- Value Objects: `@dataclass(frozen=True)` + `__post_init__` — `frozen=True` makes mutation a `TypeError`
- Refinement types: Pydantic `Field(min_length=1, gt=0)` — constraints proven at parse time
- Parse at the boundary: Pydantic models on HTTP/CLI input; pass validated domain objects (`Email`, `Money`) internally

**Signs you need this skill:** `isinstance` checks scattered through functions, `Optional[str]` fields that "must coexist", validation repeated in multiple places, `float` used for currency, `str` used for IDs.

---

## Design Patterns in Python

Apply patterns from the `design-patterns` skill. Below are the idiomatic Python translations. Prefer the Python form over a mechanical OOP translation from Java/C++. For cross-cutting structural decisions (layering, dependency direction, module boundaries), also apply `code-architecture-best-practices`.

### Creational

**Factory** — return `Protocol` implementations from plain functions:
```python
def make_parser(fmt: str) -> Parser:
    match fmt:
        case "json": return JSONParser()
        case "csv":  return CSVParser()
        case _: raise ValueError(f"Unknown format: {fmt}")
```

**Builder / Functional Config** — use `dataclass` with `replace`, or a builder class for complex construction:
```python
from dataclasses import dataclass, replace

@dataclass(frozen=True)
class QueryConfig:
    table: str
    limit: int = 100
    offset: int = 0
    order_by: str | None = None

# Compose config functionally — no mutation
base = QueryConfig(table="orders")
paged = replace(base, limit=20, offset=40)
```

**Singleton** — Python's module system gives you module-level singletons for free; avoid class-based singletons:
```python
# config.py — imported once, shared everywhere
_settings: Settings | None = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```
Prefer dependency injection over module-level globals for testability.

---

### Structural

**Decorator** — Python has first-class decorator syntax; use it for cross-cutting concerns:
```python
import functools

def retry(times: int = 3):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(times):
                try:
                    return fn(*args, **kwargs)
                except Exception:
                    if attempt == times - 1:
                        raise
        return wrapper
    return decorator

@retry(times=3)
def call_api(url: str) -> dict: ...
```

**Adapter** — wrap a third-party/legacy object behind your own Protocol:
```python
from typing import Protocol

class StorageBackend(Protocol):
    def put(self, key: str, data: bytes) -> None: ...
    def get(self, key: str) -> bytes: ...

class S3Adapter:
    def __init__(self, bucket: str) -> None:
        self._client = boto3.client("s3")
        self._bucket = bucket

    def put(self, key: str, data: bytes) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data)

    def get(self, key: str) -> bytes:
        return self._client.get_object(Bucket=self._bucket, Key=key)["Body"].read()
```

**Facade** — a `Service` class that hides subsystem complexity (already in this skill as the `GithubService` pattern):
```python
class NotificationService:
    def __init__(self, email: EmailClient, sms: SMSClient, push: PushClient) -> None:
        self._email, self._sms, self._push = email, sms, push

    def notify_user(self, user: User, message: str) -> None:
        if user.email: self._email.send(user.email, message)
        if user.phone: self._sms.send(user.phone, message)
        if user.device_token: self._push.send(user.device_token, message)
```

---

### Behavioral

**Strategy** — use `Protocol` with a callable, or a plain callable type:
```python
from typing import Protocol

class PricingStrategy(Protocol):
    def calculate(self, base_price: float, quantity: int) -> float: ...

def bulk_discount(base_price: float, quantity: int) -> float:
    return base_price * quantity * (0.9 if quantity > 10 else 1.0)

# Or pass functions directly — no Protocol needed for simple cases
type PricingFn = Callable[[float, int], float]
```

**Observer / Event Bus** — use a simple callback registry:
```python
from collections import defaultdict
from typing import Callable

class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event: str, handler: Callable) -> None:
        self._handlers[event].append(handler)

    def publish(self, event: str, **payload) -> None:
        for handler in self._handlers[event]:
            handler(**payload)
```

**Command** — use callables or `dataclass` + a `execute()` method:
```python
@dataclass
class SendEmailCommand:
    to: str
    subject: str
    body: str

class CommandBus:
    def dispatch(self, cmd: SendEmailCommand) -> None:
        # resolve handler by type
        handler = self._handlers[type(cmd)]
        handler(cmd)
```
For simple cases, just store `Callable[[], None]` in a list and call them.

**Template Method** — use ABC with abstract methods:
```python
from abc import ABC, abstractmethod

class DataPipeline(ABC):
    def run(self, data: bytes) -> None:  # the template
        validated = self.validate(data)
        parsed = self.parse(validated)
        self.store(parsed)

    @abstractmethod
    def validate(self, data: bytes) -> bytes: ...

    @abstractmethod
    def parse(self, data: bytes) -> dict: ...

    @abstractmethod
    def store(self, record: dict) -> None: ...
```

**Chain of Responsibility / Middleware** — compose callables:
```python
type Handler = Callable[[Request], Response]
type Middleware = Callable[[Handler], Handler]

def logging_middleware(next: Handler) -> Handler:
    def handle(req: Request) -> Response:
        print(f"{req.method} {req.path}")
        return next(req)
    return handle

def auth_middleware(next: Handler) -> Handler:
    def handle(req: Request) -> Response:
        if not req.headers.get("Authorization"):
            return Response(status=403)
        return next(req)
    return handle
```

**State** — use a `Protocol` or dataclass per state; return the next state:
```python
from typing import Protocol

class OrderState(Protocol):
    def confirm(self) -> "OrderState": ...
    def ship(self) -> "OrderState": ...
    def cancel(self) -> "OrderState": ...

@dataclass
class PendingState:
    def confirm(self) -> "OrderState": return ConfirmedState()
    def ship(self)    -> "OrderState": raise InvalidTransition("confirm first")
    def cancel(self)  -> "OrderState": return CancelledState()
```

---

### PoEAA Patterns in Python

**Repository** — define with `Protocol` in domain; implement in infrastructure:
```python
class UserRepository(Protocol):
    def get_by_id(self, user_id: str) -> User | None: ...
    def save(self, user: User) -> None: ...
    def delete(self, user_id: str) -> None: ...

class SqlUserRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def get_by_id(self, user_id: str) -> User | None:
        row = self._db.fetchone("SELECT * FROM users WHERE id = %s", user_id)
        return User(**row) if row else None
```

**Value Object** — use `@dataclass(frozen=True)`:
```python
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Currency mismatch")
        return Money(self.amount + other.amount, self.currency)
```

**Service Layer** — thin orchestration, no business logic:
```python
class OrderService:
    def __init__(self, orders: OrderRepository, payments: PaymentGateway) -> None:
        self._orders = orders
        self._payments = payments

    def place_order(self, cmd: PlaceOrderCommand) -> OrderId:
        order = Order.create(cmd.customer_id, cmd.items)
        self._payments.reserve(order.total())
        self._orders.save(order)
        return order.id
```

**Unit of Work** — manage transaction scope explicitly:
```python
class UnitOfWork:
    def __init__(self, session_factory) -> None:
        self._factory = session_factory

    def __enter__(self) -> "UnitOfWork":
        self.session = self._factory()
        self.users = SqlUserRepository(self.session)
        return self

    def __exit__(self, *args) -> None:
        if args[0]:  # exception
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()

# Usage
with UnitOfWork(session_factory) as uow:
    user = uow.users.get_by_id("123")
    user.deactivate()
    uow.users.save(user)
```

---

## Common Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| `Optional[X]` / `List[str]` | `X \| None` / `list[str]` (3.10+) |
| `datetime.utcnow()` | `datetime.now(UTC)` (aware datetime) |
| Bare `except:` | `except SpecificError as e:` |
| `from module import *` | Explicit imports |
| Mutable default arg `def f(x=[])` | `def f(x: list \| None = None)` |
| Business logic in CLI handlers | Extract to service/domain function |
| Returning `None` on error silently | Raise a typed exception |
| `type: ignore` without reason | `type: ignore[specific-code]  # reason` |
| `asyncio.get_event_loop()` | `asyncio.get_running_loop()` inside async |
| `time.sleep()` in async code | `await asyncio.sleep()` |
| `httpx.AsyncClient()` per request | One long-lived client via lifespan |
| `asyncio.create_task()` without ref | Store ref + `add_done_callback(set.discard)` |
| Swallowing `CancelledError` | Always `raise` after cleanup |
| Patching module internals in tests | Protocol-based `FakeRepository` instead |
| `datetime.now()` inside domain model | Inject clock as argument |
| Service locator / global registry | Constructor injection at composition root |

---

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

---

## Test Doubles Taxonomy

> When a bug is hard to reproduce or the root cause is unclear, apply `code-debugging` (systematic debugging + root cause tracing) before writing new tests.

| Type | What it does | Use when |
|------|-------------|----------|
| **Fake** | Working in-memory implementation | Replacing heavy infra (DB, email) |
| **Stub** | Returns canned values | Controlling indirect inputs |
| **Spy** | Records calls for later assertion | Verifying side-effects occurred |
| **Mock** | Asserts expected calls upfront | Strict behavior verification (use sparingly) |
| **Dummy** | Passed but never used | Satisfying required params |

### Fakes — the preferred pattern for repositories

```python
# tests/fakes.py
class FakeOrderRepository:
    """In-memory OrderRepository — implements the Protocol structurally."""

    def __init__(self) -> None:
        self._store: dict[OrderId, Order] = {}

    def get(self, order_id: OrderId) -> Order:
        return self._store[order_id]

    def add(self, order: Order) -> None:
        self._store[order.id] = order

    def list_pending(self) -> list[Order]:
        return [o for o in self._store.values() if o.status == "pending"]

    def all(self) -> list[Order]:  # test helper, not on Protocol
        return list(self._store.values())
```

```python
# tests/unit/test_ship_order.py — zero infra, zero mocks
def test_ship_order_marks_shipped():
    repo = FakeOrderRepository()
    repo.add(Order(id=OrderId("123")))
    ship_order(OrderId("123"), repo, FakeNotifier())
    assert repo.get(OrderId("123")).status == "shipped"
```

### Why over-mocking is an architectural smell

- `patch("module.Class.method")` couples tests to module paths — any refactor breaks tests
- Mocks assert *how* code works, not *what* it does
- If you need 5+ mocks for one test, the function has too many dependencies
- Mocks can "pass" while behavior is broken

**Rule**: if you find yourself writing `mock.assert_called_once_with(...)` for repository operations, write a `FakeRepository` instead.

### When `unittest.mock` is acceptable

```python
# OK: mocking at an architectural boundary (third-party HTTP call)
from unittest.mock import patch

def test_notifier_calls_smtp():
    with patch("adapters.notifications.smtplib.SMTP") as mock_smtp:
        SmtpNotifier(host="localhost").notify_shipped(order)
        mock_smtp.return_value.__enter__.return_value.sendmail.assert_called_once()
```

### Verify fakes match Protocol at type-check time

```python
from typing import runtime_checkable

@runtime_checkable
class OrderRepository(Protocol): ...

# mypy --strict tests/fakes.py catches structural mismatches at CI time
```

---

## Pytest Fixtures in Depth

### Scope hierarchy

| Scope | Lifetime | Use for |
|-------|----------|---------|
| `session` | Entire test run | DB containers, HTTP clients |
| `module` | One `.py` file | File-level shared state |
| `class` | One test class | Class-level shared state |
| `function` | One test (default) | Isolated per-test state |

### Session-scoped container + per-test transaction rollback

```python
# tests/integration/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine("postgresql://localhost/testdb")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

@pytest.fixture(scope="function")
def db_session(db_engine):
    conn = db_engine.connect()
    tx = conn.begin()
    session = sessionmaker(bind=conn)()
    yield session
    session.close()
    tx.rollback()
    conn.close()
```

### Factory fixture — when tests need multiple instances

```python
@pytest.fixture
def make_user(db_session):
    created = []

    def _make(name: str = "Alice", role: str = "user", **kwargs) -> User:
        user = User(name=name, role=role, **kwargs)
        db_session.add(user)
        db_session.flush()
        created.append(user)
        return user

    yield _make
    for user in reversed(created):
        db_session.delete(user)
    db_session.commit()
```

### Parametrized fixtures — run tests against multiple backends

```python
@pytest.fixture(params=["sqlite", "postgresql"])
def database_url(request, tmp_path):
    if request.param == "sqlite":
        return f"sqlite:///{tmp_path}/test.db"
    return "postgresql://localhost/testdb"
```

### Async fixtures — use `pytest_asyncio.fixture`

```python
import pytest_asyncio
import httpx

@pytest_asyncio.fixture(scope="session")
async def http_client():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        yield client
```

**Gotcha**: `@pytest.fixture` silently breaks async teardown — always use `@pytest_asyncio.fixture` for async fixtures.

### pyproject.toml for async tests

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"   # all async tests/fixtures treated as asyncio; no @pytest.mark.asyncio needed
```

---

## Property-Based Testing with Hypothesis

Use Hypothesis for **invariants** (properties that hold for all inputs), not specific cases.

```python
from hypothesis import given, settings
from hypothesis import strategies as st

# Invariant: encode → decode is always identity
@given(st.text())
def test_round_trip(s: str) -> None:
    assert decode(encode(s)) == s

# Algebraic property
@given(st.integers(min_value=0), st.integers(min_value=0))
def test_add_commutative(a: int, b: int) -> None:
    assert add(a, b) == add(b, a)

# Control example count and deadline
@given(st.lists(st.integers(), min_size=1))
@settings(max_examples=500)
def test_sort_idempotent(lst: list[int]) -> None:
    assert sorted(sorted(lst)) == sorted(lst)
```

### Custom strategies

```python
from hypothesis import strategies as st

# st.builds — construct domain objects
address_strategy = st.builds(
    Address,
    street=st.text(min_size=1, max_size=100),
    zip_code=st.from_regex(r"\d{5}"),
)

# @st.composite — correlated values
@st.composite
def date_range(draw):
    start = draw(st.dates())
    end = draw(st.dates(min_value=start))
    return DateRange(start, end)
```

### Stateful testing

```python
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant

class StackMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.model: list = []
        self.impl = Stack()

    @rule(value=st.integers())
    def push(self, value: int) -> None:
        self.model.append(value)
        self.impl.push(value)

    @rule()
    def pop(self) -> None:
        if self.model:
            assert self.impl.pop() == self.model.pop()

    @invariant()
    def size_matches(self) -> None:
        assert len(self.impl) == len(self.model)

TestStack = StackMachine.TestCase
```

**Shrinking**: when Hypothesis finds a failure, it automatically reduces the input to the smallest example that still fails — a 1000-element list becomes `[0]`.

---

## Integration Testing with testcontainers

```bash
uv add --dev testcontainers[postgres,redis]
```

```python
# tests/integration/conftest.py
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg

@pytest.fixture(scope="session")
def db_engine(postgres_container):
    engine = create_engine(postgres_container.get_connection_url())
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()
```

**Pattern**: session-scoped container (Docker start is 2-5s) + function-scoped transaction rollback (microseconds). Never start a new container per test.

---

## Async / Await Patterns

### TaskGroup (3.11+) — preferred over `gather()`

```python
import asyncio

async def main() -> None:
    async with asyncio.TaskGroup() as tg:
        t1 = tg.create_task(fetch("https://a.example"))
        t2 = tg.create_task(fetch("https://b.example"))
    results = [t1.result(), t2.result()]
```

`TaskGroup` cancels all sibling tasks on the first failure. `gather()` silently continues unless `return_exceptions=False`.

Use `gather()` when: Python < 3.11, or `return_exceptions=True` is needed to collect all results including errors.

### Timeouts — `asyncio.timeout()` (3.11+)

```python
async def robust_fetch(url: str) -> bytes:
    async with asyncio.timeout(10.0):       # raises TimeoutError; no new task created
        async with httpx.AsyncClient() as c:
            return (await c.get(url)).content
```

`asyncio.timeout()` wraps arbitrary blocks and can be rescheduled. Prefer it over `asyncio.wait_for()` in 3.11+.

### Cancellation — always re-raise `CancelledError`

```python
async def worker() -> None:
    try:
        await long_running_io()
    except asyncio.CancelledError:
        await cleanup()   # release resources
        raise             # MANDATORY — never swallow
```

### Store task references

```python
_background: set[asyncio.Task] = set()

def fire_and_forget(coro) -> None:
    task = asyncio.create_task(coro)
    _background.add(task)
    task.add_done_callback(_background.discard)   # auto-cleanup
```

Tasks with no stored reference are garbage-collected mid-flight.

### Async context managers and generators

```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator

@asynccontextmanager
async def managed_connection(dsn: str) -> AsyncGenerator[Connection, None]:
    conn = await connect(dsn)
    try:
        yield conn
    finally:
        await conn.close()

async def stream_lines(path: str) -> AsyncGenerator[str, None]:
    async with aiofiles.open(path) as f:
        async for line in f:
            yield line.rstrip()
```

Use `contextlib.aclosing()` when consuming a generator and breaking early — guarantees cleanup even on `break` or exception.

### httpx — one long-lived client

```python
# BAD: new TCP + TLS handshake per call
async def bad_fetch(url: str) -> bytes:
    async with httpx.AsyncClient() as c:   # created and destroyed each time
        return (await c.get(url)).content

# GOOD: lifespan-managed (FastAPI example)
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = httpx.AsyncClient(
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0),
    )
    yield
    await app.state.client.aclose()
```

### Blocking calls — don't block the event loop

```python
import asyncio, functools

# Thread offload for blocking I/O
async def read_file(path: str) -> bytes:
    return await asyncio.to_thread(Path(path).read_bytes)

# Process offload for CPU-bound work
async def compress(data: bytes) -> bytes:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        ProcessPoolExecutor(), functools.partial(zlib.compress, data, 9)
    )
```

### Semaphore for rate limiting

```python
_sem = asyncio.Semaphore(10)

async def fetch_limited(client: httpx.AsyncClient, url: str) -> bytes:
    async with _sem:
        return (await client.get(url)).content
```

### anyio — when to use it

Reach for `anyio` over raw `asyncio` when: writing a library that must work on both asyncio and Trio, needing `tg.start()` (wait until subtask signals readiness), or wanting superior cancellation semantics.

```python
import anyio

async def main() -> None:
    async with anyio.create_task_group() as tg:
        tg.start_soon(worker_a)
        tg.start_soon(worker_b)
```

`pytest-anyio` for testing anyio code; `pytest-asyncio` for asyncio-only.

### Enable asyncio debug mode during development

```python
asyncio.run(main(), debug=True)  # catches unawaited coroutines, slow callbacks
# or: PYTHONASYNCIODEBUG=1 python myapp.py
```

---

## Configuration Management

Use `pydantic-settings` for typed, validated config loaded from env vars, `.env` files, and Docker secrets.

```bash
uv add pydantic-settings
```

```python
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",    # DB__URL → db.url
        secrets_dir="/run/secrets",   # Docker secrets
        extra="ignore",
    )

    app_name: str = "myapp"
    debug: bool = False
    db_url: str = "postgresql://localhost/dev"
    api_key: SecretStr          # never logged; redacted in repr

    @field_validator("app_name")
    @classmethod
    def no_spaces(cls, v: str) -> str:
        if " " in v:
            raise ValueError("app_name must not contain spaces")
        return v

settings = Settings()
key = settings.api_key.get_secret_value()  # explicit unwrap

# Test override — no monkeypatching needed
test_settings = Settings(db_url="sqlite:///:memory:", api_key="test")
```

**Priority** (highest → lowest): constructor kwargs → env vars → `.env` file → `/run/secrets/` → field defaults.

---

## Structured Logging

> When debugging a running service via logs, apply `code-root-cause-analysis` to extract error signatures and correlate across log entries.

Use `structlog` for production services. Use `loguru` for scripts. Don't fight stdlib in frameworks that own the logging tree.

```bash
uv add structlog
```

```python
import logging, os, sys, structlog
from structlog.contextvars import merge_contextvars, bind_contextvars, clear_contextvars

def configure_logging(*, json: bool = False) -> None:
    shared = [
        merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
    ]
    structlog.configure(
        processors=shared + (
            [structlog.processors.JSONRenderer()]
            if json
            else [structlog.dev.ConsoleRenderer(colors=True)]
        ),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

configure_logging(json=os.getenv("LOG_FORMAT") == "json")
log = structlog.get_logger(__name__)
```

### Bind request context (FastAPI middleware)

```python
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    clear_contextvars()
    bind_contextvars(trace_id=request.headers.get("X-Trace-ID", str(uuid4())))
    response = await call_next(request)
    bind_contextvars(status_code=response.status_code)
    log.info("request_completed")
    return response
```

Every `log.info(...)` in that request automatically carries `trace_id` and `status_code`.

**Never log**: passwords, tokens, API keys, full request/response bodies (PII + size), stack traces at WARNING level.

---

## Concurrency Decision Tree

```
What kind of work?
│
├─ CPU-bound (image processing, ML, heavy math)
│   └─ Threads blocked by GIL → use ProcessPoolExecutor
│
├─ I/O-bound, synchronous code (legacy DB drivers, blocking libs)
│   └─ GIL released during I/O syscalls → ThreadPoolExecutor
│      or asyncio.to_thread() to stay in async context
│
└─ I/O-bound, new code
    └─ asyncio with async/await throughout
```

```python
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import os

# CPU-bound
with ProcessPoolExecutor(max_workers=os.cpu_count()) as pool:
    futures = {pool.submit(crunch, chunk): chunk for chunk in chunks}
    for fut in as_completed(futures):
        result = fut.result(timeout=30)

# I/O-bound sync
with ThreadPoolExecutor(max_workers=20) as pool:
    results = list(pool.map(fetch_sync, urls, timeout=60))

# Blocking call inside async
async def read_async(path: str) -> bytes:
    return await asyncio.to_thread(Path(path).read_bytes)
```

**GIL note (2025)**: Python 3.13 ships with a disableable GIL (`PYTHON_GIL=0`) but most C extensions aren't yet compatible. The CPU→processes / I/O→threads/async rule still holds.

---

## Complete pyproject.toml Template

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-package"
version = "0.1.0"
description = "One-line description"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"
authors = [{ name = "Your Name", email = "you@example.com" }]
dependencies = [
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "structlog>=24.1",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = ["my-package[test,lint]"]
test = [
    "pytest>=8.2",
    "pytest-cov>=5.0",
    "pytest-asyncio>=0.23",
    "pytest_asyncio",
    "hypothesis>=6.100",
    "testcontainers[postgres]>=4.7",
    "anyio[trio]>=4.4",
]
lint = [
    "ruff>=0.5",
    "mypy>=1.10",
]

[project.scripts]
my-cli = "mypackage.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]

[tool.ruff]
src = ["src"]
line-length = 120
target-version = "py311"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "UP", "B", "SIM", "ANN", "RUF"]
ignore = ["ANN101", "ANN102"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["some_untyped_lib.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = [
    "--strict-markers",
    "--tb=short",
    "--cov=src/mypackage",
    "--cov-report=term-missing",
    "--cov-report=xml",
]
markers = [
    "integration: requires external services (deselect with '-m not integration')",
    "slow: takes more than 1s",
]

[tool.coverage.run]
source = ["src/mypackage"]
branch = true
omit = ["*/migrations/*", "*/__main__.py"]

[tool.coverage.report]
show_missing = true
fail_under = 80
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "@overload",
    "raise NotImplementedError",
]
```

---

## Related Skills

Apply these companion skills when the situation calls for it — don't duplicate their guidance here.

| Skill | When to apply in a Python context |
|-------|----------------------------------|
| `code-architecture-best-practices` | Designing layers, applying SOLID/DDD/Clean Architecture, evaluating module boundaries, deciding where logic belongs |
| `type-driven-design` | Encoding domain invariants into the type system: `NewType`, smart constructors, sum types, refinement types |
| `design-patterns` | Choosing GoF or PoEAA patterns; deciding when a `Protocol` vs ABC is the right abstraction |
| `code-debugging` | Systematic bug investigation — the four-phase framework (root cause → pattern analysis → hypothesis → fix); defense-in-depth validation before claiming a fix is complete |
| `code-root-cause-analysis` | Diagnosing errors with stack traces, searching Logseq history for prior incidents, correlating across log entries |
| `code-review` | Receiving PR feedback with technical rigor; requesting a `code-reviewer` subagent; verification gates before claiming completion |
| `code-refactoring` | Large structural refactors using `ast-grep` (scope discovery) + `gritql` (AST-based transformation) with mandatory quality gates |
| `code-ast-grep` | Semantic code search — find all call sites or usages of a pattern structurally rather than with text grep |
| `code-gritql` | Automated multi-file code transformations (rename API, modernize syntax, bulk pattern replacement) |
| `infra-docker-build-test` | Containerizing Python services; pre-push Docker build validation checklist to prevent CI failures |
| `security-review` | Adversarial OWASP Top 10 audit — injection (SQL, OS command, template), auth/session, secrets, dependency CVEs; apply before any public-facing release |