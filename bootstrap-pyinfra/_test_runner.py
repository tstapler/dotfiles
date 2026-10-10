"""Shared `__main__` runner for this project's plain-function test files.

No pytest here by convention — each test_*.py is run directly (`uv run
test_x.py`) or via `make pyinfra-test`. Not itself a test file (leading
underscore keeps it out of both globs).
"""


def run_tests(namespace: dict) -> None:
    tests = [value for key, value in namespace.items() if key.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
