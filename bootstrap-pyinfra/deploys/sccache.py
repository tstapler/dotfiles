"""
Keeps an sccache server running persistently.

~/.cargo/config.toml sets `rustc-wrapper = "sccache"`. Without a managed
server, the first cargo build spawns one as a child of whatever shell ran it,
so it dies with that shell/session. Every later rustc then logs "sccache: The
server looks like it shut down unexpectedly, compiling locally instead" and
silently gets no caching. This deploy runs the server in the foreground under
launchd (macOS) or systemd --user (Linux) instead.

SCCACHE_IDLE_TIMEOUT=0 disables the default 10-minute idle shutdown, and
SCCACHE_START_SERVER=1 + SCCACHE_NO_DAEMON=1 make `sccache` run the server in
the foreground, which service managers require.

The sccache binary itself comes from the Brewfile / Brewfile.linux.
"""

import io
import os

from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.operations import files, server, systemd

from common import brew_prefix, is_macos

LAUNCHD_LABEL = "com.tstapler.sccache"
LAUNCH_AGENTS_DIR = os.path.expanduser("~/Library/LaunchAgents")
LAUNCHD_PLIST = os.path.join(LAUNCH_AGENTS_DIR, f"{LAUNCHD_LABEL}.plist")
LAUNCHD_LOG = os.path.expanduser("~/Library/Logs/sccache.log")

SYSTEMD_USER_DIR = os.path.expanduser("~/.config/systemd/user")
SYSTEMD_UNIT = "sccache.service"

SERVER_ENV = {
    "SCCACHE_START_SERVER": "1",
    "SCCACHE_NO_DAEMON": "1",
    "SCCACHE_IDLE_TIMEOUT": "0",
}


def launchd_plist_content(sccache_bin: str, log_path: str) -> str:
    env_entries = "\n".join(
        f"        <key>{key}</key>\n        <string>{value}</string>"
        for key, value in SERVER_ENV.items()
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LAUNCHD_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sccache_bin}</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
{env_entries}
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_path}</string>
    <key>StandardErrorPath</key>
    <string>{log_path}</string>
</dict>
</plist>
"""


def systemd_unit_content(sccache_bin: str) -> str:
    env_lines = "\n".join(f"Environment={k}={v}" for k, v in SERVER_ENV.items())
    return f"""[Unit]
Description=sccache compilation cache server

[Service]
{env_lines}
ExecStart={sccache_bin}
Restart=always
RestartSec=2

[Install]
WantedBy=default.target
"""


def _install_launchd_agent(sccache_bin: str) -> None:
    files.directory(
        name="Ensure ~/Library/LaunchAgents exists",
        path=LAUNCH_AGENTS_DIR,
        present=True,
        mode="0755",
    )
    plist = files.put(
        name=f"Deploy {LAUNCHD_LABEL} LaunchAgent",
        src=io.StringIO(launchd_plist_content(sccache_bin, LAUNCHD_LOG)),
        dest=LAUNCHD_PLIST,
        mode="0644",
    )
    domain = "gui/$(id -u)"
    # Reload only when the plist changed, so re-runs don't kill a live server
    # mid-build; the guarded bootstrap covers first install and a booted-out agent.
    server.shell(
        name="Reload sccache LaunchAgent after plist change",
        commands=[
            f"launchctl bootout {domain}/{LAUNCHD_LABEL} 2>/dev/null || true",
            f"launchctl bootstrap {domain} {LAUNCHD_PLIST}",
        ],
        _if=plist.did_change,
    )
    server.shell(
        name="Bootstrap sccache LaunchAgent if not loaded",
        commands=[
            f"launchctl print {domain}/{LAUNCHD_LABEL} >/dev/null 2>&1 "
            f"|| launchctl bootstrap {domain} {LAUNCHD_PLIST}"
        ],
    )


def _install_systemd_user_service(sccache_bin: str) -> None:
    files.directory(
        name="Ensure ~/.config/systemd/user exists",
        path=SYSTEMD_USER_DIR,
        present=True,
        mode="0755",
    )
    files.put(
        name=f"Deploy {SYSTEMD_UNIT} (user)",
        src=io.StringIO(systemd_unit_content(sccache_bin)),
        dest=os.path.join(SYSTEMD_USER_DIR, SYSTEMD_UNIT),
        mode="0644",
    )
    systemd.service(
        name=f"Enable and start {SYSTEMD_UNIT}",
        service=SYSTEMD_UNIT,
        running=True,
        enabled=True,
        user_mode=True,
        daemon_reload=True,
    )


@deploy("sccache")
def sccache() -> None:
    sccache_bin = f"{brew_prefix()}/bin/sccache"
    if is_macos():
        _install_launchd_agent(sccache_bin)
    else:
        _install_systemd_user_service(sccache_bin)
