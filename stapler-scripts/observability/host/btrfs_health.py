#!/usr/bin/env python3
"""Writes btrfs allocation/health as Prometheus textfile-collector metrics.
Linux only; reads /sys/fs/btrfs directly (no root, no btrfs-progs).

Exists because node_exporter's btrfs collector omits bytes_may_use, pinned and
readonly bytes, and global_rsv_reserved -- exactly the terms that decide whether
metadata writes block (2026-11-01 incident: raw total-used looked like 529 MiB
while usable headroom was negative). `btrfs_metadata_usable_headroom_bytes`
subtracts them.

Which hosts/filesystems to watch is per-host config: every *.yaml under
config.d/btrfs_health.d/ may carry a `hosts` allowlist (exact hostname) and an
optional `uuids` list (default: every btrfs filesystem found). With no matching
config the script writes nothing, so it is harmless on hosts without btrfs.

Run on a schedule (systemd/btrfs-health.timer) so node_exporter's
`--collector.textfile.directory` always has a fresh reading.
"""
import argparse
import os
import socket
import sys
import time
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).parent / "config.d" / "btrfs_health.d"
DEFAULT_OUT_DIR = Path(__file__).parent / "textfile_collector"
DEFAULT_SYSFS = Path("/sys/fs/btrfs")
OUT_NAME = "btrfs_health.prom"

ERROR_KINDS = ("write", "read", "flush", "corruption", "generation")
SPACE_FIELDS = ("total_bytes", "bytes_used", "disk_total", "bytes_reserved",
                "bytes_pinned", "bytes_readonly", "bytes_may_use")
SECTOR_BYTES = 512  # devices/<dev>/size is in 512-byte sectors regardless of device sector size


def _read(path: Path):
    try:
        return path.read_text().strip()
    except OSError:
        return None


def _read_int(path: Path):
    raw = _read(path)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def load_config(hostname, config_dir=CONFIG_DIR):
    """Returns the merged uuid filter (None = all) or False if no config applies."""
    matched, uuids = False, set()
    for config_file in sorted(config_dir.glob("*.yaml")):
        entry = yaml.safe_load(config_file.read_text()) or {}
        hosts = entry.get("hosts")
        if hosts and hostname not in hosts:
            continue
        matched = True
        if entry.get("uuids"):
            uuids.update(entry["uuids"])
        else:
            return None
    return uuids if matched else False


def find_filesystems(sysfs, uuids=None):
    found = []
    if not sysfs.is_dir():
        return found
    for fs in sorted(sysfs.iterdir()):
        if (fs / "allocation").is_dir() and (uuids is None or fs.name in uuids):
            found.append(fs)
    return found


def read_filesystem(fs: Path):
    """Raw sysfs values for one filesystem. Missing files become None, not errors."""
    alloc = fs / "allocation"
    types = {}
    for type_dir in sorted(p for p in alloc.iterdir() if p.is_dir()):
        types[type_dir.name] = {f: _read_int(type_dir / f) for f in SPACE_FIELDS}

    devices = {}
    devices_dir = fs / "devices"
    if devices_dir.is_dir():
        for dev in sorted(devices_dir.iterdir()):
            sectors = _read_int(dev / "size")
            if sectors is not None:
                devices[dev.name] = sectors * SECTOR_BYTES

    errors, missing = {}, {}
    devinfo = fs / "devinfo"
    if devinfo.is_dir():
        for dev in sorted(devinfo.iterdir()):
            stats = {}
            for line in (_read(dev / "error_stats") or "").splitlines():
                key, _, value = line.partition(" ")
                if key.endswith("_errs") and value.strip().isdigit():
                    stats[key[: -len("_errs")]] = int(value)
            errors[dev.name] = stats
            missing[dev.name] = _read_int(dev / "missing")

    return {
        "uuid": fs.name,
        "types": types,
        "devices": devices,
        "errors": errors,
        "missing": missing,
        "global_rsv_size": _read_int(alloc / "global_rsv_size"),
        "global_rsv_reserved": _read_int(alloc / "global_rsv_reserved"),
        "exclusive_operation": _read(fs / "exclusive_operation"),
    }


def unallocated_bytes(raw):
    """Device bytes not assigned to any chunk. disk_total already counts DUP/RAID copies."""
    if not raw["devices"]:
        return None
    allocated = sum(t["disk_total"] or 0 for t in raw["types"].values())
    return sum(raw["devices"].values()) - allocated


def metadata_headroom_bytes(raw):
    """Metadata bytes a normal write can still use; negative means writes will block.

    Conservative on purpose: the kernel may already count the global reserve inside
    bytes_may_use, so this can read low (false alarm) but not high (missed freeze).
    """
    meta = raw["types"].get("metadata")
    if not meta or meta["total_bytes"] is None:
        return None
    held = sum(meta[f] or 0 for f in
               ("bytes_used", "bytes_reserved", "bytes_pinned", "bytes_readonly", "bytes_may_use"))
    return meta["total_bytes"] - held - (raw["global_rsv_size"] or 0)


PSEUDO_FSTYPES = {
    "proc", "sysfs", "devtmpfs", "tmpfs", "devpts", "cgroup", "cgroup2", "securityfs", "debugfs", "tracefs",
    "configfs", "fusectl", "efivarfs", "bpf", "pstore", "mqueue", "hugetlbfs", "autofs", "binfmt_misc",
    "overlay", "squashfs", "ramfs", "nsfs",
}


def parse_mountinfo(text):
    """(mountpoint, fstype, source) for real filesystems; one entry per source so btrfs subvolume mounts collapse."""
    best = {}
    for line in text.splitlines():
        left, sep, right = line.partition(" - ")
        fields, rest = left.split(), right.split()
        if not sep or len(fields) < 5 or len(rest) < 2:
            continue
        fstype, source = rest[0], rest[1]
        if fstype in PSEUDO_FSTYPES or fstype.startswith("fuse."):
            continue
        mountpoint = fields[4].replace("\\040", " ")
        key = (source, fstype)
        if key not in best or len(mountpoint) < len(best[key][0]):
            best[key] = (mountpoint, fstype, source)
    return sorted(best.values())


def read_mount_stats(mounts, statvfs=os.statvfs):
    stats = []
    for mountpoint, fstype, source in mounts:
        try:
            st = statvfs(mountpoint)
        except OSError:
            continue
        stats.append({"mountpoint": mountpoint, "fstype": fstype, "device": source,
                      "size": st.f_blocks * st.f_frsize, "avail": st.f_bavail * st.f_frsize,
                      "files": st.f_files, "files_free": st.f_ffree})
    return stats


class _Writer:
    def __init__(self):
        self.lines = []
        self._declared = set()

    def sample(self, name, help_text, labels, value, kind="gauge"):
        if value is None:
            return
        if name not in self._declared:
            self._declared.add(name)
            self.lines += [f"# HELP {name} {help_text}", f"# TYPE {name} {kind}"]
        label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
        self.lines.append(f"{name}{{{label_str}}} {value}")


def render(filesystems, now, mount_stats=()):
    w = _Writer()
    block_group = [
        ("total_bytes", "btrfs_block_group_total_bytes", "Logical size of all block groups of this type"),
        ("bytes_used", "btrfs_block_group_used_bytes", "Bytes in use inside block groups of this type"),
        ("disk_total", "btrfs_block_group_disk_total_bytes", "Raw device bytes consumed by this type, including DUP/RAID copies"),
        ("bytes_reserved", "btrfs_block_group_reserved_bytes", "Bytes reserved for in-flight allocations"),
        ("bytes_pinned", "btrfs_block_group_pinned_bytes", "Bytes pinned until the current transaction commits"),
        ("bytes_readonly", "btrfs_block_group_readonly_bytes", "Bytes in read-only block groups"),
        ("bytes_may_use", "btrfs_block_group_may_use_bytes", "Bytes promised to pending reservations"),
    ]
    for raw in filesystems:
        uuid = raw["uuid"]
        for type_name, fields in raw["types"].items():
            for field, metric, help_text in block_group:
                w.sample(metric, help_text, {"uuid": uuid, "type": type_name}, fields[field])
        for dev, size in raw["devices"].items():
            w.sample("btrfs_device_size_bytes", "Size of the member device", {"uuid": uuid, "device": dev}, size)
        w.sample("btrfs_unallocated_bytes", "Device bytes not assigned to any chunk", {"uuid": uuid}, unallocated_bytes(raw))
        w.sample("btrfs_metadata_usable_headroom_bytes",
                 "Metadata total minus used, reserved, pinned, readonly, may_use and global reserve; negative blocks writes",
                 {"uuid": uuid}, metadata_headroom_bytes(raw))
        w.sample("btrfs_global_reserve_size_bytes", "Global block reserve size", {"uuid": uuid}, raw["global_rsv_size"])
        w.sample("btrfs_global_reserve_reserved_bytes", "Global block reserve bytes currently held", {"uuid": uuid}, raw["global_rsv_reserved"])
        for devid, stats in raw["errors"].items():
            for kind in ERROR_KINDS:
                w.sample("btrfs_device_errors_total", "Cumulative btrfs device error counter from sysfs error_stats",
                         {"uuid": uuid, "devid": devid, "type": kind}, stats.get(kind), kind="counter")
        for devid, value in raw["missing"].items():
            w.sample("btrfs_device_missing", "1 if the member device is missing", {"uuid": uuid, "devid": devid}, value)
        op = raw["exclusive_operation"]
        if op is not None:
            # Scrub is not an exclusive operation and its status needs root, so only balance is observable here.
            w.sample("btrfs_exclusive_operation", "1 for the exclusive operation currently running (none/balance/...)",
                     {"uuid": uuid, "operation": op}, 1)
            w.sample("btrfs_balance_running", "1 while a balance is actively running", {"uuid": uuid}, int(op == "balance"))
    for m in mount_stats:
        labels = {"mountpoint": m["mountpoint"], "fstype": m["fstype"], "device": m["device"]}
        w.sample("host_filesystem_size_bytes", "statfs total size", labels, m["size"])
        w.sample("host_filesystem_avail_bytes", "statfs bytes available to unprivileged users", labels, m["avail"])
        if m["files"]:  # btrfs reports 0 inodes: it allocates them dynamically
            w.sample("host_filesystem_files", "statfs total inodes", labels, m["files"])
            w.sample("host_filesystem_files_free", "statfs free inodes", labels, m["files_free"])
    w.sample("btrfs_exporter_filesystems", "Number of btrfs filesystems read in the last run", {}, len(filesystems))
    w.sample("btrfs_exporter_last_success_timestamp_seconds", "Unix time of the last completed run", {}, int(now))
    return "\n".join(w.lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sysfs-root", type=Path, default=DEFAULT_SYSFS)
    parser.add_argument("--mountinfo", type=Path, default=Path("/proc/self/mountinfo"))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--config-dir", type=Path, default=CONFIG_DIR)
    parser.add_argument("--stdout", action="store_true", help="print instead of writing the .prom file")
    args = parser.parse_args(argv)

    uuids = load_config(socket.gethostname().split(".")[0], args.config_dir)
    if uuids is False:
        print("btrfs_health: no config.d/btrfs_health.d entry matches this host; nothing to do", file=sys.stderr)
        return 0
    filesystems = [read_filesystem(fs) for fs in find_filesystems(args.sysfs_root, uuids)]
    mounts = read_mount_stats(parse_mountinfo(args.mountinfo.read_text())) if args.mountinfo.exists() else []
    text = render(filesystems, time.time(), mounts)

    if args.stdout:
        sys.stdout.write(text)
        return 0
    args.output_dir.mkdir(exist_ok=True)
    out = args.output_dir / OUT_NAME
    tmp = out.with_suffix(".prom.tmp")
    tmp.write_text(text)
    tmp.chmod(0o644)  # the Alloy container reads it as a different uid
    tmp.rename(out)  # atomic so node_exporter never scrapes a half-written file
    return 0


if __name__ == "__main__":
    sys.exit(main())
