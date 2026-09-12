"""
Regression check for the zswap GRUB cmdline sed replacement.

Run directly: uv run test_memory_optimizer.py
"""

import re

from deploys.memory_optimizer import GRUB_CMDLINE_REGEX, grub_cmdline_replacement


def test_replacement_appends_zswap_params_inside_the_quotes() -> None:
    line = 'GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"'
    replacement = grub_cmdline_replacement("zstd", 20)

    result = re.sub(GRUB_CMDLINE_REGEX, replacement, line)

    assert result == (
        'GRUB_CMDLINE_LINUX_DEFAULT="quiet splash zswap.enabled=1 '
        'zswap.compressor=zstd zswap.max_pool_percent=20"'
    )


def test_regex_only_matches_the_default_cmdline_variable() -> None:
    assert re.match(GRUB_CMDLINE_REGEX, 'GRUB_CMDLINE_LINUX="quiet"') is None


if __name__ == "__main__":
    tests = [value for key, value in list(globals().items()) if key.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
