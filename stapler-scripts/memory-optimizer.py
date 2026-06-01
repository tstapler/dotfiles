#!/usr/bin/env python3
"""
memory-optimizer: Detect and interactively apply Linux memory optimizations.

Covers: zswap, zram, KSM deduplication, Transparent Huge Pages, MGLRU
tuning, vm.swappiness, swap file creation, and DAMON proactive reclaim.

Run as your normal user — sudo is invoked per-operation.
"""

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


# ── terminal helpers ──────────────────────────────────────────────────────────

def bold(s: str) -> str:   return f"\033[1m{s}\033[0m"
def green(s: str) -> str:  return f"\033[32m{s}\033[0m"
def yellow(s: str) -> str: return f"\033[33m{s}\033[0m"
def red(s: str) -> str:    return f"\033[31m{s}\033[0m"
def dim(s: str) -> str:    return f"\033[2m{s}\033[0m"


def header(title: str):
    print(f"\n{bold(title)}")
    print("─" * len(title))


def ask(prompt: str, default: bool = True) -> bool:
    suffix = " [Y/n] " if default else " [y/N] "
    try:
        ans = input(f"  {prompt}{suffix}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return ans.startswith("y") if ans else default


# ── low-level helpers ─────────────────────────────────────────────────────────

def read_file(path: str, default: str = "") -> str:
    try:
        return Path(path).read_text().strip()
    except OSError:
        return default


def sysctl(key: str) -> str:
    try:
        return subprocess.check_output(
            ["sysctl", "-n", key], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def sudo_run(*cmd: str, input: str = None) -> bool:
    """Run a command with sudo. Returns True on success."""
    result = subprocess.run(
        ["sudo", *cmd],
        input=input,
        text=True if input is not None else False,
    )
    return result.returncode == 0


def sudo_tee(path: str, content: str) -> bool:
    """Write content to a system path via sudo tee."""
    result = subprocess.run(
        ["sudo", "tee", path],
        input=content,
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def sudo_tee_append(path: str, line: str) -> bool:
    """Append a line to a system path via sudo tee -a."""
    result = subprocess.run(
        ["sudo", "tee", "-a", path],
        input=line if line.endswith("\n") else line + "\n",
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def check_sudo_available() -> bool:
    return subprocess.run(["sudo", "-n", "true"], capture_output=True).returncode == 0


# ── system detection ──────────────────────────────────────────────────────────

@dataclass
class SystemInfo:
    # Memory
    ram_kb: int = 0
    ram_gb: float = 0.0
    swap_total_kb: int = 0
    swap_devices: list = field(default_factory=list)

    # Storage
    has_nvme: bool = False
    root_free_gb: float = 0.0

    # Kernel & distro
    kernel_version: str = ""
    kernel_major: int = 0
    kernel_minor: int = 0
    distro_id: str = ""
    distro_name: str = ""
    pkg_manager: str = ""   # pacman | apt | dnf | zypper | ""

    # zram
    zram_active: bool = False
    zram_devices: list = field(default_factory=list)
    zram_generator_installed: bool = False

    # zswap
    zswap_enabled: bool = False
    zswap_compressor: str = ""
    zswap_max_pool_percent: int = 0

    # KSM
    ksm_available: bool = False
    ksm_run: int = 0
    ksm_pages_to_scan: int = 0
    ksm_pages_shared: int = 0
    ksm_pages_sharing: int = 0

    # THP
    thp_enabled: str = ""   # always | madvise | never
    thp_defrag: str = ""

    # vm params
    vm_swappiness: int = 60
    vm_page_cluster: int = 3
    vm_watermark_scale: int = 10

    # MGLRU
    mglru_enabled: bool = False
    mglru_min_ttl_ms: int = 0

    # DAMON
    damon_reclaim_available: bool = False
    damon_reclaim_enabled: bool = False


def _extract_bracket(raw: str) -> str:
    """Extract the [selected] option from a sysfs file like 'always [madvise] never'."""
    m = re.search(r"\[(.+?)\]", raw)
    return m.group(1) if m else raw.split()[0] if raw else ""


def detect() -> SystemInfo:
    info = SystemInfo()

    # Memory
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemTotal:"):
            info.ram_kb = int(line.split()[1])
        elif line.startswith("SwapTotal:"):
            info.swap_total_kb = int(line.split()[1])
    info.ram_gb = info.ram_kb / 1024 / 1024

    # Swap devices
    try:
        lines = Path("/proc/swaps").read_text().splitlines()[1:]
        info.swap_devices = [l.split()[0] for l in lines if l.strip()]
    except OSError:
        pass

    # NVMe
    info.has_nvme = bool(list(Path("/sys/block").glob("nvme*")))

    # Disk space
    st = os.statvfs("/")
    info.root_free_gb = (st.f_bavail * st.f_frsize) / (1024 ** 3)

    # Kernel version
    info.kernel_version = read_file("/proc/sys/kernel/osrelease")
    m = re.search(r"(\d+)\.(\d+)", info.kernel_version)
    if m:
        info.kernel_major, info.kernel_minor = int(m.group(1)), int(m.group(2))

    # Distro
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if line.startswith("ID="):
                info.distro_id = line.split("=", 1)[1].strip().strip('"').lower()
            elif line.startswith("PRETTY_NAME="):
                info.distro_name = line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass

    for pm, cmd in [("pacman","pacman"),("apt","apt-get"),("dnf","dnf"),("zypper","zypper")]:
        if shutil.which(cmd):
            info.pkg_manager = pm
            break

    # zram
    zram_devs = list(Path("/sys/block").glob("zram*"))
    info.zram_devices = [d.name for d in zram_devs]
    info.zram_active = bool(zram_devs)
    if info.pkg_manager == "pacman":
        info.zram_generator_installed = (
            subprocess.run(["pacman", "-Q", "zram-generator"], capture_output=True).returncode == 0
        )
    elif shutil.which("dpkg"):
        info.zram_generator_installed = (
            subprocess.run(["dpkg", "-l", "systemd-zram-generator"], capture_output=True).returncode == 0
        )

    # zswap
    zswap_params = Path("/sys/module/zswap/parameters")
    if zswap_params.exists():
        info.zswap_enabled = read_file(str(zswap_params / "enabled")) == "Y"
        info.zswap_compressor = read_file(str(zswap_params / "compressor"))
        pct = read_file(str(zswap_params / "max_pool_percent"))
        info.zswap_max_pool_percent = int(pct) if pct.isdigit() else 0
    if "zswap.enabled=1" in read_file("/proc/cmdline"):
        info.zswap_enabled = True

    # KSM
    ksm_base = Path("/sys/kernel/mm/ksm")
    info.ksm_available = ksm_base.exists()
    if info.ksm_available:
        info.ksm_run = int(read_file(str(ksm_base / "run"), "0"))
        info.ksm_pages_to_scan = int(read_file(str(ksm_base / "pages_to_scan"), "0"))
        info.ksm_pages_shared = int(read_file(str(ksm_base / "pages_shared"), "0"))
        info.ksm_pages_sharing = int(read_file(str(ksm_base / "pages_sharing"), "0"))

    # THP
    thp_base = Path("/sys/kernel/mm/transparent_hugepage")
    if thp_base.exists():
        info.thp_enabled = _extract_bracket(read_file(str(thp_base / "enabled")))
        info.thp_defrag  = _extract_bracket(read_file(str(thp_base / "defrag")))

    # vm params
    info.vm_swappiness    = int(sysctl("vm.swappiness")           or "60")
    info.vm_page_cluster  = int(sysctl("vm.page-cluster")         or "3")
    info.vm_watermark_scale = int(sysctl("vm.watermark_scale_factor") or "10")

    # MGLRU (Linux 6.1+)
    mglru_enabled_path = Path("/sys/kernel/mm/lru_gen/enabled")
    if mglru_enabled_path.exists():
        raw = read_file(str(mglru_enabled_path))
        try:
            val = int(raw, 16) if raw.startswith("0x") else int(raw)
            info.mglru_enabled = val != 0
        except ValueError:
            info.mglru_enabled = False
        info.mglru_min_ttl_ms = int(
            read_file("/sys/kernel/mm/lru_gen/min_ttl_ms", "0")
        )

    # DAMON (Linux 5.15+)
    damon_mod = Path("/sys/module/damon_reclaim")
    info.damon_reclaim_available = damon_mod.exists()
    if info.damon_reclaim_available:
        info.damon_reclaim_enabled = (
            read_file(str(damon_mod / "parameters" / "enabled"), "N") == "Y"
        )

    return info


def print_summary(info: SystemInfo):
    header("System Summary")
    print(f"  {'OS':<18} {info.distro_name} (kernel {info.kernel_version})")
    print(f"  {'RAM':<18} {info.ram_gb:.1f} GB")

    swap_str = (f"{info.swap_total_kb // 1024} MB  {dim(str(info.swap_devices))}"
                if info.swap_total_kb else red("none"))
    print(f"  {'Swap':<18} {swap_str}")
    print(f"  {'NVMe':<18} {'yes' if info.has_nvme else 'no'}")
    print(f"  {'Free disk':<18} {info.root_free_gb:.1f} GB")

    zswap_str = (green(f"enabled  compressor={info.zswap_compressor} pool={info.zswap_max_pool_percent}%")
                 if info.zswap_enabled else red("disabled"))
    print(f"  {'zswap':<18} {zswap_str}")

    zram_str  = (green(f"active  {info.zram_devices}") if info.zram_active else "inactive")
    print(f"  {'zram':<18} {zram_str}")

    if info.ksm_available:
        if info.ksm_run:
            savings_mb = max(0, info.ksm_pages_sharing - info.ksm_pages_shared) * 4 // 1024
            ksm_str = green(f"active  {info.ksm_pages_sharing} sharing / {info.ksm_pages_shared} shared  (~{savings_mb} MB saved)")
        else:
            ksm_str = red("inactive")
        print(f"  {'KSM':<18} {ksm_str}")

    print(f"  {'THP':<18} {info.thp_enabled or 'unknown'}  defrag={info.thp_defrag or 'unknown'}")
    print(f"  {'MGLRU':<18} {green('active') if info.mglru_enabled else yellow('inactive (upgrade kernel to 6.1+)')}")
    print(f"  {'DAMON reclaim':<18} {'available' if info.damon_reclaim_available else dim('not in kernel')}"
          + (f"  {green('enabled') if info.damon_reclaim_enabled else 'disabled'}"
             if info.damon_reclaim_available else ""))
    print(f"  {'vm.swappiness':<18} {info.vm_swappiness}")


# ── recommendations ───────────────────────────────────────────────────────────

@dataclass
class Rec:
    id: str
    title: str
    reason: str
    action: str
    apply: Callable[[], Optional[bool]]


def build_recs(info: SystemInfo) -> list[Rec]:
    recs: list[Rec] = []
    planned_ids: set[str] = set()

    swap_file = Path("/swapfile")
    has_swap = info.swap_total_kb > 0
    rec_swap_gb = max(8, min(32, int(info.ram_gb / 4)))

    # ── 1. Swap file ──────────────────────────────────────────────────────────
    if not has_swap and not swap_file.exists():
        def _apply_swap():
            gb = rec_swap_gb
            dev = "/swapfile"
            print(f"  Creating {gb} GB swap file at {dev} ...")
            if not sudo_run("fallocate", "-l", f"{gb}G", dev):
                # Fallback to dd if fallocate fails (e.g. btrfs)
                print("  fallocate failed, trying dd (slower) ...")
                if not sudo_run("dd", "if=/dev/zero", f"of={dev}",
                                "bs=1M", f"count={gb * 1024}"):
                    print(red("  Could not create swap file."))
                    return False
            sudo_run("chmod", "600", dev)
            sudo_run("mkswap", dev)
            sudo_run("swapon", dev)
            fstab = Path("/etc/fstab").read_text()
            if dev not in fstab:
                sudo_tee_append("/etc/fstab", f"{dev} none swap defaults 0 0")
                print("  Added to /etc/fstab.")
            return True

        recs.append(Rec(
            id="swap_file",
            title="Create swap file",
            reason=(
                f"No swap exists. Without it, any memory spike ends in OOM kills with "
                f"no recovery path. A {rec_swap_gb} GB swap file gives zswap a writeback "
                f"target (so compressed pages can be evicted to disk when the pool fills) "
                f"and provides an emergency buffer."
            ),
            action=f"fallocate -l {rec_swap_gb}G /swapfile → mkswap → swapon → /etc/fstab",
            apply=_apply_swap,
        ))
        planned_ids.add("swap_file")

    # ── 2. zswap ─────────────────────────────────────────────────────────────
    kernel_ok = (info.kernel_major, info.kernel_minor) >= (5, 0)
    will_have_swap = has_swap or "swap_file" in planned_ids

    if kernel_ok and not info.zswap_enabled and will_have_swap:
        def _apply_zswap():
            # Enable at runtime immediately
            ok = True
            zsp = Path("/sys/module/zswap/parameters")
            if zsp.exists():
                sudo_tee(str(zsp / "enabled"), "1")
                sudo_tee(str(zsp / "compressor"), "zstd")
                sudo_tee(str(zsp / "max_pool_percent"), "20")
                print("  Enabled zswap at runtime.")
            else:
                print(yellow("  /sys/module/zswap/parameters not found — zswap may need a kernel module."))

            # Persist via GRUB
            grub = Path("/etc/default/grub")
            if grub.exists():
                content = grub.read_text()
                params = "zswap.enabled=1 zswap.compressor=zstd zswap.max_pool_percent=20"
                if "zswap.enabled" in content:
                    print("  zswap already in GRUB config.")
                else:
                    new_content = re.sub(
                        r'(GRUB_CMDLINE_LINUX_DEFAULT=")([^"]*)"',
                        lambda m: f'{m.group(1)}{m.group(2).rstrip()} {params}"',
                        content,
                    )
                    if new_content == content:
                        print(yellow("  Could not find GRUB_CMDLINE_LINUX_DEFAULT — edit /etc/default/grub manually."))
                        ok = False
                    else:
                        # Backup original
                        sudo_run("cp", "/etc/default/grub", "/etc/default/grub.bak")
                        sudo_tee("/etc/default/grub", new_content)
                        print("  Updated /etc/default/grub (backup at /etc/default/grub.bak).")

                        # Regenerate grub config
                        for cmd in [["grub-mkconfig", "-o", "/boot/grub/grub.cfg"],
                                    ["update-grub"]]:
                            if shutil.which(cmd[0]):
                                sudo_run(*cmd)
                                print(f"  Ran {cmd[0]}.")
                                break
            else:
                print(yellow("  /etc/default/grub not found. Add zswap params to your bootloader manually."))
            return ok

        zswap_vs_zram = (
            " NOTE: zswap is superior to zram when disk swap exists — zram's fixed pool"
            " causes LRU inversion; zswap's reclaim-path integration avoids it."
            if info.zram_active else ""
        )
        recs.append(Rec(
            id="zswap",
            title="Enable zswap (kernel compressed memory cache)",
            reason=(
                "zswap intercepts pages being swapped to disk, compresses them in RAM "
                "first (~5:1 with zstd on JVM data), and only writes to disk when the "
                "pool fills. Hot pages are served from RAM, cold pages from disk. "
                "Instagram production: 25% fewer disk writes vs. no swap at all."
                + zswap_vs_zram
            ),
            action="Enable at runtime via sysfs; persist via GRUB_CMDLINE_LINUX_DEFAULT",
            apply=_apply_zswap,
        ))
        planned_ids.add("zswap")

    # ── 2b. zswap compressor upgrade ─────────────────────────────────────────
    if info.zswap_enabled and info.zswap_compressor not in ("zstd", ""):
        def _apply_zswap_compressor():
            sudo_tee("/sys/module/zswap/parameters/compressor", "zstd")
            grub = Path("/etc/default/grub")
            if grub.exists():
                content = grub.read_text()
                new_content = re.sub(r"zswap\.compressor=\w+", "zswap.compressor=zstd", content)
                if new_content != content:
                    sudo_run("cp", "/etc/default/grub", "/etc/default/grub.bak")
                    sudo_tee("/etc/default/grub", new_content)
                    for cmd in [["grub-mkconfig", "-o", "/boot/grub/grub.cfg"], ["update-grub"]]:
                        if shutil.which(cmd[0]):
                            sudo_run(*cmd)
                            break
            return True

        recs.append(Rec(
            id="zswap_compressor",
            title=f"Switch zswap compressor: {info.zswap_compressor} → zstd",
            reason="zstd achieves 4.5–10:1 compression on JVM heap data vs. lzo's 3.5:1, with similar CPU cost on modern hardware.",
            action="Set compressor in sysfs + update GRUB cmdline",
            apply=_apply_zswap_compressor,
        ))

    # ── 3. Disable zram if zswap is active/planned ───────────────────────────
    if info.zram_active and (info.zswap_enabled or "zswap" in planned_ids):
        def _apply_disable_zram():
            cfg = Path("/etc/systemd/zram-generator.conf")
            if cfg.exists():
                sudo_run("cp", str(cfg), str(cfg) + ".bak")
                sudo_run("rm", str(cfg))
                print("  Removed zram-generator config (backup at .bak).")
            sudo_run("systemctl", "stop", "systemd-zram-setup@zram0.service")
            print("  zram stopped. (Persists after reboot since config is removed.)")
            return True

        recs.append(Rec(
            id="disable_zram",
            title="Disable zram (conflicts with zswap)",
            reason=(
                "Running zram alongside zswap + disk swap creates LRU inversion: pages "
                "are trapped in whichever compressed tier they landed in, regardless of "
                "access frequency. Let zswap own the compressed tier exclusively."
            ),
            action="Stop zram service + remove /etc/systemd/zram-generator.conf",
            apply=_apply_disable_zram,
        ))

    # ── 4. KSM enable ────────────────────────────────────────────────────────
    if info.ksm_available and info.ksm_run == 0:
        def _apply_ksm():
            sudo_tee("/sys/kernel/mm/ksm/run", "1")
            sudo_tee("/sys/kernel/mm/ksm/pages_to_scan", "4000")
            service = (
                "[Unit]\n"
                "Description=Kernel Samepage Merging (memory deduplication)\n"
                "After=multi-user.target\n\n"
                "[Service]\n"
                "Type=oneshot\n"
                "ExecStart=/usr/bin/bash -c "
                "'echo 1 > /sys/kernel/mm/ksm/run && "
                "echo 4000 > /sys/kernel/mm/ksm/pages_to_scan'\n"
                "RemainAfterExit=yes\n\n"
                "[Install]\n"
                "WantedBy=multi-user.target\n"
            )
            sudo_tee("/etc/systemd/system/ksm.service", service)
            sudo_run("systemctl", "daemon-reload")
            sudo_run("systemctl", "enable", "--now", "ksm.service")
            return True

        recs.append(Rec(
            id="ksm",
            title="Enable KSM (kernel same-page merging / memory deduplication)",
            reason=(
                "KSM scans anonymous memory pages across all processes, finds identical "
                "content, and merges them into a single copy-on-write physical page. "
                "Multiple Gradle daemons and JVM processes load identical JDK classes and "
                "library bytecode — KSM deduplicates those pages. Meta production: ~20% "
                "capacity increase with process-level KSM on JVM orchestration workloads."
            ),
            action="Enable at runtime (pages_to_scan=4000) + persist via systemd oneshot service",
            apply=_apply_ksm,
        ))

    # ── 4b. KSM pages_to_scan ────────────────────────────────────────────────
    elif info.ksm_available and info.ksm_run == 1 and info.ksm_pages_to_scan < 1000:
        def _apply_ksm_tune():
            sudo_tee("/sys/kernel/mm/ksm/pages_to_scan", "4000")
            svc = Path("/etc/systemd/system/ksm.service")
            if svc.exists():
                content = svc.read_text()
                updated = re.sub(
                    r"echo \d+ > /sys/kernel/mm/ksm/pages_to_scan",
                    "echo 4000 > /sys/kernel/mm/ksm/pages_to_scan",
                    content,
                )
                if updated != content:
                    sudo_tee(str(svc), updated)
                    sudo_run("systemctl", "daemon-reload")
            return True

        recs.append(Rec(
            id="ksm_tune",
            title=f"Increase KSM scan rate: {info.ksm_pages_to_scan} → 4000 pages/cycle",
            reason=(
                "The default of 100 pages/cycle is described in the Linux kernel docs as "
                "'only useful for demonstration'. Production deployments use 4000–5000."
            ),
            action="Write 4000 to /sys/kernel/mm/ksm/pages_to_scan; update systemd service",
            apply=_apply_ksm_tune,
        ))

    # ── 5. THP ───────────────────────────────────────────────────────────────
    if info.thp_enabled and info.thp_enabled != "madvise":
        def _apply_thp():
            sudo_tee("/sys/kernel/mm/transparent_hugepage/enabled", "madvise")
            sudo_tee("/sys/kernel/mm/transparent_hugepage/defrag", "defer+madvise")
            service = (
                "[Unit]\n"
                "Description=Transparent Huge Pages configuration\n"
                "After=multi-user.target\n\n"
                "[Service]\n"
                "Type=oneshot\n"
                "ExecStart=/usr/bin/bash -c "
                "'echo madvise > /sys/kernel/mm/transparent_hugepage/enabled && "
                "echo defer+madvise > /sys/kernel/mm/transparent_hugepage/defrag'\n"
                "RemainAfterExit=yes\n\n"
                "[Install]\n"
                "WantedBy=multi-user.target\n"
            )
            sudo_tee("/etc/systemd/system/thp-config.service", service)
            sudo_run("systemctl", "daemon-reload")
            sudo_run("systemctl", "enable", "--now", "thp-config.service")
            return True

        recs.append(Rec(
            id="thp",
            title=f"Set Transparent Huge Pages to 'madvise' (currently: '{info.thp_enabled}')",
            reason=(
                "Meta production data (2024): 20% of CPU cycles handle TLB misses on "
                "large JVM workloads. THP uses 2 MB pages, covering 512× more memory per "
                "TLB entry. 'madvise' mode lets JVMs opt in via -XX:+UseTransparentHugePages "
                "without triggering khugepaged compaction latency spikes for unrelated "
                "processes. 'defer+madvise' defrag allows background huge page assembly."
            ),
            action="Set THP=madvise, defrag=defer+madvise; persist via systemd service",
            apply=_apply_thp,
        ))

    # ── 6. vm.swappiness + vm tuning ─────────────────────────────────────────
    if info.vm_swappiness < 100:
        def _apply_swappiness():
            content = (
                "# Tuned for zswap/zram fast compressed swap (ChromeOS/Steam Deck values)\n"
                "vm.swappiness = 180\n"
                "vm.watermark_boost_factor = 0\n"
                "vm.watermark_scale_factor = 125\n"
                "vm.page-cluster = 0\n"
            )
            sudo_tee("/etc/sysctl.d/99-compressed-swap.conf", content)
            sudo_run("sysctl", "--system")
            return True

        recs.append(Rec(
            id="swappiness",
            title=f"Increase vm.swappiness to 180 (currently: {info.vm_swappiness})",
            reason=(
                f"vm.swappiness={info.vm_swappiness} was calibrated for slow magnetic disk "
                f"swap where swapping is expensive. With zswap/zram, compressed swap is "
                f"nearly as fast as RAM access. swappiness=180 tells the kernel to prefer "
                f"compressing cold anonymous pages (your idle JVM heap) over evicting hot "
                f"file cache — the correct tradeoff for JVM workloads. "
                f"vm.page-cluster=0 disables swap readahead (pointless for compressed RAM)."
            ),
            action="Write vm.swappiness=180, vm.page-cluster=0, vm.watermark_scale_factor=125 to /etc/sysctl.d/",
            apply=_apply_swappiness,
        ))

    # ── 7. MGLRU min_ttl tuning ──────────────────────────────────────────────
    if info.mglru_enabled and info.mglru_min_ttl_ms < 500:
        def _apply_mglru():
            sudo_tee("/sys/kernel/mm/lru_gen/min_ttl_ms", "1000")
            # vm.lru_gen.min_ttl_ms is a sysfs path, not a sysctl key — use a
            # systemd oneshot service (same pattern as KSM/THP) for persistence.
            service = (
                "[Unit]\n"
                "Description=MGLRU min_ttl_ms tuning\n"
                "After=multi-user.target\n\n"
                "[Service]\n"
                "Type=oneshot\n"
                "ExecStart=/usr/bin/bash -c "
                "'echo 1000 > /sys/kernel/mm/lru_gen/min_ttl_ms'\n"
                "RemainAfterExit=yes\n\n"
                "[Install]\n"
                "WantedBy=multi-user.target\n"
            )
            sudo_tee("/etc/systemd/system/mglru-tune.service", service)
            sudo_run("systemctl", "daemon-reload")
            sudo_run("systemctl", "enable", "--now", "mglru-tune.service")
            return True

        recs.append(Rec(
            id="mglru",
            title=f"Tune MGLRU min_ttl_ms: {info.mglru_min_ttl_ms}ms → 1000ms",
            reason=(
                "MGLRU (Multi-Gen LRU, Linux 6.1+) is already active on your kernel — "
                "it reduced kswapd CPU 40% and low-memory kills 85% in Google's fleet. "
                "min_ttl_ms=1000 prevents the youngest generation from being reclaimed "
                "too aggressively during memory spikes, reducing churn on JVM workloads "
                "that access memory in bursty patterns."
            ),
            action="Set /sys/kernel/mm/lru_gen/min_ttl_ms=1000; persist via systemd service",
            apply=_apply_mglru,
        ))

    # ── 8. DAMON proactive reclaim ────────────────────────────────────────────
    if info.damon_reclaim_available and not info.damon_reclaim_enabled:
        def _apply_damon():
            quota_sz = 128 * 1024 * 1024        # 128 MB/interval
            min_age  = 5 * 60 * 1_000_000_000  # 5 min cold threshold (nanoseconds)
            p = Path("/sys/module/damon_reclaim/parameters")
            sudo_tee(str(p / "enabled"),   "Y")
            sudo_tee(str(p / "quota_ms"),  "500")
            sudo_tee(str(p / "quota_sz"),  str(quota_sz))
            sudo_tee(str(p / "min_age"),   str(min_age))
            # modprobe.d covers the loadable-module case (all 4 params)
            sudo_tee(
                "/etc/modprobe.d/damon_reclaim.conf",
                f"options damon_reclaim enabled=Y quota_ms=500"
                f" quota_sz={quota_sz} min_age={min_age}\n",
            )
            # systemd service covers the built-in / already-loaded case
            service = (
                "[Unit]\n"
                "Description=DAMON proactive memory reclaim\n"
                "After=multi-user.target\n"
                "ConditionPathExists=/sys/module/damon_reclaim/parameters/enabled\n\n"
                "[Service]\n"
                "Type=oneshot\n"
                "ExecStart=/usr/bin/bash -c '"
                f"echo Y > /sys/module/damon_reclaim/parameters/enabled && "
                f"echo 500 > /sys/module/damon_reclaim/parameters/quota_ms && "
                f"echo {quota_sz} > /sys/module/damon_reclaim/parameters/quota_sz && "
                f"echo {min_age} > /sys/module/damon_reclaim/parameters/min_age'\n"
                "RemainAfterExit=yes\n\n"
                "[Install]\n"
                "WantedBy=multi-user.target\n"
            )
            sudo_tee("/etc/systemd/system/damon-reclaim.service", service)
            sudo_run("systemctl", "daemon-reload")
            sudo_run("systemctl", "enable", "--now", "damon-reclaim.service")
            return True

        recs.append(Rec(
            id="damon",
            title="Enable DAMON proactive memory reclaim",
            reason=(
                "DAMON monitors actual memory access patterns and proactively reclaims "
                "cold anonymous pages before OOM pressure builds — unlike kswapd which "
                "reacts only under pressure. AWS Aurora Serverless uses DAMON in production "
                "for VM memory reclamation. A conservative quota (128 MB/interval, 5-min "
                "minimum age) means it only touches pages that are genuinely idle."
            ),
            action="Enable damon_reclaim via sysfs; persist via modprobe.d (all params) + systemd service",
            apply=_apply_damon,
        ))

    return recs


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    if os.geteuid() == 0:
        print(red("Run as your normal user, not root — sudo is invoked per-operation."))
        sys.exit(1)

    print(bold("\n╔══════════════════════════════╗"))
    print(bold("║   Linux Memory Optimizer     ║"))
    print(bold("╚══════════════════════════════╝"))
    print("Inspects your memory configuration and proposes optimizations.")
    print("Each change is explained before you confirm it.\n")

    print("Detecting system...")
    info = detect()
    print_summary(info)

    recs = build_recs(info)

    if not recs:
        print(green("\nNo optimizations needed — your configuration is already solid."))
        return

    header(f"Recommendations  ({len(recs)} found)")

    applied = skipped = failed = 0

    for i, rec in enumerate(recs, 1):
        print(f"\n{'─' * 64}")
        print(f"{bold(f'[{i}/{len(recs)}]')}  {bold(rec.title)}")
        print()
        # Word-wrap the reason at 70 chars
        words, line = rec.reason.split(), ""
        for w in words:
            if len(line) + len(w) + 1 > 70:
                print(f"  {line}")
                line = w
            else:
                line = (line + " " + w).lstrip()
        if line:
            print(f"  {line}")
        print(f"\n  {yellow('Action:')} {rec.action}")

        if not ask("\nApply?"):
            print(yellow("  Skipped."))
            skipped += 1
            continue

        # Acquire sudo credentials before the first privileged call
        if not check_sudo_available():
            print("  Requesting sudo credentials...")
            subprocess.run(["sudo", "-v"])

        print()
        result = rec.apply()
        if result is False:
            print(red(f"  ✗ Failed: {rec.title}"))
            failed += 1
        else:
            print(green(f"  ✓ Done: {rec.title}"))
            applied += 1

    print(f"\n{'═' * 64}")
    print(bold(f"Summary:  {green(str(applied))} applied  "
               f"{yellow(str(skipped))} skipped  "
               f"{red(str(failed)) if failed else str(failed)} failed"))

    if applied > 0:
        print(yellow(
            "\nSome changes (GRUB cmdline) require a reboot to take full effect."
        ))
        print("\nUseful monitoring commands after reboot:")
        print(dim("  # zswap pool usage"))
        print("  cat /sys/kernel/debug/zswap/stored_pages")
        print(dim("  # KSM deduplication savings"))
        print("  cat /sys/kernel/mm/ksm/pages_sharing")
        print(dim("  # zram state (if still active)"))
        print("  zramctl")
        print(dim("  # Overall memory"))
        print("  free -h")


if __name__ == "__main__":
    main()
