"""
Regression check for the llm-sync systemd --user timer unit content.

sync_command() itself isn't called here: it resolves brew_prefix()/is_macos()
via pyinfra's host.get_fact(), which only works inside a connected pyinfra
run (see test_llm_sync_deploy.py's docstring for the same constraint on
llm_sync()). sync_service_unit_content() takes the command as a plain string
precisely so this file can test the unit-rendering logic without a pyinfra
host.

Run directly: uv run test_llm_sync_timer.py
"""

from deploys.llm_sync import sync_service_unit_content, sync_timer_unit_content

_FAKE_COMMAND = 'cd /fake/llm-sync && PATH="/fake/bin" uv run main.py'


def test_service_unit_embeds_the_exact_sync_command() -> None:
    unit = sync_service_unit_content(_FAKE_COMMAND)

    assert f"ExecStart=/bin/sh -c '{_FAKE_COMMAND}'" in unit
    assert "[Service]" in unit
    assert "Type=oneshot" in unit


def test_timer_unit_sets_boot_delay_and_interval() -> None:
    unit = sync_timer_unit_content(boot_delay="5min", interval="30min")

    assert "OnBootSec=5min" in unit
    assert "OnUnitActiveSec=30min" in unit
    assert "Persistent=true" in unit
    assert "WantedBy=timers.target" in unit


if __name__ == "__main__":
    tests = [value for key, value in list(globals().items()) if key.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
