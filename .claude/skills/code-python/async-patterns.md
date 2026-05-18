# Async / Await Patterns

## TaskGroup (3.11+) — preferred over `gather()`

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

## Timeouts — `asyncio.timeout()` (3.11+)

```python
async def robust_fetch(url: str) -> bytes:
    async with asyncio.timeout(10.0):       # raises TimeoutError; no new task created
        async with httpx.AsyncClient() as c:
            return (await c.get(url)).content
```

`asyncio.timeout()` wraps arbitrary blocks and can be rescheduled. Prefer it over `asyncio.wait_for()` in 3.11+.

## Cancellation — always re-raise `CancelledError`

```python
async def worker() -> None:
    try:
        await long_running_io()
    except asyncio.CancelledError:
        await cleanup()   # release resources
        raise             # MANDATORY — never swallow
```

## Store task references

```python
_background: set[asyncio.Task] = set()

def fire_and_forget(coro) -> None:
    task = asyncio.create_task(coro)
    _background.add(task)
    task.add_done_callback(_background.discard)   # auto-cleanup
```

Tasks with no stored reference are garbage-collected mid-flight.

## Async context managers and generators

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

## httpx — one long-lived client

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

## Blocking calls — don't block the event loop

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

## Semaphore for rate limiting

```python
_sem = asyncio.Semaphore(10)

async def fetch_limited(client: httpx.AsyncClient, url: str) -> bytes:
    async with _sem:
        return (await client.get(url)).content
```

## anyio — when to use it

Reach for `anyio` over raw `asyncio` when: writing a library that must work on both asyncio and Trio, needing `tg.start()` (wait until subtask signals readiness), or wanting superior cancellation semantics.

```python
import anyio

async def main() -> None:
    async with anyio.create_task_group() as tg:
        tg.start_soon(worker_a)
        tg.start_soon(worker_b)
```

`pytest-anyio` for testing anyio code; `pytest-asyncio` for asyncio-only.

## Enable asyncio debug mode during development

```python
asyncio.run(main(), debug=True)  # catches unawaited coroutines, slow callbacks
# or: PYTHONASYNCIODEBUG=1 python myapp.py
```
