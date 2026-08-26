#!/usr/bin/env python3
"""Writes per-process RSS/CPU/count as Prometheus textfile-collector metrics.
Must run on the macOS host (not in a container).

Which processes to watch is host-specific config, not hardcoded: every
*.yaml file under config.d/process_watch.d/ declares a `label` and a `match`
substring checked against each running process's full command line (`ps -o
command`), plus an optional `hosts` allowlist (exact hostname match) so an
entry only takes effect on the machines it applies to -- e.g. the
CrowdStrike Falcon watch only makes sense on hosts that actually run
falcond. Entries with no `hosts` key apply everywhere.

Run on a schedule (cron/launchd -- see README) so node-exporter's
`--collector.textfile.directory` always has a fresh reading.
"""
import socket
import subprocess
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).parent / "config.d" / "process_watch.d"
OUT_DIR = Path(__file__).parent / "textfile_collector"
OUT_FILE = OUT_DIR / "process_watch.prom"


def load_targets():
    hostname = socket.gethostname().split(".")[0]
    targets = []
    for config_file in sorted(CONFIG_DIR.glob("*.yaml")):
        entry = yaml.safe_load(config_file.read_text())
        hosts = entry.get("hosts")
        if hosts and hostname not in hosts:
            continue
        targets.append((entry["label"], entry["match"]))
    return targets


def get_processes():
    result = subprocess.run(
        ["ps", "-axo", "pid=,rss=,%cpu=,command="],
        capture_output=True,
        check=True,
        text=True,
    )
    processes = []
    for line in result.stdout.splitlines():
        pid, rss_kb, cpu, command = line.split(maxsplit=3)
        processes.append((int(rss_kb), float(cpu), command))
    return processes


def collect(targets, processes):
    stats = {}
    for label, match in targets:
        matched = [p for p in processes if match in p[2]]
        stats[label] = {
            "rss_bytes": sum(rss_kb for rss_kb, _, _ in matched) * 1024,
            "cpu_percent": sum(cpu for _, cpu, _ in matched),
            "count": len(matched),
        }
    return stats


def render(stats):
    lines = [
        "# HELP process_watch_rss_bytes Sum of RSS across all processes matching this watch's config",
        "# TYPE process_watch_rss_bytes gauge",
    ]
    for label, entry in sorted(stats.items()):
        lines.append(f'process_watch_rss_bytes{{label="{label}"}} {entry["rss_bytes"]}')
    lines += [
        "# HELP process_watch_cpu_percent Sum of %CPU across all processes matching this watch's config",
        "# TYPE process_watch_cpu_percent gauge",
    ]
    for label, entry in sorted(stats.items()):
        lines.append(f'process_watch_cpu_percent{{label="{label}"}} {entry["cpu_percent"]}')
    lines += [
        "# HELP process_watch_count Number of running processes matching this watch's config",
        "# TYPE process_watch_count gauge",
    ]
    for label, entry in sorted(stats.items()):
        lines.append(f'process_watch_count{{label="{label}"}} {entry["count"]}')
    lines.append("")
    return "\n".join(lines)


def main():
    targets = load_targets()
    stats = collect(targets, get_processes())

    OUT_DIR.mkdir(exist_ok=True)
    tmp_file = OUT_FILE.with_suffix(".prom.tmp")
    tmp_file.write_text(render(stats))
    tmp_file.rename(OUT_FILE)


if __name__ == "__main__":
    main()
