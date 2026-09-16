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
import importlib.util
import os
import re

from pyinfra.api import deploy  # type: ignore[attr-defined]  # pyinfra/#439
from pyinfra.operations import server

from common import dev_tools_path_env, shell_capture

# Assumes the `~/code/<host>/<owner>/<repo>` layout (see root CLAUDE.md). To
# adopt a different layout, change this — e.g. a flat `~/WorkProjects/*`.
OVERLAY_SCAN_GLOBS = ["~/code/*/*/*"]

# `bootstrap/deploy.py` is the pyinfra-era replacement for Ansible's
# include_tasks-based `bootstrap/tasks.yml` hook (which pyinfra has no
# equivalent for — it dynamically interprets arbitrary Ansible YAML, inherently
# Ansible-specific). An overlay ships a module-level `deploy()` callable
# (typically `@deploy`-decorated) in this file; it's imported and called
# in-process, so it can `import common` and any other bootstrap-pyinfra module
# exactly like a first-party deploy in deploys/. First consumer:
# ndotfiles/bootstrap/deploy.py (aimee provisioning).
OVERLAY_DEPLOY_HOOK = "bootstrap/deploy.py"
OVERLAY_LEGACY_HOOK = "bootstrap/tasks.yml"

# Trusted git remote hosts for executing an overlay's deploy.py. deploy.py is
# arbitrary Python that runs in-process (unlike cfgcaddy linking, which only
# ever symlinks files the overlay itself declares) — it can install software,
# call internal APIs, and write credentials. OVERLAY_SCAN_GLOBS matches by
# *path*, not identity, so a personal fork of an overlay repo checked out at
# the same conventional path would otherwise get the exact same provisioning
# code executed against it. Checking the resolved remote host closes that
# gap — but this repo never names a trusted host directly (same reason it
# never names an overlay directly, see the module docstring): hosts come
# from files dropped under ~/.config/dotfiles/trusted-overlay-hosts.d/*.txt
# (one hostname per line, '#' comments allowed), which an overlay supplies
# for itself via its own .cfgcaddy.yml — e.g. a private overlay repo ships
# `trusted-overlay-hosts.d/50-<name>.txt` containing its own git host(s) and
# links it there. Empty/absent by default: fails closed, trusting nothing.
#
# Bootstrap ordering note: cfgcaddy linking is a QUEUED pyinfra operation
# (doesn't run until this whole invocation finishes — see this project's
# README, "Critical rule: queued operations vs. immediate execution"), but
# reading trusted hosts is an IMMEDIATE check. So on a genuinely fresh
# overlay clone, the very first run won't yet see a host file its own
# .cfgcaddy.yml just queued — deploy.py is skipped that once, then runs
# normally on the next invocation once the symlink actually exists. Matches
# this project's existing "run live twice" convention for newly-ported
# deploys (see the per-role migration status table in README.md).
_TRUSTED_HOSTS_GLOB = "~/.config/dotfiles/trusted-overlay-hosts.d/*.txt"


def _trusted_deploy_hook_hosts() -> set[str]:
    hosts: set[str] = set()
    for path in glob.glob(os.path.expanduser(_TRUSTED_HOSTS_GLOB)):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.split("#", 1)[0].strip()
                if line:
                    hosts.add(line)
    return hosts


def _overlay_remote_host(overlay_dir: str) -> str | None:
    code, url = shell_capture(f'git -C "{overlay_dir}" remote get-url origin')
    if code != 0:
        return None
    match = re.search(r"(?:@|://)([^/:]+)[:/]", url.strip() + "/")
    return match.group(1) if match else None


def _run_deploy_hook(overlay_dir: str, deploy_hook_path: str) -> None:
    trusted_hosts = _trusted_deploy_hook_hosts()
    host = _overlay_remote_host(overlay_dir)
    if host not in trusted_hosts:
        print(
            f"Overlay {overlay_dir}: git remote host {host!r} is not in "
            f"{sorted(trusted_hosts)} ({_TRUSTED_HOSTS_GLOB}) — refusing to "
            f"run {OVERLAY_DEPLOY_HOOK}. If this is a real overlay, make sure "
            "it links its own trusted-overlay-hosts.d fragment; if it's a "
            "personal fork or unrelated checkout at a matching path, this is "
            "working as intended."
        )
        return

    module_name = f"_overlay_deploy_{abs(hash(overlay_dir))}"
    spec = importlib.util.spec_from_file_location(module_name, deploy_hook_path)
    if spec is None or spec.loader is None:
        print(f"Overlay {overlay_dir}: could not load {OVERLAY_DEPLOY_HOOK}, skipping.")
        return
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    overlay_deploy = getattr(module, "deploy", None)
    if overlay_deploy is None:
        print(
            f"Overlay {overlay_dir}: {OVERLAY_DEPLOY_HOOK} has no `deploy()` "
            "export, skipping."
        )
        return
    overlay_deploy()


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

        legacy_hook_path = os.path.join(overlay_dir, OVERLAY_LEGACY_HOOK)
        deploy_hook_path = os.path.join(overlay_dir, OVERLAY_DEPLOY_HOOK)
        has_legacy_hook = os.path.isfile(legacy_hook_path)
        has_deploy_hook = os.path.isfile(deploy_hook_path)

        if has_deploy_hook:
            _run_deploy_hook(overlay_dir, deploy_hook_path)
        elif has_legacy_hook:
            print(
                f"Overlay {overlay_dir} ships {OVERLAY_LEGACY_HOOK} (Ansible-only, "
                f"not supported here) but no {OVERLAY_DEPLOY_HOOK} — migrate it to "
                "run under the pyinfra bootstrap."
            )
