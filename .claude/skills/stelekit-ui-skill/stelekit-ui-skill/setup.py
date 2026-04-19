#!/usr/bin/env python3
"""
Setup script for stelekit-ui-skill.
Installs xdotool, wmctrl, and scrot for desktop UI automation.
"""

import subprocess
import sys
import shutil


def check_installed(cmd):
    return shutil.which(cmd) is not None


def run(args, check=True):
    print(f"  Running: {' '.join(args)}")
    result = subprocess.run(args, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"  ERROR: {result.stderr.strip()}")
    return result


def install_pacman(packages):
    """Install packages via pacman (Arch/Manjaro)."""
    print(f"Installing via pacman: {', '.join(packages)}")
    result = run(["sudo", "pacman", "-S", "--noconfirm"] + packages, check=False)
    if result.returncode != 0:
        print(f"  pacman failed: {result.stderr.strip()}")
        return False
    return True


def install_brew(packages):
    """Install packages via Homebrew (macOS/Linux)."""
    print(f"Installing via brew: {', '.join(packages)}")
    for pkg in packages:
        result = run(["brew", "install", pkg], check=False)
        if result.returncode != 0:
            print(f"  brew failed for {pkg}: {result.stderr.strip()}")
            return False
    return True


def main():
    tools = {
        "xdotool": "xdotool",
        "wmctrl": "wmctrl",
        "scrot": "scrot",
    }

    already_installed = []
    to_install = []

    for cmd, pkg in tools.items():
        if check_installed(cmd):
            already_installed.append(cmd)
        else:
            to_install.append(pkg)

    if already_installed:
        print(f"Already installed: {', '.join(already_installed)}")

    if not to_install:
        print("All tools are already installed. Setup complete.")
        return 0

    print(f"Need to install: {', '.join(to_install)}")

    # Detect package manager and install
    if check_installed("pacman"):
        success = install_pacman(to_install)
    elif check_installed("brew"):
        success = install_brew(to_install)
    else:
        print("ERROR: No supported package manager found (pacman or brew).")
        print("Please install manually:")
        for pkg in to_install:
            print(f"  {pkg}")
        return 1

    if success:
        # Verify installation
        failed = [cmd for cmd in to_install if not check_installed(cmd)]
        if failed:
            print(f"WARNING: These tools may not be in PATH: {', '.join(failed)}")
        else:
            print(f"Successfully installed: {', '.join(to_install)}")
        print("Setup complete.")
        return 0
    else:
        print("Setup failed. Please install the tools manually.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
