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

Annotate all function arguments and return types:

```python
def process_data(
    items: list[str],
    max_count: int = 100,
    verbose: bool = False
) -> dict[str, int]:
    pass
```

## Library Preferences

| Need | Built-in | With Dependencies |
|------|----------|-------------------|
| CLI | `argparse` | `Typer` |
| Data models | `dataclasses` | `Pydantic` |
| String enums | - | `Literal` |

## Code Style

- Follow PEP 8 with line lengths up to **120 characters**
- Use **Black** for formatting
- Mark unfinished code with `# TODO:` or `# FIXME:`
- Comment only when code isn't self-explanatory

## Data Models

Use `dataclasses` or `Pydantic` for DTOs:

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

## Code Structure Principles

- **Separation of Concerns**: Isolate UI/IO from business logic
- **Facade Pattern**: For APIs, use service classes (e.g., `GithubService`)
- **Dependency Injection**: For external dependencies
- **DTOs**: Use for function arguments and return values