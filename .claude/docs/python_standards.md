# Python Development Standards

## Overview

This document defines the Python coding standards and best practices for all Python development work. These guidelines ensure consistency, maintainability, and quality across all Python projects.

## Base Instructions

- **Adhere to All Guidelines:** Follow these rules for the entire session when writing Python code.
- **Define Dependencies with PEP 723:**

  ```python
  # /// script
  # requires-python = ">=3.11"
  # dependencies = [
  #   "requests<3",
  #   "rich",
  # ]
  # ///
  ```

- **Package Management:**
  - Always use `uv` for installing and manipulating python dependencies
  - Use `uv install -e .` for development installations
  - Use `uv run` for executing scripts with dependencies

## Library Usage

### Default Approach
- Use built-in libraries (e.g., `argparse`, `dataclasses`) for portability in simple scripts.

### With Dependencies
If dependencies are preferred, confirm first. Then:
- Use `Pydantic` for Data Transfer Objects (DTOs), including field documentation
- Use `Literal` for string enums
- Provide constructors for typed DTO creation
- Use `Typer` for building user-friendly command-line interfaces

## Code Quality

### Type Annotations
- Annotate all function arguments and return types
- Use default values for optional parameters
- Example:
  ```python
  def process_data(
      items: list[str],
      max_count: int = 100,
      verbose: bool = False
  ) -> dict[str, int]:
      pass
  ```

### Comments & Documentation
- Comment only when the code isn't self-explanatory
- Write clear docstrings for functions and modules, detailing their purpose, parameters, and usage
- Use type hints instead of documenting types in docstrings

### Style
- Follow PEP 8 standards, allowing line lengths up to 120 characters
- Use Black for consistent code formatting
- Clearly mark any unfinished code sections with `# TODO:` or `# FIXME:`

## Code Structure

### Separation of Concerns
- Isolate UI and IO from business logic to enhance testability and maintenance
- Keep data validation separate from business logic
- Use dependency injection for external dependencies

### Facade Pattern
- For API or networking libraries, implement a facade named "service"
- Example: `GithubService`, `DatadogService`

### Data Models
- Use classes for DTOs and Domain Objects with `dataclasses` or `Pydantic` (if using dependencies)
- Define DTOs with built-in methods for common tasks
- Use DTOs for function arguments and return values
- Example:
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

## Extras

### API Clients
- Support pagination where necessary
- Use class-based structures (e.g., `GithubClient`)
- Expose configurable options during class initialization
- Example:
  ```python
  class APIClient:
      def __init__(self, base_url: str, timeout: int = 30):
          self.base_url = base_url
          self.timeout = timeout

      def list_items(self, page: int = 1, per_page: int = 100) -> list[Item]:
          pass
  ```

### Testing
- Write pytest parametrized tests in separate files
- Focus on edge cases
- Use `dataclasses` for test data, avoiding names that start with 'Test'
- Use `ids=lambda testcase: testcase.description` for descriptive test names
- When creating benchmarks use the pytest-benchmark tool to run them and configure them with the benchmark mark
- Example:
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

## Quick Reference

### Common Patterns

**CLI Application:**
```python
import typer
from pydantic import BaseModel

app = typer.Typer()

class Config(BaseModel):
    input_file: str
    output_dir: str
    verbose: bool = False

@app.command()
def process(
    input_file: str,
    output_dir: str = "./output",
    verbose: bool = False
):
    config = Config(
        input_file=input_file,
        output_dir=output_dir,
        verbose=verbose
    )
    # Process...

if __name__ == "__main__":
    app()
```

**API Service:**
```python
from dataclasses import dataclass
import requests

@dataclass
class APIResponse:
    status: int
    data: dict

class APIService:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    def fetch_data(self, endpoint: str) -> APIResponse:
        response = requests.get(
            f"{self.base_url}/{endpoint}",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return APIResponse(
            status=response.status_code,
            data=response.json()
        )
```
