"""Tiny fixture entry point: imports lib.py across a file boundary so `gd`
on greet/total jumps there, and the total() call is a good spot to set a
DAP breakpoint via <leader>db.
"""

from fixture_app.lib import greet, total


def main() -> None:
    msg = greet("World")
    print(msg)

    nums = [1, 2, 3, 4, 5]
    result = total(nums)
    print(f"Total: {result}")


if __name__ == "__main__":
    main()
