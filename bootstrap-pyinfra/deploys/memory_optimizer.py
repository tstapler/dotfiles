"""
Port of stapler-scripts/roles/memory-optimizer/tasks/main.yml — Linux-only
swap/zswap/systemd-oomd/KSM/THP/MGLRU/DAMON kernel memory tuning.

Every mutating step in the Ansible original has `become: yes` — this deploy
is entirely root-touching. The swapfile and zswap/GRUB sections are
immediate execution (shell_capture/shell_ok with `sudo` embedded in the
command, matching deploys/homebrew.py's convention), since each step's
branch depends on the real outcome of the step before it (Ansible's
register-then-`when` chain). Everything else (systemd units, sysctl,
modprobe) has no such same-run dependency, so it uses ordinary queued
pyinfra operations with `_sudo=True`.

NOT yet run live anywhere — every mutation here needs root, which needs a
real interactive terminal for the sudo password prompt (see
bootstrap-pyinfra/README.md's "Operations that need root" note). Code
review + the pure-logic checks in test_memory_optimizer.py are the
verification so far.
"""

import io
import re
from dataclasses import dataclass

from pyinfra import host  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.api.exceptions import DeployError
from pyinfra.operations import files, server, systemd

from common import shell_capture, shell_ok

GRUB_PATH = "/etc/default/grub"
GRUB_CMDLINE_REGEX = r'^(GRUB_CMDLINE_LINUX_DEFAULT="[^"]*)"'

KSM_UNIT_TEMPLATE = """[Unit]
Description=Kernel Samepage Merging (memory deduplication)
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/bin/bash -c 'echo 1 > /sys/kernel/mm/ksm/run && echo {pages_to_scan} > /sys/kernel/mm/ksm/pages_to_scan'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""

THP_UNIT = """[Unit]
Description=Transparent Huge Pages configuration
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/bin/bash -c 'echo madvise > /sys/kernel/mm/transparent_hugepage/enabled && echo defer+madvise > /sys/kernel/mm/transparent_hugepage/defrag'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""

MGLRU_UNIT_TEMPLATE = """[Unit]
Description=MGLRU min_ttl_ms tuning
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/bin/bash -c 'echo {min_ttl_ms} > /sys/kernel/mm/lru_gen/min_ttl_ms'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""

DAMON_UNIT_TEMPLATE = """[Unit]
Description=DAMON proactive memory reclaim
After=multi-user.target
ConditionPathExists=/sys/module/damon_reclaim/parameters/enabled

[Service]
Type=oneshot
ExecStart=/usr/bin/bash -c '\\
  echo Y > /sys/module/damon_reclaim/parameters/enabled && \\
  echo {quota_ms} > /sys/module/damon_reclaim/parameters/quota_ms && \\
  echo {quota_sz} > /sys/module/damon_reclaim/parameters/quota_sz && \\
  echo {min_age} > /sys/module/damon_reclaim/parameters/min_age'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""


@dataclass(frozen=True)
class MemoryOptimizerConfig:
    swap_file: str
    swap_size_gb: int
    zswap_enabled: bool
    zswap_compressor: str
    zswap_max_pool_percent: int
    vm_swappiness: int
    vm_watermark_boost_factor: int
    vm_watermark_scale_factor: int
    vm_page_cluster: int
    ksm_pages_to_scan: int
    mglru_min_ttl_ms: int
    damon_quota_ms: int
    damon_quota_sz: int
    damon_min_age: int


def _config_from_host_data() -> MemoryOptimizerConfig:
    data = host.data
    return MemoryOptimizerConfig(
        swap_file=data.get("swap_file"),
        swap_size_gb=int(data.get("swap_size_gb")),
        zswap_enabled=bool(data.get("zswap_enabled")),
        zswap_compressor=data.get("zswap_compressor"),
        zswap_max_pool_percent=int(data.get("zswap_max_pool_percent")),
        vm_swappiness=int(data.get("vm_swappiness")),
        vm_watermark_boost_factor=int(data.get("vm_watermark_boost_factor")),
        vm_watermark_scale_factor=int(data.get("vm_watermark_scale_factor")),
        vm_page_cluster=int(data.get("vm_page_cluster")),
        ksm_pages_to_scan=int(data.get("ksm_pages_to_scan")),
        mglru_min_ttl_ms=int(data.get("mglru_min_ttl_ms")),
        damon_quota_ms=int(data.get("damon_quota_ms")),
        damon_quota_sz=int(data.get("damon_quota_sz")),
        damon_min_age=int(data.get("damon_min_age")),
    )


def _run(step: str, command: str) -> None:
    code, output = shell_capture(command)
    if code != 0:
        raise DeployError(f"{step} failed ({code}): {output}")


def _swapfile_exists(swap_file: str) -> bool:
    return shell_ok(f"sudo test -e {swap_file}")


def _ensure_swapfile_nocow(swap_file: str, root_fstype: str) -> None:
    """btrfs requires NoCOW (chattr +C) set before any data is written — a
    swapfile created without it always fails `swapon` with EINVAL. Detect
    that case and remove the file so it's recreated with the attribute."""
    if root_fstype != "btrfs":
        return

    if _swapfile_exists(swap_file):
        has_nocow = shell_ok(
            f"sudo lsattr {swap_file} | awk '{{print $1}}' | grep -q C"
        )
        if not has_nocow:
            _run(
                f"Remove {swap_file} missing NoCOW attribute", f"sudo rm -f {swap_file}"
            )

    if not _swapfile_exists(swap_file):
        _run(
            f"Touch {swap_file} before setting attributes",
            f"sudo touch {swap_file} && sudo chmod 0600 {swap_file} && sudo chown root:root {swap_file}",
        )
        _run(f"Set NoCOW attribute on {swap_file}", f"sudo chattr +C {swap_file}")


def _configure_swapfile(swap_file: str, swap_size_gb: int) -> None:
    root_fstype = shell_capture("stat -f -c '%T' /")[1].strip()
    _ensure_swapfile_nocow(swap_file, root_fstype)

    if not _swapfile_exists(swap_file):
        _run(f"Allocate {swap_file}", f"sudo fallocate -l {swap_size_gb}G {swap_file}")

    _run(
        f"Set {swap_file} permissions",
        f"sudo chmod 0600 {swap_file} && sudo chown root:root {swap_file}",
    )

    has_swap_signature = shell_ok(f"sudo blkid -t TYPE=swap {swap_file}")
    if not has_swap_signature:
        _run(f"Format {swap_file}", f"sudo mkswap {swap_file}")

    active_swaps = shell_capture("swapon --show --noheadings")[1]
    if swap_file not in active_swaps:
        _run(f"Activate swap {swap_file}", f"sudo swapon {swap_file}")

    files.line(
        name="Persist swapfile in fstab",
        path="/etc/fstab",
        line=f"^{re.escape(swap_file)}\\s",
        replace=f"{swap_file}\tnone\tswap\tdefaults\t0\t0",
        _sudo=True,
    )


def grub_cmdline_replacement(compressor: str, max_pool_percent: int) -> str:
    """Pure string-building for the GRUB_CMDLINE_LINUX_DEFAULT sed
    replacement, factored out so test_memory_optimizer.py can check it
    without a real /etc/default/grub."""
    return f'\\1 zswap.enabled=1 zswap.compressor={compressor} zswap.max_pool_percent={max_pool_percent}"'


def _configure_zswap(config: MemoryOptimizerConfig) -> None:
    if not config.zswap_enabled or not shell_ok("test -e /sys/module/zswap/parameters"):
        return

    _run(
        "Enable zswap at runtime",
        "echo 1 | sudo tee /sys/module/zswap/parameters/enabled > /dev/null && "
        f"echo {config.zswap_compressor} | sudo tee /sys/module/zswap/parameters/compressor > /dev/null && "
        f"echo {config.zswap_max_pool_percent} | sudo tee /sys/module/zswap/parameters/max_pool_percent > /dev/null",
    )

    if shell_ok(f"sudo grep -q 'zswap.enabled=1' {GRUB_PATH}"):
        return

    server.shell(
        name="Back up GRUB config (once)",
        commands=[f"test -f {GRUB_PATH}.bak || cp {GRUB_PATH} {GRUB_PATH}.bak"],
        _sudo=True,
    )
    files.replace(
        name="Add zswap params to GRUB cmdline",
        path=GRUB_PATH,
        text=GRUB_CMDLINE_REGEX,
        replace=grub_cmdline_replacement(
            config.zswap_compressor, config.zswap_max_pool_percent
        ),
        extended_regex=True,
        _sudo=True,
    )
    server.shell(
        name="Regenerate GRUB config",
        commands=["grub-mkconfig -o /boot/grub/grub.cfg"],
        _sudo=True,
    )


def _disable_zram() -> None:
    """Only called when zswap is enabled — the two swap-compression
    backends conflict, so zswap wins (see memory_optimizer())."""
    if not shell_ok("test -e /sys/block/zram0"):
        return
    systemd.service(
        name="Stop zram service",
        service="systemd-zram-setup@zram0.service",
        running=False,
        _sudo=True,
        _ignore_errors=True,
    )
    files.file(
        name="Remove zram-generator config",
        path="/etc/systemd/zram-generator.conf",
        present=False,
        _sudo=True,
    )


def _configure_oomd() -> None:
    # Kills the offending cgroup under memory/swap pressure before the
    # kernel's global OOM killer does — disabled by default on Manjaro/Arch,
    # unlike Fedora/Ubuntu.
    if not shell_ok("test -e /usr/lib/systemd/system/systemd-oomd.service"):
        return
    systemd.service(
        name="Enable and start systemd-oomd",
        service="systemd-oomd.service",
        running=True,
        enabled=True,
        _sudo=True,
    )


def _deploy_oneshot_kernel_service(
    *, service_name: str, sentinel_path: str, unit_content: str
) -> None:
    """Ansible's stat-guarded "copy unit + systemd enable/start" pattern,
    repeated for KSM/THP/MGLRU/DAMON — all gated on a /sys path only present
    when the kernel/config supports the feature."""
    if not shell_ok(f"test -e {sentinel_path}"):
        return
    files.put(
        name=f"Deploy {service_name} systemd service",
        src=io.StringIO(unit_content),
        dest=f"/etc/systemd/system/{service_name}",
        mode="0644",
        _sudo=True,
    )
    systemd.service(
        name=f"Enable and start {service_name}",
        service=service_name,
        running=True,
        enabled=True,
        daemon_reload=True,
        _sudo=True,
    )


def _configure_ksm(pages_to_scan: int) -> None:
    _deploy_oneshot_kernel_service(
        service_name="ksm.service",
        sentinel_path="/sys/kernel/mm/ksm",
        unit_content=KSM_UNIT_TEMPLATE.format(pages_to_scan=pages_to_scan),
    )


def _configure_thp() -> None:
    _deploy_oneshot_kernel_service(
        service_name="thp-config.service",
        sentinel_path="/sys/kernel/mm/transparent_hugepage",
        unit_content=THP_UNIT,
    )


def _configure_vm_tunables(config: MemoryOptimizerConfig) -> None:
    content = (
        "# Tuned for zswap fast compressed swap (ChromeOS/Steam Deck values)\n"
        f"vm.swappiness = {config.vm_swappiness}\n"
        f"vm.watermark_boost_factor = {config.vm_watermark_boost_factor}\n"
        f"vm.watermark_scale_factor = {config.vm_watermark_scale_factor}\n"
        f"vm.page-cluster = {config.vm_page_cluster}\n"
    )
    files.put(
        name="Deploy compressed-swap sysctl config",
        src=io.StringIO(content),
        dest="/etc/sysctl.d/99-compressed-swap.conf",
        mode="0644",
        _sudo=True,
    )
    # ponytail: always re-apply rather than tracking whether the file
    # changed — `sysctl --system` is cheap and idempotent.
    server.shell(
        name="Apply sysctl settings",
        commands=["sysctl --system"],
        _sudo=True,
    )


def _configure_mglru(min_ttl_ms: int) -> None:
    _deploy_oneshot_kernel_service(
        service_name="mglru-tune.service",
        sentinel_path="/sys/kernel/mm/lru_gen/enabled",
        unit_content=MGLRU_UNIT_TEMPLATE.format(min_ttl_ms=min_ttl_ms),
    )


def _configure_damon(config: MemoryOptimizerConfig) -> None:
    if not shell_ok("test -e /sys/module/damon_reclaim"):
        return
    files.put(
        name="Deploy DAMON modprobe config",
        src=io.StringIO(
            f"options damon_reclaim enabled=Y quota_ms={config.damon_quota_ms} "
            f"quota_sz={config.damon_quota_sz} min_age={config.damon_min_age}\n"
        ),
        dest="/etc/modprobe.d/damon_reclaim.conf",
        mode="0644",
        _sudo=True,
    )
    _deploy_oneshot_kernel_service(
        service_name="damon-reclaim.service",
        sentinel_path="/sys/module/damon_reclaim",
        unit_content=DAMON_UNIT_TEMPLATE.format(
            quota_ms=config.damon_quota_ms,
            quota_sz=config.damon_quota_sz,
            min_age=config.damon_min_age,
        ),
    )


@deploy("Memory optimizer")
def memory_optimizer() -> None:
    config = _config_from_host_data()
    _configure_swapfile(config.swap_file, config.swap_size_gb)
    _configure_zswap(config)
    if config.zswap_enabled:
        _disable_zram()
    _configure_oomd()
    _configure_ksm(config.ksm_pages_to_scan)
    _configure_thp()
    _configure_vm_tunables(config)
    _configure_mglru(config.mglru_min_ttl_ms)
    _configure_damon(config)
