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

Apply techniques from the `type-driven-design` skill to encode invariants into Python's type system.

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

Apply patterns from the `design-patterns` skill. Below are the idiomatic Python translations. Prefer the Python form over a mechanical OOP translation from Java/C++.

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