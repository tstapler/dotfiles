#!/usr/bin/env python3
"""Writes current Wi-Fi RSSI/noise/tx-rate as Prometheus textfile-collector
metrics. Must run on the macOS host (not in a container): Docker Desktop's
LinuxKit VM has no Wi-Fi hardware to query, and `system_profiler
SPAirPortDataType` is a macOS-only command anyway.

Run on a schedule (cron/launchd -- see README) so node-exporter's
`--collector.textfile.directory` always has a fresh reading.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

OUT_DIR = Path(__file__).parent / "textfile_collector"
OUT_FILE = OUT_DIR / "wifi_signal.prom"


def get_wifi_info():
    result = subprocess.run(
        ["system_profiler", "SPAirPortDataType", "-json"],
        capture_output=True,
        check=True,
        text=True,
    )
    data = json.loads(result.stdout)
    interfaces = data.get("SPAirPortDataType", [{}])[0].get(
        "spairport_airport_interfaces", []
    )
    for iface in interfaces:
        info = iface.get("spairport_current_network_information")
        if info:
            return info
    return None


def parse_signal_noise(value):
    match = re.match(r"(-?\d+)\s*dBm\s*/\s*(-?\d+)\s*dBm", value or "")
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def render(info):
    ssid = info.get("_name", "unknown").replace('"', "'")
    rssi, noise = parse_signal_noise(info.get("spairport_signal_noise"))
    rate = info.get("spairport_network_rate")

    lines = []
    if rssi is not None:
        lines += [
            "# HELP wifi_rssi_dbm Wi-Fi RSSI signal strength in dBm",
            "# TYPE wifi_rssi_dbm gauge",
            f'wifi_rssi_dbm{{ssid="{ssid}"}} {rssi}',
        ]
    if noise is not None:
        lines += [
            "# HELP wifi_noise_dbm Wi-Fi noise floor in dBm",
            "# TYPE wifi_noise_dbm gauge",
            f'wifi_noise_dbm{{ssid="{ssid}"}} {noise}',
        ]
    if rate is not None:
        lines += [
            "# HELP wifi_tx_rate_mbps Wi-Fi last negotiated transmit rate in Mbps",
            "# TYPE wifi_tx_rate_mbps gauge",
            f'wifi_tx_rate_mbps{{ssid="{ssid}"}} {rate}',
        ]
    return "\n".join(lines) + "\n" if lines else ""


def main():
    info = get_wifi_info()
    if not info:
        print("not connected to Wi-Fi, skipping write", file=sys.stderr)
        return

    OUT_DIR.mkdir(exist_ok=True)
    tmp_file = OUT_FILE.with_suffix(".prom.tmp")
    tmp_file.write_text(render(info))
    tmp_file.rename(OUT_FILE)


if __name__ == "__main__":
    main()
