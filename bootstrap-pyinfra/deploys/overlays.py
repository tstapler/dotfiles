"""
Port of bootstrap/roles/overlays/tasks/main.yml — generic overlay-repo
discovery. Any directory matched by OVERLAY_SCAN_GLOBS that ships its own
`.cfgcaddy.yml` gets linked automatically. This repo never names the overlay
directly — it only knows the glob pattern — so overlay repos (e.g. an
employer-specific dotfiles overlay) never need to be referenced from this
repo's git history. Inert if nothing matches.

Glob expansion is plain Python stdlib (glob.glob), not a pyinfra fact/shell
command — since this project only ever targets @local, there's no reason to
round-trip local filesystem discovery through a remote-command fact. This
also fixes what the Ansible version worked around: ansible.builtin.find
can't expand a pattern with `*` in more than one path segment (e.g.
"code/*/*/*"), which is why that role had to shell out to bash for globbing.
Python's glob.glob() handles multi-segment `*` natively.
"""

import glob
import os

from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.operations import server

from common import dev_tools_path_env

# Assumes the `~/code/<host>/<owner>/<repo>` layout (see root CLAUDE.md). To
# adopt a different layout, change this — e.g. a flat `~/WorkProjects/*`.
OVERLAY_SCAN_GLOBS = ["~/code/*/*/*"]

# Ansible's include_tasks-based bootstrap/tasks.yml hook has no pyinfra
# equivalent (it dynamically interprets arbitrary Ansible YAML — inherently
# Ansible-specific). No overlay on this machine currently ships one; if that
# changes, migrate the overlay to ship this file instead. Deliberately not
# implementing the "run bootstrap/deploy.py if present" side of this yet —
# there's no real overlay to validate the contract (what it exports, how
# it's invoked) against, so it'd be speculative, untestable code. Build it
# against the first real overlay that needs it.
OVERLAY_DEPLOY_HOOK = "bootstrap/deploy.py"
OVERLAY_LEGACY_HOOK = "bootstrap/tasks.yml"


def _discover_overlay_dirs() -> list[str]:
    dirs: set[str] = set()
    for pattern in OVERLAY_SCAN_GLOBS:
        for path in glob.glob(os.path.expanduser(pattern)):
            if os.path.isdir(path):
                dirs.add(path)
    return sorted(dirs)


@deploy("Overlays")
def overlays() -> None:
    for overlay_dir in _discover_overlay_dirs():
        cfgcaddy_yml = os.path.join(overlay_dir, ".cfgcaddy.yml")
        if os.path.isfile(cfgcaddy_yml):
            server.shell(
                name=f"Link overlay {overlay_dir}",
                commands=[
                    f'PATH="{dev_tools_path_env()}" cfgcaddy link -c "{cfgcaddy_yml}" -y'
                ],
            )

        has_legacy_hook = os.path.isfile(os.path.join(overlay_dir, OVERLAY_LEGACY_HOOK))
        has_deploy_hook = os.path.isfile(os.path.join(overlay_dir, OVERLAY_DEPLOY_HOOK))
        if has_legacy_hook and not has_deploy_hook:
            print(
                f"Overlay {overlay_dir} ships {OVERLAY_LEGACY_HOOK} (Ansible-only, "
                f"not supported here) but no {OVERLAY_DEPLOY_HOOK} — migrate it to "
                "run under the pyinfra bootstrap."
            )
