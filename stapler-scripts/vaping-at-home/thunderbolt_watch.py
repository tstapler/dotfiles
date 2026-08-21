#!/usr/bin/env python3
"""Writes Thunderbolt/USB4 device connection state and re-enumeration counts
as Prometheus textfile-collector metrics. Must run on the macOS host (not in
a container).

The Mac is wired via en7, a Thunderbolt Ethernet port on a CalDigit TS4 dock,
not built-in Ethernet - a dock disconnect/re-enumeration (bad cable seating,
firmware hiccup, power event) would drop the network exactly like a generic
outage from Google Meet's perspective, but needs a different signal to
diagnose. `system_profiler SPThunderboltDataType` enumerates the live device
tree; comparing it against the previous poll's state (persisted to
STATE_FILE) turns "device present/absent" into "device connected" (gauge)
and "device came back after being gone" (counter).

Run on a schedule (cron/launchd -- see README) so node-exporter's
`--collector.textfile.directory` always has a fresh reading.
"""
import json
import subprocess
from pathlib import Path

OUT_DIR = Path(__file__).parent / "textfile_collector"
OUT_FILE = OUT_DIR / "thunderbolt.prom"
STATE_FILE = Path("/tmp/vaping-thunderbolt-state.json")


def get_connected_devices():
    result = subprocess.run(
        ["system_profiler", "SPThunderboltDataType", "-json"],
        capture_output=True,
        check=True,
        text=True,
        timeout=10,
    )
    data = json.loads(result.stdout)

    devices = {}

    def walk(node):
        if isinstance(node, dict):
            vendor = node.get("vendor_name_key")
            name = node.get("_name")
            if vendor and vendor != "Apple Inc." and name:
                devices[name] = vendor
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return devices


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def update_state(state, connected_now):
    for name, vendor in connected_now.items():
        entry = state.get(name, {"vendor": vendor, "connected": False, "reenumerations": 0})
        if connected_now and not entry["connected"] and name in state:
            entry["reenumerations"] += 1
        entry["connected"] = True
        entry["vendor"] = vendor
        state[name] = entry
    for name, entry in state.items():
        if name not in connected_now:
            entry["connected"] = False
    return state


def render(state):
    lines = [
        "# HELP thunderbolt_device_connected Whether a Thunderbolt/USB4 device is currently enumerated (1) or was seen before but has disappeared (0)",
        "# TYPE thunderbolt_device_connected gauge",
    ]
    for name, entry in sorted(state.items()):
        state_value = 1 if entry["connected"] else 0
        lines.append(
            f'thunderbolt_device_connected{{name="{name}",vendor="{entry["vendor"]}"}} {state_value}'
        )
    lines += [
        "# HELP thunderbolt_device_reenumerations_total Number of times this device has disappeared and come back since the watcher started",
        "# TYPE thunderbolt_device_reenumerations_total counter",
    ]
    for name, entry in sorted(state.items()):
        lines.append(
            f'thunderbolt_device_reenumerations_total{{name="{name}",vendor="{entry["vendor"]}"}} {entry["reenumerations"]}'
        )
    lines.append("")
    return "\n".join(lines)


def main():
    connected_now = get_connected_devices()
    state = update_state(load_state(), connected_now)
    STATE_FILE.write_text(json.dumps(state))

    OUT_DIR.mkdir(exist_ok=True)
    tmp_file = OUT_FILE.with_suffix(".prom.tmp")
    tmp_file.write_text(render(state))
    tmp_file.rename(OUT_FILE)


if __name__ == "__main__":
    main()
