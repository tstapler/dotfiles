#!/usr/bin/env python3
"""
Universal executor for stelekit-ui-skill scripts.

Usage:
  python3 run.py /tmp/stelekit-ui-script.py   # Execute a script file
  python3 run.py "from helpers import *; ..."  # Execute inline code

Adds lib/ to sys.path so scripts can do: from helpers import *
"""

import sys
import os
import shutil

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(SKILL_DIR, "lib")

# Add lib/ to path so helpers is importable
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)


def check_setup():
    """Check if required tools are installed."""
    missing = [cmd for cmd in ["xdotool", "wmctrl"] if not shutil.which(cmd)]
    return missing


def run_file(path):
    """Execute a Python script file with helpers available."""
    if not os.path.exists(path):
        print(f"ERROR: Script file not found: {path}", file=sys.stderr)
        sys.exit(1)

    with open(path) as f:
        code = f.read()

    _exec_code(code, path)


def run_inline(code):
    """Execute inline Python code with helpers available."""
    _exec_code(code, "<inline>")


def _exec_code(code, source):
    """Execute code string with helpers pre-imported."""
    # Pre-import helpers into the execution namespace
    namespace = {"__file__": source, "__name__": "__main__"}

    # Import helpers module into namespace
    try:
        import helpers as _helpers_module
        import importlib
        for name in dir(_helpers_module):
            if not name.startswith("_"):
                namespace[name] = getattr(_helpers_module, name)
        # Also make the module available
        namespace["helpers"] = _helpers_module
    except ImportError as e:
        print(f"ERROR: Could not import helpers: {e}", file=sys.stderr)
        print(f"  LIB_DIR: {LIB_DIR}", file=sys.stderr)
        sys.exit(1)

    # Wrap code in try/except if not already wrapped
    if "try:" not in code:
        wrapped = f"""
try:
    {chr(10).join('    ' + line for line in code.splitlines())}
except Exception as _e:
    import traceback
    print(f"ERROR: {{_e}}", file=__import__('sys').stderr)
    traceback.print_exc()
    __import__('sys').exit(1)
"""
    else:
        wrapped = code

    exec(compile(wrapped, source, "exec"), namespace)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 run.py <script.py>|<inline code>", file=sys.stderr)
        print("  Example: python3 run.py /tmp/stelekit-ui-test.py")
        print("  Example: python3 run.py \"from helpers import *; screenshot('/tmp/s.png')\"")
        sys.exit(1)

    arg = sys.argv[1]

    # Check setup
    missing = check_setup()
    if missing:
        print(f"WARNING: Missing tools: {', '.join(missing)}")
        print(f"Run setup first: python3 {SKILL_DIR}/setup.py")
        print("Continuing anyway (some helpers may fail)...")

    # Determine if arg is a file path or inline code
    if os.path.exists(arg) or (arg.endswith(".py") and "/" in arg):
        run_file(arg)
    else:
        run_inline(arg)


if __name__ == "__main__":
    main()
