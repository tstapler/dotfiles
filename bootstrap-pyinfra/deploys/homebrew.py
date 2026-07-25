"""
Port of bootstrap/roles/homebrew/tasks/main.yml.

Everything here runs via shell_capture (immediate execution), NOT queued
pyinfra operations (brew.packages/apt.packages/etc.) — deliberately. pyinfra
queues operations and only runs them in a separate "execute" phase after ALL
prepare-time Python across the whole deploy has finished; any host.get_fact()
call (which shell_ok/shell_capture use) always runs immediately, during
prepare. Confirmed empirically: a queued operation that creates a file is
NOT visible to an immediate fact check made right after queuing it, only
after the whole run completes. Since later deploys (asdf, dotfiles, secrets)
immediately check for tools this role installs (asdf, uv, op), the install
steps here have to actually be done — not merely queued — before this
function returns, or those later checks see a not-yet-installed state on a
genuinely fresh machine. `files.link` for the gdu symlink is the one step
left as a real queued operation, since nothing else in this run depends on
its result immediately.

Sets HOMEBREW_NO_AUTO_UPDATE / HOMEBREW_NO_ANALYTICS / HOMEBREW_NO_INSTALL_CLEANUP
on every brew invocation below except the explicit `brew update` — these are
official, zero-risk Homebrew env vars, not a reimplementation of anything.
Measured on this machine: an untuned `brew bundle check` can cost several
seconds when brew's auto-update silently decides to re-fetch the tap first;
with a warm tap cache it's usually well under a second either way. The env
vars don't change what gets installed — they just stop brew from doing its
own implicit update/telemetry/cleanup work inside commands that already run
right after an explicit `brew update` here, making bootstrap timing
consistent instead of occasionally paying for a surprise tap fetch.
"""

from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.api.exceptions import DeployError
from pyinfra.operations import files

from common import brew_prefix, is_debian_like, is_macos, shell_capture, shell_ok

BREW_ENV = (
    "HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_ANALYTICS=1 HOMEBREW_NO_INSTALL_CLEANUP=1"
)
NO_GIT_PROMPT_ENV = (
    'GIT_TERMINAL_PROMPT=0 GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0="credential.helper" '
    'GIT_CONFIG_VALUE_0=""'
)


def _run(step: str, command: str) -> None:
    code, output = shell_capture(command)
    if code != 0:
        raise DeployError(f"{step} failed ({code}): {output}")


def _install_linux_prerequisites() -> None:
    if is_debian_like():
        _run(
            "Install Linux prerequisites (Debian/Ubuntu)",
            "sudo apt-get update && sudo apt-get install -y build-essential curl file git",
        )
    else:
        _run(
            "Install Linux prerequisites (Arch/Manjaro)",
            "sudo pacman -Sy --noconfirm --needed base-devel curl file git",
        )


def _ensure_homebrew_installed(brew: str) -> None:
    if shell_ok(f"test -x {brew}/bin/brew"):
        return
    _run(
        "Install Homebrew",
        '/bin/bash -c "$(curl -fsSL '
        'https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',
    )


def _sync_taps(brew: str, brewfile: str) -> None:
    _run("Update Homebrew", f"{brew}/bin/brew update")

    # Homebrew 4.x security model: taps must be explicitly trusted before use.
    _run(
        "Trust all taps in Brewfile",
        f"""{{
  grep -E '^tap ' {brewfile} | sed -E 's/^tap "([^"]+)".*/\\1/'
  grep -E '^(brew|cask) ' {brewfile} | sed -E 's/^(brew|cask) "([^"]+)".*/\\2/' | \\
    grep -E '^[^/]+/[^/]+/[^/]+' | awk -F'/' '{{print $1 "/" $2}}'
}} | sort -u | while read -r tap; do
  {BREW_ENV} {brew}/bin/brew trust --tap "$tap" 2>/dev/null || true
done""",
    )
    _run(
        "Add all taps from Brewfile",
        f"""grep -E '^tap ' {brewfile} | sed -E 's/^tap "([^"]+)".*/\\1/' | \\
while read -r tap; do
  {NO_GIT_PROMPT_ENV} {BREW_ENV} {brew}/bin/brew tap "$tap" 2>/dev/null || true
done""",
    )


def _install_brewfile_packages(brew: str, brewfile: str) -> None:
    already_satisfied = shell_ok(
        f"{BREW_ENV} {brew}/bin/brew bundle check --file={brewfile}"
    )
    if not already_satisfied:
        _run(
            "Install packages from Brewfile",
            f"{NO_GIT_PROMPT_ENV} {BREW_ENV} "
            f"{brew}/bin/brew bundle install --file={brewfile} --no-upgrade",
        )


@deploy("Homebrew")
def homebrew() -> None:
    brew = brew_prefix()

    if not is_macos():
        _install_linux_prerequisites()

    _ensure_homebrew_installed(brew)

    brewfile = f"~/dotfiles/{'Brewfile' if is_macos() else 'Brewfile.linux'}"
    _sync_taps(brew, brewfile)
    _install_brewfile_packages(brew, brewfile)

    # Homebrew renames gdu to gdu-go to avoid a coreutils conflict. Nothing
    # else in this run depends on this immediately, so it's fine as a real
    # queued operation.
    files.link(
        name="Symlink gdu-go to gdu",
        path=f"{brew}/bin/gdu",
        target=f"{brew}/bin/gdu-go",
    )
