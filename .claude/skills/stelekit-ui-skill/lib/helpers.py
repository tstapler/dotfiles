"""
SteleKit UI automation helpers.
Provides xdotool/ImageMagick-based desktop automation for the SteleKit Compose Desktop app.

Usage in scripts:
    from helpers import *
"""

import subprocess
import os
import sys
import shutil
import time

# --- Configuration ---

STELEKIT_WINDOW_TITLE = "stelekit"
STELEKIT_BIN = os.path.expanduser("~/.local/bin/stelekit")
# Also check common Gradle run locations
STELEKIT_GRADLE_MAIN = "dev.stapler.stelekit.desktop.MainKt"


def _require(cmd, hint=None):
    """Raise a clear error if a tool is not installed."""
    if not shutil.which(cmd):
        skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        msg = f"'{cmd}' is not installed."
        if hint:
            msg += f" {hint}"
        else:
            msg += f" Run: python3 {skill_dir}/setup.py"
        raise RuntimeError(msg)


def _run(args, check=False, capture=True):
    """Run a subprocess, return CompletedProcess."""
    result = subprocess.run(
        args,
        capture_output=capture,
        text=True,
        check=False,
    )
    return result


# --- Window Management ---

def window_id(title=STELEKIT_WINDOW_TITLE):
    """
    Find the window ID for SteleKit by title pattern.
    Returns the first matching window ID as a string, or None if not found.
    """
    _require("xdotool")
    result = _run(["xdotool", "search", "--name", title])
    if result.returncode != 0 or not result.stdout.strip():
        return None
    # Return the last window ID (usually the most recent/visible one)
    ids = result.stdout.strip().splitlines()
    return ids[-1] if ids else None


def focus_stelekit(title=STELEKIT_WINDOW_TITLE):
    """
    Focus and raise the SteleKit window.
    Raises RuntimeError if the window is not found.
    """
    _require("xdotool")
    wid = window_id(title)
    if wid is None:
        raise RuntimeError(
            f"SteleKit window not found (searched for title: '{title}'). "
            "Is the app running? Call launch_app() first."
        )
    _run(["xdotool", "windowfocus", "--sync", wid])
    _run(["xdotool", "windowraise", wid])
    time.sleep(0.1)
    return wid


def window_geometry(window_id_or_title=None):
    """
    Return (x, y, width, height) for the SteleKit window (or given window ID/title).
    Returns (0, 0, 0, 0) if window not found.
    """
    _require("xdotool")

    if window_id_or_title is None:
        wid = window_id()
    elif window_id_or_title.isdigit():
        wid = window_id_or_title
    else:
        wid = window_id(window_id_or_title)

    if wid is None:
        return (0, 0, 0, 0)

    result = _run(["xdotool", "getwindowgeometry", "--shell", wid])
    if result.returncode != 0:
        return (0, 0, 0, 0)

    geo = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            geo[k.strip()] = v.strip()

    try:
        return (int(geo.get("X", 0)), int(geo.get("Y", 0)),
                int(geo.get("WIDTH", 0)), int(geo.get("HEIGHT", 0)))
    except (ValueError, KeyError):
        return (0, 0, 0, 0)


def wait_for_window(title=STELEKIT_WINDOW_TITLE, timeout=15):
    """
    Wait up to timeout seconds for the SteleKit window to appear.
    Returns the window ID string when found.
    Raises TimeoutError if the window does not appear.
    """
    _require("xdotool")
    deadline = time.time() + timeout
    while time.time() < deadline:
        wid = window_id(title)
        if wid:
            return wid
        time.sleep(0.5)
    raise TimeoutError(
        f"SteleKit window did not appear within {timeout}s "
        f"(searched for title: '{title}')"
    )


def launch_app(wait=True, timeout=15):
    """
    Launch SteleKit if it is not already running.
    If wait=True, blocks until the window appears and returns its ID.
    Returns the window ID, or None if wait=False.
    """
    wid = window_id()
    if wid:
        print(f"SteleKit already running (window {wid})")
        focus_stelekit()
        return wid

    # Try installed binary first
    if os.path.exists(STELEKIT_BIN):
        print(f"Launching: {STELEKIT_BIN}")
        subprocess.Popen([STELEKIT_BIN], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        # Fall back to gradle run in the project directory
        project_dir = os.path.expanduser("~/Programming/stelekit")
        if os.path.exists(os.path.join(project_dir, "gradlew")):
            print(f"Launching via gradle run in {project_dir}")
            subprocess.Popen(
                ["./gradlew", "run"],
                cwd=project_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            raise RuntimeError(
                f"Cannot find SteleKit binary at {STELEKIT_BIN} "
                f"and no gradlew found in {project_dir}. "
                "Please build and install the app first."
            )

    if wait:
        print(f"Waiting up to {timeout}s for SteleKit window...")
        wid = wait_for_window(timeout=timeout)
        print(f"SteleKit window ready: {wid}")
        time.sleep(0.5)  # Give the UI time to settle
        return wid
    return None


# --- Screenshot ---

def screenshot(path="/tmp/stelekit-screenshot.png", window=None):
    """
    Take a screenshot and save it to path.

    window=None: captures the full screen (most reliable)
    window='stelekit' or a window ID: attempts window-only capture via ImageMagick import

    Returns the path where the screenshot was saved.
    """
    if window is not None:
        # Try window-specific capture with ImageMagick
        if shutil.which("import"):
            wid = window if str(window).isdigit() else window_id(window)
            if wid:
                result = _run(["import", "-window", wid, path])
                if result.returncode == 0:
                    print(f"Screenshot (window {wid}): {path}")
                    return path
                # Fall through to full-screen on failure

    # Full-screen fallback using scrot (preferred) or import
    if shutil.which("scrot"):
        result = _run(["scrot", path])
        if result.returncode == 0:
            print(f"Screenshot (full screen via scrot): {path}")
            return path

    if shutil.which("import"):
        result = _run(["import", "-window", "root", path])
        if result.returncode == 0:
            print(f"Screenshot (full screen via import): {path}")
            return path

    raise RuntimeError(
        "No screenshot tool available. "
        "Install scrot (recommended) or ImageMagick: python3 setup.py"
    )


# --- Mouse & Keyboard ---

def click(x, y, button=1):
    """
    Click at absolute screen coordinates (x, y).
    button: 1=left, 2=middle, 3=right
    """
    _require("xdotool")
    _run(["xdotool", "mousemove", "--sync", str(x), str(y)])
    _run(["xdotool", "click", str(button)])


def click_in_window(x, y, button=1, window=None):
    """
    Click at coordinates relative to the SteleKit window's top-left corner.

    Example:
        click_in_window(150, 80)   # click 150px right, 80px down from window top-left
    """
    geo = window_geometry(window)
    win_x, win_y, win_w, win_h = geo
    if win_w == 0:
        raise RuntimeError(
            "Cannot determine window geometry. Is SteleKit running? "
            "Call focus_stelekit() first."
        )
    abs_x = win_x + x
    abs_y = win_y + y
    click(abs_x, abs_y, button)


def type_text(text, delay=12):
    """
    Type text into the currently focused window.
    delay: milliseconds between keystrokes (default 12ms).
    """
    _require("xdotool")
    _run([
        "xdotool", "type",
        "--delay", str(delay),
        "--clearmodifiers",
        text,
    ])


def key(keysym):
    """
    Press a key or key combination.

    Examples:
        key("Return")
        key("Escape")
        key("ctrl+k")
        key("ctrl+shift+f")
        key("Tab")
        key("BackSpace")
    """
    _require("xdotool")
    _run(["xdotool", "key", "--clearmodifiers", keysym])


# --- Utility ---

def find_and_click_text(text, window=None):
    """
    Attempt to locate and click on visible text in the SteleKit window.

    This function takes a screenshot and returns instructions for the caller
    (Claude) to identify the coordinates visually, since pixel-level OCR is
    not available without additional tools.

    Returns a dict with screenshot path and instructions.
    """
    path = f"/tmp/stelekit-find-{text.replace(' ', '_')[:20]}.png"
    screenshot(path, window=window)
    return {
        "screenshot": path,
        "instructions": (
            f"Read the screenshot at '{path}' and identify the pixel coordinates "
            f"of the text '{text}'. Then call click_in_window(x, y) with those "
            "coordinates (relative to the window top-left)."
        ),
    }
