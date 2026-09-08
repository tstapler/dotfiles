"""Pure regression checks for Pi installation ownership decisions.

Run directly: uv run test_pi_install.py
"""

from deploys.pi import PI_NPM_PACKAGE, plan_pi_install


def test_uses_the_maintained_pi_package() -> None:
    assert PI_NPM_PACKAGE == "@earendil-works/pi-coding-agent"


def test_auto_installs_only_when_absent() -> None:
    plan = plan_pi_install(
        "auto", pi_present=False, installed_version=None, target_version="0.84.4"
    )
    assert plan.action == "install"


def test_auto_preserves_work_or_other_existing_install() -> None:
    plan = plan_pi_install(
        "auto", pi_present=True, installed_version="9.1.0", target_version="0.84.4"
    )
    assert plan.action == "preserve"
    assert "9.1.0" in plan.reason


def test_external_never_installs() -> None:
    plan = plan_pi_install(
        "external", pi_present=False, installed_version=None, target_version="0.84.4"
    )
    assert plan.action == "external"


def test_managed_converges_only_on_mismatch() -> None:
    current = plan_pi_install(
        "managed", pi_present=True, installed_version="0.84.4", target_version="0.84.4"
    )
    old = plan_pi_install(
        "managed", pi_present=True, installed_version="0.72.0", target_version="0.84.4"
    )
    unknown = plan_pi_install(
        "managed", pi_present=True, installed_version=None, target_version="0.84.4"
    )

    assert current.action == "preserve"
    assert old.action == "update"
    assert unknown.action == "update"


def test_rejects_invalid_mode_and_unsafe_version() -> None:
    invalid = (
        ("surprise", "0.84.4"),
        ("managed", "latest"),
        ("managed", "1.2.3;whoami"),
    )
    for mode, version in invalid:
        try:
            plan_pi_install(
                mode, pi_present=False, installed_version=None, target_version=version
            )
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected mode={mode!r}, version={version!r} to fail")


if __name__ == "__main__":
    tests = [value for key, value in list(globals().items()) if key.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} checks passed")
