# Tooling: pyproject.toml, Config, Logging, Concurrency

## Tooling Baseline

Add to `pyproject.toml`:
```toml
[tool.ruff]
line-length = 120
target-version = "py312"

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
requires-python = ">=3.12"
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
    "pytest>=9.0",
    "pytest-cov>=5.0",
    "pytest-asyncio>=0.24",
    "hypothesis>=6.100",
    "testcontainers[postgres]>=4.7",
    "anyio[trio]>=4.4",
]
lint = [
    "ruff>=0.13",
    "mypy>=2.0",
]

[project.scripts]
my-cli = "mypackage.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]

[tool.ruff]
src = ["src"]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "UP", "B", "SIM", "ANN", "RUF"]
# ANN101/ANN102 (missing self/cls annotations) were removed from ruff in 0.2.0 — don't ignore codes that no longer exist

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["some_untyped_lib.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"   # pytest-asyncio >=0.24 warns if unset
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

## Configuration Management (pydantic-settings)

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

## Structured Logging (structlog)

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

**GIL note (2026)**: free-threading (PEP 703/779) is now officially supported as of 3.14, with most top packages shipping free-threaded wheels — but default builds still ship with the GIL on, and per-thread overhead on free-threaded builds is still ~5–10%. The CPU→processes / I/O→threads/async rule still holds unless you've deliberately opted into a free-threaded build for a measured reason.
