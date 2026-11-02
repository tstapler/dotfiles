"""Tests for btrfs_health.py against a sysfs fixture tree, never live /sys.

Run: uv run --with pytest --with pyyaml pytest tests/
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import btrfs_health as bh  # noqa: E402

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "sysfs_btrfs"
UUID = "df821037-344f-4c7d-b593-ca292893058e"


def _write(path: Path, content) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(content))


def _incident_fs(root: Path) -> Path:
    """Metadata 25G used of 26G total, 512 MiB global reserve, ~1 MiB unallocated."""
    gib = 1 << 30
    fs = root / "incident"
    _write(fs / "allocation/global_rsv_size", 512 << 20)
    _write(fs / "allocation/global_rsv_reserved", 512 << 20)
    meta = {"total_bytes": 26 * gib, "bytes_used": 25 * gib, "disk_total": 52 * gib,
            "bytes_reserved": 100 << 20, "bytes_pinned": 0, "bytes_readonly": 0, "bytes_may_use": 800 << 20}
    for field, value in meta.items():
        _write(fs / "allocation/metadata" / field, value)
    _write(fs / "allocation/data/total_bytes", 1000 * gib)
    _write(fs / "allocation/data/disk_total", 1000 * gib)
    device_bytes = (1000 + 52) * gib + (1 << 20) + 67108864  # leaves 1 MiB beyond the system chunk
    _write(fs / "allocation/system/total_bytes", 33554432)
    _write(fs / "allocation/system/disk_total", 67108864)
    _write(fs / "devices/sda1/size", device_bytes // 512)
    return fs


def test_raw_headroom_looks_healthy_but_usable_headroom_is_negative(tmp_path):
    raw = bh.read_filesystem(_incident_fs(tmp_path))

    meta = raw["types"]["metadata"]
    assert meta["total_bytes"] - meta["bytes_used"] == 1 << 30  # what a naive total-used check sees
    assert bh.metadata_headroom_bytes(raw) < 0
    assert bh.unallocated_bytes(raw) == 1 << 20


def test_fixture_matches_hand_computed_values():
    raw = bh.read_filesystem(FIXTURE_ROOT / UUID)

    assert bh.unallocated_bytes(raw) == 75163009536
    assert bh.metadata_headroom_bytes(raw) == 3470671872
    assert raw["devices"] == {"nvme0n1p2": 3906405569 * 512}
    assert raw["errors"]["1"]["corruption"] == 14586
    assert raw["errors"]["1"]["write"] == 0
    assert raw["exclusive_operation"] == "balance"
    assert raw["global_rsv_size"] == raw["global_rsv_reserved"] == 536870912


def test_render_emits_expected_series():
    text = bh.render([bh.read_filesystem(FIXTURE_ROOT / UUID)], now=1_700_000_000)

    assert f'btrfs_block_group_disk_total_bytes{{uuid="{UUID}",type="metadata"}} 61287170048' in text
    assert f'btrfs_unallocated_bytes{{uuid="{UUID}"}} 75163009536' in text
    assert f'btrfs_metadata_usable_headroom_bytes{{uuid="{UUID}"}} 3470671872' in text
    assert f'btrfs_device_errors_total{{uuid="{UUID}",devid="1",type="corruption"}} 14586' in text
    assert f'btrfs_balance_running{{uuid="{UUID}"}} 1' in text
    assert "btrfs_exporter_last_success_timestamp_seconds{} 1700000000" in text
    assert text.count("# TYPE btrfs_device_errors_total counter") == 1


def test_missing_sysfs_files_are_skipped_not_fatal(tmp_path):
    fs = tmp_path / "bare"
    _write(fs / "allocation/metadata/total_bytes", 100)

    text = bh.render([bh.read_filesystem(fs)], now=1)

    assert 'btrfs_block_group_total_bytes{uuid="bare",type="metadata"} 100' in text
    assert "btrfs_unallocated_bytes" not in text  # no devices, so no honest value


def test_find_filesystems_honours_uuid_filter(tmp_path):
    _write(tmp_path / "aaa/allocation/data/total_bytes", 1)
    _write(tmp_path / "bbb/allocation/data/total_bytes", 1)
    (tmp_path / "features").mkdir()  # non-filesystem sibling, as in real /sys/fs/btrfs

    assert [p.name for p in bh.find_filesystems(tmp_path)] == ["aaa", "bbb"]
    assert [p.name for p in bh.find_filesystems(tmp_path, {"bbb"})] == ["bbb"]


def test_load_config_host_allowlist(tmp_path):
    _write(tmp_path / "a.yaml", "hosts: [onyx]\n")
    _write(tmp_path / "b.yaml", "hosts: [other]\nuuids: [x]\n")

    assert bh.load_config("onyx", tmp_path) is None  # matched, all filesystems
    assert bh.load_config("laptop", tmp_path) is False  # nothing applies


def test_main_writes_atomically_to_output_dir(tmp_path):
    out = tmp_path / "out"
    cfg = tmp_path / "cfg"
    _write(cfg / "any.yaml", "{}\n")

    assert bh.main(["--sysfs-root", str(FIXTURE_ROOT), "--mountinfo", str(tmp_path / "none"), "--output-dir", str(out), "--config-dir", str(cfg)]) == 0

    assert (out / "btrfs_health.prom").exists()
    assert not list(out.glob("*.tmp"))


MOUNTINFO = r"""22 28 0:21 / /sys rw - sysfs sys rw
24 28 0:22 / /run rw - tmpfs run rw
26 1 0:26 / / rw - btrfs /dev/nvme0n1p2 rw,subvolid=256
27 26 0:26 /@home /home rw - btrfs /dev/nvme0n1p2 rw,subvolid=257
30 26 259:1 / /boot/efi rw - vfat /dev/nvme0n1p1 rw
31 26 0:40 / /mnt/with\040space rw - ext4 /dev/sdb1 rw
32 26 0:41 / /run/user/1000/doc rw - fuse.portal portal rw
"""


def test_parse_mountinfo_skips_pseudo_and_collapses_subvolumes():
    assert bh.parse_mountinfo(MOUNTINFO) == [
        ("/", "btrfs", "/dev/nvme0n1p2"),
        ("/boot/efi", "vfat", "/dev/nvme0n1p1"),
        ("/mnt/with space", "ext4", "/dev/sdb1"),
    ]


def test_mount_stats_render_and_skip_zero_inodes():
    class St:
        f_blocks, f_bavail, f_frsize, f_files, f_ffree = 1000, 400, 4096, 0, 0

    def fake_statvfs(mountpoint):
        if mountpoint != "/":
            raise OSError("gone")
        return St

    stats = bh.read_mount_stats([("/", "btrfs", "/dev/x"), ("/gone", "ext4", "/dev/y")], statvfs=fake_statvfs)
    text = bh.render([], now=1, mount_stats=stats)

    assert 'host_filesystem_size_bytes{mountpoint="/",fstype="btrfs",device="/dev/x"} 4096000' in text
    assert 'host_filesystem_avail_bytes{mountpoint="/",fstype="btrfs",device="/dev/x"} 1638400' in text
    assert "host_filesystem_files" not in text and "/gone" not in text
