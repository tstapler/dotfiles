"""
Regression check for tymuxd's ENOENT-discrimination logic.

Run directly: uv run test_tymuxd.py
"""

from deploys.tymuxd import tymuxd_present


def test_enoent_means_not_present() -> None:
    assert tymuxd_present(2) is False


def test_any_other_exit_code_means_present() -> None:
    for rc in (0, 1, 124, 255):
        assert tymuxd_present(rc) is True


if __name__ == "__main__":
    from _test_runner import run_tests

    run_tests(globals())
