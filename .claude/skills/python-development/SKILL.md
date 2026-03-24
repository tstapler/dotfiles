--
name: python-development
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