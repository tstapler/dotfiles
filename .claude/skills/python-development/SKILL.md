---
name: python-development
description: Apply idiomatic, well-structured Python development practices. Use when writing, reviewing, or refactoring Python code. Covers type annotations, package management with uv, Pydantic DTOs, Typer CLIs, pytest patterns, PEP 8 style, architecture, and type-driven design.
paths: "**/*.py,**/pyproject.toml,**/*.toml"
---

# Python Development

Apply these standards when writing, reviewing, or debugging Python code.

## Project Setup: Reference This Skill in CLAUDE.md

The first time you touch Python code in a project, check that repo's `CLAUDE.md` (or `AGENTS.md`). If it exists but doesn't mention this skill, add a line pointing at it, e.g.:

```markdown
## Python
Apply the `python-development` skill for all Python code (standards, architecture, type-driven design).
```

If no `CLAUDE.md` exists yet, don't create one just for this — only add the note when the file already exists for another reason, or when the user is setting up project conventions.

## Package Management

- **Always use `uv`** for dependency management
- Use `uv install -e .` for development installations
- Use `uv run` for executing scripts with dependencies
- Group dev/test/docs deps with the standard `[dependency-groups]` table (PEP 735) in `pyproject.toml` — not a Poetry-style custom scheme
- For monorepos with multiple packages sharing a lockfile, use a **uv workspace** (root `[tool.uv.workspace]` + member `pyproject.toml` files) rather than separate venvs per package

## Dependencies Declaration (PEP 723)

```python
# /// script
# requires-python = ">=3.12"
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

**PEP 695 generics** (3.12+, matches this skill's baseline) — replaces `TypeVar` + `Generic[T]` boilerplate:

```python
type UserId = int                              # generic-friendly alias, not a nominal type
class Repository[T]:                            # generic class
    def get(self, id: T) -> T: ...
def first[T](items: list[T]) -> T: ...          # generic function
```

This is distinct from `NewType` below — a `type` alias is *interchangeable* with its target (a `UserId` and a plain `int` mix freely), while `NewType` gives *nominal* typing (mypy treats them as incompatible). Use `type` aliases for readability, `NewType`/frozen dataclasses when you need mypy to catch mixups.

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
- Use **`ruff format`** for formatting — it's the Black-compatible successor; don't add Black as a separate tool
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

Use parametrized tests with descriptive IDs. Prefer `FakeRepository` over mocks for infra boundaries.
See [testing-guide.md](testing-guide.md) for Test Doubles Taxonomy, Pytest Fixtures in Depth, Hypothesis property-based testing, and testcontainers integration patterns.

```python
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

See [tooling.md](tooling.md) for the complete `pyproject.toml` template (ruff, mypy, pytest config), `pydantic-settings` config management, `structlog` structured logging, and the concurrency decision tree. Use `ruff` alongside (or instead of) `flake8` — it also handles import sorting and auto-modernizes old type syntax.

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

See [design-patterns.md](design-patterns.md) for full GoF and PoEAA patterns with Python idioms.
Quick reference: Factory (plain functions + `match`), Strategy (Protocol injection or callable), Observer (callback registry), Repository (Protocol in domain + SQL impl in adapters), Unit of Work (context manager).

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

## Project Structure & Architecture

See [architecture.md](architecture.md) for the `src/` layout, Hexagonal Architecture (Ports & Adapters), domain model rules, and composition root wiring.
Quick reference: `domain/` has zero I/O imports; `ports/` are `Protocol` definitions; `adapters/` implement ports; `entrypoints/` is the composition root.

---

## Async / Await Patterns

See [async-patterns.md](async-patterns.md) for full async patterns.
Quick reference: prefer `TaskGroup` (3.11+) over `gather()`; use `asyncio.timeout()` instead of `wait_for()`; always re-raise `CancelledError`; store task references; one long-lived `httpx.AsyncClient` per lifespan.

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