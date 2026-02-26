#!/usr/bin/env python3
import sys
import subprocess
import re
import os
import stat
import datetime

STATE_FILE = "/tmp/monitor_state.sh"
LOG_FILE = "/tmp/display_switch.log"

def log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")
    # Also print to stdout/stderr for Sunshine logs
    print(message)

def get_current_state():
    """Parses xrandr output to get current state of connected monitors."""
    try:
        # Ensure we are capturing output
        output = subprocess.check_output(["xrandr", "--verbose"], text=True)
    except subprocess.CalledProcessError as e:
        log(f"Error running xrandr: {e}")
        sys.exit(1)
    except FileNotFoundError:
        log("Error: xrandr command not found.")
        sys.exit(1)

    monitors = []
    current_monitor = None

    # Matches: Name, "connected", optional "primary", geometry/pos string, rest
    # Example: "HDMI-0 connected 1920x1080+3146+0 (0x1cc) normal ..."
    # Group 1: Name (HDMI-0)
    # Group 2: "primary " or None
    # Group 3: Geometry (1920x1080+3146+0)
    # Group 4: Identifier (0x1cc) - ignored by non-capturing group logic if not strictly matched?
    # Actually, let's make it more robust.

    for line in output.splitlines():
        line = line.strip()
        if not line: continue

        # Detection line
        if " connected" in line:
            # Save previous
            if current_monitor:
                monitors.append(current_monitor)

            parts = line.split()
            name = parts[0]
            state = parts[1] # "connected"

            is_primary = "primary" in parts

            # Find geometry part: looks like WxH+X+Y
            geom_index = -1
            geom_pos = None
            for i, part in enumerate(parts):
                if re.match(r"[0-9]+x[0-9]+\+[0-9]+\+[0-9]+", part):
                    geom_pos = part
                    geom_index = i
                    break

            # Rotation is typically the token AFTER geometry (and optional identifier)
            # But BEFORE the parentheses starting capabilities like (normal left ...)
            # Example: ... 1920x1080+0+0 (0x1cc) normal (normal ...
            # Example: ... 1440x2560+0+0 right (normal ...

            rotation = "normal"
            if geom_index != -1:
                # Scan tokens after geometry
                for i in range(geom_index + 1, len(parts)):
                    token = parts[i]
                    # Skip identifier like (0x1e4)
                    if token.startswith("(0x"):
                        continue

                    if token in ["normal", "left", "right", "inverted"]:
                        rotation = token
                        break
                    if token.startswith("("):
                        # Hit the capabilities list, stop searching
                        break

            current_monitor = {
                "name": name,
                "primary": is_primary,
                "active": bool(geom_pos),
                "pos": None,
                "rotation": rotation,
                "active_mode": None,
                "rate": None
            }

            if geom_pos:
                # Extract mode and pos from string like 1920x1080+3146+0
                # mode: 1920x1080
                # pos: +3146+0 -> convert to 3146x0
                m = re.match(r"([0-9]+x[0-9]+)(\+[0-9]+\+[0-9]+)", geom_pos)
                if m:
                    current_monitor['active_mode'] = m.group(1)
                    raw_pos = m.group(2) # +3146+0
                    # Convert +X+Y to XxY
                    pm = re.match(r"\+(\d+)\+(\d+)", raw_pos)
                    if pm:
                        current_monitor['pos'] = f"{pm.group(1)}x{pm.group(2)}"

            continue

        # Rate line (looking for *)
        #   1920x1080 (0x1cc) 60.00*+ 119.88 ...
        if current_monitor and current_monitor['active'] and not current_monitor['rate']:
            if "*" in line:
                # This line contains the active rate
                # The first token usually is NOT the rate in verbose output?
                # In verbose: "  1920x1080 (0x1cc) 60.00*+ 119.88 ..." -> NO, verbose output is messy.
                # Let's fallback to standard xrandr for rate if needed, or parse carefully.
                # Standard xrandr: "   1920x1080     60.00*+ 119.88 ..."
                # Verbose: "  1920x1080 (0x1cc)  60.00*+  119.88 ..."

                # Simple strategy: find token with *
                tokens = line.split()
                for t in tokens:
                    if "*" in t:
                        rate = t.strip("*+")
                        current_monitor['rate'] = rate
                        break

    if current_monitor:
        monitors.append(current_monitor)

    return monitors

def save_state():
    log("Saving state...")
    if os.path.exists(STATE_FILE):
        log(f"State file {STATE_FILE} already exists. Skipping save to preserve original state.")
        return

    monitors = get_current_state()
    active_monitors = [m for m in monitors if m['active']]

    if not active_monitors:
        log("No active monitors found to save.")
        return

    command_parts = ["xrandr"]

    for m in active_monitors:
        command_parts.extend(["--output", m['name']])

        if m['primary']:
            command_parts.append("--primary")

        if m['active_mode']:
            command_parts.extend(["--mode", m['active_mode']])

        if m['rate']:
            command_parts.extend(["--rate", m['rate']])

        if m['pos']:
            command_parts.extend(["--pos", m['pos']])

        command_parts.extend(["--rotate", m['rotation']])

    full_command = " ".join(command_parts)
    log(f"Generated restore command: {full_command}")

    try:
        with open(STATE_FILE, "w") as f:
            f.write("#!/bin/bash\n")
            f.write(full_command + "\n")

        os.chmod(STATE_FILE, os.stat(STATE_FILE).st_mode | stat.S_IEXEC)
        log(f"State saved successfully to {STATE_FILE}")
    except IOError as e:
        log(f"Failed to write state file: {e}")
        sys.exit(1)

def restore_state():
    log("Restoring state...")
    if not os.path.exists(STATE_FILE):
        log(f"No state file found at {STATE_FILE}. Nothing to restore.")
        return

    try:
        log(f"Executing {STATE_FILE}...")
        subprocess.run(STATE_FILE, check=True, shell=True)
        log("State restored successfully.")
        os.remove(STATE_FILE)
        log(f"Deleted {STATE_FILE}")
    except subprocess.CalledProcessError as e:
        log(f"Failed to restore state: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ["save", "restore"]:
        print("Usage: python3 display_switch.py [save|restore]")
        sys.exit(1)

    # Ensure DISPLAY is set (heuristic)
    if "DISPLAY" not in os.environ:
        os.environ["DISPLAY"] = ":0"
        log("DISPLAY environment variable was missing, set to :0")

    if sys.argv[1] == "save":
        save_state()
    else:
        restore_state()