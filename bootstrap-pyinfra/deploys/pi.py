"""Install the public Pi distribution without replacing work-managed installs.

Installation policy is deliberately separate from Pi's runtime configuration:

- ``auto`` (default) preserves any ``pi`` already on PATH and installs the
  pinned public package only when Pi is absent.
- ``managed`` converges the user-local public install to the configured exact
  version.
- ``external`` never installs Pi; an overlay or machine manager owns it.

The install itself is a queued pyinfra operation. This is important because
``pyinfra --dry`` does not protect immediate ``shell_capture`` mutations.
Nothing later in the bootstrap needs the Pi executable itself, so queuing is
safe here.
"""

import re
from dataclasses import dataclass
from typing import Literal

from pyinfra import host  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.api.exceptions import DeployError
from pyinfra.operations import server

from common import brew_prefix, dev_tools_path_env, shell_capture

PI_NPM_PACKAGE = "@earendil-works/pi-coding-agent"
_VALID_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$")

InstallAction = Literal["install", "update", "preserve", "external"]


@dataclass(frozen=True)
class PiInstallPlan:
    action: InstallAction
    reason: str


def plan_pi_install(
    mode: str,
    *,
    pi_present: bool,
    installed_version: str | None,
    target_version: str,
) -> PiInstallPlan:
    """Return a side-effect-free installation decision for tests and deploy."""
    if mode not in {"auto", "managed", "external"}:
        raise ValueError(
            f"invalid pi_install_mode {mode!r}; expected auto, managed, or external"
        )
    if not _VALID_VERSION.fullmatch(target_version):
        raise ValueError(f"invalid pinned Pi version {target_version!r}")

    if mode == "external":
        return PiInstallPlan("external", "installation is externally managed")
    if mode == "auto":
        if pi_present:
            version = installed_version or "unknown version"
            return PiInstallPlan("preserve", f"preserving existing Pi ({version})")
        return PiInstallPlan("install", f"Pi is absent; install {target_version}")

    if not pi_present:
        return PiInstallPlan(
            "install", f"managed Pi is absent; install {target_version}"
        )
    if installed_version == target_version:
        return PiInstallPlan("preserve", f"managed Pi {target_version} is current")
    return PiInstallPlan(
        "update",
        f"managed Pi is {installed_version or 'an unknown version'}; converge to {target_version}",
    )


def pi_hook_install_command(path_env: str) -> str:
    """Return an idempotent install command for Stapler Squad's Pi extension."""
    return (
        f'PATH="{path_env}"; export PATH; '
        "if command -v ssq-hooks >/dev/null 2>&1; then "
        "ssq-hooks install pi; "
        "else echo 'ssq-hooks unavailable; skipping Pi approval extension'; fi"
    )


def _installed_pi() -> tuple[bool, str | None]:
    code, output = shell_capture(f'PATH="{dev_tools_path_env()}" pi --version')
    if code != 0:
        return False, None

    match = re.search(r"\b([0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?)\b", output)
    return True, match.group(1) if match else None


@deploy("Pi")
def pi() -> None:
    mode = str(host.data.get("pi_install_mode", "auto"))
    target_version = str(host.data.get("pi_install_version", "0.84.4"))
    present, installed_version = _installed_pi()

    try:
        plan = plan_pi_install(
            mode,
            pi_present=present,
            installed_version=installed_version,
            target_version=target_version,
        )
    except ValueError as error:
        raise DeployError(str(error)) from error

    print(f"Pi installation: {plan.reason}")
    if plan.action not in {"external", "preserve"}:
        npm = f"{brew_prefix()}/bin/npm"
        package = f"{PI_NPM_PACKAGE}@{target_version}"
        install_command = (
            "mkdir -p ~/.local && "
            f'{npm} install --global --prefix ~/.local --no-audit --no-fund "{package}" && '
            "~/.local/bin/pi --version"
        )
        server.shell(
            name=f"{plan.action.title()} Pi {target_version} in ~/.local",
            commands=[install_command],
        )

    # Stapler Squad owns its approval extension and provides an idempotent
    # installer. Run it after Pi is present rather than reimplementing the
    # generated extension in dotfiles.
    if present or plan.action in {"install", "update"}:
        server.shell(
            name="Install Stapler Squad Pi approval extension",
            commands=[pi_hook_install_command(dev_tools_path_env())],
        )
