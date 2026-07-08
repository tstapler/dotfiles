# Testing Guide

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

Mypy checks Protocol structural compatibility without any decorator — just run `mypy --strict tests/fakes.py` in CI. `@runtime_checkable` is only needed if you want `isinstance(obj, OrderRepository)` checks at runtime; don't add it just for mypy.

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
asyncio_mode = "auto"                             # all async tests/fixtures treated as asyncio; no @pytest.mark.asyncio needed
asyncio_default_fixture_loop_scope = "function"   # pytest-asyncio >=0.24 warns if unset
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
