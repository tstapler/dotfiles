#!/usr/bin/env python3
"""Writes per-interface up/down state as a Prometheus textfile-collector
metric. Must run on the macOS host (not in a container).

node_exporter's darwin netdev collector reports byte/packet/error counters
per interface but has no equivalent of Linux's `node_network_up` (there's no
macOS sysfs `operstate` to read) - this fills that one gap so interface
state changes (e.g. Wi-Fi toggled off, cable unplugged) show up as a metric
instead of only being inferrable from traffic going to zero.

Run on a schedule (cron/launchd -- see README) so node-exporter's
`--collector.textfile.directory` always has a fresh reading.
"""
import re
import subprocess
from pathlib import Path

OUT_DIR = Path(__file__).parent / "textfile_collector"
OUT_FILE = OUT_DIR / "interface_state.prom"


def get_hardware_ports():
    result = subprocess.run(
        ["networksetup", "-listallhardwareports"],
        capture_output=True,
        check=True,
        text=True,
    )
    ports = {}
    for block in result.stdout.split("\n\n"):
        name_match = re.search(r"Hardware Port:\s*(.+)", block)
        device_match = re.search(r"Device:\s*(\S+)", block)
        if name_match and device_match:
            ports[device_match.group(1)] = name_match.group(1).strip()
    return ports


def is_active(device):
    result = subprocess.run(["ifconfig", device], capture_output=True, text=True)
    return "status: active" in result.stdout


def render(ports):
    lines = [
        "# HELP host_interface_up Whether the network interface reports status: active (1) or not (0)",
        "# TYPE host_interface_up gauge",
    ]
    for device, hardware_port in sorted(ports.items()):
        state = 1 if is_active(device) else 0
        lines.append(
            f'host_interface_up{{device="{device}",hardware_port="{hardware_port}"}} {state}'
        )
    lines.append("")
    return "\n".join(lines)


def main():
    ports = get_hardware_ports()
    OUT_DIR.mkdir(exist_ok=True)
    tmp_file = OUT_FILE.with_suffix(".prom.tmp")
    tmp_file.write_text(render(ports))
    tmp_file.rename(OUT_FILE)


if __name__ == "__main__":
    main()
