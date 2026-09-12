"""
Installs and enables the `btrfsmaintenance` package (balance/scrub/trim
systemd timers), replacing the never-wired-in
stapler-scripts/roles/btrfs-balance/ Ansible role — that role installed its
own units named identically (btrfs-balance.timer/.service) under
/etc/systemd/system/, which would silently shadow this package's own units
under /usr/lib/systemd/system/ if it were ever applied. Removed rather than
left around as a landmine.

Arch/Manjaro + btrfs-root only, matching the machine this was written for.

defrag is deliberately never enabled: it breaks the shared (reflinked)
extents that CoW snapshots (e.g. Timeshift, which this machine uses) depend
on, ballooning real disk usage the moment a defragmented subvolume's blocks
diverge from a snapshot.
"""

from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.operations import files, pacman, systemd

from common import is_archlinux, is_btrfs_root

CONFIG_PATH = "/etc/default/btrfsmaintenance"
MOUNTPOINT_VARS = (
    "BTRFS_BALANCE_MOUNTPOINTS",
    "BTRFS_SCRUB_MOUNTPOINTS",
    "BTRFS_TRIM_MOUNTPOINTS",
)
ENABLED_TIMERS = ("btrfs-balance.timer", "btrfs-scrub.timer", "btrfs-trim.timer")


def _pin_mountpoint(var: str) -> None:
    # Regex-replace whatever the package ships (commonly "auto") instead of
    # assuming its exact default text.
    files.line(
        name=f"Pin {var} to / in {CONFIG_PATH}",
        path=CONFIG_PATH,
        line=f"^{var}=",
        replace=f'{var}="/"',
        _sudo=True,
    )


@deploy("btrfs maintenance")
def btrfs_maintenance() -> None:
    if not is_archlinux() or not is_btrfs_root():
        return

    pacman.packages(
        name="Install btrfsmaintenance",
        packages=["btrfsmaintenance"],
        present=True,
        _sudo=True,
    )
    for var in MOUNTPOINT_VARS:
        _pin_mountpoint(var)
    for timer in ENABLED_TIMERS:
        systemd.service(
            name=f"Enable and start {timer}",
            service=timer,
            running=True,
            enabled=True,
            _sudo=True,
        )
