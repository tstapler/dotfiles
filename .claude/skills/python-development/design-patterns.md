# Design Patterns in Python

Apply patterns from the `design-patterns` skill. Below are the idiomatic Python translations. Prefer the Python form over a mechanical OOP translation from Java/C++. For cross-cutting structural decisions (layering, dependency direction, module boundaries), also apply `code-architecture-best-practices`.

## Creational

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

## Structural

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

## Behavioral

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
    def __init__(self) -> None:
        self._handlers: dict[type, Callable] = {}

    def register(self, cmd_type: type, handler: Callable) -> None:
        self._handlers[cmd_type] = handler

    def dispatch(self, cmd: SendEmailCommand) -> None:
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

## PoEAA Patterns in Python

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
