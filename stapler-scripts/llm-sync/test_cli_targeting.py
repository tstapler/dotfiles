#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

from cli import should_sync_non_pi_integrations


def test_pi_target_does_not_mutate_other_agents() -> None:
    assert should_sync_non_pi_integrations("pi", plugins_only=False) is False
    assert should_sync_non_pi_integrations("all", plugins_only=False) is True
    assert should_sync_non_pi_integrations("pi", plugins_only=True) is True


if __name__ == "__main__":
    test_pi_target_does_not_mutate_other_agents()
    print("ok  test_pi_target_does_not_mutate_other_agents")
