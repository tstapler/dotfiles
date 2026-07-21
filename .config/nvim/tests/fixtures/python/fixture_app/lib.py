"""Tiny fixture module for exercising cross-file go-to-definition/references
and DAP breakpoints under nvim-next's basedpyright + debugpy setup.
"""


def greet(name: str) -> str:
    """Return a greeting for name — a cross-file gd/grr target."""
    return f"Hello, {name}!"


def total(nums: list[int]) -> int:
    """Sum nums — a good DAP breakpoint target: a loop with a local
    accumulator to set a breakpoint on and inspect mid-loop."""
    result = 0
    for n in nums:
        result += n
    return result
