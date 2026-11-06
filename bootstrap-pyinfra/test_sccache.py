"""
Regression check for the sccache launchd plist / systemd unit content.

Run directly: uv run test_sccache.py
"""

from deploys.sccache import launchd_plist_content, systemd_unit_content

_BIN = "/fake/bin/sccache"


def test_launchd_plist_runs_server_in_foreground_and_stays_alive() -> None:
    plist = launchd_plist_content(_BIN, "/fake/sccache.log")

    assert f"<string>{_BIN}</string>" in plist
    assert "<key>SCCACHE_NO_DAEMON</key>" in plist
    assert "<key>SCCACHE_START_SERVER</key>" in plist
    assert "<key>SCCACHE_IDLE_TIMEOUT</key>\n        <string>0</string>" in plist
    assert "<key>KeepAlive</key>\n    <true/>" in plist


def test_systemd_unit_runs_server_in_foreground_and_restarts() -> None:
    unit = systemd_unit_content(_BIN)

    assert f"ExecStart={_BIN}" in unit
    assert "Environment=SCCACHE_NO_DAEMON=1" in unit
    assert "Environment=SCCACHE_START_SERVER=1" in unit
    assert "Environment=SCCACHE_IDLE_TIMEOUT=0" in unit
    assert "Restart=always" in unit


if __name__ == "__main__":
    from _test_runner import run_tests

    run_tests(globals())
